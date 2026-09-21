---
name: tasks
description: Personal task tracking with history, source linking, and cross-project correlation. Tracks tasks from meetings, decisions, and manual input with automatic carry-forward.
user-invocable: true
argument-hint: [show|add|done|import|weekly|archive] [options]
---

# /tasks -- Personal Task Tracker

Track personal tasks across projects with source linking, history, and automatic carry-forward.

**Design principles:**
- Distributed per-folder `_tasks.yaml` files (like `_insights.yaml`)
- Root file holds projects registry + cross-project tasks
- Per-folder discovery: closest `_tasks.yaml` for local operations
- `--all` flag aggregates all files across vault
- Private by default (user-only unless explicitly shared)
- Source linking back to meetings/decisions
- History preservation for audit trail

---

## Architecture

### Distributed File Layout (v2)

```
~/Documents/Vault/
  _tasks.yaml                              # Root: projects registry + cross-project tasks
  _tasks-history.md                        # Completed tasks log (append-only)
  _projects/acme/_tasks.yaml               # Org-level tasks
  _projects/acme/ops/management/_tasks.yaml     # Domain tasks
  _projects/acme/ops/marketing/_tasks.yaml      # Domain tasks
  _projects/acme/projects/mobile-v3/_tasks.yaml # Project tasks
  _projects/bravo/_tasks.yaml              # Org-level
  _projects/bravo/side-project/_tasks.yaml      # Project tasks
  _private/_tasks.yaml                     # Personal tasks
  _contacts/david-ekberg_consulting/_tasks.yaml # Contact tasks
```

### Placement Rule

`_tasks.yaml` can exist at any level where a `CLAUDE.md` or `CHANGELOG.md` exists.

### ID Namespacing

IDs are unique per file. Visualisation displays as `context#id` (e.g., `mobile-v3#3`). Skills always operate on one file, so local IDs suffice.

---

## Data Model

### Per-file schema (v2)

```yaml
version: 2
last_updated: 260304
context: "acme-mobile-v3"       # Folder identity (like _insights.yaml)
scope: project                   # root | org | project | personal

tasks:
  - id: 1
    task: "Fix database connection issue"
    tags: [backend]
    source:
      type: meeting
      file: "meetings/260303-daily-standup.md"
    priority: P0
    due: 260307
    created: 260303
    status: pending              # pending | in_progress | blocked | completed | cancelled
    blocked_reason: null
    private: false
    notes:
      - date: 260303
        note: "Identified"

next_id: 2
```

**Key fields:**
- No `project:` field per task (implicit from folder context)
- `context` + `scope` fields at file level (mirrors `_insights.yaml`)
- `version: 2` distinguishes from v1

### Root file keeps

- `projects:` registry (vault paths, shared_view settings)
- Cross-project tasks (rare)
- Reference to `_tasks-history.md`

### _tasks-history.md (Completed Tasks Log)

```markdown
# Task History

Completed tasks archive. Append-only log.

---

## 2026-02

### 260220

- [x] **acme#47** War room mobile app
  - Context: acme-mobile-v3
  - Source: [260219-war-room.md](path/to/file.md)
  - Created: 260219 | Completed: 260220
  - Duration: 1 day
```

---

## File Discovery

When a `/tasks` command runs, find the target `_tasks.yaml`:

1. Look for `_tasks.yaml` in current working directory
2. Walk up parent directories toward vault root
3. **Closest match wins** for local operations (`show`, `add`, `done`)
4. `--all` flag scans all `_tasks.yaml` files across the vault

### New file creation

If no `_tasks.yaml` exists in the current folder and a task is being added:
1. Create with v2 schema
2. Derive `context` from folder name
3. Derive `scope` from path depth (root/org/project/personal)
4. Start with `next_id: 1`

---

## Commands

### `/tasks` or `/tasks show`

Show current active tasks from the local `_tasks.yaml`.

**Default:** Current folder's `_tasks.yaml` (or nearest ancestor).

```
/tasks show              # Local file
/tasks show --all        # Aggregate all _tasks.yaml files
/tasks show P1           # Filter by priority
/tasks show #board       # Filter by tag
/tasks show due:this-week  # Filter by due date
```

**Output format:**
```
# Active Tasks -- acme-mobile-v3 (12)

### P0 - Critical
1. [ ] Fix database connection issue (due: 260307)
   Source: [260303-daily-standup.md](meetings/260303-daily-standup.md)

### P1 - This Week
2. [ ] Release v1.1.62 (due: today)
3. [~] Handle Android DND -- IN PROGRESS

### P2 - Important
4. [ ] Include end-user changelog in build posts

---
Last updated: 260304
```

### `/tasks add "description"`

Add a new task to the local `_tasks.yaml`.

**Flow:**
```
> /tasks add "Review contract terms"

Adding task to: acme-mobile-v3/_tasks.yaml

Priority? [P2] P0 P1 P2 P3
> P1

Due date? [none] today tomorrow YYMMDD "before X"
> 260310

Tags? (comma-separated)
> contracts, legal

Source? (meeting file or "manual")
> manual

Private? [no] yes
> no

Task #15 created:
- Review contract terms
- Context: acme-mobile-v3 | Priority: P1 | Due: 260310
```

### `/tasks done <id>` or `/tasks done <id> <id> ...`

Mark task(s) as completed in the local `_tasks.yaml`.

1. Set `status: completed` and `completed: YYMMDD`
2. Append entry to root `_tasks-history.md`
3. Report remaining active task count

```
> /tasks done 3

Completing task #3: "Handle Android DND" (acme-mobile-v3)

Task #3 marked complete.
- Duration: 4 days (created 260301)
- Logged to _tasks-history.md

Remaining active tasks: 11
```

### `/tasks import <file.md>`

Import tasks from a meeting summary. **Target = folder where source file lives.**

```
> /tasks import meetings/260303-daily-standup.md

Scanning for action items in: 260303-daily-standup.md

Found 4 action items:
1. Fix database connection issue (Alex)
2. Complete store descriptions (Grace)
3. Create individual accounts (Sam)
4. Investigate CLI enforcement gap (Sam)

Import all? [yes] no select
> yes

Importing 4 tasks to acme-mobile-v3/_tasks.yaml...
Tasks #15-18 created.
```

### `/tasks weekly`

Generate weekly review. **Aggregates all `_tasks.yaml` files.**

```
> /tasks weekly

# Weekly Review: 260224-260302

## Completed This Week (8)
- acme#12 Kickoff brand meeting
- acme-mobile-v3#45 Release v1.1.60
- ...

## Carried Forward (5)
- acme#32 Offer team lead 1-on-1 - 12 days old
- ...

## Blocked (1)
- side-project#3 Integrate content - waiting on partner

## New This Week (7)
- acme-mobile-v3#15-18 from standup
- ...

## Stats
- Completed: 8
- Added: 7
- Net: -1 (backlog shrinking)
```

### `/tasks archive`

Archive completed tasks older than 30 days from history.

---

## Integration with Other Skills

### /transcript (Step 4: task import)

When `/transcript` finds action items, import to the **local `_tasks.yaml`** in the contact/project folder where the transcript lives (not vault root).

### /daily-dashboard (task display)

Dashboard scans all `_tasks.yaml` files in vault, groups by context, filters by privacy.

### /ops (Step 7 + Step 9)

- Step 7: Write `_tasks.yaml` in the project/domain folder (replaces `task-priority-matrix.md`)
- Step 9: Task import targets local `_tasks.yaml`

---

## Privacy Model

- Tasks with `private: true`: only visible in personal views
- Tasks with `private: false`: can appear in shared dashboards
- Default for meeting imports: `private: false`
- Default for manual adds: `private: true`
- Sensitive tags (#costs, #personal, #confidential): `private: true`

---

## Convention Files

| File | Signals | Used by |
|------|---------|---------|
| `_tasks.yaml` | Folder with tracked tasks | `/tasks`, `/ops`, `/daily-dashboard`, visualisation |
| `_tasks-history.md` | Completed tasks log | `/tasks done`, `/daily-dashboard` |

---

## File Format Details

### YAML Schema (v2)

```yaml
type: object
required: [version, context, scope, tasks, next_id]
properties:
  version:
    type: integer
    const: 2
  last_updated:
    type: [integer, string]  # YYMMDD
  context:
    type: string
  scope:
    enum: [root, org, project, personal]
  projects:
    type: object  # Only in root file
  tasks:
    type: array
    items:
      type: object
      required: [id, task, priority, created, status]
      properties:
        id: { type: integer }
        task: { type: string }
        tags: { type: array, items: { type: string } }
        source:
          type: object
          properties:
            type: { enum: [meeting, decision, manual, imported] }
            file: { type: string }
            section: { type: string }
        priority: { enum: [P0, P1, P2, P3] }
        due: { type: [string, integer, "null"] }
        created: { type: [string, integer] }
        status: { enum: [pending, in_progress, blocked, completed, cancelled] }
        blocked_reason: { type: [string, "null"] }
        completed: { type: [string, integer, "null"] }
        private: { type: boolean }
        notes:
          type: array
          items:
            type: object
            properties:
              date: { type: [string, integer] }
              note: { type: string }
  next_id:
    type: integer
```

---

## Implementation Notes

### Skill Location

```
~/.claude/skills/tasks/          # Symlinked
~/repos/core-skills/skills/tasks/ # Actual location
```

### Dependencies

- None (standalone skill)
- Optional integration with: transcript, daily-dashboard, ops

### Language

- Skill prompts: English
- Task content: Preserves original language (Swedish or English)
- Swedish character enforcement when task content is Swedish

---

## Handoff snapshots are not tasks (CR-033)

A frozen snapshot in `.handoff/` is context, not intent. It never generates a task, and `/tasks` never scans `.handoff/`.

If a snapshot's subject should become work, the **user** decides that and the task is written normally — stating the subject in its own words, never linking the snapshot (snapshots are not referenced from living documents).

## Future Enhancements

1. **Recurring tasks** -- `recur: weekly` for repeating tasks
2. **Subtasks** -- Hierarchical task breakdown
3. **Time tracking** -- Optional time spent logging
4. **Delegation** -- Assign tasks to others
5. **Calendar sync** -- Export due dates to calendar
