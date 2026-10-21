#!/usr/bin/env python3
"""Mechanical hygiene checks for `/ops check` (CR-122, with CR-123 and CR-124).

    python3 hygiene_check.py <folder>            # [FINDING] lines + a count
    python3 hygiene_check.py <folder> --json
    python3 hygiene_check.py <folder> --only links,yaml,tasks,profile,themes,inferred

Report only: nothing is rewritten. The fix is a judgement each time (encode the link
or rename the file, map a status or cancel the task), so it stays with a person.

  links    Markdown links whose target holds a raw `(`, `)` or space (write %28 %29 %20),
           or a relative target that does not resolve from the file's own folder.
           Five classes (CR-137), because they need different people:
             moved      exactly one file of that name exists elsewhere -- the computed
                        relative path is the offered fix. Mechanical.
             ambiguous  several candidates -- all listed, none chosen.
             dead       no file of that name anywhere. **A content finding:** the
                        document claims a source that does not exist.
             ancestor   resolves only from a folder above the file's own. Was silently
                        accepted before CR-137; reported, not failed, so an adopting
                        vault is not met by a wall of them.
             privacy    two tiers. `sealed`: a link into .handoff/ from any living document
                        -- written once, indexed nowhere, referenced from nothing. `outgoing`: a link
                        into one person's private material (.notes/board-private/) from a
                        document staged to LEAVE (_outbox/). A private note linking its
                        owner's other private notes is normal practice and is not flagged.
                        Reported whatever the link's state, and the offered fix is REMOVAL,
                        not repair: a broken link into restricted material is an inoperative
                        leak, and repairing it mechanically restores it.
           Scope is every .md file by default; `workflows.sweep.links.scope: dated`
           restores the pre-CR-137 set (YYMMDD-*, README, CHANGELOG). External,
           anchor-only and mailto links are skipped.
  yaml     a .yaml file holding \\xNN or \\uNNNN escapes of LETTERS: the signature of
           an agent that loaded and re-dumped the whole file (CR-122 section 2).
  tasks    _tasks.yaml against the declared enums: `task` present, status,
           priority, source.type, file-level scope, and `kind` when the profile
           declares task_kinds (CR-123); a finished task with neither `closed:` nor
           the legacy `completed:` (CR-127); `verksamhet:` outside the vault's declared
           ventures, `projekt:` with no portfolio row, a portfolio row no entry names,
           and an `objekttyp:` other than Uppgift still filed as a task (CR-135; absent
           fields are never findings). One finding per file, field and value,
           with the task ids, so a ledger with one habit gives one line, not eighty.
  profile  an unknown `profile:` name (CR-123).
  themes   the CR-124 registry checks, when the project enables themes.
  inferred a decision whose note still carries `*inferred: <what>*` (CR-142): something that was
           not said and is in no source, written where the register reads as decided. Reported
           per decision line, with what was inferred. A line that also carries
           `*confirmed: <source>*` is not a finding -- the inference has its source and the next
           summary drops the marker. Scope is the decisions section of any .md file (Decisions,
           Beslut, Decision register and their variants), because that is where a guess written
           as a fact survived two days and had to be corrected. Fenced blocks are skipped, as in
           `links`: an illustrative marker is not a decision, and a `#` comment inside a fence
           is not a heading that ends the section.
  raw      a raw file in `<root>/.transcripts/` with `written_by:` and an empty `summary`,
           older than 14 days: archived by a client, never filed (CR-128). Names the inbox item
           it points to. The one check that reads `.transcripts/` (read-locked in a vault): by name, and only the
           first 64 KiB of each raw file, never its body. The lock exemption is written in CR-128.

Dot-folders (.archive/, .transcripts/, .knowledge/ ...) are never walked; the one exception is
the `raw` check, which opens `.transcripts/*-raw.md` by name and reads the head only.
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
# CR-142: the inference marker has ONE reader, the one the agenda uses. A second copy of
# the pattern here would let the agenda and this check disagree about the same line, and
# a marker that means two things is worse than no marker.
import build_agenda  # noqa: E402
sys.path.insert(0, str(HERE.parent / "ops-base"))
import raw_archive  # noqa: E402
sys.path.insert(0, str(HERE.parent / "tasks"))
import task_attributes  # noqa: E402

ECOSYSTEM = HERE.parents[1] / "ecosystem.yaml"
LINKED_DATED = re.compile(r"^(\d{6}-.*|README|CHANGELOG)\.md$")   # pre-CR-137 scope
LINKED = LINKED_DATED                                              # kept: imported elsewhere
# Read-restricted paths (CR-137 class 5), in two tiers because they are two different rules.
# SEALED: the vault's own hard rule -- a frozen snapshot is written once, indexed nowhere and
# referenced from no living document. A link into one is a finding from anywhere.
# `.transcripts/` is deliberately NOT here: a summary naming the raw file it was built from is
# the vault's own provenance convention, and flagging it fired 175 times on one vault.
SEALED = (".handoff",)
# PRIVATE: material that is one person's to read. A planning note of their own may link it; a
# document that LEAVES (staged in an outbox, or carrying a send manifest) may not. Flagged only
# for outgoing sources -- otherwise the check fires on normal practice and gets ignored.
PRIVATE = (".notes/board-private",)
OUTGOING = ("_outbox",)
ESCAPE = re.compile(r"\\x([0-9A-Fa-f]{2})|\\u([0-9A-Fa-f]{4})")
# The tasks schema's four, plus the two source kinds the contract declared later as terms
# (content, CR-105; correspondence, CR-080): a task from a report or a mail thread is not drift.
SOURCE_TYPES = ("meeting", "decision", "manual", "imported", "content", "correspondence")
SCOPES = ("root", "org", "project", "personal")
PRIORITIES = ("P0", "P1", "P2", "P3")
CHECKS = ("links", "yaml", "tasks", "profile", "themes", "raw", "inferred")
RAW_PENDING_DAYS = 14
# CR-142: what was inferred, pulled out of the marker the agenda's reader matched, so the
# finding can name the phrase to go and ask about. The agenda's own, not a copy: the module
# comment above says the marker has one reader, and the words it names are part of that --
# two patterns would let this check and the *Confirm or drop* column quote different words
# off one line (defect pass). Re-exported because `INFERRED_WHAT` was a name here first.
INFERRED_WHAT = build_agenda.INFERRED_WHAT
# A decisions section, in either declared language and in the shapes a register uses:
# `## Beslut`, `## Decisions`, `### Decision register`, `## Decisions & Rationale`.
DECISIONS_HEADING = re.compile(r"^#{1,6}\s*(?:\d+[.)]\s*)?(decisions?|beslut)\b", re.I)
HEADING = re.compile(r"^#{1,6}\s")


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


def _links_scope(root: Path):
    """Which files are link-checked. `all` (default, CR-137) or `dated` (pre-CR-137)."""
    try:
        cfg = profiles.resolve(root).get("config") or {}
    except Exception:
        cfg = {}
    scope = (((cfg.get("workflows") or {}).get("sweep") or {}).get("links") or {}).get("scope")
    if scope in (None, "all"):
        return None                       # every .md
    if scope == "dated":
        return LINKED_DATED
    try:
        return re.compile(scope)          # a vault may name its own pattern
    except re.error:
        return None


def _basename_index(root: Path):
    """basename -> [paths], over the whole vault the scope sits in. Built once, and only
    when something is already broken: it is the difference between `moved` and `dead`."""
    top = root
    for d in (root, *root.parents):
        if (d / "_inbox").is_dir() or (d / "INDEX.md").is_file():
            top = d
            break
    index = {}
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", "__pycache__", ".git")]
        for name in filenames:
            index.setdefault(name, []).append(Path(dirpath) / name)
        for name in dirnames:
            index.setdefault(name + "/", []).append(Path(dirpath) / name)
    return index


def _under(path: Path, parts) -> bool:
    s = str(path).replace(os.sep, "/") + "/"
    return any(("/" + r + "/") in s for r in parts)


def _crossing(src: Path, tgt: Path):
    """The privacy class, or None. Two tiers -- see SEALED / PRIVATE."""
    if _under(tgt, SEALED) and not _under(src, SEALED):
        return ("sealed", "a frozen snapshot / raw transcript is referenced from no living document")
    if _under(tgt, PRIVATE) and not _under(src, PRIVATE) and _under(src, OUTGOING):
        return ("outgoing", "this document is staged to leave the vault")
    return None


def check_links(root: Path) -> list:
    root = Path(root)
    pattern = _links_scope(root)
    found, broken, private = [], [], {}
    for p in walk(root):
        if p.suffix != ".md" or (pattern and not pattern.match(p.name)):
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
                    t, raw_ok = t[1:-1], True
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
                if not path:
                    continue
                own = (p.parent / path)
                # class 5 first: a crossing is a finding even when the link resolves
                if _under(own, PRIVATE) and not _under(p, PRIVATE) and not _under(p, OUTGOING):
                    # not a finding per link: a planning note of one's own may reference
                    # one's own private material. Counted once per run instead (CR-137).
                    private[p] = private.get(p, 0) + 1
                cross = _crossing(p, own)
                if cross:
                    why = cross[1]
                    found.append(_finding("links", p, n,
                                          f"privacy ({cross[0]}): {t} -- {why}. Offered fix is REMOVAL "
                                          "(keep the reference as text), not repair: a broken link into "
                                          "restricted material is an inoperative leak", root))
                    continue
                if own.exists():
                    continue
                broken.append((p, n, t, path))

    if private:
        top = sorted(private.items(), key=lambda kv: -kv[1])[:5]
        names = ", ".join(f"{_finding('links', f, None, '', root)['file']} ({c})" for f, c in top)
        found.append(_finding("links", root, None,
                              f"privacy (advisory): {sum(private.values())} link(s) in {len(private)} living "
                              f"document(s) point into private material -- {names}"
                              f"{' ...' if len(private) > 5 else ''}. Not a finding per link: an owner's own "
                              "planning note may reference it. Review whether any of these are SHARED -- "
                              "a document a colleague opens must not carry the link", root))
    if not broken:
        return found
    index = _basename_index(root)
    for p, n, t, path in broken:
        if any((d / path).exists() for d in p.parent.parents):
            found.append(_finding("links", p, n, f"ancestor: resolves only from a folder above its own: {t} "
                                                 "(wrong relative to this file)", root))
            continue
        base = os.path.basename(path.rstrip("/"))
        key = base + "/" if path.rstrip().endswith("/") else base
        cands = index.get(key) or index.get(base) or []
        if len(cands) == 1:
            new = os.path.relpath(cands[0], p.parent)
            if path.rstrip().endswith("/"):
                new += "/"
            note = " [target is archived]" if "/.archive/" in str(cands[0]).replace(os.sep, "/") else ""
            found.append(_finding("links", p, n, f"moved: {t} -> {new}{note}", root))
        elif cands:
            found.append(_finding("links", p, n, f"ambiguous: {t} -- {len(cands)} candidates, "
                                                 "none chosen", root))
        else:
            found.append(_finding("links", p, n, f"dead: no file named {base} anywhere in the vault "
                                                 f"-- this document claims a source that does not exist: {t}",
                                  root))
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
    attrs = task_attributes.load(root)      # CR-135: the vault's declared vocabulary
    used_projects = []
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
        attr_groups = {}                # (field, message) -> [task ids] (CR-135)

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
            if st in finished and all(t.get(k) in (None, "") for k in ("closed", "completed")):
                unclosed.append(tid)
            if t.get("projekt"):
                used_projects.append(t["projekt"])
            for fld, _val, msg in task_attributes.validate(t, attrs):
                attr_groups.setdefault((fld, msg), []).append(tid)
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
        for (fld, msg), ids in attr_groups.items():
            shown = ", ".join(str(i) for i in ids[:5]) + (f" and {len(ids) - 5} more" if len(ids) > 5 else "")
            found.append(_finding("tasks", p, None, f"{msg}, on {len(ids)} task(s): {shown}", root))
        if unclosed:
            shown = ", ".join(str(i) for i in unclosed[:5]) + (f" and {len(unclosed) - 5} more" if len(unclosed) > 5 else "")
            found.append(_finding("tasks", p, None,
                                  f"{len(unclosed)} finished task(s) with no closing day (`closed:`): {shown}", root))
    # A row is "unused" only over the whole vault; a sub-folder run sees a slice of the ledger.
    whole = attrs["root"] is not None and Path(attrs["root"]).resolve() == Path(root).resolve()
    for name in (task_attributes.unused_projects(attrs, used_projects) if whole else ()):
        found.append(_finding("tasks", (attrs["root"] or root) / task_attributes.PORTFOLIO_FILE, None,
                              f"portfolio row '{name}' has no ledger entries (`projekt:`)", root))
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
        fm = raw_archive.read_head(p)  # the head only: the body of a raw file is never read
        if fm is None or not raw_archive.get(fm, "written_by") or not raw_archive.is_pending(fm):
            continue
        try:
            d = raw_archive.get(fm, "date")
            filed = datetime.date(2000 + int(d[:2]), int(d[2:4]), int(d[4:6]))
        except (ValueError, IndexError):
            # no usable date: fall back on the file's own age
            filed = datetime.date.fromtimestamp(p.stat().st_mtime)
        age = (today - filed).days
        written_by = raw_archive.get(fm, "written_by")
        if age > RAW_PENDING_DAYS:
            found.append(_finding("raw", p, None, f"archived by {written_by} {age} days ago, never filed"
                                  f" (inbox item: {raw_archive.get(fm, 'inbox') or 'unknown'})", root))
    return found


# --- inferred ------------------------------------------------------------

def check_inferred(root: Path) -> list:
    """CR-142, proposal 2: a decision whose note still carries an unconfirmed inference.

    A register line reads as settled whatever it was built from. One meeting's audio was
    partly garbled, three phrases were resolved by guessing and written as facts, and two
    days later a decision register line had to be corrected -- the marker was written on
    the carried lines but nothing read it where the decision itself lived. So this reads
    it: inside a decisions section, a line holding `*inferred: ...*` and no
    `*confirmed: ...*` is a finding, and the message carries what was inferred so the
    reader knows which phrase to go and ask about.

    A fenced block is skipped, exactly as `check_links` skips one (defect pass): inside a
    fence a hash-prefixed comment line matches `HEADING`, so a `# set the day` in a code
    sample closed the decisions section and a real unconfirmed inference below the fence
    was MISSED; and the example marker in a document explaining the convention was
    reported as a finding on the documentation itself. Neither line is a decision.

    Report only, like every other check here: confirming an inference or dropping it is
    a person's judgement, and a tool that edited the register would be making the same
    mistake the marker exists to prevent.
    """
    found = []
    for p in walk(root):
        if p.suffix != ".md":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "inferred" not in text.lower():
            continue                       # the usual case: one pass, no line walk
        inside, fenced = False, False
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            if HEADING.match(line):
                # A heading ends the previous section whether or not it opens a new one,
                # so an inference further down the file is not attributed to decisions.
                inside = bool(DECISIONS_HEADING.match(line))
                continue
            if not inside or not build_agenda.inferred(line):
                continue
            what = build_agenda.inferred_what(line)
            found.append(_finding("inferred", p, n,
                                  f"decision carries an unconfirmed inference ({what}): confirm it with"
                                  " a source and drop the marker, or write what is known (CR-142)", root))
    return found


def run(root, only=CHECKS) -> list:
    root = Path(root).expanduser()
    out = []
    for name in only:
        out += {"links": check_links, "yaml": check_yaml, "tasks": check_tasks,
                "profile": check_profile, "themes": check_themes, "raw": check_raw,
                "inferred": check_inferred}[name](root)
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
