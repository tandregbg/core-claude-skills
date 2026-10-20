# CR-138 — The task audit's shape lives in the skill, not only in the script

| | |
|---|---|
| **Status** | **Proposed** (2026-10-20) |
| **Contract** | additive — documents an existing output; no new fields, no behaviour change |
| **Date** | 2026-10-20 |
| **Area** | `inbox` (SKILL.md), `skills/inbox/survey.py` docstring |
| **Related CRs** | CR-134 (the outbox reports what is there — same gap on the other side), CR-135 (the ledger uses the object model, which this view renders), CR-022 (the triage working surface) |

## What happened

An operator and an assistant settled the shape of the task audit in a working session on the morning
of 2026-10-20: grouped **venture → context**, with the state (overdue, no age, …) travelling on each
row instead of defining the sections, one row per open entry, and a trailing empty **Godta** column
for the operator's decision. It took several rejected attempts to get there; the operator's objection
to the earlier ones was that they were lists without the detail needed to decide.

**That evening, the same session rebuilt it differently** — sectioned by problem type (overdue /
undated P2 / one project's cluster / no age), with different columns in each section, and showing
**79 of 215 open entries** instead of all 215. The operator noticed within a minute and asked whether
the agreed shape was not in the skill.

**It is not.** `skills/inbox/SKILL.md` contains no occurrence of `survey`, `_uppgifter`, `verksamhet`,
`--table` or `--markdown`. The whole format exists as code in `survey.py`, whose own docstring
describes `--markdown` as *"the situation half of an audit"* — half an input, not the settled view.

## Why this is the same failure as CR-134, mirrored

CR-134 found that the outbox audit was hand-written with its numbers baked in, so each pass answered
the same question differently. The fix was to generate the situation half.

Here the generation already exists and is correct. What is missing is the **contract**: nothing states
that `_inbox/_uppgifter.md` is the task audit, that its filename is stable so the operator can keep it
open, that it is grouped venture → context, or that every open entry appears exactly once. So any
surface — a different session, the same session past a context compaction, another assistant — meets
the requirement by building something plausible instead.

**[E] The drift was caught by the person, not by any check.** That is the measurement: a format with no
written contract has no detector, and the operator becomes the regression test.

## The shape, as it stands today

| Element | Rule |
|---|---|
| Filename | `_inbox/_uppgifter.md`, **stable across runs** — it is meant to stay open, not to accumulate dated copies |
| Grouping | `## <Venture> — N poster` then `### \`<context>\` — N · projekt **<Project>**` |
| State | Travels **with the row** (`förfallen 31 d`, `ingen ålder`). It never becomes a section — one entry can hold several states, and sectioning by state duplicates or hides it |
| Row | `# | Verksamhet | Projekt | Läge | Uppgift | Förslag | ✓/? | Godta` |
| Coverage | **Every open entry appears exactly once.** A subset is a different document and must say so |
| Header | Movement line (decided today), open count, proposals by kind, ✓ against `?`, the `Godta` legend, and a per-venture summary table |
| `Godta` | Left empty by the generator. Empty means the proposal stands; the operator writes a date, `R`, `Ö` or `S` |
| `✓` / `?` | Whether the proposal has a signal in the entry's own text or is a guess. The operator reads the guesses first |

## Proposal

1. **Write the table above into `skills/inbox/SKILL.md`** as a `### \`/inbox survey\`` subcommand
   section, next to `/inbox triage` which documents the sibling surface (CR-022). A reader of the
   skill should be able to reproduce the file without reading the script.
2. **Correct `survey.py`'s docstring.** `--markdown` is not "the situation half of an audit" on this
   path; with `--table` it is the audit. Say which flags produce the operator-facing view.
3. **State the relationship to `daglig-triage.md`.** Both render `_tasks.yaml`; the triage answers
   *what do I do now* and is cut to the dated and the prioritised, while this one answers *what is
   there* and is complete. Without that sentence the two look like duplicates and one gets dropped.
4. **Name the failure in one line** where the shape is given: *a subset presented in this file's name
   is a regression* — because that is the form the drift took, twice, and it reads as a reasonable
   document unless the count is checked against the ledger.

## What this does not propose

No change to `survey.py`'s behaviour, no new fields, no enforcement. The generator is right; only its
contract is missing. A check that the file holds as many rows as the ledger has open entries is
cheap and belongs in `/ops check`, but it is a separate decision and is not asked for here.
