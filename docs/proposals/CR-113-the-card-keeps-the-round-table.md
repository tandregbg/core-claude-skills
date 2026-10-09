# CR-113 — The card keeps the round table: the one-minute round is the body of the meeting

| | |
|---|---|
| **Status** | **Proposed** 2026-10-08 — **partly implemented by CR-114 (v1.89.3)**: items 1 (routing, as a *Bring to your minute* column with kinds and a task count) and 4 (the post names the round order). Items 2, 3 and the per-person post lines remain |
| **Contract** | none — card layout output only (`build_agenda.py`); no config key |
| **Date** | 2026-10-08 |
| **Area** | `ops` (`build_agenda.py` card layout, the Teams post in card layout) |
| **Related CRs** | CR-057 (carry-forward and the round), CR-084 (the round table built from `people[]`, owner routing), CR-090 (track columns), CR-107 (the card; it reduced the round to a question and an order line) |

Marks: **[E]** observed in a running series · **[H]** not yet run.

## What happened

A project switched to the card layout (CR-107) on a meeting morning. The regenerated agenda's round was:

```
## One-minute round
One minute each. What moved toward the milestone? What is stuck, and who owns the other end?
Order: A · B · C · D · ...
```

The list layout it replaced had a **table with one row per person and what each owed into the session**,
routed from the carried items by owner (CR-084). The owner of the series: *"Why did we lose the one-minute
round with the table like the prior tables? Everything should be there, but we should focus on the
one-minute round."* The table was restored by hand before the meeting. **[E]**

## Cause

CR-107 moved the **carried list** to the details file to stop the meeting reading it line by line — right —
and in doing so also dropped the **per-person routing** of those items, which is a different thing. The
carried list is a register; the round table is the **question each person is asked**. Without it, a person
with three items carried five sessions is asked the same open question as a person with none.

## Proposal

1. **In card layout, the one-minute round is the body of the agenda and keeps the table** from the list
   layout: one row per round member (`people[]`, `adjacent` excluded), column *Owed into today*, each item
   with its session count when above one. Track columns (CR-090) unchanged when declared.
2. **Two lines under the table, as in the list layout:** *Nobody owes these* (UNOWNED items) and *Not in
   this room* — items owned by someone in the project roster who is `adjacent` or not in `people[]`. In the
   observed run a five-session item owned by an absent manager sat in neither place.
3. **No duplication with *Stuck?*:** items in the round table that are past the escalation threshold keep
   their bold count there; the *Stuck?* section stays as the decision prompt above the round (CR-107) but
   is limited to items whose owner is not in the round, or which are UNOWNED. Everything else is asked in
   the round, by name.
4. **The Teams post in card layout** keeps the per-person lines (*"**Name:** item · item"*) it had in the
   list layout, after the milestone line. The post is how people come prepared; a post without their own
   name in it does not do that.

## Verification

Regenerate the observed agenda in card layout:

1. The round shows a table with nine rows; the five-session items appear in their owners' rows with bold
   counts.
2. The absent manager's six-session item appears under *Not in this room*; the two UNOWNED items under
   *Nobody owes these*.
3. *Stuck?* lists only items not routed to a round member.
4. The Teams post carries one line per person with what they owe.
