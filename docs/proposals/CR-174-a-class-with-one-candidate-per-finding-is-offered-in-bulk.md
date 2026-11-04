# CR-174 — A class with one candidate per finding is offered in bulk, or it is never worked

| | |
|---|---|
| **Status** | **Proposed** (2026-11-04) |
| **Contract** | none — behaviour of an existing check and its offered fix |
| **Date** | 2026-11-04 |
| **Area** | `ops` (`hygiene_check.py` `--offer`, `check` classes 11 and 1), `ops-base` (the offered-fix convention) |
| **Related CRs** | **CR-137** (the link check, which produced these numbers), CR-122 (the hygiene checks), CR-099 (a check that is mostly wrong is one nobody reads), CR-103 (`close --all-resolved`, the shape this copies), CR-019 (report-only by default, every fix confirmed) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E] Measured on one vault, 2026-11-04.** The hygiene check reported **1,215 findings**, of which
**1,124 are links**:

| Class | Count | What a fix would be |
|---|---|---|
| **moved** | **385** | One candidate, a path, mechanical |
| dead | 307 | A content decision: the document claims a source that does not exist |
| ancestor | 305 | Reported, not failed — possibly not a finding at all on this vault |
| ambiguous | 119 | Several candidates, none chosen |
| raw parentheses | 8 | Mechanical |
| privacy | 3 | **Removal, not repair** (CR-137) |

CR-137 shipped this in 1.92.1. **Nothing has been worked since.** That is the finding, and it is not
about diligence.

### A per-finding offer is a per-finding decision, and 385 of those is a project

The suite's rule is right and is not what this CR questions: report only, every fix confirmed, never
automatic (CR-019). But *confirmed* has been implemented as **one confirmation per finding**, and
that is a different thing from *confirmed*. At 385 findings with exactly one candidate each, the
work is not deciding — the candidate is unambiguous — it is **385 round trips**, which nobody begins
because beginning is indistinguishable from finishing.

**The suite already knows this.** `/outbox close --all-sent` and `--all-resolved` (CR-103) exist for
precisely the case of *a class of items whose resolution is mechanical once the class is confirmed*.
Links have the same shape and no equivalent.

### What makes the bulk offer safe here

**The `moved` class is the one with a single candidate by construction** — CR-137 separates it from
`ambiguous` on exactly that basis. A moved link's fix is a path substitution in a file the check has
already read and whose target it has already resolved. There is no judgement left in the individual
row; the judgement is *do I accept this class on this vault*, asked once.

## Proposal

**1. `hygiene_check.py --offer <class>` prints a patch, and only a patch.** For `moved` and
`raw-parens`: file, line, old target, new target, one row each, grouped by folder. It writes
nothing. This is the artefact a person reads to decide, and it is also the record of what was
decided.

**2. `--apply <class> --confirm <n>` applies exactly the rows the operator confirmed**, by count or
by folder, never by a bare `--all`. The count is in the command because a number that does not match
what the operator just read is the signal that the tree moved underneath them — the same reason
`propose_repos.py --write` requires `--confirm` with names (CR-151).

**3. `ancestor` is settled before anything is applied, not during.** 305 of 1,124 is 27 % of the
class, and CR-137 already reports it *without failing* because an adopting vault should not be met
by a wall. **Whether an ancestor-resolved link is a finding at all is a per-vault question**, and it
should be answered once in config (`workflows.sweep.links.ancestor: finding | tolerated`) rather
than re-decided on every run. On a vault that tolerates them, the class drops out of the count and
the remaining numbers become workable.

**4. `check` reports the class totals before the findings.** A class line — *links: 385 moved
(offerable), 307 dead, 305 ancestor, 119 ambiguous* — is what tells a reader whether they are
looking at a chore or a project. Today the first thing they see is finding number one of 1,215.

## What this is not

**Not automatic repair.** Nothing is applied without a confirmation that names what is being
applied. The default run still writes nothing, and `--offer` still writes nothing.

**Not a change to the `dead`, `ambiguous` or `privacy` classes.** `dead` is a content finding — the
document claims a source that does not exist, and inventing a target would be worse than the broken
link. `privacy`'s offered fix is removal and must stay one at a time. `ambiguous` has no single
candidate, which is the whole reason it is a separate class.

**Not an argument that 1,215 findings is wrong.** The check is right. A check being right and being
unusable are independent properties, and CR-099 is the precedent for treating the second as a defect
in its own right.

## Acceptance

- `--offer moved` prints a reviewable patch and writes nothing.
- `--apply` refuses without `--confirm`, and refuses when the confirmed count no longer matches.
- `ancestor` is configurable per vault and its state is printed in the class line either way.
- `check` prints class totals before findings for any class over a threshold. **[H]** Re-run the
  measured vault and state the four numbers after the ancestor decision — the point of this CR is
  that the remaining pile is small enough to finish.
