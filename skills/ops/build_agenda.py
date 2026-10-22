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
          balance_window: 1                 # CR-090: sessions counted in the track balance line
          meets: [mon, tue, wed, thu, fri]  # CR-139: alias for schedule_days
          skip_dates:                       # CR-139: days this series did not meet
            - date: 261020
              reason: holiday-in
            - from: 261224
              to: 261226
              reason: leave
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
# "bi-weekly-*" swallows "bi-weekly-preparation-...". /ops check skips the same set.
COMPANION = ("-agenda", "agenda-", "-preparation", "preparation-", "-förberedelse",
             "förberedelse-", "-priorities", "priorities-", "-facilitator",
             "facilitator-", "-appendix", "-recap", "-mejl", "-teams")
ITEM = re.compile(r"^-\s+(?:\[[a-z]+\]\s+)?\*\*(.+?)\*\*(.*)$", re.M)
# CR-107: a carried line may open with its kind -- `- [blocker] **item** — note · **owner**`.
# The kind decides where the item goes in a card-layout agenda; an untagged line is a task.
KIND_RE = re.compile(r"^-\s+\[([a-z]+)\]\s+\*\*(.+?)\*\*", re.M)
KINDS = ("blocker", "dependency", "decision")

# CR-148: the declared layouts. `list` is the default and the reading of anything
# unknown, which is what `cf.get("layout") == "card"` did before there was a third
# value. The predicates below replace that scattered comparison: `compact` is a card
# VARIANT -- it redistributes sections the card already computes and computes nothing
# of its own -- so every place that asked "does this project get the card's data
# discipline?" must answer yes for it, and `is_card` is the one place that says so.
LAYOUTS = ("list", "card", "compact")


def layout_of(cf: dict) -> str:
    """CR-148: the declared layout, with an unknown value reading as `list`."""
    lay = cf.get("layout")
    return lay if lay in LAYOUTS else "list"


def is_card(cf: dict) -> bool:
    """CR-148: whether this project gets the card's DATA rules (CR-147, CR-142).

    `compact` inherits them deliberately. What it does NOT inherit is the card's TEXT
    -- the headings, the lead line, the markdown post -- which is `section_plan()`'s.
    A heading decided by `is_card` is this mechanism's one way of going wrong.
    """
    return layout_of(cf) in ("card", "compact")


def is_compact(cf: dict) -> bool:
    """CR-148: the four-output layout -- post, agenda, facilitator document, details."""
    return layout_of(cf) == "compact"


# The config file pair, nearest-first within one folder: a project's own config, then a
# folder-level one. Named once so a reader that walks the chain itself (`hygiene_check`)
# cannot drift from the order `config()` resolves -- the two disagreeing would mean a key
# the agenda reads from one file and the lint reads from another.
CONFIG_FILES = (Path(".claude") / "ops-config.yaml", Path("_ops.yaml"))


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
            # CR-101: where the roster WOULD be declared, and who a schedule names.
            # The participants key describes a schedule, not a round order, so it is
            # only ever named in the no-roster message -- never used to fill rows.
            cf["_config_file"] = p
            cf["_participants"] = participants_of(d.get("meeting_types"))
            cf["ext"] = src or external(root)
            # The project's declared track axis (four permanent surfaces, one owner
            # each). Its presence is what makes the round's first column a STATED
            # axis rather than a looked-up attribute -- see the round table below.
            cf["tracks"] = [str(t) for t in (d.get("tracks") or []) if t]
            # CR-107: the date the card runs toward. Project-wide, so it sits beside
            # `tracks:` rather than inside carry_forward; a nearer declaration wins.
            cf["milestone"] = d.get("milestone") or cf.get("milestone")
            # CR-149: the dates that matter are more than one. `milestones:` is the list;
            # `milestone:` stays readable as a list of one, so a config that declares only
            # it behaves exactly as before. Merged the same way -- nearest wins -- and
            # resolved for every reader by `milestones()`, never read raw.
            cf["milestones"] = d.get("milestones") or cf.get("milestones")
            cf["definitions"] = d.get("definitions") or cf.get("definitions")   # CR-118
            # CR-150: the owner-only document where work counted per person is allowed to
            # live. Merged like the keys above -- nearest declaration wins -- and read for
            # one purpose only: to know which path the lint must leave alone. The generator
            # NEVER writes to it and never links it from a team-facing file, which is why
            # there is no renderer anywhere that takes this value.
            cf["metrics_document"] = d.get("metrics_document") or cf.get("metrics_document")
            # CR-139: `meets:` is an ALIAS for `schedule_days`, not a second key. The
            # two would answer the same question -- which days this series meets --
            # and a config declaring both would have no defined winner, so the reader
            # resolves one list and `schedule_days` keeps precedence: a config that
            # already declares it behaves exactly as before.
            if not cf.get("schedule_days") and cf.get("meets"):
                cf["schedule_days"] = cf["meets"]
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


def participants_of(meeting_types) -> list[str]:
    """Names under `meeting_types.<type>.participants` (CR-101), in order, deduplicated.

    Accepts strings or `{name: ...}` entries. Used only to name who a schedule lists
    when the round has no `people:` roster -- never to populate the round.
    """
    names: list[str] = []
    for m in (meeting_types or {}).values() if isinstance(meeting_types, dict) else []:
        if not isinstance(m, dict):
            continue
        for p_ in m.get("participants") or []:
            n = p_.get("name") if isinstance(p_, dict) else str(p_)
            if n and n not in names:
                names.append(n)
    return names


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


def definitions(cf: dict) -> dict:
    """CR-118: the two levels of definitions a project works under.

    `definitions:` -- the project's own file (beside `carry_forward`, relative to the project root).
    `standards:`   -- the organisation's standards folder, from the nearest config further up that
                      declares it (relative to that config's folder). Its README is the index.

    Returns {"definitions": Path|None, "standards": Path|None, "local": n, "upward": n, "unmarked": n}.
    Counting reads the definitions file's status words; it never decides anything.
    """
    root = Path(cf["_root"])
    out = {"definitions": None, "standards": None, "local": 0, "upward": 0, "unmarked": 0}
    if cf.get("definitions"):
        f = root / cf["definitions"]
        out["definitions"] = f if f.exists() else None
    for d in (root, *root.parents):
        for name in (Path(".claude") / "ops-config.yaml", Path("_ops.yaml")):
            p = d / name
            if p.exists():
                try:
                    y = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                except Exception:
                    continue
                if y.get("standards") and out["standards"] is None:
                    sp = (p.parent if name.name == "_ops.yaml" else p.parent.parent) / y["standards"]
                    out["standards"] = sp if sp.exists() else None
    if out["definitions"]:
        # Only tables whose header has a Status column carry statuses; other tables in
        # the file (examples, role matrices) are not term registers.
        col, in_table = None, False
        for ln in out["definitions"].read_text(encoding="utf-8").splitlines():
            if not ln.startswith("|"):
                col, in_table = None, False
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if not in_table:
                in_table = True
                col = next((i for i, c in enumerate(cells) if c.lower().strip("* ") == "status"), None)
                continue
            if col is None or set(ln.replace("|", "").strip()) <= set("-: "):
                continue
            st = cells[col].lower() if col < len(cells) else ""
            if "proposed" in st:
                out["upward"] += 1
            elif "local" in st:
                out["local"] += 1
            else:
                out["unmarked"] += 1
    return out


def kinds(path: Path) -> dict[str, str]:
    """CR-107: key(label) -> declared kind, for lines that carry one. Unknown kinds are
    kept as written so /ops check can name them; only KINDS are routed to the card."""
    m = SECTION.search(path.read_text(encoding="utf-8"))
    return {key(lab): k for k, lab in KIND_RE.findall(m.group(1))} if m else {}


def details_name(cf: dict, target: str) -> str:
    """CR-107: the card layout's companion file. `agenda-x` -> `agenda-details-x`."""
    a = cf["agenda_suffix"]
    return f"{target}-" + (a.replace("agenda-", "agenda-details-", 1) if a.startswith("agenda-") else a + "-details") + ".md"


def facilitator_name(cf: dict, target: str) -> str:
    """CR-148: the compact layout's facilitator document. `agenda-x` -> `agenda-facilitator-x`.

    Derived exactly as `details_name` is, so a project that renames its agenda suffix
    gets both companions renamed with it and does not have to declare either.
    `compact.facilitator_suffix` overrides the whole name where a project needs to.
    """
    over = ((cf.get("compact") or {}) if isinstance(cf.get("compact"), dict) else {}).get("facilitator_suffix")
    if over:
        return f"{target}-{over}.md"
    a = cf["agenda_suffix"]
    return f"{target}-" + (a.replace("agenda-", "agenda-facilitator-", 1)
                           if a.startswith("agenda-") else a + "-facilitator") + ".md"


# CR-121/CR-148: a section is an id. Its title, its lead line and the kind it draws
# from are DATA, so one key can drop a section (CR-121's `release_blockers: false`)
# and one key can move it between outputs (CR-148's `layout: compact`) -- neither
# needs a branch inside a renderer. The strings here were MOVED out of the card
# renderer unchanged, which is what keeps the default card byte-identical.
#
# `blockers` and `release_blockers` are two ids over the SAME kind: that is how
# CR-121 changes a heading and a lead with no conditional in the renderer.
SECTIONS: dict[str, dict] = {
    "milestone":        {"title": "Milestone"},
    "movement":         {"title": "Movement"},
    "release_blockers": {"title": "Release blockers", "kind": "blocker",
                         "lead": "**What blocks the release, who owns it, the plan.**",
                         "col": "Stuck for"},
    "blockers":         {"title": "Blockers", "kind": "blocker",
                         "lead": "**What is stuck, who owns it, the plan.**",
                         "col": "Stuck for"},
    "dependencies":     {"title": "Dependencies", "kind": "dependency",
                         "lead": "**A person waiting on another person, or on someone"
                                 " outside the room.**",
                         "col": "Waiting"},
    "decisions":        {"title": "Decisions needed today", "kind": "decision",
                         "lead": "**Each one leaves the room decided, or with a date.**",
                         "col": "Open for"},
    # CR-114: the carried blockers that the repo's gap label does not name. A second
    # heading under the repo table, and an id here for the same reason as the rest.
    "other_blockers":   {"title": "Other blockers carried", "kind": "blocker",
                         "lead": "**Carried as blockers; not labelled in the repo.**",
                         "col": "Stuck for"},
    "demo":             {"title": "Demo"},          # CR-121
    "confirm": {}, "stuck": {}, "round": {}, "close": {},
}
# CR-121: how the post labels the carried sections it carries inline. Kept beside
# SECTIONS so one id names one thing in both renderers.
POST_LABELS = {"release_blockers": "Blockers", "blockers": "Blockers",
               "dependencies": "Waiting on", "decisions": "Decide today"}


def demo_on(cf: dict, day: datetime.date) -> dict | None:
    """CR-121: the milestone being demonstrated TODAY, or None.

    Read off the first entry whose `kind:` is `demo` and whose date is the generated
    day. Any other day, or any other kind, and the card is unchanged -- which is the
    whole of CR-121's "on the milestone's own date".
    """
    for e in milestones(cf):
        if str(e.get("kind") or "").strip().lower() == "demo" and e["_date"] == day:
            return e
    return None


def section_plan(cf: dict, day: datetime.date) -> dict[str, list[str]]:
    """CR-121, CR-148: which sections each output carries, in order.

    The ONLY place a layout or a `card:` key decides a section's presence or its
    position. A renderer loops the list it is given and never asks what layout it is
    in: that split is what keeps `is_card()` about data and this function about text.
    """
    card = cf.get("card") if isinstance(cf.get("card"), dict) else {}
    rel = (card or {}).get("release_blockers", True)      # CR-121: default True
    blockers = "release_blockers" if rel else "blockers"
    plan = ({"agenda":      ["decisions", "confirm", "round"],
             "post":        ["milestone", blockers],
             "facilitator": ["dependencies", "movement", "stuck"],
             "details":     ["all"]} if is_compact(cf) else
            {"agenda": ["milestone", "movement", blockers, "dependencies",
                        "decisions", "confirm", "stuck", "round", "close"],
             "post":   ["milestone", "movement", blockers, "dependencies", "decisions", "round"],
             "facilitator": [],                   # the card writes none
             "details": ["all"]})
    # CR-121: the Demo section sits directly under the milestone, in the agenda and in
    # the post. Inserted HERE rather than in two renderers, so "on its own date" is
    # stated once.
    #
    # CR-121 vs CR-148, a real conflict, resolved in favour of CR-148 and stated here
    # so the operator can overrule it with one line: CR-121 puts Demo "directly under
    # the milestone", and the COMPACT agenda carries no milestone to put it under --
    # CR-148 says that agenda is the decisions and the round, "Nothing else." Putting
    # Demo at index 0 instead would make the compact agenda three sections on demo day
    # and quietly repeal the layout the project opted into. So compact keeps Demo in
    # the POST only, which is also where CR-121 itself says the demo list goes ("the
    # Teams post carries the demo list in place of the blockers line"). To reverse it,
    # drop the `is_compact` guard: the renderer and the lead line need no change.
    if demo_on(cf, day):
        for out in ("agenda", "post"):
            if out == "agenda" and is_compact(cf):
                continue
            if "milestone" in plan[out]:
                plan[out].insert(plan[out].index("milestone") + 1, "demo")
            else:
                plan[out].insert(0, "demo")
    return plan


def lead_line(cf: dict, plan: dict[str, list[str]], day: datetime.date) -> str:
    """The agenda's italic lead: what the room is being asked to do today.

    CR-107 wrote one sentence inline. CR-121 gives it two more readings -- a project
    with no releases should not be asked to confirm release blockers, and on a demo
    day the content IS what is shown -- so the sentence is chosen from the plan, which
    is the thing that already knows both.
    """
    if demo_on(cf, day):      # CR-121
        return ("*Demo day: the people who raised the ideas show them; then what we wait on,"
                " and one minute each. Five to ten minutes when nothing blocks; statistics"
                " are read offline.*\n")
    # CR-121 + CR-148, DELIBERATE: the compact agenda never carries a blockers section
    # of either id (CR-148: it is the decisions and the round, "Nothing else"), so the
    # test below would always read as "no release" there -- and that is the wanted
    # reading, not an accident of the plan's contents. Under compact the blockers live
    # in the post, so asking the room in the AGENDA to confirm a list it cannot see
    # would be wrong whatever `card.release_blockers` says. The key still governs the
    # post's blockers heading; it is inert for the compact lead on purpose.
    if is_compact(cf) or "release_blockers" not in plan["agenda"]:   # CR-121: `release_blockers: false`
        return ("*Raise what you wait on, then one minute each. Five to ten minutes when"
                " nothing blocks; statistics are read offline.*\n")
    return ("*Confirm the release blockers and their plan, raise what you wait on, then one minute each. "
            "Five to ten minutes when nothing blocks; statistics are read offline.*\n")


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


# CR-145, proposal 1: the kinds a declared chat may be. `group` is the only kind that
# existed before, so it is the default and an entry declaring nothing keeps behaving
# exactly as it did. `direct` is a one-to-one conversation with ONE person.
#
# Why it exists, measured: an operator sent four one-to-one questions after a meeting,
# to the people who owed the answers. The archive reads only declared group chats, so
# the replies were invisible to everything downstream and the operator relayed them by
# hand -- the one job this loop exists to remove. The answers were later found, by luck,
# in the project chat where the people had also posted them.
CHAT_KINDS = ("group", "direct")
CHAT_DEFAULT_KIND = "group"


def chat_kind(entry: dict) -> str:
    """The declared kind of one `chats:` entry, or `group` (CR-145, proposal 1).

    An unknown value reads as `group`: a kind nobody implemented must not quietly turn a
    declared chat into an unread one, and `config_checks` reports the bad value instead.
    """
    k = str((entry or {}).get("kind") or "").strip().lower()
    return k if k in CHAT_KINDS else CHAT_DEFAULT_KIND


def chat_person(cf: dict, entry: dict) -> str | None:
    """The roster name a `kind: direct` chat is with, as the roster spells it, or None.

    Resolution is `roster_entries`/`keys_of` -- CR-143's resolver, shared with the pronoun
    check and the per-person lint -- so a declared `person: Bob` resolves
    through name, alias or first name exactly as every other roster reader in this module
    does. A second resolver here would eventually disagree with that one about who a name
    belongs to, which is the drift this repo warns about.

    A `person:` no roster answers to returns None and keeps its declared spelling at the
    call site: the chat is still READ -- the archive does not care what the config calls
    the person -- and the unresolved name is a config finding, not a dropped source.
    """
    want = str((entry or {}).get("person") or "").strip().lower()
    if not want:
        return None
    for p_, keys in roster_entries(cf):
        if want in keys:
            return str(p_.get("name") or "").strip() or None
    return None


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

    **A `kind: direct` entry is read the same way (CR-145, proposal 1)** -- same archive,
    same id match, same message reader. Direct messages are chat traffic; the only thing
    the kind changes is what the output CALLS the source, so a reader can tell a reply
    owed by one person from a post to the room. Nothing here is conditional on the kind,
    deliberately: a second reading path for direct messages is a second place for a
    source to go quietly unread.

    Returns one record per declared chat -- `{name, kind, person, messages, problem}` --
    so the caller can report per chat. A chat that cannot be resolved carries a `problem`
    and NO messages: a diagnostic counted as traffic is worse than no count at all.
    """
    chats = cf.get("ext", {}).get("chats") or []
    if not chats:
        return []

    def rec_for(c, messages, problem):
        """One record. `person` is the roster's spelling where the roster answers to the
        declared one, and the declared spelling otherwise -- never dropped, because a
        name the roster does not hold is still the only thing that says whose reply this
        is."""
        kind = chat_kind(c)
        who = (chat_person(cf, c) or str(c.get("person") or "").strip() or None) \
            if kind == "direct" else None
        return {"name": c.get("name"), "kind": kind, "person": who,
                "messages": messages, "problem": problem}

    venture = next((p for p in cf["_root"].parents if (p / ".teamschats").is_dir()), None)
    if not venture:
        return [{"name": None, "kind": CHAT_DEFAULT_KIND, "person": None, "messages": [],
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
        out.append(rec_for(c, _chat_messages(d, after) if d else [],
                           None if d else "declared chat not in the archive"))
    return out


def chat_label(c: dict) -> str:
    """What the output calls one chat record (CR-145, proposal 1).

    A group chat is its declared name, as it always was. A direct chat is named for the
    PERSON, because that is the fact a reader needs: the four invisible replies were owed
    by four named people, and *direct: Ravi* says whose answer arrived where a platform
    conversation id says nothing. The declared name is the fallback for a direct entry
    that names no person -- an unlabelled source is worse than an imperfectly named one.
    """
    if c.get("kind") == "direct":
        return "direct: " + str(c.get("person") or c.get("name") or "?")
    return str(c.get("name") or "?")


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
        reads = info.get("reads") or []
        # CR-101: pull requests are read when `pulls` is declared. A repository that
        # tracks its work in a separate ticket system keeps its movement in PRs, and
        # the early return on "no issues" made its appendix permanently empty while
        # the archive held the pulls. The skip note now means neither is declared.
        if "issues" not in reads and "pulls" not in reads:
            out.append({"note": f"{info['repo']}: neither issues nor pulls in declared reads — skipped"})
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
        if "pulls" in reads:
            out += pulls_since(info["repo"], snap.get("pulls") or [], after)
        if "releases" in reads:
            for r in snap.get("releases") or []:
                pub = (r.get("publishedAt") or r.get("createdAt") or "")
                if pub and not r.get("isDraft") and datetime.date.fromisoformat(pub[:10]) >= after:
                    name = r.get("name") or r.get("tagName") or ""
                    # CR-141: a release names what it shipped in its NOTES, so the ids
                    # are read here, where the archived notes are, under either
                    # archiver name. Without this the notes never reached the matcher.
                    notes = str(r.get("body") or r.get("description") or "")
                    out.append({"kind": "release", "repo": info["repo"],
                                "n": r.get("tagName") or r.get("name") or "",
                                "title": name, "when": pub,
                                "names": sorted(identifiers(name) | identifiers(notes))})
        if "issues" not in reads:
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
                out.append({"kind": "issue", "repo": info["repo"], "n": i["number"], "title": i["title"],
                            "state": i["state"].lower(), "who": who, "when": i.get("closedAt") or i["updatedAt"],
                            "area": (areas[0][5:] if areas else "no area"),
                            "new": datetime.date.fromisoformat(i["createdAt"][:10]) >= after})
    return out


def pulls_since(repo: str, pulls: list[dict], after: datetime.date,
                today: datetime.date | None = None) -> list[dict]:
    """Pull requests that moved since the last note (CR-101), one row each.

    `status` is one of `merged`, `closed` (closed unmerged), `awaiting review`
    (open, not a draft, no approval yet) or `open` (other open ones, drafts
    included). `age` is days since the PR was opened -- the question for one
    awaiting review is how long it has waited.

    CR-141: `closes` carries the ids the PR SAYS it closes, read HERE, where the
    archived record still is -- from the title and from the description under
    whichever name the archiver stored it (`body` is `gh`'s field, `bodyText` the
    GraphQL plain-text one). The row handed on is a fixed shape, so a closing
    reference that lives only in the description had no way through it before and
    `Fixes #12` in a PR body never matched anything. An archive that stores no
    description matches on the title, which is always present; `closes` is then an
    empty set and the marker falls back to the PR's own number.
    """
    today = today or datetime.date.today()
    out = []
    for pr in pulls:
        upd = (pr.get("updatedAt") or pr.get("createdAt") or "")[:10]
        if not upd or datetime.date.fromisoformat(upd) < after:
            continue
        state = str(pr.get("state") or "").lower()
        if pr.get("mergedAt"):
            status, when = "merged", pr["mergedAt"]
        elif state == "closed":
            status, when = "closed", pr.get("closedAt") or pr.get("updatedAt")
        elif not pr.get("isDraft") and str(pr.get("reviewDecision") or "").upper() != "APPROVED":
            status, when = "awaiting review", pr.get("updatedAt")
        else:
            status, when = "open", pr.get("updatedAt")
        created = (pr.get("createdAt") or "")[:10]
        age = (today - datetime.date.fromisoformat(created)).days if created else 0
        who = (pr.get("author") or {}).get("login", "") if isinstance(pr.get("author"), dict) else ""
        title = pr.get("title") or ""
        # CR-141: read the closing references off the archived record while it is in
        # hand -- the title plus the description under either archiver name.
        closes = closing_refs(title) | closing_refs(str(pr.get("body") or pr.get("bodyText") or ""))
        out.append({"kind": "pull", "repo": repo, "n": pr.get("number"), "title": title,
                    "status": status, "when": when or "", "age": age, "who": who,
                    "closes": sorted(closes),
                    "new": bool(created) and datetime.date.fromisoformat(created) >= after})
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
                        # CR-147: a close has to state WHEN, and the archive already
                        # holds it -- the row simply dropped it on the way through.
                        "updated": t.get("updated") or t.get("updatedAt") or "",
                        "track": t.get("track") or t.get("component") or ""})
    return out


# Words a team actually uses when something is finished. Deliberately short: a
# long list matches more and means less, and every false positive here costs a
# person the time to say "no, still open" in the room.
DONE_WORDS = re.compile(r"\b(deployed|shipped|released|live|merged|fixed|resolved|done|closed|moved to)\b", re.I)


# CR-101: a done-word is evidence of a CLAIM, not of a state. "I have fixed and
# raised a PR" claims an attempt; the next day's "not solved after my fix" is the
# state. These words make a message counter-evidence.
NEGATIVE_WORDS = re.compile(r"\b(failing|fails|failed|not solved|not fixed|not working|broken|reverted|still)\b", re.I)

_CHAT_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?")


def _chat_when(txt: str) -> str:
    """`YYYY-MM-DD HH:MM` from an archived chat line, or the date alone."""
    m = _CHAT_STAMP.match(txt or "")
    return f"{m.group(1)} {m.group(2)}".strip() if m and m.group(2) else (m.group(1) if m else "")


# ---- CR-141: identifiers, the only thing the closed matcher matches on ------
# The matcher used to compare word sets: two shared 4+-letter words between the
# carried line and an evidence string made a hit. Measured over three mornings on
# one project it was right 0 of 9, 2 of 5 and 1 of 7 times -- the evidence string
# always carries the repository name and the ticket prefix, so a *checkout* fix
# matched a carried payments line on the two words they happened to share. A
# marker that is wrong most of the time is removed by hand every morning, which is
# the work the generator exists to save. So: an explicit identifier, or nothing.

# `#12`, but not a colour (`#fff`) and not the `#` of a heading.
_ID_HASH = re.compile(r"(?<![\w#])#(\d{1,6})\b")
# `TICK-9`, `ABC-1234`. The prefix is 2+ characters, upper-case and starting with a
# letter, so a hyphenated word (`re-run`) and a date (`2026-09-24`) are not read as
# ticket keys. Upper-case is the board's own convention and keeping it that way is
# what stops ordinary prose turning into an identifier.
_ID_TICKET = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-(\d{1,6})\b")
# A range of ticket keys: `TICK-9..12`, `TICK-9-12`, `TICK-9–12` (en dash) and the
# fully written `TICK-9..TICK-12`. A note writes one of these for a batch of work
# and means every key in it, so each is extracted.
#
# CR-141: the separator takes NO surrounding whitespace. A spaced dash is prose --
# and ` — ` is this file's own separator, on nearly every carried line -- so allowing
# one made `Q3-2026 - Q3-2030 roadmap` yield five keys and `ISO-8601 - ISO-8609
# encoding` nine, inventing identifiers nobody wrote. That is the over-matching this
# CR exists to remove, re-entering through the range feature. A written range is
# tight (`TICK-9..12`), so requiring tight costs nothing real and the two prose lines
# above now yield only the literal keys they contain.
_ID_TICKET_RANGE = re.compile(
    r"\b([A-Z][A-Z0-9]{1,9})-(\d{1,6})(?:\.\.|[–—-])(?:\1-)?(\d{1,6})\b")
# A pull request naming the issue it closes. GitHub's own closing keywords plus the
# `Re #id` a team writes by hand.
_ID_CLOSES = re.compile(r"\b(?:re|fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s*:?\s*#(\d{1,6})\b", re.I)

# How many keys a written range may expand to. A typo (`TICK-9..99999`) otherwise
# expands to a set that matches every ticket on the board, which is the old
# everything-matches failure in a new costume.
MAX_RANGE = 50


def identifiers(text: str) -> set[str]:
    """Explicit identifiers named in a line: `#12` -> `#12`, `TICK-9` -> `TICK-9`.

    The one place CR-141's "match only on an explicit identifier" is decided, and
    deliberately reusable: CR-147 acts on certain closes and needs the same answer
    to "which work does this line name?" that the marker was based on.

    Recognised, in the carried line, a chat message, a pull request title or a
    commit body alike:

      - `#12`                       an issue or pull request number
      - `TICK-9`                    a ticket key
      - `TICK-9..12`, `TICK-9-12`   a written range, expanded to every key in it
      - `Fixes #12`, `Re #12`       a closing reference (also yielded as `#12`)

    Case is kept for ticket keys (they are upper by convention and compared as
    written) and the hash form has no case. Returns a set, so a line that names the
    same id twice counts once. Never guesses: prose with no identifier returns an
    empty set, and the caller then says nothing rather than something wrong.
    """
    out: set[str] = set()
    t = text or ""
    for pre, a, b in _ID_TICKET_RANGE.findall(t):
        lo, hi = int(a), int(b)
        if lo <= hi and hi - lo < MAX_RANGE:
            out.update(f"{pre}-{n}" for n in range(lo, hi + 1))
    out.update(f"{pre}-{int(n)}" for pre, n in _ID_TICKET.findall(t))
    out.update(f"#{int(n)}" for n in _ID_HASH.findall(t))
    out.update(f"#{int(n)}" for n in _ID_CLOSES.findall(t))
    return out


def closing_refs(text: str) -> set[str]:
    """The ids a pull request or commit says it CLOSES (`Fixes #12`, `Re #12`).

    Separate from `identifiers` because the distinction is what proposal 3 prints:
    a PR whose own number is #7 and whose body says `Fixes #12` is evidence about
    #12, and the marker says so -- `PR #7 (Re #12) merged` -- so a reader checks
    the right thing in one click.
    """
    return {f"#{int(n)}" for n in _ID_CLOSES.findall(text or "")}


# ---- CR-150: work counted per person -------------------------------------------
# One reader, in the module the lint already imports for exactly this reason (CR-142's
# marker): a lint and a generator that disagreed about what "a count against a name" is
# would be worse than neither having a rule.
#
# Why the rule exists, because it governs what this matches and what it must not: counts
# of work per person mislead -- lines reward volume, closures reward splitting one job
# into three, and part of the code is written in agent sessions, so the number measures
# the work's shape and not the person. And the person leading the meeting is often one of
# the people counted, which makes the figure something they read out about themselves.
# Counting belongs in one owner-only document (`metrics_document:`), never in what the
# team reads.
#
# What is NOT a finding, and this is the whole difficulty: a name beside an item -- an
# owner, an assignee, a *Shown by* -- is accountability for a task, and the agenda is
# built out of exactly those. A lint that fires on every owner column is one somebody
# switches off, and then nothing is checked at all. So a finding needs BOTH a DECLARED
# PERSON as its subject AND a count of work against it, and where the subject is a person
# the ORDER decides: a line that names an identifier FIRST is a statement about that item,
# whatever follows it.
#
# The subject is resolved against the project's own `people:` roster and nothing else
# (defect pass). A shape test cannot tell a person from a team, and the capitalised-word
# shape every name has is also the shape of every team, area and grand total a standup
# writes -- `Mobile: 7 PRs merged`, `Backend: 12 issues closed`, `Total: 40 PRs merged`.
# Flagging those as work counted per person is not a near miss, it is the opposite answer,
# and a lint that gives it on ordinary lines gets switched off. Counts per AREA are what a
# standup is for; only counts per PERSON are the rule's business, and the roster is the one
# place a project states who its people are.

# The units of work a person gets compared on. Deliberately a closed list: a count of
# anything else ("3 sessions", "2 days") is not this rule's business, and widening it is
# how a lint starts firing on the round table.
_COUNTED = (r"(?:issues?|tickets?|pull\s+requests?|PRs?|merge\s+requests?|MRs?|commits?"
            r"|lines?(?:\s+of\s+code)?|LOC|story\s+points?)")
# `Bob: 14 issues`, `Bob — 7 PRs merged`, `**Dee** 312 lines of code`. The name is a
# short capitalised token or two, so a sentence is not read as a name, and the count comes
# AFTER it. Whether such a pair is a FINDING is decided in the loop, by what precedes it.
_PERSON_COUNT = re.compile(
    # The name follows the start of the line, a cell boundary, a list bullet or an
    # emphasis mark. Dashes are in the class for the bullet, which is also what lets
    # `- **Dee** — 14 issues closed` match: the subject is found at the bullet, and the
    # dash before the figure is consumed by the separator group below.
    # Sentence punctuation is an anchor too: a leaderboard line often follows a team
    # total on the same line (`Total: 40 PRs merged, Bob: 14 issues closed`), and a
    # subject reachable only after a bullet or a cell wall let that one through.
    # The second word must not be a separator word: under `re.I` a two-word subject
    # happily swallowed `has`, so `Bob has 14 issues` matched with the name "Bob has",
    # which no roster holds -- the count then read as nobody's and went unreported.
    r"(?:^|[|*_·\-]\s*|[,.;]\s+)\*{0,2}([A-Z][\w.'-]*(?:\s+(?!has\b|with\b)[A-Z][\w.'-]*)?)"
    # The separator may sit INSIDE the emphasis (`**Bob:** 14 issues`) or outside it
    # (`**Ann** 312 lines`), which is the difference between matching the shape people
    # actually write and matching only the one shape that was thought of first.
    # `has`/`with` need their own leading space: a `\s*` before this group would eat
    # it and leave `\bhas\b` unreachable, which is what made those two legs dead.
    # The emphasis may close before OR after the separator (`**Ann** 312 lines` against
    # `**Bob:** 14 issues`), so a closing run is allowed on either side of it.
    # `--` is the separator this repo writes in its own prose, so it belongs beside
    # the em and en dashes; without it a leaderboard line written the house way was
    # the one spelling the lint missed.
    r"\*{0,2}(?:\s*[:—–]|\s+(?:has|with)\b|\s*(?:--|[—–\-]))?\*{0,2}\s*"
    r"\*{0,2}(\d+)\*{0,2}\s*" + _COUNTED + r"\b",
    re.I | re.UNICODE)
# ... and the same pair written the other way round: `14 issues closed by Bob`.
_COUNT_PERSON = re.compile(r"\b\d+\s*" + _COUNTED + r"\b[^.|]{0,24}?\bby\s+\*{0,2}([A-Z][\w.'-]*)",
                           re.I | re.UNICODE)
# A column header that names a unit of work, with or without a verb: `Issues closed`,
# `PRs`, `Commits`, `Lines of code`.
_COUNT_HEADER = re.compile(r"^\**\s*(?:\w+\s+)?" + _COUNTED + r"(?:\s+\w+)?\s*\**$", re.I)
# A first cell that is a bare person: one or two capitalised words, no identifier, no
# link, no parenthetical. `**Ann**` is the spelling the round table uses.
_BARE_NAME = re.compile(r"^\**\s*([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*)?)\s*\**$")
_TABLE_RULE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")


def _cells(line: str) -> list[str] | None:
    """A markdown table row's cells, or None when the line is not one."""
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def roster_names(cf: dict) -> set[str]:
    """Every spelling the project's `people:` roster answers to, lower-cased (CR-150).

    Name and aliases both, the way every other roster reader in this module resolves a
    person (the round table, the owed lines, the track spread): a note names whoever was
    spoken, and a config that declares `aliases: [Bob]` for `Robert` has stated that both
    are the same person. First names too -- a roster entry `Ann Rivera` is `Ann` in the
    room, and a lint that only knew the full spelling would miss the leaderboard that
    writes it the short way, which is the way it is always written.
    """
    out: set[str] = set()
    for p_ in cf.get("people") or []:
        if not isinstance(p_, dict):
            continue
        for k in [p_.get("name")] + list(p_.get("aliases") or []):
            if not k:
                continue
            out.add(str(k).strip().lower())
            out.add(str(k).strip().split()[0].lower())
    return out


def person_count_lines(text: str, roster: set[str] | None = None) -> list[tuple[int, str]]:
    """Lines that count work per person: `(line number, what was found)`.

    Two shapes, which are the two ways this gets written:

      - a TABLE whose rows are people and whose columns are counts -- a header naming a
        unit of work (`Issues closed`, `PRs`, `Commits`) over body rows whose first cell
        is a roster name. The header alone is not enough: an area table with a `Closed`
        column is the appendix's own, and its first cell is an area, not a person.
      - a LINE pairing a person with a count of that work, in either order
        (`Bob: 14 issues closed`, `9 commits by Dee`).

    `roster` is the set `roster_names()` builds, and the SUBJECT HAS TO BE IN IT. That is
    the whole gate (defect pass): the capitalised-word shape a name has is also the shape
    every team, area and grand total has, so a shape test answers "work counted per
    person" for `Mobile: 7 PRs merged` and for `Total: 40 PRs merged` -- counts per area,
    which are what a standup is for. Only a count against a person the project DECLARED
    is this rule's business.

    No roster, or an empty one, means NO findings, and that is deliberate rather than a
    fallback. The alternative -- guess at the shape when nothing is declared -- is the
    defect itself, just moved to the projects least able to notice it: a project with no
    `people:` is usually one that has not configured `/ops` much, and it would get the
    false findings while a configured project got none. Silence is the honest answer, and
    `--check` is where a project is told that the check needs a roster (`_check_persons`),
    once, instead of in a finding per line of every file.

    The reason never to return the FIGURE: a finding that repeats it has published it
    into the next file, which is the one place the rule was trying to keep it out of.
    So the second element names the shape and the person, never the number.

    Fenced blocks are skipped, as in `/ops check`'s other readers: a table inside a
    fence is an example of the convention and not a file's content.
    """
    if not roster:
        return []
    out: list[tuple[int, str]] = []
    lines = (text or "").splitlines()
    fenced = False
    count_cols: list[int] = []
    header: list[str] = []
    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            count_cols, header = [], []
            continue
        if fenced:
            continue
        cells = _cells(line)
        if cells is None:
            count_cols, header = [], []
        elif _TABLE_RULE.match(line):
            pass                                  # the rule under a header: table still open
        elif not count_cols and (cols := [i for i, c in enumerate(cells)
                                          if i and _COUNT_HEADER.match(c)]):
            # A candidate header: at least one column after the first names a unit of
            # work. Which ones they are is remembered rather than recomputed, so the
            # finding can name the column that made this a leaderboard, and so the gate
            # and the column set cannot disagree about the same header.
            header, count_cols = cells, cols
        elif count_cols:
            who = _BARE_NAME.match(cells[0]) if cells else None
            if who and who.group(1).strip().lower() in roster \
                    and any(i < len(cells) and re.fullmatch(r"\**\d+\**", cells[i])
                            for i in count_cols):
                col = header[count_cols[0]].strip("* ")
                out.append((n, f"a table row counting {who.group(1)} by {col.lower()}"))
            continue
        # Every pair on the line, not only the first: the subject gate means a match can
        # now be rejected for not being a person, and stopping at the first one would let
        # `Mobile: 7 PRs merged · Bob: 3 commits` hide a real count behind an area's.
        m = next((x for x in list(_PERSON_COUNT.finditer(line)) + list(_COUNT_PERSON.finditer(line))
                  if x.group(1).strip().lower() in roster), None)
        # An identifier BEFORE the pair rules the line out: `#12 Payment webhook — Bob`
        # and `TICK-9 · 3 commits · Ann` are statements about one item, with a name on it
        # for accountability, which is what every line the generator writes is.
        #
        # Only before it, and that is the whole correction (defect pass): "the line names
        # an identifier anywhere" also swallowed `**Bob:** 3 commits on #12`, so appending
        # one issue number to a leaderboard line silenced the lint -- a rule that can be
        # switched off by adding `on #12` is not a rule. What decides is the ORDER: an item
        # with an owner names the item first, and a count against a person names the person
        # first. `m.start()` is where that pair begins.
        if m and not identifiers(line[:m.start()]):
            out.append((n, f"a count of work against {m.group(1)}"))
    return out


def metrics_path(cf: dict) -> Path | None:
    """CR-150, proposal 3: the declared owner-only metrics document, resolved -- or None.

    `metrics_document: status/metrics.md`, relative to the project root or found walking
    up, exactly as a declared report's `dir:` is. Returned whether or not the file exists:
    the lint has to leave the declared PATH alone, and a document that is about to be
    written must not become a finding the day before it is.
    """
    rel = cf.get("metrics_document")
    if not rel:
        return None
    root = Path(cf.get("_root") or ".")
    return next((p / rel for p in (root, *root.parents) if (p / rel).exists()), root / rel)


def source_person_counts(cf: dict) -> list[str]:
    """CR-150, proposal 2: declared sources that already count work per person.

    One line per source, naming it and nothing else -- *per-person figures present in the
    source, not copied*. A digest reads a status report because of what the report says
    about the work; the figures in it are its author's own method (out of scope here) and
    copying them into the agenda would move them from one owner's document into the one
    the room reads, which is the whole thing CR-150 forbids. Saying so is not optional
    either: a digest that silently left them out would be indistinguishable from one whose
    author had not noticed them, and the next person to write one would copy them.

    Vault reports only -- a repo report's path lives in the repository, where this script
    has nothing to read (the same boundary `_renamed_hint` draws). The declared
    `metrics_document` is never one of these: it is the place the figures BELONG.

    WHICH file a declaration resolves to is `build_movement`'s answer, not a second one
    kept here (defect pass): the dir walked up from the project root, `current:` before
    `pattern:`, newest by sort. That module already owns `vault_reports:` -- it is what
    reports their age to `--check` -- and two resolvers would eventually disagree, which
    would mean a report whose age is read off one file and whose figures are read off
    another. Imported inside the function, as the other `build_movement` calls here are:
    it is an optional companion, and a project with no declared report must still build.
    """
    out: list[str] = []
    mine = metrics_path(cf)
    roster = roster_names(cf)
    if not roster:
        return out                     # nothing to resolve a subject against (see above)
    try:
        import build_movement
    except Exception:
        return out                     # best effort, as everywhere else in this pipeline
    for r in ((cf.get("ext") or {}).get("vault_reports") or []):
        if not isinstance(r, dict) or not r.get("dir"):
            continue
        d = build_movement.vault_report_dir(cf, r)
        if not d:
            continue
        for f in build_movement.vault_report_files(d, r):
            if mine and f.resolve() == mine.resolve():
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue               # unreadable is `--check`'s finding, not this one
            if person_count_lines(text, roster):
                out.append(f"**{r.get('name') or r['dir']}**: per-person figures present in"
                           " the source, not copied.")
    return out


# ---- CR-143: generated text uses the roster's names and pronouns ----------------
# One reader for the generator, `/ops check` and the staging gate, in the module that
# already owns roster resolution (CR-150's `roster_names`). A gate and a lint that
# disagreed about what "the wrong pronoun" is would be worse than one of them existing:
# a draft would pass staging and then be a finding, or the reverse.
#
# Why it exists: a team member's name is also a common female name when shortened, and
# the member is male. The roster carried the full name, the aliases and a note. An
# assistant wrote the short form and the wrong pronoun in two separate drafts, once in
# each of two sessions, after the roster and its own notes had both said otherwise, and
# the person had corrected it in a meeting weeks earlier. Both were caught by the
# operator; no check caught either. A name does not tell you anyone's pronouns, which is
# why proposal 3 defaults an unlisted person to `they` and never infers.
#
# WHAT MAKES A LINE A FINDING, and this is the whole design problem. `they` is both the
# singular pronoun for an unlisted person and the ordinary English plural, so a rule that
# fired whenever a declared name shares a line with a pronoun fires on nearly every
# sentence a standup writes -- "Ann and Bob shipped the import; their release is Friday",
# "the team said they would". A lint that fires on ordinary prose is switched off within a
# week, and then it checks nothing at all (CR-150 shipped that failure and it had to be
# fixed twice). So a finding needs ALL FOUR of:
#
#   1. the subject is a person the project DECLARED (`roster_names`, nearest declaration),
#      resolved by name, alias or first name -- never by the shape of a capitalised word;
#   2. the person's entry DECLARES `pronouns:`. No declaration, no finding: the roster is
#      the only thing that knows, and guessing from the name is the defect itself;
#   3. the pronoun is SINGULAR AND GENDERED (`he`/`him`/`his`, `she`/`her`/`hers`).
#      `they`/`them`/`their` is never a finding in either direction -- it is the plural,
#      it is the default for the unlisted, and it is correct for a person who declares it;
#   4. the pronoun CONTRADICTS the declaration, and the line names ONE declared person.
#      A line naming two people is a plural subject, so a gendered pronoun on it may
#      belong to either; that is a sentence to rewrite, not a wrong fact to report.
#
# WHAT THIS CANNOT KNOW, stated plainly because the finding states it too (defect pass).
# The rule above is a POSITION test: the pronoun comes after the name. It is not a REFERENT
# test, and a line-based lint cannot be one -- resolving which noun phrase a pronoun refers
# to is anaphora resolution, and the cases are structurally identical:
#
#     Dee led the review; his summary is filed.               <- the pronoun IS Dee's
#     Dee filed the ticket the reporter raised; her account was locked.   <- it is not
#
# Same shape, same punctuation, same distance; the only difference is that `the reporter`
# denotes a person and `the review` does not, which needs a word list of role nouns, and
# CR-150 records what a word list or a shape test does to this kind of check. So the
# narrowing is condition 6 -- the ONE intervening referent the lint can see without
# guessing, an undeclared person written as a two-word name (`_OTHER_NAME`) -- and the
# finding SAYS the check read position and not reference, so the author confirms rather
# than obeying. A third party named by a role noun still produces a finding; it is a
# finding the author can dismiss in one read, which is the honest cost of a line-based
# check, and it is written down here rather than left for the operator to discover.
#
# The second finding is the AMBIGUOUS SHORT FORM: a roster entry declaring
# `canonical_short:` has said which short spelling a summary uses, and any other short form
# of that entry is reported WITH the canonical one. That is the measured incident's other
# half -- the short form was written, and it reads as somebody else.
#
# ... and it needed a fifth condition, because the lint fired on the GENERATOR'S OWN OUTPUT
# (defect pass). A repo's data carries GitHub LOGINS -- `author.login`, `assignees[].login`
# -- and a login is lower-case and short, so a login that happens to equal somebody's short
# form made every repo-detail line a finding:
#
#     - acme/app #12 Import fix (dee)          <- `pulls_since`, rendered by this module
#     - #7 Retest — dee                        <- the issue list
#     | [#3](url) | api | **open** | dee | ... |  <- the release-blocker table
#
# `/ops check` then reported a wall of findings about text this module wrote deliberately,
# and the operator switches the check off -- which is exactly how CR-150 shipped and had to
# be fixed twice.
#
#   5. an IDENTIFIER BEFORE the short form rules the line out. This is CR-150's rule, and
#      the same reason holds: an item with a handle on it names the ITEM first, and the
#      name after it is an accountability slot the generator filled from the source's own
#      field. PROSE about a person names the person first -- `Dee reviewed the import`,
#      `Dee owns it` -- and has no issue number, ticket key or PR number ahead of them.
#      That is a POSITION-AND-CONTEXT test, not a word list: no login is enumerated
#      anywhere, so a new repo, a new login or a new renderer needs no change here. All
#      three shapes above put `#n` ahead of the name, and so does every other line this
#      module writes from a repo row.
#
# What it deliberately does NOT rule out: `Dee closed #12 yesterday` -- the person is named
# first, the identifier follows, and that is prose. A draft can still silence a genuine
# finding by putting an issue number in front of a sentence about a person, and that is the
# same residual CR-150 accepted for the same reason: the alternative fires on every line of
# every generated appendix, and a check nobody runs catches nothing.

# Singular gendered pronouns, by the form the roster declares. `they` is deliberately
# absent as a MATCH target: see rule 3 above. It is a value `pronouns:` may declare, and
# an entry declaring it simply has no gendered form to contradict.
_PRONOUN_FORMS = {"he": ("he", "him", "his", "himself"),
                  "she": ("she", "her", "hers", "herself")}
PRONOUN_VALUES = ("he", "she", "they")
# Which declared form a spoken pronoun belongs to, lower-cased. `her` is both object and
# possessive and belongs to `she` either way, so one map answers both.
_PRONOUN_OF = {w: form for form, words in _PRONOUN_FORMS.items() for w in words}
_GENDERED = re.compile(r"\b(" + "|".join(sorted(_PRONOUN_OF, key=len, reverse=True)) + r")\b", re.I)
# CR-143, defect pass: an UNDECLARED person named between the declared name and the
# pronoun. Two capitalised words in a row -- a NAME shape, which is the one person-shape a
# single capitalised word does NOT have: `Mobile`, `Backend`, `Total` and every area and
# team a standup writes are one word, and CR-150 records that flagging on single-word
# capitalisation is "not a near miss, it is the opposite answer". So two words, both
# capitalised, both with a lower-case letter following (`API Gateway` and `PR Review` stay
# out). It is a NARROWING only: a match means the pronoun has another candidate referent
# and the line is NOT reported. Missing a third party this does not see is a false
# negative, which is the safe direction for a lint somebody has to keep switched on.
_OTHER_NAME = re.compile(r"\b[A-Z][a-z][\w'-]*\s+[A-Z][a-z][\w'-]*")
# A Title Case pair that is a PERSON rather than a thing: an article or a possessive
# in front of it makes it an object (`the Payment Webhook`, `its Release Branch`), and
# an object is never a candidate referent for `he` or `she`. Everything else is read as
# a name, because the roster is not exhaustive and an undeclared colleague still owns a
# pronoun this check cannot know (CR-143, defect pass).
_OTHER_PERSON = re.compile(
    r"(?<!\bthe )(?<!\ba )(?<!\ban )(?<!\bits )(?<!\bour )(?<!\btheir )(?<!\bthis )"
    r"\b[A-Z][a-z][\w'-]*\s+[A-Z][a-z][\w'-]*")


def pronoun_of(entry: dict) -> str:
    """The pronouns a roster entry declares, or `they` (CR-143, proposal 3).

    `they` for an entry that declares nothing, and for an undeclared value: the default is
    never inferred from the name, which is the whole point of the CR. An entry declaring
    something outside `PRONOUN_VALUES` is a config finding, not a licence to guess.
    """
    v = str((entry or {}).get("pronouns") or "").strip().lower()
    return v if v in PRONOUN_VALUES else "they"


def roster_entries(cf: dict) -> list[tuple[dict, set[str]]]:
    """Each roster entry with every spelling it answers to, lower-cased (CR-143).

    The same resolution `roster_names` performs -- declared name, aliases, and the first
    name of each, because a roster entry `Ann Rivera` is `Ann` in the room -- but kept PER
    ENTRY, because a pronoun belongs to a person and not to the roster as a whole.
    `roster_names` is the union of exactly these sets, so the lint and the per-person
    check cannot disagree about who is declared (the drift this repo warns about).
    """
    return [(p_, keys_of(p_)) for p_ in cf.get("people") or [] if isinstance(p_, dict)]


def keys_of(entry: dict) -> set[str]:
    """Every spelling ONE roster entry answers to, lower-cased: `roster_names` for one."""
    return roster_names({"people": [entry]})


def checkable_entries(people) -> list[tuple[dict, set[str]]]:
    """The roster entries the pronoun lint can check: those that DECLARE something.

    `pronouns:` or `canonical_short:` -- and a spelling to be found by. A scope whose
    roster declares neither contributes nothing, which is what lets `pronoun_scope` keep
    walking up to one that does, and it is the same reason CR-150's check needs a roster:
    the declaration is the only thing that knows.
    """
    return [(e, keys) for e, keys in roster_entries({"people": people or []})
            if keys and (e.get("pronouns") or e.get("canonical_short"))]


def pronoun_scope(path) -> list[tuple[dict, set[str]]]:
    """The roster entries governing `path` for the CR-143 pronoun lint.

    THE ONE RESOLUTION, and that is the point of it (defect pass). `/ops check` and the
    `/outbox` staging gate each had their own walk, and they disagreed: a project folder
    declaring its own roster in `.claude/ops-config.yaml` and holding no plain file at its
    own level was invisible to the check's scope list -- `walk()` skips dotted folders, so
    the project never appeared as a scope -- while the gate's upward walk found it. The
    same draft in that project then PASSED the gate against the project's roster and became
    a finding against the venture's. A gate and a lint that disagree about what the wrong
    pronoun is are worse than one of them existing, which is what this module's own design
    comment says, so there is now one function and both surfaces call it.

    Nearest declaration wins, walking UP from the file's own folder, which is how
    `config()` resolves every other key in this family -- a project declaring its own
    roster is not read against the venture's. The first scope with a CHECKABLE entry
    answers; a scope whose roster declares neither key is passed over, because a roster
    that says nothing about pronouns is not a declaration that the nearer silence wins.

    `None`, no config, or nothing declared anywhere above it, and the answer is empty: the
    caller then reports nothing. Guessing a person's pronouns from their name is the defect
    CR-143 is about.
    """
    if path is None:
        return []
    p = Path(path).expanduser().resolve()
    start = p.parent if p.is_file() or p.suffix else p
    for root in (start, *start.parents):
        for name in CONFIG_FILES:
            f = root / name
            if not f.is_file():
                continue
            try:
                d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(d, dict):
                continue
            if ents := checkable_entries(d.get("people")):
                return ents
    return []


def short_forms(entry: dict) -> set[str]:
    """Every one-word spelling of an entry, lower-cased: the short forms a draft may write.

    The first word of the declared name and of each alias -- the spellings a short form on a
    line is looked up in. Whether a given one is AMBIGUOUS is `pronoun_lines`'s decision and
    only its decision: a `canonical_short:` of `Dee O` and a declared name of `Dee Okafor`
    share their first word, so the question is never "is this word the canonical form" but
    "is this word followed by the rest of a longer spelling". Excluding the canonical form
    here as well was a second answer to that one, and a dead one (mutation pass): removing
    it changed no behaviour, because the longer-spelling guard already covered every case.
    """
    out: set[str] = set()
    for k in [entry.get("name")] + list(entry.get("aliases") or []):
        if k and str(k).strip():
            out.add(str(k).strip().split()[0].lower())
    return {s for s in out if s}


def pronoun_lines(text: str, entries: list[tuple[dict, set[str]]]) -> list[tuple[int, str]]:
    """Lines whose pronoun or short form contradicts the roster: `(line number, what)`.

    The six conditions a finding needs are in the block comment above; they are what keeps
    this off ordinary prose and off this module's own output. Two kinds come back:

      - *a wrong pronoun*: the line names exactly ONE declared person whose entry declares
        `pronouns:`, and then uses a singular gendered pronoun of the other form. Reported
        with the declared form, so the fix is in the finding.
      - *an ambiguous short form*: the line writes a short spelling of an entry that
        declares `canonical_short:`, which has said which short form a summary uses.
        Reported with the canonical one.

    Never a finding: `they`/`them`/`their` anywhere (the plural, the default for an
    unlisted person, and correct for anyone declaring it); a gendered pronoun on a line
    naming two or more declared people (a plural subject -- the pronoun may belong to
    either, which is a sentence to rewrite and not a wrong fact); a gendered pronoun with
    no declared person on the line at all (nobody to contradict); and a person whose entry
    declares no `pronouns:`, because the roster is the only thing that knows.

    The PRONOUN MUST FOLLOW THE NAME on the line. "He reviewed it; Ann is next" names a
    previous subject and a new one, and reading the pronoun back onto the later name is how
    a lint starts being wrong about correct prose.

    Nor is either kind a finding where an IDENTIFIER precedes the name (condition 5): the
    line is then a statement about an item and the name after it is the slot THIS MODULE
    filled from a repo login, not prose about a person. Without this the check reported
    every repo-detail line the generator writes whenever a login equalled somebody's short
    form, which is a check the operator switches off.

    And the wrong-pronoun kind is not a finding where another person is named BETWEEN the
    name and the pronoun (condition 6): the pronoun has a second candidate referent. This
    check reads POSITION, NOT REFERENCE -- it cannot resolve anaphora, a third party named
    by a role noun (*the reporter*, *the customer*) still produces a finding, and the
    finding says so, so the author confirms rather than obeys. The block comment above has
    the two structurally identical sentences that make this unavoidable.

    Fenced blocks are skipped, as in every other reader here: a line inside a fence is an
    example of the convention, not a file's content.
    """
    out: list[tuple[int, str]] = []
    declared = [(e, keys) for e, keys in entries if keys]
    if not declared:
        return out
    fenced = False
    for n, line in enumerate((text or "").splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        low = line.lower()
        words = set(re.findall(r"[\w'-]+", low))
        # Who the line names, and WHERE: the earliest spelling of each entry on the line.
        # A word-boundary search rather than the token set, so the position is known --
        # condition 4 needs the pronoun to come after the name.
        # The END of the matched spelling is kept beside its start (defect pass): the
        # referent narrowing below reads the span BETWEEN the name and the pronoun, and
        # taking that span from the name's start would put the name's own second word
        # (`Dee Okafor`) inside it and read as an intervening person every time.
        named: list[tuple[int, int, dict]] = []
        for e, keys in declared:
            spans = [(m.start(), m.end()) for k in keys
                     for m in [re.search(r"\b" + re.escape(k) + r"\b", low)] if m]
            if spans:
                named.append((*min(spans), e))
        # The ambiguous short form is its own finding and does not need a pronoun at all:
        # the measured incident wrote the short spelling AND the wrong pronoun, and either
        # alone is the thing to fix. One per entry per line.
        #
        # It has to be written SHORT, standing alone (defect pass): `Dee` is the first word
        # of `Dee Okafor`, so a token test reported the FULL declared name as its own
        # ambiguous short form -- a finding on the one spelling that is never ambiguous, on
        # every line naming the person. What is looked for is the short form NOT followed by
        # a further word of a longer spelling the same entry answers to.
        for _at, _end, e in named:
            canon = str(e.get("canonical_short") or "").strip()
            if not canon:
                continue
            # The CANONICAL form counts as one of the longer spellings (defect pass):
            # `Dee O` starts with `Dee`, so without it the one spelling the roster ASKS
            # for was reported as the ambiguous one -- a lint telling the author to write
            # exactly what they wrote.
            longer = sorted((k for k in keys_of(e) | {canon.lower()} if " " in k),
                            key=len, reverse=True)
            # A longer spelling must match AT A WORD BOUNDARY from here, not as a bare
            # prefix (defect pass): `Dee O` is a prefix of `Dee owns the import`, so a
            # `startswith` silenced the finding on the very sentence the CR is about.
            #
            # Condition 5 (defect pass): each occurrence is kept only if NO identifier
            # precedes it on the line. `line[:m.start()]` rather than the whole line, so
            # `Dee closed #12` -- prose, person first -- is still the finding it was,
            # while `#12 Import fix (dee)`, which this module wrote from a login, is not.
            wrote = sorted(s for s in short_forms(e) & words
                           if any(not any(re.match(re.escape(k) + r"\b", low[m.start():])
                                          for k in longer)
                                  and not identifiers(line[:m.start()])
                                  for m in re.finditer(r"\b" + re.escape(s) + r"\b", low)))
            if wrote:
                out.append((n, f"the short form `{wrote[0]}` is ambiguous: write `{canon}`"))
        if len(named) != 1:
            continue          # no declared person, or a plural subject (condition 4)
        at, end, e = named[0]
        want = pronoun_of(e)
        if want not in _PRONOUN_FORMS:
            continue          # `they`, declared or defaulted: no gendered form to contradict
        # Condition 5, as for the short form: an identifier BEFORE the name means the line
        # is a statement about an item and the name is the slot this module filled from a
        # login, not prose about a person.
        if identifiers(line[:at]):
            continue
        m = next((x for x in _GENDERED.finditer(line) if x.start() > at
                  and _PRONOUN_OF[x.group(1).lower()] != want), None)
        # Condition 6 (defect pass): another person named between the name and the pronoun
        # gives the pronoun a second candidate referent, and the line is then not reported.
        # This is a NARROWING, and a partial one on purpose -- see the honesty note below.
        # Only another PERSON gives the pronoun a second candidate referent: a declared
        # one, or a two-word name that is not a known thing. `_OTHER_NAME` alone matched
        # any Title Case pair, so an artefact or an area title between the name and the
        # pronoun (`Ann reviewed the Payment Webhook and he signed off`) silenced a
        # genuine wrong pronoun. The roster is not exhaustive -- an undeclared colleague
        # is still a referent -- so a Title Case pair counts unless the words before it
        # make it a thing: `the`, `a` and a possessive introduce an object, never a name.
        # A DECLARED second person never reaches here: condition 4 above already drops a
        # line with two declared subjects, so this only has to recognise an UNDECLARED
        # one -- which is why the roster is not consulted again.
        between = line[end:m.start()] if m else ""
        if m and not _OTHER_PERSON.search(between):
            out.append((n, f"{e.get('name')} is `{want}` in the roster, and this line"
                           f" writes `{m.group(1).lower()}` after their name -- confirm the"
                           " pronoun refers to them (this check reads position, not"
                           " reference)"))
    return out


def probably_closed(items, chat, repo, jira):
    """Carried items the sources suggest are finished, each with its basis.

    Carry-forward is never compared with anything, so an item that shipped
    yesterday leads this morning's agenda and the room spends its first minutes
    saying so. This looks for evidence and separates those items -- it NEVER drops
    one. A human confirms in the room and the next note records the close: a
    machine that closes items silently is worse than one that repeats them.

    CR-101, how evidence is weighed:
    - per item, the NEWEST matching evidence decides, not the first found;
    - a chat message with a negative (failing, not solved, reverted ...) is
      counter-evidence, and a newer negative cancels an older positive;
    - a merged PR, a published release, a closed issue or a done ticket that
      matches outranks any chat message;
    - the evidence cell carries the date (and time, for chat) that was used.

    CR-141, what MATCHES:
    - an explicit identifier shared between the carried line and the evidence --
      the line's own `#id` or ticket key, or a pull request that names the issue
      (`Re #id`, `Fixes #id`). No title-similarity matching, at all;
    - a carried line that names no identifier is never marked. It stays carried and
      `without_identifier` lists it for the details file as *items with no
      identifier, cannot be checked* -- saying nothing is the honest answer;
    - a state change is not a close: a ticket that only moved to a *fixed* state
      is evidence of `fixed, waiting for a test`, never of a close, so it is not
      marked as probably closed.

    Returns (closed, still), unchanged in shape: CR-141 narrows WHICH items land in
    the first list, and the lines it can say nothing about are read separately with
    `without_identifier`.
    """
    ev = []   # (rank, when, kind, ref, txt, negative, ids)
    for c in chat:
        for line in (c.get("messages") or []):
            txt = line[1] if isinstance(line, (tuple, list)) and len(line) > 1 else str(line)
            neg = bool(NEGATIVE_WORDS.search(txt or ""))
            if neg or DONE_WORDS.search(txt or ""):
                ids = identifiers(txt)
                if ids:   # CR-141: a done-word with no id names no work
                    # CR-141, proposal 3: the basis names the identifier matched on.
                    # `<channel> · <timestamp>` alone named no id, so the one marker
                    # a reader could not verify in one click was the chat one -- and
                    # the quote it leaned on is truncated, which could cut the id out.
                    ev.append((1, _chat_when(txt), "chat",
                               f"{c.get('name') or 'chat'} names {', '.join(sorted(ids))}",
                               txt.strip(), neg, ids))
    for r in repo:
        kind = r.get("kind", "issue")
        when = str(r.get("when") or "")[:16].replace("T", " ")
        n = r.get("n", "")
        title = r.get("title", "")
        if kind == "pull" and r.get("status") == "merged":
            # CR-141: a merged PR is evidence about what it SAYS it closes, and about
            # itself. `Re #12` is the link a reader checks. `closes` is read by the
            # producer, where the archived description is (`pulls_since`); the title
            # is re-read here so a row assembled by another caller still works.
            closes = set(r.get("closes") or ()) | closing_refs(title)
            basis = f"{r.get('repo','')} PR #{n} merged"
            if closes:
                basis = f"{r.get('repo','')} PR #{n} ({', '.join(f'Re {c_}' for c_ in sorted(closes))}) merged"
            ev.append((2, when, "repo", basis, title, False, closes | {f"#{n}"} if n != "" else closes))
        elif kind == "release":
            # A release names what it shipped in its notes; nothing else about it is
            # an identifier, so a release with no id in its notes matches nothing.
            # CR-141: `names` is read by the producer, which has the archived notes;
            # the title is re-read here for a row another caller assembled.
            ev.append((2, when, "repo", f"{r.get('repo','')} release {r.get('n','')}",
                       title, False, set(r.get("names") or ()) | identifiers(title)))
        elif kind == "issue" and r.get("state") == "closed":
            ev.append((2, when, "repo", f"{r.get('repo','')} issue #{n} closed", title, False,
                       {f"#{n}"} if n != "" else set()))
    for t in jira:
        state = t.get("state") or ""
        n = str(t.get("n") or "")
        if not n:
            continue
        # CR-141, proposal 4: a state change is not a close. `fixed` on a board means
        # the work is waiting for a test, and the agenda already has words for that.
        if any(w in state for w in ("done", "closed", "resolved")):
            ev.append((2, "", "tickets", f"ticket {n} {state or 'done'}", t.get("title", ""), False, {n.upper()}))
    if not ev:
        return [], items

    closed, still = [], []
    for label, rest in items:
        want = identifiers(f"{label} {rest}")
        if not want:
            # CR-141, proposal 2: no identifier, no marker. The line stays carried and
            # the details file says it could not be checked, rather than the card
            # claiming something about it that nobody can verify in one click.
            still.append((label, rest))
            continue
        matches = [e for e in ev if want & e[6]]
        strong = sorted((e for e in matches if e[0] == 2), key=lambda e: e[1])
        chats = sorted((e for e in matches if e[0] == 1), key=lambda e: e[1])
        hit = None
        if strong:
            hit = strong[-1]
        elif chats and not chats[-1][5]:
            hit = chats[-1]           # the newest chat word is a positive one
        if hit:
            _rank, when, kind, ref, txt, _neg, ids = hit
            # CR-141, proposal 3: the quote is cut here, where the ids that matched
            # are known, so the cut cannot remove the id the basis names.
            closed.append((label, rest, (kind, f"{ref} · {when}" if when else ref,
                                         quote_for(txt, want & ids))))
        else:
            still.append((label, rest))
    return closed, still


# CR-141, proposal 4: states a board uses for work that is BUILT but not accepted.
# A close is a close; everything here is a state change, and the agenda already has
# the words for it -- the release-blockers table has said `fixed, waiting for a test`
# since CR-114. Marking one of these *probably closed* is how a carried item left the
# card before anyone had tested it.
FIXED_STATES = ("fixed", "in review", "in test", "ready for test", "ready for qa",
                "verify", "awaiting test", "qa")


def state_changed(items, jira) -> list[tuple[str, str, str]]:
    """Carried items whose ticket moved to a built-but-not-accepted state.

    `(label, rest, "fixed, waiting for a test")` per item, matched on the ticket key
    the carried line names -- never on words, same rule as `probably_closed`. This
    is deliberately NOT a close: the room is told the work exists and the test does
    not, which is the thing it has to schedule, and the item stays carried until
    somebody says it passed.
    """
    by_id = {}
    for t_ in jira:
        n = str(t_.get("n") or "").upper()
        st = str(t_.get("state") or "").lower()
        if n and any(w in st for w in FIXED_STATES) and not any(
                w in st for w in ("done", "closed", "resolved")):
            by_id[n] = st
    if not by_id:
        return []
    out = []
    for label, rest in items:
        hit = sorted(identifiers(f"{label} {rest}") & set(by_id))
        if hit:
            out.append((label, rest, "fixed, waiting for a test"))
    return out


def quote_for(txt: str, ids, width: int = 70) -> str:
    """CR-141, proposal 3: a quoted evidence line that still shows the id.

    The quote is truncated to keep the table readable, and a chat line that says
    the interesting thing late (`... which closes #12`) lost the identifier to the
    cut -- leaving a marker whose own quote did not support it. The basis names the
    id either way, so this is about the quote agreeing with it: if the first `width`
    characters contain none of the matched ids, the window slides to the first one
    and is marked as a middle (an elision on each side it actually cut).
    """
    t = " ".join((txt or "").split())
    if len(t) <= width:
        return t
    found = sorted((t.find(i), len(i)) for i in (ids or ()) if i in t)
    if not found or any(p + n <= width for p, n in found):
        return t[:width].rstrip() + "..."       # an id is already in the window
    at = found[0][0]
    start = max(0, at - width // 3)
    return "..." + t[start:start + width].rstrip() + ("..." if start + width < len(t) else "")


def reconcile_closed(closed, fixed_rows):
    """CR-141: one carried line gets ONE verdict, and *waiting for a test* wins.

    `probably_closed` and `state_changed` read the same carried lines against the
    same sources independently, and a line naming two keys can satisfy both: with
    `TICK-9` done and `TICK-10` in review, the line was reported as *probably
    closed* AND as *fixed, waiting for a test* -- two sections contradicting each
    other -- and the close also took it off the carried list, so the room lost the
    item whose test nobody had run.

    Precedence is proposal 4's: a state change is not a close, so an item with any
    built-but-not-accepted key stays carried and keeps only the *waiting for a
    test* row. The close evidence is not thrown away silently -- it is still true
    about the key it names -- but the line is not declared finished while part of
    it is untested. Returns the filtered `closed` list; `fixed_rows` is unchanged.
    """
    waiting = {(l, r) for l, r, _st in fixed_rows}
    return [(l, r, h) for l, r, h in closed if (l, r) not in waiting]


def without_identifier(items) -> list[tuple[str, str]]:
    """CR-141: carried lines that name no `#id` and no ticket key.

    The honest companion to a narrowed matcher. Nothing can be checked about these
    lines, so they get no marker -- and that silence is itself worth printing, in
    the details file rather than on the card: a reader who knows the matcher ran
    should know which items it had nothing to go on for, otherwise *no markers*
    reads as *nothing moved*.
    """
    return [(l, r) for l, r in items if not identifiers(f"{l} {r}")]


# ---- CR-147: a certain close, read back off the source -----------------------
# CR-141 made the match reliable; this acts on it. The distinction is the whole
# CR: *probably closed* SUGGESTS a close from any evidence the sources carry --
# a chat word included -- and the line stays on the page for a human. A CERTAIN
# close is a state read off the work's own source, and the line leaves the card.
# Measured over two consecutive meetings, about six of eleven dependency rows and
# then four of seven were removed on sight by the person leading, and for most of
# them the tracker already said closed, merged or done. That removal is the work
# this does before the room sits down.
#
# What counts, and nothing else (proposal 5):
#   - an issue whose state is closed;
#   - a pull request that is merged AND names the id (`Fixes #12`, `Re #12`);
#   - a ticket whose state contains done, closed or resolved.
# A merged pull request that names no id closes nothing: it is evidence about
# itself, and the carried line is not its subject. A label change is never a
# close -- `state_changed` already owns that judgement and `reconcile_closed`
# already gives it precedence, so this reuses both rather than deciding again.

# Which archive answers for an identifier's kind, and which config key declares it
# (proposal 6). A `#id` is a repo number and a ticket key is the board's, so a line
# can only be dropped when the archive that would contradict the drop was actually
# read -- and only a DECLARED source can be unread, exactly as in `failed_fetches`.
_ID_SOURCE = {"repo": (".githubmeta", "repos"), "tickets": (".jirameta", "jira")}


def certainly_closed(items, repo, jira):
    """Carried lines whose own source says closed or merged, each with its basis.

    `(label, rest, (kind, basis, when))` per line, where `kind` is `repo` or
    `tickets` -- the archive the verdict came from, so the caller can refuse to
    drop a line whose archive failed to fetch (CR-147, proposal 6).

    Identifiers come from CR-141's `identifiers` and `closing_refs`; a second
    extractor here would drift from the marker's own notion of what a line names,
    and the two disagreeing about the same line is worse than either being wrong.

    The newest state wins, as in `probably_closed`: a reopened issue re-read in
    the same window must not be closed by the older row.
    """
    # (when, kind, basis, ids, closes) -- a row that is NOT a close is evidence too,
    # because the NEWEST state has to decide: an issue closed and reopened inside the
    # same window appears twice, and acting on the older row would drop a live line.
    ev = []
    for r in repo:
        if not isinstance(r, dict):
            continue
        kind = r.get("kind", "issue")
        when = str(r.get("when") or "")[:16].replace("T", " ")
        n = r.get("n", "")
        if kind == "issue" and n != "":
            shut = r.get("state") == "closed"
            ev.append((when, "repo", f"{r.get('repo','')} issue #{n} "
                       + ("closed" if shut else str(r.get("state") or "open")), {f"#{n}"}, shut))
        elif kind == "pull" and r.get("status") == "merged":
            # Proposal 5: a merged PR is a certain close only of what it SAYS it
            # closes. Its own number is deliberately not in the id set -- a line
            # naming #7 where #7 is the pull request is a line about the change,
            # not about a closed issue, and dropping it would be the false drop
            # this CR must not make.
            closes = set(r.get("closes") or ()) | closing_refs(r.get("title", ""))
            if closes:
                ev.append((when, "repo",
                           f"{r.get('repo','')} PR #{n} ({', '.join('Re ' + c for c in sorted(closes))}) merged",
                           closes, True))
    for t_ in jira:
        if not isinstance(t_, dict):
            continue
        n = str(t_.get("n") or "")
        state = str(t_.get("state") or "").lower()
        if not n:
            continue
        shut = any(w in state for w in ("done", "closed", "resolved"))
        ev.append((str(t_.get("updated") or "")[:16].replace("T", " "), "tickets",
                   f"ticket {n.upper()} {state or 'open'}", {n.upper()}, shut))
    if not ev:
        return []
    out = []
    for label, rest in items:
        want = identifiers(f"{label} {rest}")
        if not want:
            continue          # proposal 3's case, not this one
        # Per identifier the newest row decides; across identifiers ANY still-closing
        # one closes the line, and `reconcile_closed` is what holds a line whose other
        # key is merely built (CR-141's precedence, reused rather than re-decided).
        hit, shut_ids = None, set()
        for i in sorted(want):
            rows = sorted((e for e in ev if i in e[3]), key=lambda e: e[0])
            if rows and rows[-1][4]:
                hit = hit or rows[-1]
                # Only the identifiers whose OWN newest row closes them. A line may
                # name several; announcing the line's whole id set as closed asserts
                # a close for an id whose source still says open, which is the silent
                # misstatement this CR exists to prevent.
                shut_ids.add(i)
        if hit:
            when, kind, basis, _ids, _shut = hit
            out.append((label, rest, (kind, basis, when, shut_ids)))
    return out


def readable_sources(cf: dict, recs: dict, rows: dict, today: datetime.date | None = None) -> dict[str, str]:
    """CR-147, proposal 6: per verdict kind, the reason its source may not be
    trusted to remove a line -- or nothing, when it was read.

    `{"repo": "fetch failed ...", "tickets": ...}`, keyed as `certainly_closed`
    keys its verdicts. Two ways a source cannot be read, and both are already
    reported elsewhere, so both are reused rather than re-derived:

    - CR-088's fetch record says the fetch FAILED. A failed fetch leaves the last
      good data in place, which reads as current (CR-140) -- tolerable for a line
      the page repeats, fatal for a line the page removes.
    - the producer could not reach the archive at all and said so in a `note` row
      (no archive above the project, no snapshot, unreadable, not refreshed).

    A fetch that was never RECORDED is not a failed one. `fetch_status` calls it
    *fetch not recorded* precisely because the three states need three answers,
    and treating the unknown as a failure would make this pass inert on every
    project whose archiver predates CR-088 -- which is most of them.

    An UNDECLARED source is not an unread one either, which is what `cf` is read
    for -- the same gate `failed_fetches` applies, and for the same reason. A
    `_fetch.json` left under `.jirameta/` by a config that no longer declares
    `jira:` produces no verdicts at all, so nothing is held back on its word; but
    the header names every blocked source, and naming one the project does not use
    tells the room a source failed when none did.
    """
    today = today or datetime.date.today()
    ext = cf.get("ext") or {}
    bad = {}
    for kind, (sub, declares) in _ID_SOURCE.items():
        if not ext.get(declares):
            continue
        rec = recs.get(sub)
        if rec is not None and not fetch_ok(rec):
            bad[kind] = fetch_status(rec, today)
            continue
        notes = [r["note"] for r in (rows.get(kind) or [])
                 if isinstance(r, dict) and r.get("note")]
        if notes:
            bad[kind] = notes[0]
    return bad


def drop_closed(closed, blocked: dict[str, str]):
    """CR-147, proposal 6: split certain closes into the ones that may act and the
    ones whose source could not be read.

    Returns `(acted, held)`. A held line keeps carrying exactly as before this CR
    -- which is the point: a source that cannot be read must not be able to empty
    the card, and the header names it instead.
    """
    acted = [h for h in closed if h[2][0] not in blocked]
    held = [h for h in closed if h[2][0] in blocked]
    return acted, held


def off_card_keys(certain_keys: set[str], pending_keys: set[str],
                  closed_keys: set[str], card_keep: set[str]) -> set[str]:
    """CR-147: the carried lines kept off the card's own sections.

    One predicate, because the card's sections, each person's minute and the chat
    post all decide this and three copies of the condition drifted apart once
    already. A line is off the card when its source certainly closed it, when
    nothing could be read about it and nobody confirmed it (proposal 3), or when a
    probable close was matched and CR-107 does not hold it.

    `certain_keys` is named in its own right although it is, today, redundant:
    every certain close is also a probable one, and `card_keep` is built as
    `closed_keys - certain_keys`, so `closed_keys - card_keep` already covers it.
    It stays because the redundancy is an accident of two matchers reading the same
    rows, not an invariant this predicate should rest on -- the header announces a
    certain close, and a line announced closed must never still be on the card.
    Verified redundant 2026-10-21; if the matchers diverge, this term is what keeps
    the page honest, so it is tested directly rather than through `main()`.
    """
    return certain_keys | pending_keys | (closed_keys - card_keep)


# ---- CR-147, proposal 3: a line nobody can check is not asserted as live -----
# A line with no identifier used to sit on the card looking like a live
# dependency. Nothing can be checked about it, so the card must not assert it:
# it goes to the details file under *cannot be checked* and returns to the card
# only on its owner's word, said in their own minute and written into the note.
#
# CR-142 adds a second state with exactly these rules (an inference nobody has
# confirmed), so the mechanism is factored on the marker, not on this CR's one
# case: `unconfirmed()` takes the markers to look for and `ages_out()` counts the
# sessions. CR-142 adds its marker to `CONFIRM_MARKERS` and inherits both.

# What an owner's confirmation looks like in the source part of a carried line.
# `*confirmed: still waiting on the other team*` -- the word plus whose word it
# is, because "still open" with no name is the thing that kept carrying.
_CONFIRMED = re.compile(r"\*confirmed\b", re.I)

# CR-142: what the writer of a summary writes where a phrase was not said and is in no
# source -- `*inferred: the release day*`. Measured: one meeting's audio was partly
# garbled, three phrases were resolved by guessing and written as facts (a release day,
# an owner, which items belonged together), and two days later all three turned out
# partly wrong and a decision register line had to be corrected. One regex for all three
# places the marker is written -- the source part of a carried line, a decision's note,
# and `Inferred:` in prose -- because a second reader would let the agenda and the check
# disagree about the same line.
_INFERRED = re.compile(r"\*inferred\b|^[ \t]*inferred:", re.I | re.M)

# WHAT was inferred, pulled out of the marker the pattern above matched --
# `*inferred: the release day*` -> `the release day`. Public and exported for the same
# reason `_INFERRED` is one regex: the agenda asks the room about the guess and `check`
# names it in a finding, and a second copy would let the two quote different words off
# one line (CR-142, defect pass -- it was duplicated inline here and in the check).
INFERRED_WHAT = re.compile(r"\*inferred:?\s*(.*?)\*", re.I)

# CR-147: markers that put a carried line in the unconfirmed state. One entry per
# CR that defines such a state; CR-142's `*inferred:*` is the second one.
CONFIRM_MARKERS: tuple[re.Pattern, ...] = (_INFERRED,)


# Proposal 3: how many sessions an unconfirmed line may carry before the agenda
# stops repeating it. Two, as written -- long enough for an owner who was absent
# once, short enough that the list does not become the thing nobody reads.
CONFIRM_SESSIONS = 2


def inferred_what(text: str, default: str = "not stated") -> str:
    """CR-142: the words the marker on `text` names, or `default` where it names none.

    One reader for both callers -- the agenda's *Confirm or drop* column and `check`'s
    finding message -- because a line is asked about by the GUESS and not by the item,
    and two readers quoting one line differently is the disagreement the single regex
    for the marker itself already rules out.
    """
    m = INFERRED_WHAT.search(text or "")
    return (m.group(1).strip() if m else "") or default


def confirmed(rest: str) -> bool:
    """Whether a carried line's source part carries its owner's confirmation."""
    return bool(_CONFIRMED.search(rest or ""))


def inferred(text: str) -> bool:
    """CR-142: whether a piece of text carries an UNCONFIRMED inference marker.

    True for a carried line's source part, a decision's note or a line of prose holding
    `*inferred: <what>*`; false once the same text also carries a confirmation, because
    proposal 5 is that a confirmed inference loses its marker in the next summary, and
    until that summary is written the owner's word is what the room actually has.
    """
    txt = text or ""
    return bool(_INFERRED.search(txt)) and not _CONFIRMED.search(txt)


def unconfirmed(items, extra_markers=()):
    """Carried lines in the unconfirmed state, with the reason each is in it.

    `(label, rest, reason)`. A line carrying one of the registered markers or of
    `extra_markers` is unconfirmed because what it says was inferred (CR-142); a
    line carrying none of them and naming no identifier is unconfirmed because
    nothing can be read about it (CR-147). A line whose owner confirmed it is in
    neither list -- that is the one word that puts it back on the card.

    The MARKER is tested first, and that order is the requirement rather than a
    detail (CR-142, defect pass). An inference is exactly the thing that has to be
    confirmed or dropped, and most inferences -- an owner, a release day, which
    items belong together -- name no identifier at all. Testing the identifier
    first routed every one of those into CR-147's *cannot be checked* table, where
    `confirm_or_drop` does not look, so after two sessions the agenda stopped
    asking about the guess instead of asking harder. A line with NO marker still
    gets CR-147's reason unchanged.
    """
    out = []
    for label, rest in items:
        if confirmed(rest):
            continue
        if any(pat.search(rest or "")
               for pat in tuple(CONFIRM_MARKERS) + tuple(extra_markers)):
            out.append((label, rest, "unconfirmed inference"))
        elif not identifiers(f"{label} {rest}"):
            out.append((label, rest, "no identifier, nothing to read"))
    return out


def ages_out(sessions: int, limit: int = CONFIRM_SESSIONS) -> bool:
    """Whether an unconfirmed line has carried long enough to stop being repeated.

    Sessions, not days: CR-139's point that a session is not a unit of time cuts
    both ways, and an item nobody confirmed over two sittings of the series is the
    one the agenda should stop asserting.
    """
    return sessions > limit


def confirm_or_drop(items, streaks: dict[str, int], limit: int = CONFIRM_SESSIONS):
    """CR-142, proposal 2: carried lines whose inference nobody has confirmed, after
    `limit` sessions of carrying it.

    `(label, rest, sessions)`, **owner first** -- sorted by owner and only then by the
    item, because this list is read out to people and one ordered by item makes every
    owner hunt for their own rows. `UNOWNED` sorts last: a line nobody owns is not a
    question for anyone in particular, and putting it first buries the ones that are.

    The state and the threshold are CR-147's, reused rather than counted again:
    `unconfirmed` decides which lines are in it and `ages_out` when they have waited
    long enough, so an unconfirmed inference and a line nothing can be read about come
    off the card on exactly the same schedule.
    """
    rows = [(l, r) for l, r, why in unconfirmed(items) if why == "unconfirmed inference"]
    out = [(l, r, streaks.get(key(l), 0)) for l, r in rows
           if ages_out(streaks.get(key(l), 0), limit)]
    out.sort(key=lambda t: (owner_of(t[0], t[1]) == "UNOWNED",
                            owner_of(t[0], t[1]).lower(), item_of(t[0], t[1]).lower()))
    return out


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


# ---- CR-145, proposal 3: which of two recordings of one meeting is the source ---
#
# Measured: two recordings of one meeting existed in the store -- a notetaker's and the
# operator's own, differing in length and in whether speakers are named. Nothing in the
# config said which was the source, so the assistant chose one (the one with named
# speakers) and mentioned the other in a header. The choice was defensible and
# undeclared, which means the next run could make the other one and nothing would notice.
#
# So the project DECLARES its preference and the output LISTS BOTH. Those are two separate
# fixes for two separate halves of the same incident: a declared preference makes the
# choice reproducible, and listing the one not used is what stops a dropped recording from
# looking like a recording that never existed. Dropping the second silently is the failure
# this module names everywhere else -- a source that was skipped must say so.
#
# `named-speakers` is the only preference implemented, because it is the only one measured
# and because each one is a claim about what an archiver writes. An undeclared or unknown
# value falls back to the longest recording: without a preference the longest is the one
# most likely to be the whole meeting, and a run that cannot explain its choice at least
# makes the same one every time.
RECORDING_PREFERENCES = ("named-speakers", "longest")
RECORDING_DEFAULT_PREFERENCE = "longest"
# A variant an archiver writes when the transcript resolves speakers to names rather than
# to "Speaker 1". The spelling is the archiver's and this side of the contract does not get
# to dictate it, so several are accepted -- but each is matched as a WHOLE TOKEN sequence
# and never as a substring (CR-145, defect pass).
#
# Why: with substring matching, the bare word `named` in this list made
# `unnamed-speakers`, `unnamed` and `renamed-v2` all report named speakers,
# so a `prefer: named-speakers` declaration selected the recording whose speakers are
# explicitly NOT named -- the opposite of what the operator declared, and silently, because
# the output names the chosen recording and not the reason. A variant is a token list
# (`named-speakers`, `named speakers v2`), so tokenising it is reading the contract as the
# archivers write it rather than guessing inside words.
#
# The bare `named` is NOT one of the accepted spellings, for the same reason: on its own it
# says nothing about speakers, it is the token every negative spelling also contains, and
# as one token it still matched `un-named`. A spelling that cannot be told apart from its
# own negation is not a signal. Each accepted spelling names SPEAKERS explicitly.
_NAMED_SPEAKER_WORDS = ("named-speakers", "named speakers", "speaker-names")
# Tokens that NEGATE whatever follows them. `not-named-speakers` contains the accepted
# sequence `named speakers` and means its opposite, so a match immediately preceded by one
# of these is not a match: the same defect as `unnamed`, one token further out.
_VARIANT_NEGATIONS = ("not", "no", "un", "without")
# Anything that is not a letter or a digit separates tokens: `-`, `_`, `.`, space and `/`
# are all seen in one archiver or another, and none of them is part of a word.
_VARIANT_TOKEN = re.compile(r"[^a-z0-9]+")


def _variant_tokens(value) -> list[str]:
    """One recording variant as its lower-cased tokens (CR-145, defect pass)."""
    return [t for t in _VARIANT_TOKEN.split(str(value or "").lower()) if t]


# The spellings of true and false a hand-written YAML flag arrives as (CR-145, defect
# pass). `yaml.safe_load` already turns bare `true`/`yes`/`on` into a bool, but a QUOTED
# `"true"` and a `1` reach this side as a string and an int -- and the first reading of
# `connected:` tested `is True`, so both fell through to the false branch and produced NO
# finding: an operator who declared the connection in a spelling YAML permits got the old
# behaviour and nothing telling them why. Every other key this CR adds either takes effect
# or is reported, so this one does too.
_FLAG_TRUE = ("true", "yes", "on", "1")
_FLAG_FALSE = ("false", "no", "off", "0")


def flag_value(value) -> bool | None:
    """One declared boolean flag as a bool, or None where the spelling is not one.

    None is "the operator wrote something, and it is not a yes or a no" -- the case that
    earns a config finding rather than a silent default, exactly as an unknown `kind:` or
    `prefer:` does (CR-145, defect pass). An ABSENT key is also None, so callers that
    distinguish the two check for the key themselves.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):  # `connected: 1` is the same declaration as `connected: true`
        return True if value == 1 else False if value == 0 else None
    if isinstance(value, str):
        v = value.strip().lower()
        return True if v in _FLAG_TRUE else False if v in _FLAG_FALSE else None
    return None


def store_connected(cf: dict) -> bool:
    """Whether the declared recording store is one the close-out step can read itself.

    CR-145, proposal 4. `connected: true` beside a `store:` is the operator saying the
    close-out has a way in -- so the CR-140 check can say *checked* rather than reporting
    *not checked* forever at a source somebody does look at.

    **Whether a project declares it stays the operator's decision, and this never infers
    it.** A store's name says nothing about whether anything can read it, and a guess here
    would turn an undeclared store into a claim that the transcript will arrive. It also
    requires a `store:`: `connected: true` on its own names nothing to connect to.

    The flag is read through `flag_value`, so the YAML-truthy spellings an operator may
    write -- a quoted `"true"`, a `1`, `yes` -- are the declaration they look like, and a
    value that is NEITHER a yes nor a no is a config finding rather than a quiet no
    (CR-145, defect pass).
    """
    trd = (cf.get("ext") or {}).get("transcripts") or {}
    return bool(trd.get("store")) and flag_value(trd.get("connected")) is True


def recording_preference(cf: dict) -> str:
    """The declared `transcripts.prefer:`, or `longest` (CR-145, proposal 3)."""
    v = str(((cf.get("ext") or {}).get("transcripts") or {}).get("prefer") or "").strip().lower()
    return v if v in RECORDING_PREFERENCES else RECORDING_DEFAULT_PREFERENCE


def _duration_seconds(value) -> int:
    """A recording's duration as seconds, or 0 where it cannot be read.

    Archivers write this as seconds, as `MM:SS` or as `H:MM:SS`, so all three are read
    here rather than one being declared the only true spelling -- the field belongs to
    the archiver. An unreadable duration is 0, which puts the recording LAST in a
    longest-first order: a recording whose length is unknown must not win a comparison
    it never entered.
    """
    s = str(value or "").strip()
    if not s:
        return 0
    if re.fullmatch(r"\d+", s):
        return int(s)
    if re.fullmatch(r"(?:\d+:)?\d{1,2}:\d{2}", s):
        total = 0
        for part in s.split(":"):
            total = total * 60 + int(part)
        return total
    return 0


def has_named_speakers(rec: dict) -> bool:
    """Whether a recording's declared variant says its speakers are named.

    Matched on WHOLE TOKENS (CR-145, defect pass): `unnamed-speakers`, `unnamed` and
    `renamed-v2` say the speakers are not named, or say nothing about them, and each one
    matched the bare substring `named`. A preference the operator declared must not select
    the one recording that contradicts it.
    """
    toks = _variant_tokens((rec or {}).get("variant"))
    for want in (_variant_tokens(w) for w in _NAMED_SPEAKER_WORDS):
        for i in range(len(toks) - len(want) + 1):
            # A token SEQUENCE, so `named-speakers` matches `named speakers v2` as well,
            # while `unnamed speakers` -- a different first token -- matches nothing.
            if toks[i:i + len(want)] != want:
                continue
            if i and toks[i - 1] in _VARIANT_NEGATIONS:
                continue  # `not named-speakers` is the claim's negation, not the claim
            return True
    return False


def choose_recordings(recs: list[dict], prefer: str) -> list[dict]:
    """The same recordings, each gaining `used` and grouped by meeting (CR-145, proposal 3).

    One meeting is one DAY of this series: the `match` filter has already decided every
    recording here belongs to this series, so two on one day are two captures of one
    session and not two sessions. Exactly one per day is marked `used: True` and the rest
    `used: False` -- marked, never removed, because the second recording being absent from
    the output is the half of the incident that made the choice invisible.

    Order within a day is the preference's, and it is a TOTAL order in every case: a
    `named-speakers` preference puts the named-speaker recordings first and then the
    longest among them, so two named-speaker recordings of one meeting still resolve the
    same way on every run rather than by whichever the archiver happened to write first.
    """
    rows = [r for r in recs if not r.get("note")]
    out = [r for r in recs if r.get("note")]
    named_first = prefer == "named-speakers"
    for day in sorted({r.get("day") for r in rows}):
        group = sorted(
            (r for r in rows if r.get("day") == day),
            key=lambda r: ((0 if has_named_speakers(r) else 1) if named_first else 0,
                           -_duration_seconds(r.get("duration")),
                           str(r.get("id") or "")))
        for i, r in enumerate(group):
            out.append({**r, "used": i == 0})
    return out


def recording_lines(recs: list[dict], prefer: str) -> list[str]:
    """The recordings of this series as markdown lines, the used one marked (proposal 3).

    Written where the detail lives -- the details file on the card layout, the appendix of
    the one page on the list layout -- and not on the card: which capture a transcript came
    from is a fact the close-out needs and not a thing the room talks through.
    """
    chosen = choose_recordings(recs, prefer)
    rows = [r for r in chosen if not r.get("note")]
    if not rows:
        return []
    out = ["## Recordings of this series", "",
           f"Source preference declared: `{prefer}`. A recording marked *not used* is listed"
           " because it exists, not because anything is wrong with it: two captures of one"
           " meeting is the normal case, and the one not used must not vanish.", "",
           "| Day | Recording | Duration | Variant | |", "|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r.get('day', '?')} | {r.get('id') or '?'}"
                   f"{' — ' + str(r['title']) if r.get('title') else ''}"
                   f" | {r.get('duration') or '—'} | {r.get('variant') or '—'}"
                   f" | {'**used**' if r.get('used') else 'not used'} |")
    return out + [""]


DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def round_table(path: Path) -> dict[str, str]:
    """A note's round table as {name (lower): track}, first row per name wins.

    The CR-084 shape `| <person> | <track> | ... |`. A `(carried)` mark is stripped --
    including the italic `*(carried)*` the agenda writes, which a note that kept the
    prefill carries verbatim and which used to survive as a stray `*` -- so
    a note that kept the agenda's prefill reads as the value it confirmed. Best effort:
    an unreadable note is an empty table, never a stopped agenda."""
    out: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip().strip("*") for c in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and cells[1] and not set(cells[0]) <= set("- "):
                if cells[0].lower() not in ("", "owed into today") and "---" not in cells[1]:
                    out.setdefault(cells[0].lower(), re.sub(r"\s*\*?\(carried\)\*?\s*", "", cells[1]).strip())
    except OSError:
        pass
    return out


# CR-149: the declared states of a milestone. `confirmed` is the only one that asserts a
# commitment, which is why proposal 3 makes it the one that has to name where it came from;
# the rest say plainly that the date is not yet anybody's word.
MILESTONE_STATES = ("confirmed", "proposed", "target", "done")
MILESTONE_DEFAULT_STATE = "proposed"


def as_date(value):
    """A `YYYY-MM-DD` value (or a date) as a `datetime.date`, or None where it is neither.

    One reader for the config's dates. The milestone block had its own copy inside
    `config_checks`, and CR-149 gives three renderers the same parsing job, so a date the
    card sorts by and a date the validation complains about can no longer disagree.
    """
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def milestones(cf: dict) -> list[dict]:
    """CR-149: the project's milestones, resolved and sorted by date, earliest first.

    The shape every reader gets, whatever the config declared. `milestones:` is the list;
    a lone `milestone:` (CR-107) reads as a list of ONE, which is what keeps this additive --
    the card, the chat post and `config_checks` all came through here, and a config that
    declares only `milestone:` renders byte for byte as before. Where both are declared the
    list wins and `milestone:` is appended if the list does not already hold its date, so a
    project adding `milestones:` beside an existing block loses nothing.

    Each entry keeps its declared keys and gains three resolved ones:

    - `_date`: the parsed `date:`, or None where none is declared or it is malformed.
    - `_state`: the state as it is SHOWN. Proposal 3: `confirmed` without a source is not a
      commitment anybody can trace, so it is shown as `proposed` -- the validation says why
      (`config_checks`). An undeclared or unknown state reads as `proposed` too: the state
      exists to tell a commitment from a proposal, and the safe reading of silence is that
      nothing has been committed.
    - `_sourced`: whether the entry names a `source:` -- a decision id, a plan section or a
      named confirmer. Carried so the renderers need not re-derive the demotion.

    Dateless entries sort last: an entry still waiting for a date cannot be placed in the
    sequence, and putting it first would read as the next thing due.
    """
    raw = cf.get("milestones")
    if isinstance(raw, dict):            # a single mapping written under the plural key
        raw = [raw]
    entries = [m for m in (raw or []) if isinstance(m, dict)]
    lone = cf.get("milestone")
    if isinstance(lone, dict) and lone:
        # The duplicate is suppressed only where there is a date to compare. An undated
        # `milestone:` beside an undated list entry is None == None, which read as the
        # same milestone and DROPPED the declared block from the list, the card, the post
        # and the validation -- a commitment vanishing is the opposite of what CR-149 is
        # for, so a dateless lone block is always kept and the two dateless entries are
        # shown as the two things that still need a date.
        if not (lone.get("date") and any(m.get("date") == lone.get("date") for m in entries)):
            entries.append(lone)
    out = []
    for m in entries:
        e = dict(m)
        e["_date"] = as_date(m.get("date"))
        e["_sourced"] = bool(str(m.get("source") or "").strip())
        state = str(m.get("state") or MILESTONE_DEFAULT_STATE).strip().lower()
        if state not in MILESTONE_STATES:
            state = MILESTONE_DEFAULT_STATE
        if state == "confirmed" and not e["_sourced"]:
            state = MILESTONE_DEFAULT_STATE
        e["_state"] = state
        out.append(e)
    out.sort(key=lambda e: (e["_date"] is None, e["_date"] or datetime.date.max,
                            str(e.get("name") or "")))
    return out


def unreadable_milestones(cf: dict) -> list[str]:
    """CR-149: the `milestones:` items `milestones()` could not read, as written.

    `milestones()` is best effort -- a list item that is not a mapping is skipped so the
    readable entries still render -- but a skipped item is a milestone the author DECLARED
    and the card, the post and the timeline then do not mention. `- Go/no-go` instead of
    `- name: Go/no-go` is the slip, and silence about it is the disappearance this CR
    exists to prevent, so `config_checks` reports every one of them.
    """
    raw = cf.get("milestones")
    if isinstance(raw, dict) or not isinstance(raw, list):
        return []
    return [str(m) for m in raw if not isinstance(m, dict)]


def next_milestone(ms: list[dict], day: datetime.date) -> dict | None:
    """The earliest entry dated after `day`, or None where none is.

    Proposal 2's *next date after today*: the one line that carries the days left. A `done`
    entry is still eligible -- a done date in the future is a finding, not something to hide
    from the reader who has to ask about it.
    """
    return next((e for e in ms if e["_date"] and e["_date"] > day), None)


def timeline_line(ms: list[dict]) -> str:
    """Proposal 5: the dated sequence on one line, for a reader who wants it at a glance.

    Dates only, in order, with the undated entries left out -- a sequence is what this line
    is for, and an entry with no date has no place in one.
    """
    return " -> ".join(e["_date"].isoformat() for e in ms if e["_date"])


def undated_phrase(e: dict) -> str:
    """CR-149: what a list line says where the entry has no date the generator can read.

    Two different states, and the surfaces used to say the same thing about both: an entry
    with no `date:` at all, and an entry whose declared date does not parse. The second is
    not *date not set* -- a date WAS set, and printing it as unset tells the reader the
    opposite of what the config says. So the unreadable value is shown as written, and
    `config_checks` asks for `YYYY-MM-DD`.
    """
    if e.get("date"):
        return f"{e['date']} (unreadable date)"
    return "date not set" + (f", decide by {e['decide_by']}" if e.get("decide_by") else "")


CONFIG_MARKER = "<!-- CONFIG-REVIEW:"


def config_checks(cf: dict, hist: list, day: datetime.date, mv_x: dict | None) -> list[str]:
    """CR-119: what a script can tell about whether the config still describes the project.

    Each finding is one plain sentence. Nothing is changed: the config is a person's to edit,
    and prepare proposes the edit out loud before generating.
    """
    out = []
    # CR-149: the list, resolved once. Each entry is checked as the single milestone always
    # was, so a config declaring only `milestone:` produces exactly the findings it did; an
    # entry is NAMED in the message only where there is more than one, because the wording
    # of the one-milestone findings is what the card and the skill doc already quote.
    ms_all = milestones(cf)
    _d = as_date
    many = len(ms_all) > 1
    for ms in ms_all:
        at = f" ({ms.get('name')})" if many and ms.get("name") else ""
        declared = str(ms.get("state") or "").strip().lower()
        # A `done` date in the past is the normal case, not a slip: proposal 4's finding is
        # the reverse of it (a `done` date in the FUTURE), checked below.
        if ms["_date"] and ms["_date"] < day and ms["_state"] != "done":
            # Proposal 4: a date that went by without being confirmed or moved. A DECLARED
            # proposal gets the sharper wording -- that is the reading the state was added
            # to make possible -- and the two readings of one passed date stay one finding.
            # An entry that declares no state keeps the CR-107 sentence unchanged: it has
            # said nothing about being a proposal, and the card has quoted that wording
            # since CR-119.
            out.append(f"milestone date {ms['date']}{at} was proposed and has passed without being "
                       "confirmed or moved (CR-149)"
                       if declared in ("proposed", "confirmed") and ms["_state"] == MILESTONE_DEFAULT_STATE
                       else f"milestone date {ms['date']}{at} has passed: move it, or declare "
                            "the next milestone")
        elif ms.get("date") and not ms["_date"]:
            # CR-149: a date WAS declared and `as_date` could not read it. Without this
            # branch the card printed "*date not set*" and the post "date not set" -- a
            # false statement about a config that says otherwise, and the one reading the
            # reader cannot correct. So the finding names what was written and asks for
            # the form, and never calls a declared date unset.
            out.append(f"milestone date{at} is not a date the generator can read "
                       f"({ms['date']}): write it as YYYY-MM-DD (CR-149)")
        elif not ms.get("date") and ms.get("decide_by") and _d(ms["decide_by"]) and _d(ms["decide_by"]) < day:
            out.append(f"milestone{at} has no date and its decide-by ({ms['decide_by']}) has passed")
        # CR-127: a date nobody can trace is a date that cannot be shown to have slipped.
        if ms.get("date") and not ms.get("set_on"):
            out.append(f"milestone date{at} has no `set_on`: when was it set? (CR-127)")
        # Proposal 3: `confirmed` asserts a commitment, and a commitment nobody signed is
        # a proposal. `milestones()` has already demoted it; this says so out loud.
        if str(ms.get("state") or "").strip().lower() == "confirmed" and not ms["_sourced"]:
            out.append(f"milestone{at} is marked `confirmed` with no `source`: shown as "
                       "`proposed` until a decision id or a named confirmer says otherwise (CR-149)")
        if ms["_state"] == "done" and ms["_date"] and ms["_date"] > day:
            out.append(f"milestone{at} is marked `done` with a date in the future ({ms['date']}) (CR-149)")
        hist_ = ms.get("history")
        if hist_ and not isinstance(hist_, list):
            out.append(f"milestone{at} `history` must be a list of entries (CR-127)")
        else:
            for i, h in enumerate(hist_ or [], 1):
                miss = [k for k in ("reason", "source") if not (isinstance(h, dict) and h.get(k))]
                if miss:
                    out.append(f"milestone{at} history entry {i} has no "
                               + " or ".join(f"`{k}`" for k in miss))
    # CR-149: an item in `milestones:` that is not a mapping. Dropped from every surface
    # by `milestones()`, so without this finding a declared milestone disappears in
    # silence -- `- Go/no-go` where `- name: Go/no-go` was meant.
    for item in unreadable_milestones(cf):
        out.append(f"`milestones:` entry `{item}` is not a mapping: write it as "
                   "`- name: ...` with its `date:`, or it is left off the card (CR-149)")
    # Proposal 4: two entries on one date. Reported per date, once, naming both: the
    # sequence the card renders cannot say which of them comes first.
    for when in sorted({e["_date"] for e in ms_all if e["_date"]}):
        same = [e for e in ms_all if e["_date"] == when]
        if len(same) > 1:
            out.append(f"{len(same)} milestones on the same date ({when.isoformat()}): "
                       + ", ".join(str(e.get("name") or "unnamed") for e in same) + " (CR-149)")
    # CR-148: compact is a card variant -- its post leads with the milestone list -- so
    # a compact project with no milestone has the same nothing to run toward.
    if not ms_all and is_card(cf):
        out.append("card layout without a milestone: the card has nothing to run toward")
    # CR-121, proposal 3: the config and the project contradicting each other about
    # releases. Report only -- both readings are legitimate, and which one is right is
    # the team's to say, not the generator's.
    card_cfg = cf.get("card") if isinstance(cf.get("card"), dict) else {}
    declared_labels = [r for r in ((cf.get("ext") or {}).get("repos") or [])
                       if isinstance(r, dict) and (r.get("labels") or {})]
    if is_card(cf) and (card_cfg or {}).get("release_blockers") is None and not declared_labels:
        kinds_ = {str(e.get("kind") or "").strip().lower() for e in ms_all} - {""}
        if kinds_ and "release" not in kinds_:
            out.append("card layout with no repo `labels:` and a milestone kind of "
                       + ", ".join(sorted(kinds_))
                       + ": nothing here ships a release — consider `card: {release_blockers: false}` (CR-121)")
    if (card_cfg or {}).get("release_blockers") is False and ((mv_x or {}).get("top")):
        out.append("`release_blockers: false` with the repo declaring a "
                   f"`{mv_x.get('top')}` label: the config says this project ships no release"
                   " and the repo says it does — one of the two is wrong (CR-121)")
    for lab in ((mv_x or {}).get("missing_labels") or []):
        out.append(f"declared label `{lab}` does not exist in the repo: its counts read as zero")
    for nm, _own, p_, age in ((mv_x or {}).get("reports") or []):
        if p_ is None:
            out.append(f"report '{nm}' declared but not found")
        elif age is not None and age >= 3:
            out.append(f"report '{nm}' is {age} days old: retire the declaration, or ask its owner")
    # CR-150, proposal 3: the owner-only metrics document, declared and not there. Worth
    # one sentence because the declaration is what EXEMPTS a path from the lint: a stale
    # `metrics_document:` silently exempts nothing, and the figures then have no declared
    # home at all. Nothing else is checked about it -- the generator never writes to it,
    # and what a project measures is its own method (CR-150, not in scope).
    if cf.get("metrics_document") and not (mp := metrics_path(cf)).exists():
        out.append(f"`metrics_document: {cf['metrics_document']}` does not exist ({mp.name}):"
                   " the owner-only document the lint exempts is not there (CR-150)")
    # CR-150: the per-person check resolves its subject against the `people:` roster and
    # has nothing to resolve against without one, so it finds nothing. Said ONCE here,
    # where a project is told about its configuration, rather than guessed at per line:
    # the shape a name has is the shape every team and area has, and a check that fell
    # back to it would report `Mobile: 7 PRs merged` as work counted per person.
    #
    # Only where there is history to lint. A series with no notes yet has nothing for the
    # check to read, so a missing roster is not yet a gap -- and saying so would put a
    # CR-150 line in the output of a project that has not held its first session.
    if hist and not roster_names(cf):
        out.append("no `people:` roster: the per-person check (CR-150) finds nothing,"
                   " because a count's subject is resolved against the roster")
    # CR-143, proposal 1: a `pronouns:` value outside the declared three. Reported rather
    # than guessed at: `pronoun_of` answers `they` for it, which is the safe reading, but a
    # config that meant something by the value has said it in a spelling nothing reads, and
    # the person it describes then gets the default silently.
    for p_ in cf.get("people") or []:
        v = str(p_.get("pronouns") or "").strip()
        if v and v.lower() not in PRONOUN_VALUES:
            out.append(f"`pronouns: {v}` for {p_.get('name')} is not one of "
                       + ", ".join(PRONOUN_VALUES)
                       + f": the text defaults to `they` (CR-143)")
    # CR-145: the new declarations, checked against the project. Each one is a key whose
    # bad value falls back to the old behaviour rather than failing -- which is right for
    # the build and wrong for the operator, who then has a declaration that reads as
    # honoured and is not. So the fallback happens AND the finding is reported.
    ext_ = cf.get("ext") or {}
    roster_ = roster_names(cf)
    for c_ in ext_.get("chats") or []:
        if not isinstance(c_, dict):
            continue
        nm_ = c_.get("name") or c_.get("id") or "(unnamed chat)"
        k_ = str(c_.get("kind") or "").strip().lower()
        if k_ and k_ not in CHAT_KINDS:
            out.append(f"`kind: {c_.get('kind')}` on chat {nm_} is not one of "
                       + ", ".join(CHAT_KINDS)
                       + f": it is read as `{CHAT_DEFAULT_KIND}` (CR-145)")
        elif k_ == "direct":
            # A direct chat with no person is readable and unattributable: the output can
            # say a reply arrived and not whose, which is the one fact the measured
            # incident needed (four replies, four people who owed them).
            who_ = str(c_.get("person") or "").strip()
            if not who_:
                out.append(f"chat {nm_} is `kind: direct` with no `person:`:"
                           " the source line cannot say whose reply it is (CR-145)")
            elif roster_ and who_.lower() not in roster_:
                out.append(f"`person: {who_}` on chat {nm_} is in no `people:` entry"
                           " (name, alias or first name): the chat is still read, but the"
                           " name is not the roster's (CR-145)")
    trd_ = ext_.get("transcripts") or {}
    pref_ = str(trd_.get("prefer") or "").strip()
    if pref_ and pref_.lower() not in RECORDING_PREFERENCES:
        out.append(f"`transcripts.prefer: {pref_}` is not one of "
                   + ", ".join(RECORDING_PREFERENCES)
                   + f": the source falls back to `{RECORDING_DEFAULT_PREFERENCE}` (CR-145)")
    # CR-145, defect pass: the flag is read through `flag_value`, so a quoted `"true"` or a
    # `1` is the declaration it looks like -- and a value that is NEITHER a yes nor a no is
    # reported, as an unknown `kind:` or `prefer:` is, instead of falling through to the
    # not-connected branch and leaving the operator with the old behaviour and no reason.
    conn_ = trd_.get("connected")
    if conn_ is not None and flag_value(conn_) is None:
        out.append(f"`transcripts.connected: {conn_}` is not a yes or a no:"
                   " the store is read as not connected, so the check reports it as"
                   " not checked (CR-145)")
    elif flag_value(conn_) is True and not trd_.get("store"):
        out.append("`transcripts.connected: true` with no `store:`: nothing is named to"
                   " connect to, so the check still reports the store as not checked (CR-145)")
    rounds = [round_table(n) for _d_, n in hist[-3:]]
    if rounds and all(rounds):
        absent = [p_["name"] for p_ in cf.get("people") or []
                  if not any(k.lower() in r for r in rounds for k in [p_["name"]] + list(p_.get("aliases") or []))]
        if absent:
            out.append("on the roster, not in the last three rounds: " + ", ".join(absent)
                       + " (absent, or no longer in this meeting?)")
    if hist:
        sec = SECTION.search(hist[-1][1].read_text(encoding="utf-8"))
        unknown = sorted({k for k, _l in KIND_RE.findall(sec.group(1))} - set(KINDS)) if sec else []
        if unknown:
            out.append("unknown kind(s) in the last note: " + ", ".join(f"[{k}]" for k in unknown))
    dfs = definitions(cf)
    if dfs["unmarked"]:
        out.append(f"{dfs['unmarked']} term(s) in {dfs['definitions'].name} without a status")
    return out


def declared_track(value: str, tracks: list[str]) -> str | None:
    """The declared track a round cell names, in its declared spelling -- or None.

    CR-090: only a declared track is carried or counted. An area or free text in the
    cell is dropped, which keeps CR-084's fix (areas never under a Track heading)."""
    v = (value or "").strip().lower()
    return next((t for t in tracks if t.lower() == v), None)


def weekdays(days) -> set[int]:
    """Declared cadence days as weekday numbers, full name or three letters.

    CR-139: `meets: [mon, tue]` is the shape an operator writes; `schedule_days`
    has always been read as full names. Both resolve here, so the alias needs no
    second spelling rule and an unrecognised entry is ignored exactly as before --
    a typo must not silently empty the schedule and turn every day into a meeting day.
    """
    out = set()
    for x in days or []:
        v = str(x).strip().lower()
        i = next((n for n, d in enumerate(DAYS) if d == v or (len(v) == 3 and d.startswith(v))), None)
        if i is not None:
            out.add(i)
    return out


def next_session(yymmdd: str, days: list[str] | None) -> str:
    """The next day this series actually meets.

    Not every standup is daily. A twice-weekly Monday/Thursday series generating a
    Tuesday agenda produces a file nobody opens, and the carry-forward chain then
    looks broken on Thursday because the Tuesday file is the newest thing with no
    note behind it. Falls back to the next weekday where no schedule is declared.
    """
    want = weekdays(days)
    d = datetime.datetime.strptime(yymmdd, "%y%m%d").date() + datetime.timedelta(days=1)
    for _ in range(14):
        if (d.weekday() in want) if want else (d.weekday() <= 4):
            return d.strftime("%y%m%d")
        d += datetime.timedelta(days=1)
    return d.strftime("%y%m%d")


def default_target(now: datetime.date, hist: list[tuple[str, Path]] | None = None,
                   days: list[str] | None = None) -> str:
    """CR-139: the date an agenda is for when the caller does not say.

    TODAY, unless today already has a note -- then the NEXT session the series meets.
    The two cases are the loop's two runs, and they want different dates:

    * the morning run. Nothing has been written for today, the session is ahead, and
      the agenda is for it. The old default (`next_session` after the newest note) got
      this wrong after a day nobody met: no note was written for the skipped day, so
      it built for the skipped day and then stamped its own output STALE.
    * the same-day close-out (SKILL.md, *After the meeting, the same day*). The summary
      for today has just been written, and the next thing wanted is the NEXT session's
      agenda. A note for today is exactly the signal that the close-out has happened,
      so it is read as one rather than refused: refusing it would break this repo's own
      documented sequence, which runs the generator with no `--date` after step 5.

    `next_session` stays the answer to its own question -- which day the series next
    meets, also asked by `project_brief` -- and is reused here rather than re-derived,
    so a cadence declared once is honoured in both.
    """
    today = now.strftime("%y%m%d")
    if any(d_ == today for d_, _p in hist or []):
        return next_session(today, days)
    return today


def refuse_target(target: str, now: datetime.date, hist: list[tuple[str, Path]],
                  explicit: bool) -> str | None:
    """CR-139: why this date may not be built for, or None.

    One refusal beyond a malformed date, and it is not the pre-existing output-file
    guard (which says only that this agenda was already generated): a date earlier
    than today that nobody typed. The day has gone, so an agenda for it is read after
    the meeting it was meant to prepare. An explicit `--date` is the caller saying
    they mean it, so the refusal only catches a date the default produced.

    A date that already has a note is NOT refused. The CR's contract is that an
    explicit `--date` behaves as before, and before this CR such a date built -- a
    rebuild after deleting the agenda is the ordinary way to correct one. With no
    `--date` the case cannot arise: `default_target` reads a note for today as the
    close-out having happened and moves to the next session, so there is nothing
    left here to refuse.

    `hist` is still read, for the malformed-date path's ordering and so a caller
    passing history keeps one signature across both functions.
    """
    try:
        day = datetime.datetime.strptime(target, "%y%m%d").date()
    except ValueError:
        return f"--date {target!r} is not a YYMMDD date"
    if day < now and not explicit:
        return (f"would build for {target}, which is earlier than today ({now:%y%m%d}) — "
                f"pass --date {target} if you mean to build for a day that has gone")
    return None


def base_line(note: str, last_date: str, skips: list[tuple[datetime.date, str]],
              day: datetime.date) -> str:
    """CR-139: `Base: <note> (last meeting held <date>; skipped: <dates>)`.

    The agenda already named the note it was built from further down, in the sources
    block -- but a reader working out why a session count did not move has to know
    which days did not count, and that fact lived nowhere. It goes in the header, so
    it is read before the carried list rather than after it.

    Only skip days between the base note and this agenda are listed: a skip from
    three months ago says nothing about this agenda, and a header that lists it reads
    as though it did.
    """
    held = datetime.datetime.strptime(last_date, "%y%m%d").date()
    inside = [(d, why) for d, why in skips if held < d <= day]
    tail = ""
    if inside:
        tail = "; skipped: " + ", ".join(f"{d:%y%m%d} ({why})" for d, why in inside)
    return f"Base: {note} (last meeting held {held:%y%m%d}{tail})"


def skip_dates(cf: dict) -> list[tuple[datetime.date, str]]:
    """CR-139: the days this series did not meet, each with its one-word reason.

    Two shapes, because a holiday is one day and leave is a stretch of them:

        - date: 261020
          reason: holiday-in
        - from: 261224
          to: 261226
          reason: leave

    A bare `261020` is accepted too -- an operator adding one day should not have to
    write a mapping -- and then has no reason, which prints as `no reason given`
    rather than being dropped. The list is OPERATOR-WRITTEN (the skill does not know
    which days a team is away), so an unparseable entry is skipped and the rest are
    kept: one bad line must not take the whole skip list down and silently restore
    the ageing it was written to stop.

    `skip_dates: 261020` -- one day written without the dash, which YAML reads as a
    scalar int rather than a list -- is read as that one day. It is the natural typo
    for an operator declaring a single day, it says unambiguously what was meant, and
    iterating it raised a TypeError and a raw traceback instead of building the agenda.
    """
    out: dict[datetime.date, str] = {}

    def _d(v):
        try:
            return datetime.datetime.strptime(str(v).strip(), "%y%m%d").date()
        except (TypeError, ValueError):
            return None

    raw = cf.get("skip_dates") or []
    # A str is iterable, so a bare `skip_dates: 261020` or a quoted one would
    # otherwise be walked character by character and yield nothing.
    if isinstance(raw, (str, int, dict)):
        raw = [raw]
    elif not isinstance(raw, (list, tuple, set)):
        return []
    for e in raw:
        if isinstance(e, dict):
            why = str(e.get("reason") or "").strip() or "no reason given"
            # `from:` alone and `to:` alone are the same declaration of one day read
            # from either end, so both resolve to that day: accepting one and
            # silently dropping the other restores the ageing on exactly the day the
            # operator wrote a reason for.
            ends = [x for x in (_d(e.get("from")), _d(e.get("to")), _d(e.get("date"))) if x]
            if not ends:
                continue
            a_, b_ = min(ends), max(ends)
            d = a_
            while d <= b_:
                out.setdefault(d, why)
                d += datetime.timedelta(days=1)
        elif (a_ := _d(e)) is not None:
            out.setdefault(a_, "no reason given")
    return sorted(out.items())


def skipped_between(skips: list[tuple[datetime.date, str]],
                    first: datetime.date, last: datetime.date) -> int:
    """How many declared skip days fall in `(first, last]`.

    CR-139: a skipped day is not a missing note, so nothing may age across it. The
    half-open interval is what makes that true at both ends -- the day an item was
    first carried is a day the series DID meet, and a skip on the target day itself
    still removes that day from the count."""
    return sum(1 for d, _why in skips if first < d <= last)


# ---- CR-140: the pre-flight -------------------------------------------------
# The full build takes about three minutes and exceeds the default foreground
# command limit, so a check that needs the build to find a missing source finds it
# three minutes late. `--check` answers the same question in seconds: is every
# declared source ready, and if not, which one and why.
#
# It reads the cheap half of what the build reads -- the fetch records, the local
# note and the archives' own status -- plus one status call per declared report.
# None of the expensive readers (`from_chat`, `from_repo`, `from_jira`) is called:
# their answer is WHAT MOVED, which a pre-flight does not ask.
READY, STALE, FAILED, MISSING, UNCHECKED = "ready", "stale", "failed", "missing", "not checked"
# CR-151, proposal 6: a source the reports name and the config does not hold. Its own
# state because it is the opposite question from the others: not *is the declared source
# there* but *is a source missing from the declaration*, which is why it stays out of
# `CHECK_BAD` below.
UNDECLARED = "undeclared"
# The states that make the exit code non-zero. `failed` is among them: a fetch that
# failed is a source that is not there, whatever the archive still holds.
CHECK_BAD = (STALE, FAILED, MISSING)
# CR-151, proposal 6: days a report must name an undeclared repository on before the
# pre-flight says so. One reader, in `propose_repos`, so the warning and the proposal
# cannot disagree about the same repository.
UNDECLARED_DAYS = 3
# Days before a dated report counts as stale. Matches the config_checks threshold
# (CR-119) so the two cannot disagree about the same report.
REPORT_STALE_DAYS = 3


def check_rows(cf: dict, md: Path, hist: list[tuple[str, Path]],
               today: datetime.date | None = None,
               reports=None) -> list[tuple[str, str, str, str]]:
    """One (source, state, time, detail) row per declared source, in reading order.

    `reports` is injected by the caller so the one network-touching part of the
    check -- a report's status call -- can be left out or supplied by a test; None
    means read it here.
    """
    today = today or datetime.date.today()
    rows: list[tuple[str, str, str, str]] = []
    ext = cf.get("ext") or {}
    after = since(hist[-1][0]) if hist else today

    # The archives, one row each, from the fetch record alone (CR-088). `fetch_ok`
    # says the last attempt worked; `fetched_since` says it worked recently enough
    # for the note. A source can be ok and stale, which is the whole point of the
    # two questions being separate.
    for label, sub, declared in (("chat fetch", ".teamschats", ext.get("chats")),
                                 ("repository fetch", ".githubmeta", ext.get("repos")),
                                 ("ticket fetch", ".jirameta", ext.get("jira"))):
        if not declared:
            continue
        rec = fetch_record(archive_dir(cf, sub))
        if rec is None:
            rows.append((label, MISSING, "—", f"no fetch recorded in {sub}/"))
        elif not fetch_ok(rec):
            rows.append((label, FAILED, _stamp(_when(rec.get("last_success")), today),
                         fetch_status(rec, today)))
        elif not fetched_since(rec, after):
            rows.append((label, STALE, _stamp(_when(rec.get("last_success")), today),
                         f"last success predates {hist[-1][1].name if hist else 'the note'}"))
        else:
            rows.append((label, READY, _stamp(_when(rec.get("last_success")), today),
                         str(rec.get("result"))))

    # Every declared report, repo-kept and vault-kept alike. A report with no age
    # is one whose date could not be read -- reported as missing, never as fresh.
    if reports is None:
        reports, problems = _check_reports(cf, today)
    else:
        problems = []
    for nm, _own, path_, age in reports:
        if path_ is None:
            # CR-140: a rename reads as "config stale", not "source missing". The
            # suggestion decides nothing -- the report is still missing -- but it is
            # the difference between looking for a renamed folder and looking for a
            # report that was never written.
            rows.append((f"report: {nm}", MISSING, "—",
                         "declared, not found" + (f" · config stale? {hint} exists"
                                                  if (hint := _renamed_hint(cf, nm)) else "")))
        elif age is None:
            rows.append((f"report: {nm}", MISSING, "—", f"{path_}: no date in the name"))
        elif age >= REPORT_STALE_DAYS:
            rows.append((f"report: {nm}", STALE, f"{age}d old", str(path_)))
        else:
            rows.append((f"report: {nm}", READY, "today" if age == 0 else f"{age}d old", str(path_)))
    for nm, detail in problems:
        rows.append((f"report: {nm}", FAILED, "—", detail))

    # The previous note. Absent, there is nothing to carry from and the build stops
    # anyway -- but it stops three minutes in, which is what this exists to avoid.
    if not hist:
        rows.append(("previous note", MISSING, "—",
                     f"no YYMMDD-{cf['note_suffix']}.md in {md.name}/"))
    else:
        last_date, last = hist[-1]
        if not has_section(last):
            rows.append(("previous note", MISSING, last_date,
                         f"{last.name} has no '## Carried forward' section — close-out not written"))
        else:
            rows.append(("previous note", READY, last_date, last.name))

    # The recording store is CHECKED or NOT CHECKED, never ready or stale: the
    # script does not fetch it (CR-087), so the honest answer is whether anything
    # looked. Declaring no archive is not a failure -- prepare checks the store by
    # hand -- so NOT CHECKED leaves the exit code alone.
    #
    # CR-140: a DECLARED archive is resolved before the row says "checked". Printing
    # "checked" from the declaration alone let a typo'd or deleted archive read as a
    # source that was looked at, which is the opposite of what this row is for: the
    # archive reader finds nothing there and reports no session, and the row agreed.
    # A declaration pointing nowhere is a source that is not there, so it is missing.
    trd = ext.get("transcripts") or {}
    if trd:
        arch = trd.get("archive")
        root_ = Path(cf["_root"])
        found = next((p_ / arch for p_ in (root_, *root_.parents)
                      if (p_ / arch).is_dir()), None) if arch else None
        if arch and found is None:
            rows.append(("recording source", MISSING, "—",
                         f"declared archive not found: {arch}"))
        elif arch:
            rows.append(("recording source", "checked", "—", str(arch)))
        elif store_connected(cf):
            # CR-145, proposal 4: a store the close-out step can read ITSELF is a source
            # that something looked at, so the row says CHECKED. Before this, the only way
            # to earn `checked` was an archive written by an archiver, and a project whose
            # close-out pulls the transcript directly read as `not checked` every morning
            # -- a permanent "nobody looked" on a source somebody does look at, which is
            # how a row stops being read at all.
            #
            # It stays OUTSIDE `CHECK_BAD`, like every other recording row: this script
            # never fetches (CR-087), so the row reports what the DECLARATION entitles a
            # reader to assume and never claims to have reached a store.
            rows.append(("recording source", "checked", "—",
                         f"{trd.get('store') or 'declared'} — connected;"
                         " the close-out step pulls the transcript (CR-145)"))
        else:
            rows.append(("recording source", UNCHECKED, "—",
                         str(trd.get("store") or "declared")
                         + " — no archive; prepare checks by hand (CR-117)"))

    # CR-151, proposal 6: a repository the status reports name day after day that the
    # project does not declare. Measured, a project declared one repository and the
    # release depended on at least seven others; every reader downstream -- the agenda,
    # the movement block, the digest -- therefore read a fraction of the work and read as
    # complete. The reports said so all along, so the gap is one a check can see.
    #
    # UNDECLARED, not `stale` or `missing`: the sources that ARE declared are all there,
    # so the exit code is left alone (`CHECK_BAD` does not hold it). The finding is that
    # the config is short of a source, which is a judgement the operator makes with
    # `propose_repos.py` -- and a pre-flight that refused the build over it would be a
    # script blocking a morning on a declaration only a person can write.
    for nm, days in _undeclared_repos(cf, today):
        rows.append((f"repository: {nm}", UNDECLARED, f"{days}d named",
                     "named by the reports, not declared — propose_repos.py --dir <project>/meetings"))
    return rows


def _undeclared_repos(cf: dict, today: datetime.date) -> list[tuple[str, int]]:
    """CR-151's undeclared repositories, read from the declared reports -- or nothing.

    Imported here rather than at module scope, as `build_movement` is: the helper is an
    optional companion and a project with no declared report must still get a check.
    One window reader, in `propose_repos`, so the warning and the proposal cannot
    disagree about how many days a repository was named on.
    """
    try:
        import propose_repos
        start = propose_repos.working_days_back(today, 14)
        counts, _read, _problems = propose_repos.count_window(cf, start, today)
        return propose_repos.undeclared(cf, counts, UNDECLARED_DAYS)
    except Exception:
        return []                  # best effort, as everywhere else in this pipeline


def _renamed_hint(cf: dict, name: str) -> str | None:
    """CR-140: for a declared report that is missing, a sibling directory that looks
    like the same series renamed -- matched back to the declaration by its name.

    Vault reports only: a repo report's path is in the repository, where this script
    has no listing to compare against and a guess would be invented rather than seen.
    """
    for r in ((cf.get("ext") or {}).get("vault_reports") or []):
        if not (isinstance(r, dict) and r.get("dir")):
            continue
        if (r.get("name") or r["dir"]) != name:
            continue
        try:
            import build_movement
            return build_movement.renamed_to(Path(cf["_root"]), r["dir"])
        except Exception:
            return None            # best effort, as everywhere else in this pipeline
    return None


def _check_reports(cf: dict, today: datetime.date):
    """The report states for `--check`, or an empty list when they cannot be read.

    Imported here rather than at module scope because `build_movement` is itself an
    optional companion: a project with no declared report must still get a check.
    """
    try:
        import build_movement
        return build_movement.report_states(cf, today)
    except Exception as e:
        return [], [("declared reports", f"not read — {type(e).__name__}: {str(e).splitlines()[0][:80]}")]


def check_table(rows: list[tuple[str, str, str, str]]) -> str:
    """The rows as one fixed-width table -- the same shape as the sources block."""
    w = max([len(r[0]) for r in rows] + [6])
    out = [f"  {'Source'.ljust(w)}  {'State'.ljust(11)}  Time",
           f"  {'-' * w}  {'-' * 11}  {'-' * 12}"]
    for name, state, when, detail in rows:
        out.append(f"  {name.ljust(w)}  {state.ljust(11)}  {when:<12}  {detail}".rstrip())
    bad = [r for r in rows if r[1] in CHECK_BAD]
    out += ["", f"  {len(bad)} of {len(rows)} source(s) not ready"
            if bad else f"  all {len(rows)} source(s) ready"]
    return "\n".join(out)


def run_check(md: Path, cf: dict, hist: list[tuple[str, Path]]) -> int:
    rows = check_rows(cf, md, hist)
    print(check_table(rows))
    return 1 if any(r[1] in CHECK_BAD for r in rows) else 0


def failed_fetches(cf: dict, recs: dict, today: datetime.date) -> list[str]:
    """CR-140: the fetches that failed, named for the agenda's own header.

    A failed fetch was only ever in the fetch's own file and in one line of the
    sources block. The repo-detail section meanwhile used the last good data and
    read as current, so the agenda looked complete -- which is how the same fetch
    failed twice in one morning without the room hearing about it.

    **CR-145, proposal 2: each line also says WHEN the data it left behind is from.**
    CR-140's line named the failure and said the sections below hold the last good data,
    which is half the answer: a reader who cannot see the age of that data has no way to
    judge whether reading on is safe. Measured, a fetch failed for a morning and the
    repository section used older data without saying so -- so the age comes from the
    SAME record as the failure (`last_success`), and a record with no successful fetch in
    it says that instead of implying a time nobody has. One line, extended; a second
    header line about the same fetch would be two statements for one fact.
    """
    ext = cf.get("ext") or {}
    out = []
    for label, sub, declared in (("chat", ".teamschats", ext.get("chats")),
                                 ("repository", ".githubmeta", ext.get("repos")),
                                 ("tickets", ".jirameta", ext.get("jira"))):
        rec = recs.get(sub)
        if declared and rec is not None and not fetch_ok(rec):
            when = _when(rec.get("last_success"))
            age = f"data is from {_stamp(when, today)}" if when is not None \
                else "no successful fetch on record"
            out.append(f"{label}: {age}; {fetch_status(rec, today)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="the meetings folder")
    ap.add_argument("--date", help="YYMMDD; CR-139: default is TODAY, or the next session when today "
                                   "already has a note (the close-out has happened). A date in the "
                                   "past is refused unless --date names it")
    ap.add_argument("--recorded", metavar="YYMMDD[,id...]",
                    help="CR-087: a recording of this series the caller already found. "
                         "The script never fetches; this is how a session that has looked tells it")
    ap.add_argument("--skip-unprocessed", action="store_true",
                    help="CR-087: build anyway, over a session that was recorded and never written "
                         "up. Skipping is then a decision on the record, not an accident")
    ap.add_argument("--check", action="store_true",
                    help="CR-140: print one table of source states and exit non-zero on any stale "
                         "or missing source. Seconds, not the full build's minutes: no repository "
                         "read beyond one status call per declared report")
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
    # CR-140: the pre-flight runs BEFORE the no-note exit and before the target-date
    # refusals. A check whose own preconditions can refuse it cannot be what a
    # scheduler runs: a missing note is a row in the table, not a reason to say
    # nothing about the other sources.
    if a.check:
        sys.exit(run_check(md, cf, hist))
    if not hist:
        sys.exit(f"no YYMMDD-{cf['note_suffix']}.md in {md}")

    last_date, last = hist[-1]
    # CR-139: the default is TODAY, not the next session after the last note. The old
    # default is only right when the series meets every scheduled day and every
    # meeting is written up the same day; on the morning after a day nobody met, it
    # built an agenda for the SKIPPED day and the generator then stamped its own
    # output STALE -- the right warning on the wrong file. Once today HAS a note the
    # close-out has happened and the next session is what is wanted, which is the
    # same-day sequence in SKILL.md and the one case the old default got right.
    now = datetime.date.today()
    target = a.date or default_target(now, hist, cf.get("schedule_days"))
    if (why := refuse_target(target, now, hist, bool(a.date))):
        sys.exit(why)
    day = datetime.datetime.strptime(target, "%y%m%d").date()

    skips = skip_dates(cf)

    def age(first: str | None) -> int:
        """Days an item has carried, SESSIONS not calendar days (CR-139).

        A day nobody met is not a day an item survived, so declared skip days are
        taken out of the count. Anchored on the target `day`, not on the real today:
        with the default that is the same date, and for an explicit `--date` it keeps
        the age measured against the meeting the agenda is for -- which is what the
        elapsed-days escalation threshold asks about.
        """
        if not first:
            return 0
        f_ = datetime.datetime.strptime(first, "%y%m%d").date()
        return max(0, (day - f_).days - skipped_between(skips, f_, day))

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
    # CR-145, proposal 3: the declared preference decides which capture of a day is the
    # source, and BOTH are named. The caller's next step is to process one of them, so
    # the stop message is the first place that has to say which -- and that the other
    # exists, which is what the measured incident never said anywhere.
    prefer = recording_preference(cf)
    unprocessed = choose_recordings(unprocessed, prefer)
    if unprocessed and not a.skip_unprocessed:
        lines = ["", f"  A session appears to have been recorded after {last.name} and never written up:", ""]
        for r in unprocessed:
            if r.get("note"):
                lines.append(f"    {r['note']}")
            else:
                bits = [r.get("id", "?"), r.get("title", ""), r.get("duration", ""), r.get("variant", "")]
                lines.append(f"    {r['day']}  " + "  ".join(str(b) for b in bits if b)
                             + ("   <- the source (prefer: " + prefer + ")" if r.get("used")
                                else "   (also recorded, not the source)"))
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
    # CR-141: the matcher now only answers about lines that name an identifier. Which
    # lines it had nothing to go on for is printed too -- in the details, never on the
    # card -- because an agenda with no markers otherwise reads as "nothing moved".
    # And a ticket that only reached a fixed state is a state change, not a close, so
    # the two verdicts are reconciled before either is printed or acted on: *waiting
    # for a test* wins and the item stays carried.
    unchecked = without_identifier(raw_items)
    fixed_rows = state_changed(raw_items, jira)
    closed_hits = reconcile_closed(closed_hits, fixed_rows)
    # CR-147: the same carried lines, re-read off their own source, acting only on a
    # CERTAIN close -- a closed issue, a merged PR that names the id, a done ticket.
    # `reconcile_closed` applies here too and for the same reason: a line with any
    # built-but-not-accepted key is *fixed, waiting for a test*, never closed, so a
    # state change can no more drop a line than it could mark one.
    certain = reconcile_closed(certainly_closed(raw_items, repo, jira), fixed_rows)
    # Proposal 6: a source whose fetch did not work may not remove anything. The
    # verdicts it produced are held back and named in the header instead.
    blocked = readable_sources(cf, recs, {"repo": repo, "tickets": jira}, now)
    certain, held = drop_closed(certain, blocked)
    certain_keys = {key(l) for l, _r, _h in certain}
    closed_keys = {key(l) for l, _r, _h in closed_hits}
    # CR-107 kept a matched blocker, dependency or decision ON the card, marked, because
    # the matcher was a word heuristic: a false hit would have silently dropped the one
    # thing the room most needs to see, and marking it cost a glance. CR-141 replaced the
    # heuristic with explicit identifiers, and CR-147 now splits the two cases that were
    # one. A PROBABLE close is still only evidence -- the same id can name different work
    # in a chat line -- so CR-107's rule stands for it unchanged: the line stays in its
    # section, marked, evidence in the details. A CERTAIN close is the work's own source
    # saying closed or merged, which is what the person leading the meeting was reading off
    # the tracker by hand before removing the row; that line leaves the card, with its
    # basis in the header and the details. So `card_keep` now means exactly "kept because
    # the close is only probable", and a certain close is never in it.
    card_keep = set()
    # CR-148: `card_keep` is a DATA rule -- what a probable close does to a carried
    # line -- so compact shares it; the layout only decides where the line is printed.
    if is_card(cf):
        kd0 = kinds(last)
        card_keep = {k for k in closed_keys - certain_keys if kd0.get(k) in KINDS}
    # Proposal 3: a line nobody can check is not asserted as live either. It leaves the
    # card for the details file, and comes back only on its owner's written confirmation
    # -- until it has carried past `CONFIRM_SESSIONS`, after which the agenda stops
    # repeating it at all. CR-142 hooks its own marker into `unconfirmed` and inherits
    # this routing. Proposal 4: nothing here can OPEN a line; creation stays in the room.
    # It is the CARD that asserts a short list as today's live work; the list layout's
    # carried-forward table is the full list by definition and keeps every line, which
    # is what "additive" means for a project that has not moved to the card.
    # CR-148: compact asserts the same short list of live work, so the unconfirmed
    # routing is the same; only which output carries the question differs.
    pending = unconfirmed(raw_items) if is_card(cf) else []
    streaks = {key(t[0]): t[2] for t in items}
    # A line in its FIRST session was raised aloud last night; the room is its
    # confirmation and proposal 4 forbids this pass touching what the room created.
    # From the second session on, "it was said once" has stopped being evidence that
    # anyone is still waiting -- that is the nagging the team named -- so the owner's
    # word is what keeps it, and after `CONFIRM_SESSIONS` unconfirmed sessions the
    # agenda stops listing it at all.
    pending = [(l, r, why) for l, r, why in pending if streaks.get(key(l), 0) > 1]
    pending_keys = {key(l) for l, _r, _why in pending}
    aged_keys = {k for k in pending_keys if ages_out(streaks.get(k, 0))}
    # CR-142, proposal 2: an unconfirmed inference ages. The state and the threshold are
    # CR-147's; what this adds is the one thing a carried line otherwise lacked --
    # somewhere to be SAID. A line that is only *not readable* has CR-147's *cannot be
    # checked* table; an inferred line may name an id, in which case it never reached
    # that table and after two sessions would have come off the card with no trace at
    # all. Both layouts get the section: it adds a question and removes nothing, so the
    # list layout's own carried table is untouched.
    #
    # `certain_keys` is filtered out for the same reason CR-147 filters it out of
    # *Probably closed* (defect pass): a line whose own source says closed is GONE, and
    # the header already announces it under *Closed in the data since the last meeting*.
    # Asking the room to confirm the guess on a line the same page declares closed is two
    # statements about one item, and the one that reads as an open question is the wrong
    # one. The inference itself is not lost -- a wrong guess inside a closed item is
    # settled by the close, and a decision register line carrying the marker is still
    # reported by `check_inferred`.
    confirm_drop = [t for t in confirm_or_drop(raw_items, streaks)
                    if key(t[0]) not in certain_keys]
    all_items = items
    items = [t for t in items if key(t[0]) not in closed_keys | certain_keys]

    _off = off_card_keys(certain_keys, pending_keys, closed_keys, card_keep)
    off_card = _off.__contains__

    # CR-139: the base line goes in the header, above everything the reader has to
    # take on trust -- which note this was built from, when the series last actually
    # met, and which days in between did not count.
    base = base_line(last.name, last_date, skips, day)
    L = [f"# {cf.get('title', md.parent.name)}",
         f"### {day.strftime('%A %-d %B')}" + (f" · {cf['time']}" if cf.get("time") else ""),
         "", f"*{base}*", ""]
    # CR-140: a failed fetch is named HERE, not only in the fetch's own file and one
    # line of the sources block. The sections built from an archive use its last good
    # data and read as current, so the page looked complete while a fetch had failed
    # twice that morning. The header is the one place every reader passes.
    if (ff := failed_fetches(cf, recs, now)):
        # CR-145, proposal 2: each item now carries the age of the data it left behind,
        # which is what the reader needs in order to decide whether to read on.
        L += [f"> ⚠ **Fetch failed — {'; '.join(ff)}.** What follows is the last good data for that"
              " source, not today's.", ""]
    # CR-147, proposal 2: a line that leaves the card leaves a trace where every reader
    # passes. The agenda's own rule is that a machine which closes items silently is
    # worse than one that repeats them, so the ids go in the header and the basis and
    # time follow -- a close that shows its basis, not a silent one.
    #
    # WHERE they follow is the layout's. On the card the basis table lives in the
    # companion details file, which only the card layout writes; on the LIST layout
    # the same table is a section of this one page, so the link is to the section and
    # never to a file that was not written. Every other head-block link to the details
    # file is inserted inside the `if card:` branch for exactly this reason.
    if certain:
        where = (f"Basis and time: [{details_name(cf, target)}]({details_name(cf, target)})."
                 # CR-148: compact writes the same details file, so the link target is
                 # the card's; the list layout still points at its own section.
                 if is_card(cf)
                 else "Basis and time below, under *Closed in the data since the last meeting*.")
        L += ["> **Closed in the data since the last meeting:** "
              + ", ".join(sorted({i for _l, _r, h in certain
                                  for i in (h[3] if len(h) > 3 else ())}))
              + ". " + where, ""]
    # Proposal 6: the held verdicts. Nothing was dropped on this source's word, and the
    # header says which source and why -- otherwise the page is simply shorter on a
    # morning a fetch failed, which is the failure CR-140 exists to prevent.
    if held:
        why = "; ".join(f"{k}: {v}" for k, v in sorted(blocked.items()))
        L += ["> ⚠ **Source not read, so nothing was removed on its word — " + why + ".** "
              + f"Held on the card: {', '.join(item_of(l, r) for l, r, _h in held)}.", ""]
    L += ["---", ""]

    # ---- CR-084: the sources block, first ------------------------------------
    # An agenda that looks complete and was built from stale or missing inputs is
    # the failure this block exists to make impossible. STALE and NOT DECLARED are
    # printed, never omitted: a missing source that announces itself is honest, a
    # silent one is indistinguishable from an empty result.
    # CR-090: with `tracks:` declared, what the last session(s) said per person, and
    # the spread across the declared tracks -- counted over the roster only, so a
    # second column of some other table in the note is never read as a track.
    tracks = cf.get("tracks") or []
    roster = {k.lower(): p_["name"] for p_ in cf["people"]
              for k in [p_["name"]] + list(p_.get("aliases") or [])}
    last_round = round_table(last)
    round_recorded = any(k in roster for k in last_round)
    try:
        window = max(1, int(cf.get("balance_window") or 1))
    except (TypeError, ValueError):
        window = 1
    balance: dict[str, int] = {t: 0 for t in tracks}
    counted = 0
    for _d, note in hist[-window:]:
        rt = round_table(note)
        rows = {roster[k]: v for k, v in rt.items() if k in roster}
        if rows:
            counted += 1
        for v in rows.values():
            if (t := declared_track(v, tracks)):
                balance[t] += 1

    built = datetime.datetime.now().strftime("%y%m%d %H:%M")
    # CR-107; CR-148: true for compact too -- the movement fetch feeds the facilitator
    # document and the post's release-gap line, so the data is read the same way.
    card = is_card(cf)
    mv_head = mv_note = None
    mv_reports: list[str] = []
    mv_x: dict = {}
    if card:
        try:
            import build_movement
            mv_head, mv_note, mv_reports, mv_x = build_movement.run(cf, day)
        except Exception as e:   # best effort, like every other source
            mv_head, mv_note = None, f"not read — {e}"
        # CR-116: vault-kept report series join the repo ones -- same lines, same card.
        try:
            vl, vs = build_movement.vault_reports(cf, datetime.date.today())
            mv_reports = list(mv_reports) + vl
            mv_x = dict(mv_x or {}); mv_x["reports"] = list(mv_x.get("reports") or []) + vs
        except Exception as e:
            mv_reports = list(mv_reports) + [f"  report    vault reports NOT READ — {e}"]
    i_src = len(L)
    src = [f"## Sources — built {built} from", "", "```"]
    src.append(f"  note      {last.name:44} read")
    if tracks:
        # A missing round table is said, not shown as an empty column that looks
        # like a quiet day.
        src.append(f"  round     {last.name:44} "
                   + ("read" if round_recorded else "not recorded — no Last-track column, no balance line"))

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
            # CR-145, proposal 1: a direct chat is named for its person here, so it
            # appears in this block -- and therefore in the *Built from* line, which is
            # parsed from it -- like any other chat rather than as an opaque id.
            label = chat_label(c)[:44]
            if c.get("problem"):
                src.append(f"  chat      {label:44} NOT READ — {c['problem']}")
            else:
                msgs = c.get("messages") or []
                newest = max((m[0] for m in msgs), default="—")
                tail = stale_mark(crec) or fetch_status(crec)
                src.append(f"  chat      {label:44} newest {newest} · {n} since the note · {tail}")

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
    # CR-101: the digest is a slot prepare fills. Unfilled, the agenda is a draft,
    # and the sources block says so where the reader looks first.
    total_msgs = sum(len(c.get("messages") or []) for c in chat)
    if total_msgs:
        src.append(f"  digest    {str(total_msgs) + ' message(s) since ' + last_date:44} NOT FILLED — prepare reads them and fills the digest slot")
    trd = (cf.get("ext") or {}).get("transcripts") or {}
    if trd:
        # CR-145, proposal 4: the same three answers the check row gives, in the block the
        # *Built from* line is parsed from, so the page and the pre-flight cannot disagree
        # about whether anything looked at the recording store.
        src.append(f"  record    {str(trd.get('store') or 'declared')[:44]:44} "
                   + ("archive read" if trd.get("archive") else
                      "connected — the close-out step pulls the transcript (CR-145)"
                      if store_connected(cf) else
                      "declared, no archive — prepare checks the store by hand (CR-117)"))
    if card:
        src.append(f"  movement  {('read' if mv_head else (mv_note or '—'))[:60]}")
        src += mv_reports
    # CR-119: the config checked against the project, by script; prepare adds the judgement.
    cfg_findings = config_checks(cf, hist, day, mv_x if card else None)
    for f_ in cfg_findings:
        src.append(f"  config    {f_}")
    if not cfg_findings:
        src.append("  config    checks passed")
    src += ["```", "",
            f"{CONFIG_MARKER} decisions since {last_date} not yet checked against the config. Prepare: read them,"
            " propose any config edit out loud, then replace this line with 'Config reviewed against <decisions>'. -->", ""]

    # CR-117: the same facts as one line a reader sees first -- what the agenda was
    # built from, what it did not use, and the age of each. Parsed from the block
    # above so the two can never disagree.
    def built_from(lines: list[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """(name, short status) for each source, split into used and not used/stale."""
        used, unused, seen_current = [], [], set()
        for ln in lines:
            if not ln.startswith("  ") or ln.startswith("```"):
                continue
            kind, rest = ln[2:11].strip(), ln[11:].strip()
            name, status = (rest[:44].strip(), rest[44:].strip()) if len(rest) > 44 else (rest, "")
            if kind in ("digest", "round", "record", "config"):
                continue                          # recordings feed the note, not the agenda
            if kind == "report":
                if "current " in status:
                    seen_current.add(name)
                elif name in seen_current:
                    continue                      # the dated history behind a stable file
            # CR-145, proposal 1: a direct chat already carries its own word in the
            # name (`direct: Ravi`), so the `chat ` prefix would read as "chat direct".
            nm = {"note": name, "chat": name if name.startswith("direct:") else f"chat {name}",
                  "repo": "repo", "tickets": "tickets",
                  "movement": "issue labels", "record": f"recordings ({name})"}.get(kind, name)
            bits = []
            if (m := re.search(r"(\d+) since the note", status)):
                bits.append(f"{m.group(1)} msgs")
            if (m := re.search(r"fetched (\d\d:\d\d)", status)):
                bits.append(f"fetched {m.group(1)}")
            if "updated today" in status or re.search(r"\b0d old", status):
                bits.append("today")
            elif (m := re.search(r"(\d+)d (old|ago)", status)):
                bits.append(f"{m.group(1)}d old")
            bad = any(w in status for w in ("NOT DECLARED", "NOT READ", "NOT FOUND", "STALE", "not read", "no archive"))
            if kind == "report" and not bad and re.search(r"\b[2-9]\d*d old|\b1\dd old", " ".join(bits)):
                bad = True                        # two days or more counts as stale on a daily series
            if "NOT DECLARED" in status:
                bits = ["not declared"]
            elif "no archive" in status:
                bits = ["checked by hand"]
            (unused if bad else used).append((nm, ", ".join(bits)))
        return used, unused
    L += src
    i_carry = len(L)

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

    i_closed = len(L)
    # CR-147, proposal 2: the trace for a line that LEFT. Basis and time per line, so
    # the close can be checked in one click -- and `certainly_closed` keyed each verdict
    # by the archive it came from, which is the thing a reader distrusts first.
    if certain:
        L += [f"## Closed in the data since the last meeting ({len(certain)})", "",
              "**These left the card.** Each one's own source says closed or merged; the person leading",
              "was reading the tracker and removing these rows by hand. A close here is not a judgement",
              "about whether the work was good -- that is the test -- only that the source says it is done.",
              "", "| Item | Owner | Basis | When |", "|---|---|---|---|"]
        for lab, rest, hit in certain:
            kind, basis, when = hit[0], hit[1], hit[2]
            L.append(f"| {item_of(lab, rest)} | {owner_of(lab, rest)} | {kind} · {basis} | {when or '—'} |")
        L.append("")
    # CR-142, proposal 2: the inferences nobody has confirmed, owner first. Built once
    # and used twice -- the card asks the question, the details file keeps the copy --
    # because the one thing that must not happen to an unconfirmed guess is to be written
    # somewhere and read nowhere, which is how three wrong phrases reached a decision
    # register two days after the meeting they came from.
    confirm_block: list[str] = []
    if confirm_drop:
        confirm_block = [f"## Confirm or drop ({len(confirm_drop)})", "",
                         f"**Carried with an unconfirmed inference for more than {CONFIRM_SESSIONS}"
                         " sessions.** Each line holds something that",
                         "was not said and is in no source. Ask its owner: confirm it, and the next summary"
                         " names the",
                         "confirming source and drops the marker — or drop the inference and write what is"
                         " actually known.", "",
                         "| Item | Owner | Inferred | Sessions |", "|---|---|---|---|"]
        for lab, rest, n_ in confirm_drop:
            # The marker's own words, so the room is asked about the GUESS and not about
            # the item: `*inferred: the release day*` -> `the release day`.
            what = inferred_what(rest)
            confirm_block.append(f"| {item_of(lab, rest)} | {owner_of(lab, rest)} | {what} | {n_} |")
        confirm_block.append("")
        L += confirm_block
    # CR-084: printed after the carried block, before anything else the room does.
    # CR-147: a line with a CERTAIN close is not offered for confirmation -- it is gone,
    # and listed above with its basis. Only the probable ones are a question for the room.
    closed_hits = [h for h in closed_hits if key(h[0]) not in certain_keys]
    if closed_hits:
        L += ["## Probably closed — confirm", "",
              "**The sources say these moved since the last note.** They are NOT dropped: a machine that",
              "closes items silently is worse than one that repeats them. Confirm in the room, and the",
              "next note records the close.", "",
              "| Item | Owner | Evidence |", "|---|---|---|"]
        for lab, rest, hit in closed_hits:
            kind, ref, txt = hit
            # CR-141: already cut to width by `quote_for`, with the matched id kept.
            ev = f"{kind} · {ref}" + (f" — {txt}" if txt else "")
            L.append(f"| {item_of(lab, rest)} | {owner_of(lab, rest)} | {ev} |")
        L.append("")
    if fixed_rows:
        L += ["## Fixed, waiting for a test", "",
              "**Built, not accepted.** The ticket moved; nobody has tested it. These stay carried —",
              "schedule the test, do not close them.", "",
              "| Item | Owner | State |", "|---|---|---|"]
        for lab, rest, st in fixed_rows:
            L.append(f"| {item_of(lab, rest)} | {owner_of(lab, rest)} | {st} |")
        L.append("")
    # CR-147, proposal 3: ONE section, not two -- CR-141's list of lines nothing could
    # be read about and this CR's list of lines the card therefore does not assert are
    # the same lines, and printing both said it twice. CR-141's heading and reason
    # stand; this adds what the card now does with each, its session count, and the
    # ageing. CR-142's marker joins the same table through `unconfirmed`.
    pending_by_key = {key(l): (r, why) for l, r, why in pending}
    if unchecked:
        L += [f"## Items with no identifier, cannot be checked ({len(unchecked)})", "",
              "**No `#id` and no ticket key on these lines, so the sources were not consulted for them.**",
              "No marker here means *not checked*, not *not moved*. Add the id to that line in the",
              "summary and the next agenda can check it.", ""]
        if pending:
            L += ["**Not on the card either (CR-147): the agenda does not assert a line it cannot read.**",
                  "A line returns to the card when its owner confirms it in their own minute and the",
                  f"summary writes `*confirmed: <what they said>*` on it. Its FIRST session is the one"
                  " exception:",
                  "it was raised aloud last night and the room is its confirmation, so it is asserted"
                  " once and",
                  f"then asked for. Unconfirmed after {CONFIRM_SESSIONS} sessions the card stops asking"
                  " and the row below says",
                  "*aged out* — it keeps its place in this table, because a line removed from the one"
                  " list that",
                  "names it would be removed silently. Nothing here can be OPENED by the data: a"
                  " dependency is raised aloud.",
                  ""]
        # CR-147, defect pass: the card column is printed only where there IS a card.
        # On the list layout `pending` is empty by design -- that layout's carried table
        # is the full list and keeps every line -- so every row fell through to the final
        # branch and a line nobody had confirmed was printed as *yes, confirmed*, which
        # is a false statement about the operator's own data. A column with no meaning
        # is left out rather than filled with a guess.
        # CR-148: compact has a card, so the column means something there too.
        on_card = is_card(cf)
        head_ = ["Item", "Owner"] + (["On the card"] if on_card else []) + ["Sessions"]
        L += ["| " + " | ".join(head_) + " |", "|" + "---|" * len(head_)]
        for lab, rest in unchecked:
            k_ = key(lab)
            n_ = streaks.get(k_, 0)
            cells = [item_of(lab, rest), owner_of(lab, rest)]
            if on_card:
                if k_ in aged_keys:
                    # Off the card, still listed here: see the prose above.
                    cells.append("**aged out** — unconfirmed, off the card")
                elif k_ in pending_by_key:
                    cells.append("no — awaiting its owner's word")
                elif n_ <= 1:
                    # Proposal 4: the room raised it last night and this pass may not
                    # unmake that. Said as the reason it is there, not as a bare *yes*.
                    cells.append("yes — first session, raised in the room")
                else:
                    cells.append("yes — confirmed by its owner")
            cells.append(str(n_))
            L.append("| " + " | ".join(cells) + " |")
        L.append("")
    # CR-142: the inferred lines that have come off the card but have NOT yet aged into
    # *Confirm or drop*. Where such a line names an identifier CR-147's *cannot be
    # checked* table never held it, and without this it would leave the card with no
    # trace at all -- the silent removal this agenda's whole rule is against. Same two
    # routes out: the owner's confirmation, or the section on the card.
    #
    # Three keys are excluded, each because the line is already accounted for on this
    # page and CR-147's rule is ONE section per line, not two (defect pass):
    # `confirm_drop_keys`, the aged ones the card now asks about; `unchecked_keys`,
    # the lines the table just above already lists with their own card column -- an
    # inference naming no identifier is in both states at once, and that table is the
    # one that names it; and `certain_keys`, a line whose own source says closed, which
    # the header reports as closed and is no longer carried at all.
    confirm_drop_keys = {key(l) for l, _r, _n in confirm_drop}
    unchecked_keys = {key(l) for l, _r in unchecked}
    held_inferred = sorted(((l, r) for l, r, why in pending
                            if why == "unconfirmed inference"
                            and key(l) not in confirm_drop_keys | unchecked_keys | certain_keys),
                           key=lambda t: (owner_of(*t) == "UNOWNED", owner_of(*t).lower(),
                                          item_of(*t).lower()))   # owner first, as on the card
    if held_inferred:
        L += [f"## Unconfirmed inferences, off the card ({len(held_inferred)})", "",
              "**Each of these carries `*inferred: <what>*`: something nobody said and no source holds.**",
              "The card does not assert an inference, so the line sits here until its owner confirms it —",
              "the next summary then names the confirming source and drops the marker. Still unconfirmed",
              f"after {CONFIRM_SESSIONS} sessions, it moves to *Confirm or drop* on the card.", "",
              "| Item | Owner | Sessions |", "|---|---|---|"]
        for lab, rest in held_inferred:
            L.append(f"| {item_of(lab, rest)} | {owner_of(lab, rest)} | {streaks.get(key(lab), 0)} |")
        L.append("")


    # Raw chat lines are still NOT printed: pasted into a team-facing document they
    # are noise, and quoting a colleague back at the room reads as surveillance.
    # CR-101 keeps that and adds what the room does need -- the FACTS: what landed,
    # who waits on whom, what depends on another team. A digest is a judgement this
    # script cannot make, so it writes a marked slot and `prepare` fills it. The
    # marker is what makes an unread digest visible: an agenda still carrying it is
    # a draft, and `/ops orient` reports it as one.
    i_digest = len(L)
    if total_msgs:
        # CR-145, proposal 1: `prepare` reads this marker to know where the traffic was,
        # and for a direct chat that is a PERSON -- a conversation title says nothing
        # about whose reply is waiting in it.
        per = ", ".join(f"{chat_label(c)} {len(c['messages'])}" for c in chat if c.get("messages"))
        L += ["## Since the last standup — not said in the room", "",
              f"<!-- DIGEST: {total_msgs} messages since {last_date} ({per}). Not yet read. -->", ""]
    # CR-150, proposal 2: a declared source that already counts work per person. Written
    # into the digest section, before `prepare` fills the slot, because `prepare` is the
    # reader that would otherwise copy them -- the note tells it the figures are there and
    # that they stay there. ONE line per source, naming the source and NO figure: a note
    # that quoted one would itself have copied it. Independent of `total_msgs`: a report
    # carrying figures is read whether or not the chat was busy.
    if (src_counts := source_person_counts(cf)):
        if not total_msgs:
            L += ["## Since the last standup — not said in the room", ""]
        L += [f"- {ln}" for ln in src_counts] + [""]
        for ln in src_counts:
            print("  source    " + ln.replace("**", ""))
    # CR-076: say when nothing was DECLARED, as distinct from declared-but-empty.
    # An undeclared block and a quiet week both render as no messages, and the one
    # that is a configuration miss is the one worth naming -- silently empty is how
    # this went unnoticed in the first place.
    if not (cf.get("ext") or {}).get("chats"):
        print("  no external_systems.chats declared in the config chain"
              " — nothing to retrieve (declare it, or ignore if intended)")
    total = sum(len(c["messages"]) for c in chat)
    if total:
        print(f"  {total} chat message(s) since {last_date} — the agenda has a digest slot;"
              " prepare must read them and fill it before the agenda is done (CR-101)")
        # Which chat to go and read. With one declared chat the name is noise; with
        # several, an undivided total does not say where the traffic was.
        if len([c for c in chat if c["messages"]]) > 1:
            for c in chat:
                if c["messages"]:
                    print(f"    {chat_label(c)}: {len(c['messages'])}")
    # Problems print SEPARATELY and are never counted as messages. Folded into the
    # total they would report traffic that does not exist and hide the reason.
    for c in chat:
        if c["problem"]:
            print(f"  chat not read — {c['problem']}: {chat_label(c) if c.get('name') or c.get('person') else '(declared chats)'}")

    # What each person is carrying INTO this session, routed to their own row.
    # The chain already knows it -- it was being printed once at the top and then
    # dropped, so the round asked everyone the same empty question.
    # CR-084: what each person said their track was last session. The note's round
    # table records it on every line; the agenda then asked again from blank, which
    # is how a column the project asks for first came to be empty every morning.
    prior_track = round_table(last)

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
    cols, people = cf.get("round_columns") or [], cf["people"]
    i_round = len(L)
    L += ["---", "", "## Round", ""]
    # The legend below says this better when there is one; printing both repeats
    # the instruction and buries the values.
    if cols and not tracks:
        L.append(f"**Say your {cols[0].lower()} before anything else.**\n")
    if tracks:
        L.append("**Track before anything else.** "
                 + " · ".join(t[:1].upper() + t[1:] for t in tracks) + ". One per item, never two.\n")
    L.append("**What moved · what you are blocked on and who owns the other end · what you need a decision on.**")
    # CR-090: the spread, as a question. Zeros included -- an empty track is the
    # thing a person-by-person round never shows.
    if tracks and counted:
        span = "Last session" if window == 1 or counted == 1 else f"Last {counted} sessions"
        L.append("")
        L.append(f"{span} by track: " + " · ".join(f"{t} {balance[t]}" for t in tracks))
        empty = [t for t in tracks if balance[t] == 0]
        if empty:
            names = empty[0] if len(empty) == 1 else ", ".join(empty[:-1]) + " and " + empty[-1]
            L.append(f"- {names} had no one. Intended, or unbalanced?")
    if not people:
        # CR-101: an empty round is a configuration miss that renders as a finished
        # section. Say so (CR-076: declared-but-empty is not undeclared), and name who
        # a schedule lists -- but never fill rows from it: participants describe a
        # schedule, not a round order, and an `adjacent` person would get a permanent
        # empty row.
        where = cf.get("_config_file")
        where = where.name if where else "the config chain"
        L += ["", "| | Owed into today |", "|---|---|", "",
              f"No roster: `people:` is not declared beside `carry_forward` in {where}. The round has no rows."]
        print(f"  no roster: `people:` is not declared beside carry_forward in {where} — the round has no rows")
        if cf.get("_participants"):
            names = ", ".join(cf["_participants"])
            L.append(f"Attendees found under `meeting_types.<type>.participants`: {names} — declare them as `people:`.")
            print(f"    attendees under meeting_types.<type>.participants: {names} — declare them as people:")
    if people:
        # A table is only worth its space when it has rows to hold.
        # The header must carry the same cell count as the separator and the rows:
        # one for the name, one per configured column, one for the free text.
        # CR-090: with `tracks:` declared, yesterday's answer gets its own column.
        # Today's stays blank and is stated in the room; merging the two is how a
        # carried value comes to read as a confirmed one.
        last_col = bool(tracks and round_recorded)
        head = [""] + cols + (["Last track"] if last_col else []) + ["Owed into today"]
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
            lt = []
            if last_col:
                prev = next((last_round[k.lower()] for k in [p_["name"]] + list(p_.get("aliases") or [])
                             if k.lower() in last_round), "")
                t_ = declared_track(prev, tracks)
                lt = [f"{t_} *(carried)*" if t_ else ""]
            cells = ([f"**{p_['name']}**"] + ([first] + [""] * (len(cols) - 1) if cols else [])
                     + lt + [due])
            L.append("| " + " | ".join(cells) + " |")
        if (un := [item_of(l, r) for l, r, *_ in items if owner_of(l, r) == "UNOWNED"]):
            L += ["", f"**Nobody owes these: {', '.join(un)}.** They are on no row above, which is"
                  " why they keep carrying. Give each one a name in the round or take it off the list."]
    i_close = len(L)
    L += ["", "---", "", "## Close", "", "- Read-back: what the recap says",
          "- **Read-back: what carries to tomorrow, and whose name is on each.** An item read back",
          "  without a name is the one that will be here again", ""]

    i_app = len(L)
    # CR-145, proposal 3: the recordings, in the DETAILS. On the card layout `L[i_app:]`
    # is written to the companion details file; on the list layout it is the tail of the
    # one page. Either way it is detail rather than something the room talks through --
    # which capture the transcript came from is the close-out's fact. Only written when
    # the build ran over a recording (`--skip-unprocessed`, or a told recording): with no
    # recording to report, a heading saying nothing is noise.
    if (rec_lines := recording_lines(unprocessed, prefer)):
        L += ["---", ""] + rec_lines
    if repo:
        notes = [r["note"] for r in repo if "note" in r]
        rows = [r for r in repo if "note" not in r and r.get("kind", "issue") == "issue"]
        prs = [r for r in repo if r.get("kind") == "pull"]
        rels = [r for r in repo if r.get("kind") == "release"]
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
        if prs:
            # CR-101: grouped by what the room does with each -- note what landed,
            # chase what waits for review (oldest first), ask about what was dropped.
            L += [f"**{len(prs)} pull request(s) moved since the last note.**", ""]
            for status, head in (("merged", "Merged"), ("awaiting review", "Awaiting review"),
                                 ("open", "Opened, still open"), ("closed", "Closed unmerged")):
                group = [r for r in prs if r["status"] == status
                         and (status != "open" or r.get("new"))]
                if not group:
                    continue
                if status == "awaiting review":
                    group.sort(key=lambda r: -r["age"])
                L += [f"*{head} ({len(group)})*", ""]
                for r in group:
                    tail = f" — waiting {r['age']} day(s)" if status == "awaiting review" else ""
                    L.append(f"- {r['repo']} #{r['n']} {r['title'][:90]}"
                             + (f" ({r['who']})" if r.get("who") else "") + tail)
                L.append("")
        if rels:
            L += [f"**Released since the last note ({len(rels)}):** "
                  + ", ".join(f"{r['repo']} {r['n']}" for r in rels), ""]

    if card:
        kd = kinds(last)
        dname = details_name(cf, target)
        # CR-121/CR-148: which sections this project's outputs carry, and in what order.
        plan = section_plan(cf, day)
        head = L[:i_src]
        A = list(head)
        used_, unused_ = built_from(src)
        fmt = lambda xs: " · ".join(n + (f" ({b})" if b else "") for n, b in xs)
        if cfg_findings:
            A.insert(len(A) - 2, f"> **Config: {len(cfg_findings)} finding(s)** — " + "; ".join(cfg_findings)
                     + ". Fix the config, or say why not, before the meeting.\n")
        A.insert(len(A) - 2, f"> **Built from** ({built}): " + fmt(used_)
                 + ("" if not unused_ else ". **Not used or stale:** " + fmt(unused_))
                 + f". Detail: [{details_name(cf, target)}]({details_name(cf, target)}).\n")
        # CR-121: the lead is chosen from the plan, which already knows whether this
        # project confirms release blockers and whether today is its demo day. The
        # three head inserts above stay in this order: each goes in at len-2, so the
        # header reads in the REVERSE of the insert sequence.
        A.insert(len(A) - 2, lead_line(cf, plan, day))
        ms_all = milestones(cf)
        ms = ms_all[0] if ms_all else {}
        # Page-level, not a section's: `rest_n` is printed after the loop, and the
        # facilitator document (CR-148) renders the same `stuck_tasks` list.
        stuck_tasks = [t for t in items if kd.get(key(t[0])) not in KINDS and (t[2] >= E or (ED and t[4] >= ED))]
        rest_n = len([t for t in items if kd.get(key(t[0])) not in KINDS]) - len(stuck_tasks)

        # CR-121/CR-148: one section, named by its id. The title, the lead and the
        # column come out of SECTIONS, so a plan can swap `release_blockers` for
        # `blockers` (CR-121) or move a section to another output (CR-148) without
        # a conditional in here. The body is CR-107's, unchanged.
        def sect(sid):
            s_ = SECTIONS[sid]
            kind, title, lead, col = s_["kind"], s_["title"], s_["lead"], s_["col"]
            rows_ = [t for t in all_items if kd.get(key(t[0])) == kind
                     and not off_card(key(t[0]))]
            if not rows_:
                return [f"## {title}", "", f"*None carried as `[{kind}]`.*", ""]
            out_ = [f"## {title}", "", lead, "", f"| Item | Owner | {col} |", "|---|---|---|"]
            for lab, rest, n, g, d in rows_:
                mark = f"**{n}** sessions" if n >= E else f"{n} session{'s' if n != 1 else ''}"
                if d >= 7:
                    mark += f" · {d}d"
                note = rest.split("·")[0].strip(" —-") if "·" in rest else ""
                if key(lab) in card_keep:
                    mark += " · *probably closed? evidence in details*"
                out_.append(f"| **{item_of(lab, rest)}**" + (f" — {note}" if note else "") + f" | {owner_of(lab, rest)} | {mark} |")
            return out_ + [""]

        def s_milestone():
            A = []
            A += ["## Milestone" + ("s" if len(ms_all) > 1 else ""), ""]
            if len(ms_all) > 1:
                # CR-149, proposal 2: a table, sorted by date, the state on every line, and the
                # next date after today carrying the days left. The state is the column the
                # reader needs: a bare date cannot say whether it is a commitment somebody made
                # or a proposal out of a plan document, and both are on this card.
                nxt = next_milestone(ms_all, day)
                A += ["| Milestone | Date | State | Set on | Source |", "|---|---|---|---|---|"]
                for e in ms_all:
                    when = e["_date"].isoformat() if e["_date"] else ""
                    if e is nxt:
                        when = f"**{when}** · **{(e['_date'] - day).days} days**"
                    elif e.get("date"):
                        # CR-149: declared and unparseable. Shown as written -- never as
                        # "date not set", which would contradict the config.
                        when = f"**{e['date']}** (unreadable date)"
                    else:
                        when = "*date not set*" + (f"; decide by {e['decide_by']}" if e.get("decide_by") else "")
                    A.append(f"| **{e.get('name', 'Unnamed')}** | {when} | {e['_state']} | "
                             f"{e.get('set_on') or '—'} | {e.get('source') or '—'} |")
                tl = timeline_line(ms_all)
                if tl:
                    A += ["", f"*Sequence: {tl}*"]
                crit = [f"Exit criteria — {e.get('name', 'Unnamed')}: {e['criteria']}"
                        for e in ms_all if e.get("criteria")]
                if crit:
                    A += [""] + crit
            elif ms:
                when = ms.get("date")
                line = f"**{ms.get('name', 'Next milestone')}**"
                # CR-149: through `as_date` like every other config date -- the last copy
                # of the parse lived here, and the one reader is what stops the date the
                # card sorts by and the date the validation complains about disagreeing.
                if ms["_date"]:
                    dd = (ms["_date"] - day).days
                    line += f" — {when} · **{dd} days**"
                elif when:
                    # A date that was declared and does not parse. Calling it unset would
                    # be false; config_checks names it and asks for YYYY-MM-DD.
                    line += f" — **{when}** (not a date the generator can read)"
                else:
                    line += " — **date not set**" + (f"; decide by {ms['decide_by']}" if ms.get("decide_by") else "")
                # CR-149: the state is appended only where the config declared one. A single
                # milestone that says nothing about its state renders exactly as it did before.
                if ms.get("state"):
                    line += f" · *{ms['_state']}*"
                A.append(line)
                if ms.get("criteria"):
                    A.append(f"Exit criteria: {ms['criteria']}")
            else:
                A.append("*No milestone declared (`milestone:` in the project config). An agenda with no date has nothing to run toward.*")
            # CR-121: a demo date that has gone by. The milestone line itself is left
            # exactly as it is -- config_checks already says the date has passed -- and
            # this adds the one thing that finding does not: the demo is the kind of
            # milestone whose outcome has to be recorded before the next date is set.
            past_demo = next((e for e in ms_all
                              if str(e.get("kind") or "").strip().lower() == "demo"
                              and e["_date"] and e["_date"] < day), None)
            if past_demo:
                A.append(f"*Demo held ({past_demo['_date'].isoformat()})? Record it and set the"
                         " next milestone.*")
            A.append("")
            return A

        def s_movement():
            A = []
            if mv_head:
                A += ["## Movement", "", mv_head, ""]
                rs = (mv_x or {}).get("reports") or []
                if rs:
                    A.append("**Status sources:** " + " · ".join(
                        f"{nm} — " + ("updated today" if a_ == 0 else ("missing" if a_ is None else f"**{a_}d old**"))
                        + ("" if p_ and not p_.split("/")[-1][:4].isdigit() else " (dated file, no stable link)")
                        for nm, _o, p_, a_ in rs))
                    A.append("")
            elif cf.get("movement") is not None or any((r or {}).get("labels") for r in ((cf.get("ext") or {}).get("repos") or []) if isinstance(r, dict)):
                A += ["## Movement", "", f"*Not available: {mv_note}.*", ""]
            return A

        def s_blockers(sid="release_blockers"):
            A = []
            # CR-114: a blocker is a RELEASE blocker. With labels declared, the list comes
            # from the repo -- the label is the definition -- and the room confirms it.
            # Carried [blocker] lines follow; people waiting on people are dependencies.
            #
            # CR-121: the repo table is NOT config's to suppress. `release_blockers: false`
            # says this project does not ship releases; a repo that declares a gap label
            # says it does, and hiding the repo's own data on a config key would be the
            # wrong direction. The key reaches `sid` -- the carried-line section -- only.
            rb = (mv_x or {}).get("blockers") or []
            if rb:
                A += ["## Release blockers", "",
                      f"**From the repo's `{mv_x.get('top')}` label. Is this the list? Anything missing? What is the plan for each?**", "",
                      "| # | Area | State | Assignee | Issue |", "|---|---|---|---|---|"]
                for b_ in rb:
                    A.append(f"| [#{b_['n']}]({b_['url']}) | {b_['area']} | "
                             + ("fixed, waiting for a test" if b_["fixed"] else "**open**")
                             + f" | {', '.join(b_['who']) or '—'} | {b_['title'][:80].replace('|', '/')} |")
                A.append("")
                more = sect("other_blockers")
                # The index-2 probe is CR-114's: `sect` puts its *None carried* placeholder
                # there, and a section with nothing in it is not worth a second heading.
                if not more[2].startswith("*None"):
                    A += more
            else:
                A += sect(sid)
            return A

        def s_dependencies():
            A = []
            A += sect("dependencies")
            return A

        def s_decisions():
            A = []
            A += sect("decisions")
            return A

        def s_confirm():
            A = []
            # CR-142, proposal 2: on the card, not only in the details. An unconfirmed
            # inference is a question for a named person, and the card is where the room
            # reads the questions it has to answer out loud.
            A += confirm_block
            return A

        def s_stuck():
            A = []
            if stuck_tasks:
                A += [f"## Stuck? ({len(stuck_tasks)})", "",
                      f"Tasks carried {E}+ sessions. Give each a date and a name, or drop it.", ""]
                A += [f"- {item_of(l, r)} · **{owner_of(l, r)}** ({n} sessions)" for l, r, n, _g, _d in stuck_tasks] + [""]
            # The link to the details file follows the stuck list: it is what the card
            # offers instead of the rest, and it is the reason the card can be short.
            A += [f"*{rest_n} more carried task(s), the sources, the chat digest and the repo detail: [{dname}]({dname}).*", ""]
            return A

        def s_round():
            A = []
            # The round: one minute each, one question, the previous track as a hint.
            rnd = L[i_round:i_close]
            A += ["---", "", "## One-minute round", "",
                  "**One minute each. What moved toward the milestone? What is stuck, and who owns the other end?**"
                  + (" Track first." if tracks else ""), ""]
            A += [x for x in rnd if x.startswith("Last session") or x.startswith("Last ") or x.startswith("- ") and "had no one" in x]
            # Each person's minute starts from what they carry (CR-084 routed it to their row;
            # the card must not lose that): their card items by kind, then a count of their
            # other carried tasks. The question is the same for everyone; the prompt is not.
            mark_ = {"blocker": "blocked", "dependency": "waiting", "decision": "decide"}
            per: dict[str, list[str]] = {}
            tasks_n: dict[str, int] = {}
            for lab, rest, n, _g, _d in all_items:
                if off_card(key(lab)):
                    continue
                who = owner_of(lab, rest)
                if who == "UNOWNED":
                    continue
                k_ = kd.get(key(lab))
                short = re.split(r"[:—;]", item_of(lab, rest))[0].strip()[:60]
                for nm in re.split(r",|\band\b|·", who):
                    nm = nm.strip().strip("*").lower()
                    if not nm:
                        continue
                    if k_ in KINDS:
                        per.setdefault(nm, []).append(f"*{mark_[k_]}:* {short}")
                    else:
                        tasks_n[nm] = tasks_n.get(nm, 0) + 1
            if people:
                lt_col = bool(tracks and round_recorded)
                A += ["", "| | " + ("Last track | " if lt_col else "") + "Bring to your minute |",
                      "|---|" + ("---|" if lt_col else "") + "---|"]
                for p_ in people:
                    keys_ = [p_["name"]] + list(p_.get("aliases") or [])
                    mine_, seen_ = [], set()
                    for k in keys_:
                        for x in per.get(k.lower(), []):
                            if x not in seen_:
                                seen_.add(x); mine_.append(x)
                    order_k = {"*blocked:*": 0, "*waiting:*": 1, "*decide:*": 2}
                    mine_.sort(key=lambda x: order_k.get(x.split(" ", 1)[0], 3))
                    nt = max((tasks_n.get(k.lower(), 0) for k in keys_), default=0)
                    cell = " · ".join(mine_)
                    for nm_r, own_r, _p, a_r in ((mv_x or {}).get("reports") or []):
                        if own_r and own_r.lower() in [k.lower() for k in keys_]:
                            cell = f"*summarise:* {nm_r}" + (" (STALE)" if a_r not in (0,) else "") + (" · " + cell if cell else "")
                    if nt:
                        cell += (" · " if cell else "") + f"{nt} carried task{'s' if nt != 1 else ''} (details)"
                    prev = next((last_round[k.lower()] for k in keys_ if k.lower() in last_round), "")
                    A.append(f"| **{p_['name']}** | " + (f"{declared_track(prev, tracks) or ''} | " if lt_col else "")
                             + (cell or "—") + " |")
            return A

        def s_close():
            A = []
            A += L[i_close:i_app]
            return A

        def s_demo():
            """CR-121: what is being shown today, who shows it, and in what state.

            Rows come from what the pipeline already knows: the carried lines that are
            on the card, and the repo's gap-label issues fixed and waiting for a test
            (`mv_x["blockers"]` with `fixed`), which is "on staging or done since the
            last demo" as the repo states it. A gap-label issue nobody has fixed yet is
            NOT a demo row (CR-121 proposal 2): it is on the card under Release blockers.

            *Shown by* is READ or left BLANK. The demo convention is that the person who
            raised an idea shows it, so a carried line's owner is the raiser; an issue the
            repo assigned to nobody has no raiser to read, and a plausible guess -- the
            assignee, the last person to touch it -- would put a name against work that
            person never offered to present. The blank is the point: the room fills it.
            """
            A = ["## Demo", "",
                 "**What is shown today, by whom, in what state. A blank *Shown by* is for"
                 " the room to fill, not for the generator to guess.**", "",
                 "| Item | Shown by | State |", "|---|---|---|"]
            seen_ = set()
            for lab, rest, _n, _g, _d in all_items:
                if off_card(key(lab)) or kd.get(key(lab)) not in KINDS:
                    continue
                who = owner_of(lab, rest)
                item = item_of(lab, rest)
                seen_.add(item.lower())
                A.append(f"| **{item}** | " + ("" if who == "UNOWNED" else who)
                         + f" | carried as `[{kd.get(key(lab))}]` |")
            for b_ in ((mv_x or {}).get("blockers") or []):
                # CR-121 proposal 2: rows are the repo items "on staging or done since
                # the last demo", which for this repo's data is the `awaiting_test`
                # label -- fixed and waiting for a test. An item nobody has fixed is
                # not something to show at a demo, and listing it as **open** put the
                # release-blocker table's content into the Demo section. The open ones
                # are still on the card, under Release blockers, where they belong.
                if not b_["fixed"] or b_["title"].strip().lower() in seen_:
                    continue
                A.append(f"| [#{b_['n']}]({b_['url']}) {b_['title'][:70].replace('|', '/')} | "
                         # No raiser in the repo's data: the assignee fixed it, which is
                         # not the same statement as "this person will show it".
                         + " | fixed, waiting for a test |")
            if len(A) == 6:
                A.append("| *nothing carried or moved* | | |")
            return A + [""]

        # CR-121/CR-148: the agenda is its plan. The order and the presence of every
        # section are section_plan()'s; this loop only renders what it is handed, so
        # a layout or a `card:` key never reaches into a renderer.
        render = {"milestone": s_milestone, "movement": s_movement,
                  # One renderer, two ids: CR-121 changes the heading and the lead by
                  # choosing the id, not by branching inside the renderer.
                  "release_blockers": lambda: s_blockers("release_blockers"),
                  "blockers": lambda: s_blockers("blockers"),
                  "dependencies": s_dependencies, "decisions": s_decisions,
                  "confirm": s_confirm, "stuck": s_stuck, "round": s_round,
                  "close": s_close, "demo": s_demo}
        for sid in plan["agenda"]:
            A += render[sid]()
        # CR-148: the compact agenda has no Stuck? section, so the link to the details
        # file -- which `s_stuck` carries on the card -- is written here instead. The
        # link is not optional: "the rest is in the details" is the whole claim that
        # lets the agenda be two sections, and an agenda that drops it is simply short.
        if is_compact(cf):
            A += ["",
                  f"*Everything else -- the dependencies, the movement, the sources, the full"
                  f" carried list: [{dname}]({dname}). The facilitator's document is"
                  f" `{facilitator_name(cf, target)}`.*", ""]
        out.write_text("\n".join(A), encoding="utf-8")
        D = [f"# Agenda details — {day.strftime('%A %-d %B')}", "",
             f"Companion to [{out.name}]({out.name}): what the agenda was built from, the full carried list, "
             "and the detail nobody needs to talk through. Not read out in the meeting.", "",
             f"*{base}*", ""]   # CR-139
        D += L[i_src:i_carry] + L[i_carry:i_closed] + L[i_closed:i_digest] + L[i_digest:i_round] + L[i_app:]
        (md / dname).write_text("\n".join(D), encoding="utf-8")
        if is_compact(cf):
            # CR-148: the facilitator's own document. Time boxes, the dependencies read
            # against the data, and what to watch.
            #
            # CR-150: NO PER-PERSON FIGURES. The temptation here is a "who carries the
            # most" watch list, and it is exactly the aggregation CR-150 forbids -- the
            # person reading this is often one of the people who would be counted. The
            # dependencies are ordered by AGE, never by owner, and an owner appears only
            # beside the one item they own, which is accountability, not a scoreboard.
            F = [f"# Facilitator — {day.strftime('%A %-d %B')}", "",
                 f"For whoever leads. Not screen-shared: the room reads `{out.name}`.", "",
                 f"*{base}*", ""]   # CR-139
            if cfg_findings:
                F += [f"> **Config: {len(cfg_findings)} finding(s)** — " + "; ".join(cfg_findings)
                      + ". Fix the config, or say why not, before the meeting.", ""]
            F += ["> **Built from** (" + built + "): " + fmt(used_)
                  + ("" if not unused_ else ". **Not used or stale:** " + fmt(unused_))
                  + f". Detail: [{dname}]({dname}).", ""]

            def f_timeboxes():
                """CR-148: how long each part of the agenda gets.

                Derived from what the agenda actually carries -- a minute per person for
                the round, and the remainder of CR-107's ten minutes for the decisions.
                A box is a plan for the time, not a claim about what happened.
                """
                dec_n = len([x for x in all_items if kd.get(key(x[0])) == "decision"
                             and not off_card(key(x[0]))])
                rnd_m = max(1, len(people))
                return ["## Time boxes", "",
                        "| Part | Minutes |", "|---|--:|",
                        f"| Decisions needed ({dec_n}) | {max(2, dec_n * 2)} |",
                        f"| One-minute round ({rnd_m} people) | {rnd_m} |",
                        "| Anything raised in the room | 2 |", ""]

            def f_dependencies():
                """CR-148: the dependencies, each line read against the data (CR-147).

                A line whose own source says closed or merged is LISTED AS CLOSED rather
                than dropped: the facilitator is the person who would otherwise raise it,
                and a line that silently disappeared is the failure CR-147 names. Ordered
                by age, oldest first -- never by owner (CR-150).
                """
                rows_ = [x for x in all_items if kd.get(key(x[0])) == "dependency"]
                if not rows_:
                    return ["## Dependencies", "", "*None carried as `[dependency]`.*", ""]
                F_ = ["## Dependencies", "",
                      "**Oldest first. Each line was read against its own source; a closed one is"
                      " listed as closed, not removed.**", "",
                      "| Item | Owner | Waiting | Read against the data |", "|---|---|---|---|"]
                for lab, rest, n, _g, d in sorted(rows_, key=lambda x: (-x[4], -x[2])):
                    k_ = key(lab)
                    if k_ in certain_keys:
                        state = "**closed** — its own source says so"
                    elif k_ in card_keep:
                        state = "probably closed? evidence in the details"
                    elif k_ in aged_keys:
                        state = f"unconfirmed for {CONFIRM_SESSIONS}+ sessions — off the card"
                    elif k_ in pending_keys:
                        state = "awaiting its owner's word"
                    elif k_ in {key(l) for l, _r, _h in held}:
                        state = "source not read, so nothing was removed on its word"
                    else:
                        state = "open"
                    F_.append(f"| **{item_of(lab, rest)}** | {owner_of(lab, rest)} | "
                              + (f"{n} session{'s' if n != 1 else ''}"
                                 + (f" · {d}d" if d >= 7 else "")) + f" | {state} |")
                return F_ + [""]

            def f_movement():
                return s_movement()

            def f_stuck():
                """CR-148: what to watch. CR-150: counted by ITEM, never by person."""
                F_ = ["## What to watch", ""]
                if stuck_tasks:
                    F_ += [f"- {len(stuck_tasks)} task(s) carried {E}+ sessions: "
                           + " · ".join(item_of(l, r) for l, r, *_ in stuck_tasks)]
                if certain:
                    F_ += [f"- {len(certain)} carried line(s) came off the card because their own"
                           " source says closed. The header says which; the basis is in the details."]
                if held:
                    F_ += ["- a source was not read, so nothing was removed on its word: "
                           + "; ".join(f"{k}: {v}" for k, v in sorted(blocked.items()))]
                if rest_n:
                    F_ += [f"- {rest_n} more carried task(s) in the details, not raised here."]
                return F_ + ([""] if len(F_) > 2 else ["*Nothing.*", ""])

            f_render = {"dependencies": f_dependencies, "movement": f_movement,
                        "stuck": f_stuck}
            F += f_timeboxes()
            for sid in plan["facilitator"]:
                F += f_render[sid]()
            (md / facilitator_name(cf, target)).write_text("\n".join(F), encoding="utf-8")
    else:
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
    # One repo line, not two (CR-107): pull requests and issues in a single sentence.
    prs_all = [r for r in repo if r.get("kind") == "pull"]
    rws = [r for r in repo if "note" not in r and r.get("kind", "issue") == "issue"]
    bits = []
    if prs_all:
        waiting = [r for r in prs_all if r["status"] == "awaiting review"]
        oldest = max((r["age"] for r in waiting), default=0)
        bits.append(f"{sum(1 for r in prs_all if r['status'] == 'merged')} merged, "
                    f"{len(waiting)} awaiting review"
                    + (f" (oldest {oldest} day{'s' if oldest != 1 else ''})" if waiting else ""))
    if rws:
        bits.append(f"{len(rws)} issues moved, {sum(1 for r in rws if r['new'])} opened, "
                    f"{sum(1 for r in rws if r['state'] == 'closed')} closed, "
                    f"{sum(1 for r in rws if not r['who'])} with no assignee")
    if bits:
        T += ["**Repo since the last note:** " + " · ".join(bits) + ".", ""]
    if card:
        # CR-107: the post is the card -- the date, what is stuck, what is waiting,
        # what must be decided. Each person's full carried list stays in the details.
        kd = kinds(last)
        ms_all = milestones(cf)
        ms = ms_all[0] if ms_all else {}
        plan = section_plan(cf, day)        # CR-121/CR-148
        C = [T[0], ""]
        used_, unused_ = built_from(src)
        C += ["**Built from:** " + " · ".join(n for n, _ in used_)
              + ("" if not unused_ else ". Not used or stale: " + " · ".join(n for n, _ in unused_)) + ".", ""]

        def c_milestone():
            C = []
            if len(ms_all) > 1:
                # CR-149, proposal 2: in the plain-text post a SHORT list -- one line per
                # milestone, the state on each, the days left on the next date after today.
                # No table: the post is pasted into a chat where a table does not survive.
                nxt = next_milestone(ms_all, day)
                C.append("**Milestones:**")
                for e in ms_all:
                    when = e["_date"].isoformat() if e["_date"] else undated_phrase(e)
                    C.append(f"- {e.get('name', 'Unnamed')} — {when} · {e['_state']}"
                             + (f" · **{(e['_date'] - day).days} days**" if e is nxt else "")
                             + (f" · {e['source']}" if e.get("source") else ""))
                tl = timeline_line(ms_all)
                if tl:
                    C.append(f"Sequence: {tl}")
            elif ms:
                C.append(f"**Milestone:** {ms.get('name', '')}" + (f" — {ms['date']}" if ms.get("date") else
                         " — date not set" + (f", decide by {ms['decide_by']}" if ms.get("decide_by") else ""))
                         # CR-149: appended only where a state was declared, so an existing
                         # single-milestone post is unchanged.
                         + (f" · {ms['_state']}" if ms.get("state") else ""))
            return C

        def c_movement():
            C = []
            if mv_head:
                m_ = re.search(r"\*\*Release gap\*\*[^|]*\| \*\*(\d+)\*\* \(([^)]*)\) \| ([^|]+)\|", mv_head)
                m2 = re.search(r"Release gap: still to fix \| \*\*(\d+)\*\*", mv_head)
                if m_:
                    C.append(f"**Release gap:** {m_.group(1)} open ({m_.group(2)})"
                             + (f", {m2.group(1)} still to fix" if m2 else "") + f" · since yesterday {m_.group(3).strip()}")
            return C

        def c_kind(sid):
            """One carried-line section, inline, labelled as POST_LABELS names it.

            CR-121: `release_blockers` and `blockers` are the same kind under two ids,
            and the post labels both *Blockers* -- the post has never carried the word
            release in that label, so the key changes nothing here.
            """
            C = []
            kind = SECTIONS[sid]["kind"]
            rows_ = [t for t in all_items if kd.get(key(t[0])) == kind
                     and not off_card(key(t[0]))]
            if rows_:
                C.append(f"**{POST_LABELS[sid]}:** "
                         + " · ".join(f"{item_of(l, r)} ({owner_of(l, r)})" for l, r, *_ in rows_))
            return C

        def c_demo():
            """CR-121: on demo day the post carries what is shown, not the blockers line."""
            rows_ = [f"{item_of(l, r)}"
                     + ("" if owner_of(l, r) == "UNOWNED" else f" ({owner_of(l, r)})")
                     for l, r, *_ in all_items
                     if kd.get(key(l)) in KINDS and not off_card(key(l))]
            # Same filter as `s_demo`: on staging or done, never the still-open ones.
            rows_ += [f"#{b_['n']} {b_['title'][:60]}"
                      for b_ in ((mv_x or {}).get("blockers") or []) if b_["fixed"]]
            return ["**Demo today:** " + (" · ".join(rows_) if rows_
                                          else "nothing carried or moved — agree the list in the room")]

        def c_round():
            C = []
            C += ["", "**Round, one minute each:** what moved toward the milestone, what is stuck."]
            order_ = []
            for p_ in people:
                keys_ = [p_["name"]] + list(p_.get("aliases") or [])
                mine_ = []
                for lab, rest, *_ in all_items:
                    if kd.get(key(lab)) in KINDS and not off_card(key(lab)):
                        owners_ = [o.strip().strip("*").lower() for o in re.split(r",|\band\b|·", owner_of(lab, rest))]
                        if any(k.lower() in owners_ for k in keys_):
                            mine_.append((["blocker", "dependency", "decision"].index(kd.get(key(lab))),
                                          re.split(r"[:—;]", item_of(lab, rest))[0].strip()[:50]))
                mine_ = [x for _, x in sorted(mine_, key=lambda t: t[0])]
                order_.append(f"**{p_['name']}**" + (f" ({'; '.join(mine_)})" if mine_ else ""))
            if order_:
                C.append("Order: " + " · ".join(order_))
            return C

        # CR-121/CR-148: the post is its plan too, and the same ids name the same
        # sections as in the agenda.
        c_render = {"milestone": c_milestone, "movement": c_movement, "demo": c_demo,
                    "release_blockers": lambda: c_kind("release_blockers"),
                    "blockers": lambda: c_kind("blockers"),
                    "dependencies": lambda: c_kind("dependencies"),
                    "decisions": lambda: c_kind("decisions"),
                    "round": c_round}
        for sid in plan["post"]:
            C += c_render[sid]()
        if bits:
            C += ["", "**Repo since the last note:** " + " · ".join(bits) + "."]
        C += ["", f"Agenda: `{out.name}` · details: `{details_name(cf, target)}`"]
        T = C
    else:
        T += [f"Full agenda: `{out.name}`"]
    # ---- CR-148: the compact post ---------------------------------------------
    # PLAIN TEXT, in a .txt file. The measured failure was a markdown post pasted into
    # a chat whose own rule is three to five lines of plain text: the asterisks showed
    # as asterisks and the post ran about 660 words. So this writer uses no emphasis,
    # no table and no link, and it carries the milestones, the blockers and the ask --
    # not the round and not the dependencies, which have their own documents.
    if is_compact(cf):
        kd = kinds(last)
        ms_all = milestones(cf)
        nxt = next_milestone(ms_all, day)
        P = [f"{cf.get('title', md.parent.name)} — {day.strftime('%A %-d %B')}"
             + (f", {cf['time']}" if cf.get("time") else "")]
        parts: list[tuple[str, list[str]]] = []
        if demo_on(cf, day):      # CR-121: on demo day the post carries the demo list
            shown = [item_of(l, r) for l, r, *_ in all_items
                     if kd.get(key(l)) in KINDS and not off_card(key(l))]
            # The repo's own rows, under the same CR-121 filter the card's Demo section
            # applies: on staging or done, never the still-open ones. Without them the
            # compact post -- the only post a compact project has -- would carry less
            # than the card's post does on the same day.
            shown += [f"#{b_['n']} {b_['title'][:60]}"
                      for b_ in ((mv_x or {}).get("blockers") or []) if b_["fixed"]]
            parts.append(("demo", ["Demo today: " + (", ".join(shown) if shown
                                                     else "list to be agreed in the room")]))
        ml = []
        for e in ms_all:
            # CR-149: an unreadable declared date is shown as written, not as "date not
            # set" -- the compact post is the one some readers see instead of the card.
            # The decide-by that `undated_phrase` adds is new here and wanted: a date
            # still to be decided is exactly what this post is meant to raise.
            when = e["_date"].isoformat() if e["_date"] else undated_phrase(e)
            ml.append(f"- {e.get('name', 'Unnamed')}: {when}, {e['_state']}"
                      + (f", {(e['_date'] - day).days} days" if e is nxt else ""))
        parts.append(("milestones", (["Milestones:"] + ml) if ml else
                      ["Milestones: none declared."]))
        # The blockers, one per line, grouped as the repo states them: what still has to
        # be fixed, and what is fixed and waiting for a test. The carried [blocker]
        # lines join the first group -- a line nobody has fixed is something to fix.
        to_fix = [f"- {b_['title'][:70]} (#{b_['n']})"
                  for b_ in ((mv_x or {}).get("blockers") or []) if not b_["fixed"]]
        waiting = [f"- {b_['title'][:70]} (#{b_['n']})"
                   for b_ in ((mv_x or {}).get("blockers") or []) if b_["fixed"]]
        bsid = "release_blockers" if "release_blockers" in plan["post"] else "blockers"
        to_fix += [f"- {item_of(l, r)}"
                   + ("" if owner_of(l, r) == "UNOWNED" else f" ({owner_of(l, r)})")
                   for l, r, *_ in all_items
                   if kd.get(key(l)) == SECTIONS[bsid]["kind"] and not off_card(key(l))]
        bl = []
        if to_fix:
            bl += ["To fix:"] + to_fix
        if waiting:
            bl += ["Waiting for a test:"] + waiting
        parts.append((POST_LABELS[bsid].lower(), bl or ["No blockers."]))
        parts.append(("ask", ["Bring what moved, what is stuck and who owns the other end."
                              f" Agenda: {out.name}"]))

        def assemble(ps):
            return "\n".join(P + [x for _n, ls in ps for x in [""] + ls]) + "\n"

        def shortened(ls: list[str], keep: int, total: int) -> list[str]:
            """`ls` with only its first `keep` `- ` rows, and a counted line for the rest.

            The rows are grouped ("To fix:", "Waiting for a test:") and the grouping is
            CR-148's, so rows are dropped from the END and a group left with no rows is
            dropped with its own heading -- an empty "Waiting for a test:" says nothing.
            Dropping from the end means only the LAST heading can be left empty, so one
            trailing check is the whole of it.
            """
            o, left = [], keep
            for x in ls:
                if not x.startswith("- "):
                    o.append(x)
                elif left > 0:
                    o.append(x); left -= 1
            while o and not o[-1].startswith("- "):
                o.pop()
            return o + ([f"- and {total - keep} more, in {out.name}"] if keep < total else [])

        # CR-148: `max_words` (default 150). Read with an explicit None test, NOT `or`:
        # CR-148's own key may legitimately be 0, which `or 150` read as unset -- a
        # project writing 0 to mean "always warn" silently got the default and no
        # warning at all.
        raw_mw = ((cf.get("compact") or {}) if isinstance(cf.get("compact"), dict)
                  else {}).get("max_words")
        try:
            limit = 150 if raw_mw is None else int(raw_mw)
        except (TypeError, ValueError):
            limit = 150
        limit = max(0, limit)
        text = assemble(parts)
        words = len(text.split())
        if words > limit:
            # CR-148 acceptance bullet 1: "with ten blockers, the post is at most 150
            # words". A warning beside a 300-word file does not meet that bullet -- the
            # post is the thing pasted into a chat whose rule is three to five lines, so
            # a post that does not fit has already failed at the only job it has.
            #
            # So the ceiling HOLDS, and the BLOCKER list is the part that gives way --
            # named by its id, not by being the longest. It is the only unbounded part:
            # the milestones are declared by the project and the ask is one line and the
            # reason the post exists, so a post that dropped either would be a worse
            # post than a long one. As many whole blocker lines are kept as fit, and the
            # remainder becomes ONE counted line naming the file that carries them all.
            # Nothing disappears silently: the count is in the post, the full list is in
            # the agenda and the details, and the warning below still names the longest
            # part, which is what CR-148 proposal 1 asks the operator to be told.
            nm_, ln_ = max(((n, len(" ".join(ls).split())) for n, ls in parts),
                           key=lambda x: x[1])
            print(f"  post is {words} words (limit {limit}); longest part: {nm_}, {ln_} words")
            bid = POST_LABELS[bsid].lower()
            over = next((i for i, (n, _l) in enumerate(parts) if n == bid), None)
            if over is not None:
                full = parts[over][1]
                total = sum(1 for x in full if x.startswith("- "))
                for keep in range(total, -1, -1):
                    trial = list(parts)
                    trial[over] = (bid, shortened(full, keep, total))
                    if len(assemble(trial).split()) <= limit or keep == 0:
                        parts = trial
                        break
                text = assemble(parts)
        (md / f"{target}-teams-{cf['agenda_suffix']}.txt").write_text(text, encoding="utf-8")
    # CR-148: under compact the post IS the .txt above. Writing the markdown one too
    # would leave two posts in the folder and the team would paste the wrong one -- the
    # markdown one is the file whose asterisks caused this CR.
    if not is_compact(cf):
        post = md / f"{target}-teams-{cf['agenda_suffix']}.md"
        post.write_text("\n".join(T) + "\n", encoding="utf-8")
    if not has_section(last):
        print(f"  ⚠ {last.name} has no '## Carried forward' section — chain broken, nothing carried in")
    print(f"  {last.name} -> {out.name}  ({len(items)} carried"
          + (f", {len(stuck)} at {E}+ sessions" if items and stuck else "")
          + f"; {len(chat)} chat, {len(repo)} repo)")


if __name__ == "__main__":
    main()
