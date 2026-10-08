# CR-114 — A blocker is a release blocker, a dependency is a person waiting, and each status has one stable source

| | |
|---|---|
| **Status** | **Implemented 2026-10-08** |
| **Contract** | additive — `reports[].current`, `reports[].owner`; the card's blocker section reads the repo when labels are declared |
| **Date** | 2026-10-08 |
| **Area** | `ops` (`build_agenda.py` card layout, `build_movement.py`, carry-forward kinds), `ops-config/schema.md` |
| **Related CRs** | **CR-107** (the card; this refines it after its first meeting and fixes two of its regressions), **CR-113** (implements its round routing, items 1 and 4 in part: each row carries the person's card items and a task count, the post names the order; its *Nobody owes these* / *Not in this room* lines and the *Stuck?* limit remain proposed), **CR-110** (the matcher itself is unchanged here; only its effect on the card), CR-084, CR-101 |

Marks: **[E]** observed in a running series · **[H]** not yet run.

## What happened

The first standup run on a CR-107 card:

1. **The room corrected the card in the first two minutes.** A blocker had been resolved the day
   before; a dependency carried the wrong owner. Both had been sorted by AI from a transcript. **[E]**
2. ***Blocked* and *blocker* were one word for two things.** A participant was "blocked on 80 issues,
   but not on anything important". Another set it out: a **release blocker** belongs in the tracker,
   as a label; **a person waiting on another person** is dialogue and rarely reaches any tracker. Two
   groups, both needed. **[E]**
3. **The one-minute round was blank.** CR-107's card dropped the per-person routing CR-084 had built,
   so everyone got the same empty question. **[E]**
4. **A false *probably closed* match took a real blocker off the card.** The matcher found a merged fix
   for a different 404. **[E]**
5. **The status lived in a new dated file every day,** and the living status page had not been updated
   for three weeks. The question that settled it: *if today's report was not written, what do we rely
   on?* **[E]**
6. **The agreed format:** confirm the release blockers and their plan, raise dependencies, one minute
   each; **five to ten minutes when nothing blocks**; statistics read offline, each report's owner
   summarising it in their minute. **[E]** as an agreement, **[H]** as a practice.

## Change

1. **Release blockers from the repo.** With `labels:` declared, the card lists open issues carrying the
   top priority label, with state and assignee, asking *is this the list, what is missing, what is the
   plan*. Carried `[blocker]` lines without a label follow separately.
2. **Kinds sharpened.** `blocker` blocks the release; `dependency` is a person waiting on another person
   or on someone outside the room; a person's own pending work is a task.
3. **Stable sources.** `reports[].current` names the path that *is* the status; its last commit date is
   its age, shown on the card (*updated today* / *N d old*). A series with only `pattern:` is reported as
   having no stable path. `reports[].owner` puts *summarise: <report>* in that person's round row.
4. **The card states the time:** five to ten minutes when nothing blocks.
5. **Fixes to CR-107:** the round routes each person's card items (blocked → waiting → decide) and counts
   their other tasks, and the post names the order; a *probably closed* match never removes a blocker,
   dependency or decision from the card — it stays, marked.

## Tests

`tests/test_cr114_blockers_and_sources.py` and additions to `tests/test_cr107_agenda_card.py`.
