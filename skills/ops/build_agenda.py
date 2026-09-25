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
      - name: Other
        adjacent: true                    # on the project, not in the round

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


def external(start: Path) -> dict:
    """external_systems (CR-054, contract 16) resolved by the normal config chain:
    project `.claude/ops-config.yaml`, then `_ops.yaml`, WALKING UP from `start`.

    CR-076: this used to read only `start`'s own two files. `config()` calls it with
    the folder where `carry_forward` was found, so a project declaring the loop in its
    own config and its chats one level up (the venture) resolved to `{}` -- and the
    miss was silent, because an empty block renders as a section with nothing in it
    rather than as an error. Nearest declaration wins, same as every other key."""
    for root in (start, *start.parents):
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
            if not isinstance(cf, dict):
                cf = {"enabled": bool(cf)}
            if not cf:
                continue
            # Read the field, not the block (CR-067). A block written to DISABLE
            # carry-forward is a non-empty dict, so testing the block alone treats
            # "off" as "on" -- and `enabled: false` is the only way a project can
            # decline a carry_forward an org layer enabled above it.
            #
            # A disabled declaration STOPS resolution; it does not fall through.
            # Nearest declaration wins (see the docstring), and continuing the walk
            # would let a further-away "on" override a nearer "off" -- which is the
            # opt-out failing in the one direction it exists for. Defaults ON when
            # the key is absent: a block predating the flag must keep working.
            if not cf.get("enabled", True):
                return {"enabled": False, "_root": root}
            src = d.get("external_systems") or {}
            cf.setdefault("note_suffix", "daily-standup")
            cf.setdefault("agenda_suffix", "agenda-" + cf["note_suffix"])
            cf.setdefault("escalate_after", 3)
            cf.setdefault("escalate_after_days", 14)
            # `adjacent: true` means the person belongs to the project but not to the
            # daily round -- a name with a permanently empty row trains the room to
            # skip rows, and the round is the one place that must be read in full.
            # Keep the whole entry, not just the name: the round table's first column
            # is answerable from `areas`/`role`, and emitting it blank made the table
            # look unbuilt when the config had the answer all along.
            cf["people"] = [p_ for p_ in (d.get("people") or [])
                            if p_.get("name") and not p_.get("adjacent")]
            cf["ext"] = src or external(root)
            # The project's declared track axis (four permanent surfaces, one owner
            # each). Its presence is what makes the round's first column a STATED
            # axis rather than a looked-up attribute -- see the round table below.
            cf["tracks"] = [str(t) for t in (d.get("tracks") or []) if t]
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
    # An item with an owner but NO note loses its separator: carried() strips a
    # leading " —-:·", so `- **item** · **Bob**` arrives here as `**Bob**`
    # alone and the middot the pattern above needs is gone. Reading that as UNOWNED
    # silently converts owned items into the one class this whole mechanism exists
    # to surface -- the worst possible direction for the error to run.
    if (m := re.fullmatch(r"\s*\*\*(.+?)\*\*\s*", rest)):
        return m.group(1).strip()
    if label.endswith(":"):
        return label.rstrip(":")
    return "UNOWNED"


def item_of(label: str, rest: str) -> str:
    """What the item IS, which is not always the bold label.

    `- **<item>** — <note> · **<owner>**`   the label is the item
    `- **<Name>:** <what they owe>`         the label is the OWNER; the item is the rest

    Reading the label as the item in the second shape printed a row saying
    "Bob | Bob" and threw the three things they owed on the floor -- the agenda
    still looked complete, which is why it survived a session.
    """
    if label.endswith(":"):
        return rest.strip(" —-:·") or label.rstrip(":")
    return label.rstrip(":")


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


# ---- CR-088: the fetch record ------------------------------------------------
# A snapshot older than the note says the data is old; it cannot say WHY. Nothing
# may have happened, the fetch may not have run, or it may have failed on an
# expired login -- three states needing three responses, all printing as STALE.
# Each archive root carries a `_fetch.json` written by its fetcher. It is the one
# file in a dot-folder any tool may read: timestamps and a status, nothing from
# the source.
FETCH_RESULTS = ("ok", "partial", "auth_required", "error", "timeout")
FETCH_REASON = {"auth_required": "login required", "timeout": "timed out"}


def archive_dir(cf: dict, sub: str) -> Path | None:
    """`<venture>/<sub>` for the nearest venture above the project, as the readers resolve it."""
    return next((p / sub for p in cf["_root"].parents if (p / sub).is_dir()), None)


def fetch_record(archive: Path | None) -> dict | None:
    """The archive's `_fetch.json`, or None when there is none.

    An unreadable record is an error, not an absence: on a synced vault a file can
    be listed and still fail on open, and reporting that as "not recorded" would
    send a person looking for a fetch that did run. An unknown `result` reads as
    `error` -- a value nobody declared is more likely a failure than a success.
    """
    if archive is None:
        return None
    try:
        raw = (archive / "_fetch.json").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as e:
        return {"result": "error", "detail": f"_fetch.json unreadable ({type(e).__name__})"}
    try:
        rec = json.loads(raw)
    except ValueError:
        return {"result": "error", "detail": "_fetch.json unreadable (not JSON)"}
    if not isinstance(rec, dict):
        return {"result": "error", "detail": "_fetch.json unreadable (not an object)"}
    if rec.get("result") not in FETCH_RESULTS:
        rec = {**rec, "detail": f"unknown result {rec.get('result')!r}", "result": "error"}
    return rec


def _when(iso) -> datetime.datetime | None:
    try:
        return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _stamp(dt: datetime.datetime | None, today: datetime.date) -> str:
    if dt is None:
        return "?"
    return dt.strftime("%H:%M") if dt.date() == today else dt.strftime("%y%m%d %H:%M")


def fetch_ok(rec: dict | None) -> bool:
    return bool(rec) and rec.get("result") in ("ok", "partial")


def fetched_since(rec: dict | None, after: datetime.date) -> bool:
    """The last successful fetch is on or after the note's day: the archive is current
    even if it holds nothing newer, because a fetch that found nothing is an answer."""
    ok = _when((rec or {}).get("last_success"))
    return ok is not None and ok.date() >= after


def fetch_status(rec: dict | None, today: datetime.date | None = None) -> str:
    """One phrase for a sources line. Never empty: a missing record says so (CR-071)."""
    today = today or datetime.date.today()
    if rec is None:
        return "fetch not recorded"
    if fetch_ok(rec):
        when = _when(rec.get("last_success")) or _when(rec.get("last_attempt"))
        return f"fetched {_stamp(when, today)} {rec['result']}"
    reason = FETCH_REASON.get(rec.get("result")) or (rec.get("detail") or "error").splitlines()[0][:60]
    return f"fetch failed {_stamp(_when(rec.get('last_attempt')), today)}: {reason}"


def _chat_messages(d: Path, after: datetime.date) -> list[tuple[str, str]]:
    """(date, line) per message in one archived chat folder."""
    out: list[tuple[str, str]] = []
    for f in sorted(d.glob("*.md")):
        if not ((m := re.search(r"(\d{4}-\d{2}-\d{2})\.md$", f.name))
                and datetime.date.fromisoformat(m.group(1)) >= after):
            continue
        filled = True
        for line in f.read_text(encoding="utf-8").splitlines():
            # The archive keeps its own trailing sections (held-back boilerplate and
            # why it matched). They are provenance for the archive, not chat traffic.
            if line.startswith("## "):
                break
            if line.startswith("### "):
                out.append((m.group(1), f"{m.group(1)} {line[4:].strip()}"))
                filled = False
            elif not filled and line.strip() and not line.startswith(("#", "---", "[")):
                # One opening snippet per message. Concatenating every line flattens a
                # long post into an unreadable wall and buries the messages after it.
                out[-1] = (out[-1][0], out[-1][1] + f" \u2014 {line.strip()[:160]}")
                filled = True
    return out


def from_chat(cf: dict, after: datetime.date) -> list[dict]:
    """Messages posted to the series chats since the last note -- said in writing,
    never in the room, therefore absent from every transcript.

    `external_systems.chats` declares each chat by its PLATFORM ID. The archive
    (CR-047) stores `_chat.json` carrying that same id, so the folder is resolved by
    matching rather than by a second hand-written name that could drift.

    **Every declared chat is read (CR-071).** `default:` answers "where does this
    project POST?" -- one answer, and the dispatcher's. Reading asks "what was said
    anywhere that bears on this session?", which has no default: a project whose work
    runs across three chats and whose agenda quietly reads one produces a block that
    is complete-looking and partial.

    Returns one record per declared chat -- `{name, messages, problem}` -- so the
    caller can report per chat. A chat that cannot be resolved carries a `problem`
    and NO messages: a diagnostic counted as traffic is worse than no count at all.
    """
    chats = cf.get("ext", {}).get("chats") or []
    if not chats:
        return []
    venture = next((p for p in cf["_root"].parents if (p / ".teamschats").is_dir()), None)
    if not venture:
        return [{"name": None, "messages": [],
                 "problem": "no .teamschats/ archive found above this project"}]
    # One pass over the archive; declared ids are then looked up rather than the
    # archive re-globbed and re-parsed once per declared chat.
    byid = {}
    for f in (venture / ".teamschats").glob("*/_chat.json"):
        try:
            byid[json.loads(f.read_text(encoding="utf-8")).get("chat_id")] = f.parent
        except (OSError, ValueError):
            continue  # best effort: one unreadable _chat.json must not lose the rest
    out = []
    for c in chats:
        d = byid.get(c.get("id"))
        out.append({"name": c.get("name"),
                    "messages": _chat_messages(d, after) if d else [],
                    "problem": None if d else "declared chat not in the archive"})
    return out


def from_repo(cf: dict, after: datetime.date, rec: dict | None = None) -> list[str]:
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
        return [{"note": "no .githubmeta/ archive found above this project"}]

    declared = {re.sub(r"^(https?://)?(www\.)?github\.com/", "", r.get("url", "")).strip("/")
                for r in repos if r.get("url")}
    out = []
    for meta in sorted((venture / ".githubmeta").glob("*/_repo.json")):
        info = json.loads(meta.read_text(encoding="utf-8"))
        if info.get("repo") not in declared:
            continue
        if "issues" not in (info.get("reads") or []):
            out.append({"note": f"{info['repo']}: issues not in declared reads — skipped"})
            continue
        snaps = sorted(meta.parent.glob(f"{meta.parent.name}-*.json"))
        if not snaps:
            out.append({"note": f"{info['repo']}: no snapshot in the archive"})
            continue
        snap = json.loads(snaps[-1].read_text(encoding="utf-8"))
        taken = snap.get("day", "")
        if taken and datetime.date.fromisoformat(taken) < after:
            # CR-088: fetched since the note and still no newer snapshot means
            # nothing changed -- current, not stale.
            if fetch_ok(rec) and fetched_since(rec, after):
                continue
            out.append({"note": f"{info['repo']}: newest snapshot is {taken}, older than the last note — not refreshed"})
            continue
        for i in snap.get("issues") or []:
            if datetime.date.fromisoformat(i["updatedAt"][:10]) >= after:
                who = ", ".join(a.get("login", "?") for a in i.get("assignees") or []) or ""
                # Raising an issue IS movement. It arrives with updatedAt == createdAt,
                # so it is already in this list -- but reading as plain "open" it is
                # indistinguishable from a three-week-old issue someone relabelled.
                labs = [(l.get("name") if isinstance(l, dict) else str(l))
                        for l in (i.get("labels") or [])]
                areas = [l for l in labs if l and l.startswith("area:")]
                out.append({"repo": info["repo"], "n": i["number"], "title": i["title"],
                            "state": i["state"].lower(), "who": who,
                            "area": (areas[0][5:] if areas else "no area"),
                            "new": datetime.date.fromisoformat(i["createdAt"][:10]) >= after})
    return out


def from_jira(cf: dict, after: datetime.date, rec: dict | None = None) -> list[dict]:
    """Tickets from `<venture>/.jirameta/` (CR-074), the sibling of `.githubmeta/`.

    The archive has existed since CR-074 and nothing read it, so a project that
    tracks its work in a ticket system had that half of its status missing from
    every agenda -- silently, because an undeclared source and an empty one look
    identical on the page. Same contract as `from_repo`: read what an archiver
    wrote, honour the declared `reads:` scope, never reach the network.
    """
    boards = cf.get("ext", {}).get("jira") or []
    if isinstance(boards, dict):
        boards = [boards]
    if not boards:
        return []
    venture = next((p for p in cf["_root"].parents if (p / ".jirameta").is_dir()), None)
    if not venture:
        return [{"note": "no .jirameta/ archive found above this project"}]

    declared = {str(b.get("project") or b.get("key") or "").strip().upper()
                for b in boards if isinstance(b, dict)} - {""}
    out = []
    for meta in sorted((venture / ".jirameta").glob("*/_project.json")):
        try:
            info = json.loads(meta.read_text(encoding="utf-8"))
        except Exception as e:
            out.append({"note": f"{meta.parent.name}: archive unreadable ({type(e).__name__})"})
            continue
        key_ = str(info.get("project") or meta.parent.name).upper()
        if declared and key_ not in declared:
            continue
        reads = info.get("reads")
        if reads is not None and "issues" not in reads:
            out.append({"note": f"{key_}: issues not in declared reads — skipped"})
            continue
        snaps = sorted(meta.parent.glob(f"{meta.parent.name}-*.json"))
        if not snaps:
            out.append({"note": f"{key_}: no snapshot in the archive"})
            continue
        snap = json.loads(snaps[-1].read_text(encoding="utf-8"))
        taken = snap.get("day", "")
        if taken and datetime.date.fromisoformat(taken) < after:
            if fetch_ok(rec) and fetched_since(rec, after):   # CR-088, as in from_repo
                continue
            out.append({"note": f"{key_}: newest snapshot is {taken}, older than the last note — not refreshed"})
            continue
        for t in snap.get("issues") or []:
            upd = (t.get("updated") or t.get("updatedAt") or "")[:10]
            if not upd or datetime.date.fromisoformat(upd) < after:
                continue
            out.append({"board": key_, "n": t.get("key") or t.get("id"),
                        "title": t.get("summary") or t.get("title") or "",
                        "state": str(t.get("status") or "").lower(),
                        "who": t.get("assignee") or "",
                        "track": t.get("track") or t.get("component") or ""})
    return out


# Words a team actually uses when something is finished. Deliberately short: a
# long list matches more and means less, and every false positive here costs a
# person the time to say "no, still open" in the room.
DONE_WORDS = re.compile(r"\b(deployed|shipped|released|live|merged|fixed|resolved|done|closed|moved to)\b", re.I)


def probably_closed(items, chat, repo, jira):
    """Carried items the sources suggest are finished.

    Carry-forward is never compared with anything, so an item that shipped
    yesterday leads this morning's agenda and the room spends its first minutes
    saying so. This looks for evidence and separates those items -- it NEVER drops
    one. A human confirms in the room and the next note records the close: a
    machine that closes items silently is worse than one that repeats them.
    """
    ev = []
    for c in chat:
        for line in (c.get("messages") or []):
            txt = line[1] if isinstance(line, (tuple, list)) and len(line) > 1 else str(line)
            if DONE_WORDS.search(txt or ""):
                ev.append(("chat", c.get("name") or "chat", txt.strip()))
    for r in repo:
        if r.get("state") == "closed":
            ev.append(("repo", f"{r.get('repo','')}#{r.get('n','')}", r.get("title", "")))
    for t in jira:
        if any(w in (t.get("state") or "") for w in ("done", "closed", "resolved")):
            ev.append(("tickets", str(t.get("n") or ""), t.get("title", "")))
    if not ev:
        return [], items

    def words(x):
        return {w for w in re.findall(r"[a-zåäö0-9]{4,}", x.lower())}

    closed, still = [], []
    for label, rest in items:
        want = words(label)
        hit = next(((kind, ref, txt) for kind, ref, txt in ev
                    if want and len(want & words(f"{ref} {txt}")) >= 2), None)
        (closed.append((label, rest, hit)) if hit else still.append((label, rest)))
    return closed, still


def recorded_since(cf: dict, after: datetime.date, told: str | None) -> list[dict]:
    """Recordings of THIS series that are newer than the newest note (CR-087).

    A session that was recorded and never written up is invisible to everything
    the loop reads: notes, agendas, archives and the outbox all look healthy, and
    the next agenda is then built from a note that predates the session — silently
    skipping it, re-raising what it closed and carrying none of what it opened.

    **This never fetches.** Two sources only:

      1. `--recorded YYMMDD[,id...]`, passed by a caller that already looked
      2. a declared `external_systems.transcripts.archive`, written by an external
         archiver, read the way `.teamschats/` and `.githubmeta/` are read

    A guard that sometimes reached the network would cost the property that makes
    the offline path trustworthy: an agenda generates with no credential and no
    connectivity. That is worth more than the convenience.
    """
    if told:
        parts = [x.strip() for x in told.split(",") if x.strip()]
        day = parts[0] if parts and re.fullmatch(r"\d{6}", parts[0]) else ""
        if day and datetime.datetime.strptime(day, "%y%m%d").date() <= after:
            return []                      # told about something older than the note
        return [{"day": day or "?", "id": i} for i in (parts[1:] or ["(not identified)"])]

    tr = (cf.get("ext") or {}).get("transcripts") or {}
    arch = tr.get("archive")
    if not arch:
        return []
    root = cf["_root"]
    d = next((p / arch for p in (root, *root.parents) if (p / arch).is_dir()), None)
    if not d:
        return [{"note": f"declared transcript archive not found: {arch}"}]

    want = [m.lower() for m in (tr.get("match") or []) if m]
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue                        # one unreadable entry must not lose the rest
        for r in (rec if isinstance(rec, list) else [rec]):
            day = str(r.get("day") or r.get("date") or "")[:10].replace("-", "")[2:]
            if not re.fullmatch(r"\d{6}", day):
                continue
            if datetime.datetime.strptime(day, "%y%m%d").date() <= after:
                continue
            # `match` is what keeps this from becoming noise: a store holding every
            # meeting someone records would otherwise report all of them.
            hay = " ".join(str(r.get(k, "")) for k in ("title", "name", "series", "chat")).lower()
            if want and not any(m in hay for m in want):
                continue
            out.append({"day": day, "id": r.get("id") or r.get("document_id") or "?",
                        "title": r.get("title") or "", "duration": r.get("duration") or "",
                        "variant": r.get("variant") or ""})
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
    ap.add_argument("--recorded", metavar="YYMMDD[,id...]",
                    help="CR-087: a recording of this series the caller already found. "
                         "The script never fetches; this is how a session that has looked tells it")
    ap.add_argument("--skip-unprocessed", action="store_true",
                    help="CR-087: build anyway, over a session that was recorded and never written "
                         "up. Skipping is then a decision on the record, not an accident")
    a = ap.parse_args()

    md = Path(a.dir).resolve()
    cf = config(md)
    if not cf.get("enabled", True):
        sys.exit(f"carry-forward is disabled for {cf.get('_root', md)} — no agenda built")
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

    raw_items = carried(last)
    items = sorted(((l, r, n, g, age(f)) for l, r in raw_items
                    for n, g, f in [streak(key(l), hist)]),
                   key=lambda t: (-t[2], -t[4]))
    out = md / f"{target}-{cf['agenda_suffix']}.md"
    if out.exists():
        sys.exit(f"{out.name} exists -- delete it first if you mean to regenerate")

    E = cf["escalate_after"]
    ED = cf.get("escalate_after_days")

    # CR-084: read every declared source BEFORE the agenda is assembled, so the page
    # can state what it was built from and the carried items can be checked against it.
    after = since(last_date)
    recs = {sub: fetch_record(archive_dir(cf, sub))
            for sub in (".teamschats", ".githubmeta", ".jirameta")}   # CR-088
    chat = from_chat(cf, after)
    repo = from_repo(cf, after, recs[".githubmeta"])
    jira = from_jira(cf, after, recs[".jirameta"])

    # CR-087: a session that happened and left no note. Building over it produces an
    # agenda that looks complete and silently skips a session — re-raising what that
    # session closed and carrying none of what it opened. Stop, name the recording,
    # and make skipping an explicit choice.
    unprocessed = recorded_since(cf, after, a.recorded)
    if unprocessed and not a.skip_unprocessed:
        lines = ["", f"  A session appears to have been recorded after {last.name} and never written up:", ""]
        for r in unprocessed:
            if r.get("note"):
                lines.append(f"    {r['note']}")
            else:
                bits = [r.get("id", "?"), r.get("title", ""), r.get("duration", ""), r.get("variant", "")]
                lines.append(f"    {r['day']}  " + "  ".join(str(b) for b in bits if b))
        lines += ["",
                  "  Process it first — the next agenda is built from the newest note, so building now",
                  "  drops that session entirely.",
                  "",
                  "  Or pass --skip-unprocessed to build over it deliberately.", ""]
        sys.exit("\n".join(lines))

    # CR-084: an item that shipped yesterday should not lead this morning's agenda.
    # Separated, never dropped -- a human confirms in the room and the next note
    # records the close. Silent closing is worse than repetition.
    closed_hits, _still = probably_closed(raw_items, chat, repo, jira)
    closed_keys = {key(l) for l, _r, _h in closed_hits}
    items = [t for t in items if key(t[0]) not in closed_keys]

    L = [f"# {cf.get('title', md.parent.name)}",
         f"### {day.strftime('%A %-d %B')}" + (f" · {cf['time']}" if cf.get("time") else ""),
         "", "---", ""]

    # ---- CR-084: the sources block, first ------------------------------------
    # An agenda that looks complete and was built from stale or missing inputs is
    # the failure this block exists to make impossible. STALE and NOT DECLARED are
    # printed, never omitted: a missing source that announces itself is honest, a
    # silent one is indistinguishable from an empty result.
    built = datetime.datetime.now().strftime("%y%m%d %H:%M")
    src = [f"## Sources — built {built} from", "", "```"]
    src.append(f"  note      {last.name:44} read")

    # CR-088: every archive-backed line carries its fetch status, and STALE carries
    # the reason when the record gives one. A fetch that failed after the last good
    # one is what scheduled fetching makes the usual way a source goes stale.
    def stale_mark(rec) -> str:
        return "" if fetch_ok(rec) or fetched_since(rec, after) or rec is None \
            else f"STALE — {fetch_status(rec)}"

    declared_chats = (cf.get("ext") or {}).get("chats") or []
    if not declared_chats:
        src.append(f"  chat      {'—':44} NOT DECLARED")
    else:
        crec = recs[".teamschats"]
        for c in chat:
            n = len(c.get("messages") or [])
            if c.get("problem"):
                src.append(f"  chat      {(c.get('name') or '?')[:44]:44} NOT READ — {c['problem']}")
            else:
                msgs = c.get("messages") or []
                newest = max((m[0] for m in msgs), default="—")
                tail = stale_mark(crec) or fetch_status(crec)
                src.append(f"  chat      {(c.get('name') or '?')[:44]:44} newest {newest} · {n} since the note · {tail}")

    for kind, rows, declared, rec in (("repo", repo, (cf.get("ext") or {}).get("repos"), recs[".githubmeta"]),
                                      ("tickets", jira, (cf.get("ext") or {}).get("jira"), recs[".jirameta"])):
        if not declared:
            src.append(f"  {kind:9} {'—':44} NOT DECLARED")
            continue
        status = fetch_status(rec)
        notes = [r["note"] for r in rows if isinstance(r, dict) and r.get("note")]
        if notes:
            for n_ in notes:
                # A snapshot older than the note is the one that reads as fresh and is not.
                flag = f"STALE — {status}" if "older than the last note" in n_ else "NOT READ"
                src.append(f"  {kind:9} {n_[:44]:44} {flag}")
        else:
            src.append(f"  {kind:9} {'declared':44} read · {len([r for r in rows if not r.get('note')])} changed"
                       f" · {stale_mark(rec) or status}")
    src += ["```", ""]
    L += src

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
            L.append(f"| {item_of(lab, rest)} | {owner_of(lab, rest)} | {mark} |")
        L.append("")
        if any(g for _, _, _, g, _ in items):
            L += ["*\"skipped\" means the item was absent from a note that had a carry-forward section,"
                  " then returned. It still counts — but check whether it was dropped by mistake or"
                  " resolved and re-raised, because the two look identical from here.*", ""]
        stuck = [item_of(l, r) for l, r, n, _, d in items if n >= E or (ED and d >= ED)]
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

    # CR-084: printed after the carried block, before anything else the room does.
    if closed_hits:
        L += ["## Probably closed — confirm", "",
              "**The sources say these moved since the last note.** They are NOT dropped: a machine that",
              "closes items silently is worse than one that repeats them. Confirm in the room, and the",
              "next note records the close.", "",
              "| Item | Owner | Evidence |", "|---|---|---|"]
        for lab, rest, hit in closed_hits:
            kind, ref, txt = hit
            ev = f"{kind} · {ref}" + (f" — {txt[:70]}" if txt else "")
            L.append(f"| {item_of(lab, rest)} | {owner_of(lab, rest)} | {ev} |")
        L.append("")


    # The chat archive is deliberately NOT printed here. It is context for whoever
    # writes the agenda and the facilitator sheet -- raw message lines pasted into
    # a team-facing document are noise, and quoting a colleague's message back at
    # the room reads as surveillance rather than preparation. Retrieved, counted,
    # used; not reproduced.
    # CR-076: say when nothing was DECLARED, as distinct from declared-but-empty.
    # An undeclared block and a quiet week both render as no messages, and the one
    # that is a configuration miss is the one worth naming -- silently empty is how
    # this went unnoticed in the first place.
    if not (cf.get("ext") or {}).get("chats"):
        print("  no external_systems.chats declared in the config chain"
              " — nothing to retrieve (declare it, or ignore if intended)")
    total = sum(len(c["messages"]) for c in chat)
    if total:
        print(f"  {total} chat message(s) since {last_date} — read them for the"
              " facilitator sheet; they are not printed into the agenda")
        # Which chat to go and read. With one declared chat the name is noise; with
        # several, an undivided total does not say where the traffic was.
        if len([c for c in chat if c["messages"]]) > 1:
            for c in chat:
                if c["messages"]:
                    print(f"    {c['name']}: {len(c['messages'])}")
    # Problems print SEPARATELY and are never counted as messages. Folded into the
    # total they would report traffic that does not exist and hide the reason.
    for c in chat:
        if c["problem"]:
            print(f"  chat not read — {c['problem']}: {c['name'] or '(declared chats)'}")

    # What each person is carrying INTO this session, routed to their own row.
    # The chain already knows it -- it was being printed once at the top and then
    # dropped, so the round asked everyone the same empty question.
    # CR-084: what each person said their track was last session. The note's round
    # table records it on every line; the agenda then asked again from blank, which
    # is how a column the project asks for first came to be empty every morning.
    prior_track: dict[str, str] = {}
    try:
        for line in last.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip().strip("*") for c in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and cells[1] and not set(cells[0]) <= set("- "):
                if cells[0].lower() not in ("", "owed into today") and "---" not in cells[1]:
                    prior_track.setdefault(cells[0].lower(), re.sub(r"\s*\(carried\)\s*", "", cells[1]).strip())
    except OSError:
        pass  # best effort: an unreadable note must not stop the agenda

    owed: dict[str, list[tuple[str, int]]] = {}
    for lab, rest, n, _g, _d in items:
        who = owner_of(lab, rest)
        if who == "UNOWNED":
            continue
        for nm in re.split(r",|\band\b|·", who):
            if nm := nm.strip().strip("*"):
                owed.setdefault(nm.lower(), []).append((item_of(lab, rest), n))

    # A declared axis is STATED in the room, not looked up from the roster. Where
    # the config declares `tracks:`, the round's first column is that axis: the
    # legend is printed and the column stays empty, because which track a person
    # reports on changes per session and most participants own none of them.
    # Prefilling it from `areas` put non-track values under a "Track" header and
    # contradicted the instruction above the table -- worse than blank, because a
    # wrong prefilled answer teaches the wrong vocabulary.
    tracks = cf.get("tracks") or []
    cols, people = cf.get("round_columns") or [], cf["people"]
    L += ["---", "", "## Round", ""]
    # The legend below says this better when there is one; printing both repeats
    # the instruction and buries the values.
    if cols and not tracks:
        L.append(f"**Say your {cols[0].lower()} before anything else.**\n")
    if tracks:
        L.append("**Track before anything else.** "
                 + " · ".join(t[:1].upper() + t[1:] for t in tracks) + ". One per item, never two.\n")
    L.append("**What moved · what you are blocked on and who owns the other end · what you need a decision on.**")
    if people:
        # A table is only worth its space when it has rows to hold.
        # The header must carry the same cell count as the separator and the rows:
        # one for the name, one per configured column, one for the free text.
        head = [""] + cols + ["Owed into today"]
        L += ["", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for p_ in people:
            # CR-084: the track is HANDED ON, not re-answered. Yesterday's note
            # first, then the declared default. `areas` is never used for this --
            # an area is what someone works on, a track is the axis the round runs
            # along, and filling the column with areas is how it came to hold the
            # wrong thing. Marked `(carried)` so the room confirms in a word
            # instead of spending the first minutes restating what it already said.
            if tracks:
                first = ""
            elif cols:
                carried_track = prior_track.get(p_["name"].lower()) or next(
                    (prior_track[k.lower()] for k in (p_.get("aliases") or [])
                     if k.lower() in prior_track), None)
                if carried_track:
                    first = f"{carried_track} *(carried)*"
                else:
                    first = p_.get("track") or ""
            else:
                first = ""
            # Match aliases too: a note names whoever was spoken, which is not
            # always the roster's canonical spelling, and a silent miss here
            # empties the row rather than erroring.
            keys = [p_["name"]] + list(p_.get("aliases") or [])
            mine = [x for k in keys for x in owed.get(k.lower(), [])]
            seen, uniq = set(), []
            for t, n in mine:
                if t not in seen:
                    seen.add(t); uniq.append((t, n))
            due = " · ".join(t if n <= 1 else f"{t} (**{n}×**)" for t, n in uniq)
            cells = [f"**{p_['name']}**"] + ([first] + [""] * (len(cols) - 1) if cols else []) + [due]
            L.append("| " + " | ".join(cells) + " |")
        if (un := [item_of(l, r) for l, r, *_ in items if owner_of(l, r) == "UNOWNED"]):
            L += ["", f"**Nobody owes these: {', '.join(un)}.** They are on no row above, which is"
                  " why they keep carrying. Give each one a name in the round or take it off the list."]
    L += ["", "---", "", "## Close", "", "- Read-back: what the recap says",
          "- **Read-back: what carries to tomorrow, and whose name is on each.** An item read back",
          "  without a name is the one that will be here again", ""]

    if repo:
        notes = [r["note"] for r in repo if "note" in r]
        rows = [r for r in repo if "note" not in r]
        L += ["---", "", "## Appendix — what moved in the repo", ""]
        if notes:
            L += [f"- {n}" for n in notes] + [""]
        if rows:
            # A flat list of forty issues is not something anyone reads before a
            # standup. Two questions are worth answering -- WHERE did it move, and
            # WHAT has no name on it -- so the appendix answers those and stops.
            areas = sorted({r["area"] for r in rows})
            L += [f"**{len(rows)} issues moved since the last note.** Raising one counts as movement.", "",
                  "| Area | Opened | Closed | Other movement | No assignee |",
                  "|---|--:|--:|--:|--:|"]
            for ar in areas:
                g = [r for r in rows if r["area"] == ar]
                op = sum(1 for r in g if r["new"])
                cl = sum(1 for r in g if r["state"] == "closed")
                ot = len(g) - op - cl
                na = sum(1 for r in g if not r["who"])
                L.append(f"| {ar} | {op or ''} | {cl or ''} | {ot or ''} | "
                         + (f"**{na}**" if na else "") + " |")
            tot = (sum(1 for r in rows if r["new"]), sum(1 for r in rows if r["state"] == "closed"))
            nam = sum(1 for r in rows if not r["who"])
            L += [f"| **all** | **{tot[0]}** | **{tot[1]}** | "
                  f"**{len(rows) - tot[0] - tot[1]}** | **{nam}**|", ""]

            fresh = [r for r in rows if r["new"] and r["state"] != "closed"]
            if fresh:
                # Not simply "opened": one raised and closed inside the window is
                # in the Opened column but not here, and a reader who spots the
                # mismatch is right to distrust the whole table.
                L += [f"**Opened since the last note and still open ({len(fresh)})**", ""]
                for r in sorted(fresh, key=lambda r: -r["n"]):
                    L.append(f"- #{r['n']} {r['title'][:90]} — "
                             + (r["who"] or "**no assignee**"))
                L.append("")
            if nam:
                L += [f"*{nam} of the {len(rows)} carry no assignee. That is the same shape as an"
                      " unowned carry-forward line, in a second place.*", ""]

    out.write_text("\n".join(L), encoding="utf-8")

    # ---- the Teams post: same facts, a shape that survives being pasted --------
    # Markdown tables flatten into unreadable runs in a chat client, so the post
    # carries no table at all. It is not a summary of the agenda; it is the part
    # a participant needs in order to arrive prepared.
    T = [f"**{cf.get('title', md.parent.name)} — {day.strftime('%A %-d %B')}**"
         + (f"  ·  {cf['time']}" if cf.get("time") else ""), ""]
    if cf.get("purpose"):
        T += [cf["purpose"], ""]
    T += ["**Bring:** what moved · what you are blocked on and who owns the other end · what you"
          " need a decision on."
          + (f" Say your {cols[0].lower()} first." if cols else ""), ""]
    if owed:
        T += ["**Carried from the last session — every line needs a name said out loud:**"]
        for p_ in people:
            keys = [p_["name"]] + list(p_.get("aliases") or [])
            mine, seen = [], set()
            for k in keys:
                for t, _n in owed.get(k.lower(), []):
                    if t not in seen:
                        seen.add(t); mine.append(t)
            if mine:
                T.append(f"- **{p_['name']}:** " + " · ".join(mine))
        T.append("")
    if items:
        un2 = [item_of(l, r) for l, r, *_ in items if owner_of(l, r) == "UNOWNED"]
        if un2:
            T += [f"**Nobody owes these: {', '.join(un2)}.** They have been on the agenda without a"
                  " name; today they get one or come off.", ""]
    if repo and [r for r in repo if "note" not in r]:
        rws = [r for r in repo if "note" not in r]
        T += [f"**Repo since the last note:** {len(rws)} issues moved, "
              f"{sum(1 for r in rws if r['new'])} opened, "
              f"{sum(1 for r in rws if r['state'] == 'closed')} closed, "
              f"{sum(1 for r in rws if not r['who'])} with no assignee. Breakdown in the full agenda.", ""]
    T += [f"Full agenda: `{out.name}`"]
    post = md / f"{target}-teams-{cf['agenda_suffix']}.md"
    post.write_text("\n".join(T) + "\n", encoding="utf-8")
    if not has_section(last):
        print(f"  ⚠ {last.name} has no '## Carried forward' section — chain broken, nothing carried in")
    print(f"  {last.name} -> {out.name}  ({len(items)} carried"
          + (f", {len(stuck)} at {E}+ sessions" if items and stuck else "")
          + f"; {len(chat)} chat, {len(repo)} repo)")


if __name__ == "__main__":
    main()
