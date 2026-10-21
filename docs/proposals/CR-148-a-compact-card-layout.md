# CR-148 — A compact card layout: a short post, a round-only agenda, dependencies for the facilitator

| | |
|---|---|
| **Status** | **Proposed** (2026-10-21) |
| **Contract** | additive — `layout: compact` alongside the existing `card`; nothing existing changes |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`build_agenda.py` renderers for the post, the agenda and the facilitator document; the config key `carry_forward.layout`), SKILL.md |
| **Related CRs** | CR-107 (the card), CR-147 (carried lines re-read), CR-149 (milestones as a list), CR-150 (no per-person aggregation) |

## What happened

A project's own rule says a chat message is *three to five lines and carries the ask, not the content*, in plain
text because pasted markdown shows as literal asterisks. The day's generated post ran **about 660 words** in
markdown, and the agenda it accompanies about 1,880. The room walks the sections row by row, and the dependencies
appear twice: once as a section, once again in each person's cell of the round.

On 21 October the operator and a team member agreed on a shape without having seen a file: **the post carries the
milestones and the blockers; the agenda is the one-minute round; the dependencies go to the facilitator's document,
read against the data first.** The team member's reasoning: the meeting costs about one working week of people's
time each week, and anything people will do anyway should not be raised in it.

## Proposal

`layout: compact` produces four outputs:

1. **The post — plain text (`.txt`), at most `max_words` (default 150).** Milestones as a dated list with a state on
   each (CR-149); blockers one per line, grouped *to fix* and *waiting for a test*; the ask. No round, no
   dependencies, no markdown. Over the limit, it warns and names the longest part.
2. **The agenda — the screen-shared document.** The decisions needed and the one-minute round, with each person's
   open items. Nothing else.
3. **The facilitator document — for whoever leads.** Time boxes; the dependencies table, each line read against the
   data (CR-147) with closed ones listed as closed; what to watch. **No per-person figures** (CR-150).
4. **The details file — unchanged and complete**, linked from the agenda, for anyone who wants the rest.

`layout: card` stays the default; a project opts in. The existing sections are not removed, only moved.

## Acceptance

- With `layout: compact` and a project with ten blockers, the post is at most 150 words and plain text.
- The agenda has no Dependencies or Blockers section; the facilitator document has the dependencies.
- A project on `card` is unaffected.

## Not in scope

The meeting's length or cadence. This changes what is written, not whether people meet.
