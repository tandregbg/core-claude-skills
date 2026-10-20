# CR-132 — `Kanonisk källa` and a declared status word are required when material is staged, not reported afterwards

| | |
|---|---|
| **Status** | **Implemented** (2026-10-20) |
| **Contract** | additive enforcement — no new fields; two existing requirements move from report-time to write-time |
| **Date** | 2026-10-20 |
| **Area** | `ops` (staging), `outbox` (SKILL.md, `resolved.py`), `ops` (`check`), any dispatching surface that creates a manifest (CR-115) |
| **Related CRs** | CR-032 (`Kanonisk källa` is required), CR-103 (status words are declared, not invented), CR-115 (a dispatcher may create a missing manifest), CR-102 (manifests edited in place) |

## What happened

Both requirements already exist. Neither is enforced where the answer is known.

**CR-032** states the field is required and explains why: the 2026-08-28 audit found 86 outbox items of
which only 3 of 71 manifests named a source, which made *"is this a copy or the original?"* unanswerable
without opening every folder — and made a bulk clean-up unsafe, because the mail texts and manifests
existed **only** in `_outbox/`. CR-032's own enforcement is `list` flagging it and `archive` warning.

**[E]** Measured on the same vault, 2026-10-20 — 26 months after CR-032: **36 of 127 manifests had no
`Kanonisk källa`.** 30 % of the queue, and the same question as unanswerable as in August.

**CR-103** states status words are declared, not invented, and that `/ops check` *"reports undeclared
status words with the closest declared one; it never rewrites them."*

**[E]** Same measurement: **8 items carried undeclared status words** — `retired`, `parkerad`, `INAKTUELL`,
`förfallen`, `klar att läsa`, `staged, ej skickat`, `redo att skickas`. One had no parseable `Status` field
at all, because it was written `**Status: SKICKAD 2026-10-01.**` with the colon *inside* the bold: every
tool keying on `**Status:**` saw the item as statusless, and it fell out of every count.

## Why reporting after the fact does not work

Both holes refill. A report tells the operator that 36 fields are missing; it does not stop the thirty-
seventh. And the determination is cheapest exactly where it is skipped — **at staging, the author knows
whether the folder is a rendering or the original.** At clean-up time nobody does.

**[E]** Resolving the 36 by hand on 2026-10-20 took a mechanical probe (a distinctive line from each
attachment, searched across the vault outside `_outbox/`) because the authors' knowledge was gone. The
result: 11 had the source under a different label (`Källa:`), 20 were verifiably unique, **4 had their
original elsewhere in the vault** — and those 4 are the ones a bulk default would have got wrong. Writing
*"the original lives here"* on a copy tells the next clean-up to preserve the copy and drop the original.

## Proposal

**At staging — `/ops`, `/outbox`, or any surface that creates a manifest (CR-115):**

1. `Kanonisk källa` is written. The two valid answers are unchanged: a path, or `ingen (originalet bor här)`.
   A staged item without it is not written — the author is asked, since the author is the one who knows.
2. `Status` is written as one of the declared forms only. A free phrase is not accepted at write time.
3. The field is written as `**Status:** <value>` — the colon outside the bold. A status that a reader cannot
   parse is worse than a missing one, because it counts as present.

**`/ops check` keeps reporting and still never rewrites** (CR-103 stands). The check becomes a backstop for
legacy items rather than the only line of defence.

## Migration

None required. The 36 fields and 8 status words in the measured vault were filled on 2026-10-20; this CR is
about the thirty-seventh.

## Not in scope

Validating that a `Kanonisk källa` path resolves. CR-120 already settled that a path into another repository
is **unverifiable, not broken**.

## As built

- `skills/outbox/resolved.py`: `staging_problems(text)` and `--validate <manifest|->` (exit 1 plus JSON
  problems; writes nothing). It refuses a missing or placeholder `Kanonisk källa`, an undeclared status
  (naming the closest declared form), and a `Status` not written `**Status:** <value>`.
- `skills/outbox/SKILL.md` (section on `Kanonisk källa`) and `skills/ops/SKILL.md` (Staging): surfaces
  that create a manifest, including CR-115 dispatchers, run the check before writing and ask the author
  rather than defaulting the source.
- `/ops check` is unchanged: it still reports and never rewrites.
- Tests: `tests/test_cr132_staging_gate.py`. No contract change.
