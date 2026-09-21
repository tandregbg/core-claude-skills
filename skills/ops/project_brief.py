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
                          streak, next_session)                      # noqa: E402

SENT = ("skickad", "arkiverad")
FIELD = re.compile(r"^\*\*(Status|Projekt):\*\*\s*(.+?)\s*$", re.M)


def days(a: str, b: datetime.date) -> int:
    return (b - datetime.datetime.strptime(a, "%y%m%d").date()).days


def vault(start: Path) -> Path | None:
    return next((p for p in start.parents if (p / "_outbox").is_dir()), None)


def venture(start: Path, sub: str) -> Path | None:
    """The archives are PER VENTURE, not at the vault root -- `<venture>/.chats/`.
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
                f"    newest note     {last.name}  ({days(last_date, today)}d ago)",
                f"    next session    {nxt}  — agenda {'exists' if agenda.exists() else 'NOT GENERATED'}"]
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
    chats_dir, meta_dir = venture(root, ".chats"), venture(root, ".githubmeta")
    lines = []
    for c in ext.get("chats") or []:
        d = None
        if chats_dir:
            d = next((f.parent for f in chats_dir.glob("*/_chat.json")
                      if json.loads(f.read_text(encoding="utf-8")).get("chat_id") == c.get("id")), None)
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
            f = dict(FIELD.findall(man.read_text(encoding="utf-8")))
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
        m = re.search(r"^## \[(\d{4}-\d{2}-\d{2})\]", ch.read_text(encoding="utf-8"), re.M)
        out += ["  Record", f"    CHANGELOG last entry   {m.group(1) if m else 'none parsed'}", ""]

    print("\n".join(out))


if __name__ == "__main__":
    main()
