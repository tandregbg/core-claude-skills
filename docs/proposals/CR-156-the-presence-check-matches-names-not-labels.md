# CR-156 — The presence check matches names, not whole row labels, and reads declared leave

| | |
|---|---|
| **Status** | **Proposed** (2026-10-22) |
| **Contract** | additive — a looser match of a roster name to a round row; an optional `away:` list on a roster entry |
| **Date** | 2026-10-22 |
| **Area** | `ops` (`build_agenda.py`: the config finding *on the roster, not in the last three rounds*; `round_table`), `ops-config` (`people:`) |
| **Related CRs** | CR-143 (generated text uses the roster), CR-017 (the people roster), CR-139 (skip days) |

## What happened

The agenda's config check warns when a roster person is *not in the last three rounds*. On one morning it named three:
one was on leave the day before, one was away for a week, and one had been **in the room every day**.

The third is a defect. The check builds its list of names from the first column of each round table (lower-cased,
exact) and asks whether the roster name or one of its aliases is **exactly** one of them. A note that labelled the
row *Robert (Bob)* (the canonical name with the spoken one in brackets, which is how a reader finds both) matched
neither *robert* nor *bob*, so a person present on all three days was reported absent. Aliases are resolved, as
the code intends; it is the **whole-label comparison** that fails on any label with extra text.

A second problem is that the check cannot know leave. A person on a planned absence is reported with the same
question (*absent, or no longer in this meeting?*) as one who has quietly stopped coming. A check that is wrong
once in three reports is read as noise.

## Proposal

1. **Match a roster name or alias as a whole word inside the row label.** Text in brackets, a role or a trailing note
   does not stop a match. The match is still exact on the word, never a substring (a name inside a longer word).
2. **An optional `away:` list on a roster entry**, each item a date or a range with a short reason
   (`away: [2026-10-21, 2026-10-26..2026-10-30 leave]`). A person with an entry covering a day is not reported for it.
3. **A person in the last three rounds under *any* spelling is present**, whichever of those spellings the notes use.
4. **The message names the basis**: *no row matching <name or alias> in <the three notes>*, so the operator can see why.

## Acceptance

- A round row labelled `Name (Alias)` counts as the roster person `Name` with alias `Alias`.
- A roster person with an `away` range covering the days is not reported.
- A name that appears only inside a longer word does not match.

## Not in scope

Deciding whether a person should stay on the roster. The check asks the question; the operator answers it.
