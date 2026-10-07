# CR-107 — The generated agenda is the card: milestone, blockers, dependencies, decisions; the rest is an appendix

| | |
|---|---|
| **Status** | **Implemented 2026-10-07** (opt-in: `carry_forward.layout: card`) |
| **Contract** | additive — new config keys (`layout`, `milestone`, `movement`, `repos[].labels`, `repos[].reports`), an optional kind prefix on carried lines, a companion details file. The default layout is unchanged |
| **Date** | 2026-10-07 |
| **Area** | `ops` (`build_agenda.py`, new `build_movement.py`, `project_brief.py`, `prepare` P0, carry-forward contract, `check` 2d), `ops-config/schema.md` |
| **Related CRs** | **CR-005** and **CR-106** (*the card comes first* — the rule the generator never obeyed), CR-057 (carry-forward), CR-084 (sources block; carried lines name something findable), CR-088 (fetch record), CR-090 (track balance), CR-101 (digest slot). **Absorbs** the *pending decisions* gap of the unreleased options-and-deferrals proposal |

Marks: **[E]** observed in a running series · **[H]** not yet run.

## What happened

A daily standup in a project with a wired agenda loop (CR-057) ran three days on generated agendas,
with these results:

1. **The meeting read the list.** On the third day the lead read the carried list line by line,
   about 13 minutes of a meeting that ran 48 against a 30-minute target. The carried list had grown
   to 31 lines. **[E]**
2. **Two carried lines meant nothing to their owners.** One was a mechanism name lifted from a
   rollout plan without its source; the named owner asked what it referred to. The other was a
   security issue given a softened name to keep detail out of a team document; nobody could tell
   what it was. **[E]**
3. **A count in a carried line went stale.** "19 open" was read out right after a fresh reading
   said 16. **[E]**
4. **Nobody could say whether the release gap was shrinking.** Asked directly, the room had a daily
   snapshot from a team report and no trend. **[E]**
5. **The release had no date to run toward,** and the agenda had nowhere to say so. **[E]**
6. ***Probably closed* was wrong every time:** 12 of 12 matches across three agendas were
   unrelated updates, documentation PRs, or work merged before the meeting. **[E]**

Afterwards the facilitator and a colleague arrived, independently of the generator, at the shape
the skill already prescribes: **the goal and the next milestone, what blocks it and who owns that,
what we wait on, a one-minute round — everything else in an appendix,** kept so you can later see
where things diverged. A proactive document that steers the meeting, not a summary of everything.

## Why it happened

`/ops prepare` already says *"the card comes first"* (CR-005, inherited by CR-106): at most five
items on top, enough to lead the meeting; metadata, sources and rationale below a rule. **The
generator for wired projects never implemented it.** `build_agenda.py` opens with an 11-line
Sources block, then every carried item, then *Probably closed*, the digest, the round and a repo
appendix. A wired project therefore gets the one agenda shape the skill forbids, and the more
diligent the carry-forward, the worse the agenda.

The carry-forward line had no way to say *what kind* of item it is, so the generator could not
tell a blocker from a chore, and could only list everything in session order.

## Change

### 1. Card layout (`carry_forward.layout: card`) — `build_agenda.py`

The agenda opens with **Milestone → Movement → Blockers → Dependencies → Decisions needed today →
Stuck? → One-minute round → Close.** A companion `YYMMDD-agenda-details-<…>.md` holds the Sources
block, the full carried list, *Probably closed*, the digest slot and the repo detail. The chat post
is the card: milestone, release gap, blockers, waiting-on, decide-today, the round question, one
repo line. **[H]** for the whole; the movement block in it is **[E]**.

| Talked about (agenda) | Appendix (details file) |
|---|---|
| Milestone, date or *not set; decide by …*, days left | Sources, fetch status, declared reports and their age |
| Movement block with checks | The full carried list with session counts |
| `[blocker]`, `[dependency]`, `[decision]` items | *Probably closed* |
| Tasks past the escalation threshold (*Stuck?*) | The digest slot |
| One-minute round: *what moved toward the milestone, what is stuck* | Repo, issue and PR detail |

### 2. Kind on carried lines

`- [blocker] **item** — source · **owner**`; also `[dependency]`, `[decision]`; untagged is a task.
`process` assigns it when writing the section. The list layout parses the prefix and ignores it.

### 3. `milestone:` (project-wide)

`name`, `date` (optional), `decide_by` (optional), `criteria` (optional). Absent, the card says
an agenda with no date has nothing to run toward.

### 4. Movement — new `build_movement.py`

The release gap over time, by area, rebuilt from the repo's issue events with label names read from
`external_systems.repos[].labels` (priority order, the gap set, the awaiting-test label, optional
blocked/answered labels, the area prefix). Writes a dated details file and a per-run snapshot.
**Three checks are printed, pass or fail:** the rebuilt state equals the repo's current state; every
day shown is covered by event history (the API keeps about 90 days); the agenda's date equals the day
it was read, else **STALE**. The one live read in the pipeline, because the archive answers *what
moved*, never *how many are open*. Best effort. **[E]** — read out unprompted by the meeting's lead
the first day it existed.

### 5. Declared reports — `repos[].reports`

A dated report series in the repo (`dir` + filename `pattern`); the details file's Sources block
names the newest and its age, or *none found*. **[E]** — two daily reports were read every morning
only because a person remembered to.

### 6. Carried-line rules (`check` 2d, sharpened)

A borrowed term is not plain words; a carried line carries **no counts**; unknown kinds are flagged;
card layout without `milestone:` is flagged. **[E]**

### 7. Chat post: one repo line

Pull requests and issues in one sentence; the post printed two lines with the same lead. **[E]**

### 8. `/ops orient`

Reads the details file for an unfilled digest marker as well as the agenda.

## Not changed (named so they are not assumed)

- *Probably closed* matching is unchanged; in card layout it moves to the appendix, which removes
  its cost from the meeting. A stricter matcher (evidence after the note, a closed state on a
  referenced issue) is left for its own CR.
- Which count *is* the release gap when a team report and the labels disagree is the team's
  decision. The movement block states the definition it uses (`gap:`) and nothing more.
- The deferrals half of the unreleased options-and-deferrals proposal (unwired projects) stays with
  that proposal.

## Tests

`tests/test_cr107_agenda_card.py`: card order; kinds route to their sections; tasks and sources go
to the details file; milestone without a date says so; the post is the card; the digest slot lives
in the details file; the default layout is unchanged and still parses a kind prefix.
