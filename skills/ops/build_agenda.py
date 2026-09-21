#!/usr/bin/env python3
"""Generate the next standup agenda from the last daily note's carry-forward.

The gap this closes: a series writes an agenda, holds the meeting, records a note --
and nothing compares them. Items fall through silently, and the same item can lead
the agenda twice without anyone noticing it was skipped twice.

    python3 build_agenda.py --dir <project>/meetings
    python3 build_agenda.py --dir <project>/meetings --date 260922

Reads every `YYMMDD-<note_suffix>.md`, takes the `## Carried forward` section of the
newest, and counts how many CONSECUTIVE prior notes carried the same item. Three
sessions is the signal: the problem is not the agenda, it is that nobody owns it.

Config, from the project's `.claude/ops-config.yaml`:

    workflows:
      post_processing:
        carry_forward:
          enabled: true
          note_suffix: daily-standup        # YYMMDD-<this>.md; `*` is a wildcard
          agenda_suffix: agenda-daily-standup
          title: "Webapp v3 — daily standup"
          time: "10:30 CET / 14:00 IST · 40 min"
          escalate_after: 3
          round_columns: [Track]            # extra blank columns in the round table
    people:
      - name: Name                        # the round table, in order

Nothing here is series-specific. Owner is read from a defined position, never guessed
from prose -- see `owner_of`.
"""
import argparse, json, re, sys, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml -- run with a python that has it")

SECTION = re.compile(r"^## Carried forward\s*$(.*?)(?=^## |\Z)", re.M | re.S)
# Companion artifacts that sit in the same folder as the note and must never be
# mistaken for one. A wildcard note_suffix matches greedily -- "coreteam-weekly-w*"
# otherwise swallows "...-w38-appendix-dashboard-db-modifications", and
# "bi-weekly-*" swallows "bi-weekly-preparation-...". /ops lint skips the same set.
COMPANION = ("-agenda", "agenda-", "-preparation", "preparation-", "-förberedelse",
             "förberedelse-", "-priorities", "priorities-", "-facilitator",
             "facilitator-", "-appendix", "-recap", "-mejl", "-teams")
ITEM = re.compile(r"^-\s+\*\*(.+?)\*\*(.*)$", re.M)


def external(root: Path) -> dict:
    """external_systems (CR-054, contract 16) resolved by the normal config chain:
    project `.claude/ops-config.yaml`, then the folder's `_ops.yaml`."""
    for name in (".claude/ops-config.yaml", "_ops.yaml"):
        p = root / name
        if p.exists():
            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            if es := d.get("external_systems"):
                return es
    return {}


def config(meetings: Path) -> dict:
    """Nearest declaration wins, walking up. A recurring series is not always a
    project -- an org-level meetings folder has no `.claude/ops-config.yaml`, only a
    folder `_ops.yaml` further up, and looking for the former alone silently found
    nothing and fell back to defaults."""
    for root in (meetings, *meetings.parents):
        for name in (Path(".claude") / "ops-config.yaml", Path("_ops.yaml")):
            p = root / name
            if not p.exists():
                continue
            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            cf = (d.get("workflows", {}).get("post_processing", {}) or {}).get("carry_forward", {}) or {}
            if not cf:
                continue
            src = d.get("external_systems") or {}
            cf.setdefault("note_suffix", "daily-standup")
            cf.setdefault("agenda_suffix", "agenda-" + cf["note_suffix"])
            cf.setdefault("escalate_after", 3)
            cf.setdefault("escalate_after_days", 14)
            cf["people"] = [p_["name"] for p_ in (d.get("people") or []) if p_.get("name")]
            cf["ext"] = src or external(root)
            if not cf.get("schedule_days"):
                mt = (d.get("meeting_types") or {}).values()
                sched = next((m.get("schedule", {}).get("days") for m in mt
                              if isinstance(m, dict) and m.get("schedule", {}).get("days")), None)
                cf["schedule_days"] = cf.get("schedule_days") or sched
            cf["_root"] = root
            return cf
    return {"note_suffix": "daily-standup", "agenda_suffix": "agenda-daily-standup",
            "escalate_after": 3, "escalate_after_days": 14, "people": [],
            "ext": external(meetings.parent),
            "_root": meetings.parent}


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


def owner_of(label: str, rest: str) -> str:
    """Owner comes from a defined position, never from guessing at prose.

    `- **<item>** — <note> · **<owner>**`   trailing bold after the last middot
    `- **<Name>:** <what they owe>`         a person's own line

    Anything else is UNOWNED -- and that is the point, not a formatting slip. An item
    with no owner is the one that falls through an agenda that lists it.
    """
    if (m := re.search(r"·\s*\*\*(.+?)\*\*\s*$", rest)):
        return m.group(1).strip()
    if label.endswith(":"):
        return label.rstrip(":")
    return "UNOWNED"


def key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", label.rstrip(":").lower())[:28]


def has_section(path: Path) -> bool:
    """An ABSENT section and an EMPTY one mean different things.

    Empty is a real answer -- nothing carried that day. Absent is indistinguishable
    from a note nobody finished, and it is the one failure in this loop that is
    otherwise silent: the next agenda generates with zero carried items and looks
    perfectly correct. So the absence is said out loud, here and in the agenda.
    """
    return SECTION.search(path.read_text(encoding="utf-8")) is not None


def carried(path: Path) -> list[tuple[str, str]]:
    m = SECTION.search(path.read_text(encoding="utf-8"))
    return [(a.strip(), b.strip(" —-:·")) for a, b in ITEM.findall(m.group(1))] if m else []


# How many sessions an item may be missing from and still be the same item. Beyond
# this it is treated as a fresh raise, because "carried in March, back in September"
# is a new problem wearing an old name.
MAX_GAP = 2


def streak(k: str, history: list[tuple[str, Path]]) -> tuple[int, int, str | None]:
    """How many sessions an item has survived, how many it skipped, and since when.

    Counts APPEARANCES, not consecutive ones. An earlier version broke on the first
    absence, so an item carried on the 16th, dropped from the 19th and carried again
    on the 21st read as brand new and its escalation clock restarted -- letting a
    genuinely stuck item hide indefinitely by skipping every third session.

    A note with no carry-forward section is skipped entirely rather than counted as
    an absence: that note says nothing about any item, and treating its silence as
    "resolved" is the same mistake in a different place.

    Returns (sessions, gaps, first_seen). Gaps are reported rather than hidden,
    because a gap has two readings that look identical from here -- a note that
    dropped the item by mistake, or an item someone resolved and later re-raised --
    and only a person can tell them apart.

    `first_seen` exists because **a session is not a unit of time.** Three sessions
    is three days on a daily standup and up to three months on a fortnightly one, so
    a session count alone escalates far too late on an irregular series -- which is
    exactly where items go missing.
    """
    seen = gaps = missing = 0
    first = None
    for date, p in reversed(history):
        if not has_section(p):
            continue
        if any(key(l) == k for l, _ in carried(p)):
            seen += 1
            gaps += missing
            missing = 0
            first = date
        else:
            missing += 1
            if missing > MAX_GAP:
                break
    return seen, gaps, first


# --- retrieval -------------------------------------------------------------
# Context the transcript does not carry. Both are BEST EFFORT: a failure prints a
# line and the agenda is still generated. An agenda that does not appear because a
# network call failed is worse than one without its context block.

def since(yymmdd: str) -> datetime.date:
    return datetime.datetime.strptime(yymmdd, "%y%m%d").date()


def from_chat(cf: dict, after: datetime.date) -> list[str]:
    """Messages posted to the series chat since the last note -- said in writing,
    never in the room, therefore absent from every transcript.

    `external_systems.chats` declares the chat by its PLATFORM ID. The archive
    (CR-047) stores `_chat.json` carrying that same id, so the folder is resolved by
    matching rather than by a second hand-written name that could drift.
    """
    chats = cf.get("ext", {}).get("chats") or []
    if not chats:
        return []
    c = next((x for x in chats if x.get("default")), chats[0])
    venture = next((p for p in cf["_root"].parents if (p / ".chats").is_dir()), None)
    if not venture:
        return ["no .chats/ archive found above this project"]
    d = next((f.parent for f in (venture / ".chats").glob("*/_chat.json")
              if json.loads(f.read_text(encoding="utf-8")).get("chat_id") == c.get("id")), None)
    if not d:
        return [f"declared chat not in the archive: {c.get('name')}"]
    out = []
    for f in sorted(d.glob("*.md")):
        if (m := re.search(r"(\d{4}-\d{2}-\d{2})\.md$", f.name)) and \
           datetime.date.fromisoformat(m.group(1)) >= after:
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.startswith("### "):
                    out.append(f"{m.group(1)} {line[4:].strip()}")
                elif out and line.strip() and not line.startswith(("#", "---", "[")):
                    if not out[-1].endswith(")"):
                        out[-1] += f" — {line.strip()[:120]}"
    return out


def from_repo(cf: dict, after: datetime.date) -> list[str]:
    """Issues that changed state since the last note, from the metadata archive.

    Reads `<venture>/.githubmeta/<slug>/` (CR-055) rather than calling a client:
    the archiver writes one snapshot per repository per day and already honours the
    declared `reads:` scope, which is recorded in `_repo.json`. Reading the archive
    keeps this symmetric with `from_chat` -- both consume what an archiver wrote,
    neither reaches the network -- and means an agenda generates with no credential
    and no connectivity.

    A snapshot is *a reading taken at a moment*, not an event log. If the newest one
    predates the last note, say so rather than presenting stale rows as news.
    """
    repos = cf.get("ext", {}).get("repos") or []
    if not repos:
        return []
    venture = next((p for p in cf["_root"].parents if (p / ".githubmeta").is_dir()), None)
    if not venture:
        return ["no .githubmeta/ archive found above this project"]

    declared = {re.sub(r"^(https?://)?(www\.)?github\.com/", "", r.get("url", "")).strip("/")
                for r in repos if r.get("url")}
    out = []
    for meta in sorted((venture / ".githubmeta").glob("*/_repo.json")):
        info = json.loads(meta.read_text(encoding="utf-8"))
        if info.get("repo") not in declared:
            continue
        if "issues" not in (info.get("reads") or []):
            out.append(f"{info['repo']}: issues not in declared reads — skipped")
            continue
        snaps = sorted(meta.parent.glob(f"{meta.parent.name}-*.json"))
        if not snaps:
            out.append(f"{info['repo']}: no snapshot in the archive")
            continue
        snap = json.loads(snaps[-1].read_text(encoding="utf-8"))
        taken = snap.get("day", "")
        if taken and datetime.date.fromisoformat(taken) < after:
            out.append(f"{info['repo']}: newest snapshot is {taken}, older than the last note — not refreshed")
            continue
        for i in snap.get("issues") or []:
            if datetime.date.fromisoformat(i["updatedAt"][:10]) >= after:
                who = ", ".join(a.get("login", "?") for a in i.get("assignees") or []) or "unassigned"
                out.append(f"{info['repo']}#{i['number']} [{i['state'].lower()}] {i['title']} — {who}")
    return out


DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def next_session(yymmdd: str, days: list[str] | None) -> str:
    """The next day this series actually meets.

    Not every standup is daily. A twice-weekly Monday/Thursday series generating a
    Tuesday agenda produces a file nobody opens, and the carry-forward chain then
    looks broken on Thursday because the Tuesday file is the newest thing with no
    note behind it. Falls back to the next weekday where no schedule is declared.
    """
    want = {DAYS.index(x.lower()) for x in (days or []) if x.lower() in DAYS}
    d = datetime.datetime.strptime(yymmdd, "%y%m%d").date() + datetime.timedelta(days=1)
    for _ in range(14):
        if (d.weekday() in want) if want else (d.weekday() <= 4):
            return d.strftime("%y%m%d")
        d += datetime.timedelta(days=1)
    return d.strftime("%y%m%d")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="the meetings folder")
    ap.add_argument("--date", help="YYMMDD; default is the next weekday after the last note")
    a = ap.parse_args()

    md = Path(a.dir).resolve()
    cf = config(md)
    # `*` in note_suffix becomes a wildcard. Real series are not uniform:
    # "coreteam-weekly-w38" carries a week number, "bi-weekly-Ann-Bo-Cai[-Dee]"
    # carries participants that change. An exact match finds none of them.
    pat = note_pattern(cf["note_suffix"])
    hist = sorted((m.group(1), p) for p in md.glob("*.md")
                  if (m := pat.match(p.name)) and not any(c in p.name for c in COMPANION))
    if not hist:
        sys.exit(f"no YYMMDD-{cf['note_suffix']}.md in {md}")

    last_date, last = hist[-1]
    target = a.date or next_session(last_date, cf.get("schedule_days"))
    day = datetime.datetime.strptime(target, "%y%m%d").date()
    today = datetime.datetime.strptime(target, "%y%m%d").date()

    def age(first: str | None) -> int:
        return 0 if not first else (today - datetime.datetime.strptime(first, "%y%m%d").date()).days

    items = sorted(((l, r, n, g, age(f)) for l, r in carried(last)
                    for n, g, f in [streak(key(l), hist)]),
                   key=lambda t: (-t[2], -t[4]))
    out = md / f"{target}-{cf['agenda_suffix']}.md"
    if out.exists():
        sys.exit(f"{out.name} exists -- delete it first if you mean to regenerate")

    E = cf["escalate_after"]
    ED = cf.get("escalate_after_days")
    L = [f"# {cf.get('title', md.parent.name)}",
         f"### {day.strftime('%A %-d %B')}" + (f" · {cf['time']}" if cf.get("time") else ""),
         "", "---", ""]

    if items:
        fresh = [i for i in items if i[2] <= 1]
        old = [i for i in items if i[2] > 1]
        L += ["## Carried forward — before anything else", "",
              f"From [{last.name}]({last.name}). **Every line needs a name said out loud, or it carries again.**", ""]
        if fresh and old:
            L += [f"**Owed into this session ({len(fresh)})** — raised last time, due now.", ""]
        L += ["| Item | Owner | Sessions · age |", "|---|---|---|"]
        for lab, rest, n, g, d in (fresh + old if fresh and old else items):
            if old and fresh and (lab, rest, n, g, d) == old[0]:
                L += ["", f"**Still carrying ({len(old)})** — open across more than one session.", "",
                      "| Item | Owner | Sessions · age |", "|---|---|---|"]
            hot = n >= E or (ED and d >= ED)
            mark = f"**{n}** ⚠" if hot else str(n)
            if d >= 7 or (ED and d >= ED):
                mark += f" · {d}d"
            if g:
                mark += f" · skipped {g}"
            L.append(f"| {lab.rstrip(':')} | {owner_of(lab, rest)} | {mark} |")
        L.append("")
        if any(g for _, _, _, g, _ in items):
            L += ["*\"skipped\" means the item was absent from a note that had a carry-forward section,"
                  " then returned. It still counts — but check whether it was dropped by mistake or"
                  " resolved and re-raised, because the two look identical from here.*", ""]
        stuck = [l.rstrip(":") for l, _, n, _, d in items if n >= E or (ED and d >= ED)]
        if stuck:
            L += [f"> ⚠ **{', '.join(stuck)}** — at or past {E} sessions, or carried more than {ED} days.",
                  "> An item that survives that long is not an agenda problem — it has no owner who is",
                  "> present, or it is not actually being asked for. **A session is not a unit of time:**",
                  f"> {E} sessions is three days on a daily series and two months on a fortnightly one,",
                  "> which is why the age counts too.",
                  "> **Decide today: give it a date and a name, or drop it.**", ""]
    elif has_section(last):
        L += ["## Carried forward", "", "*Nothing carried — the previous note says so explicitly.*", ""]
    else:
        L += ["## Carried forward — ⚠ CHAIN BROKEN", "",
              f"**[{last.name}]({last.name}) has no `## Carried forward` section**, so nothing could be",
              "carried into this agenda. That is not the same as nothing carrying: an absent section is",
              "indistinguishable from a note nobody finished.",
              "",
              "**Before the meeting:** add the section to that note — even if the honest content is",
              "*nothing carried* — and regenerate. Otherwise anything left open at the last session is",
              "now invisible to this one.", ""]

    after = since(last_date)
    chat, repo = from_chat(cf, after), from_repo(cf, after)
    if chat or repo:
        L += ["---", "", "## Since the last standup — not said in the room", "",
              "*Retrieved from the chat archive and the repo. Read before the round; most of it will not"
              " come up otherwise.*", ""]
        if chat:
            L += ["**In the chat**"] + [f"- {c}" for c in chat[:12]] + [""]
        if repo:
            L += ["**Issues that moved**"] + [f"- {r}" for r in repo[:15]] + [""]

    cols, people = cf.get("round_columns") or [], cf["people"]
    L += ["---", "", "## Round", ""]
    if cols:
        L.append(f"**Say your {cols[0].lower()} before anything else.**\n")
    L.append("**What moved · what you are blocked on and who owns the other end · what you need a decision on.**")
    if people:
        # A table is only worth its space when it has rows to hold.
        L += ["", "| | " + " | ".join(cols + [""]), "|---|" + "---|" * (len(cols) + 1)]
        L += [f"| **{n}** |" + " |" * (len(cols) + 1) for n in people]
    L += ["", "---", "", "## Close", "", "- Read-back: what the recap says",
          "- **Read-back: what carries to tomorrow, and whose name is on each.** An item read back",
          "  without a name is the one that will be here again", ""]

    out.write_text("\n".join(L), encoding="utf-8")
    if not has_section(last):
        print(f"  ⚠ {last.name} has no '## Carried forward' section — chain broken, nothing carried in")
    print(f"  {last.name} -> {out.name}  ({len(items)} carried"
          + (f", {len(stuck)} at {E}+ sessions" if items and stuck else "")
          + f"; {len(chat)} chat, {len(repo)} repo)")


if __name__ == "__main__":
    main()
