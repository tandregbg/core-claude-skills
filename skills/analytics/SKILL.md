---
name: analytics
description: Vault-level content analytics — file creation trends, skill adoption, contact engagement, content distribution, pipeline outcome metrics (insights/tasks/changelog per meeting), and unprocessed backlog detection. Outputs to _analytics/ folder.
user-invocable: true
argument-hint: [overview|skills|contacts|pipeline|backlog|help]
---

# /analytics -- Vault Content Analytics

Analyse the vault as a dataset — file metadata (names, dates, paths, counts), not file contents. Answers "how is my system performing?" rather than "what did I learn from this conversation?"

**Standalone skill** — no dependency on ops-base or ops-config.

**Key distinction from `/insights`:** The insights skill extracts *knowledge from conversations* (decisions, learnings, patterns about people and projects). This skill analyses *the vault itself* — creation velocity, skill adoption, engagement frequency, content distribution.

---

## Design Principles

- **Metadata and structured fields only.** Read filenames, paths, dates, and file sizes. Never read prose content — the only in-file reads allowed are lightweight classification (H1 heading, first line) and **structured-field scans** for the pipeline subcommand: regex-matching `date:`/`type:` lines in `_insights.yaml`, `created:` lines in `_tasks.yaml`, and `- **YYMMDD:` bullets in `CHANGELOG.md`. Field values only; summaries, rationale, and notes are never read.
- **Non-destructive.** Only writes to `_analytics/` — never modifies existing files.
- **Snapshot-based.** Each run produces a dated snapshot. Historical snapshots enable trend comparison.
- **Privacy-aware.** Contact names appear in analytics (they are folder names, not extracted content). Mark private contacts with `private: true` in `_meta.yaml` to exclude them from output.

---

## Output Location

All output goes to `{vault_root}/_analytics/`:

```
_analytics/
├── YYMMDD-vault-overview.md       <- /analytics overview
├── YYMMDD-skill-adoption.md       <- /analytics skills
├── YYMMDD-contact-engagement.md   <- /analytics contacts
├── YYMMDD-pipeline-report.md      <- /analytics pipeline
├── YYMMDD-backlog-report.md       <- /analytics backlog
└── .archive/                      <- older snapshots (auto-archived)
```

**Archive policy:** When writing a new snapshot, move any existing file of the same type to `.archive/` with its date prefix preserved. Keep the latest of each type at the top level.

---

## Vault Detection

Determine vault root:

1. Walk up from cwd looking for `_contacts/` or `_projects/` markers
2. Fallback: `$OBSIDIAN_VAULT` environment variable
3. Fallback: cwd itself

---

## File Discovery

The core scanning step shared by all subcommands.

### YYMMDD File Detection

Scan vault recursively (max depth 8, skip `.archive/`, `.handoff/`, `.git/`, `node_modules/`, `clones/`). Match files where the basename starts with 6 digits followed by a separator:

```
Pattern: /^(\d{6})[-_ ]/
```

Validate the 6 digits as a plausible date:
- Year (positions 1-2): 22-29 (2022-2029)
- Month (positions 3-4): 01-12
- Day (positions 5-6): 01-31

### Metadata Collected Per File

| Field | Source |
|-------|--------|
| `date` | Filename prefix (YYMMDD) |
| `path` | Relative path from vault root |
| `directory` | Parent directory (2 levels from vault root) |
| `extension` | File extension (.md, .txt, .pptx, etc.) |
| `skill_type` | Classified by path and filename keywords (see below) |
| `contact` | Extracted from `_contacts/{name}/` path segment, if present |

### Skill Classification

Classify each file by **path first, keywords second**:

**Step 1 — Path-based classification** (highest confidence):

| Path contains | Classification |
|---------------|---------------|
| `_inbox/` | `inbox` |
| `_analytics/` | `analytics` (skip — don't count own output) |
| `_outbox/` | `outbox` |

**Step 2 — Keyword-based classification** (filename, case-insensitive):

| Keywords | Classification |
|----------|---------------|
| `samtal`, `call`, `transcript` | `transcript` |
| `agenda`, `facilitator` | `agenda` (dual-mode docs, CR-018 — check before preparation) |
| `förberedelse`, `preparation`, `prep-` | `preparation` |
| `meeting`, `möte`, `standup`, `board`, `alignment`, `kickoff`, `weekly`, `sprint`, `retro`, `sync`, `sammanfattning`, `summary` | `ops/meeting` |

**Step 3 — Directory-context classification** (for files that didn't match keywords):

| Directory pattern | Classification |
|-------------------|---------------|
| `meetings/` or `moten/` or `möten/` anywhere in path | `ops/meeting` |
| `ops/` anywhere in path | `ops` |
| `_resor/` or `resor/` | `travel` |
| `ppc/` or `marketing/` or `marknads` | `marketing` |
| `.txt` extension | `raw-text` |
| `.pptx`, `.pdf`, `.docx`, `.xlsx` | `office-doc` |
| `.png`, `.jpg`, `.jpeg`, `.heic` | `image` |

**Step 4 — Fallback:** `uncategorized`

### Privacy Filtering (CR-009)

Before including a contact in named output:

1. **Resolve classification** for the contact folder:
   - If `_meta.yaml` exists and has `classification` field: use it
   - Else if `_meta.yaml` exists and has `private: true`: treat as `personal`
   - Else check folder name against `privacy_defaults` in `base.yaml`:
     - `_contacts/a1-*` or `_contacts/a2*` → `family`
   - Else default: `professional`

2. **Apply filtering by subcommand:**
   - `/analytics contacts`: Exclude `family` and `personal` contacts from output
   - `/analytics overview`, `/analytics skills`: Include all files in aggregate counts without contact attribution
   - `/analytics backlog`: Include all files (backlog is about content gaps, not people)

3. **Never expose family/personal contact names** in any output file. Aggregate their files into totals only.

---

## Subcommands

### `overview` -- Vault-wide metrics snapshot

**Trigger:** `/analytics overview` or `/analytics` (default subcommand)

**Steps:**

1. Run file discovery (scan vault)
2. Compute summary metrics:
   - Total YYMMDD files, date range, unique active dates, active months
   - Current pace (files/day for current quarter)
   - **Active-day density** — active days / calendar days for the current quarter (e.g. `84/91`), plus files per *active* day. The gap between files/day and files/active-day shows whether growth comes from busier days or from fewer idle days.
   - Trend direction (current quarter rate vs previous quarter rate)
3. Compute yearly totals with year-over-year growth multiplier
4. Compute **content type × quarter pivot** — the core analytical view showing how each skill type's volume evolves over time. Columns: transcript, ops/meeting, preparation, ops, travel, raw-text, uncategorized, other. Use `·` for zero cells.
5. Compute **content type × month pivot** (last 12 months) — same columns, monthly granularity for recent trends
6. Compute monthly activity bar chart (last 12 months)
7. Compute quarterly trend table with deltas
8. Compute distributions:
   - **By skill type** — table with count and percentage
   - **By top-level directory** — top 15 areas with count (private contacts aggregated as single anonymous row)
   - **By file extension** — count per extension
   - **By day of week** — weekday vs weekend pattern with bar chart
9. Compute **top 5 busiest dates** — date, day of week, count
10. Write to `_analytics/YYMMDD-vault-overview.md`

**Output format:**

```markdown
# Vault Analytics — Overview
Generated: YYYY-MM-DD

---

## Summary

| Metric | Value |
|--------|-------|
| Total files | N |
| Date range | YYYY-MM-DD → YYYY-MM-DD |
| Active months | N |
| Avg files/month | N.N |
| Unique dates | N |
| Current pace | N.N files/day (QN YYYY) |
| Active days (current quarter) | N/N |
| Files per active day | N.N |
| Trend | ↑ N% vs previous quarter |

---

## Yearly Growth

| Year | Files | Growth |
|------|------:|-------:|
| YYYY | N | — |
| YYYY | N | N.Nx |

---

## Content Type × Quarter

| Quarter | transcript | ops/meeting | preparation | ops | travel | raw-text | uncategorized | other | **Total** |
|---------|------:|------:|------:|------:|------:|------:|------:|------:|------:|
| YYYY-QN | N| N| ·| N| ·| N| N| ·| **N** |
| YYYY-QN * | N| N| N| ·| N| ·| N| N| **N** |

\* partial quarter

---

## Content Type × Month (Last 12)

| Month | transcript | ops/meeting | preparation | ops | travel | raw-text | uncategorized | other | **Total** |
|-------|------:|------:|------:|------:|------:|------:|------:|------:|------:|
| YYYY-MM | N| N| ·| N| ·| N| N| ·| **N** |

---

## Monthly Activity (Last 12 Months)

| Month | Files | |
|-------|------:|---|
| YYYY-MM | N | ████████████ |

---

## Quarterly Trend

| Quarter | Files | Delta |
|---------|------:|------:|
| YYYY-QN | N | — |
| YYYY-QN | N | +N |
| YYYY-QN (partial) | N | -N |

---

## Content Distribution

### By Skill Type

| Type | Files | % |
|------|------:|----:|
| ops/meeting | N | N% |
| transcript | N | N% |
| preparation | N | N% |
| ... | | |

### By Directory (Top 15)

| Directory | Files |
|-----------|------:|
| org/meetings | N |
| *(private contacts, N folders)* | *N* |

### By File Extension

| Extension | Files |
|-----------|------:|
| .md | N |
| .txt | N |

### By Day of Week

| Day | Files | |
|-----|------:|---|
| Monday | N | █████████████ |

---

## Busiest Dates

| Date | Day | Files |
|------|-----|------:|
| YYYY-MM-DD | Thu | N |
```

---

### `skills` -- Skill adoption analysis

**Trigger:** `/analytics skills`

**Steps:**

1. Run file discovery
2. Build **skill share pivot (absolute)** — same columns as the overview pivot (transcript, ops/meeting, preparation, ops, travel, raw-text, uncategorized, other), one row per quarter. Use `·` for zero cells.
3. Build **skill share pivot (percentage)** — same layout but percentages per quarter.
4. For each skill type, compute per-skill summary:
   - **First appeared** — which quarter the skill type first produced files
   - **Total files** across all time
   - **Current share** — percentage in the most recent full quarter, with ↑/↓/→ arrow vs previous quarter
   - **Peak quarter** — quarter with most files from this skill
5. Compute **structured vs unstructured ratio** by quarter. Structured = transcript + ops/meeting + preparation + ops. Unstructured = everything else. Show absolute counts, and a trend line from first to last full quarter.
6. Write to `_analytics/YYMMDD-skill-adoption.md`

**Output format:**

```markdown
# Vault Analytics — Skill Adoption
Generated: YYYY-MM-DD

---

## Skill Share Over Time (absolute)

| Quarter | transcript | ops/meeting | preparation | ops | travel | raw-text | uncategorized | other | Total |
|---------|------:|------:|------:|------:|------:|------:|------:|------:|------:|
| YYYY-QN | N| N| ·| N| ·| N| N| ·| N |
| YYYY-QN * | N| N| N| ·| N| ·| N| N| N |

## Skill Share Over Time (%)

| Quarter | transcript | ops/meeting | preparation | ops | travel | raw-text | uncategorized | other |
|---------|------:|------:|------:|------:|------:|------:|------:|------:|
| YYYY-QN | N%| N%| ·| N%| ·| N%| N%| · |

---

## Per-Skill Trends

### transcript
- First appeared: YYYY-QN
- Total files: N
- Current share: N% (↑ vs previous quarter N%)
- Peak quarter: YYYY-QN (N files)

### ops/meeting
[Same structure for each skill with >0 files]

---

## Structured vs Unstructured

| Quarter | Structured | Unstructured | Structured % |
|---------|----------:|-------------:|-------------:|
| YYYY-QN | N | N | N% |

Trend: Structured content share grew from **N%** (YYYY-QN) to **N%** (YYYY-QN).
```

---

### `contacts` -- Contact engagement analysis

**Trigger:** `/analytics contacts`

**Steps:**

1. Run file discovery, filtered to `_contacts/` paths
2. Apply privacy filter — resolve `classification` per contact (see Privacy Filtering section). Exclude `family` and `personal` contacts from named output. Report count and total files of excluded contacts as an anonymous summary line.
3. For each remaining (professional) contact, compute:
   - Total file count
   - First and last file dates (as YYYY-MM)
   - Active months count
   - Peak month (month with most files, with count)
   - Average files per active month
   - Quarterly activity map (for timeline visualisation)
4. Compute contact lifecycle metrics:
   - **New contacts by year** — when contacts first appeared, with cumulative total
   - **Active contacts per quarter** — contacts with at least 1 file in the quarter
5. Sort contacts by total file count descending
6. Generate **activity timelines** — a monospace block showing quarterly engagement density for top 20 contacts using heat notation: `·` = 0, `░` = 1-2, `▒` = 3-5, `▓` = 6-10, `█` = 11+
7. Write to `_analytics/YYMMDD-contact-engagement.md`

**Output format:**

```markdown
# Vault Analytics — Contact Engagement
Generated: YYYY-MM-DD

*N private contacts excluded (N files in aggregate totals only)*

---

## Top Contacts (by file count)

| Contact | Files | Span | Active mo | Peak month | Avg/mo |
|---------|------:|------|----------:|-----------|-------:|
| name | N | YYYY-MM → YYYY-MM | N | YYYY-MM (N) | N.N |

---

## Activity Timelines

```
Contact                              Q4   Q1   Q2   Q3   Q4   Q1   Q2
contact-name (N)                     ·    ░    ▒    ▓    █    ▒    ·

Legend: · = 0  ░ = 1-2  ▒ = 3-5  ▓ = 6-10  █ = 11+
```

---

## Network Growth

| Year | New contacts | Cumulative |
|------|------------:|----------:|
| YYYY | N | N |

## Active Contacts Per Quarter

| Quarter | Active contacts |
|---------|----------------:|
| YYYY-QN | N |
```

---

### `pipeline` -- Input → meeting docs → outcomes over time

**Trigger:** `/analytics pipeline`

The document counts alone are not the full picture — a meeting's *outcomes* live in structured files the other subcommands never touch. This subcommand traces the whole chain: what came in, what was documented, and what it produced.

**Data sources (structured fields only — never prose):**

| Layer | Source | Field scanned |
|-------|--------|---------------|
| Insights | `_insights.yaml` (all folders) | `date:` + preceding `type:` per entry |
| Tasks created | `_tasks.yaml` (v2, all folders) | `created:` per task |
| CHANGELOG entries | `CHANGELOG.md` (all folders) | `- **YYMMDD:` bullet dates |
| Outbox packages | `_outbox/**` file discovery | filename YYMMDD prefix |
| New contacts | `_contacts/<name>/` | earliest YYMMDD file per folder |

**Steps:**

1. Run file discovery (same scan as overview)
2. Scan the structured sources above
3. Build the **grouped chain table — quarters as columns** (metrics as row groups, so the whole chain aligns vertically). Collapse quarters before the first meaningful year into a single `≤YYYY` column to keep width manageable. Row groups:
   - **INPUT:** transcripts, raw text (.txt)
   - **MEETING DOCS:** summaries/notes, agenda/facilitator, preparations
   - **OUTCOMES:** insights total + one row per insight type (largest types first, small ones aggregated as "other"), tasks created, CHANGELOG entries, outbox packages, new contact folders
4. Compute **derived ratios** for quarters where the systems are fully active: insights per meeting+transcript, tasks per meeting+transcript, CHANGELOG entries per meeting+transcript
5. Compute **per-day averages by quarter:** active days / calendar days, files/day, meetings+transcripts/day, insights/day, tasks/day, files per active day (partial quarters use elapsed days)
6. Write to `_analytics/YYMMDD-pipeline-report.md`

**Report structure — two parts, mandatory:**

- **Part 1 — Overview:** headline totals table, a numbered list of *interpreted* findings (adoption inflections, ratio shifts, what converged or diverged — written as conclusions, not table prose), and the **measurement notes**.
- **Part 2 — Deep dive:** the grouped chain table, derived ratios, per-day averages, and any monthly detail.

**Measurement notes (mandatory in every pipeline report):**

- Outcome systems have adoption dates: a `·` before a system existed means "not yet measured", not "nothing happened". State each source's start-of-record explicitly (e.g. insights backfilled with extraction dates, tasks v2 introduction).
- CHANGELOG entries carry the original meeting date and are therefore the best longitudinal outcome proxy.
- Action items inside summary tables are NOT counted (would require prose reads); the task count is the nearest proxy.
- Mark partial quarters/months and use elapsed days for their per-day rates.

**Output format (Part 2 core table):**

```markdown
| Group / metric | ≤YYYY | YY-Q1 | YY-Q2 | ... | **Total** |
|---|---:|---:|---:|---:|---:|
| **INPUT** | | | | | |
| &nbsp;&nbsp;Transcripts | N | N | N | ... | **N** |
| &nbsp;&nbsp;Raw text (.txt) | N | N | N | ... | **N** |
| **MEETING DOCS** | | | | | |
| &nbsp;&nbsp;Summaries / notes | N | N | N | ... | **N** |
| &nbsp;&nbsp;Agenda/facilitator | · | N | N | ... | **N** |
| &nbsp;&nbsp;Preparations | · | N | N | ... | **N** |
| **OUTCOMES** | | | | | |
| &nbsp;&nbsp;Insights (total) | · | · | N | ... | **N** |
| &nbsp;&nbsp;&nbsp;&nbsp;— learning | · | · | N | ... | **N** |
| &nbsp;&nbsp;&nbsp;&nbsp;— pattern | · | · | N | ... | **N** |
| &nbsp;&nbsp;Tasks created | · | · | N | ... | **N** |
| &nbsp;&nbsp;CHANGELOG entries | N | N | N | ... | **N** |
| &nbsp;&nbsp;Outbox packages | · | · | N | ... | **N** |
| &nbsp;&nbsp;New contact folders | N | N | N | ... | **N** |
```

Per-day averages table:

```markdown
| Metric | YY-Q1 | YY-Q2 | ... |
|---|---:|---:|---:|
| Active days (≥1 file) | N/N | N/N | ... |
| Files/day | N.N | N.N | ... |
| Meetings+transcripts/day | N.N | N.N | ... |
| Insights/day | · | N.N | ... |
| Tasks/day | · | N.N | ... |
| Files per active day | N.N | N.N | ... |
```

---

### `backlog` -- Unprocessed content detection

**Trigger:** `/analytics backlog`

Identifies content that may benefit from processing through existing skills.

**Steps:**

1. Run file discovery
2. **Detect unprocessed transcriptions:**
   - Find `.txt` files with YYMMDD prefix (classified as `raw-text`)
   - These are likely raw transcriptions that haven't been processed through `/transcript`
   - Group by directory, sorted by count descending, show count and date range
3. **Detect orphaned content:**
   - Find directories containing YYMMDD-prefixed files but no `CHANGELOG.md`
   - Only include directories with 2+ files (single files are likely intentional one-offs)
   - Show top 15 by file count, with `*(+ N more)*` if truncated
4. **Detect stale inbox items:**
   - Read `_inbox/_inbox.yaml` if it exists
   - Count items with `status: pending`
   - Report age of oldest pending item
5. **Detect insight gaps:**
   - Find folders with `CHANGELOG.md` but no `_insights.yaml`
   - Count YYMMDD-prefixed files in each (potential insight yield)
   - Only include folders with 1+ transcript files
   - Show top 15 by transcript count, with `*(+ N more)*` if truncated
6. Write summary table at top with all four categories and suggested actions
7. Write to `_analytics/YYMMDD-backlog-report.md`

**Output format:**

```markdown
# Vault Analytics — Backlog Report
Generated: YYYY-MM-DD

---

## Summary

| Category | Items | Potential action |
|----------|------:|-----------------|
| Raw text files (.txt) | N | `/transcript` or `/inbox` |
| Folders without CHANGELOG | N dirs, N files | Manual triage |
| Pending inbox items | N | `/inbox` process |
| Folders missing _insights.yaml | N dirs, ~N transcripts | `/insights reprocess` |

---

## Raw Text Files (Likely Unprocessed Transcriptions)

| Directory | Count | Date range |
|-----------|------:|-----------|
| _contacts/name | N | YYMMDD → YYMMDD |
| _projects/name | N | YYMMDD → YYMMDD |

---

## Folders Without CHANGELOG

| Folder | YYMMDD files |
|--------|-------------:|
| org/meetings/area | N |
| _contacts/name/subfolder | N |
| *(+ N more)* | |

---

## Pending Inbox Items

N items pending. Oldest: YYYY-MM-DD
(or: No pending items.)

---

## Insight Reprocessing Opportunities

| Folder | Transcripts | Has _insights.yaml |
|--------|------------:|-------------------:|
| _contacts/name | N | No |
| org/_projects/name | N | No |
| *(+ N more)* | | |
```

---

### `help` -- Usage guide

**Trigger:** `/analytics help`

**Output:**

```
/analytics -- Vault Content Analytics
======================================

Analyse the vault as a dataset -- file metadata, not contents.

Usage:
  /analytics                      Vault overview (default)
  /analytics overview             Same as above
  /analytics skills               Skill adoption over time
  /analytics contacts             Contact engagement timelines
  /analytics pipeline             Input -> meeting docs -> outcomes chain
  /analytics backlog              Unprocessed content detection
  /analytics help                 This guide

Output: _analytics/ folder in vault root (one snapshot per run).

Data flow:
  YYMMDD-*.* files  ──>  /analytics  ──>  _analytics/YYMMDD-*.md
  (read filenames,        (classify,       (markdown snapshots,
   paths, dates)           aggregate)       one per subcommand)

Related skills:
  /insights          Extract knowledge FROM file contents
  /insights status   Count _insights.yaml coverage
  /daily-dashboard   Daily view (today's meetings + tasks)
  /analytics         Longitudinal view (trends over time)
```

---

## Language

Output language follows the same resolution as other standalone skills:

1. If vault root `CLAUDE.md` specifies a language policy, follow it
2. Default: Swedish for section headers and labels, English for technical terms
3. Swedish text MUST use correct å, ä, ö characters

---

## Notes

- The `_analytics/` folder is created automatically on first run
- Old snapshots are archived to `_analytics/.archive/` — never deleted
- This skill reads `_insights.yaml`/`_tasks.yaml`/`CHANGELOG.md` at **field level only** (dates and type enums for the pipeline subcommand) — entry contents (summaries, rationale, notes) remain the visualisation app's domain
- This skill does NOT read file prose (except optional H1 heading for display)
- Contact privacy is respected via `_meta.yaml` `private: true`
- The skill classification algorithm uses **path first, keywords second** — this avoids the ~17% miscount that pure keyword matching produces (e.g., acme/meetings/ files with descriptive names)
- Quarterly comparisons handle partial quarters gracefully — the current quarter is annualised for trend comparison
