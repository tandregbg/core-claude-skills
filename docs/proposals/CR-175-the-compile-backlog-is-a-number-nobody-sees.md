# CR-175 — The compile backlog is a number nobody sees

| | |
|---|---|
| **Status** | **Proposed** (2026-11-04) |
| **Contract** | none — one aggregate line in an existing check, one existing stamp read differently |
| **Date** | 2026-11-04 |
| **Area** | `ops` (`check` class 2), `insights` (`status`), `analytics` |
| **Related CRs** | **CR-020** (the `last_compiled` stamp, written so a never-running loop is visible instead of silent), CR-013 (the hypothesis → rule lifecycle this feeds), CR-094 and CR-098 (why promotion is hard and honest), CR-027 (the wiki the corpus renders into), CR-019 (the sweep that reports what nobody looks at) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E] Measured on one vault, 2026-11-04: 133 insight ledgers, 3,389 entries, and 42 of the 133
ledgers are not compiled.**

| | |
|---|---|
| Ledgers with no `last_compiled` stamp at all | **24** (the largest carries 58 entries) |
| Ledgers compiled, but >30 days behind their own newest entry | **18** (worst: 44 days) |
| Compiled and current | 95 |
| Entries in the corpus | **3,389** |

The knowledge loop is the suite's own thesis — capture once, confirmed patterns become standing
rules, the skills get smarter in the folders you work in most. **A third of the ledgers are not
participating in it**, and the corpus has reached a size where that is no longer a small loss.

### CR-020 wrote the stamp for exactly this, and the stamp is working

This is not a missing mechanism. `last_compiled` exists **because** a never-running synthesis loop
is otherwise silent, and `check` class 2 already reads it: *"`_insights.yaml` whose `last_compiled`
stamp is absent or >30 days older than its newest entry (compile never ran / is stale)"*.

**The check is correct and fires per folder.** Which means the operator meets the fact 42 times,
scattered among 1,215 other findings from eleven other classes, each time as a single line about a
single folder. **Nothing anywhere states the number 42, or the number 3,389.**

That is the difference between a defect and a backlog. One stale ledger in a quiet folder is noise.
Forty-two of a hundred and thirty-three is a loop that has stopped, and those are the same finding
counted differently.

### The shape of the failure is the one the suite keeps finding

A measurement that exists, is correct, is read by a check, and is never aggregated into the sentence
that would make someone act. The same shape as CR-169 (a drop zone with no ageing rule), CR-170 (an
exit nobody took over) and CR-138 (a detector that errored for a week): **the instrument was fine
and nobody was shown the total.**

## Proposal

**1. `check` class 2 opens with one aggregate line**, before the per-folder findings:

```
insights: 133 ledgers, 3389 entries. 24 never compiled, 18 stale (>30d), 95 current.
```

Where any ledger is uncompiled, add the consequence in plain words — *the promotion pass has not run
over N entries, so no hypothesis in them can become a rule* — because the number alone does not say
what is lost.

**2. The same line in `/insights status`**, which is where a person goes when they are already
thinking about the corpus. Today `status` answers for the folder in hand; this is the vault answer.

**3. A never-compiled ledger is reported differently from a stale one.** They are currently one
finding with an `or` in it. *Never* means the folder has been accumulating since it was created and
nothing has ever read it back; *stale* means the loop ran and then stopped. The first is a setup
gap, the second is a cadence gap, and they have different fixes.

**4. `/analytics` counts the corpus over time.** It already measures creation trends and backlog;
corpus size against compiled share is the same kind of number and is the one that says whether the
loop is keeping up with capture. **[H]** Worth checking whether the ratio moves with vault growth —
if it degrades steadily, the finding is about cadence, not about any one run.

## What this is not

**Not a scheduler.** Nothing in this CR runs `compile`. The suite's position that skills observe and
a person acts (CR-019) is unchanged, and an automatic compile would promote rules nobody read — the
precise failure CR-098 and CR-100 were written to prevent.

**Not a change to promotion.** The gates, the contradiction check and the review mark are untouched.
This CR is about knowing how much has never reached them.

**Not a new file.** No report, no state, no stamp. One line in a check that already reads the data.

## Acceptance

- `check` class 2 states ledger count, entry count, and the never/stale/current split before any
  per-folder finding.
- Never-compiled and stale are separate counts with separate wording.
- `/insights status` prints the same three numbers for the vault.
- Nothing is compiled, promoted or written by any of it.
