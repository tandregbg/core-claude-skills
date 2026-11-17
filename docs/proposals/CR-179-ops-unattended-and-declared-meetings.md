# CR-179 — `/ops` unattended: a declared meeting schedule, and a run that stops at staged

| | |
|---|---|
| **Status** | **Implemented** v1.97.0, contract 51 (2026-11-17) |
| **Contract** | New: `meetings:` in a project's ops config — when a recurring meeting happens and what may run around it. Additive; a reader that ignores it reads what it read before |
| **Date** | 2026-11-17 |
| **Area** | `ecosystem.yaml` (`meetings` schema), `ops` (`prepare`, the process path, a new `apply` step, `orient` block 1), `build_agenda.py` / `project_brief.py` (read the declaration) |
| **Related CRs** | **CR-082** / **CR-107** (the generated agenda and its card — the deterministic half of a preparation), **CR-087** (`external_systems.transcripts`, where a series is recorded), **CR-088** (`_fetch.json` — how a stale source is reported), CR-061 (`orient`), CR-071 (`default:` is a send concept, not a read concept); vault-tools CR-009 (the scheduler that calls this) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E] Three recurring project meetings are run with this suite, each by hand, each day it meets.** The
loop is the same in all three: fetch, `/ops prepare`, finish the card by hand, stage in `_outbox/`,
hold the meeting, paste the transcript, process it, write the recap, stage it. Most of it is already
deterministic — the archives are fetched on a schedule and `build_agenda.py` builds the card — and
the rest is model work that does not need a person **until the result is reviewed**.

A companion scheduler (vault-tools CR-009) will start these steps at fixed times: the preparation 45
minutes before the meeting, the processing once the recording's transcript exists. A skill cannot start
a session; the scheduler can. What the scheduler cannot do is decide **what a run may do with nobody
there**. That is this suite's to say, because it owns what the files mean.

Two gaps make that impossible today:

1. **No declared schedule.** The three series write their meeting time in three shapes — a
   `meeting_types.<type>.schedule` block, a `time_cet:` key, a YAML comment. Nothing can read all three.
2. **Every step assumes someone answers.** Attribution, routing, an ambiguous name variant, "is this the
   right milestone" — the skill asks, and an unattended run has no one to ask.

## Proposal

### 1. `meetings:` — the declaration (contract)

In the project's ops config, beside `meeting_types`:

```yaml
meetings:
  - type: standup                     # a key in meeting_types; names the preparation mode
    days: [mon, thu]                  # or: weekdays
    time: "08:30"
    timezone: Europe/Stockholm
    duration: 30m
    prepare_lead: 45m                 # when the preparation starts; ready by lead - 15m
    transcript_wait: 4h               # how long after the end to look for the recording
    unattended: [prepare, process]    # what may run with nobody there; absent = nothing
    apply_ledgers: false              # see section 3
```

- **Absent means off.** A series without `meetings:` is never touched by a scheduler.
- `unattended` is opt-in per step, so a series can automate its preparation and keep processing by hand.
- `/ops orient` (block 1, *Loop position*) reads it for *next session* instead of inferring it from
  the last two notes.

### 2. `--unattended` for `prepare` and the process path

The same steps, with four differences:

| | Attended | Unattended |
|---|---|---|
| A question the skill would ask | asked | **not asked.** Written into the output as `[OPEN: <question>]` at the point it arises, and listed at the top of the run's report |
| Outbox status | as today | **always `draft`.** Never `klar-att-skicka`, never a sent status. A person promotes it |
| Shared ledgers (`CHANGELOG.md`, `_tasks.yaml`, `_insights.yaml`, meetings README, rolling plans) | written | **proposed, not written**, unless `apply_ledgers: true` (section 3) |
| Files it may create | any the step needs | **new dated files only**: the agenda set, the summary, its own `_outbox/` folder, the raw transcript the scheduler handed it. An existing file is never edited |

- **The card rule holds.** A preparation that cannot fill the card says so on the card (`[OPEN]`),
  rather than filling it with a guess.
- **A stale source is reported, not hidden.** If a fetch record says `auth_required` or `error`, the card's
  *Fetch problems* block (CR-088) is mandatory, not optional.
- **The run report** — the open questions, the files written, the ledger changes proposed — is the
  session's final output, so the scheduler can forward it as the notification.

### 3. `/ops apply` — the ledger changes, from the attended session

`apply <folder> [YYMMDD]` reads the run report's proposed ledger changes for that meeting, shows them,
and writes them on confirmation. The interactive session is where shared files are edited, so two
writers never touch the same ledger at once.

`apply_ledgers: true` lets the unattended run write them itself. It is meant to be set once a series has
run cleanly for a while — trust that is earned, per series, in config, not assumed by default.

## What does not change

- The attended path is unchanged in every step.
- **Nothing in this suite sends.** Unattended or not, the outbox stops at staged.
- The read restriction on raw transcripts stands: the process step reads the one transcript it was handed,
  for the summary it writes from it, as the attended path does.

## Tests

- `meetings:` parses; `orient` names the next session from it; an absent block changes nothing.
- An unattended preparation with a fetch record in `auth_required`: the card carries *Fetch problems*.
- An unattended run with an ambiguous attribution: `[OPEN]` in the summary, listed in the report, no
  ledger written.
- An existing file at an output path: the run stops and reports it; the file is unchanged.
- `apply` writes exactly the proposed changes and nothing else.

## As implemented (v1.97.0)

- **The reader** is `skills/ops/meeting_schedule.py`: `declared()` resolves `meetings:` from the
  folder's own config only -- the first directory walking up that holds `.claude/ops-config.yaml` or
  `_ops.yaml`; if neither file there declares `meetings:`, nothing is declared, so an org's schedule and
  unattended permission never reach a project beneath it (review fix; the first cut walked on to
  ancestors and `_config/base.yaml`). The list is taken whole; `meetings: []` declares none. Defaults where a field is absent: `duration` 30m, `prepare_lead`
  45m, `transcript_wait` 4h, `timezone` the machine's own zone, `unattended` nothing, `apply_ledgers`
  false. A malformed entry is a reported problem, never a crash; an unknown day or step is dropped and
  reported. `build_agenda.py` re-exports its config-file pair from here, and reads the declared days
  where `schedule_days`/`meets` are absent -- ahead of the older `meeting_types.<type>.schedule`.
- **`orient`** prints `next session    <YYMMDD> <HH:MM> <type> (declared)`, an `unattended` line and
  any declaration problem; `--now` was added so the line can be tested. Absent, the output is as before.
- **The unattended differences that can be checked are in scripts**, the rest in SKILL.md:
  `run_report.py allowed` (permission from the declaration), `guard` (existing output stops the run),
  `write` (the report in `<project>/.runs/`, collecting `[OPEN: ...]` markers and `## Fetch problems`,
  reporting undated files and non-draft outbox status), and `build_agenda.py --unattended` (the whole
  agenda set checked before writing; a mandatory `## Fetch problems` block on the card).
- **`/ops apply`** is `run_report.py apply`: shows by default, `--write` after confirmation, `--only`
  for a subset, `--unattended` for a run applying its own proposals (refused unless `apply_ledgers:
  true`). Four operations; all or nothing; YAML ledgers re-parsed; dot-folders and paths out of the vault
  refused; applied ids recorded in the report.
- **Tests:** `tests/test_cr179_unattended.py`, 58 tests (47 at implementation, 11 from the review), one class per bullet of the Tests section.
- **[H] Not run against a live series.** The scheduler (vault-tools CR-009) does not exist yet; the
  unattended path has run only in the test vaults.
