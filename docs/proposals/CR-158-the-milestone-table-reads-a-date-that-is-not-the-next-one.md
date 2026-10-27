# CR-158 — The card's milestone table calls every date except the next one "unreadable"

| | |
|---|---|
| **Status** | **Proposed** (2026-10-23) |
| **Contract** | none: a rendering fix, no config key, no schema change |
| **Date** | 2026-10-23 |
| **Area** | `ops` (`build_agenda.py` `s_milestone`, the milestone table in the card layouts), the CR-149 tests |
| **Related CRs** | **CR-149** (milestones as a list: this is a defect in its table), CR-155 (the compact agenda keeps the milestones: the same table), CR-107 (the single-milestone block, which renders correctly) |

Marks: **[E]** observed in a running series and reproduced · **[H]** not yet run.

## What happened

A project moved from a single `milestone:` block to the CR-149 list so that the card would carry its dated table. The table
appeared, and two of its dates, both **parsed correctly** (they sorted into the sequence line under the table), were printed as
`2026-10-23 (unreadable date)`. The date was the day the agenda was generated for. **[E]**

A throwaway project reproduces it with four confirmed or targeted entries, generated for 23 Oct 2026:

```
| **Past one**  | **2026-10-20** (unreadable date)  | confirmed |
| **Today one** | **2026-10-23** (unreadable date)  | confirmed |
| **Next one**  | **2026-10-30** · **7 days**       | confirmed |
| **Later one** | **2026-11-06** (unreadable date)  | target    |

*Sequence: 2026-10-20 -> 2026-10-23 -> 2026-10-30 -> 2026-11-06*
```

Every entry but one is mislabelled: **the passed milestone, the one on the day, and every later one**. The sequence line, which
reads the same parsed dates, orders all four correctly. **[E]**

## Why

In the card's milestone table the branch order is *the next date after today* (`next_milestone`), else *a date was declared*
(`elif e.get("date")`), else *date not set*. The middle branch was written for a date that does not parse, and its comment says
so. But it is reached by **every declared date that is not the one `next_milestone` returned**, parsed or not:

- `next_milestone` returns the first entry with a date **strictly after** the generated day, so an entry **on** the day is never
  "next";
- an entry in the past, parsed, is not "next";
- a second and every later future entry is not "next".

The chat post's list and the facilitator's list test `e["_date"]` first and are correct; only the card's table has the
branch order. **A project with two future milestones, the ordinary case CR-149 exists for, shows the second as unreadable.**

## Why it matters more than the wording

A reader meeting *(unreadable date)* is told the **config is wrong**, and the config check (which does report truly unreadable
dates) reports nothing, so the card contradicts the check. On a passed milestone the failure is worse: a commitment that was
missed reads as a typo, not as overdue, and a milestone that is today reads as broken on the day it matters.

## Proposal

1. **"Unreadable" only where the date does not parse:** `e["_date"] is None and e.get("date")`. A parsed date is always shown
   as its date.
2. **A marker for the date's place relative to the generated day**, in the same cell and using the same words the single-milestone
   block already uses:
   - **the next date after today:** `N days`, as now;
   - **today:** `today`;
   - **a passed date whose state is not `done`:** `N days ago, not marked done`, so a missed milestone reads as overdue;
   - **a passed date whose state is `done`, and a later future date:** the date alone.
3. **The sequence line and the post are unchanged.** They already read the parsed date.
4. **One shared helper** for the cell, called by the card's table and the two list renderers, so the three cannot disagree again.

## Verification

1. The throwaway project above renders `2026-10-20 · 3 days ago, not marked done`, `2026-10-23 · today`,
   `2026-10-30 · 7 days`, `2026-11-06`. None says *unreadable*.
2. A milestone with `date: soon` still renders `soon (unreadable date)` and the config check still reports it.
3. A passed milestone with `state: done` shows the date alone.
4. A project with a single `milestone:` renders byte for byte as before (CR-149's acceptance).
5. The card's table, the post and the facilitator's list agree on every cell for the four-entry fixture.

## Not in scope

The wording of the state column, and whether an entry on the same date as another is worth a finding (it is reported today and
is correct).

## Evidence

- A mobile project's agenda of 23 Oct 2026: a follow-up meeting and a release target, both on that day, both printed
  *(unreadable date)* while the sequence line listed them.
- The four-entry throwaway project above, reproducible with `build_agenda.py --dir <meetings> --date 261023` against a config
  carrying those entries.
