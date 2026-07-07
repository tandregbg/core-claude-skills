---
name: daily-dashboard
description: Create daily dashboard with meeting agendas, tasks, and quick-access links. Creates both Obsidian-compatible dashboard file and desktop symlinks.
user-invocable: true
argument-hint: [org] [today|tomorrow|YYMMDD]
---

# /daily-dashboard -- Daily Meeting & Task Dashboard

Generate a dashboard file and symlinks for quick access to today's (or specified date's) meetings, preparations, and project status.

**Standalone skill** -- no dependency on ops-base.

**Two modes:**
- **Generic mode** (default) -- scan current working directory for dated files
- **Org mode** -- load org-specific config for project-specific discovery

---

## String Resolution

Template strings marked as `{strings.section.key}` are resolved at runtime.

**Resolution order:**

1. Org config `strings` section (if loaded)
2. Language-matched defaults from `base.yaml`:
   - `swedish` -> `strings_sv`
   - `english` -> `strings`
   - `input` -> match detected language
3. Hardcoded strings already in template (fallback -- current Swedish defaults)

When scanning for files, always check **both** `{strings.filename_keywords.*}` and `{strings_sv.filename_keywords.*}` to handle files created in either language regardless of current config.

---

## Argument Parsing

Parse arguments left to right:

1. **First argument:** Check if it matches a known org config name by looking for `~/.claude/skills/{arg}-ops-config/{arg}.yaml`. If found, load that config and shift to the next argument.
2. **Remaining argument:** Date specification -- `today` (default), `tomorrow`, or `YYMMDD` format (e.g. `260219`).

### Examples

```
/daily-dashboard                 -> Generic mode, today's date
/daily-dashboard today           -> Generic mode, today's date
/daily-dashboard tomorrow        -> Generic mode, tomorrow's date
/daily-dashboard 260219          -> Generic mode, specific date
/daily-dashboard acme         -> Org mode (Acme config), today's date
/daily-dashboard acme 260219  -> Org mode (Acme config), specific date
```

---

## Mode Selection

- If an org config was loaded -> **Org Mode** (project-specific discovery)
- If no org config -> **Generic Mode** (recursive scan from cwd)

## Dashboard Filename

| Mode | Filename |
|------|----------|
| Generic | `_Dashboard.md` |
| Org | `_Dashboard-{org}.md` (e.g. `_Dashboard-acme.md`) |

This prevents collisions when running both generic and org dashboards. Both files coexist in the vault root directory.

---

## Date Handling

Parse the date argument to determine target date:
- No date argument or `today` -> current date
- `tomorrow` -> next day
- `YYMMDD` format -> specific date (e.g. `260219` = 2026-02-19)

Compute both:
- **Target date** (YYMMDD) -- for today's files
- **Next date** (YYMMDD+1) -- for tomorrow's preparations

Use target date for:
- Finding meeting/preparation files (`YYMMDD-*.md`)
- Dashboard header
- Symlink naming (`_TODAY-*` always refers to target date)

---

## Generic Mode

### Vault Detection

- **Vault root** = current working directory
- **Dashboard location** = vault root (same as cwd)
- **Dashboard filename** = `_Dashboard.md`

### File Discovery

Scan all subdirectories of the vault root for files matching `YYMMDD-*.md` where YYMMDD = target date. Also scan for YYMMDD+1 (next date) to find upcoming preparations.

**Scan locations:**
- All `_contacts/*/` contact folders (recursively)
- Root of vault
- Any other subdirectories

### File Categorization

Categorize discovered files by keywords in the filename:

| Keyword in filename | Category | Produced by |
|---------------------|----------|-------------|
| `förberedelse` or `preparation` | **{strings.dashboard.preparations_today}** | `/preparation` |
| `standup` or `daily-standup` | **{strings.dashboard.standup_section}** | `/ops` |
| Everything else (`samtal`, `sammanfattning`, etc.) | **{strings.dashboard.meetings_today}** | `/transcript`, `/ops` |

Always scan for both Swedish and English keywords to discover files regardless of which language was used when creating them.

### Meeting Status Detection

Determine whether each meeting/standup has been completed or is still pending. Apply `(Completed)`, `(Pending)`, or no label to the `### ` heading.

**Detection logic (in order):**

1. **Preparation-only file** (filename contains `förberedelse` or `preparation`): Mark as `(Pending)` -- the meeting hasn't happened yet.
2. **Summary/transcript file** (no preparation keyword in filename): Check the file content:
   - **Canonical headings (CR-006):** `## Nästa steg`, `## Next Steps`, `## Beslut`, `## Decisions`, `## Konklusion`, `## Outcome`, `## Diskussion`, `## Discussion`
   - **Legacy headings (read-only back-compat for files written before CR-006):** `## Summary`, `## Executive Summary`, `## Sammanfattning`, `## Action Items`, `## Åtgärdspunkter`, `## Huvudpunkter`, `## Key Discussion Points`, `## Decisions Made`, `#### Introduction` with date/time/participants
   - If the file contains **any** of the canonical or legacy headings above -- it is a **completed meeting summary**. Mark as `(Completed)`.
   - If the file is a standalone preparation without a corresponding transcript -- mark as `(Pending)`.
3. **Both preparation AND transcript exist** for the same meeting: The transcript supersedes (see Deduplication below). Mark the transcript entry as `(Completed)`.

**Important:** When running the dashboard later in the day (after meetings have occurred and been transcribed), most files will be summaries. The dashboard MUST reflect this by showing `(Completed)` status. A file that IS a meeting summary is by definition completed -- do not leave it without a status label.

**Status labels use title case:** `(Completed)`, `(Pending)`, `(In Progress)`.

### Deduplication

When both a preparation and a transcript exist for the **same contact + same date**:

- Show only the **transcript** in the meetings section (it supersedes the preparation)
- **Do NOT** also show the preparation in the preparations section (avoid duplication)
- The preparation remains accessible via the transcript's cross-reference link (added by `/transcript` Step 1.5)

This prevents the same meeting from appearing twice in the dashboard.

### Contact Name Extraction

Extract the contact name from the parent folder using the name resolution algorithm:

1. **Check for `_meta.yaml`** in the contact folder:
   - If exists and has `display_name`, use it directly
   - If has `company` field, use it for company context
   - Result: canonical spelling with correct Swedish characters (e.g., "David Ekberg", "Erik Sandberg")

2. **Fallback** (no `_meta.yaml`):
   - Take the folder name (e.g. `david-ekberg`)
   - Replace `-` with space
   - Apply title case
   - Result: `David Ekberg`
   - For company-suffixed folders (e.g. `erik-lindgren_techco`), the part after `_` is the company name

If the file is not in a `_contacts/*/` folder, use the filename to derive a display name.

See [Contact Metadata Schema](../ops-config/contact-meta-schema.md) for `_meta.yaml` specification.

### Content Extraction

For each discovered file, extract:
- **Title** from the H1 heading (`# ...`)
- **Key talking points** from numbered `## ` sections (first 3-5 items)
- **Date/time** if mentioned in the heading or content

### Dashboard Template (Generic)

```markdown
# Dashboard - [YYYY-MM-DD] ([Weekday])

{strings.metadata.generated}: [timestamp]

---

## {strings.dashboard.preparations_today}

### [Contact Name]: [Title from H1]
**{strings.dashboard.file_label}:** [Filnamn](relative/path/to/file)

**{strings.dashboard.topics_label}:**
- [Key point 1 from ## sections]
- [Key point 2]
- [Key point 3]

---

### [Next Contact]: [Title]
...

---

## {strings.dashboard.meetings_today}

### [Contact Name]: [Title from H1]
**{strings.dashboard.file_label}:** [Filnamn](relative/path/to/file)

---

## {strings.dashboard.standup_section}

### [Project]: [Title from H1]
**{strings.dashboard.file_label}:** [Filnamn](relative/path/to/file)

---

## Uppgifter

[Generated from _tasks.yaml, all projects where private=false]

### Överförfallna
- [ ] #[id] [task] ([project]) -- [days] dagar

### P1 - Denna vecka
- [ ] #[id] [task] ([project], [due])
- [~] #[id] [task] ([project]) -- PÅGÅR

### P2 - Viktigt
- [ ] #[id] [task] ([project])

---

## Slutfört idag

[From _tasks-history.md for target date]
- [x] [task] ([project])

---

## {strings.dashboard.preparations_tomorrow}

### [Contact Name]: [Title from H1]
**{strings.dashboard.file_label}:** [Filnamn](relative/path/to/file)

**{strings.dashboard.topics_label}:**
- [Key point 1]
- [Key point 2]

---

## {strings.dashboard.no_meetings}

[Message if no files found for target date]
```

If a section has no files, omit the entire section (including the standup section -- only show it when standup files are found). If no files are found at all, state that clearly.

The "Uppgifter" section is always shown if `_tasks.yaml` exists and has active tasks. The "Slutfört idag" section is only shown if there are completions for the target date.

### Triage (read-only, CR-022)

If the vault has a registered **triage doc** (an `_inbox/` working document with `type: working_doc` + tag `do-not-process` -- see `docs/schemas/inbox.md`, CR-022 section), add a **Triage** section: link the doc, then inline its open PRIO items and the DENNA VECKA bucket headings with open-item counts. Optionally show the INKORG count as a nudge (`INKORG: 6 osorterade`).

```
## Triage

[daglig-triage.md](_inbox/daglig-triage.md) · Veckoankare: <line> · INKORG: <N> osorterade

### PRIO
- [ ] <open PRIO items verbatim>

### DENNA VECKA
- <bucket>: <N> öppna
```

This surface is **read-only** -- the dashboard never writes to, reorders, or checks off triage items (same principle as Rolling Plans). Upkeep is owned by the human plus `/inbox triage refresh`. No registered triage doc: omit the section entirely.

Applies to **both generic and org mode** (the triage doc is personal and vault-level, not org-scoped).

### Symlinks (Generic)

Created in the vault root directory (same directory as the dashboard file):

```bash
# Remove old dynamic symlinks
rm -f _TODAY-*.md _PREP-*.md

# Create preparation symlinks
ln -sf "_contacts/contact-folder/YYMMDD-förberedelse-file.md" "_PREP-ContactName.md"

# Create meeting/summary symlinks
ln -sf "_contacts/contact-folder/YYMMDD-samtal-file.md" "_TODAY-ContactName.md"
```

**Important:** In generic mode, do NOT create or touch persistent symlinks (`_MGMT-*`, `_MKT-*`, `_MOBILE-*`, etc.). Those are org mode only.

Symlink paths are relative to the vault root (e.g. `_contacts/contact-folder/...`).

---

## Org Mode (with org config)

When an org config is loaded (e.g. `acme`):

### Config Loading

Load config from `<vault>/<org>/_ops.yaml` (CR-011). Falls back to `~/.claude/skills/{org}-ops-config/{org}.yaml` with a deprecation warning until v1.17.0. This provides:
- Team structure
- Terminology
- Workflow settings

### Vault Detection

1. Look for `CLAUDE.md` in current directory or parents
2. Extract vault structure from CLAUDE.md (MEETING ROUTING, etc.)
3. Fallback to vault path convention: `~/Vault/{org}`

Dashboard goes in **parent** of vault for cross-project visibility.

**Dashboard filename** = `_Dashboard-{org}.md` (e.g. `_Dashboard-acme.md`). This avoids overwriting the generic `_Dashboard.md`.

### Meeting Discovery (Org Mode)

Use CLAUDE.md MEETING ROUTING if available. Otherwise scan org-specific paths:

```
meetings/management/YYMMDD-*.md
meetings/management/Bob/YYMMDD-*.md
meetings/management/Carol/YYMMDD-*.md
meetings/marketing/ppc/YYMMDD-*.md
meetings/marketing/meta/YYMMDD-*.md
meetings/marketing/strategic/YYMMDD-*.md
meetings/YYMMDD-*.md                      # Project standup summaries
```

For each found meeting, extract:
- Title from H1 heading
- Agenda items (## sections)
- Decisions needed (if any)

Files containing `standup` or `daily-standup` in the filename are categorized under `{strings.dashboard.standup_section}` rather than general meetings.

### Rolling Plans (Org Mode, read-only)

If the loaded org config has `workflows.rolling_plans` (CR-014), add a **Rolling plans** section to the dashboard linking each configured plan (skip `status: archived`). For each plan, show its `axis` and a relative link to the doc; optionally pull the plan's **NOW** block (rows that have a status set) so the day's working items are visible at a glance.

This surface is **read-only** -- the dashboard never writes to or maintains rolling plans. Maintenance is owned by `/ops` (participant-triggered update after a 1-on-1). If a configured plan's file is missing, list it as `(not yet scaffolded)` rather than erroring.

Dashboard section template:

```
## Rolling plans

- **[<Partner>](<relative path>)** -- <axis>
  - NOW: <first few open NOW rows, owner-tagged>   # optional
```

### Task Discovery (Org Mode)

Scan for `_tasks.yaml` files under the org's vault path:

**Management:**
- `ops/management/_tasks.yaml` -- domain tasks
- `ops/management/CHANGELOG.md` -- recent entries

**Marketing:**
- `ops/marketing/_tasks.yaml` -- domain tasks
- `ops/marketing/tasks/YYMMDD-active-tasks.md` or latest `260*-active-tasks.md`

**Mobile/Projects:**
- `projects/*/_tasks.yaml` -- project tasks
- `projects/*/README.md` -- current status

---

## Personal Task Integration

The dashboard integrates with distributed `_tasks.yaml` files across the vault.

### Task File Discovery

```
{vault_root}/_tasks.yaml                          # Root: projects registry + cross-project
{vault_root}/_projects/acme/_tasks.yaml             # Org-level tasks
{vault_root}/_projects/acme/ops/management/_tasks.yaml     # Domain tasks
{vault_root}/_projects/bravo/project-alpha/_tasks.yaml     # Project tasks
{vault_root}/_private/_tasks.yaml                  # Personal tasks
{vault_root}/_contacts/*/_tasks.yaml               # Contact tasks
{vault_root}/_tasks-history.md                     # Completed tasks log
```

Scan all `_tasks.yaml` files recursively in `_projects/`, `_contacts/`, and `_private/` (skip `.` dirs). Each file has a `context` field identifying the source.

### Reading Tasks

1. **Scan all `_tasks.yaml` files** in the vault (root + `_projects/*/` + `_contacts/*/` + `_private/`, recursively, skip `.` dirs)
2. **Filter tasks** based on mode:
   - **Generic mode:** Show all tasks where `private: false`, grouped by `context`
   - **Org mode:** Show tasks from `_tasks.yaml` files under the org's vault path (e.g., `_projects/acme/**/_tasks.yaml`)
3. **Group by context** (from file-level `context` field), then by priority
4. **Apply due date logic:**
   - Overdue: `due` date has passed
   - Due today: `due` matches target date
   - Due this week: `due` within 7 days
   - No due date: Show in backlog

### Task Display Format

For the "Teamfokus" section, generate task lists from `_tasks.yaml`:

```markdown
## Teamfokus denna vecka

### Alex
[Generated from _tasks.yaml where project={org} or all projects in generic mode]

**Överförfallna:**
- [ ] #32 Offer Ivan 1-on-1 (due: 260215) -- 6 days overdue

**P0 - Kritiskt:**
- [ ] #8 Prata med Hank om teknisk scope (P0, due: idag)

**P1 - Denna vecka:**
- [ ] #1 Initiera brand/webb-möte (P1, innan styrelsemöte)
- [ ] #2 Planera Carols vecka (P1, due: 260305)
- [ ] #3 Boka styrelsemiddag (P1, due: 260310)

**P2 - Pågående:**
- [~] #5 Ha radarn på Indien-kostnader (P2, ongoing) -- IN PROGRESS
- [ ] #11 Offer Ivan 1-on-1 (P2)
```

### Privacy Filtering

- Tasks with `private: true` are **only shown** if running in a personal/private context
- In org mode with `shared_view: true`, only show tasks where `private: false`
- The dashboard owner (Alex) sees all tasks; shared dashboards filter private tasks

#### Contact-Level Filtering (CR-009)

When discovering files from `_contacts/` folders, resolve the contact's `classification` (see [Contact Metadata Schema](../ops-config/contact-meta-schema.md)):

| Classification | Generic mode | Org mode (shared) |
|---------------|-------------|-------------------|
| `family` | Show (personal view) | **Exclude** |
| `personal` | Show (personal view) | **Exclude** |
| `professional` | Show | Show |
| `confidential` | Show (personal view) | **Exclude** (unless opted in) |

Classification is resolved from: `_meta.yaml` `classification` field > `_meta.yaml` `private` field > folder name pattern (`a1-*`/`a2*` = family) > default `professional`.

### Task Status Mapping

| YAML status | Display |
|-------------|---------|
| `pending` | `[ ]` |
| `in_progress` | `[~]` with "IN PROGRESS" label |
| `blocked` | `[!]` with blocked reason |

### Completed Tasks (Today)

Pull from `_tasks-history.md` for tasks completed on target date:

```markdown
## Slutfört idag

- [x] #47 War Room mobile app
- [x] #48 Daily standup
- [x] #49 Meet with Frank
```

### Source Links

Include source links for context:

```markdown
- [ ] #1 Initiera brand/webb-möte (P1)
  Source: [260220-samtal-Alex-Frank.md](path/to/260220-samtal-Alex-Frank.md)
```

Or in compact form:
```markdown
- [ ] #1 Initiera brand/webb-möte (P1) -- [Frank](path/to/260220-samtal-Alex-Frank.md)
```

### Fallback Behavior

If `_tasks.yaml` does not exist:
1. Check for legacy task files (`ops/management/todo-Alex.md`, etc.)
2. If found, read and display in legacy format
3. Suggest running `/tasks migrate` to upgrade

### Task Counts in Quick Stats

Include task metrics in the Quick Stats table:

```markdown
## Quick Stats

| Område | Status | Nyckeltal |
|--------|--------|-----------|
| **Tasks** | 13 active | 3 P1, 2 overdue |
| **Mobile** | EXTERNAL RELEASE | v1.1.58 idag |
| **Website** | IN PROGRESS | Bob fredag |
```

### Dashboard Template (Org Mode)

```markdown
# Dashboard - [Date: YYYY-MM-DD] ([Weekday])

Genererad: [timestamp]

---

## Standup/Projekt

[Standup summaries from today, if any]

### [Project]: [Title] - [STATUS]
**Documentation:**
- [Today's Standup Summary](path/to/standup.md)
- [Current Status (README)](path/to/README.md)

**Key Decisions:**
- Decision 1
- Decision 2

---

## Today's Meetings

### [Meeting 1 Title]
**File:** [meeting title](path/to/meeting)
**Time:** [if known]

#### Agenda
- Item 1
- Item 2

#### Decisions Needed
- Decision 1

---

### [Meeting 2 Title] (Completed)
**File:** [meeting title](path/to/meeting)

**Key Outcomes:**
- Outcome 1

---

## Priority Tracker Links

### Management
- [Tasks](path/to/ops/management/_tasks.yaml)
- [CHANGELOG](path/to/CHANGELOG.md)

### Mobile
- [Mobile Status](path/to/README.md)
- [Mobile Tasks](path/to/projects/acme-mobile-v3/_tasks.yaml)

### Marketing
- [Marketing Tasks](path/to/ops/marketing/_tasks.yaml)

---

## Critical Items (P0)

[Extract from _tasks.yaml where priority=P0 and project={org}]

| Issue | Ansvarig | Status |
|-------|----------|--------|
| **Task description** | Owner | STATUS |

---

## Quick Stats

| Område | Status | Nyckeltal |
|--------|--------|-----------|
| **Tasks** | [count] active | [P1 count] P1, [overdue count] overdue |
| **Mobile** | [status] | [key metric] |
| **Website** | [status] | [key metric] |
| **Marketing** | [status] | CPA: [value] SEK |

---

## Teamfokus denna vecka

### Alex
[Generated from _tasks.yaml where project={org}]

**Överförfallna:** (if any)
- [ ] #[id] [task] (due: [date]) -- [days] days overdue

**P0 - Kritiskt:** (if any)
- [ ] #[id] [task] (P0)

**P1 - Denna vecka:**
- [ ] #[id] [task] (P1, [due info])
- [~] #[id] [task] (P1) -- IN PROGRESS

**P2 - Pågående:**
- [ ] #[id] [task] (P2)

### [Other Team Member]
[From priority-matrix or other sources]
- [ ] Task 1
- [ ] Task 2

---

## Kommande

| Datum | Event | Ansvarig |
|-------|-------|----------|
| [date] | [event] | [owner] |
| [date] | [event] | [owner] |

---

## Senaste CHANGELOG-poster

### [YYYY-MM-DD] - [Title]
- Key point 1
- Key point 2

### [YYYY-MM-DD] - [Title]
- Key point 1

---

*Genererad: [timestamp]*
```

### Symlinks (Org Mode)

Create in vault root directory:

```bash
# 1. Remove broken symlinks (targets that no longer exist)
find . -maxdepth 1 -name "_*.md" -type l ! -exec test -e {} \; -delete

# 2. Remove old TODAY symlinks
rm -f _TODAY-*.md

# 3. Create new symlinks for found meetings
ln -sf "{org}/path/to/meeting.md" "_TODAY-MeetingName.md"

# 4. Create/update persistent symlinks (org-specific)
ln -sf "{org}/ops/management/_tasks.yaml" "_MGMT-Tasks.md"
ln -sf "{org}/ops/marketing/tasks/active-tasks.md" "_MKT-Active-Tasks.md"
# ... etc per org vault structure
```

Persistent symlinks (`_MGMT-*`, `_MKT-*`, `_MOBILE-*`, etc.) are only created/updated in org mode.

---

## Casing Convention

Use **title case** consistently for meeting status labels:
- Correct: `(Completed)`, `(In Progress)`, `(Pending)`
- Wrong: `(COMPLETED)`, `(IN PROGRESS)`, `(PENDING)`

This applies to meeting headers: `### Meeting Name (Completed)`

---

## Execution Steps

1. **Parse arguments** -- determine org (if any) and target date
2. **Select mode** -- generic or org
3. **Detect vault** -- cwd (generic) or CLAUDE.md/config (org)
4. **Clean up broken symlinks** in vault root (targets that no longer exist)
5. **Discover files** -- scan for YYMMDD-*.md matching target date and next date
6. **Read and extract** -- H1 titles, key content, talking points
7. **Load tasks** -- scan all `_tasks.yaml` files in vault, filter by org/context/privacy
8. **Load completed tasks** -- read today's completions from `_tasks-history.md`
9. **Generate dashboard** -- apply appropriate template with meetings + tasks
10. **Write dashboard** -- save to vault root: `_Dashboard.md` (generic) or `_Dashboard-{org}.md` (org mode)
11. **Create symlinks** -- in vault root, cleaning old dynamic ones first
12. **Report** -- list what was created (including task counts and any broken symlinks removed)

---

## Output

After execution, report what was found and created:

### Generic mode example

```
Dashboard skapad: _Dashboard.md (generic)

Filer hittade för 2026-02-19:
  Förberedelser:
  - David Ekberg: 260219-förberedelse-samtal-Alex-David-Ekberg.md
  Samtal:
  - Erik Sandberg: 260219-samtal-Alex-Erik-Sandberg-lokal-LLM-infrastruktur-kunddata.md
  Standup/Projekt:
  - Project Alpha: 260219-project-alpha-daily-standup.md

Deduplicerade (förberedelse dold -- samtal finns):
  - Erik Sandberg: 260219-förberedelse-möte-erik-sandberg (samtal hittad)

Morgondagens förberedelser (2026-02-20):
  - Bob Lindgren: 260220-förberedelse-samtal-Alex-Bob-Lindgren.md

Symlinks skapade:
  - _PREP-David-Ekberg.md
  - _TODAY-Erik-Sandberg.md
  - _TODAY-Project-Alpha-Standup.md
```

### Org mode example

```
Dashboard created: _Dashboard-acme.md

Broken symlinks removed: [count, if any]
- _OLD-Deleted-File.md (target missing)

Meetings found for 2026-02-19:
- Management Weekly (260219-Acme-Weekly-Management-Meeting.md)
- Bob 1-on-1 (260219-Alex-Bob-lunch-briefing.md)

Symlinks created:
- _TODAY-Management.md
- _TODAY-Bob.md
- _MGMT-Priority-Matrix.md
- _MKT-Active-Tasks.md

Critical items: 2 (see dashboard)
```

---

## Language

### Generic mode
- Dashboard content is written in **Swedish** (uses `strings_sv` defaults)
- Swedish text MUST use correct characters -- never substitute
- Section headers resolved from strings: `{strings.dashboard.preparations_today}`, `{strings.dashboard.meetings_today}`, `{strings.dashboard.preparations_tomorrow}`
- Status labels stay English: `(Completed)`, `(In Progress)`

### Org mode
- Follow the org config `language` setting
- If `per_claude_md`, follow the project CLAUDE.md LANGUAGE POLICY
- If `swedish_chars: strict`, enforce correct characters

### Common mistakes to avoid in Swedish output
- "pagaende" -> "pågående", "foretag" -> "företag", "fran" -> "från"
- "fore" -> "före", "nasta" -> "nästa", "behovs" -> "behövs"
- "anvandning" -> "användning", "mote" -> "möte", "losning" -> "lösning"
- "forberedelse" -> "förberedelse", "sammanfattning" stays as-is

---

## Notes

- Generic dashboard: `_Dashboard.md`. Org dashboard: `_Dashboard-{org}.md`. Both coexist -- no collision.
- Dashboard files work on mobile (no symlinks needed)
- Symlinks are bonus for desktop quick access
- Old `_TODAY-*` and `_PREP-*` symlinks are cleaned up automatically each run
- Broken symlinks (pointing to deleted files) are removed automatically
- Persistent symlinks (`_MGMT-*`, `_MKT-*`, `_MOBILE-*`) are only created/updated in org mode
- Generic mode scans recursively -- works with any vault structure that uses `_contacts/` folders
- Use standard markdown links: `[Display Name](relative/path/to/file)` (NOT wikilinks -- wikilinks are not supported by Typora)

---

## Task Integration Notes

### Required Files

The task integration uses distributed files:

| File | Purpose | Created by |
|------|---------|------------|
| `_tasks.yaml` (root) | Projects registry + cross-project tasks | `/tasks` skill |
| `_tasks.yaml` (per-folder) | Folder-specific tasks | `/tasks`, `/ops`, `/transcript` |
| `_tasks-history.md` | Completed tasks log | `/tasks done` command |

### Symlink for Task File

Optionally create a persistent symlink for quick access:

```bash
# In vault root directory
ln -sf "_tasks.yaml" "_TASKS.yaml"
```

### Migration from Legacy

If `_tasks.yaml` doesn't exist but legacy files do (e.g., `todo-Alex.md`), the dashboard will:

1. Display a notice: "Task tracker not configured"
2. Suggest: "Run `/tasks migrate` to upgrade from legacy task files"
3. Fall back to reading legacy files if available

### Task File Schema

See `~/.claude/skills/tasks/skill.md` for the complete `_tasks.yaml` schema.

### Cross-Project Task Display

In org mode (`/daily-dashboard acme`):
- Only show tasks from `_tasks.yaml` files under the org's vault path
- Respect `private: true/false` based on dashboard sharing settings

In generic mode (`/daily-dashboard`):
- Show all tasks across all `_tasks.yaml` files, grouped by context
- Always respect `private: true` (hide from output)
- Root tasks always included
