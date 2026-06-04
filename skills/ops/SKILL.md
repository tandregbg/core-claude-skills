---
name: ops
description: Process meeting content into structured documentation -- summaries, decision tracking, action propagation, file updates. Config-driven for any organization. Replaces project-ops, bravo-ops, management-ops, marketing-ops.
user-invocable: true
argument-hint: [status | help | prepare [type] | meeting content, transcript, or standup notes]
---

# Operations Framework

Unified meeting and operations processing. Behaviour is driven by org config -- the same skill handles Bravo veckosynk, Acme management meetings, marketing standups, and project dev standups.

**Base framework:** Extends `ops-base` -- read `~/.claude/skills/ops-base/SKILL.md` for shared standards (meeting formats, task management, workflows, archive policy).

**IMPORTANT:** The project CLAUDE.md is the single source of truth for vault-specific details. This skill defines the processing workflow; CLAUDE.md defines file locations and naming conventions.

---

## SUBCOMMANDS

### `status` -- Show available configurations

**Trigger:** `/ops status`

Parse the user's input. If the first word is `status`, execute this subcommand instead of the normal processing flow (Steps 1-9).

**Steps:**

1. **Scan for org configs:**
   - Find vault root (walk up from CWD until `_inbox/`, `_outbox/`, or `.obsidian/`; or `VAULT_ROOT` env)
   - Glob `<vault>/*/_ops.yaml` for org-folder configs
   - Check `<vault>/_config/base.yaml` for vault-wide override
   - Read and parse each config
   - **Deprecated fallback:** also scan `~/.claude/skills/*-ops-config/` for legacy skill-based configs and emit a one-time deprecation warning per session if any are found (removed in v1.17.0)

2. **Detect active config:**
   - Check for project-level `.claude/ops-config.yaml` in current working directory
   - Walk up from CWD looking for the nearest `<folder>/_ops.yaml`
   - Determine org from CLAUDE.md `organization` field or folder name pattern
   - Report which config would be loaded for the current directory

3. **Present report** for each org config:
   - Organization name, language, swedish_chars
   - Team members (name + role, abbreviated if >4 members)
   - Workflows: update_files list, action_propagation status, agenda_management status, post_processing status
   - Rolling plans: count + axes (if `workflows.rolling_plans` configured)
   - Domain additions count
   - Summary sections (custom or default TWO-TIER)
   - Templates (if configured)
   - Strings (custom or default)

4. **Show base defaults** from `~/.claude/skills/ops-config/base.yaml`

5. **Vault health check** (CR-010 `rules.single_inbox_outbox`, `rules.yaml_naming`):
   - From the detected vault root, run `find <vault> -type d -name "_inbox" -not -path "*/.archive/*"` and `find <vault> -type d -name "_outbox" -not -path "*/.archive/*"`. Anything that resolves to a path other than `<vault>/_inbox` or `<vault>/_outbox` is a stray folder; flag each.
   - For every `<vault>/<folder>/_ops.yaml` found in step 1, the folder is treated as ops-aligned. Confirm each parses as YAML; flag any that don't.
   - List ops-aligned folders that are *missing* an `_ops.yaml` only when CLAUDE.md or `_meta.yaml` in that folder declares `organization` -- otherwise the folder is intentionally not ops-aligned and should be silent.
   - If `~/.claude/skills/acme-ops-config/`, `~/.claude/skills/bravo-ops-config/`, or `~/.claude/skills/delta-ops-config/` still exists, emit the deprecation warning from step 1 here as a vault-health item too (one-line each, with the `unlink`/`mv` command to fix).
   - If everything is clean, print a single `Vault health: OK` line. Only expand into a warning list when something is non-conforming.

**Output format:** Structured markdown report:

```
## /ops Configuration Status

### Active Config (current directory)
Organization: Acme
Config source: ~/.claude/skills/acme-ops-config/acme.yaml
Project override: none

### Available Organizations

#### Acme
Language: per_claude_md | Swedish chars: strict
Team: Bob (CEO), Carol (COO), Alex (CAIO), +9 more
Workflows:
  update_files: summary, changelog, readme, task_matrix, meetings_index
  action_propagation: disabled
  agenda_management: disabled
  post_processing: task_import (enabled), dashboard_refresh (enabled, org: acme)
Domain additions: 8 sections configured
Summary sections: default (TWO-TIER)
Strings: default (per language)

#### Bravo
Language: swedish | Swedish chars: strict
Team: Alex (Affärsutveckling), Hank (CTO)
Workflows:
  update_files: summary, changelog
  action_propagation: enabled -> BRAVO.md, ALEX.md, HANK.md
  agenda_management: enabled -> BRAVO.md / "Nästa veckosynk"
  post_processing: disabled
Domain additions: 4 sections configured
Summary sections: default (TWO-TIER)
Templates: meeting_reflection

### Base Defaults
Language: input
Team: (none -- must be defined in org config)
Workflows: summary only

### Vault Health
Vault health: OK
```

When non-conforming, the Vault Health section expands. Examples:

```
### Vault Health
- Stray `_inbox/` at acme/_inbox -- contract requires exactly one at vault root. Move contents to <vault>/_inbox/ and remove.
- Missing `_ops.yaml` in <vault>/acme/ -- folder declares `organization: Acme` but has no _ops.yaml. Drop one in or remove the organization declaration.
- Legacy skill `~/.claude/skills/acme-ops-config/` still present (CR-011, removed in v1.17.0). Run `unlink ~/.claude/skills/acme-ops-config`.
```

---

### `help` -- Show usage guide

**Trigger:** `/ops help`

If the first word is `help`, present a usage guide instead of processing content.

**Include:**
1. One-line description of what /ops does
2. Available commands: `/ops [content]`, `/ops prepare [type]`, `/ops status`, `/ops help`
3. Skill comparison table: when to use /ops vs /ops prepare vs /transcript, /preparation, /tasks, /daily-dashboard
4. Skill connection diagram: how /ops feeds into /tasks, /daily-dashboard, and how /ops prepare creates pre-meeting docs
5. Config loading summary (3-line version, point to `/ops status` for details)
6. Processing flow summary (9 steps, one line each)
7. Common usage patterns (examples including prepare)

**Output:** Markdown printed directly. No files created.

---

### `prepare` -- Create pre-meeting preparation

**Trigger:** `/ops prepare [type] [async-updates]`

Generate a structured preparation document for an upcoming team meeting. Pulls context from recent meetings, tasks, and optionally incorporates pre-submitted async updates from team members.

**Arguments:**
- `type` (optional): Meeting type hint (e.g., `standup`, `war-room`, `weekly`). Default: `standup`
- `async-updates` (optional): Pre-submitted text updates from team members to incorporate

**Examples:**
```
/ops prepare standup
/ops prepare war-room
/ops prepare standup [paste team updates here]
```

#### Preparation modes (single vs dual)

The skill supports two preparation modes, configured per meeting type in `_ops.yaml` under `meeting_types[<type>].preparation_mode`:

| Mode | When to use | Files produced | Filename pattern |
|------|-------------|---------------|------------------|
| `single` (default) | 1-on-1s, marketing meetings, anything where the facilitator and the participants are the same audience or there is no sensitive facilitator-only content | One file | `YYMMDD-preparation-[context]-[type].md` (or `förberedelse` for Swedish) |
| `dual` | Group meetings (standups, weeklies, war rooms) where the facilitator needs a private layer (deflection strategies, time-boxing cues, sensitive probes, policy reminders that should NOT be visible to attendees) on top of the normal team-facing prep | Two files | `YYMMDD-agenda-[context]-[type].md` (visible to team -- the standard prep) + `YYMMDD-facilitator-[context]-[type].md` (private add-on layer) |

**Default is `single`** -- only opt into `dual` when the org explicitly configures a meeting type to need it. If no `meeting_types` config exists, fall back to `single` regardless of `type` argument.

**Dual mode -- two-layer model:**

The agenda file is the team-facing prep document. It looks like the prior-day prep file in that folder -- same shape, same sections, same level of detail. The facilitator file is a *separate* private layer that contains only the additional content the facilitator needs and the team should not see.

**Agenda file** (visible to all attendees) -- mirror the prior-day single-mode prep in the same folder:
- Status overview (per-person yesterday/done/today)
- Key updates from async chat or prior meetings
- Async updates verbatim (if any)
- Agenda items with owners and time-boxes
- Blockers table, decisions pending, open action items carry-forward
- Reference links, build status, metrics
- Anything participants need to come prepared

**Facilitator file** (private, NOT shared with the team) -- contains only the additional layer:
- Facilitator's role clarification (e.g., "Alex runs the meeting only -- not driving test or fix work")
- Dana's / leader's expectations from prior handover or 1-on-1s
- Time-box discipline cues ("standup has run 25 min recently, target 30, hard stop 35")
- "Watch for" cues during the meeting (e.g., "Dana defaulting to 'I'll check after standup' on R2 blockers -- push for concrete commitment now")
- "Things NOT to surface in this forum" list (vertical/board topics, personnel matters, etc.)
- Decisions the facilitator owns and the framing for each (esp. when filling in for someone)
- Post-standup follow-ups the facilitator drives
- Pre-meeting backstory from 1-on-1s or lunches with subset of attendees

**Critical rule:** the agenda file does NOT mention or hint at the facilitator file. The visible document must not advertise that a private one exists. Cross-references go from facilitator → agenda only, not the other direction.

**Critical rule:** if the same content fits both files, it goes in the agenda file. The facilitator file should only contain content that would change behaviour or expose sensitive context if shared with the team.

---

#### Step P1: Gather Context

1. **Load org config** (same as normal /ops flow)
2. **Read recent meetings:**
   - Find last 1-3 meeting summaries in the target folder
   - Extract action items assigned to each team member
   - Note decisions made, blockers identified
3. **Read `_tasks.yaml`:**
   - Pull active tasks per person (status: pending, in_progress, blocked)
   - Identify blockers and their owners
4. **Read CHANGELOG.md:**
   - Scan recent entries for context

---

#### Step P2: Parse Async Updates (if provided)

If the user provides pre-submitted team updates:

1. **Identify team members** using the name resolution algorithm:
   - Match against org config `team[]` (name, aliases)
   - Match against `_contacts/*/_meta.yaml` (display_name, aliases) for external contacts
   - Matching is case-insensitive with Swedish character folding
   - See [Contact Metadata Schema](../ops-config/contact-meta-schema.md)
2. **Extract per-person updates:**
   - What they report as done
   - What they're working on today
   - Issues/blockers mentioned
   - Decisions or announcements
3. **Correlate with yesterday's tasks:**
   - Match reported items against action items from previous meeting
   - Determine status: DONE, IN PROGRESS, NOT STARTED, NO UPDATE

---

#### Step P3: Generate Preparation Document

Create the file using the **Standup Preparation Template**:

```markdown
# [Organization/Project] [Meeting Type] -- [DD] [Month] [YYYY]

**[Next event note if relevant, e.g., "War room tomorrow: Wednesday March 12, 10:00-12:00 CET"]**

---

## Status Overview

| Person | Yesterday | Done | Today |
|--------|-----------|------|-------|
| **[Name]** | [Tasks assigned] | [What's done] | [Today's plan] |
| ... | ... | ... | ... |

**[Key metric if relevant, e.g., "Test results: 4 PASS / 4 FAIL (50%)"]**

---

## Key Updates

| Update | Source |
|--------|--------|
| [Important update or decision] | [Person] |
| ... | ... |

---

## Agenda

- [ ] 1. **[Person]** -- [Key questions]
- [ ] 2. **[Person]** -- [Key questions]
- [ ] ...
- [ ] N. **[Topic]** -- [Confirm/discuss]

---

## Reported Updates

**[Person]:**
> "[Their exact update text]"

**[Person]:**
> "[Their exact update text]"

...

---

## Blockers

| Issue | Status | Owner |
|-------|--------|-------|
| [Blocker description] | [Status] | [Owner] |
| ... | ... | ... |

---

## Decisions

**Made:**
- [Decision] -- [brief rationale]

**Pending:**
- [Decision needed]

---

# Reference

## [Relevant reference section, e.g., Test Results]

[Tables or details as needed]

## Builds / Versions

- [Current build info]

---

*Created: [YYYY-MM-DD]*
```

---

#### Step P4: Template Variations

**For standup:**
- Focus on Status Overview (Yesterday → Done → Today)
- Keep agenda person-by-person
- Include reported updates if async input provided

**For war-room:**
- Add "Focus Areas" section after agenda
- Include test matrix reference
- Add "Participants" confirmation

**For weekly/planning:**
- Add "Sprint Goals" or "Week Priorities" section
- Include metrics summary
- Add "Carry-over Items" from previous week

---

#### Step P5: Save and Report

1. **Resolve preparation mode:**
   - Look up `meeting_types[<type>].preparation_mode` in the merged org config
   - If absent, default to `single`

2. **Determine filename(s):**

   **Single mode** -- one file:
   - Format: `YYMMDD-preparation-[org/project]-[type].md` (English) or `YYMMDD-förberedelse-[org/project]-[type].md` (Swedish)
   - Include the organization or project name to distinguish preparations created the same day for different orgs/projects
   - Examples: `260311-preparation-acme-mobile-daily-standup.md`, `260311-förberedelse-delta-veckosynk.md`

   **Dual mode** -- two files (always English -- dual mode is not yet localized for Swedish):
   - Agenda file (team-facing): `YYMMDD-agenda-[org/project]-[type].md`
   - Facilitator file (private add-on layer): `YYMMDD-facilitator-[org/project]-[type].md`
   - Examples: `260505-agenda-coreteam-weekly-w19.md` + `260505-facilitator-coreteam-weekly-w19.md`

   **Order of generation:** write the agenda file first using the same template the same folder's prior-day single-mode prep used (status overview, blockers, action items, agenda, references). Then derive the facilitator file as a slim private layer on top -- only the content from the "Facilitator file" list above. If a section is present in both, keep it in the agenda and remove it from the facilitator file.

3. **Save to meetings folder** (per CLAUDE.md MEETING ROUTING). For dual mode, both files go in the same folder.

4. **For dual mode, ensure the cross-references are one-directional:**
   - The facilitator file MUST link to the agenda file at the top with a notice such as: `> **Private facilitator file.** The team-facing version is [YYMMDD-agenda-...md](YYMMDD-agenda-...md). Do not share this file with the team.`
   - The agenda file MUST NOT mention or link to the facilitator file. The visible document must not advertise that a private one exists.

5. **Report what was created:**

   **Single mode:**
   ```
   Created: meetings/260311-preparation-acme-mobile-daily-standup.md

   Status Overview:
   - Dev1: 1 done, 4 in progress
   - ...

   Blockers: 4 items
   Agenda: 7 items
   ```

   **Dual mode:**
   ```
   Created (dual mode):
   - meetings/coreteam/260505-agenda-coreteam-weekly-w19.md (team-facing -- full prep)
   - meetings/coreteam/260505-facilitator-coreteam-weekly-w19.md (private add-on layer)

   Agenda file: status overview (8 people), 10 agenda items, 6 P0 blockers, 13 carry-forward actions
   Facilitator-only layer: 5 items (role clarification, time-box cues, "watch for" list, "do not surface" list, post-meeting follow-ups)
   ```

---

#### Step P6: Lifecycle

After the meeting, when `/ops [transcript]` is run:
- Single mode: the `preparation`/`förberedelse` file is automatically marked as superseded (per Step 9 of normal flow)
- Dual mode: BOTH the `facilitator` and `agenda` files are marked as superseded
- No manual action needed

---

#### Notes

- **No CHANGELOG update** for preparation files (they're pre-meeting)
- **Language:** Follow same rules as normal /ops (per_claude_md, etc.)
- **If no async updates provided:** Generate preparation from historical context only, with empty "Reported Updates" section or skip it
- **If team member missing from updates:** Show "No update" in Status Overview

---

### `normalize` -- Restore Swedish characters in hand-written docs (CR-007)

**Trigger:** `/ops normalize <path> [--dry-run] [--strict-no-ambiguous]`

Lint pass that scans markdown and YAML files for known Swedish character drift (`ar` → `är`, `for` → `för`, `pa` → `på`, `mote` → `möte`, etc.) and restores the correct characters. Use it on hand-written ops documents that bypassed the `/transcript` and `/ops` pipelines and accumulated character errors.

**Use cases:**
- A folder of pasted notes (e.g., `_projects/<client>/ops/*.md`) was created without going through `/ops` and never got a Swedish-character pass
- A legacy file from before CR-007 inheritance was added still contains old drift
- Bulk remediation across a sub-tree

**Arguments:**

| Argument | Meaning |
|---|---|
| `<path>` | A single file OR a folder. If a folder, scans all `.md` and `.yaml` files recursively. |
| `--dry-run` | Show the diff without writing. Use to preview before applying. |
| `--strict-no-ambiguous` | Skip substitutions marked `ambiguous: true` in `swedish_substitutions.yaml` (e.g., `ar` → `är`, `bor` → `bör`, `Andre` → `André`). Recommended for first-pass scans. |

**Examples:**

```
/ops normalize _projects/bravo-project/ops/annonsering.md
/ops normalize _projects/bravo-project/ --dry-run
/ops normalize _projects/bravo-project/_insights.yaml --strict-no-ambiguous
```

#### Step N1: Load substitution map

Read `~/.claude/skills/ops-config/swedish_substitutions.yaml`. This file contains the seed substitution list (from MEMORY.md) and is the single source of truth for the linter.

#### Step N2: Scan target file(s)

For each file:

1. **Detect language.** Treat the file as Swedish-context if any of:
   - The file already contains å, ä, or ö characters
   - The file is in a folder configured for Swedish (per CLAUDE.md or `language_inheritance` in base.yaml)
   - The user explicitly passed `--lang sv`
2. **Skip if not Swedish-context** -- this is a Swedish-character normaliser, nothing else
3. **Tokenize the file** while preserving:
   - Code blocks (```...```) -- skip
   - Inline code (`...`) -- skip
   - URLs and file paths -- skip
   - YAML keys (only `value:` parts are scanned, not keys) -- skip keys
   - Lines containing `<!-- no-normalize -->` -- skip the entire line
4. **For each token**, look up against the substitution map. Use word-boundary matching (`\bword\b`).
5. **Skip ambiguous substitutions** if `--strict-no-ambiguous` is set.

#### Step N3: Apply or report

**If `--dry-run`:**
- Print a unified diff to stdout showing all proposed substitutions
- Print a summary: total substitutions, ambiguous skipped, files affected
- Do not write anything

**If not dry-run:**
- Apply substitutions to each file
- Write the file back atomically (write to temp, rename)
- Update or create a `CHANGELOG.md` entry in the file's parent folder (if a CHANGELOG exists):

  ```markdown
  - **YYMMDD: Normalize** [filename] -- restored Swedish characters (N substitutions). -> [file]
  ```

#### Step N4: Report

```
Normalized 4 files, 23 substitutions applied:
  _projects/bravo-project/_insights.yaml         8 substitutions
  _projects/bravo-project/ops/annonsering.md     7 substitutions
  _projects/bravo-project/ops/byrasamarbete.md   5 substitutions
  _projects/bravo-project/ops/c56-krav.md        3 substitutions

Ambiguous substitutions skipped (use without --strict-no-ambiguous to apply):
  ar -> är: 14 occurrences
  bor -> bör: 2 occurrences

Backup: none (use git to revert if needed)
```

#### Notes

- **No backup files written.** Rely on git for revert. If the target is not a git repo, the user is warned and asked to confirm.
- **The substitution list is data, not code.** New common drifts can be added to `swedish_substitutions.yaml` without changing skill code.
- **Defence in depth:** the same substitution map is used by `/insights` pre-write validation (see insights/SKILL.md). The normaliser is the after-the-fact remediation; the validator is the at-write-time gate.

---

## WHEN TO USE /OPS vs /OPS PREPARE vs /TRANSCRIPT

- **`/ops prepare`**: Use **before** a team meeting to create a structured preparation with status tracking. Pulls context from recent meetings and tasks. Optionally incorporates pre-submitted async updates from team members. Outputs one file (`preparation`/`förberedelse`) by default, or two files (`facilitator` + `agenda`) when the meeting type is configured `preparation_mode: dual`.
- **`/ops`**: Use **after** a meeting to process content into structured documentation (summary, changelog, README, task matrix, meetings index, task import, dashboard). Recommended default for all org meetings. Automatically marks any preparation file as superseded.
- **`/transcript`**: Use for ad-hoc recordings, personal calls, or contexts without an ops config. Produces summary + changelog + optional task import only.

**Flow:**
```
/ops prepare standup     → creates preparation (before meeting)
[meeting happens]
/ops [transcript]        → creates summary, marks prep as superseded (after meeting)
```

When `/ops` and `/transcript` both apply, prefer `/ops` -- it is a superset of `/transcript` functionality.

---

## CONFIGURATION

### Config Loading

1. **Determine organization** from:
   - Explicit `organization` field in project CLAUDE.md
   - Project folder name pattern (e.g., `bravo-*` -> bravo, `acme-*` -> acme)
   - Participant names matching team members in configs
2. **Load config** following resolution order:
   - Project-level: `.claude/ops-config.yaml`
   - Folder-local (CR-011): nearest `<folder>/_ops.yaml` walking up from CWD until vault root
   - Vault-wide (CR-011, optional): `<vault-root>/_config/base.yaml`
   - Skill defaults: `~/.claude/skills/ops-config/base.yaml`
   - Deprecated fallback (removed v1.17.0): `~/.claude/skills/{org}-ops-config/{org}.yaml`
3. **Merge layers** -- project overrides folder-local, folder-local overrides vault-wide, vault-wide overrides skill defaults

### What Config Controls

| Setting | Effect |
|---------|--------|
| `language` | Output language (english/swedish/input/per_claude_md) |
| `swedish_chars` | Swedish character enforcement (strict) |
| `team` | Participant recognition and attribution |
| `responsibility_matrix` | Owner assignments |
| `terminology` | Domain-specific terms |
| `summary_sections` | Custom summary structure (overrides TWO-TIER) |
| `status_terminology` | Domain-specific status terms |
| `issue_id_format` | Issue ID pattern |
| `workflows.update_files` | Which files to update |
| `workflows.action_propagation` | Propagate actions to external files |
| `workflows.agenda_management` | Post-meeting agenda updates |
| `meeting_types[<type>].preparation_mode` | `single` (default) or `dual` -- whether `/ops prepare` produces one file or a facilitator/agenda pair |
| `workflows.post_processing` | Task import, dashboard refresh, and optional priorities artifact (`priorities_artifact.enabled`) after meeting |
| `workflows.rolling_plans` | Participant-triggered per-axis living planning docs (update after a matching 1-on-1) |
| `domain_additions` | Extra sections to add to summaries |
| `templates` | Custom template paths |
| `strings` | i18n string overrides |

---

## PROCESSING FLOW

### Step 0.5: Load Applicable Rules (CR-013)

Before parsing the input, load any promoted **rules** from the `_insights.yaml` chain in scope:

1. **Walk up from CWD** collecting `_insights.yaml` files at each level (max depth 6, skip `.archive/`, `clones/`).
2. **Filter to rules:** entries where `confidence: rule` AND `status: active`.
3. **Cap to 20 entries** — if more, prefer highest `confirmation_count`, ties broken by most recent confirmation date.
4. **Build a one-line-per-rule preamble** in the form `[type] summary` and treat it as additional standing instructions for this run. For example:
   - `[preference] Bob prefers concise weekly summaries`
   - `[pattern] Bob raises customer-success topics last in 1-on-1s`
   - `[decision] Board updates use English for India team`
5. **Apply the rules during Step 3 (Create Meeting Summary)** and Step 4 (Apply Domain Additions). Do not echo the preamble in the output; rules influence content, not chrome.

**Scoping:** Only rules in the CWD's parent chain apply. A rule in `meetings/marketing/_insights.yaml` is not loaded when running `/ops` from `meetings/management/`.

**No rules found:** Skip silently. The skill works without rules; this is purely additive context.

### Step 1: Parse Input

Extract from the input (transcript, notes, standup content):
- Participants and their roles -- use name resolution algorithm:
  - Match against org config `team[]` (name, aliases) for internal team
  - Match against `_contacts/*/_meta.yaml` (display_name, aliases) for external contacts
  - Use resolved canonical names in output (correct spelling, Swedish characters)
- Completed work items (who did what)
- In-progress work (current status)
- Decisions made (with rationale)
- Action items (with owners and deadlines)
- Issues/blockers discovered
- Technical updates
- Version/build information (if mentioned)
- Metrics and KPIs (if mentioned)

### Step 2: Determine Summary Format

**If `summary_sections` is defined in config** (non-empty list):
Use the configured section structure. Each section becomes a numbered heading with the specified type (table/subsections/freeform). Only include sections whose trigger condition is met.

**If `summary_sections` is empty or not defined:**
Use the TWO-TIER SUMMARY FORMAT from CLAUDE.md:
- **Concise Operational** for weekly syncs, quick calls, standups
- **Detailed Strategic** for quarterly reviews, major decisions, milestones

### Step 3: Create Meeting Summary

1. Determine date from transcript/content or use today
2. Determine filename and location from CLAUDE.md MEETING ROUTING
3. Build summary using the format from Step 2
4. Include metadata header (date, time, participants, format)
5. Write executive summary (2-3 sentences)
6. Populate all applicable sections
7. Attribute actions to correct people using `responsibility_matrix`

### Step 4: Apply Domain Additions

For each entry in `domain_additions` from config:
- `trigger: always` -- always include the section
- `trigger: if_mentioned` -- include if the topic appears in the input
- `trigger: if_relevant` -- include if contextually appropriate

Append domain-specific sections after the standard summary structure.

### Step 5: Update Files

Update files per `workflows.update_files` from config:

| File key | Target | Action |
|----------|--------|--------|
| `summary` | Meeting summary | Always created (Step 3) |
| `changelog` | CHANGELOG.md | Add dated entry at top |
| `readme` | README.md | Update Current Status, Active Tasks, Recent Meetings |
| `task_yaml` | _tasks.yaml | Update/create per-folder task file (v2 schema) |
| `meetings_index` | meetings/README.md | Add entry to meeting index |

For `changelog`, follow the format in ops-base. Always reference the meeting summary file.

### Step 5.5: Knowledge Extraction (silent)

After updating files, scan the meeting summary for durable insights worth accumulating. This step writes to `_insights.yaml` in the same folder as the CHANGELOG -- it is a silent accumulation layer that never surfaces in any skill output.

**Same extraction logic as `/transcript` Step 3.5** (insight types, threshold, format, dedup). See the transcript skill for the full `_insights.yaml` schema and extraction criteria.

**Privacy:** NEVER include personal names or company names in `summary`, `rationale`, or `tags`. The `context` and `source.file` fields provide the connection. Write generic, reusable knowledge.

**Swedish characters:** When writing Swedish content in `_insights.yaml`, ALL words MUST use correct å, ä, ö. YAML files are equally prone to missing characters.

**Additional ops-specific sources:**
- Strategic decisions from `domain_additions` -> `decision` type
- Cleared agenda items with resolution -> `learning` or `decision` type
- Configuration or workflow changes discussed -> `decision` type

**Process:**
1. Scan the meeting summary (including domain addition sections) for qualifying insights
2. Write to `_insights.yaml` in the same folder as the CHANGELOG
3. Dedup by `source.file` -- if insights from this meeting file already exist, skip

**Skip conditions:**
- No CHANGELOG.md in the target folder
- Pure standup (short status updates without decisions)
- User explicitly said "skip insights"

**Output:** Same brief format as transcript Step 3.5:
```
Extracted [N] insights to _insights.yaml:
- [type] summary sentence
```

### Step 6: Propagate Actions

If `workflows.action_propagation.enabled` is true:
- Decisions -> `targets.decisions` file
- Per-person actions -> `targets.actions_by_person.{name}` file

### Step 7: Manage Agenda

If `workflows.agenda_management.enabled` is true:
- Open the file at `agenda_management.file`
- Find the section matching `agenda_management.section`
- Clear items that were addressed in this meeting
- Add new follow-up items from this meeting
- Update date to next scheduled meeting (if determinable)

### Step 8: Apply Language and Output

1. **Resolve the output language** for the target file path:
   - If `language: per_claude_md`, look up the **target file path** in the project CLAUDE.md LANGUAGE POLICY table. Different paths within the same vault may require different languages (e.g., `meetings/management/` = Swedish, `projects/acme-mobile-v3/meetings/` = English).
   - If `language: english` or `language: swedish`, use that language for all output.
   - If `language: input`, match the transcript/input language.
2. **Apply the resolved language** to all output: summary content, section headings, filename keywords, CHANGELOG entries. When creating preparation files (`/ops prepare`), the preparation must use the language matching its target path -- not a vault-wide default.
3. **CRITICAL: If `swedish_chars: strict`, verify ALL Swedish text uses correct å, ä, ö before writing any file.** Never write "for" instead of "för", "ar" instead of "är", "mote" instead of "möte", etc. See ops-base for full list. This is a blocking requirement.
4. Include suggested CHANGELOG entry
5. Include cross-references to related documents
6. Include next steps or follow-up items

### Step 9: Post-Processing

If `workflows.post_processing` is configured:

#### Task Import (if `task_import.enabled`)
1. Extract action items from the meeting summary (same logic as /transcript Step 4)
2. Find the local `_tasks.yaml` in the folder where the meeting summary was saved (or nearest ancestor). Create with v2 schema if missing.
3. Match extracted items against existing tasks -- update status/notes for tasks mentioned
4. Present NEW action items and offer to import (yes/no/select)
5. For imported tasks: assign defaults (P1, source = meeting file, context from folder)
6. Mark completed items from the meeting in the local _tasks.yaml

#### Dashboard Refresh (if `dashboard_refresh.enabled`)
1. After all file updates and task imports are complete
2. Regenerate the org dashboard using the same logic as `/daily-dashboard {org}`
3. Update symlinks

#### Mark Preparation as Superseded + Bidirectional Link (CR-005, always)

After the meeting summary is created, check if a preparation file exists for this meeting:

1. **Search** the same folder as the meeting summary for files matching any of these patterns where `YYMMDD` matches the meeting date:
   - `YYMMDD-förberedelse-*` (single mode, Swedish)
   - `YYMMDD-preparation-*` (single mode, English)
   - `YYMMDD-facilitator-*` (dual mode, private)
   - `YYMMDD-agenda-*` (dual mode, visible)
2. **If found** (one or more files match), insert a blockquote at the very top of EACH matching file (before the H1 heading):

```markdown
> **Superseded** by [YYMMDD-meeting-summary-filename.md](YYMMDD-meeting-summary-filename.md)

```

3. **Also write a back-link in the meeting summary** (CR-005): add a line in the metadata footer of the summary file pointing to the preparation file(s). For dual mode, link both files:

```markdown
*Preparation: [YYMMDD-förberedelse-filename.md](YYMMDD-förberedelse-filename.md)*
```

or for dual mode:

```markdown
*Preparation: [agenda](YYMMDD-agenda-filename.md) | [facilitator notes](YYMMDD-facilitator-filename.md)*
```

This creates **bidirectional traceability** -- prep -> transcript and transcript -> prep -- so a reader landing on either file can navigate to its counterpart.

4. **Do not** move, archive, or delete the preparation file(s) -- they stay in place to preserve cross-reference links
5. **Do not** modify any other content in the preparation file(s) (only the supersede blockquote is added). Preparation files are **frozen** per the `/preparation` Step 0 rule -- do not edit them post-meeting beyond the supersede marker.

This marking makes it immediately clear that the meeting has been processed, while keeping the preparation available for historical reference. Monthly cleanup (per archive policy) can later move old superseded preparations to `.archive/` in bulk.

#### Generate Post-Meeting Priorities Artifact (if `priorities_artifact.enabled`)

The comprehensive meeting summary (`YYMMDD-<meeting-type>.md`) is **archive material** -- searchable, traceable, comprehensive. It is *not* meant to be the team's daily working list. For meetings where the facilitator drives a working team (daily standups, weeklies, war rooms), produce a **slim companion artifact** that the team actually works from.

This pairs symmetrically with the pre-meeting dual mode (agenda + facilitator): pre-meeting has a two-layer artifact, post-meeting also gets a two-layer artifact (comprehensive summary + slim priorities).

**Trigger:** `workflows.post_processing.priorities_artifact.enabled: true` in the org or project ops-config. Default is `false` -- opt in per meeting type or per project.

**Filename:** `YYMMDD-priorities-post-<meeting-type>.md` in the same folder as the comprehensive summary. Examples:
- `260525-priorities-post-standup.md`
- `260605-priorities-post-weekly.md`

**Source priority** for the slim artifact's content:
1. **Facilitator's post-meeting message** (email / Teams / chat) if one exists -- reproduce verbatim with light formatting. This is the strongest signal because it is the facilitator's chosen prioritization layered on top of the discussion.
2. **Top items from the comprehensive summary's Action Items table** if no facilitator message exists -- pick the items the facilitator emphasized; if unclear, ask the user before drafting rather than guessing.
3. **Skip the artifact** if neither (1) nor (2) yields a clear priority list -- producing a slim doc that just restates the action-items table adds no value.

**Content shape** (target: 1 page, scannable in 30 seconds):
- Short header: facilitator name, source (e.g., "post-standup email"), one-line statement that this is the working list and the comprehensive summary is the archive
- A "top N" table for items the facilitator flagged as the immediate deadline (e.g., "complete by tomorrow EOD") -- columns: #, Item, Owner
- An "in parallel this week" table for non-immediate items
- A one-line note on longer-horizon work (e.g., R3 features) if mentioned
- Footer linking back to the comprehensive summary for context

**Cross-references (bidirectional):**
- The slim priorities file MUST link to the comprehensive summary at the top and in the footer ("Detail in `YYMMDD-<meeting-type>.md` if needed")
- The comprehensive summary MUST link to the slim priorities file in its footer ("Team-working priorities (the slim version): `YYMMDD-priorities-post-<meeting-type>.md` -- this file is the archive; that file is what the team works from")

**Critical rule:** the slim artifact is *not* a summary of the discussion. It is the **working list**. Omit narrative, omit decision rationale, omit cross-references beyond the one back to the comprehensive summary. If it grows past one page, it has drifted into being a second summary -- trim.

**Critical rule:** if the facilitator sends their priority list **after** the meeting summary has already been generated, regenerate the priorities artifact rather than editing in place. The artifact is meant to be the authoritative working list at the time it was sent; older versions stay in `.archive/` if needed.

#### Check Verticals (if configured)

If `workflows.verticals` is configured, check whether any vertical documents should be updated with new information from this meeting.

**Verticals** are living documents that aggregate insights across multiple meetings on a single strategic topic (e.g. a product tracker, a methodology insights document). Unlike meeting summaries (point-in-time), verticals are topic-longitudinal.

1. For each vertical in the config, check if the `trigger` condition is met:
   - `if_mentioned`: scan the meeting summary for any of the `topics` keywords (case-insensitive)
   - `always`: always suggest
2. If one or more verticals are triggered, present a suggestion to the user:
   ```
   Verticals to update:
   - Voice Lake (ops/management/voice-lake-vertikal.md) -- topics matched: voice lake, samtalssammanfattningar
   - AI i utvecklingsorganisationen (ops/management/insikter-ai-utvecklingsorganisation.md) -- topics matched: utvecklingshastighet

   Update now? (yes/no/select)
   ```
3. If user confirms (yes or select), read the vertical document and update relevant sections with new information from this meeting. Preserve the document's existing structure -- add to existing sections, update timelines, append new entries.
4. If vertical file does not exist at the specified path, skip silently (no error).
5. If no verticals are triggered, do not mention verticals at all.

#### Update Rolling Plans (if configured)

If `workflows.rolling_plans` is configured, check whether any rolling plan should be updated from this meeting.

**Rolling plans** are living, shareable per-axis planning documents that aggregate state across a recurring 1-on-1 relationship (one orthogonal workstream axis per partner). They are the **participant-keyed** counterpart to verticals (which are topic-keyed): unlike a meeting summary (point-in-time) or a vertical (topic-longitudinal), a rolling plan is relationship/axis-longitudinal -- "what's on now / next / later, and who owns what" for the workstream that partner owns.

1. **Match by participant.** For each rolling plan in the config, resolve its `participants` using the standard name-resolution algorithm (org `team[]` + `_contacts/*/_meta.yaml`, case-insensitive, Swedish-char folding). The plan is triggered when this meeting's resolved participant set intersects `participants` (typically a 1-on-1, but any matching meeting qualifies). Skip plans with `status: archived`.
2. **Suggest the update** (same yes/no/select UX as verticals):
   ```
   Rolling plan to update:
   - Alex-Bob (meetings/management/Bob/rolling-plan-Alex-Bob.md) -- axis: website / sign-up / data / go-to-market

   Update now? (yes/no/select)
   ```
3. **On confirm**, update the plan in place, preserving its structure (Overall goals -> Links/tools -> Cadence -> NOW / NEXT / LATER -> Carry-forward):
   - **move completed rows out** -- into the meeting summary just written (they become the audit trail there; don't lose them),
   - **add new NOW items** surfaced in the meeting, in the correct owner column,
   - **reflect decisions / status changes** -- update wording to the current state; never translate stale wording back in,
   - keep the doc in its configured `language`.
4. **Golden rule -- one item = one owner = one doc.** If a row clearly belongs to another registered plan's axis, link it rather than copy it. Keep each plan's "Sister documents" cross-link block consistent with the set of configured plans.
5. **If the target file does not exist**, offer to scaffold it from the rolling-plan template (`ops-config/templates/rolling-plan.md`, or the org's `templates.rolling_plan` override) rather than erroring -- header + Sister-documents block (generated from the other configured plans' `axis` strings) + empty NOW / NEXT / LATER tables.
6. **If no rolling plan is triggered**, do not mention rolling plans at all.

---

## STATUS TERMINOLOGY

### Default (from ops-base)

When no `status_terminology` is configured:
- Priority: P0 (critical), P1 (high), P2 (important), P3 (research)
- Status: BLOCKED, IN PROGRESS, ON TRACK, TODO, PLANNED, COMPLETE

### Custom (from config)

When `status_terminology` is configured, use the provided terms in summary tables:
- `work_status` terms for current state of work items
- `resolution_status` terms for resolution/outcome of issues

### Issue IDs

When `issue_id_format` is configured, assign IDs to discovered issues following the pattern. Otherwise, no structured issue IDs.

---

## FILE NAMING

- Follow project CLAUDE.md conventions for all file paths and names
- Only CHANGELOG.md and README.md are uppercase; all other files use lowercase
- Use hyphens between words in filenames
- Default meeting filename: `YYMMDD-participants-description.md`

---

## FALLBACK BEHAVIOUR

When no org config is found:
- Use base.yaml defaults
- Create meeting summary only (`update_files: [summary]`)
- Use TWO-TIER format from CLAUDE.md (or sensible default if no CLAUDE.md)
- Match input language
- No action propagation
- No agenda management
- No domain additions

When a target file does not exist:
- For CHANGELOG.md: create with initial entry
- For README.md: create basic structure
- For _tasks.yaml: create with v2 schema (version: 2, context from folder, scope from path)
- For meetings/README.md: create basic index

---

## OUTPUT REQUIREMENTS

### Accuracy
- Verify participant attribution before finalizing
- Cross-check numbers, dates, and technical specs
- Ensure all decisions are captured with rationale

### Cross-References
- Link to meeting summary from CHANGELOG
- Link to related documents where relevant
- Use relative paths for all links

### Always Include
- Owner assignment per `responsibility_matrix`
- Follow-up commitments with deadlines
- Suggested CHANGELOG entry
- Next steps

---

## ATTACHMENTS AND MEDIA

When processing meetings that reference presentations, PDFs, or other binary files:

### Detection
- Look for mentions of "presentation", "slides", "PDF", "deck", "demo", "recording" in transcript
- Check if Deep Thought metadata includes a recording reference
- Ask user if attachment exists and where it is located

### Placement
- Project-specific attachments: `.attachments/` within the project folder
- Vault-level attachments: `.attachments/` at vault root (per vault CLAUDE.md)
- Follow the project CLAUDE.md if it specifies a different location

### Naming Convention
- Format: `YYMMDD-description.ext` or `description-YYYY-MM-DD.ext`
- Use lowercase with hyphens
- Match the meeting date when the attachment was presented

### Linking
In meeting summaries, add a "Related:" section after the preview/context links:

```markdown
**Related:**
- [Presentation Title (PDF)](../.attachments/YYMMDD-filename.pdf)
- [Preparation](YYMMDD-preparation-org-type.md)
```

### Workflow
1. If attachment is mentioned but location unknown, ask user
2. If attachment exists in wrong location (e.g., `assets/`), suggest moving to `.attachments/`
3. Add link to meeting summary under "Related:"
4. Ensure project CLAUDE.md documents `.attachments/` in folder structure
