# CR-133 — A sent item ages out: closing cannot depend on a field nobody fills

| | |
|---|---|
| **Status** | **Implemented** (2026-10-20) |
| **Contract** | additive — one new aging finding, one new offered outcome text; no new fields, no new status forms |
| **Date** | 2026-10-20 |
| **Area** | `outbox` (SKILL.md `close`, `close --all-sent`, `resolved.py`), `ops` (`check` outbox aging) |
| **Related CRs** | CR-019 (`close --all-sent`), CR-047 (`avskriven` requires an outcome), CR-120 (aging of staged items; `hanterad`), CR-131 (a *not sent* outcome needs no reason) |

## What happened

`close` gates on two fields: every `Svar förväntas på` box ticked, and `## Utfall` populated. CR-019 added
`close --all-sent` so a backlog could be cleared in one sitting, and `/ops check` offers it when it finds
sent-but-unarchived items.

**[E]** Measured on one vault, 2026-10-20, after a full manual pass had already taken the queue from 166
items to 127:

| Of 77 items with status `skickad` | |
|---|---|
| with `## Utfall` populated | **10** |
| with every `Svar förväntas på` box ticked | 29 *(of which 25 have no such section at all)* |
| **with both — i.e. closable** | **1** |

`close --all-sent` was available the whole time. Running it would have skipped 76 of 77 and closed one.
**The command was never the bottleneck.**

## Why the gate does not close

A send is an *observation*: a dispatching surface writes `skickad` with a date, and it is right every time.
A resolution is a *return visit* — someone must come back to the manifest after the reply and write what
happened. **Nothing triggers that visit.** No reply is watched for; no deadline fires.

So every sent item stops one step short of closable, permanently, and the queue can only grow. On this
vault it reached 166 items, the oldest sent 52 days earlier and still open.

**[E]** Which of the two fields is dead is visible in the data: **nine items have a populated `Utfall` but
unticked boxes** — someone recorded the outcome and never ticked. The reverse case (ticked boxes, no
outcome) numbered four. The checkbox is bookkeeping nobody maintains; the outcome is the field that carries
meaning, and it is written one time in eight.

## Proposal

**1. A sent item with no open reply expectation is closable now.** 25 of the 77 have no
`Svar förväntas på` section at all. A send that never expected an answer is finished when it goes out.
`close` offers `Skickat <date>. Inget svar förväntades.` as the outcome, in the shape CR-131 settled: a
complete outcome that states a fact rather than inventing a reason.

**2. Ticked boxes are not required when an outcome exists.** Where `## Utfall` is populated, `close` stops
treating unticked boxes as a blocker and reports them instead. The outcome is the record; the boxes are its
checklist. Today the nine items whose outcome *was* written are held back by the field that was not.

**3. A sent item ages out.** Past a threshold (`30` days, the same one CR-120 uses for staged items),
`/ops check` reports a sent item with no reply and no outcome, and offers `close` with
`Skickat <date>. Inget svar inkom inom <n> dagar.` **Report and offer — never automatic.** Deciding that a
thread is over is the operator's call; what the rule removes is the need for them to notice it first.

**[E]** Applied to the measured vault, 1, 2 and 3 make 34 of 77 closable without a single judgement call —
the rest are genuinely waiting, which is what `_outbox/` is for.

## Why a threshold rather than a reminder

A reminder relies on the same return visit that does not happen. The aging rule needs nothing from anybody:
the date is already in the manifest, and the threshold reads it.

## Not in scope

Watching for replies. That is a mail-integration question and belongs to a dispatching surface, not to this
repository. This CR makes the queue drain without it.

## As built

- `resolved.py`: `offered_outcome()` (+ `sent_date()`) returns the two outcome texts; `--survey` carries it as
  `offered_outcome` per item and `ages_out` in the counts and the generated markdown. Points 1 and 2 were
  already in `is_closable()` (no reply section, or a written outcome that does not defer) and are unchanged.
- `outbox` SKILL.md (`close`, `close --all-sent`) and `ops` SKILL.md (`check` outbox finding) describe the
  offer. Never applied automatically.
- Threshold: the existing `--stale-days` default of 30; no new `ecosystem.yaml` key.
- Tests: `tests/test_cr133_ages_out.py`.
- Review fixes: an aged-out offer needs at least one unticked box (all ticked is not "no reply"); a reply
  section that is present but empty or a placeholder is no longer read as "nothing expected" (`open_replies`
  returns 0, not None); `--survey` carries `unticked_reported` per item and `unticked_with_outcome` in the
  counts, which is where point 2's "reports them" is produced; the Area row no longer lists `ecosystem.yaml`.
