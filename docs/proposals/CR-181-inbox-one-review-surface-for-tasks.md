# CR-181 — `/inbox`: one review surface for tasks, regenerated before use, never a parallel file

| | |
|---|---|
| **Status** | **Proposed** (2026-11-20) |
| **Contract** | No schema change. Documents an existing view (`survey.py --table --markdown`) as the **only** surface for reviewing tasks, adds two rules (regenerate before review; validate the register before every write) and one prohibition (no ad-hoc selection files) |
| **Date** | 2026-11-20 |
| **Area** | `skills/inbox/SKILL.md` (the survey section), `skills/tasks/SKILL.md` (write rule), `ops-base` (pointer) |
| **Related CRs** | CR-089 (role keywords), CR-122 (edit, never re-dump), CR-096 (append inside the list, re-read after writing); companion **vault-tools CR-012** (`sync.py prune`) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E]** The vault already had a review surface for tasks: `survey.py --table --markdown` writes one living
view, grouped **venture → project → entry** from the venture map, with a proposed bucket per entry
(*new date / set date / leave / write off / reference*) and an accept column.

**[E]** In two consecutive sessions the assistant ignored it and built its own:

1. a dated "audit of overdue tasks" grouped by an invented set of areas derived from the free-text
   `context` field;
2. the next day, a second dated file listing only the tasks that were stale in the external task mirror.

**[E]** The user's reaction to the first: *"why is it not grouped as we have decided many times and
discussed many times"*; to the second: *"I do not want NEW files all the time — I want one uniform
structure, and I want it fully documented."* Both files were archived the same day.

**[E]** In the same two days the register (`_tasks.yaml`) was broken twice by an append that placed a
`notes:` item after the entry's last key instead of inside its notes list. Both were caught by a parse
**after** the write; one was caught only because the next command failed.

**[E]** The view itself was stale twice: generated one afternoon, reviewed the next morning after a
dozen entries had changed.

## The proposal

### 1. One surface, named in the skill

`SKILL.md` states it as a rule, not a description:

> **The task review surface is the survey table view, and only that.** Overdue, clean-up, undated,
> stale-in-the-mirror — every review is done there. **Never create a dated audit or selection file for
> tasks.** A subset is a filter on the view, not a new file and not a new grouping.

The grouping is the venture map's. It is never rebuilt by hand and never derived from `context`.

### 2. Regenerate before every review

The view is regenerated immediately before it is used, and its generation time is the first thing the
assistant states. A view older than the last register change is not reviewed.

### 3. Reviewing is never a task

A review is a conversation (spoken or in the accept column), not an entry in the register. Do not add
"go through the task view" as a task.

### 4. Validate before write

Every write to the register parses the **new** text before it is saved, and refuses to save on a parse
error. A notes item is inserted inside the entry's `notes:` list, never appended after the entry's last
key. This extends CR-096 (re-read after writing) to *validate before writing* — CR-096 catches the
error; this prevents the broken file from existing.

### 5. The mirror gap is named

The skill states which entries the external mirror carries and that removal of non-actionable entries
is the companion tool's job (vault-tools CR-012), so the review does not try to fix the mirror by hand.

## What it does not change

The view's columns, buckets and accept codes are unchanged. Other audits (meetings over a period, vault
sweep, outbox) keep their dated files; this CR is about task review only.

## Verification

1. A session asked to "go through overdue tasks" regenerates the view and works in it; no new file. **[H]**
2. A session asked for "only the ones stale in the mirror" filters the view; no new file. **[H]**
3. A deliberately misplaced notes item is refused before save. **[H]**
