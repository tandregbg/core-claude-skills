# CR-146 — The weekly status is a step the Friday close-out surfaces, with its weeks folded in

| | |
|---|---|
| **Status** | **Draft** (2026-10-21) |
| **Contract** | additive — a reminder in the close-out and a `--since` form for the weekly builder |
| **Date** | 2026-10-21 |
| **Area** | `ops` (SKILL.md post-meeting steps, the project weekly template and builder) |
| **Related CRs** | CR-057 (the carry-forward agenda), CR-005 (the card), the project's weekly template |

## What happened

A project's rules say the weekly status is built on Friday after the meeting, from the week's notes. **Two
consecutive weeks were skipped**; the gap was found three weeks later because a handoff listed it. It was
then written as one status folding both weeks in. The builder that renders the status into a deck was not run
because nothing said to.

## Proposal

1. **The Friday close-out ends with a line**: *weekly status for week NN: not written (last: week MM)*, from
   the status folder's newest file. It is shown, not enforced.
2. **A status can cover several weeks** (`weeks: [40, 41, 42]` in its frontmatter) with a gap table so a
   folded status is not mistaken for a single week.
3. **The deck builder's run is part of the same line**, so *written* and *rendered* are separate states.
4. **A figure in the status names its basis** (which file, which date), as the agenda's counts do.

## Questions

Whether the reminder belongs in the skill or only in the project's rules. The failure was a missing step
in a routine, not a defect in a tool, so the smallest fix may be one line in the close-out.

## Acceptance

- A Friday close-out with no status for the week names the gap.
- A multi-week status states which weeks it folds.
