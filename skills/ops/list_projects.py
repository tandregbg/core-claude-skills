#!/usr/bin/env python3
"""Which folders are pipelines, and which are just material (CR-065).

    python3 list_projects.py                  # search from the vault root
    python3 list_projects.py --root <path>    # or a specific tree

Read-only. A folder under a projects tree may be a running loop or a pile of
transcripts, and from the outside they look identical - same depth, same naming,
several with a CHANGELOG and a meetings/ folder. This says which is which before a
session assumes.

It does NOT replace a hand-written project registry. That file carries intent -
what a person is driving - and is authoritative for it. "What am I driving" and
"what is wired" are different questions; this answers only the second.
"""
import argparse, datetime, re, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml")

TREES = ("_projects", "_products")
DATED = re.compile(r"^(\d{6})-.*\.md$")


def vault_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "_outbox").is_dir() and (p / "_inbox").is_dir():
            return p
    return start


def config_of(d: Path) -> dict | None:
    for f in (d / ".claude" / "ops-config.yaml", d / "_ops.yaml"):
        if f.exists():
            try:
                return yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except Exception:
                return {}
    return None


def last_movement(d: Path) -> str:
    """When the record last moved -- not when a file was touched.

    A changelog entry is a deliberate act; an mtime is whatever a sync did last.
    Falls back to the newest dated meeting file, then to nothing.
    """
    ch = d / "CHANGELOG.md"
    if ch.exists():
        m = re.search(r"^## \[(\d{4}-\d{2}-\d{2})\]", ch.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    dates = [m.group(1) for f in (d / "meetings").glob("*.md") if (m := DATED.match(f.name))] \
        if (d / "meetings").is_dir() else []
    if dates:
        y = max(dates)
        return f"20{y[:2]}-{y[2:4]}-{y[4:]}"
    return "—"


def classify(d: Path) -> tuple[str, dict]:
    cfg = config_of(d)
    notes = len([f for f in (d / "meetings").glob("*.md") if DATED.match(f.name)]) \
        if (d / "meetings").is_dir() else 0
    info = {"cfg": cfg is not None, "notes": notes, "last": last_movement(d),
            "changelog": (d / "CHANGELOG.md").exists()}
    if cfg is not None:
        pp = (cfg.get("workflows") or {}).get("post_processing") or {}
        if pp.get("carry_forward"):
            return "wired", info
        return "configured", info
    if notes or info["changelog"]:
        return "material", info
    return "dormant", info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    a = ap.parse_args()
    root = Path(a.root).resolve() if a.root else vault_root(Path.cwd().resolve())

    found = {k: [] for k in ("wired", "configured", "material", "dormant")}
    scanned = 0
    for tree in root.rglob("*"):
        if tree.name not in TREES or not tree.is_dir():
            continue
        if any(part.startswith(".") for part in tree.relative_to(root).parts):
            continue
        for d in sorted(tree.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            scanned += 1
            kind, info = classify(d)
            found[kind].append((str(d.relative_to(root)), info))

    today = datetime.date.today()
    print(f"Projects — {scanned} folders scanned under {root.name}/\n")
    headings = {
        "wired": ("LOOP WIRED", "/ops brief and build_agenda.py work here."),
        "configured": ("CONFIGURED, NO LOOP", "/ops processes meetings; the agenda and carry-forward steps do not apply."),
        "material": ("MATERIAL ONLY", "No config. Notes, transcripts, documents — not a pipeline, and often correctly so."),
        "dormant": ("EMPTY OR DORMANT", "No config, no dated notes, no changelog."),
    }
    for kind in ("wired", "configured", "material", "dormant"):
        rows = found[kind]
        if not rows:
            continue
        head, why = headings[kind]
        print(f"  {head} ({len(rows)})")
        print(f"    {why}\n")
        # Undated rows sort last, not first: a folder that has never moved is the
        # least interesting thing in the group, and string-sorting put it on top.
        for path, i in sorted(rows, key=lambda r: (r[1]["last"] != "—", r[1]["last"]), reverse=True):
            age = ""
            if i["last"] != "—":
                try:
                    age = f"{(today - datetime.date.fromisoformat(i['last'])).days}d ago"
                except ValueError:
                    pass
            notes = f"{i['notes']:>4} notes" if i["notes"] else "   — notes"
            print(f"    {path[:46]:<46} {notes}   {i['last']:<12} {age}")
        print()

    print("  Intent — what is actually being driven, with status and sponsor — lives in the vault's")
    print("  hand-written project registry. This list says only what is wired.")


if __name__ == "__main__":
    main()
