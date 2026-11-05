# CR-178 — The feedback step is an identifier, and it defeated its only reader

| | |
|---|---|
| **Status** | **Implemented v1.96.0** (2026-11-05), contract 50 |
| **Contract** | `feedback_steps` declares the steps an `edge_case` or `correction` may name. Additive; a reader that ignores it reads what it read at 49 |
| **Date** | 2026-11-05 |
| **Area** | `ecosystem.yaml` (`feedback_steps`), `transcript` (Step 4.5), `ops` (Step 5.5) |
| **Related CRs** | **CR-049** (identifiers are English and are data, not free text — the rule this is the third instance of), **CR-152** (the same defect in the task ledger's `source.type`, fixed two days before this), CR-127 (a legacy spelling is read and never rewritten), CR-013 (the feedback the field describes), CR-175 (the aggregate that made this visible) |
| **Origin** | `/insights propose`, 2026-11-05 — the first proposal this suite has generated from its own compiled patterns and shipped |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E] Measured 2026-11-05 over 362 active `edge_case` and `correction` entries: 120 distinct
spellings of `source.step`.**

| Spelling | Entries |
|---|---|
| `1` | 119 |
| `Step 1` | 10 |
| `Step 1 -- speaker attribution` | 9 |
| `Step 1 -- proper-noun verification` | 8 |
| `Step 1 (proper-noun verification)` | 6 |
| `Step 1 / speaker attribution + proper-noun verification` | 6 |
| `step 1 / CR-016`, `step 1 / CR-015`, `1 (speaker attribution)` | 5 each |
| … about 110 more | 1–4 each |

They are nearly all the same step. **273 of 362 entries name Step 1 of `/transcript`** — parsing and
speaker attribution — and every one of them was written by Step 4.5, the silent feedback step. So
the field means *where the problem occurred*, which is right and useful, and the skill asked for it
as `"step number where it occurred"`: a description, in a field that is an identifier.

### The cost is not untidiness

`/insights compile` **Pass 1 is specified to cluster execution feedback by `source.skill` +
`source.step`.** With 120 values it cannot. The 2026-11-05 compile run clustered on tag families
instead, and the grouping this field exists for was never performed — silently, because the pass
still produced output.

**A field that defeats its only reader is worse than an absent one, because it looks like it is
working.** That is the same shape as the audit's other findings this week: an instrument that runs,
and a signal nobody receives.

### Third instance of one defect

- **CR-049** stated the rule: identifiers are English and live as data, not as literals or prose.
- **CR-152** (v1.95.0, two days before this) found twenty dialects in the task ledger's
  `source.type` for exactly this reason — a field asking for a controlled value without declaring
  the values — and fixed it by moving the enum into the contract.
- **This is the field next door**, written by the same two skills, and nobody had looked at it
  because the only reader that would notice had quietly worked around it.

## The change

**1. `feedback_steps` in the contract**, per skill, each id with a one-line label, ids as **strings**
(`"5.4"` and `"5.5"` as YAML floats would collide and reorder). The steps that *write* entries —
`transcript` 4.5, `ops` 9 — are declared too, and their labels say so: an entry about the feedback
step itself has to be expressible.

**2. Both writers take the id from the list.** `step: "1"`, not `step: "Step 1 -- speaker
attribution"`. What the entry is *about* goes in `tags`, which is the field that already exists for
it and which the roll-ups already read.

**3. Nothing is rewritten.** **[E]** The id is recoverable from the first token in **313 of 362**
entries, so no alias map is needed and CR-127's precedent holds: a legacy spelling is read, never
written. The remainder carry no step at all, which is a different and smaller gap.

## What this is not

- **Not a new field.** `tags` already carries what the long spellings were trying to say.
- **Not a migration.** Not one of the 362 rows is touched.
- **Not a closed list for its own sake.** The steps are the skills' own headings; a test asserts
  every declared id has a real heading in that skill, so the list cannot drift from the thing it
  names.

## Acceptance

- `feedback_steps` declares the ids per skill, as strings, each with a label. **[E]**
- Every declared id matches a real `## Step N:` heading in that skill. **[E]** asserted by test.
- Both writers document the id-alone rule and name the declaration. **[E]**
- Every observed spelling yields its id by first token. **[E]**
- **[H] The next `/insights compile` Pass 1 clusters on `skill` + `step`** — which is the point, and
  is only provable on the run after writers have been using the rule for a while.
