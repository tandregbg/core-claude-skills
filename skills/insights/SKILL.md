---
name: insights
description: Knowledge extraction manager and skill evolution engine. Backfills _insights.yaml from historical corpus, compiles execution feedback into patterns, and proposes SKILL.md improvements.
user-invocable: true
argument-hint: [reprocess|scan-claude-md|compile|propose|status|help]
---

# Insights Skill -- Knowledge Extraction & Skill Evolution

Extract and backfill durable insights from existing transcripts and CLAUDE.md files into `_insights.yaml`. Compile execution feedback (edge cases, corrections) into patterns and propose SKILL.md improvements.

This skill complements the forward-looking extraction in `/transcript` Step 3.5 and `/ops` Step 5.5 by processing the historical corpus and closing the feedback loop.

## Design Principles

- **No duplication of extraction logic.** The authoritative definition of insight types, thresholds, and `_insights.yaml` format lives in `/transcript` Step 3.5. This skill references it and includes a quick-reference copy for convenience.
- **Dedup by `source.file`.** Processing the same file twice never creates duplicate entries.
- **Additive only.** Never removes or modifies existing insights (except `scan-claude-md` which replaces stale CLAUDE.md-sourced entries).
- **Silent accumulation.** Like `/transcript` and `/ops`, insights never surface in other skill output -- only the `core-skills-visualisation` app reads `_insights.yaml`.

---

## String Resolution

Template strings marked as `{strings.section.key}` are resolved at runtime.

**Resolution order:**

1. Org config `strings` section (if loaded)
2. Language-matched defaults from `base.yaml`:
   - `swedish` -> `strings_sv`
   - `english` -> `strings`
   - `input` -> match detected transcript language
3. Hardcoded strings already in template (fallback)

---

## Configuration

Reads `workflows.knowledge_extraction` from `base.yaml` (or org config override):

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `true` | Master switch for extraction |
| `min_insights` | `1` | Minimum qualifying insights to write file |
| `types` | `[decision, preference, learning, opportunity, pattern]` | Insight types to extract |
| `max_per_meeting` | `10` | Cap per source file |

If `enabled: false`, all subcommands exit immediately with a message.

---

## Subcommands

### `reprocess [target]` -- Extract insights from existing transcripts

**Trigger:** `/insights reprocess <target>`

**Targets (all three supported):**
- **Folder path:** `/insights reprocess _contacts/bob-smith` or `/insights reprocess _projects/acme/meetings/management`
- **`all`:** `/insights reprocess all` -- all folders containing a CHANGELOG.md
- **`since YYMMDD`:** `/insights reprocess since 260201` -- only files dated after the given date, across all folders with CHANGELOG.md

**Steps:**

1. **Resolve target folders:**
   - If folder path: resolve to that single folder (must contain CHANGELOG.md)
   - If `all`: scan vault recursively for all folders containing CHANGELOG.md (max depth 6, skip `.archive/`, `clones/`)
   - If `since YYMMDD`: same as `all`, but with date filter applied in step 4

2. **For each target folder, list `YYMMDD-*.md` files** (transcript files matching the 6-digit date prefix pattern)

3. **Build dedup set:** If `_insights.yaml` exists, load it and collect all `source.file` values into a set

4. **Filter files:**
   - Skip files already in the dedup set (already processed)
   - Skip standup files: filename contains `standup` or `daily-standup`, OR file is <500 words with no qualifying insights
   - If `since YYMMDD` target: additionally skip files whose filename date prefix is before the given date

5. **Sort remaining files chronologically** (oldest first, for consistent ID ordering)

6. **Process each file:**
   - Read the file content
   - Apply the same extraction logic as `/transcript` Step 3.5:
     - Scan for decisions with rationale, stated preferences, learnings, opportunities, and patterns
     - Apply threshold: only non-obvious, durable, specific insights
     - Respect `max_per_meeting` cap
     - Respect configured `types` list
   - For each qualifying insight, create an entry with:
     - `id`: next available ID (from `next_id` in existing file, or starting at 1)
     - `type`: one of the configured types
     - `date`: extracted from the filename prefix (YYMMDD)
     - `summary`: one sentence
     - `rationale`: one sentence context
     - `source.file`: the transcript filename
     - `source.section`: the section heading where the insight was found
     - `tags`: max 5 keywords
     - `status`: `active`
     - `superseded_by`: `null`

7. **Write/append to `_insights.yaml`** in the same folder as the CHANGELOG.md:
   - If file exists: append new entries, update `next_id` and `last_updated`
   - If file does not exist: create with `version: 1`, `context` set from folder name or CHANGELOG context

**Progress output:**

```
Processing =bob-smith (8 files, 6 new)... Extracted 4 insights
Processing acme/meetings/management (52 files, 52 new)... Extracted 28 insights
...
Reprocessing complete.
Processed 186 files across 14 folders.
Extracted 89 insights (89 new, 0 already existed).
```

**Skip conditions:**
- Folder has no CHANGELOG.md
- All files already processed (dedup)
- File is a pure standup (<500 words, no qualifying insights)

---

### `scan-claude-md` -- Extract knowledge from CLAUDE.md files

**Trigger:** `/insights scan-claude-md`

**Steps:**

1. **Scan vault subfolders for CLAUDE.md files** (max depth 4, skip `.archive/`, `clones/`)

2. **For each CLAUDE.md, find nearest parent folder with CHANGELOG.md** as target for `_insights.yaml`. If no CHANGELOG.md exists in any parent (up to vault root), skip this CLAUDE.md with a note.

3. **Check freshness:**
   - If `_insights.yaml` already has entries with `source.file: "CLAUDE.md"` AND the CLAUDE.md file has not been modified since `last_updated` in the insights file, skip (already current)
   - If CLAUDE.md is newer: remove all existing `source.file: "CLAUDE.md"` entries from `_insights.yaml` (preserving transcript-sourced insights), then re-extract

4. **Extract insights using type mapping:**

   | Signal in CLAUDE.md | Insight type |
   |---------------------|-------------|
   | "Chose X over Y", "Using X because", "Beslut:", "Decision:" | `decision` |
   | "NEVER", "MUST", "Always", "Alltid", "Aldrig" | `preference` |
   | "Avoid", "Don't", "Undvik", "Learned:", "Lärdom:" | `learning` |
   | Rules, conventions, naming patterns, routing tables, format specifications | `pattern` |

   Note: `opportunity` type is not mapped for CLAUDE.md -- these files contain established decisions and conventions, not future opportunities. Opportunities are only extracted from transcripts via `reprocess`.

5. **Set source metadata:**
   - `source.file`: `"CLAUDE.md"`
   - `source.section`: the `##` heading under which the insight was found

6. **Skip sections that contain only:**
   - Bare directory listings (pure file trees without commentary)
   - Pure glossaries (term: definition lists without rationale)
   - Metadata-only content (version numbers, dates, links without context)

7. **Write to `_insights.yaml`** following the same format. Assign IDs continuing from `next_id`.

**Output:**

```
Scanning CLAUDE.md files...
  acme/CLAUDE.md -> acme/ (12 insights, replaced 8 stale)
  _contacts/bob-smith/CLAUDE.md -> _contacts/bob-smith/ (3 insights, new)
  bravo/CLAUDE.md -> skipped (no CHANGELOG.md in parent)
...
Scan complete.
Processed 14 CLAUDE.md files.
Extracted 42 insights (34 new, 8 replaced).
Skipped 3 files (no CHANGELOG.md parent).
```

---

### `status` -- Show current insights state

**Trigger:** `/insights status`

**Steps:**

1. Scan vault for all `_insights.yaml` files
2. Scan vault for all folders with CHANGELOG.md (potential insight targets)

**Output:**

```
Insights Status
===============

_insights.yaml files: 14
Total insights: 186

By type:
  decision:    52
  preference:  38
  learning:    41
  opportunity: 28
  pattern:     27

By status:
  active:      172
  superseded:  11
  archived:    3

Top folders:
  acme/meetings/management    42 insights
  _contacts/bob-smith                  18 insights
  _contacts/david-ekberg          15 insights
  ...

Reprocessing opportunities:
  12 folders have CHANGELOG.md but no _insights.yaml
  3 folders have _insights.yaml older than newest transcript
  Total: ~340 unprocessed transcript files

Skill Evolution
───────────────
  Execution feedback: 23 entries (18 edge_case, 5 correction)
  Compiled patterns: 3 skill_pattern entries
  Pending proposals: 2 in docs/proposals/
  Applied proposals: 1 in docs/proposals/.applied/
  Config: auto_apply=false, compile_threshold=3, propose_threshold=5
```

---

### `compile` -- Compile execution feedback into patterns

**Trigger:** `/insights compile` or `/insights compile since YYMMDD`

Reads all execution feedback entries (`edge_case`, `correction`) across `_insights.yaml` files and compiles recurring patterns into articles.

**Steps:**

1. **Scan all `_insights.yaml` files** in the vault for entries where `source.skill` is set (execution feedback)
2. **Filter by date** if `since YYMMDD` is specified
3. **Group by similarity** -- cluster entries by tags, summary keywords, and `source.skill` + `source.step`
4. **Apply compile threshold** -- only groups with `compile_threshold` (default: 3) or more entries become patterns. Read threshold from `workflows.knowledge_extraction.evolution.compile_threshold` in config.
5. **For each qualifying group, create a `skill_pattern` entry** in the most relevant `_insights.yaml`:
   ```yaml
   - id: [next_id]
     type: skill_pattern
     date: YYMMDD          # today
     summary: "Pattern description synthesized from N occurrences"
     detail: "Dates, contexts, and common resolution across occurrences"
     source:
       skill: insights/compile
       entries: [list of source entry IDs and their _insights.yaml locations]
     tags: [synthesized, from, source, entries]
     status: active
   ```
6. **Dedup** -- if a `skill_pattern` entry already covers the same cluster (by matching `source.entries`), update it instead of creating a duplicate

**Output:**

```
Compiling execution feedback...

Scanned 14 _insights.yaml files, found 23 execution feedback entries.

Compiled 3 patterns:
  - [skill_pattern] Name disambiguation needed in 7/23 transcript runs (transcript Step 1.5)
  - [skill_pattern] Short calls (<15 min) rarely produce importable tasks (transcript Step 4)
  - [skill_pattern] Meeting routing ambiguous when no org config loaded (ops Step 2)

Skipped 8 entries below compile threshold (3).
```

---

### `propose` -- Generate SKILL.md improvement proposals

**Trigger:** `/insights propose`

Reads compiled `skill_pattern` entries and generates concrete SKILL.md improvement proposals.

**Steps:**

1. **Scan all `_insights.yaml` files** for `skill_pattern` entries
2. **Apply propose threshold** -- only patterns with `propose_threshold` (default: 5) or more underlying occurrences generate proposals. Read threshold from `workflows.knowledge_extraction.evolution.propose_threshold` in config.
3. **For each qualifying pattern:**
   a. Read the target SKILL.md file (determined by `source.skill`)
   b. Identify the relevant step or section
   c. Generate a concrete proposed change as a markdown file

4. **Save proposals** to `docs/proposals/` in the core-skills repo:
   ```markdown
   # Proposal: [Short title]

   **Based on:** [N] occurrences of [pattern summary]
   **Target:** skills/[skill]/SKILL.md
   **Pattern entry:** [reference to skill_pattern in _insights.yaml]

   ## Proposed change

   **In section:** [Step or section name]
   **Action:** [Add/Modify/Remove]

   > [Exact text to add or replace, written in the same style as the target SKILL.md]

   ## Rationale

   [Why this change addresses the pattern, with references to specific occurrences]
   ```

5. **Check auto_apply setting** from `workflows.knowledge_extraction.evolution.auto_apply`:
   - If `false` (default): save proposal file, report to user
   - If `true`: apply the change to SKILL.md directly, log in CHANGELOG with `[AUTO-EVOLUTION]` tag, save proposal as record

**Output (auto_apply: false):**

```
Generated 2 proposals:

1. docs/proposals/260404-transcript-name-disambiguation.md
   Target: skills/transcript/SKILL.md (Step 1)
   Based on: 7 edge_case entries across 4 contacts

2. docs/proposals/260410-ops-short-call-threshold.md
   Target: skills/transcript/SKILL.md (Step 4)
   Based on: 5 skill_pattern entries

Review proposals and run /insights propose apply to accept.
```

**Output (auto_apply: true):**

```
Auto-applied 2 proposals:

1. skills/transcript/SKILL.md -- added name disambiguation pre-check (Step 1)
   [AUTO-EVOLUTION] Based on 7 edge_case entries

2. skills/transcript/SKILL.md -- added short-call skip for task import (Step 4)
   [AUTO-EVOLUTION] Based on 5 skill_pattern entries

Changes logged in CHANGELOG.md. Review with: git diff HEAD~1
```

---

### `propose apply` -- Apply a proposal

**Trigger:** `/insights propose apply [proposal-file]` or `/insights propose apply all`

**Steps:**

1. **If specific file:** Read the proposal, apply the change to the target SKILL.md
2. **If `all`:** Apply all proposals in `docs/proposals/` that haven't been applied yet
3. **For each applied proposal:**
   a. Edit the target SKILL.md with the proposed change
   b. Add a CHANGELOG entry with `[EVOLUTION]` tag
   c. Move the proposal file to `docs/proposals/.applied/` with a date prefix
   d. Mark the source `skill_pattern` entry as `status: archived` in `_insights.yaml`

**Output:**

```
Applied: docs/proposals/260404-transcript-name-disambiguation.md
  -> skills/transcript/SKILL.md updated (Step 1: added pre-check)
  -> CHANGELOG.md updated
  -> Proposal archived to docs/proposals/.applied/

1 proposal applied. Review changes with: git diff
```

---

### `help` -- Usage guide

**Trigger:** `/insights help`

**Output:**

```
/insights -- Knowledge Extraction & Skill Evolution
=====================================================

Backfill _insights.yaml, compile execution feedback, and evolve skills.

Usage:
  /insights reprocess =bob-smith          Extract from one folder
  /insights reprocess all                Extract from all folders with CHANGELOG.md
  /insights reprocess since 260201       Extract from files dated after 260201
  /insights scan-claude-md               Extract from CLAUDE.md files
  /insights compile                      Compile execution feedback into patterns
  /insights compile since 260301         Compile only recent feedback
  /insights propose                      Generate SKILL.md improvement proposals
  /insights propose apply [file|all]     Apply a proposal to SKILL.md
  /insights status                       Show insights + evolution statistics
  /insights help                         This guide

Knowledge extraction (content):
  /transcript Step 3.5    Extracts insights from NEW transcripts (forward)
  /ops Step 5.5           Extracts insights from NEW meeting docs (forward)
  /insights reprocess     Extracts insights from EXISTING transcripts (backfill)
  /insights scan-claude-md  Extracts from CLAUDE.md files

Skill evolution (execution feedback):
  /ops Step 9             Captures edge cases and corrections (silent)
  /transcript Step 4.5    Captures edge cases and corrections (silent)
  /insights compile       Finds patterns in execution feedback
  /insights propose       Generates SKILL.md improvements from patterns

Data flow:
  /transcript or /ops ─┐
                       ├── _insights.yaml ──> visualisation app
  /insights ───────────┘       │
                               ├── execution feedback (edge_case, correction)
                               │        │
                               │   /insights compile -> skill_pattern entries
                               │        │
                               │   /insights propose -> SKILL.md improvements
                               │        │
                               └── skills get smarter over time

Config: workflows.knowledge_extraction.evolution in base.yaml
  auto_apply: false (default) -- proposals require manual review
  auto_apply: true -- proposals applied automatically
```

---

## Extraction Reference (Quick Copy)

This is a convenience copy. The authoritative definition is in `/transcript` Step 3.5 (`~/.claude/skills/transcript/SKILL.md`).

| Type | Captures | Written by |
|------|----------|------------|
| `decision` | Choice + rationale | `/transcript`, `/ops`, `/insights reprocess` |
| `preference` | Working style | `/transcript`, `/ops`, `/insights reprocess` |
| `learning` | What worked/didn't | `/transcript`, `/ops`, `/insights reprocess` |
| `opportunity` | Ideas not yet actioned | `/transcript`, `/ops`, `/insights reprocess` |
| `pattern` | Recurring themes | `/transcript`, `/ops`, `/insights reprocess` |
| `edge_case` | Skill hit ambiguous input | `/transcript` Step 4.5, `/ops` Step 9 |
| `correction` | User corrected skill output | `/transcript` Step 4.5, `/ops` Step 9 |
| `skill_pattern` | Compiled execution pattern | `/insights compile` |

**Threshold:** Only non-obvious, durable, specific insights. If fewer than `min_insights` (default: 1) qualify, skip the file silently.

**Format:** See `/transcript` Step 3.5 for the complete `_insights.yaml` schema.

---

## Privacy and language rules for _insights.yaml

### Privacy

NEVER include personal names or company names in `summary`, `rationale`, or `tags` fields. The `context` field and `source.file` already provide the connection to who/what. Write insights as generic, reusable knowledge that reads well in the visualisation dashboard without exposing individuals or organizations.

#### Contact Classification (CR-009)

Insights are extracted from all contacts regardless of their `classification` (family, personal, professional, confidential) — knowledge is valuable in all contexts. The `core-skills-visualisation` app is responsible for respecting classification when rendering. The privacy scrubbing rules above (no names in summary/rationale/tags) apply equally to all classification levels.

Bad example:
```yaml
summary: "Alice switched from hourly billing to t-shirt-sized estimates at Acme Corp"
tags: [Acme, BobCo, some-tool-name]
```

Good example:
```yaml
summary: "Switched from hourly billing to t-shirt-sized estimates to handle AI-driven efficiency gains"
tags: [pricing, billing, t-shirt-sizing, business-model]
```

### Swedish Character Enforcement (CR-007: pre-write validator)

When processing Swedish-language content, ALL Swedish words MUST use correct å, ä, ö characters. Never substitute with a or o. This applies equally to `_insights.yaml` YAML fields as to markdown files -- YAML content is just as prone to missing characters.

**Pre-write validator (CR-007, mandatory):**

Before writing **any** entry to `_insights.yaml` where the `summary`, `rationale`, or `context` field is in Swedish (detected by presence of any å/ä/ö character anywhere in the file, OR by folder language per `language_inheritance` in base.yaml):

1. Load `~/.claude/skills/ops-config/swedish_substitutions.yaml`
2. Scan each Swedish text field token-by-token using word-boundary matching
3. For each match against the substitution map (excluding `category: skip`):
   - **Non-ambiguous** matches: refuse to write, report the violation, ask the user to confirm or fix
   - **Ambiguous** matches: warn but proceed (log to execution feedback as `edge_case`)
4. If no violations, proceed with the write

This is the structural validation that the MEMORY.md reminder cannot provide -- the model may write a tempting `"...byggs fran Meta..."` line, but the validator catches it before the file lands on disk.

**To remediate existing files** written before this validator was added, run `/ops normalize <path>`.

Common mistakes to avoid (full list in `swedish_substitutions.yaml`):
- "pagaende" -> "pågående", "foretag" -> "företag", "fran" -> "från"
- "fore" -> "före", "nasta" -> "nästa", "behovs" -> "behövs", "kravs" -> "krävs"
- "anvandning" -> "användning", "mote" -> "möte", "losning" -> "lösning"
- "manader" -> "månader", "forberedelse" -> "förberedelse", "karnteam" -> "kärnteam"
- "prissattning" -> "prissättning", "overgang" -> "övergång", "forandring" -> "förändring"
