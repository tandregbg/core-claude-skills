# ops

**Version:** 1.1.1

Unified meeting and operations processing, driven by organization config. Replaces the previous per-domain skills (`project-ops`, `bravo-ops`, `management-ops`, `marketing-ops`).

## Usage

```
/ops [meeting content]           # Process meeting into summary + updates
/ops prepare [type]              # Create pre-meeting preparation
/ops status                      # Show available configurations
/ops help                        # Show usage guide
```

## How it works

`/ops` reads org config to determine behaviour. The same skill handles different organizations and meeting types:

| Context | Config source | Key behaviours |
|---------|---------------|----------------|
| Bravo veckosynk | `bravo-ops-config/bravo.yaml` | Swedish output, action propagation to ALEX.md/HANK.md, agenda management |
| Acme management | `acme-ops-config/acme.yaml` | Board Relevance, Risk Assessment, Strategic Alignment sections |
| Acme marketing | `acme-ops-config/acme.yaml` | Performance Metrics, Campaign Performance sections |
| Project dev standup | `.claude/ops-config.yaml` (project-level) | 8-section standup format, 5-file update, issue IDs |
| No config | `ops-config/base.yaml` | Summary + CHANGELOG, TWO-TIER format, match input language |

## Config resolution

1. **Project-level:** `.claude/ops-config.yaml` in the project root
2. **Org config:** `~/.claude/skills/{org}-ops-config/{org}.yaml`
3. **Base defaults:** `~/.claude/skills/ops-config/base.yaml`

First match wins. See `~/.claude/skills/ops-config/schema.md` for the full schema.

## Examples

### Bravo meeting

```
/ops [veckosynk transcript with Alex and Hank]
```

Produces: Swedish meeting summary, decisions propagated to BRAVO.md, actions to ALEX.md and HANK.md, agenda updated in "Nasta veckosynk" section.

### Acme management meeting

```
/ops [management meeting notes with Bob, Carol, Alex]
```

Produces: Meeting summary with Board Relevance and Strategic Alignment sections, CHANGELOG entry.

### Project standup (with project-level config)

```
/ops [standup transcript]
```

With a `.claude/ops-config.yaml` defining `summary_sections` and `update_files: [summary, changelog, readme, task_matrix, meetings_index]`, produces: 8-section standup summary, updated task-priority-matrix.md, README.md, CHANGELOG.md, and meetings/README.md.

### No config (fallback)

```
/ops [any meeting content]
```

Produces: Meeting summary using TWO-TIER format, matching input language.

### Pre-meeting preparation

```
/ops prepare standup
/ops prepare war-room
/ops prepare standup [paste team async updates here]
```

Produces: Structured preparation document with status tracking (Yesterday → Done → Today), agenda, blockers, and decisions. If async updates are provided, correlates them with yesterday's action items.

**Flow:**
```
/ops prepare standup     → creates preparation (before meeting)
[meeting happens]
/ops [transcript]        → creates summary, marks prep as superseded
```

## What it configures

- **Summary structure** -- custom sections or TWO-TIER default
- **Files to update** -- summary only, or up to 5 files
- **Action propagation** -- decisions and actions to external files
- **Agenda management** -- clear handled items, add follow-ups
- **Domain additions** -- org-specific sections (board relevance, metrics, etc.)
- **Language** -- English, Swedish, match input, or per CLAUDE.md policy
- **Status terminology** -- domain-specific status terms and issue ID format
- **Team** -- participant recognition and owner assignment

## Setting up for project standups

To use `/ops` for development standups (replacing `/project-ops`), add a `.claude/ops-config.yaml` to the project root:

```yaml
summary_sections:
  - name: Completed
    type: table
    columns: [Item, Owner, Notes]
    trigger: always
  - name: In Progress
    type: table
    columns: [Item, Owner, Status]
    trigger: always
  - name: Key Technical Updates
    type: subsections
    trigger: if_mentioned
  - name: Issues Discovered
    type: subsections
    trigger: if_mentioned
  - name: Decisions Made
    type: table
    columns: [Decision, Rationale]
    trigger: if_mentioned
  - name: Action Items
    type: table
    columns: [Action, Owner, Priority, Due]
    trigger: always
  - name: Version Status
    type: table
    columns: [Version, Platform, Status, Notes]
    trigger: if_mentioned
  - name: Status Summary
    type: table
    columns: [Component, Status, Notes]
    trigger: if_relevant

status_terminology:
  work_status: [VERIFIED, DISPLAYED, NOT_TESTED, ISSUE, PARTIAL]
  resolution_status: [FIXED, IMPROVED, WORKING, BLOCKED, DEFERRED]

issue_id_format: "[SEVERITY]-[YYMMDD]-[###]"

workflows:
  update_files:
    - summary
    - changelog
    - readme
    - task_matrix
    - meetings_index
```

---

## Changelog

### v1.1.1 (2026-03-12)

**Added:**
- ATTACHMENTS AND MEDIA section: guidance for handling PDFs, presentations, and binary files referenced in meetings
  - Detection: look for mentions of "presentation", "slides", "PDF", "deck" in transcript
  - Placement: `.attachments/` within project folder
  - Naming: `YYMMDD-description.ext`
  - Linking: "Related:" section in meeting summaries
  - Workflow: ask user for location, suggest moving to `.attachments/`

### v1.1.0 (2026-03-11)

**Added:**
- `prepare` subcommand for pre-meeting preparation documents
- Status tracking format: Yesterday → Done → Today per person
- Async update parsing: incorporate pre-submitted team updates
- Template variations for standup, war-room, weekly meetings
- Automatic correlation of reported updates with previous action items

**Changed:**
- Updated `help` subcommand to include prepare
- Updated "WHEN TO USE" section with prepare flow diagram

### v1.0.0

Initial unified ops skill, replacing per-domain skills.
