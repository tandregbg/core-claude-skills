#!/usr/bin/env python3
"""Mechanical hygiene checks for `/ops check` (CR-122, with CR-123 and CR-124).

    python3 hygiene_check.py <folder>            # [FINDING] lines + a count
    python3 hygiene_check.py <folder> --json
    python3 hygiene_check.py <folder> --only links,yaml,tasks,profile,themes

Report only: nothing is rewritten. The fix is a judgement each time (encode the link
or rename the file, map a status or cancel the task), so it stays with a person.

  links    Markdown links in YYMMDD-*.md, README.md and CHANGELOG.md whose target
           holds a raw `(`, `)` or space (write %28 %29 %20), or a relative target
           that resolves to no file, neither from the file's folder nor from any
           folder above it (a vault may write links from its root). External,
           anchor-only and mailto links are skipped.
  yaml     a .yaml file holding \\xNN or \\uNNNN escapes of LETTERS: the signature of
           an agent that loaded and re-dumped the whole file (CR-122 section 2).
  tasks    _tasks.yaml against the declared enums: `task` present, status,
           priority, source.type, file-level scope, and `kind` when the profile
           declares task_kinds (CR-123); a finished task with neither `closed:` nor
           the legacy `completed:` (CR-127). One finding per file, field and value,
           with the task ids, so a ledger with one habit gives one line, not eighty.
  profile  an unknown `profile:` name (CR-123).
  themes   the CR-124 registry checks, when the project enables themes.
  raw      a raw file in `<root>/.transcripts/` with `written_by:` and an empty `summary`,
           older than 14 days: archived by a client, never filed (CR-128). Names the inbox item
           it points to. The one check that reads `.transcripts/`, by name, frontmatter only.

Dot-folders (.archive/, .transcripts/, .knowledge/ ...) are never walked.
"""
import argparse, datetime, json, os, re, sys
from pathlib import Path
from urllib.parse import unquote

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ops-config"))
sys.path.insert(0, str(HERE))
import profiles  # noqa: E402
import themes as themes_mod  # noqa: E402

ECOSYSTEM = HERE.parents[1] / "ecosystem.yaml"
LINKED = re.compile(r"^(\d{6}-.*|README|CHANGELOG)\.md$")
ESCAPE = re.compile(r"\\x([0-9A-Fa-f]{2})|\\u([0-9A-Fa-f]{4})")
# The tasks schema's four, plus the two source kinds the contract declared later as terms
# (content, CR-105; correspondence, CR-080): a task from a report or a mail thread is not drift.
SOURCE_TYPES = ("meeting", "decision", "manual", "imported", "content", "correspondence")
SCOPES = ("root", "org", "project", "personal")
PRIORITIES = ("P0", "P1", "P2", "P3")
CHECKS = ("links", "yaml", "tasks", "profile", "themes", "raw")
RAW_PENDING_DAYS = 14


def walk(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            yield Path(dirpath) / name


def _finding(kind, path, line, message, root):
    try:
        rel = str(Path(path).relative_to(root))
    except ValueError:
        rel = str(path)
    return {"kind": kind, "file": rel, "line": line, "message": message}


# --- links ---------------------------------------------------------------

def link_targets(line: str):
    """Yield the raw target of every inline link `[text](target)` on a line,
    reading to the BALANCED closing parenthesis, so `(live).md)` is seen whole."""
    i = 0
    while True:
        i = line.find("](", i)
        if i < 0:
            return
        j, depth = i + 2, 1
        while j < len(line) and depth:
            if line[j] == "(":
                depth += 1
            elif line[j] == ")":
                depth -= 1
            j += 1
        yield line[i + 2:j - 1] if depth == 0 else line[i + 2:]
        i = j


def check_links(root: Path) -> list:
    found = []
    for p in walk(root):
        if not LINKED.match(p.name):
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        fenced = False
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            for target in link_targets(line):
                t = target.strip()
                if t.startswith("<") and t.endswith(">"):
                    t = t[1:-1]
                    raw_ok = True
                else:
                    raw_ok = False
                    t = t.split(' "')[0] if ' "' in t else t      # [x](file "title")
                if not t or re.match(r"^[a-z][a-z0-9+.-]*:", t, re.I) or t.startswith("#"):
                    continue
                if not raw_ok and re.search(r"[()\s]", t):
                    found.append(_finding("links", p, n, f"raw parenthesis or space in link target: {t} "
                                                         "(write %28 %29 %20)", root))
                    continue
                path = unquote(t.split("#")[0])
                if path and not any((d / path).exists() for d in (p.parent, *p.parent.parents)):
                    found.append(_finding("links", p, n, f"link target does not exist: {t}", root))
    return found


# --- yaml re-dump ---------------------------------------------------------

def check_yaml(root: Path) -> list:
    found = []
    for p in walk(root):
        if p.suffix not in (".yaml", ".yml"):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        letters = 0
        first = None
        for n, line in enumerate(text.splitlines(), 1):
            for m in ESCAPE.finditer(line):
                ch = chr(int(m.group(1) or m.group(2), 16))
                if ch.isalpha():
                    letters += 1
                    first = first or n
        if letters:
            found.append(_finding("yaml", p, first, f"{letters} escaped letter(s) such as \\xE5: the file looks "
                                                    "re-dumped; edit YAML by targeted edit (CR-122)", root))
    return found


# --- tasks ---------------------------------------------------------------

def task_statuses() -> tuple:
    try:
        ts = (yaml.safe_load(ECOSYSTEM.read_text(encoding="utf-8")) or {}).get("task_statuses") or {}
        return tuple(ts.get("active") or []) + tuple(ts.get("finished") or [])
    except (OSError, yaml.YAMLError):
        return ("pending", "in_progress", "blocked", "completed", "cancelled")


def task_finished() -> tuple:
    try:
        ts = (yaml.safe_load(ECOSYSTEM.read_text(encoding="utf-8")) or {}).get("task_statuses") or {}
        return tuple(ts.get("finished") or ()) or ("completed", "cancelled")
    except (OSError, yaml.YAMLError):
        return ("completed", "cancelled")


def check_tasks(root: Path) -> list:
    found, statuses = [], task_statuses()
    finished = task_finished()
    for p in walk(root):
        if p.name != "_tasks.yaml":
            continue
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            found.append(_finding("tasks", p, None, "cannot be parsed", root))
            continue
        kinds = tuple(profiles.resolve(p.parent)["values"].get("task_kinds") or ())
        scope = doc.get("scope")
        if scope is not None and scope not in SCOPES:
            found.append(_finding("tasks", p, None, f"scope '{scope}' is not one of {', '.join(SCOPES)}", root))
        groups = {}                     # (field, value) -> [task ids]
        unclosed = []                   # finished, with no closing day (CR-127)

        def note(field, value, tid):
            groups.setdefault((field, value), []).append(tid)

        for t in doc.get("tasks") or []:
            if not isinstance(t, dict):
                continue
            tid = t.get("id", "?")
            if "task" not in t:
                note("task", "title" if "title" in t else None, tid)
            st = t.get("status")
            if st is not None and st not in statuses:
                note("status", st, tid)
            pr = t.get("priority")
            if pr is not None and pr not in PRIORITIES:
                note("priority", pr, tid)
            src = t.get("source")
            stype = src.get("type") if isinstance(src, dict) else None
            if stype is not None and stype not in SOURCE_TYPES:
                note("source.type", stype, tid)
            kind = t.get("kind")
            if kind is not None and kinds and kind not in kinds:
                note("kind", kind, tid)
            if st in finished and not (t.get("closed") or t.get("completed")):
                unclosed.append(tid)
        legal = {"status": statuses, "priority": PRIORITIES, "source.type": SOURCE_TYPES, "kind": kinds}
        for (field, value), ids in groups.items():
            shown = ", ".join(str(i) for i in ids[:5]) + (f" and {len(ids) - 5} more" if len(ids) > 5 else "")
            if field == "task":
                hint = " (they have `title`; the field is `task`)" if value == "title" else ""
                msg = f"{len(ids)} task(s) without a `task` field{hint}: {shown}"
            else:
                msg = (f"{field} '{value}' on {len(ids)} task(s) is not one of "
                       f"{', '.join(legal[field])}: {shown}")
            found.append(_finding("tasks", p, None, msg, root))
        if unclosed:
            shown = ", ".join(str(i) for i in unclosed[:5]) + (f" and {len(unclosed) - 5} more" if len(unclosed) > 5 else "")
            found.append(_finding("tasks", p, None,
                                  f"{len(unclosed)} finished task(s) with no closing day (`closed:`): {shown}", root))
    return found


# --- profile, themes ------------------------------------------------------

def check_profile(root: Path) -> list:
    r = profiles.resolve(root)
    return [_finding("profile", r["source"] or root, None, w, root) for w in r["warnings"]]


def check_themes(root: Path) -> list:
    found = []
    projects = sorted({p.parent for p in walk(root) if p.name == themes_mod.REGISTRY})
    if themes_mod.enabled(root) and root not in projects:
        projects.insert(0, root)
    for project in projects:
        if not themes_mod.enabled(project):
            continue
        for f in themes_mod.check(project):
            f = dict(f)
            f["file"] = str((project / f["file"]).relative_to(root)) if (project / f["file"]).exists() \
                else f["file"]
            found.append(f)
    return found


def check_raw(root: Path, today=None) -> list:
    tdir = root / ".transcripts"
    if not tdir.is_dir():
        return []
    today = today or datetime.date.today()
    found = []
    for p in sorted(tdir.glob("*-raw.md")):
        try:
            head = p.read_text(encoding="utf-8").split("\n---\n", 1)[0]
        except (OSError, UnicodeDecodeError):
            continue
        fm = {m.group(1): m.group(2).strip() for m in re.finditer(r"^(\w+):[ \t]*(.*)$", head, re.M)}
        if not fm.get("written_by") or fm.get("summary"):
            continue
        try:
            d = fm.get("date", "")
            age = (today - datetime.date(2000 + int(d[:2]), int(d[2:4]), int(d[4:6]))).days
        except (ValueError, IndexError):
            continue
        if age > RAW_PENDING_DAYS:
            found.append(_finding("raw", p, None, f"archived by {fm['written_by']} {age} days ago, never filed"
                                  f" (inbox item: {fm.get('inbox') or 'unknown'})", root))
    return found


def run(root, only=CHECKS) -> list:
    root = Path(root).expanduser()
    out = []
    for name in only:
        out += {"links": check_links, "yaml": check_yaml, "tasks": check_tasks,
                "profile": check_profile, "themes": check_themes, "raw": check_raw}[name](root)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Hygiene checks for /ops check (CR-122). Report only.")
    ap.add_argument("folder")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--only", help="comma-separated subset of: " + ",".join(CHECKS))
    args = ap.parse_args(argv)
    only = tuple(c.strip() for c in args.only.split(",")) if args.only else CHECKS
    bad = [c for c in only if c not in CHECKS]
    if bad:
        print(f"unknown check(s): {', '.join(bad)}", file=sys.stderr)
        return 2
    found = run(args.folder, only)
    if args.json:
        print(json.dumps(found, ensure_ascii=False, indent=2))
    else:
        for f in found:
            where = f["file"] + (f":{f['line']}" if f["line"] else "")
            print(f"[{f['kind'].upper()}] {where}  {f['message']}")
        print(f"{len(found)} hygiene finding(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
