---
name: analytics
description: Vault-level content analytics — file creation trends, skill adoption, contact engagement, content distribution, and unprocessed backlog detection. Outputs to _analytics/ folder.
user-invocable: true
argument-hint: [overview|skills|contacts|backlog|help]
---

# /analytics -- Vault Content Analytics

Analyse the vault as a dataset — file metadata (names, dates, paths, counts), not file contents. Answers "how is my system performing?" rather than "what did I learn from this conversation?"

**Standalone skill** — no dependency on ops-base or ops-config.

**Key distinction from `/insights`:** The insights skill extracts *knowledge from conversations* (decisions, learnings, patterns about people and projects). This skill analyses *the vault itself* — creation velocity, skill adoption, engagement frequency, content distribution.

---

## Design Principles

- **Metadata only.** Read filenames, paths, dates, and file sizes. Never read file contents except for lightweight classification (H1 heading, first line).
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

Scan vault recursively (max depth 8, skip `.archive/`, `.git/`, `node_modules/`, `clones/`). Match files where the basename starts with 6 digits followed by a separator:

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
| `förberedelse`, `preparation`, `prep-` | `preparation` |
| `meeting`, `möte`, `standup`, `board`, `alignment`, `kickoff`, `weekly`, `sprint`, `retro`, `sync` | `ops/meeting` |

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
2. Compute metrics:
   - Total YYMMDD files
   - Date range (earliest → latest)
   - Unique active dates
   - Active months count
3. Compute time series:
   - **Yearly totals** with year-over-year growth multiplier
   - **Quarterly totals** with quarter-over-quarter delta
   - **Monthly totals** (last 12 months only, with bar chart)
4. Compute distributions:
   - **By skill type** — table with count and percentage
   - **By top-level directory** — top 15 areas with count
   - **By file extension** — count per extension
   - **By day of week** — weekday vs weekend pattern
5. Compute highlights:
   - **Top 5 busiest dates** — date, day of week, count
   - **Current pace** — files/day for current quarter
   - **Trend direction** — comparing current quarter rate to previous quarter rate
6. Write to `_analytics/YYMMDD-vault-overview.md`

**Output format:**

```markdown
# Vault Analytics — Overview
Generated: YYYY-MM-DD

## Summary

| Metric | Value |
|--------|-------|
| Total files | N |
| Date range | YYYY-MM-DD → YYYY-MM-DD |
| Active months | N |
| Avg files/month | N.N |
| Unique dates | N |
| Current pace | N.N files/day (QN YYYY) |
| Trend | ↑ N% vs previous quarter |

## Yearly Growth

| Year | Files | Growth |
|------|------:|-------:|
| YYYY | N | — |
| YYYY | N | N.Nx |

## Quarterly Trend

[Table with quarter, count, delta]

## Monthly Activity (Last 12 Months)

[Table with month, count, visual bar]

## Content Distribution

### By Skill Type

| Type | Files | % |
|------|------:|----:|
| transcript | N | N% |
| ops/meeting | N | N% |
| preparation | N | N% |
| ... | | |

### By Directory

[Top 15 directories with count]

### By Day of Week

[Weekday distribution with bar chart]

## Busiest Dates

[Top 5 dates with count and day of week]
```

---

### `skills` -- Skill adoption analysis

**Trigger:** `/analytics skills`

**Steps:**

1. Run file discovery
2. For each skill type, compute:
   - **Quarterly file count** time series
   - **Quarterly share percentage** (what % of that quarter's files came from this skill)
   - **First appearance** — which quarter the skill type first produced files
   - **Growth trajectory** — is the skill's share growing, stable, or shrinking (compare last 2 quarters)
3. Compute **unstructured-to-structured ratio** — what percentage of files are classified vs uncategorized, by quarter
4. Write to `_analytics/YYMMDD-skill-adoption.md`

**Output format:**

```markdown
# Vault Analytics — Skill Adoption
Generated: YYYY-MM-DD

## Skill Share Over Time

| Quarter | transcript | ops/meeting | preparation | other | total |
|---------|-----------|-------------|-------------|-------|-------|
| YYYY-QN | N (N%) | N (N%) | N (N%) | N (N%) | N |

## Per-Skill Trends

### transcript
- First appeared: YYYY-QN
- Total files: N
- Current share: N% (↑/↓/→ vs previous quarter)
- Peak quarter: YYYY-QN (N files)

### ops/meeting
[Same structure]

### preparation
[Same structure]

## Structured vs Unstructured

| Quarter | Structured (%) | Unstructured (%) |
|---------|---------------|------------------|
| YYYY-QN | N% | N% |

Trend: Structured content share is [growing/stable/shrinking] — from N% to N%.

## Unstructured Content Breakdown

[Sub-classification of the "other" bucket: raw-text, travel, marketing, etc.]
```

---

### `contacts` -- Contact engagement analysis

**Trigger:** `/analytics contacts`

**Steps:**

1. Run file discovery, filtered to `_contacts/` paths
2. Apply privacy filter — exclude contacts with `private: true` in `_meta.yaml`
3. For each remaining contact, compute:
   - Total file count
   - First and last file dates
   - Active months count
   - Peak month (month with most files)
   - Average files per active month
   - Quarterly activity timeline (sparse representation)
4. Compute contact lifecycle metrics:
   - **New contacts by year** — when contacts first appeared
   - **Network growth rate** — how many new contacts per quarter
   - **Active contacts per quarter** — contacts with at least 1 file in the quarter
5. Sort contacts by total file count descending
6. Write to `_analytics/YYMMDD-contact-engagement.md`

**Output format:**

```markdown
# Vault Analytics — Contact Engagement
Generated: YYYY-MM-DD

## Top Contacts (by file count)

| Contact | Files | Span | Active months | Peak month | Avg/month |
|---------|------:|------|------:|-----------|----------:|
| name | N | MMM YY → MMM YY | N | MMM YY (N) | N.N |

## Activity Timelines

[Visual quarterly timelines using · ░ ▒ ▓ █ notation]

```
                     [quarter labels across top]
contact-name (N)     [· · · ░ ▒ ▓ █ · ·]
```

Legend: · = 0  ░ = 1-2  ▒ = 3-5  ▓ = 6-10  █ = 11+

## Network Growth

| Year | New contacts | Cumulative |
|------|-------------|-----------|
| YYYY | N | N |

## Active Contacts Per Quarter

| Quarter | Active contacts |
|---------|----------------|
| YYYY-QN | N |

## Contact Lifecycle Patterns

[Group contacts by start year with file counts]
```

---

### `backlog` -- Unprocessed content detection

**Trigger:** `/analytics backlog`

Identifies content that may benefit from processing through existing skills.

**Steps:**

1. Run file discovery
2. **Detect unprocessed transcriptions:**
   - Find `.txt` files with YYMMDD prefix
   - These are likely raw transcriptions that haven't been processed through `/transcript`
   - Group by directory, show count and date range
3. **Detect orphaned content:**
   - Find YYMMDD-prefixed files in directories that have no `CHANGELOG.md`
   - These files exist outside the normal skill pipeline
4. **Detect stale inbox items:**
   - Read `_inbox/_inbox.yaml` if it exists
   - Count items with `status: pending`
   - Report age of oldest pending item
5. **Detect insight gaps:**
   - Find folders with `CHANGELOG.md` but no `_insights.yaml`
   - These folders could benefit from `/insights reprocess`
   - Count transcript files in each (potential insight yield)
6. Write to `_analytics/YYMMDD-backlog-report.md`

**Output format:**

```markdown
# Vault Analytics — Backlog Report
Generated: YYYY-MM-DD

## Summary

| Category | Items | Potential action |
|----------|------:|-----------------|
| Raw text files (.txt) | N | `/transcript` or `/inbox` |
| Folders without CHANGELOG | N dirs, N files | Manual triage |
| Pending inbox items | N | `/inbox` process |
| Folders missing _insights.yaml | N dirs, ~N transcripts | `/insights reprocess` |

## Raw Text Files (Likely Unprocessed Transcriptions)

| Directory | Count | Date range |
|-----------|------:|-----------|
| path/ | N | YYMMDD → YYMMDD |

## Folders Without CHANGELOG

[Directories containing YYMMDD files but no CHANGELOG.md]

## Pending Inbox Items

[List from _inbox.yaml with age]

## Insight Reprocessing Opportunities

| Folder | Transcripts | Has _insights.yaml |
|--------|------------|-------------------|
| path/ | N | No |
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
- This skill does NOT read `_insights.yaml` files — that's the visualisation app's domain
- This skill does NOT read file contents (except optional H1 heading for display)
- Contact privacy is respected via `_meta.yaml` `private: true`
- The skill classification algorithm uses **path first, keywords second** — this avoids the ~17% miscount that pure keyword matching produces (e.g., acme/meetings/ files with descriptive names)
- Quarterly comparisons handle partial quarters gracefully — the current quarter is annualised for trend comparison
