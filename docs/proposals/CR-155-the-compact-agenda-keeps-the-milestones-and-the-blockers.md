# CR-155 — The compact agenda keeps the milestones and the blockers; its round is built from assignments

| | |
|---|---|
| **Status** | **Proposed** (2026-10-22) |
| **Contract** | changes the released behaviour of `layout: compact` (CR-148, v1.92.4): the agenda gains two sections; one optional key |
| **Date** | 2026-10-22 |
| **Area** | `ops` (`build_agenda.py`: the compact plan for the agenda and the facilitator document; the round's cells), SKILL.md, tests of CR-148 |
| **Related CRs** | CR-148 (the compact layout), CR-147 (carried lines re-read), CR-149 (milestones as a list), CR-121 (the card fits the project) |

## What happened

CR-148's compact layout was released with a deliberate rule: **the compact agenda carries no milestone and no
blockers section; the post carries them.** The code says so in comments, and a test asserts it. The rule came from a
conversation about the post being too long.

Two days of using a hand-built version of that shape showed what it costs. The first version took the milestones out of
the shared agenda, and the leader found the document the room was looking at had **no date on it**. After the milestones
were put back, the blockers were missing for the same reason, and the room had no list to confirm ("is this the list?
anything missing?"). Both were restored by hand on the day. In the meeting itself the team then **stopped, corrected or
asked at seven places**, among them:

- a milestone date that had been copied from a status report was wrong, and nobody had checked it against the room;
- an item "called a blocker" in chat was listed as a pending decision after its reporter had already withdrawn it;
- the round listed items **under a person's name that were not theirs** (they had been assembled from carried lines, not
  from what is assigned to them in the tracker), and they took a screenshot to work out what they were supposed to talk about.

The operator's decision, made in the room: **milestones and blockers appear in both the post and the agenda; only the
dependencies move out of the agenda.** The principle: *remove only the duplication, never what the room confirms.*

## Proposal

1. **The compact agenda keeps two sections: *Milestones* (the same dated list as the post, with a state on each, CR-149)
   and *Release blockers* (a table: the issue, what it is, the state, the owner, the next step).** *To fix* comes first;
   *fixed, waiting for a test* sits under its own heading. The agenda has no *Dependencies* and no *Decisions* section.
2. **The round's cells are built from the tracker's assignments**: each person's open `blocker` and `critical` issues
   (by assignee) plus what that person raised themselves in the last note. They are not built from carried lines. A
   carried line with an owner appears in that owner's cell only if it still resolves to an open item (CR-147).
3. **The facilitator document's dependencies table becomes optional** (`compact.facilitator_dependencies`, default
   `false`). Where the room raises dependencies itself, a pre-written table duplicates the round.
4. **The post still carries the milestones and the blockers**, in the short plain-text form it has.
5. **A date on the card is marked *from the status report* when it is copied from one and nobody has confirmed it**,
   so a reader can see that it needs checking.

## Acceptance

- With `layout: compact` the agenda has a *Milestones* section and a *Release blockers* section, and no *Dependencies*
  or *Decisions* section.
- A person's round cell contains the open blockers and criticals assigned to them and nothing assembled from another
  person's carried lines.
- The facilitator document has no dependencies table unless `compact.facilitator_dependencies: true`.
- The CR-148 tests that assert the opposite are changed with this CR, not deleted.

## Not in scope

Changing the card layout (`layout: card`), which keeps its sections. And the length limit of the post.
