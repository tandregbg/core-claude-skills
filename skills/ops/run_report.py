#!/usr/bin/env python3
"""The unattended run's report, and `/ops apply` (CR-179).

    python3 run_report.py allowed --dir <folder> --step prepare|process [--type <type>]
    python3 run_report.py guard <path> [<path> ...]
    python3 run_report.py write --dir <folder> --step <step> --date YYMMDD [--type <type>]
                                [--written <path> ...] [--proposed <file>] [--stopped <reason>]
    python3 run_report.py show  <folder> [YYMMDD]
    python3 run_report.py apply <folder> [YYMMDD] [--write] [--only 1,3] [--unattended]

An unattended run differs from an attended one in four ways, and this script is the part of
each that can be checked rather than trusted:

* a question it would have asked is written as `[OPEN: <question>]` where it arises -- `write`
  collects every marker from the files the run wrote and lists them first;
* an outbox item it stages carries Status `draft` -- `write` reports any other status;
* it creates new dated files only -- `guard` stops a run before it writes over anything, and
  `write` reports a written path that is not dated;
* shared ledgers are PROPOSED, not written -- the proposals go into the report, and `apply`
  writes them from the attended session, or from the run itself only where the series
  declares `apply_ledgers: true`.

The report is the run's final output, so a scheduler can forward it as the notification, and
it is kept as a new dated file in `<project>/.runs/` so `apply` can read it later. Frontmatter
carries the data, the body the same thing for a person.

A proposed ledger change is one of four operations, and nothing else can be expressed:

    - file: CHANGELOG.md            # relative to the project folder; stays inside the vault
      op: insert_before             # insert_before | insert_after | append | create
      anchor: "## [2026-11-18]"     # insert_*: one whole line, present exactly once
      text: |
        ## [2026-11-19]
        - ...
      why: one line, optional

`apply` computes every change in memory first and writes nothing if any of them fails --
an anchor missing or repeated, a YAML ledger that would no longer parse, a `create` over a
file that exists. Then it writes exactly the proposed text, and records in the report which
changes were applied and when, so the same change cannot be applied twice.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "outbox"))
import meeting_schedule as ms  # noqa: E402
import resolved  # noqa: E402  (the outbox manifest reader; one vocabulary for status)

RUNS = ".runs"
OPEN = re.compile(r"\[OPEN:\s*(.+?)\]")
OPS = ("insert_before", "insert_after", "append", "create")
DATED = re.compile(r"^\d{6}[a-z]?-")
FETCH_BLOCK = re.compile(r"^## Fetch problems\s*$(.*?)(?=^## |\Z)", re.M | re.S)
EXIT_REFUSED, EXIT_NOT_ALLOWED, EXIT_EXISTS, EXIT_NOTHING = 1, 2, 3, 4


# ---- where things are ---------------------------------------------------------------

def project_root(start: Path) -> Path:
    """The folder a run's report belongs to: the nearest at or above `start` that holds a
    config file, or a `.runs/` folder already. `start` itself when there is neither."""
    start = Path(start).resolve()
    for p in (start, *start.parents):
        if (p / RUNS).is_dir() or any((p / n).is_file() for n in ms.CONFIG_FILES):
            return p
    return start


def vault_root(start: Path) -> Path | None:
    return next((p for p in (start, *start.parents) if (p / "_outbox").is_dir()), None)


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root))
    except ValueError:
        return str(p)


def _sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def target_path(root: Path, rel: str) -> tuple[Path | None, str]:
    """Where a proposed change writes, or (None, why). Never absolute, never into a
    dot-folder -- the archives and the restricted folders are not ledgers -- and never
    outside the vault (or the project, where no vault is found)."""
    if not rel or Path(rel).is_absolute():
        return None, "path must be relative to the project folder"
    if any(part.startswith(".") and part not in (".", "..") for part in Path(rel).parts):
        return None, "a dot-folder is not a ledger"
    p = (root / rel).resolve()
    fence = vault_root(root) or root
    try:
        p.relative_to(fence.resolve())
    except ValueError:
        return None, "path leaves the vault"
    return p, ""


# ---- the declaration ------------------------------------------------------------------

def entry_for(folder: Path, step: str | None, typ: str | None):
    return ms.select(ms.declared(folder)["meetings"], step, typ)


def cmd_allowed(a) -> int:
    entry, why = entry_for(Path(a.dir), a.step, a.type)
    if not entry:
        print(why)
        return EXIT_NOT_ALLOWED
    print(json.dumps(ms.public(entry), ensure_ascii=False))
    return 0


def cmd_guard(a) -> int:
    taken = [p for p in a.paths if Path(p).exists()]
    for p in taken:
        print(f"EXISTS {p}")
    if taken:
        print("unattended run stopped -- an existing file is never edited; nothing written")
        return EXIT_EXISTS
    print("clear")
    return 0


# ---- the report -----------------------------------------------------------------------

def open_markers(paths: list[Path], root: Path) -> list[dict]:
    out = []
    for p in paths:
        if p.suffix not in (".md", ".txt") or not p.is_file():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in OPEN.finditer(line):
                out.append({"file": _rel(p, root), "line": n, "question": m.group(1).strip()})
    return out


def fetch_problems(paths: list[Path]) -> list[str]:
    out = []
    for p in paths:
        if p.suffix != ".md" or not p.is_file():
            continue
        m = FETCH_BLOCK.search(p.read_text(encoding="utf-8", errors="replace"))
        if m:
            out += [l[2:].strip() for l in m.group(1).splitlines() if l.startswith("- ")]
    return list(dict.fromkeys(out))


def written_problems(paths: list[Path], root: Path) -> list[str]:
    """What a run wrote that an unattended run may not: an undated file, a missing one, an
    outbox manifest whose status is past draft."""
    out = []
    for p in paths:
        r = _rel(p, root)
        if not p.exists():
            out.append(f"{r}: listed as written, does not exist")
            continue
        if p.name == "_manifest.md":
            if not DATED.match(p.parent.name):
                out.append(f"{r}: outbox folder is not dated")
            st = resolved.read_fields(p.read_text(encoding="utf-8")).get("status", "")
            if resolved.status_kind(st) != "draft":
                out.append(f"{r}: outbox status is {st or 'missing'!r} -- an unattended run stages `draft` only")
        elif not DATED.match(p.name):
            out.append(f"{r}: not a new dated file")
    return out


def load_proposed(path: str | None) -> list:
    if not path:
        return []
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    if isinstance(raw, dict):
        raw = raw.get("proposed") or []
    return raw if isinstance(raw, list) else []


def check_change(c, root: Path) -> str:
    if not isinstance(c, dict):
        return "not a mapping"
    if c.get("op") not in OPS:
        return f"op {c.get('op')!r} is not one of {', '.join(OPS)}"
    _p, why = target_path(root, str(c.get("file") or ""))
    if why:
        return why
    if c["op"].startswith("insert_") and not str(c.get("anchor") or "").strip():
        return "an insert needs an anchor line"
    if not isinstance(c.get("text"), str) or not c["text"].strip():
        return "no text"
    return ""


def report_path(root: Path, date: str, step: str, typ: str | None) -> Path:
    d = root / RUNS
    tail = f"-{step}" + (f"-{typ}" if typ else "") + ".md"
    for suffix in ("", *"bcdefghijklmnopqrstuvwxyz"):
        p = d / f"{date}{suffix}{tail}"
        if not p.exists():
            return p
    raise SystemExit("more than 26 reports for one day -- something is looping")


class _Dumper(yaml.SafeDumper):
    """Multi-line text as a literal block, so a proposed change reads as the text it writes."""


_Dumper.add_representer(str, lambda d, v: d.represent_scalar(
    "tag:yaml.org,2002:str", v, style="|" if "\n" in v else None))


def render(fm: dict) -> str:
    """The report: data in the frontmatter, the same facts in the body for a person."""
    title = f"Run report -- {fm['step']}" + (f" {fm['type']}" if fm.get("type") else "") + f" {fm['date']}"
    B = [f"# {title}", ""]
    if fm.get("stopped"):
        B += [f"**Stopped:** {fm['stopped']}", ""]
    B += [f"## Open questions ({len(fm['open'])})", ""]
    B += [f"- [OPEN] {o['question']} -- `{o['file']}:{o['line']}`" for o in fm["open"]] or ["*None.*"]
    B.append("")
    if fm["fetch_problems"]:
        B += ["## Fetch problems", ""] + [f"- {x}" for x in fm["fetch_problems"]] + [""]
    if fm["problems"]:
        B += [f"## Problems ({len(fm['problems'])})", ""] + [f"- {x}" for x in fm["problems"]] + [""]
    B += [f"## Files written ({len(fm['written'])})", ""]
    B += [f"- `{w}`" for w in fm["written"]] or ["*None.*"]
    B.append("")
    if fm["apply_ledgers"]:
        how = "the series declares `apply_ledgers: true`; the run applies them"
    else:
        how = f"not written. From the attended session: `/ops apply <folder> {fm['date']}`"
    B += [f"## Ledger changes proposed ({len(fm['proposed'])}) -- {how}", ""]
    for c in fm["proposed"]:
        state = "applied" if c["id"] in fm["applied"] else "pending"
        where = f" {c['anchor']!r}" if c.get("anchor") else ""
        B.append(f"{c['id']}. `{c['file']}` {c['op']}{where} ({state})"
                 + (f" -- {c['why']}" if c.get("why") else ""))
    if not fm["proposed"]:
        B.append("*None.*")
    B.append("")
    head = yaml.dump(fm, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000)
    return f"---\n{head}---\n\n" + "\n".join(B)


def cmd_write(a) -> int:
    folder = Path(a.dir).resolve()
    root = project_root(folder)
    if not re.fullmatch(r"\d{6}", a.date or ""):
        print("--date must be YYMMDD")
        return EXIT_REFUSED
    entry, _why = entry_for(folder, None, a.type)
    written = [Path(w).resolve() for w in a.written or []]
    problems = written_problems(written, root)
    proposed = []
    for n, c in enumerate(load_proposed(a.proposed), 1):
        why = check_change(c, root)
        if why:
            problems.append(f"proposed change {n}: {why} -- left out")
            continue
        tp, _ = target_path(root, c["file"])
        proposed.append({"id": len(proposed) + 1, "file": c["file"], "op": c["op"],
                         **({"anchor": c["anchor"]} if c["op"].startswith("insert_") else {}),
                         "text": c["text"] if c["text"].endswith("\n") else c["text"] + "\n",
                         **({"why": c["why"]} if c.get("why") else {}),
                         "base_sha256": _sha(tp)})
    fm = {"run_report": 1, "step": a.step, "type": a.type or (entry or {}).get("type"),
          "date": a.date, "written_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
          "status": "stopped" if a.stopped else ("problems" if problems else "complete"),
          "stopped": a.stopped or None,
          "apply_ledgers": bool(entry and entry.get("apply_ledgers")),
          "open": open_markers(written, root), "fetch_problems": fetch_problems(written),
          "problems": problems, "written": [_rel(w, root) for w in written],
          "proposed": proposed, "applied": [], "applied_at": None, "applied_by": None}
    out = report_path(root, a.date, a.step, fm["type"])
    out.parent.mkdir(exist_ok=True)
    text = render(fm)
    with open(out, "x", encoding="utf-8") as f:   # exclusive: a report never overwrites one
        f.write(text)
    print(f"report: {_rel(out, root)}\n")
    print(text)
    return 0


# ---- apply ----------------------------------------------------------------------------

def read_report(p: Path) -> dict | None:
    txt = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return None
    fm = yaml.safe_load(m.group(1)) or {}
    return fm if isinstance(fm, dict) and fm.get("run_report") else None


def pending_reports(folder: Path, date: str | None) -> tuple[Path, list[tuple[Path, dict]]]:
    root = project_root(folder)
    runs = sorted((root / RUNS).glob("*.md")) if (root / RUNS).is_dir() else []
    found = []
    for p in runs:
        if date and not p.name.startswith(date):
            continue
        fm = read_report(p)
        if not fm:
            continue
        if any(c["id"] not in (fm.get("applied") or []) for c in fm.get("proposed") or []):
            found.append((p, fm))
    if not date and found:
        newest = max(str(fm["date"]) for _p, fm in found)
        found = [(p, fm) for p, fm in found if str(fm["date"]) == newest]
    return root, found


def _edit(content: str | None, c: dict) -> tuple[str | None, str]:
    text = c["text"]
    if c["op"] == "create":
        return (None, "file exists -- create never overwrites") if content is not None else (text, "")
    if content is None:
        return None, "file does not exist"
    if c["op"] == "append":
        return content + ("" if content.endswith("\n") or not content else "\n") + text, ""
    lines = content.splitlines(keepends=True)
    hits = [i for i, l in enumerate(lines) if l.rstrip("\r\n") == c["anchor"]]
    if len(hits) != 1:
        return None, f"anchor {c['anchor']!r} found {len(hits)} times -- must be exactly once"
    i = hits[0] + (1 if c["op"] == "insert_after" else 0)
    if c["op"] == "insert_after" and not lines[hits[0]].endswith("\n"):
        lines[hits[0]] += "\n"
    return "".join(lines[:i]) + text + "".join(lines[i:]), ""


def plan(root: Path, reports, only: set[int] | None):
    """Every change computed in memory, in report order. (new contents, notes, errors)."""
    state: dict[Path, str | None] = {}
    notes, errors, chosen = [], [], []
    for rp, fm in reports:
        for c in fm.get("proposed") or []:
            if c["id"] in (fm.get("applied") or []) or (only and c["id"] not in only):
                continue
            label = f"{rp.name}#{c['id']}"
            tp, why = target_path(root, c["file"])
            if why:
                errors.append(f"{label}: {why}")
                continue
            if tp not in state:
                state[tp] = tp.read_text(encoding="utf-8") if tp.exists() else None
                if c.get("base_sha256") and _sha(tp) not in (None, c["base_sha256"]):
                    notes.append(f"{label}: {c['file']} changed since the run -- applied by anchor")
            new, why = _edit(state[tp], c)
            if why:
                errors.append(f"{label}: {c['file']}: {why}")
                continue
            state[tp] = new
            chosen.append((rp, c))
    for tp, txt in state.items():
        if tp.suffix in (".yaml", ".yml") and txt is not None:
            try:
                yaml.safe_load(txt)
            except yaml.YAMLError as e:
                errors.append(f"{tp.name}: would no longer parse as YAML ({str(e).splitlines()[0]})")
    return state, chosen, notes, errors


def show(reports, only) -> None:
    for rp, fm in reports:
        print(f"{rp.name} -- {fm.get('step')} {fm.get('type') or ''} {fm.get('date')}".rstrip())
        for c in fm.get("proposed") or []:
            if c["id"] in (fm.get("applied") or []) or (only and c["id"] not in only):
                continue
            where = f" {c['anchor']!r}" if c.get("anchor") else ""
            print(f"  {c['id']}. {c['file']} {c['op']}{where}" + (f" -- {c['why']}" if c.get("why") else ""))
            for l in c["text"].rstrip("\n").splitlines():
                print(f"     + {l}")


def mark_applied(rp: Path, ids: list[int], by: str) -> None:
    # The body is re-rendered from the frontmatter, so the two cannot disagree.
    fm = read_report(rp)
    fm["applied"] = sorted(set(fm.get("applied") or []) | set(ids))
    fm["applied_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    fm["applied_by"] = by
    rp.write_text(render(fm), encoding="utf-8")


def cmd_apply(a, write: bool) -> int:
    folder = Path(a.folder).resolve()
    if a.date and not re.fullmatch(r"\d{6}", a.date):
        print("date must be YYMMDD")
        return EXIT_REFUSED
    only = {int(x) for x in a.only.split(",")} if getattr(a, "only", None) else None
    root, reports = pending_reports(folder, a.date)
    if not reports:
        print("no run report with pending ledger changes" + (f" for {a.date}" if a.date else ""))
        return EXIT_NOTHING
    if getattr(a, "unattended", False):
        # The run applying its own proposals: only where the series has earned it, in config.
        for _rp, fm in reports:
            entry, why = entry_for(folder, None, fm.get("type"))
            if not entry or not entry.get("apply_ledgers"):
                print(f"not applied -- `apply_ledgers` is not true for {fm.get('type')!r}"
                      + (f" ({why})" if why else "") + "; the changes stay proposed")
                return EXIT_NOT_ALLOWED
    show(reports, only)
    state, chosen, notes, errors = plan(root, reports, only)
    for n in notes:
        print(f"  note: {n}")
    if errors:
        print("\nnothing written:")
        for e in errors:
            print(f"  ! {e}")
        return EXIT_REFUSED
    if not write:
        print(f"\n{len(chosen)} change(s) shown, nothing written. Run with --write to apply.")
        return 0
    for tp, txt in state.items():
        if txt is not None:
            tp.write_text(txt, encoding="utf-8")
    by = "unattended run" if getattr(a, "unattended", False) else "attended session"
    for rp, _fm in reports:
        ids = [c["id"] for r_, c in chosen if r_ == rp]
        if ids:
            mark_applied(rp, ids, by)
    print(f"\n{len(chosen)} change(s) written to {len(state)} file(s).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("allowed")
    p.add_argument("--dir", required=True)
    p.add_argument("--step", required=True, choices=ms.STEPS)
    p.add_argument("--type")
    p = sub.add_parser("guard")
    p.add_argument("paths", nargs="+")
    p = sub.add_parser("write")
    p.add_argument("--dir", required=True)
    p.add_argument("--step", required=True, choices=ms.STEPS)
    p.add_argument("--date", required=True)
    p.add_argument("--type")
    p.add_argument("--written", nargs="*")
    p.add_argument("--proposed")
    p.add_argument("--stopped")
    for name in ("show", "apply"):
        p = sub.add_parser(name)
        p.add_argument("folder")
        p.add_argument("date", nargs="?")
        p.add_argument("--only", help="comma-separated change ids")
        if name == "apply":
            p.add_argument("--write", action="store_true")
            p.add_argument("--unattended", action="store_true",
                           help="the run applying its own proposals; refused unless apply_ledgers: true")
    a = ap.parse_args(argv)
    if a.cmd == "allowed":
        return cmd_allowed(a)
    if a.cmd == "guard":
        return cmd_guard(a)
    if a.cmd == "write":
        return cmd_write(a)
    return cmd_apply(a, write=a.cmd == "apply" and a.write)


if __name__ == "__main__":
    sys.exit(main())
