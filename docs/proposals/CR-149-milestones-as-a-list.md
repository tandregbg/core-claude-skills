# CR-149 — Milestones as a list, each with a date, a source and a state

| | |
|---|---|
| **Status** | **Proposed** (2026-10-21) |
| **Contract** | additive — `milestones:` as a list; a single `milestone:` still reads as a list of one |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`build_agenda.py` milestone block, config validation), `ops-config` schema |
| **Related CRs** | CR-107 (the card's milestone), CR-127 (the milestone's `set_on` and history), CR-148 (the post uses the list) |

## What happened

The card runs toward **one** date. The project it serves has several that matter to the people in the room: the day
a backend release lands, a go/no-go, and three rollout steps after it. A team member said he missed *a list of
milestones and dates*, and that the dates governing the rollout are more than one.

The only place the further dates exist is a plan document whose own header says **every date in it is an unconfirmed
proposal**, not signed off by anyone. A reader meeting a bare date on the card cannot tell a confirmed commitment from
a proposal. The generator already complains that the one milestone has no `set_on`.

## Proposal

1. **`milestones:` is a list.** Each entry: `name`, `date`, `state` (`confirmed` · `proposed` · `target` · `done`),
   `source` (a decision id, a plan section, a named confirmer), `set_on`, and the existing optional `decide_by`,
   `criteria` and `history` (CR-127). A lone `milestone:` is read as one entry, so nothing existing breaks.
2. **The card and the post render the list sorted by date**, the state shown on every line, the next date after today
   marked with the days left. In the plain-text post (CR-148) it is a short list; on the card, a table.
3. **`confirmed` needs a source.** A decision id or a named confirmer. Without one, the entry is shown as `proposed`
   and the validation says so.
4. **Findings:** a `proposed` date that passes without being confirmed or moved; an entry with no `set_on`; two entries
   on the same date; a `done` date in the future.
5. **Optionally a dates-only timeline** line under the list, for a reader who wants the sequence at a glance.

## Acceptance

- A project with five entries shows five dated lines with a state each.
- An entry marked `confirmed` with no source is shown as `proposed` and flagged.
- A project with a single `milestone:` renders as before.

## Not in scope

Deciding the dates. The skill shows what has been set and by what; confirming a plan's dates is the team's.
