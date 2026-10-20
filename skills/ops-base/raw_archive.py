#!/usr/bin/env python3
"""Adopt a raw transcript a client archived at delivery (CR-128).

    python3 raw_archive.py find  <vault> --inbox <inbox item> | --source-id <id>
    python3 raw_archive.py adopt <vault> <summary stem> --summary <rel path> [--disposition "..."]
                                 --created <rel path> ... (--inbox <item> | --source-id <id>) ...

A client (a recorder app) may write `.transcripts/<capture id>-raw.md` at delivery, with an empty
`summary` and `written_by:`. The RAW SOURCE ARCHIVE step adopts it instead of writing a second one:

  one recording, one summary    rename to `<stem>-raw.md`, fill summary/summaries/disposition/
                                created_files; `written_by` and `source_id` stay; the body is
                                never edited.
  several recordings, one       write the merged file (each body unchanged under its own separator
  summary                       and metadata line), compare bodies byte for byte, only then remove
                                the adopted originals.
  already adopted (summary set) a second summary appends to `summaries` and `created_files`;
                                nothing is renamed.
  nothing pending               returns None: the caller writes the raw file as before (CR-085).

Frontmatter is edited line by line, never re-dumped, so the body and the key order survive.
"""
import argparse, re, sys
from pathlib import Path

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def split(text: str):
    m = FM.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def get(fm: str, key: str):
    """Scalar value of a top-level key, '' when empty or absent."""
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", fm, re.M)
    return m.group(1).strip() if m else ""


def is_pending(fm: str) -> bool:
    return fm is not None and get(fm, "summary") == ""


def find(vault, inbox=None, source_id=None):
    """The raw file for an inbox item or a source_id, or None. Pointer first, then source_id."""
    vault = Path(vault)
    tdir = vault / ".transcripts"
    if inbox:
        item = vault / inbox if not Path(inbox).is_absolute() else Path(inbox)
        if item.exists():
            ifm, _ = split(item.read_text(encoding="utf-8"))
            ptr = get(ifm, "raw_transcript") if ifm else ""
            if ptr and (vault / ptr).exists():
                return vault / ptr
            if ifm and not source_id:
                source_id = get(ifm, "external_id") or get(ifm, "source_id") or None
    if source_id and tdir.is_dir():
        for p in sorted(tdir.glob("*-raw.md")):
            fm, _ = split(p.read_text(encoding="utf-8"))
            if fm and get(fm, "source_id") == source_id:
                return p
    return None


def _set(fm: str, key: str, block: str) -> str:
    """Replace a top-level key (and its indented/list continuation) by `block`, or append it."""
    pat = re.compile(rf"^{re.escape(key)}:.*(?:\n(?:[ \t]+.*|- .*))*", re.M)
    return pat.sub(lambda _m: block, fm, 1) if pat.search(fm) else fm + "\n" + block


def _list(key: str, items) -> str:
    return f"{key}:\n" + "\n".join(f"  - {i}" for i in items) if items else f"{key}: []"


def _items(fm: str, key: str):
    m = re.search(rf"^{re.escape(key)}:[ \t]*(\[\])?[ \t]*\n((?:[ \t]*- .*\n?)*)", fm + "\n", re.M)
    return [l.strip()[2:].strip() for l in m.group(2).splitlines() if l.strip()] if m else []


def adopt_one(raw: Path, stem: str, summary: str, created, disposition=""):
    """One recording, one summary (or a further summary of an already adopted file)."""
    fm, body = split(raw.read_text(encoding="utf-8"))
    if fm is None:
        raise ValueError(f"{raw}: no frontmatter")
    if not is_pending(fm):
        sums = _items(fm, "summaries")
        if summary not in sums:
            sums.append(summary)
        files = _items(fm, "created_files")
        files += [c for c in created if c not in files]
        fm = _set(fm, "summaries", _list("summaries", sums))
        fm = _set(fm, "created_files", _list("created_files", files))
        raw.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
        return raw
    fm = _set(fm, "summary", f"summary: {summary}")
    fm = _set(fm, "summaries", _list("summaries", [summary]))
    if disposition:
        fm = _set(fm, "disposition", f"disposition: {disposition}")
    fm = _set(fm, "created_files", _list("created_files", created))
    target = raw.with_name(f"{stem}-raw.md")
    if target.exists() and target != raw:
        raise FileExistsError(str(target))
    target.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
    if target != raw:
        raw.unlink()
    return target


def adopt_merged(raws, stem: str, summary: str, created, disposition=""):
    """Several pending recordings, one summary: one merged file, originals removed after a
    byte-for-byte comparison of every body."""
    parsed = []
    for r in raws:
        fm, body = split(r.read_text(encoding="utf-8"))
        parsed.append((r, fm, body))
    first = parsed[0][1]
    parts = []
    for r, fm, body in parsed:
        meta = " | ".join(f"{k}: {get(fm, k)}" for k in ("source_id", "source_file", "duration", "variant"))
        parts.append(f"<!-- {meta} -->\n\n{body}")
    sep = "\n\n---\n\n"
    ids = [get(fm, "source_id") for _, fm, _ in parsed]
    head = first
    head = _set(head, "source_id", "source_id: " + ", ".join(i for i in ids if i))
    head = _set(head, "summary", f"summary: {summary}")
    head = _set(head, "summaries", _list("summaries", [summary]))
    head = _set(head, "disposition", f"disposition: {disposition or 'merged: ' + str(len(raws)) + ' recordings'}")
    head = _set(head, "created_files", _list("created_files", created))
    target = raws[0].with_name(f"{stem}-raw.md")
    target.write_text(f"---\n{head}\n---\n" + sep.join(parts), encoding="utf-8")
    written = target.read_text(encoding="utf-8")
    if not all(body in written for _, _, body in parsed):
        target.unlink()
        raise RuntimeError("merged bodies differ from the originals; originals kept")
    for r, _, _ in parsed:
        if r != target:
            r.unlink()
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Adopt a pending raw transcript (CR-128).")
    ap.add_argument("action", choices=("find", "adopt"))
    ap.add_argument("vault")
    ap.add_argument("stem", nargs="?")
    ap.add_argument("--inbox", action="append", default=[])
    ap.add_argument("--source-id", action="append", default=[])
    ap.add_argument("--summary")
    ap.add_argument("--disposition", default="")
    ap.add_argument("--created", action="append", default=[])
    a = ap.parse_args(argv)
    found = [f for f in [find(a.vault, i, None) for i in a.inbox] +
             [find(a.vault, None, s) for s in a.source_id] if f]
    found = list(dict.fromkeys(found))
    if a.action == "find":
        for f in found:
            print(f)
        return 0 if found else 1
    if not found:
        print("nothing pending: write the raw file as before")
        return 1
    if not (a.stem and a.summary):
        ap.error("adopt needs a stem and --summary")
    pending = [f for f in found if is_pending(split(f.read_text(encoding="utf-8"))[0])]
    if len(pending) > 1:
        print(adopt_merged(pending, a.stem, a.summary, a.created, a.disposition))
    else:
        print(adopt_one(found[0], a.stem, a.summary, a.created, a.disposition))
    return 0


if __name__ == "__main__":
    sys.exit(main())
