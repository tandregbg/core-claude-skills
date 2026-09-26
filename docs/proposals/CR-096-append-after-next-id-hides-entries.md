# CR-096 — Appending after `next_id` produces valid-looking YAML that hides entries

| | |
|---|---|
| **Status** | **Implemented 2026-09-26, v1.82.0** |
| **Contract** | none. Strengthens the existing write-time guard; no schema change |
| **Date** | 2026-09-26 |
| **Area** | `skills/transcript/SKILL.md` Step 3.5 write-time vocabulary guard; `skills/insights/SKILL.md` (same guard, referenced) |
| **Related** | CR-020 (write-time vocabulary guard) |

## The failure

`_insights.yaml` has this shape:

```yaml
insights:
  - id: 26
    ...
  - id: 27
    ...
next_id: 28
```

`next_id` is a **top-level key that sits after the list**. An append that adds entries at the
end of the file therefore lands *after* it:

```yaml
    ...
next_id: 28
  - id: 1                    # <- orphaned: wrong indent, duplicate id, after the top-level key
    type: learning
    summary: ...
```

Two distinct outcomes, both bad:

1. **Parse failure.** `yaml.safe_load` raises *"mapping values are not allowed here"*. The whole
   file becomes unreadable — including the 27 entries that were fine.
2. **Silent loss when indentation happens to work out.** The entries sit outside `insights:` and
   every reader that iterates `d['insights']` skips them. No error, no warning.

Outcome 1 is recoverable because it is loud. **Outcome 2 is the dangerous one.**

## Observed

Three occurrences in a single working session, 2026-09-26, across unrelated folders. One of them
had been broken since the previous day: `<venture>/_customers/<customer>/_insights.yaml` held two
insights from a customer meeting, appended after `next_id`, with ids colliding with existing
entries 1 and 2. They were invisible to every reader for 24 hours and were found only because an
unrelated compile run tried to parse the file and failed.

The recovery required renumbering to 28–29, re-indenting, splicing them before the top-level key,
and bumping `next_id` to 30 — mechanical work, but work that only happens if someone notices.

## Why the existing guard misses it

CR-020's write-time guard (`transcript/SKILL.md` Step 3.5) checks:

> `date` is `YYMMDD` (never ISO), `id` is an integer, and **`next_id` equals `max(id)+1` after
> the write**.

It validates the *value* of `next_id`. It says nothing about the **position of the append**, and
position is the whole failure. A writer can satisfy every stated condition and still produce a
file where the new entry is outside the list — because `max(id)` computed over the entries the
parser *can see* is consistent with a `next_id` that the orphan never reached.

`insights/SKILL.md` `migrate` (`normalize` before 1.79.0) goes further and offers to *repair* a missing `next_id` by setting
it to `max(id)+1` — which, run against a file with orphans below it, would cheerfully renumber
around the invisible entries.

## Proposed change

**In section:** `transcript/SKILL.md` Step 3.5, write-time vocabulary guard
**Action:** Add two bullets.

> - **Append inside the list, never at the end of the file.** `next_id` is a top-level key that
>   follows `insights:`. New entries belong **before** it, at the list's indentation. Writing at
>   end-of-file puts them outside the list — which either breaks the parse or, worse, parses
>   cleanly while every reader skips them.
> - **Re-read after writing.** Parse the file back and assert that the entries just written are
>   present in `insights` and that `len(insights)` grew by the number written. This is the only
>   check that catches a positional error, and it is cheap: one load per write.

**Also add** to `insights/SKILL.md` `migrate`, alongside the `next_id` repair row:

> | Entries below the top-level `next_id` key (orphans) | → re-indent into `insights`, renumber
>   from `max(id)+1` to avoid collisions, splice before `next_id`, then bump it. **Report the
>   recovery** — an orphan means some writer appended at end-of-file, and the count is worth
>   knowing. |

## Why re-read rather than a smarter writer

A writer that constructs the file from a parsed structure and re-serialises it (`yaml.dump` over
the loaded dict) cannot produce this bug at all, and that is the better long-term shape. But:

- Serialising the whole file reformats everything — quoting, block scalars, key order — which
  makes diffs unreadable and touches entries nobody edited.
- Several producers write these files, including tools outside this repo.

**The re-read assertion is producer-agnostic.** It catches the error regardless of how the write
was performed, costs one parse, and fails loudly at the moment the damage is done rather than
days later in an unrelated run.

## Verification

Introduce the orphan deliberately in a scratch copy, run the guard, and confirm it fails. Then
run `/insights migrate` across the vault and confirm it reports any existing orphans rather
than silently renumbering around them.

## Evidence

Three occurrences in one session across unrelated folders; one had persisted 24 hours undetected
holding two real insights from a customer meeting. Folder names withheld; the shape is the
finding.

## Outcome (2026-09-26, v1.82.0)

Implemented as proposed. `transcript/SKILL.md` Step 3.5: the process step says *inside the list,
before `next_id`*, and the guard gains the two bullets (append inside the list; re-read and assert
the list grew). `insights/SKILL.md`: the write step says the same, and `migrate` gains the orphan
row — detected from the raw text, recovered **before** any `next_id` repair, and reported with a
count.

**Vault scan at implementation:** 112 `_insights.yaml` files, **0** with orphans or parse failures
(the three occurrences in the CR had already been repaired by hand).

**Follow-up, not in scope:** `_tasks.yaml` has the same shape in some folders — of 88 ledgers, some
put `next_id` after `tasks:`. None was affected at the scan, but the same end-of-file append would
hide a task the same way. Worth the same guard in `/tasks`, as its own CR.
