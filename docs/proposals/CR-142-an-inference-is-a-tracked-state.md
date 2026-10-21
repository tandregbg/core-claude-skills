# CR-142 — An inference is a tracked state, and an item is closed only from its own source

| | |
|---|---|
| **Status** | **Proposed** (2026-10-21) |
| **Contract** | additive — one marker (`*inferred: …*`) read by the generator and the lint; one rule in the close-out step |
| **Date** | 2026-10-21 |
| **Area** | `ops` (SKILL.md post-meeting steps, `build_agenda.py` carried lines, `lint`), a project's own rules file |
| **Related CRs** | CR-057 (carry-forward), CR-006 (summary format), CR-103 (declared words, not invented) |

## What happened

A meeting's audio was partly garbled. The assistant writing the note resolved three phrases by guessing and
wrote them as facts: a release day, an owner, and which items belonged together. Two days later the people
involved answered in the chat and **all three guesses were partly wrong**; a decision register line had to be
corrected after the fact. In the same week a carried item was **closed on a loose spoken word** ("resolved")
when its source issue was still open, and its title had drifted from *a test account with a card, number and
address* to *a card in the production pipeline*, which made the spoken word plausible.

The assistant then added a convention to the project's rules file: write what is not said and not in a
source as `*inferred: <what>*`. It worked; it also depends on the next assistant reading that file.

## Proposal

1. **The marker is part of the carried-line contract.** `*inferred: <what>*` goes in the source part of a
   carried line, in a decision's note, and as `Inferred:` in prose. The generator reads whatever follows the
   bold item, so it is safe today; this makes it documented.
2. **An unconfirmed inference ages.** The agenda lists lines still carrying the marker after two sessions
   under *Confirm or drop*, owner first. `lint` reports a decision whose note carries it.
3. **Close from the source.** In the close-out step, before an item is written as closed, its source (issue,
   ticket, plan section) is opened and the state read. *Said in the room* is a reason to look, not a source.
4. **A carried line's text does not replace its source's title.** If the line is a paraphrase it quotes the
   title once; a change of wording needs the owner's word.
5. **A confirmed inference loses its marker** in the next note, with the confirming source.

## Acceptance

- A line with the marker reappears on the agenda until confirmed or dropped.
- `lint` flags a decision with an unconfirmed inference.
- The close-out step names the source it read for every item it closes.
