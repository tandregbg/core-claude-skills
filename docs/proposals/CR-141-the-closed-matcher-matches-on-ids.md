# CR-141 — The *probably closed* matcher matches on explicit ids, or says nothing

| | |
|---|---|
| **Status** | **Implemented v1.92.2** (2026-10-21) |
| **Contract** | narrowing — fewer matches, each with a stated basis |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`build_agenda.py`, the *Probably closed* section) |
| **Related CRs** | CR-057 (the carry-forward agenda), CR-101 (the digest slot), CR-117 (sources shown) |

## What happened

The agenda lists carried items that *the sources say moved* and marks them *probably closed?* on the card.
The room trusts the card, so every marker is checked by hand before the meeting.

**[E]** Measured over three mornings on one project: **0 of 9** matches were real closes (16/10), **2 of 5**
(19/10), and on 21/10 **1 of 7**. The false ones had one shape: the matched issue or pull request was
unrelated, sharing a word with the carried line (a *checkout* fix matched a carried line about a payments
release; a *CI* item matched a trial-number fix). A marker that is wrong most of the time is removed by
hand each morning, which is the cost the generator was meant to avoid.

## Proposal

1. **Match only on an explicit identifier**: the carried line's own `#id`, a pull request that names the
   issue (`Re #id`, `Fixes #id`), or a ticket key. No title-similarity matching.
2. **A line without an identifier gets no marker.** It is never reported as *probably closed*; the details
   file may list *items with no identifier, cannot be checked* instead.
3. **Each marker states its basis**: `issue #id closed 16/10 11:02` or `PR #id (Re #id) merged`. A reader can
   verify it in one click.
4. **A state change is not a close.** A label change to *fixed* produces *fixed, waiting for a test*, never
   *probably closed*.

## Acceptance

- Re-running the three mornings above produces no marker without an identifier and basis.
- The false matches in the measurement no longer appear.
