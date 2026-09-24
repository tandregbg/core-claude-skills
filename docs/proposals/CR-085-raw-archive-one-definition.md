# CR-085 — `/ops` archives its source, and the contract has one definition

| | |
|---|---|
| **Status** | **Implemented 2026-09-24, v1.75.0** |
| **Contract** | additive — `working_loop` gains an output; two frontmatter fields on an existing file type |
| **Date** | 2026-09-24 |
| **Area** | `ops`, `ops-base`, `transcript`, `working_loop` in `ecosystem.yaml` |
| **Related CRs** | CR-010 (`.transcripts/` declared), CR-062 (`working_loop` rendered from the contract), CR-078 (documentation belongs to its owner), CR-084 (the agenda states its sources) |

## The defect

`/transcript` has **Step 2.5**: after the summary has a target folder, the verbatim input is archived
to `<vault-root>/.transcripts/<summary-stem>-raw.md`, the summary gets a `Råmaterial:` back-link, one
confirmation line is printed, and the file falls under the read-back lock.

**`/ops` has no such step** — although `/ops` is documented as a superset of `/transcript`
functionality. A meeting processed with `/ops` produces a summary with no way back to what was
actually said. The source is simply gone.

It is the kind of defect that cannot announce itself: the summary looks complete, and the absence is
only visible to someone who goes looking for a file that was never written.

## Why it happened, which is the part worth fixing

**The contract was written twice, in one place.** `/transcript` holds it; `/ops` was built alongside
and never inherited it. Nothing compared them, because nothing could — there was no single definition
to compare against.

A patch that copies Step 2.5 into `/ops` reproduces the cause. **Two copies is how this happened.**

## Proposal

### 1. One definition, two callers

Move the raw-archive contract into **`ops-base`**, the shared framework both skills already extend.
`/ops` and `/transcript` reference it; neither restates it.

The contract is unchanged in substance — location, filename stem, frontmatter, back-link, single
confirmation line, read-back lock, and the skip conditions (the user said not to save it, or there is
no target folder).

**This is CR-078's rule applied inward:** the behaviour belongs to one owner, so the description does
too. A grep for a second copy of the contract should find nothing.

### 2. `/ops` runs it

After the target folder is known and before post-processing. Same step, same silence, same lock.

Where the input came from a transcript store rather than pasted text, the frontmatter records the
store's **document id, original filename, duration and transcript variant**. The id is what makes the
raw file traceable back to the recording it came from — without it the archive proves only that
*something* was said.

### 3. One session, several destinations

A single recording can cover separable subjects that belong in different folders. Today the
frontmatter cannot express that: `summary:` is singular.

- **One raw file per input, never one per summary.** The input is the thing that happened; the
  summaries are readings of it.
- `summaries:` — a list of every summary the input fed. `summary:` stays as the primary, so existing
  files keep working.
- `disposition:` — one line stating how the session was split and why.
- Every summary carries the same `Råmaterial:` back-link.
- A part routed to a frozen snapshot is **named in `disposition:` but never linked** — a snapshot
  carries no links in either direction, and a raw file pointing at one would breach that from outside.

### 4. Declare it in the working loop

The after-meeting step in `working_loop` lists the raw archive in `produces`. `/ops help` renders from
that block and `check-components.py` validates it, so the step becomes visible to a reader and
checkable by a script rather than resting on skill prose.

## A boundary this CR states rather than moves

A vault may carry a rule that one conversation must never be split across two **ledger ids** — written
for corpora where each entry is a ledger row with its own identity and attribution.

**That is not this.** Ordinary summaries may split a session by subject, and this CR permits it. The
ledger rule governs ledger corpora. If a vault means it more widely, that is a decision for that
vault's own conventions to state; the skill keeps the conservative default and does not infer it.

## Acceptance

- `/ops` on a transcript writes `.transcripts/<stem>-raw.md` unasked, and the summary carries the
  back-link. Verified on a real run.
- One raw-archive definition exists; a grep finds no second copy.
- A split run produces **one** raw file with `summaries:` and `disposition:`; each summary links it; a
  snapshot part is named, not linked.
- `working_loop` updated and `check-components.py` passes.
- Release guard and semantic review pass.

---

## Outcome (2026-09-24, v1.75.0)

The contract lives in `ops-base` as **RAW SOURCE ARCHIVE**. `/transcript` Step 2.5 and the new
`/ops` Step 5.4 both point at it and neither restates it; a grep for the read-back lock finds one
definition and two references.

**A second defect surfaced while wiring it up.** `check-components.py` refused the new loop output:
`.transcripts/` was **never declared** in `vault_conventions`. The folder has been in use and
read-blocked since Step 2.5 was written, and the rules block already named it as a surface folder
walks must skip — but as an undeclared path it was invisible to every check. Now declared, with its
writers, its explicit-request-only readers, and the lock in its lifecycle.

That is the same failure shape as the one this CR set out to fix: something real, in use, and
unwritten, so nothing could compare against it.
