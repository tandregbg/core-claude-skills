# CR-168 — The layers are built from the record of the work, not from a description of it

| | |
|---|---|
| **Area** | `README.md` ("Why it is shaped this way", layer 1 heading and one claim), `ecosystem.yaml` (the comment block above `working_loop`, where the reason is already half-written) |
| **Priority** | Low |
| **Status** | Proposed (2026-11-03) |
| **Contract** | None. Documentation only |
| **Related CRs** | **CR-166** (the orientation entry this claim belongs under), CR-015 and CR-095 (name safety — the same principle applied to one field), CR-085 (`.transcripts/` as the raw archive, one definition), CR-125 (`/company`, where the same claim is made facet by facet in CR-167) |

Marks: **[E]** observed in the repository · **[H]** not yet run.

---

## The problem

`README.md` names layer 1 **"Capture — get everything in, safely"** and spends the section on the
name-safety chain: undiarized transcripts failing safe, proper-noun verification, owner inference
never guessed **[E]**. All of it is about **safety of handling**.

None of it is about **where the material comes from**, and that is the stronger claim. The suite
builds its process and knowledge layers from the record of work that actually happened — a
transcript, a ledger, a repository archive, a chat export. The alternative, which is what most
context-building does, is to ask the person to describe how they work and write that down.

The difference is not a preference:

- A description is a summary of a summary. The person recalls their process, selects what seems
  worth saying, and states it in general terms. Three compressions before anything is written.
- A record is the primary source. What was decided, who owns it, what was not resolved, and what was
  said in the words it was said in.

The repository already acts on this everywhere **[E]**: `.transcripts/` exists as the audit trail
behind every summary; the orientation set states that *"the summary is what the vault treats as
true"* and that raw material is not re-derived; CR-015 writes `?` rather than infer an owner;
`/company` records a source per facet. **The principle is implemented five times and asserted zero
times.**

It is also the claim that explains the retrieval layer (layer 0) to a reader who does not yet see
why it is there. Layer 0's own text says the problem plainly — *"everything asynchronous is invisible
to it by construction"* **[E]** — but frames it as a coverage gap. It is the same claim: one input
where the work has three, so the record is incomplete, so the layers built on it would inherit the
hole.

## The change

**1. Layer 1 gains the claim it is missing**, as a sentence before the name-safety list:

> The material is the record of work that happened — a transcript, a ledger, an archive — not a
> description of how the work is done. A description is written from memory, selects what seemed
> worth saying, and is as true as the day it was written; the record is the primary source, and
> everything downstream inherits whichever one it was built from.

**2. The section heading is widened** from *"Capture — get everything in, safely"* to name both
properties, since the section now carries both. A heading is proposed rather than fixed here:
*"Capture — the record of the work, taken in safely"*. The wording is a merge-time decision; the
requirement is that the heading stop promising only safety.

**3. The same reason is written once in the contract**, in the comment block above `working_loop`,
so that a renderer other than the README has access to it and the claim is not README-only prose.

### Not in scope

- Any new layer. The five (0–4) are right.
- Changing what is captured, how, or any behaviour at all.
- Weakening the name-safety text. It stays; it is simply no longer the whole section.

## Verification

| Check | State |
|---|---|
| The claim is true of every current input path | **[H]** — read back the capture skills before merge. If any path builds a durable layer from a person's description rather than a record, this CR is making a claim the suite does not keep, and that path is the real finding |
| `README.md` generated blocks are untouched | **[E]** by construction — the edit is in hand-written prose, outside `orientation:start/end` and `working-loop:start/end` |
| `scripts/render-loop.py` still reports the working-loop block as matching | **[H]** |
| No external product, method or person named | **[E]** by construction |

The first row is the one that matters. This CR asserts a property; the merge should not happen until
someone has checked the assertion against the code rather than against the documentation, because
the documentation is what prompted it.
