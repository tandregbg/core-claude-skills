# CR-168 — The layers are built from a recorded source, not from memory

| | |
|---|---|
| **Area** | `README.md` ("Why it is shaped this way", layer 1 heading and one claim), `ecosystem.yaml` (the comment block above `working_loop`, where the reason is already half-written) |
| **Priority** | Low |
| **Status** | **Proposed — rewritten 2026-11-03 at its own merge gate.** The first version claimed the layers are built from the record of work and never from a description. The gate required that claim to be read back against the code; it was, and **two input paths build a durable layer from what a person said**. The claim as written is not one the suite keeps. The claim it does keep is narrower, and is stated below |
| **Contract** | None. Documentation only |
| **Related CRs** | **CR-166** (the orientation entry this claim belongs under), **CR-167** (the same property stated facet by facet in `/company`, implemented v1.93.0), CR-015 and CR-095 (name safety — the same principle applied to one field), CR-085 (`.transcripts/` as the raw archive, one definition), CR-013 (the hypothesis → rule lifecycle, which is where one of the two findings lands) |

Marks: **[E]** observed in the repository · **[H]** not yet run.

---

## The problem

`README.md` names layer 1 **"Capture — get everything in, safely"** and spends the section on the
name-safety chain: undiarized transcripts failing safe, proper-noun verification, owner inference
never guessed **[E]**. All of it is about **safety of handling**.

None of it is about **where the material comes from**, and that is the stronger claim. It is also
the claim that explains the retrieval layer (layer 0) to a reader who does not yet see why it is
there: layer 0's text says *"everything asynchronous is invisible to it by construction"* **[E]** and
frames it as a coverage gap, when it is the same claim — one input where the work has three, so the
material is incomplete, so every layer built on it inherits the hole.

The principle is implemented repeatedly and asserted nowhere **[E]**: `.transcripts/` exists as the
audit trail behind every summary; the orientation set states that *"the summary is what the vault
treats as true"* and that raw material is not re-derived; CR-015 writes `?` rather than infer an
owner; `/company` records a source per facet.

## What the gate found

The first version of this CR asserted: *the material is the record of work that happened — a
transcript, a ledger, an archive — not a description of how the work is done.* Its own merge gate
said that claim had to be read back against the capture paths, not against the documentation that
prompted it, and that any path building a durable layer from a description was the real finding.

**Two paths do exactly that [E]:**

| Path | What it takes in | The durable layer it reaches |
|---|---|---|
| `/company intake` step 4, and the interview the template drives under `init` | What the owner says when asked. *"Record the owner's answer as a dated `interview:<date>` source"*; *"use them to interview the owner ... write only the answers (with source markers) into the facet files"* | A facet file — the profile every other skill reads as standing truth |
| `/insights scan-claude-md` | A folder's `CLAUDE.md`: a person's written description of how they work, mapped to `decision` and `preference` entries by signal words | `_insights.yaml`, and from there promotable to `confidence: rule`, which `/ops` and `/transcript` load back as a **standing instruction** |

Neither is a defect, and neither should be removed. A company's voice and a folder's conventions
exist nowhere but in what a person says about them: there is no record of work to read instead. The
first version of the claim would have made the suite look like it refuses an input it accepts by
design, in two of its four knowledge layers (CR-166's four).

**What both paths actually do is the narrower, true claim.** Neither accepts the statement as a bare
fact:

- the interview answer becomes a **dated source** that `check` can call stale (`company.max_age_days`,
  default 365) **[E]**;
- the `CLAUDE.md` entries carry `source.file: "CLAUDE.md"` and are **deleted and re-extracted** when
  the file changes, so a description can never outlive itself in the corpus **[E]**;
- and a `CLAUDE.md`-derived entry still has to pass the CR-013 lifecycle — confirmed often enough,
  and contradicted by nothing — before it is loaded as a rule **[E]**.

## The change

**1. Layer 1 gains the claim it is missing**, as a sentence before the name-safety list — in the
corrected form:

> Everything a layer rests on is a recorded source: a transcript, a ledger, an archive, or — where
> the fact exists only in what a person says — a dated statement with their answer attached to it.
> Nothing is built from recall at the moment of writing. A recollection written down once is as true
> as the day it was written and has no way to say so; a recorded source has a date, an author and a
> check that can call it stale, and everything downstream inherits whichever one it was built from.

**2. The section heading is widened** from *"Capture — get everything in, safely"*, since the section
now carries both properties. Proposed rather than fixed: *"Capture — what is taken in, and what it
carries with it"*. The wording is a merge-time decision; the requirement is that the heading stop
promising only safety.

**3. The same reason is written once in the contract**, in the comment block above `working_loop`, so
a renderer other than the README has access to it and the claim is not README-only prose.

### Not in scope

- Any new layer. The five (0–4) are right.
- Changing, removing or gating either of the two paths the gate found. Both are correct as built;
  this CR is about what the README claims, not about what the skills do.
- Weakening the name-safety text. It stays; it is simply no longer the whole section.

## Verification

| Check | State |
|---|---|
| The claim is true of every current input path | **[E] re-run 2026-11-03 against the corrected claim.** The two description-fed paths both record provenance and a date, and `scan-claude-md` additionally replaces its own entries when the source file moves. No path writes an unsourced statement into a durable layer |
| Every statement in a facet file carries a source marker, including an interview answer | **[E]** `skills/company/SKILL.md` intake steps 3 and 4; `check` reports *a fact without a source marker* |
| A `CLAUDE.md`-sourced insight cannot become a rule without the CR-013 lifecycle | **[E]** `skills/insights/SKILL.md` Confidence Lifecycle |
| `README.md` generated blocks are untouched | **[H]** — the edit is hand-written prose, outside the `orientation` and `working-loop` markers; `scripts/render-loop.py --check` is the proof |
| No external product, method or person named | **[E]** by construction |

**Why this was not merged with CR-165 to CR-167 (v1.93.0).** Its gate fired. The three changes above
are small and the corrected claim is stronger than the original — but the sentence a reader meets in
the README is the one thing in this CR that matters, and rewriting it in the same session that found
the fault would skip the reading the gate exists to force. The finding above is the deliverable of
this round; the wording is the next one's.
