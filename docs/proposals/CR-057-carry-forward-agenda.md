# CR-057: `carry_forward` — the agenda is generated from what did not land

| Field | Value |
|-------|-------|
| **CR Number** | CR-057 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-21** |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `skills/ops/SKILL.md` Step 9, new `skills/ops/build_agenda.py`, one config key |
| **Related CRs** | CR-014 (priorities artifact), **CR-054** (`recap_artifact`), CR-056 (staged folder naming), CR-011 (org-config chain) |
| **Contract** | Additive config key under `workflows.post_processing`. No contract bump |
| **Breaking Changes** | No. Off unless `enabled: true` |

---

## Executive Summary

**A series writes an agenda, holds the meeting, records a note — and nothing compares them.**

Step 9 already produces artifacts *after* a meeting: tasks imported, dashboard refreshed, priorities
written, recap staged. All of them look forward from what happened. **Nothing looks back at what was
asked for and did not happen**, so an item can lead the agenda, be skipped, lead it again, and be
skipped again with no trace.

Measured on `a coordination project`, 2026-09-21: of seventeen agenda items, **six fell through** — and the
correlation was not with position on the page. Two items led the agenda on two consecutive sessions and
were skipped both times. **Every item that fell had no named owner present.**

This CR adds `carry_forward` to Step 9 and a generator that builds the next agenda from the last note's
`## Carried forward` section, counting consecutive sessions per item.

## Motivation

### Agenda position is not a mechanism

The intuitive fix is to put the important thing first. It was already first. It was skipped anyway,
twice, because the person who owned it was absent on one day and because on the other day an adjacent
problem got solved and made its absence read as coverage.

What distinguishes the six items that fell from the eleven that landed is **whether a named person in
the room was going to be asked**. That is measurable, so the mechanism should measure it rather than
rely on the facilitator noticing.

### Why it belongs in the skill, not in a project

The first implementation was a script inside one project's `meetings/` folder. That is unreachable to a
session running a **different** project — and the sibling series in the same vault has the identical gap.
**A convention that lives in one project's folder is not a convention.** Every divergence found in that
vault on the same day began the same way: one project holding a mechanism the others did not.

## Proposed Changes

### 1. `## Carried forward` is a contract on the daily note

One line per item that did not land, in a defined shape:

```
- **<item>** — <note> · **<owner>**
- **<Name>:** <what they owe>
```

The section is what the next agenda is built from, so **a note without it silently ends the chain** —
worth saying out loud, because the failure is invisible.

### 2. Owner comes from a defined position

Trailing bold after the last middot, or the label itself when the line is a person's own. **Anything
else is `UNOWNED`.**

This is deliberate. A parser that guesses at prose would have found an "owner" in every line, hiding the
finding. On the first real run it marked **gate three, inbound calls do not ring, and definition of
done** as unowned — all three genuinely unowned, all three fallen through an agenda that listed them.
The `UNOWNED` label is the output, not a failure to parse.

### 3. `skills/ops/build_agenda.py`

```
python3 ~/.claude/skills/ops/build_agenda.py --dir <project>/meetings [--date YYMMDD]
```

Reads every `YYMMDD-<note_suffix>.md`, takes the newest note's carry-forward, and counts how many
**consecutive** prior notes carried each item. Writes the agenda with them at the top, before the round.
The round table comes from the `people` roster, so the mechanism is identical across series and only the
labels differ.

Date defaults to the next weekday. Refuses to overwrite an existing agenda.

### 4. Escalation at three sessions

```yaml
escalate_after: 3
```

At the threshold the agenda prints, in itself:

> *An item that survives three agendas is not an agenda problem — it has no owner who is present, or it
> is not actually being asked for. Decide today: give it a date and a name, or drop it.*

**The escalation is the point of the CR.** Counting is cheap; saying the count out loud in the room is
what changes behaviour.

### 5. Config

```yaml
workflows:
  post_processing:
    carry_forward:
      enabled: false                    # default
      note_suffix: daily-standup        # YYMMDD-<this>.md
      agenda_suffix: agenda-daily-standup
      title: "Webapp v3 — daily standup"
      time: "10:30 CET / 14:00 IST · 40 min"
      escalate_after: 3
      round_columns: [Track]            # extra blank columns in the round table
```

### 6. The facilitator's close

Instructed in Step 9: **read back what carries and whose name is on each.** An item read back without a
name is the one that will be on the agenda again. This is the cheapest control in the loop and the one
that was missing.

## What this does not propose

- **No enforcement that a note has the section.** `/ops lint` could check it; a missing section is
  currently silent, which is the known weakness.
- **No cross-series carry.** An item that belongs to another project is that project's to carry.
- **No automatic closing.** Items leave the list when a human stops writing them, not when a tool decides
  they look done.

## Known limitation, stated plainly

The generator counts what the **note** says carried. If a pass over a transcript fails to record
something as carried, it never appears. **The check catches items that were noticed and dropped, not
items that were never noticed** — a narrower guarantee than it looks, and worth saying because the table
otherwise reads as complete.

## Evidence

First run, `a coordination project` → `260922-agenda-daily-standup.md`: six carried items, two named, **four
unowned**. The four are the ones that had already fallen through once.
