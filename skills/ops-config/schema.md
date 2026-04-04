# Configuration Schema v1.3

## Overview

This document defines the YAML schema for ops-config files.

**Related schemas:**
- [Contact Metadata Schema](contact-meta-schema.md) - `_meta.yaml` for contact folders

---

## Root Properties

```yaml
schema_version: "1.2"           # Required: Schema version
organization: string            # Required: Organization name
language: enum                  # Required: Output language
swedish_chars: enum             # Optional: Swedish character enforcement (strict)
language_inheritance:           # Optional (CR-007): Sub-tree inheritance rules
  enabled: bool
  apply_swedish_chars_strict_to: [glob]
  override_via: string
privacy_defaults:              # Optional (CR-009): Contact classification defaults
  family: [glob]               # Folder patterns that default to family classification
  personal: [glob]             # Folder patterns that default to personal classification
  professional: glob           # Fallback (default: "**")
```

### Language Options

| Value | Behavior |
|-------|----------|
| `english` | Always output in English |
| `swedish` | Always output in Swedish |
| `input` | Match input transcript language |
| `per_claude_md` | Follow the project CLAUDE.md LANGUAGE POLICY for per-file-type rules |

### Swedish Character Enforcement

Optional. Controls enforcement of correct Swedish characters (å, ä, ö).

```yaml
swedish_chars: enum               # Optional: Swedish character policy
```

| Value | Behavior |
|-------|----------|
| `strict` | ALL Swedish text MUST use å, ä, ö -- never substitute with a, o. Applies to all output regardless of `language` setting. |
| (not set) | No enforcement beyond normal language rules |

When `strict`, common mistakes to catch:
- "pagaende" -> "pågående", "foretag" -> "företag", "fran" -> "från"
- "fore" -> "före", "nasta" -> "nästa", "behovs" -> "behövs"
- "anvandning" -> "användning", "mote" -> "möte", "losning" -> "lösning"
- "manader" -> "månader", "forberedelse" -> "förberedelse", "karnteam" -> "kärnteam"

The full substitution list lives in `swedish_substitutions.yaml` and is consumed by `/ops normalize` and the `/insights` pre-write validator.

### Language Inheritance (CR-007)

Optional. Controls whether sub-trees without their own CLAUDE.md inherit `swedish_chars: strict` from base.

```yaml
language_inheritance:
  enabled: bool                  # Default: true in base
  apply_swedish_chars_strict_to: # Glob patterns
    - "_projects/**"
    - "_contacts/**"
    - "_private/**"
    - "_inbox/**"
  override_via: string           # Documentation: how to override per folder
```

**Resolution order for `swedish_chars` at write time:**

1. Folder has its own `CLAUDE.md` with explicit `swedish_chars` → use that
2. Folder is under an ops-aligned venture (e.g., `acme/`, `delta/`, `echo/`) → use that venture's config
3. Folder matches an `apply_swedish_chars_strict_to` glob → **inherit `strict` from base**
4. Else → use base default (which is `strict` since CR-007)

This means a sub-tree like `_projects/bravo-project/` automatically inherits strict mode without requiring its own CLAUDE.md.

---

## Team Structure

```yaml
team:
  - name: string                # Required: Person's name (canonical spelling)
    role: string                # Required: Role/title
    aliases: [string]           # Optional: Name variations for transcript matching
    areas: [string]             # Required: Responsibility areas
```

### Example

```yaml
team:
  - name: Bob
    role: CEO
    aliases: [Bob L, BL]
    areas: [strategy, board, finance, marketing, content]
  - name: Carol
    role: COO
    aliases: [Carol K, CK]
    areas: [operations, india-team, development, infrastructure]
```

### Name Resolution

When matching participant names from transcripts:

1. **Internal team**: Match against `team[].name` and `team[].aliases`
2. **External contacts**: Match against `_contacts/*/_meta.yaml` (see [Contact Metadata Schema](contact-meta-schema.md))
3. **Fallback**: Title-case folder name

Matching is case-insensitive with Swedish character folding ("Andre" matches "André").

---

## Responsibility Matrix

Optional. Maps areas to owner hierarchy.

```yaml
responsibility_matrix:
  area_name:
    primary: string             # Primary owner
    secondary: string           # Secondary owner
    support: string             # Support role
```

### Example

```yaml
responsibility_matrix:
  budget:
    primary: Bob
    secondary: Carol
    support: Alex
  ai_strategy:
    primary: Alex
    secondary: Bob
    support: Carol
```

---

## Terminology

Optional. Domain-specific terms and definitions.

```yaml
terminology:
  - term: string                # The term
    definition: string          # What it means
```

### Example

```yaml
terminology:
  - term: Board
    definition: Acme board of directors
  - term: India team
    definition: Development resources in India
  - term: MCC
    definition: Manager Account (Google Ads)
```

---

## Workflows

Configures which files to update and how.

```yaml
workflows:
  update_files:                 # List of files to update
    - summary                   # Always: Meeting summary
    - changelog                 # Optional: CHANGELOG.md
    - readme                    # Optional: README.md status
    - task_yaml                 # Optional: per-folder _tasks.yaml (v2)
    - meetings_index            # Optional: meetings/README.md
```

### Action Propagation

Optional. Enables propagating actions to external files.

```yaml
workflows:
  action_propagation:
    enabled: boolean
    targets:
      decisions: path           # Where to log decisions
      actions_by_person:        # Per-person action files
        person_name: path
```

### Agenda Management

Optional. Enables post-meeting agenda updates (clearing handled items, adding new ones, updating date).

```yaml
workflows:
  agenda_management:
    enabled: boolean           # Whether to manage agenda after meetings
    file: string               # Path to file containing the agenda section
    section: string            # Section heading to manage (e.g. "Nästa veckosynk")
```

### Post-Processing

Optional. Enables additional processing steps after meeting summary and file updates are complete. Both options default to disabled for backward compatibility.

```yaml
workflows:
  post_processing:
    task_import:
      enabled: boolean           # Offer to import action items to _tasks.yaml
      task_file: string          # Path to _tasks.yaml (default: vault parent)
    dashboard_refresh:
      enabled: boolean           # Run /daily-dashboard after all updates
      org: string                # Org name for dashboard (e.g. "acme")
```

#### Task Import

When `task_import.enabled` is true, action items from the meeting summary are extracted and matched against the task file. New items are offered for import; existing tasks mentioned in the meeting are updated.

#### Dashboard Refresh

When `dashboard_refresh.enabled` is true, the org dashboard is regenerated after all file updates and task imports are complete. The `org` field determines which dashboard to update.

### Evolution

Optional. Controls the skill evolution feedback loop -- whether skills capture execution feedback and whether compiled proposals are auto-applied.

```yaml
workflows:
  knowledge_extraction:
    evolution:
      enabled: boolean           # Master switch for execution feedback capture
      auto_apply: boolean        # true = proposals applied to SKILL.md automatically
      compile_threshold: integer # Minimum occurrences before pattern is compiled (default: 3)
      propose_threshold: integer # Minimum occurrences before proposal is generated (default: 5)
```

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `true` | When true, skills capture execution feedback (edge cases, corrections) to `_insights.yaml` |
| `auto_apply` | `false` | When true, `/insights propose` applies changes to SKILL.md automatically. When false, proposals require manual review |
| `compile_threshold` | `3` | An edge case must appear this many times before `/insights compile` creates a pattern article |
| `propose_threshold` | `5` | A pattern must appear this many times before `/insights propose` generates a SKILL.md diff |

#### Execution feedback types

These types extend the standard insight types when `evolution.enabled` is true:

| Type | Captures | Written by |
|------|----------|------------|
| `edge_case` | Unexpected input or ambiguity the skill handled | `/ops`, `/transcript` (silent) |
| `correction` | User corrected or overrode skill output | `/ops`, `/transcript` (silent) |
| `skill_pattern` | Recurring execution observation | `/insights compile` |

Execution feedback entries include a `source.skill` field to distinguish them from content-derived insights:

```yaml
- id: 14
  type: edge_case
  date: 260404
  summary: "Ambiguous participant name matched two contacts"
  detail: "User disambiguated between two contacts with same first name"
  source:
    file: "260404-samtal-Alex-David.md"
    skill: transcript
    step: "1.5"
  tags: [name-resolution, disambiguation]
  status: active
```

---

### Verticals

Optional. Living documents that aggregate insights across multiple meetings on a single strategic topic. Unlike meeting summaries (point-in-time), verticals are topic-longitudinal -- updated whenever their topic comes up in any meeting.

```yaml
workflows:
  verticals:
    - path: string               # Path relative to venture root
      name: string               # Human-readable name (used in suggestions)
      topics: [string]           # Keywords that trigger a check
      trigger: enum              # if_mentioned, always
```

| Field | Required | Description |
|-------|----------|-------------|
| `path` | Yes | Path to the vertical document, relative to venture root |
| `name` | Yes | Display name for the vertical (shown in post-processing suggestions) |
| `topics` | Yes | List of keywords/phrases matched against meeting content (case-insensitive) |
| `trigger` | Yes | `if_mentioned` = check when topic keywords appear; `always` = check after every meeting |

When triggered after meeting processing (Step 9.5 in /ops), the system suggests which verticals may need updating based on topic matches. The user decides whether to update.

#### Example

```yaml
workflows:
  verticals:
    - path: ops/management/voice-lake-vertikal.md
      name: Voice Lake
      topics: [voice lake, voicelake, call summaries]
      trigger: if_mentioned
    - path: ops/management/insikter-ai-utvecklingsorganisation.md
      name: AI i utvecklingsorganisationen
      topics: [utvecklingshastighet, ai-metodik, kunskapsbas, development speed]
      trigger: if_mentioned
```

### Example

```yaml
workflows:
  update_files:
    - summary
    - changelog

  action_propagation:
    enabled: true
    targets:
      decisions: operations/styrning/BRAVO.md
      actions_by_person:
        Alex: operations/styrning/alex/ALEX.md
        Hank: operations/styrning/hank/HANK.md

  agenda_management:
    enabled: true
    file: operations/styrning/BRAVO.md
    section: "Nästa veckosynk"

  post_processing:
    task_import:
      enabled: true
    dashboard_refresh:
      enabled: true
      org: acme
```

---

## Templates

Optional. Custom template paths.

```yaml
templates:
  meeting_reflection: path      # Meeting reflection template
  task_document: path           # Task document template
```

---

## Summary Sections

Optional. Defines custom section structure for meeting summaries. When defined, overrides the default TWO-TIER format from CLAUDE.md with a structured section layout (e.g. for development standups).

```yaml
summary_sections:
  - name: string               # Section name, e.g. "Completed", "In Progress"
    type: enum                 # table, subsections, freeform
    columns: [string]          # Column headers (if type=table)
    trigger: enum              # always, if_mentioned, if_relevant
```

### Section Types

| Type | Usage | Requires |
|------|-------|----------|
| `table` | Tabular data (completed items, action items) | `columns` |
| `subsections` | Named sub-topics with bullet points (technical updates, issues) | -- |
| `freeform` | Free-form text or mixed content (status summary) | -- |

### Example

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
```

---

## Status Terminology

Optional. Domain-specific status terms that extend or override the base terminology for work status and resolution tracking.

```yaml
status_terminology:
  work_status: [string]        # e.g. [VERIFIED, DISPLAYED, NOT_TESTED, ISSUE, PARTIAL]
  resolution_status: [string]  # e.g. [FIXED, IMPROVED, WORKING, BLOCKED, DEFERRED]
```

When defined, these terms are used in summary sections and status tables. When not defined, the standard ops-base terms apply (P0-P3 priorities, BLOCKED/IN PROGRESS/ON TRACK/TODO/COMPLETE).

### Example

```yaml
status_terminology:
  work_status:
    - VERIFIED
    - DISPLAYED
    - NOT_TESTED
    - ISSUE
    - PARTIAL
  resolution_status:
    - FIXED
    - IMPROVED
    - WORKING
    - BLOCKED
    - DEFERRED
```

---

## Issue ID Format

Optional. Defines the format for issue identifiers.

```yaml
issue_id_format: string        # e.g. "[SEVERITY]-[YYMMDD]-[###]"
```

When defined, issues and bugs should be assigned IDs following this pattern. When not defined, no structured issue IDs are used.

### Example

```yaml
issue_id_format: "[SEVERITY]-[YYMMDD]-[###]"
# Severity codes: CRIT (P0), HIGH (P1), MED (P2), LOW (P3)
# Example: CRIT-260212-001
```

---

## Domain Additions

Optional. Skill-specific sections to add to summaries.

```yaml
domain_additions:
  - section: string             # Section name
    trigger: string             # When to include (always, if_mentioned, if_relevant)
    format: string              # Section format description
```

### Example

```yaml
domain_additions:
  - section: Board Relevance
    trigger: if_relevant
    format: Items requiring board attention
  - section: Risk Assessment
    trigger: if_mentioned
    format: Identified risks and mitigations
```

---

## Strings (i18n)

Optional. Configurable UI strings for section headers, annotations, labels, and filename keywords. Allows skills to produce output in any language without hardcoded text.

```yaml
strings:                              # Optional: UI string overrides
  metadata:
    created: string                   # Footer label for creation date
    updated: string                   # Footer label for update date
    generated: string                 # Footer label for generated timestamp
  annotations:
    outcome: string                   # Post-meeting outcome tag, e.g. "[UTFALL]"
  preparation:
    context: string                   # "Kontext" / "Context"
    open_actions: string              # "Öppna åtgärdspunkter" / "Open action items"
    your_actions: string              # "Dina" / "Yours"
    suggested_topics: string          # "Föreslagna samtalsämnen" / "Suggested topics"
    background: string                # "Bakgrund: Relationen i korthet" / "Background"
    new_actions_post: string          # "Nya åtgärdspunkter efter mötet" / "New action items"
    reflections: string               # "Reflektioner" / "Reflections"
    post_meeting_note: string         # "insikter från genomfört möte" / "post-meeting insights"
  transcript:
    next_steps: string                # "Nästa steg" / "Next Steps"
  dashboard:
    preparations_today: string        # "Förberedelser idag" / "Preparations today"
    meetings_today: string            # "Dagens samtal och sammanfattningar" / "Meetings today"
    standup_section: string           # "Standup/Projekt" / "Standup/Projects"
    preparations_tomorrow: string     # "Morgondagens förberedelser" / "Tomorrow's preparations"
    no_meetings: string               # "Utan träffar idag" / "No meetings today"
    topics_label: string              # "Samtalsämnen" / "Topics"
    file_label: string                # "Fil" / "File"
  changelog:
    preparation_label: string         # "Förberedelse" / "Preparation"
    transcript_label: string          # "Samtal" / "Call"
  meeting_types:
    call: string                      # "Samtal" / "Call"
    meeting: string                   # "Möte" / "Meeting"
  filename_keywords:
    preparation: string               # "förberedelse" / "preparation"
    call: string                      # "samtal" / "call"
    summary: string                   # "sammanfattning" / "summary"
    standup: string                   # "standup" / "standup"
```

### String Resolution Order

Skills resolve strings in this order (first match wins):

1. **Org config `strings`** -- if the loaded org config defines a string, use it
2. **Language-matched defaults** from `base.yaml`:
   - `language: swedish` -> `strings_sv` block
   - `language: english` -> `strings` block
   - `language: input` -> match detected transcript/content language
3. **Hardcoded fallback** -- strings already in skill templates

This means org configs can override individual strings without providing the full table.

---

## Project-Level Overrides

Project configs support additional properties:

```yaml
# Extend org team with project-specific members
team_additions:
  - name: string
    role: string
    areas: [string]

# Override specific config values
language: enum                  # Override org language
swedish_chars: enum             # Override org swedish_chars policy
```

---

## Complete Example

```yaml
schema_version: "1.1"
organization: Acme
language: per_claude_md
swedish_chars: strict

team:
  - name: Bob
    role: CEO
    areas: [strategy, board, finance, marketing]
  - name: Carol
    role: COO
    areas: [operations, india-team, development]
  - name: Alex
    role: CAIO
    areas: [ai-strategy, product, architecture]

responsibility_matrix:
  budget:
    primary: Bob
    secondary: Carol
    support: Alex

terminology:
  - term: Board
    definition: Acme board of directors
  - term: India team
    definition: Development resources in India

workflows:
  update_files:
    - summary
    - changelog
  action_propagation:
    enabled: false

domain_additions:
  - section: Board Relevance
    trigger: if_relevant
    format: Items requiring board attention

strings:                              # Optional: override specific strings
  annotations:
    outcome: "[RESULTAT]"             # Override default [UTFALL]
  metadata:
    created: "Skapad"                 # Override default "Dokument skapat"
```
