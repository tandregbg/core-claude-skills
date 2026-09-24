# CR-079 — Starting a vault from an existing history

| | |
|---|---|
| **Status** | Proposed |
| **Contract** | additive (27 → 28), depends on CR-077 |
| **Date** | 2026-09-23 |
| **Area** | `/inbox`, `vault_conventions` (`_inbox/.import/`), `.transcripts/` |
| **Related CRs** | CR-024 (`.ephemeral/` vs `_inbox/.files/` — destiny decided at the drop), CR-012 (inbox schema), CR-015 (undiarized transcript owner safety), CR-036 (singleton placement) |

## The problem

A new vault starts empty, so it starts *ignorant*. A user who has months of material in a capture
product begins with only what is recorded from today onward, and the first synthesis is built on a
few days of fragments — which reads as wrong, because it is thin rather than because it is broken.

The user's own reaction on seeing it: several of the items had nothing to do with each other. They
were accurate; there was simply not enough to find the pattern.

**A vault's value is proportional to the history it can see, and today there is no way to give it
any.**

## Two purposes, one mechanism

1. **Starting up.** Build the vault from everything that already exists, not only from what happens
   next.
2. **No lock-in.** A user can take the whole dataset elsewhere. This matters more once the product
   is paid for: whoever pays should know the data comes out.

The second is a product export concern and sits outside this contract (CR-077). **This CR covers
only what happens once a dump arrives at the vault**, which is the half core-skills owns.

## Why the inbox cannot take it as it stands

`/inbox` processes **one item at a time**: classify, route, hand to a downstream skill, archive.
That is correct for a captured note and wrong for four months of transcripts.

- `_inbox/` is a **door, not a home** and normally carries very few files. A dump breaks that on
  arrival.
- The material's destination **cannot be known before it is read** — which is precisely the
  condition CR-024 uses to separate `_inbox/.files/` (has a destiny) from `.ephemeral/` (has none).
- Months of transcripts **do not fit in one context window**. Any honest startup runs in passes.

## The question that was open, and why the answer is a third thing

The working document asked whether `.ephemeral/` should move inside `_inbox/`, so a new user has
one place to put things instead of two.

**It should not.** `.ephemeral/` means *this may die*; `_inbox/` means *this is going somewhere*.
CR-024 exists to hold those apart, and merging them re-creates the confusion it was written to end.
The sweep rule would also have to change shape inside the inbox.

But the objection that prompted the question is real: **an import is genuinely neither.** It is not
scratch — it is the most valuable material the user owns. It is not a queue item — it has no
destination yet. So it is a third surface, not a merge of two.

**Proposed: `_inbox/.import/`** — a staging area that exists only during startup and is emptied by
the process that reads it.

| | `.ephemeral/` | `_inbox/.files/` | **`_inbox/.import/`** |
|---|---|---|---|
| Destiny | none | known at drop | **discovered by reading** |
| Lifecycle | may die; swept at 14 days | pass-through | **consumed, then empty** |
| Normal state | has content | has content | **empty** |

Dot-prefixed under CR-034: it is not read in everyday work. It is read once.

## The startup mode

`/inbox import` — distinct from the per-item path, and deliberately not automatic:

1. **Raw transcripts land in `.transcripts/` directly**, not in the inbox. The seal (summary is the
   truth, raw material is the audit trail) then applies from the first minute rather than being
   applied retroactively. This also keeps the dump out of the working surface entirely.
2. **Read in passes** — by tag, by month, by whatever the source grouping is — because the context
   window is a hard limit and pretending otherwise produces a confident summary of the last batch.
3. **Propose a structure, do not create one.** The startup reads, then suggests folders, tags and
   contacts. The user confirms. A vault whose structure was generated without consent is a vault
   nobody trusts.
4. **State coverage plainly.** How many sources were read, what period they span, what was skipped.
   A user must be able to tell thin from broken — the failure that prompted this CR.
5. **`.import/` is empty when the run ends**, and an empty `.import/` is the normal state.

## Speaker attribution is a precondition, not a detail

CR-015 already governs undiarized transcripts. A bulk import multiplies the exposure: if speakers
are wrong in the source, every extraction, tag and insight built on the import inherits the error
silently, across months of material at once.

**The import states what it is trusting** — diarized or not, corrected or not — and refuses to
guess an owner it was not given. Wrong attribution at this volume is worse than no import.

## Scope / non-goals

- **Does not specify an export format.** What a product exports, and in what shape, is that
  product's concern (CR-077). This CR states only what the vault side accepts: markdown plus
  frontmatter per the inbox schema, or transcripts with speaker labels.
- **Does not merge `.ephemeral/` into `_inbox/`.** Explicitly rejected above, so the question is
  closed rather than left to be re-asked.
- **Does not make import automatic.** No watcher, no folder that processes itself. Startup is a
  deliberate act with a person present.
- Does not change `_inbox/`, `.ephemeral/` or `.transcripts/` as declared. Additive.
