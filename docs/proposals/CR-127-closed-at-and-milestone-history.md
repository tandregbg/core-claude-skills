# CR-127 — The ledger and the milestone record *when*, not just *what*

| | |
|---|---|
| **Status** | **Implemented** (2026-10-20, Unreleased) |
| **Contract** | `contract_version` 43 → 44, `ops_config` 1.6 → 1.7 (**additive** — two optional fields; `tasks` stays schema 2 and every existing file remains valid). CR-126 also claims `ops_config` 1.7; whichever implements first takes it |
| **Date** | 2026-10-15 |
| **Area** | `tasks` (schema + every writer that sets a finished status), `ops-config` (`schema.md`, `milestone:`), `ops` (`prepare` config review, `check`, `build_agenda.py` `config_checks()`), `ecosystem.yaml` (`schemas`) |
| **Related CRs** | CR-107 (`milestone:` and the card), CR-119 (the config review that already notices a moved date), CR-048 (the status enum), CR-122 (enum checks; YAML is edited, never re-dumped), CR-096 (targeted append), CR-116/CR-117 (dated report series — today the only place a past plan survives), CR-128 (the Jira source for movement, proposed separately) |

## What happened

A structural read of three active projects in one vault asked three ordinary questions — *is the
backlog growing, is the plan slipping, how much are we closing per week* — and none of them could be
answered from what the skills write. Not because the data is hard to collect: because the two
fields that carry time were never declared.

**1. A finished task does not record when it finished.** The v2 schema has `created`, `due` and
`status`; there is no closing date. A writer that needed one invented `completed:`, so the field
exists in the wild and is applied unevenly — in one project 26 of 28 finished rows carry it, in
another **1 of 23**. Those 22 closures are not recoverable: the day is gone, and the ledger has no
history. Throughput — the one number that says whether a project is moving — cannot be computed
from a ledger that only knows the present.

**2. A moved deadline overwrites the old one.** `milestone:` (CR-107) is a single `date:`, and the
config comment the convention invites says so: *update after each milestone*. All three projects
declare exactly one block. In at least two the target had already moved; the previous value survives
only as prose in a dated status report, if someone happened to write one that day. There is no vault
git history to fall back on, so *what did the plan say three weeks ago* is answerable only by
reading.

CR-119 already made the generator notice a date that no longer matches the project. It reports the
drift and leaves no record of the correction — the one moment the change is in hand is the moment it
is discarded.

## Proposal

### 1. `closed:` in the tasks v2 schema

```yaml
tasks:
  - id: 1
    task: "Fix the database connection"
    priority: P1
    due: 260307
    created: 260303
    status: completed            # pending | in_progress | blocked | completed | cancelled
    closed: 260309               # NEW, optional: the day status became completed or cancelled
```

- **A writer that sets a finished status sets `closed:` in the same edit.** One field for both
  finished states: a cancelled task is a closed task, and a reader counting throughput needs the day
  either way.
- **`completed:` is accepted on read as a legacy alias and never written.** The field is already in
  real ledgers; refusing it would discard the only closing dates that exist.
- **No migration.** Rows whose closing day is unknown stay unknown — a backfilled guess is worse
  than a gap, and a mass rewrite is exactly the re-dump CR-122 forbade. The gap is visible in the
  check below, which is the honest form.
- `ecosystem.yaml` `schemas.tasks` stays `2`: an optional field added to a schema whose readers
  tolerate unknown keys is not a new schema.

### 2. `milestone:` keeps its history

```yaml
milestone:                       # project-wide, beside `tracks:` (CR-107) — unchanged
  name: "Release candidate ready"
  date: 2026-11-20
  set_on: 2026-10-14             # NEW, optional: when this date was set
  decide_by: 2026-10-30
  criteria: "exit criteria in the project README"
  history:                       # NEW, optional: newest last; append only
    - date: 2026-10-30           # the target that was in force
      set_on: 2026-09-16
      reason: "set at the first standup"
      source: "meetings/260916-daily-standup.md"
    - date: 2026-11-06
      set_on: 2026-10-30
      reason: "backend release moved; the gate did not"
      source: "decisions.md#d-92"
```

**Additive by construction.** `milestone.name`, `.date`, `.decide_by` and `.criteria` keep their
meaning and position, so `build_agenda.py`, the card and `config_checks()` keep working untouched. A
project that declares no `history:` behaves exactly as today.

**Who appends.** The config review in `prepare` (CR-119) already reads the decisions since the last
agenda and asks whether any of them changes the config. When one moves the milestone, the review
**appends the outgoing date to `history:` with its `reason` and `source` before writing the new
`date:`** — the record is a by-product of a step that already happens, not a new habit. The
generator still edits nothing.

### 3. Two report-only checks

In `/ops check <folder>` (the folder pass, beside the CR-122 enum checks):

- **a finished task with no closing day** — `status` in `finished` and neither `closed:` nor a legacy
  `completed:`. Report the count and the ids; from the day this lands the count should only fall.
- **a milestone date with no provenance** — `date:` present and `set_on:` absent, or a `history:`
  entry missing `reason` or `source`. Report it on the card's existing *Config: N finding(s)* line,
  where a stale milestone is already reported.

Report only, both of them. The fix for a missing closing day is a judgement about a specific task,
and a skill guessing the day a task finished is a skill writing fiction into a ledger.

## What this is not

- **Not a `due` history per task.** A row's own date moves often and the notes already carry why.
  One time field at a time; a second one earns its own CR if the first proves out.
- **Not a Jira source for the movement block.** The archive exists (CR-074) and the agenda already
  reads it; the movement reader does not. That is CR-128, and it is independent of this one.
- **Not a chart.** core-skills writes records, not pictures. What this CR delivers is that the four
  obvious views — cumulative flow, inflow against outflow per week, a slip line of target date
  against the day it was observed, and age of what is stuck — become *computable* from declared
  fields. Where they are rendered is a project's own business.

## Why it cannot wait for the rendering question

Every other gap in this family is recoverable later: a check can be added next month and will find
what is already on disk. These two are not. A closure that happens today without a `closed:` and a
date that moves today without a `history:` entry are **gone** — there is no event log behind either
field, and no git history under the vault. The cost of a week's delay is a week of missing rows in
the one series nobody can reconstruct.

## Files touched

| File | Change |
|---|---|
| `skills/tasks/SKILL.md` | `closed:` in the v2 schema and in the key list; `completed:` named as a read alias; the writing rule for a finished status |
| `skills/ops-config/schema.md` | `set_on:` and `history:` under `milestone:`; header to v1.7 |
| `skills/ops/SKILL.md` | the two findings in `check <folder>`; the append step in the CR-119 config review |
| `skills/ops/build_agenda.py` | `config_checks()`: milestone provenance finding |
| `ecosystem.yaml` | `schemas.ops_config` 1.6 → 1.7; `contract_version` 43 → 44 with its comment block |
| `CHANGELOG.md` | the release entry, `(CR-127)` |
| `docs/proposals/README.md` | row moved from Proposed to Implemented in the same commit (CR-020) |

## As built (2026-10-20)

- Everything in the proposal, as written. `tasks` stays schema 2; `ecosystem.yaml` declares contract 44 and
  `ops_config` 1.7 (CR-126 also names 1.7; one declaration serves both, the field lists are disjoint).
- The closing-day finding is in `hygiene_check.py` (`tasks` kind), so it runs in the folder pass beside
  the CR-122 enum checks: one line per ledger, count and first five ids. A finished status is read from
  `ecosystem.yaml` `task_statuses.finished`.
- The provenance findings are in `config_checks()` and so appear on the card's *Config* line and in
  the sources block. A milestone with no `date:` raises none.
- Existing tests that built a clean milestone now carry `set_on:`; that is the intended consequence of the
  finding, not a regression.
- The append step is prose in `ops/SKILL.md` (the CR-119 config review). No script writes `history:`.

### Review fixes (2026-10-20)

- `config_checks()` reports a non-list `milestone.history` once ("must be a list") instead of iterating it.
- Closing day: missing means `None` or blank on both `closed:` and `completed:`; any other value counts.
- `skills/tasks/SKILL.md` gains `/tasks cancel`, so `status: cancelled` + `closed:` has a documented writer
  beside `/tasks done`. No other writer of a finished status was found in `skills/`.
- Tests cover a dateless milestone, non-list and empty `history`, blank `closed:`, and å/ä/ö task text.
- No contract change; contract stays at the 44 the CR already declared.
