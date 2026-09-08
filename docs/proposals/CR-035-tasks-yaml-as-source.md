# CR-035: `_tasks.yaml` as source of truth for the personal working document

| Field | Value |
|-------|-------|
| **CR Number** | CR-035 |
| **Date** | 2026-09-07 |
| **Author** | User + Claude Code |
| **Status** | Implemented |
| **Implementation Date** | 2026-09-07 (v1.36.0) |
| **Priority** | High |
| **Complexity** | Medium |
| **Estimated Scope** | `ecosystem.yaml`, `inbox` schema, `ops` skill, external tool `todoist-triage` |
| **Related CRs** | CR-022 (daily triage as system of record — **superseded in part**), CR-012 (`_inbox/` schema), CR-034 (prefix conventions), CR-010 (vault file conventions) |
| **Depends On** | CR-022 |
| **Breaking Changes** | **Yes** — `_inbox/daglig-triage.md` becomes a generated view; tools must no longer write to it |

---

## Executive Summary

CR-022 made `_inbox/daglig-triage.md` the personal system of record. Fifteen months of
daily use showed the format does not scale as a **data store**:

| Metric | Value at migration (2026-09-07) |
|---|---|
| File size | 438 lines, 80 KB |
| Open tasks | 189 |
| **Median task line** | **273 characters** |
| Longest line | 1 079 characters |
| Lines over 300 chars | 79 (41 %) |
| **Non-task lines** | **249 of 438 (56 %)** |

The user's verdict: *"helt oläsbar för mig manuellt — ingen struktur och otroligt komplex."*

**Root cause:** every row carried four kinds of information in one sentence — the task,
its history, its reference data (links, order numbers, addresses, quotes), and reasoning
about why. Markdown has no way to separate them, so they concatenated.

**The fix is not a shorter markdown file.** It is to put tasks where structured data
belongs — YAML, which the vault already uses for **2 020 prioritised tasks** across
per-folder `_tasks.yaml` files — and let markdown be a *rendered view*.

```
_inbox/_capture.md   →   _inbox/_tasks.yaml   →   daglig-triage.md   →   Todoist
   (free-form in)          (SOURCE OF TRUTH)        (generated view)      (mirror)
```

Result: `task:` median dropped **273 → 87 characters**; the view went **438 → 52 lines**.

---

## Proposed Changes

### 1. `_inbox/_tasks.yaml` is the source of truth

Standard v2 schema, identical to every other `_tasks.yaml` in the vault, plus one field:

```yaml
- id: 29
  task: "Agree structure and staffing, then set up the project"
  context: "Org · web-app setup"
  priority: P1
  due: 260910
  status: open
  triage_id: "7133"     # NEW — preserves the {id} token from the markdown era
  notes:
    - "A-260905-46. Resolve the staffing contradiction at the same time…"
```

**Rule: `task:` states what is to be done and nothing else.** History, references,
warnings and reasoning go in `notes:`. This is the constraint markdown could not enforce.

`triage_id` exists so the external Todoist sync keeps its link identity across the
migration — 117 of 119 links survived.

### 2. `daglig-triage.md` becomes a generated view

**Rendered, never hand-edited.** Carries a header saying so. Shows only:

overdue · today · tomorrow · P0/P1 without a date · the coming seven days

Items with neither date nor priority stay in YAML. Of 189 tasks, **19 appeared in the
view** — which is the point: the view answers *"what do I do now?"*, not *"what exists?"*

Hand-written context lives in `_inbox/_frame.md` and is pasted in verbatim, so the
generator never owns prose.

### 3. `_inbox/_capture.md` is the write path

The original intent of `_inbox` as a **door** — drop in, route out — applied to tasks.
One line each, free-form; import moves them into YAML and empties the file.

```
- [Org] Verify the paying-customer figure !P0 ⏰260917
- Call the bank about the estate @finance !P1
```

`@tag` or `[Tag]` → `context` · `!P0`–`!P3` → `priority` · `⏰YYMMDD` → `due`

Import also **lists** unprocessed files from `_inbox.yaml` as candidates but never
imports them — a transcript is not a task.

### 4. Only dated or P0/P1 items sync to an external tracker

A task with neither is reference or a watch item; it stays in YAML.

**This was previously implicit** — it emerged from which markdown blocks the parser chose
to read. Making it explicit was necessary: without the rule the migration would have
created 72 tracker items out of reference material.

### 5. `ecosystem.yaml` changes

Add `_inbox/_tasks.yaml`, `_inbox/_capture.md` and `_inbox/_frame.md` as declared paths;
mark `_inbox/daglig-triage.md` as **generated**; and **replace** the `yaml_naming` rule
with the fuller prefix contract from CR-034 rather than leaving two overlapping
descriptions.

---

## What This Supersedes

**CR-022** named `daglig-triage.md` the system of record. That role moves to
`_tasks.yaml`. The markdown file persists — same path, same purpose to the reader — but
is now output, not input. **Any tool that writes to it must stop.**

---

## Out of Scope

- Migrating other `_tasks.yaml` files — they are already YAML.
- The `ops` skill's sweep checks for the new files (follow-up).
- Whether the view should also render a projects section — deferred until the section
  restructure (projects out of the triage, no double storage) is decided.

---

## Implementation Notes

**Done in the reference vault 2026-09-07:**

| Artefact | Location |
|---|---|
| Migration | `~/bin/todoist-triage/migrate_to_yaml.py` (one-shot, 189 tasks) |
| Import | `~/bin/todoist-triage/import_inbox.py` |
| Renderer | `~/bin/todoist-triage/render_triage.py` |
| Sync | `sync.py` — `parse_actionable_yaml()` + `report_dates_yaml()` |
| Original preserved | `_inbox/.archive/260907-daglig-triage-fore-yaml.md` |
| Vault contract | `CLAUDE.md` — TASKS section rewritten |

The date-check feature from the same day (`⏰YYMMDD`, warns on every sync) moved to the
YAML reader; it no longer parses markdown.
