# CR-139 — The agenda defaults to today, and a series can say which days it does not meet

| | |
|---|---|
| **Status** | **Proposed** (2026-10-21) |
| **Contract** | additive — one config key (`skip_dates`), one changed default; an explicit `--date` behaves as before |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`build_agenda.py`, SKILL.md step 9), `ops-config` (schema), `ecosystem.yaml` |
| **Related CRs** | CR-057 (the carry-forward agenda), CR-087 (a recording the caller already found), CR-127 (the milestone's `set_on`) |

## What happened

The generator's `--date` defaults to *"the next weekday after the last note"*. On a morning when the previous
working day had no meeting (a public holiday for most of the team, so no note was written), the run
produced an agenda for **the skipped day**, not for today. The file was stamped *STALE — read 21/10, the
agenda is for 20/10* by the generator itself, which is the right warning on the wrong output. The assistant
deleted three generated files and re-ran with `--date`, a further three minutes.

**[E]** One occurrence in a run of seven working days, and it cost one wasted build and a manual correction.
The default is only right when the series meets every weekday and every meeting is written up the same day.

## Proposal

1. **Default `--date` is today** (the operator's local date). A run for a date earlier than today is refused
   unless `--date` is given explicitly; a run for a date that already has a note says so and stops.
2. **`skip_dates:` in the series' ops config**, a list of `YYMMDD` or ranges, each with a one-word reason
   (`holiday-in`, `leave`). A skipped day is not a missing note: the base note stays the last meeting held,
   and the carry-forward counts **sessions**, not calendar days, so nothing ages on a day nobody met.
3. **The agenda's header says the base**: `Base: <note> (last meeting held <date>; skipped: <dates>)`, so a
   reader sees at once which days did not count.
4. **A day-of-week cadence key** (`meets: [mon, tue, wed, thu, fri]`) is read when present, so a series
   that meets three days a week does not need a skip list for the other two.

## Not in scope

A holiday calendar of its own. The skip list is operator-written; the skill does not know which days a
team is away.

## Acceptance

- With no `--date`, a run on a day after a skipped day builds for today.
- `--date` earlier than today without confirmation refuses.
- The carried-forward session counts do not advance across a skipped day.
