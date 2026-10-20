#!/usr/bin/env python3
"""The ledger's declared attributes: `verksamhet:`, `projekt:`, `objekttyp:` (CR-135).

    python3 task_attributes.py <folder-or-_tasks.yaml>      # [FINDING] lines
    python3 task_attributes.py --validate '<json entry>' --root <folder>

A ledger entry's `context:` used to carry venture, project, activity type and
subject in one free-text slot. Three optional fields split it, each against a
vocabulary the vault already declares:

  verksamhet  one of the ventures the vault declares, or ABSENT. Absent is a valid
              answer: a follow-up or a watch belongs to no business. An undeclared
              value is a finding; an absent one never is.
  projekt     must match a row of the portfolio register (prefix, not equality).
  objekttyp   only when the entry is not an Uppgift; one of the seven object types.
              Anything but Uppgift in a task ledger is a re-mark-and-move candidate.

The vocabulary lives in the vault, not here: `_config/task-attributes.yaml`
(`verksamhet: [...]`, optionally `objekttyp: [...]`) and the portfolio table in
`_INDEX-projekt.md`. A vault that declares nothing gets no findings for the part it
does not declare. Report only (CR-103): nothing is rewritten.

Used by `hygiene_check.py` (`/ops check`) and by the writers at staging, where the
author still knows the venture (CR-132's rule).
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "inbox"))
import survey  # noqa: E402  (portfolio_projects, match_project: one parser, not two)

ECOSYSTEM = HERE.parents[1] / "ecosystem.yaml"
VOCAB_FILE = Path("_config") / "task-attributes.yaml"
PORTFOLIO_FILE = "_INDEX-projekt.md"
DEFAULT_OBJEKTTYP = ("Idé", "Projekt", "Löpande ansvar", "Uppgift", "KPI", "Länk", "Note/logg")
TASK = "Uppgift"


def declared_objekttyp() -> tuple:
    try:
        d = (yaml.safe_load(ECOSYSTEM.read_text(encoding="utf-8")) or {}).get("task_attributes") or {}
        return tuple(d.get("objekttyp") or ()) or DEFAULT_OBJEKTTYP
    except (OSError, yaml.YAMLError):
        return DEFAULT_OBJEKTTYP


def vault_root(start: Path):
    """Nearest folder at or above `start` that holds the vocabulary or the portfolio."""
    p = Path(start).resolve()
    for d in [p] + list(p.parents):
        if d.is_file():
            continue
        if (d / VOCAB_FILE).is_file() or (d / PORTFOLIO_FILE).is_file():
            return d
    return None


def load(start) -> dict:
    """{'verksamhet': tuple, 'objekttyp': tuple, 'projects': {key: name}, 'root': Path|None}.

    An empty `verksamhet` or `projects` means the vault declares none: that part is
    not checked.
    """
    root = vault_root(Path(start))
    vocab = {}
    if root and (root / VOCAB_FILE).is_file():
        try:
            vocab = yaml.safe_load((root / VOCAB_FILE).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            vocab = {}
    return {
        "root": root,
        "verksamhet": tuple(str(v) for v in (vocab.get("verksamhet") or ())),
        "objekttyp": tuple(str(v) for v in (vocab.get("objekttyp") or ())) or declared_objekttyp(),
        "projects": survey.portfolio_projects(root) if root else {},
    }


def validate(entry: dict, vocab: dict) -> list:
    """Problems with one entry, as (field, value, message). Empty = fine."""
    out = []
    for fld in ("verksamhet", "projekt", "objekttyp"):
        x = entry.get(fld)
        if x not in (None, "") and not isinstance(x, str):
            out.append((fld, x, f"{fld} must be a string, got {type(x).__name__}"))
    str_ = lambda f: entry.get(f) if isinstance(entry.get(f), str) else None
    v, p, o = str_("verksamhet"), str_("projekt"), str_("objekttyp")
    if v and vocab["verksamhet"] and v not in vocab["verksamhet"]:
        out.append(("verksamhet", v, f"verksamhet '{v}' is not one of the declared ventures"))
    if p and vocab["projects"] and not survey.match_project(p, vocab["projects"]):
        out.append(("projekt", p, f"projekt '{p}' matches no row in the portfolio"))
    if o:
        known = {t.casefold(): t for t in vocab["objekttyp"]}
        t = known.get(o.casefold())
        if t is None:
            out.append(("objekttyp", o, f"objekttyp '{o}' is not one of {', '.join(vocab['objekttyp'])}"))
        elif t != TASK:
            out.append(("objekttyp", o, f"a {t} is filed as a task: re-mark and move it, never delete (järnregel 2)"))
    return out


def unused_projects(vocab: dict, used: list) -> list:
    """Portfolio rows no entry names. Only meaningful once some entry names a project."""
    if not used:
        return []
    return sorted(name for key, name in vocab["projects"].items()
                  if not any(survey.match_project(str(u), {key: name}) for u in used))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate ledger attributes (CR-135). Report only.")
    ap.add_argument("target", nargs="?", help="a folder or a _tasks.yaml")
    ap.add_argument("--validate", help="one entry as JSON, checked at staging")
    ap.add_argument("--root", help="folder to resolve the vocabulary from (with --validate)")
    a = ap.parse_args(argv)
    if a.validate:
        vocab = load(a.root or ".")
        probs = validate(json.loads(a.validate), vocab)
        for _f, _v, m in probs:
            print(f"[REFUSED] {m}")
        return 1 if probs else 0
    if not a.target:
        ap.error("a target or --validate is required")
    t = Path(a.target)
    files = [t] if t.is_file() else sorted(t.rglob("_tasks.yaml"))
    vocab, used, n = load(t), [], 0
    for f in files:
        try:
            doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        for e in doc.get("tasks") or []:
            if not isinstance(e, dict):
                continue
            if e.get("projekt") and isinstance(e["projekt"], str):
                used.append(e["projekt"])
            for _fld, _val, msg in validate(e, vocab):
                n += 1
                print(f"[FINDING] {f}  #{e.get('id', '?')}  {msg}")
    for name in unused_projects(vocab, used):
        n += 1
        print(f"[FINDING] portfolio row '{name}' has no ledger entries")
    print(f"{n} attribute finding(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
