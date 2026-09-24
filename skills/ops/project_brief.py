#!/usr/bin/env python3
"""Where a recurring project actually stands, before work resumes (CR-061).

    python3 project_brief.py --dir <project>/meetings

Read-only. Writes nothing, fetches nothing, judges nothing. Everything below is
already machine-readable -- the gap was that nothing read it together, so every
session rebuilt the same picture by hand and lost the parts nobody wrote down.

`/bod` for a coordination project. Both exist because the expensive mistake is not
doing the wrong work; it is doing the right work against yesterday's picture.
"""
import argparse, datetime, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_agenda import (COMPANION, config, carried, has_section, key, owner_of,
                          streak, next_session, recorded_since, since)   # noqa: E402

SENT = ("skickad", "arkiverad")
FIELD = re.compile(r"^\*\*(Status|Projekt):\*\*\s*(.+?)\s*$", re.M)


def days(a: str, b: datetime.date) -> int:
    return (b - datetime.datetime.strptime(a, "%y%m%d").date()).days


def vault(start: Path) -> Path | None:
    return next((p for p in start.parents if (p / "_outbox").is_dir()), None)


def venture(start: Path, sub: str) -> Path | None:
    """The archives are PER VENTURE, not at the vault root -- `<venture>/.teamschats/`.
    Walking up for the folder that holds them is the same resolution build_agenda
    uses; computing it from the vault root instead silently finds nothing and
    reports 'no snapshot', which reads as an archiver problem rather than a bug."""
    return next((p / sub for p in start.parents if (p / sub).is_dir()), None)


def notes(md: Path, cf: dict) -> list[tuple[str, Path]]:
    pat = note_pattern(cf["note_suffix"])
    return sorted((m.group(1), p) for p in md.glob("*.md")
                  if (m := pat.match(p.name)) and not any(c in p.name for c in COMPANION))


def note_pattern(suffix) -> re.Pattern:
    """`note_suffix` is a string or a list of them, each allowing a `*` wildcard.

    A list because a series can legitimately carry more than one filename shape --
    a weekly plus its extra sessions, or a series renamed mid-history. Matching only
    the main shape silently drops the others, and an extra session is where the most
    urgent items tend to live.
    """
    pats = [suffix] if isinstance(suffix, str) else list(suffix)
    alt = "|".join(".+".join(re.escape(x) for x in p.split("*")) for p in pats)
    return re.compile(rf"^(\d{{6}})-(?:{alt})\.md$")


def slurp(f: Path) -> str | None:
    """Read a vault file, or None if it cannot be read right now.

    A cloud-backed vault serves a file synced from another machine as *dataless*
    until it is pulled, and the read raises OSError (EDEADLK) rather than returning
    nothing. This brief reads six kinds of file it does not own, so the failure is a
    CLASS, not a case: fixing it at the chat archive alone left the outbox manifest
    to take the whole run down twenty minutes later. Every such read goes through
    here, and the caller decides what a missing file means.
    """
    try:
        return f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="the project's meetings folder")
    a = ap.parse_args()
    md = Path(a.dir).resolve()
    cf = config(md)
    root, today = cf["_root"], datetime.date.today()
    project_names = {root.name} | ({cf["project"]} if cf.get("project") else set())
    # An org-level series lives in a folder whose config sits further up, so root.name
    # is the venture, not the series. The declared title is the only honest label.
    out = [f"Project brief — {cf.get('title') or root.name}", ""]

    # 1-3. loop position, chain, what is carrying
    hist = notes(md, cf)
    if not hist:
        out += ["  Loop", f"    no YYMMDD-{cf['note_suffix']}.md in {md.name}/", ""]
    else:
        last_date, last = hist[-1]
        nxt = next_session(last_date, cf.get("schedule_days"))
        agenda = md / f"{nxt}-{cf['agenda_suffix']}.md"
        out += ["  Loop",
                f"    newest note     {last.name}  ({days(last_date, today)}d ago)"]

        # CR-087: a session that happened and left no note is invisible to every
        # other line here — notes, agendas, archives and the outbox all read as
        # healthy. It is the one fact that changes what to do next, so it goes
        # directly under the newest note rather than in a block further down.
        tr = (cf.get("ext") or {}).get("transcripts") or {}
        if not tr:
            out.append("    transcripts     NOT DECLARED")
        else:
            rec = recorded_since(cf, since(last_date), None)
            if not rec:
                out.append("    recorded        nothing newer than the note")
            else:
                notes_ = [r["note"] for r in rec if r.get("note")]
                if notes_:
                    for n_ in notes_:
                        out.append(f"    recorded        NOT READ — {n_}")
                else:
                    day = max(r["day"] for r in rec)
                    out.append(f"    recorded        {day} — {len(rec)} recording(s), NO NOTE"
                               "        ← process before the next agenda")
                    # Listed, never chosen between: picking among duplicate
                    # recordings is a judgement the machine cannot make honestly.
                    for r in rec:
                        bits = [r.get("id", "?"), r.get("title", ""), r.get("duration", ""), r.get("variant", "")]
                        out.append("                      " + "  ".join(str(b) for b in bits if b))

        out.append(f"    next session    {nxt}  — agenda {'exists' if agenda.exists() else 'NOT GENERATED'}")
        if has_section(last):
            out.append("    chain           intact")
        else:
            out += ["    chain           ⚠ BROKEN — newest note has no '## Carried forward'",
                    "                    the next agenda will carry nothing and look correct"]
        out.append("")

        items = [(l, r, *streak(key(l), hist)) for l, r in carried(last)]
        if items:
            E, ED = cf["escalate_after"], cf.get("escalate_after_days")
            out.append(f"  Carrying ({len(items)})")
            for lab, rest, n, g, first in sorted(items, key=lambda t: -t[2]):
                age = days(first, today) if first else 0
                hot = n >= E or (ED and age >= ED)
                own = owner_of(lab, rest)
                mark = "⚠" if hot else " "
                extra = f" · skipped {g}" if g else ""
                out.append(f"    {mark} {lab.rstrip(':')[:38]:<38} {own[:20]:<20} {n}× · {age}d{extra}")
            unowned = sum(1 for l, r, *_ in items if owner_of(l, r) == "UNOWNED")
            if unowned:
                out.append(f"    → {unowned} unowned. An item nobody is named against is the one that falls through.")
            out.append("")

    # 4. archive freshness -- a stale archive is worse than none: it still reads as current
    ext, ven = cf.get("ext") or {}, vault(root)
    chats_dir, meta_dir = venture(root, ".teamschats"), venture(root, ".githubmeta")
    lines = []
    for c in ext.get("chats") or []:
        d = None
        if chats_dir:
            # One unreadable _chat.json must not take the whole brief down. On an
            # iCloud-backed vault a file synced from another machine is dataless
            # until it is pulled, and the read raises EDEADLK rather than returning
            # nothing -- so the archive block, which is the least important of the
            # six, was killing the five that matter. Skip what cannot be read and
            # say how many, because a silently short list is the other failure.
            unread = 0
            for f in chats_dir.glob("*/_chat.json"):
                try:
                    if json.loads(slurp(f) or "{}").get("chat_id") == c.get("id"):
                        d = f.parent
                        break
                except (OSError, ValueError):
                    unread += 1
            if d is None and unread:
                lines.append(f"    chat  {str(c.get('name'))[:30]:<30} "
                             f"not resolved -- {unread} archive config(s) unreadable")
                continue
        newest = max((m.group(1) for f in d.glob("*.md")
                      if (m := re.search(r"(\d{4}-\d{2}-\d{2})\.md$", f.name))), default=None) if d else None
        lines.append(f"    chat  {str(c.get('name'))[:30]:<30} {newest or 'no snapshot'}")
    for r in ext.get("repos") or []:
        slug = re.sub(r"^(https?://)?(www\.)?github\.com/", "", r.get("url", "")).strip("/").split("/")[-1]
        d = (meta_dir / slug) if meta_dir else None
        newest = max((m.group(1) for f in d.glob("*.json")
                      if (m := re.search(r"(\d{4}-\d{2}-\d{2})\.json$", f.name))), default=None) \
            if d and d.is_dir() else None
        lines.append(f"    repo  {slug[:30]:<30} {newest or 'no snapshot'}")
    if lines:
        out += ["  Archives"] + lines
        if any("no snapshot" in l for l in lines):
            out += ["    → a stale or missing archive is worse than none: retrieval still produces a",
                    "      block, and it reads as current."]
        out.append("")

    # 5. staged and unsent -- a meetings-folder file carries no status; this is where it shows
    if ven:
        rows = []
        for man in sorted((ven / "_outbox").glob("*/_manifest.md")):
            if (txt := slurp(man)) is None:
                continue
            f = dict(FIELD.findall(txt))
            # An org-level series resolves its config from a venture folder, so
            # root.name is the venture, not the series -- the same mismatch that made
            # the heading wrong. A manifest names the series, so the series must be
            # declarable rather than inferred from a directory.
            if f.get("Projekt", "").strip() not in project_names:
                continue
            st = f.get("Status", "").strip()
            if any(st.lower().startswith(x) for x in SENT):
                continue
            dm = re.match(r"(\d{6})", man.parent.name)
            # An item staged AHEAD of its session is the normal case for an agenda,
            # and a negative age reads as a bug rather than as "not yet due".
            n = days(dm.group(1), today) if dm else None
            age = "?" if n is None else (f"{n}d" if n >= 0 else f"in {-n}d")
            rows.append(f"    {man.parent.name[:38]:<38} {st[:26]:<26} {age}")
        if rows:
            out += [f"  Staged, not sent ({len(rows)})"] + rows + [""]

    # 6. record movement -- when anyone last wrote this project down, not when a file was touched
    ch = root / "CHANGELOG.md"
    if ch.exists():
        m = re.search(r"^## \[(\d{4}-\d{2}-\d{2})\]", slurp(ch) or "", re.M)
        out += ["  Record", f"    CHANGELOG last entry   {m.group(1) if m else 'none parsed'}", ""]

    print("\n".join(out))


if __name__ == "__main__":
    main()
