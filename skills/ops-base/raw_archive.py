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
import argparse, json, re, sys
from pathlib import Path

# The closing fence may end the file (empty body) and the file may use CRLF.
FM = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
HEAD_BYTES = 65536


def split(text: str):
    """(frontmatter with \\n line ends, body). The body is returned exactly as read."""
    m = FM.match(text)
    if not m:
        return None, text
    return m.group(1).replace("\r\n", "\n"), text[m.end():]


def _nl(text: str) -> str:
    return "\r\n" if text.startswith("---\r\n") else "\n"


def _render(fm: str, body: str, nl: str = "\n") -> str:
    return f"---{nl}{fm.replace(chr(10), nl)}{nl}---{nl}{body}"


def read_head(path):
    """Frontmatter of a file, reading only its head (never the body), or None.

    `.transcripts/` is read-locked in a vault; the one sanctioned reader is the frontmatter
    of a pending raw file (CR-128), so the body must not be pulled in."""
    try:
        with open(path, "rb") as f:
            head = f.read(HEAD_BYTES).decode("utf-8", errors="ignore")
    except OSError:
        return None
    return split(head)[0]


def _unq(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        try:
            return json.loads(v)
        except ValueError:
            return v[1:-1]
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    if v.startswith("#"):
        return ""
    return re.split(r"[ \t]+#", v, maxsplit=1)[0].strip()


def _q(v: str) -> str:
    """A YAML scalar for a path or text: double-quoted when plain style would break."""
    if v == "" or re.search(r": |:$|[ \t]#|^[-?:,\[\]{}#&*!|>'\"%@`~ ]|[ \t]$|^(?i:null|true|false|yes|no|on|off)$", v):
        return json.dumps(v, ensure_ascii=False)
    return v


def get(fm: str, key: str):
    """Scalar value of a top-level key, '' when empty or absent (quotes and comments removed)."""
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", fm, re.M)
    return _unq(m.group(1)) if m else ""


def is_pending(fm: str) -> bool:
    """No summary yet: empty, a bare comment, or an explicit null/\"\"/''."""
    return fm is not None and get(fm, "summary").lower() in ("", "null", "~")


def source_ids(fm: str):
    """The source ids of a raw file; a merged file carries several, comma separated."""
    return [i.strip() for i in get(fm, "source_id").split(",") if i.strip()]


def find(vault, inbox=None, source_id=None):
    """The raw file for an inbox item or a source_id, or None. Pointer first, then source_id
    (a merged file answers to each of its ids)."""
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
                source_id = get(ifm, "source_id") or None
    if source_id and tdir.is_dir():
        for p in sorted(tdir.glob("*-raw.md")):
            fm, _ = split(p.read_text(encoding="utf-8"))
            if fm and source_id in source_ids(fm):
                return p
    return None


def _set(fm: str, key: str, block: str) -> str:
    """Replace a top-level key (and its indented/list continuation) by `block`, or append it."""
    pat = re.compile(rf"^{re.escape(key)}:.*(?:\n(?:[ \t]+.*|- .*))*", re.M)
    return pat.sub(lambda _m: block, fm, 1) if pat.search(fm) else fm + "\n" + block


def _list(key: str, items) -> str:
    return f"{key}:\n" + "\n".join(f"  - {_q(i)}" for i in items) if items else f"{key}: []"


def _items(fm: str, key: str):
    m = re.search(rf"^{re.escape(key)}:[ \t]*(\[\])?[ \t]*\n((?:[ \t]*- .*\n?)*)", fm + "\n", re.M)
    return [_unq(l.strip()[2:]) for l in m.group(2).splitlines() if l.strip()] if m else []


def adopt_one(raw: Path, stem: str, summary: str, created, disposition=""):
    """One recording, one summary (or a further summary of an already adopted file)."""
    text = raw.read_text(encoding="utf-8", newline="")
    fm, body = split(text)
    nl = _nl(text)
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
        raw.write_text(_render(fm, body, nl), encoding="utf-8", newline="")
        return raw
    fm = _set(fm, "summary", f"summary: {_q(summary)}")
    fm = _set(fm, "summaries", _list("summaries", [summary]))
    if disposition:
        fm = _set(fm, "disposition", f"disposition: {_q(disposition)}")
    fm = _set(fm, "created_files", _list("created_files", created))
    target = raw.with_name(f"{stem}-raw.md")
    if target.exists() and target != raw:
        raise FileExistsError(str(target))
    target.write_text(_render(fm, body, nl), encoding="utf-8", newline="")
    if target != raw:
        raw.unlink()
    return target


def adopt_merged(raws, stem: str, summary: str, created, disposition=""):
    """Several pending recordings, one summary: one merged file, originals removed after a
    byte-for-byte comparison of every body in its own slot."""
    parsed = []
    for r in raws:
        text = r.read_text(encoding="utf-8", newline="")
        fm, body = split(text)
        if fm is None:
            raise ValueError(f"{r}: no frontmatter")
        parsed.append((r, fm, body, _nl(text)))
    head = parsed[0][1]
    nl = parsed[0][3]
    parts = []
    for r, fm, body, _ in parsed:
        meta = " | ".join(f"{k}: {get(fm, k)}" for k in ("source_id", "source_file", "duration", "variant"))
        parts.append((f"<!-- {meta} -->\n\n", body))
    sep = "\n\n---\n\n"
    ids = [get(fm, "source_id") for _, fm, _, _ in parsed]
    head = _set(head, "source_id", "source_id: " + _q(", ".join(i for i in ids if i)))
    head = _set(head, "summary", f"summary: {_q(summary)}")
    head = _set(head, "summaries", _list("summaries", [summary]))
    head = _set(head, "disposition",
                f"disposition: {_q(disposition or 'merged: ' + str(len(raws)) + ' recordings')}")
    head = _set(head, "created_files", _list("created_files", created))
    target = raws[0].with_name(f"{stem}-raw.md")
    if target.exists() and target not in raws:
        raise FileExistsError(str(target))
    target.write_text(_render(head, sep.join(a + b for a, b in parts), nl), encoding="utf-8", newline="")
    written = split(target.read_text(encoding="utf-8", newline=""))[1]
    pos, ok = 0, True
    for (lead, body), (_, _, orig, _) in zip(parts, parsed):
        end = pos + len(lead) + len(body)
        ok = ok and written[pos:end] == lead + orig and written[pos + len(lead):end] == orig
        pos = end + len(sep)
        ok = ok and (pos - len(sep) == len(written) or written[end:pos] == sep)
    if not ok or pos - len(sep) != len(written):
        if target not in raws:
            target.unlink()
        raise RuntimeError("merged bodies differ from the originals; originals kept")
    for r, *_ in parsed:
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
    adopted = [f for f in found if f not in pending]
    # Pending files first (renamed or merged), then the summary is appended to each file already adopted.
    if len(pending) > 1:
        print(adopt_merged(pending, a.stem, a.summary, a.created, a.disposition))
    elif pending:
        print(adopt_one(pending[0], a.stem, a.summary, a.created, a.disposition))
    for f in adopted:
        print(adopt_one(f, a.stem, a.summary, a.created, a.disposition))
    return 0


if __name__ == "__main__":
    sys.exit(main())
