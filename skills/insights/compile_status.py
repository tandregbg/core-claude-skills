#!/usr/bin/env python3
"""The compile backlog, as one number (CR-175).

    python3 compile_status.py <vault-or-folder>           # the line, and the folders behind it
    python3 compile_status.py <vault> --json              # for another reader
    python3 compile_status.py <vault> --quiet             # the aggregate line alone

CR-020 wrote `last_compiled` so that a never-running synthesis loop would be visible
instead of silent, and `/ops check` class 2 reads it correctly -- per folder. On a
133-ledger vault that means the operator meets the fact once per folder, scattered
through a report with eleven other classes in it, and **nothing anywhere states the
total**. Measured 2026-11-04 on one vault: 24 ledgers had never been compiled, 18 were
over 30 days behind their own newest entry, and the corpus held 3,389 entries. Finding
that took a session; being told it takes a line.

The arithmetic lives here rather than in each of the three readers (`/ops check`,
`/insights status`, `/analytics`), so they cannot report different numbers for the same
corpus -- the reason CR-100 put promotion's gates in one script.

NEVER and STALE are counted apart, because they have different fixes: a ledger with no
stamp has never been read back since the folder was created (a setup gap), while a stale
one ran and then stopped (a cadence gap).

A file that cannot be read is NAMED, never dropped and never fatal (CR-145, CR-177).
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:                                     # pragma: no cover
    sys.exit("needs pyyaml")

SKIP = {".archive", ".transcripts", ".handoff", "clones", "node_modules"}
STALE_DAYS = 30


def insight_files(root: Path):
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP and not d.startswith(".git"))
        if "_insights.yaml" in filenames:
            yield Path(dirpath) / "_insights.yaml"


def ymd(value):
    """YYMMDD -> date. Anything else is None, which is how an undated entry reads."""
    s = str(value or "").strip().strip("'\"")
    if not re.fullmatch(r"\d{6}", s):
        return None
    try:
        return datetime.date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
    except ValueError:
        return None


def scan(root: Path, stale_days: int = STALE_DAYS) -> dict:
    out = {"root": str(root), "stale_days": stale_days, "ledgers": 0, "entries": 0,
           "active": 0, "never": [], "stale": [], "current": [], "unreadable": []}
    for f in insight_files(root):
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            out["unreadable"].append({"file": str(f), "error": type(error).__name__})
            continue
        if not isinstance(doc, dict):
            out["unreadable"].append({"file": str(f),
                                      "error": f"not a mapping ({type(doc).__name__})"})
            continue
        entries = [e for e in (doc.get("insights") or []) if isinstance(e, dict)]
        out["ledgers"] += 1
        out["entries"] += len(entries)
        out["active"] += sum(1 for e in entries if str(e.get("status", "active")) == "active")
        try:
            rel = str(f.parent.relative_to(root))
        except ValueError:
            rel = str(f.parent)
        dates = [d for d in (ymd(e.get("date")) for e in entries) if d]
        newest = max(dates) if dates else None
        compiled = ymd(doc.get("last_compiled"))
        row = {"folder": rel, "entries": len(entries),
               "newest": newest.isoformat() if newest else None,
               "last_compiled": compiled.isoformat() if compiled else None}
        if compiled is None:
            out["never"].append(row)
        elif newest and (newest - compiled).days > stale_days:
            row["behind_days"] = (newest - compiled).days
            out["stale"].append(row)
        else:
            out["current"].append(row)
    out["never"].sort(key=lambda r: -r["entries"])
    out["stale"].sort(key=lambda r: -r.get("behind_days", 0))
    return out


def line(report: dict) -> str:
    """The one line. Every reader prints this before any per-folder finding."""
    return (f"insights: {report['ledgers']} ledgers, {report['entries']} entries. "
            f"{len(report['never'])} never compiled, {len(report['stale'])} stale "
            f"(>{report['stale_days']}d), {len(report['current'])} current.")


def consequence(report: dict):
    """What the number costs, in words. Omitted when there is nothing to say."""
    uncompiled = sum(r["entries"] for r in report["never"])
    if not report["never"]:
        return None
    return (f"The promotion pass has never run over {uncompiled} entries in "
            f"{len(report['never'])} ledgers, so no hypothesis in them can become a rule.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="a vault root, a folder, or one _insights.yaml")
    ap.add_argument("--stale-days", type=int, default=STALE_DAYS)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="the aggregate line alone")
    a = ap.parse_args(argv)

    report = scan(Path(a.target).expanduser(), a.stale_days)
    if a.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    print(line(report))
    why = consequence(report)
    if why:
        print(f"  {why}")
    if a.quiet:
        return 0
    if report["never"]:
        print(f"\nNever compiled ({len(report['never'])}) -- a setup gap: the loop has not run here at all")
        for r in report["never"][:12]:
            print(f"    {r['entries']:5d} entries  {r['folder']}")
        if len(report["never"]) > 12:
            print(f"    ... and {len(report['never']) - 12} more")
    if report["stale"]:
        print(f"\nStale ({len(report['stale'])}) -- a cadence gap: it ran, then stopped")
        for r in report["stale"][:12]:
            print(f"    {r['behind_days']:5d}d behind  {r['folder']}  ({r['entries']} entries)")
        if len(report["stale"]) > 12:
            print(f"    ... and {len(report['stale']) - 12} more")
    if report["unreadable"]:
        print(f"\nUnreadable ({len(report['unreadable'])}) -- outside the loop until migrated")
        for u in report["unreadable"]:
            print(f"    {u['error']}: {u['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
