# CR-176 — The triage check still assumes a hand-sorted document

| | |
|---|---|
| **Status** | **Proposed** (2026-11-04) |
| **Contract** | none — one check reads a declaration it already has |
| **Date** | 2026-11-04 |
| **Area** | `ops` (`check` class 7), `inbox` (`triage refresh`, SKILL.md), `ops-config` (`view_files`, CR-171) |
| **Related CRs** | **CR-022** (the triage surface, whose premise this corrects), **CR-035** (`_tasks.yaml` is the source of truth and the working document is a GENERATED VIEW — the CR that superseded it), CR-171 (`view_files`, where the document's name now lives), CR-162 (the generated audit over the same ledger), CR-019 (class 7) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E] Measured on one vault, 2026-11-04.** `check` class 7 ran against the declared triage document
and reported its buckets, its tick state and its week anchor. Three of the four things it checks
cannot be true of that file, because **the file is generated**. Its own header says so:

> *Generated from `_tasks.yaml` — do not edit here. Add and change in the YAML, then run
> `render_triage.py`.*

Class 7 reads, in the shipped wording: *"INKORG items unsorted >7 days, `[x]` items not yet moved to
the KLART archive, week anchor >7 days stale"*, and offers `/inbox triage refresh`, *"which handles
all but the sorting — that stays human."*

| What class 7 assumes | What the vault has |
|---|---|
| A human sorts items between buckets | Buckets are **rendered** from `_tasks.yaml` fields |
| `[x]` items wait to be moved to an archive | A ticked item changes `status:` in the YAML and leaves the view on the next render |
| The week anchor is hand-maintained and goes stale | The anchor is written by the renderer |
| `/inbox triage refresh` does the mechanical upkeep | The renderer does; `refresh` would edit a generated file |

**The check is not wrong about the file. It is wrong about who writes it** — and CR-034's own rule
is that who writes a surface is a declared property, not something a reader infers.

### The premise was superseded three releases before the check was written

CR-022 built the triage doc as *the* human surface, with the design principle inverted from
everything else: **skills adapt to the triage doc; the triage doc never adapts to skills.** That was
right when the markdown was the system of record.

CR-035 then made `_tasks.yaml` the source of truth and demoted the markdown to a generated view —
and `vault_conventions` has said so ever since: *"GENERATED VIEW of `_inbox/_tasks.yaml` (CR-035).
NEVER hand-edited; tools must not write to it."* **Class 7 was never updated to read that
declaration.** It is the same class of defect as CR-171's (a rule shipped, and the thing it governs
drifted past it unchecked) and CR-169's (a surface declared in one place and checked against an
older assumption in another).

### What the check should be reporting instead

The 134 overdue items it surfaced are real and are the finding that matters — **[E]** oldest dated
three months back. But they are overdue **tasks**, carried into the view from the ledger. Reporting
them as a property of the markdown sends the operator to the wrong file: editing the view fixes
nothing and is overwritten by the next render.

## Proposal

**1. Class 7 resolves who writes the document before checking it.** The declaration already exists
in two places — `vault_conventions` (`write_ownership`: the working-document view is GENERATED) and,
since CR-171, `view_files` in the config chain. Where the resolved document is a generated view:

| Dropped | Because |
|---|---|
| unsorted-bucket ageing | the bucket is a render of a field |
| `[x]` not archived | status lives in the ledger |
| week-anchor staleness | the renderer writes it |
| the `/inbox triage refresh` offer | it would write to a generated file |

**2. What replaces them is the same question asked of the source.** Overdue count and oldest age
**read from `_tasks.yaml`**, with the ledger named as the place to act. Plus the one check that is
only possible on a generated view and is worth more than all four: **is the view stale against its
source** — the ledger's `last_updated` newer than the view's own file date means the file on screen
is not what the ledger says.

**3. A hand-owned triage document keeps class 7 exactly as it is.** The four checks are correct for
the surface CR-022 describes, and a vault that still runs one must not lose them. This is a branch
on a declaration, not a replacement.

**4. The credential-looking-line check stays in both branches.** It is about content, not about
authorship, and a generated file can carry a secret copied from a task note.

## What this is not

**Not a retirement of CR-022.** The triage habit is the surface people actually work, and its design
principle holds. What changed is which file *is* that surface.

**Not a change to `/inbox triage refresh`.** It keeps working for a hand-owned document. It is
simply not offered against a generated one.

**Not an argument that the overdue items are noise.** 134 overdue, the oldest three months old, is
the loudest single number in the audit. This CR is about which file the operator is sent to.

## Acceptance

- Class 7 branches on the resolved write-ownership of the triage document and says which branch it
  took.
- On a generated view it reports overdue count, oldest age and view-vs-source staleness, naming the
  ledger as the place to act.
- On a hand-owned document all four original checks run unchanged.
- `/inbox triage refresh` is never offered for a generated view. **[H]** Re-run the measured vault:
  class 7 should report the ledger's overdue figures and no bucket-ageing findings at all.
