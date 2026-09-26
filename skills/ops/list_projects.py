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
SKIP = {".archive", ".transcripts", ".handoff", "clones", "node_modules"}
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


def carry_forward_of(cfg: dict) -> dict | None:
    """The carry_forward block as written, or None when there is no block.

    Absent is not the same as declared-without-a-flag: no block means no loop,
    a block without `enabled` means one written before the flag existed.
    """
    cf = ((cfg.get("workflows") or {}).get("post_processing") or {}).get("carry_forward")
    if cf is None:
        return None
    return cf if isinstance(cf, dict) else {"enabled": bool(cf)}


def series_chain(d: Path, root: Path) -> dict | None:
    """carry_forward for a DECLARED series, resolved up the config chain (CR-072).

    A series inherits its loop from an ancestor config -- an org-level weekly has
    no config of its own beyond the declaration -- so reading only the folder's
    file reports a running loop as no loop. Nearest definition wins, matching the
    documented resolution order.

    The walk is deliberately NOT applied to project folders. An org-level
    carry_forward block is typically written for one named series (its
    `note_suffix` names that series), so letting every sibling project inherit it
    would report loops that do not exist -- the same over-reporting shape CR-067
    fixed in the other direction.
    """
    for p in [d, *d.parents]:
        cfg = config_of(p)
        if cfg is not None:
            cf = carry_forward_of(cfg)
            if cf is not None:
                return cf
        if p == root:
            break
    return None


def find_series(root: Path) -> list[Path]:
    """Folders that declare themselves a recurring series (CR-072).

    Opt-in, never inferred. `/ops project list` answers *what is wired*, and a
    series that lives outside the project trees -- an org-level weekly in a
    meetings folder -- is invisible to it however completely its loop runs.
    Inferring instead of declaring would classify every folder carrying an org
    config as a series, including the org root itself.
    """
    out = []
    for f in root.rglob("_ops.yaml"):
        d = f.parent
        rel = d.relative_to(root).parts
        if any(part.startswith(".") or part in SKIP for part in rel):
            continue
        try:
            cfg = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if isinstance(cfg.get("series"), dict):
            out.append(d)
    return out


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
    # Same rule as the note count: a series IS its meetings folder, a project HAS
    # one. Looking only in the subfolder reports "never moved" for a folder whose
    # dated notes sit directly in it.
    src = (d / "meetings") if (d / "meetings").is_dir() else d
    dates = [m.group(1) for f in src.glob("*.md") if (m := DATED.match(f.name))]
    if dates:
        y = max(dates)
        return f"20{y[:2]}-{y[2:4]}-{y[4:]}"
    return "—"


def classify(d: Path, root: Path | None = None) -> tuple[str, dict]:
    cfg = config_of(d)
    # A series IS its meetings folder; a project HAS one. Counting only the
    # subfolder reports a series with hundreds of notes as having none.
    if (d / "meetings").is_dir():
        notes = len([f for f in (d / "meetings").glob("*.md") if DATED.match(f.name)])
    else:
        notes = len([f for f in d.glob("*.md") if DATED.match(f.name)])
    series = (cfg or {}).get("series") if isinstance((cfg or {}).get("series"), dict) else None
    info = {"cfg": cfg is not None, "notes": notes, "last": last_movement(d),
            "changelog": (d / "CHANGELOG.md").exists(), "series": series}
    if cfg is not None:
        # A declared series resolves carry_forward up the chain; a project reads
        # its own config only. See series_chain() for why the two differ.
        cf = series_chain(d, root) if (series and root) else carry_forward_of(cfg)
        # Read the field, not the block (CR-067): a block written to DISABLE
        # carry-forward is a non-empty dict, and testing the block reports it as
        # wired. Declaring enabled: false is the only way a project can decline an
        # org-level carry_forward, so "off" must not read as "on".
        #
        # Absent means enabled, matching build_agenda: a block written before the
        # flag existed described a working loop, and no existing config should
        # change classification because a field was added.
        if cf is not None and cf.get("enabled", True):
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
    seen: set[Path] = set()
    scanned = 0
    for tree in root.rglob("*"):
        if tree.name not in TREES or not tree.is_dir():
            continue
        if any(part.startswith(".") for part in tree.relative_to(root).parts):
            continue
        for d in sorted(tree.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            seen.add(d)
            scanned += 1
            kind, info = classify(d, root)
            found[kind].append((str(d.relative_to(root)), info))

    # Declared series (CR-072) -- wired loops that live outside the project trees.
    for d in find_series(root):
        if d in seen:
            continue
        seen.add(d)
        scanned += 1
        kind, info = classify(d, root)
        found[kind].append((str(d.relative_to(root)), info))

    today = datetime.date.today()
    print(f"Projects — {scanned} folders scanned under {root.name}/\n")
    headings = {
        "wired": ("LOOP WIRED", "/ops orient and build_agenda.py work here."),
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
            # A series is marked, because "wired" must not quietly read as
            # "project": one is a standing meeting, the other a thing that ends.
            # The cadence is shown because escalation thresholds are counted in
            # sessions, and a session is a day on one series and a fortnight on
            # another -- the number means nothing without it.
            tag = ""
            if i.get("series"):
                cadence = i["series"].get("cadence")
                tag = f"  [series{': ' + str(cadence) if cadence else ''}]"
            print(f"    {path[:46]:<46} {notes}   {i['last']:<12} {age}{tag}")
        print()

    print("  Intent — what is actually being driven, with status and sponsor — lives in the vault's")
    print("  hand-written project registry. This list says only what is wired.")


if __name__ == "__main__":
    main()
