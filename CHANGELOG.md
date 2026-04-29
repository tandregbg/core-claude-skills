# Changelog

All notable changes to core-skills will be documented in this file.

<!-- Release checklist:
1. Update ecosystem.yaml core_skills_version
2. Run scripts/check-ecosystem-alignment.sh
3. Update visualiser if contract fields changed
4. Update landing page if skill list or descriptions changed
-->

## [1.16.0] - 2026-04-29

### Added
- **`vault_conventions` block in `ecosystem.yaml` (CR-010):** Authoritative declaration of every file the suite produces or consumes in a user's vault. Each entry documents path pattern, purpose, schema link (when one exists), writers, readers, and lifecycle. Three sections: `vault_root` (7 entries -- `_inbox/`, `_inbox/.audio/`, `_outbox/`, `_config/`, `_analytics/`, `_tasks.yaml`, `_Dashboard.md`), `per_folder` (6 entries -- `_ops.yaml`, `_tasks.yaml`, `_insights.yaml`, `_meta.yaml`, `_summary.yaml`, `CHANGELOG.md`), and `rules` (5 cross-cutting rules covering vault root resolution, inbox/outbox singularity, config resolution order, naming conventions, audio/transcript pairing). Bumps `contract_version` 1 -> 2; additive change, contract_version=1 clients ignore the new block. Marvin, Trillian (vault-pulse), and future external skills should read this as the contract.
- **Formal `_inbox/` schema at `docs/schemas/inbox.md` (CR-012):** Canonical contract for `_inbox/<id>.md` frontmatter (id, created, classification, status, source, target_skill, target_folder), `_inbox/.audio/<id>.m4a` pairing-by-basename rule, and lifecycle states (`pending` -> `processing` -> `processed` -> archived). Identifier format upgraded to `YYMMDD-HHMMSS[-slug]` for second-level uniqueness across multiple producers (Trillian writes audio, Deep Thought writes transcript later). `_inbox.yaml` is now a derived index, rebuilt from frontmatter; frontmatter wins on disagreement. Schema bump for `_inbox.yaml`: v1 -> v2 (auto-rewritten lazily on first `/inbox` run). Hidden `.audio/` subfolder convention keeps audio out of Obsidian sync by default. Producers: `/inbox`, Trillian, Deep Thought, Marvin web UI. Cross-linked from `vault_conventions` block.

### Changed
- **`/ops` config resolution chain rewritten (CR-011):** Org configs now live in the vault folder they describe (`<vault>/<org>/_ops.yaml`) instead of dedicated skill repos. New chain: (1) project-level `.claude/ops-config.yaml`, (2) folder-local `_ops.yaml` walked up from CWD until vault root, (3) vault-wide `<vault>/_config/base.yaml`, (4) skill `base.yaml`. Vault root is detected by `_inbox/`, `_outbox/`, or `.obsidian/` markers, or `VAULT_ROOT` env override. Updated in `skills/ops/SKILL.md`, `skills/ops-base/SKILL.md`, `skills/ops-config/README.md`. Replaces the pre-v1.16.0 step "Org config skill: `~/.claude/skills/{org}-ops-config/{org}.yaml`".

### Deprecated
- **`*-ops-config` skill-based discovery (CR-011):** `~/.claude/skills/acme-ops-config/`, `bravo-ops-config/`, `delta-ops-config/` are deprecated. They remain as fallback (between vault-wide and skill defaults) with a one-time per-session deprecation warning. Removed entirely in v1.17.0.

### Migration
- **CR-011 -- migrate org configs to vault folders.** One-time per machine:
  1. `cp ~/repos/acme-skills/skills/acme-ops-config/acme.yaml <vault>/acme/_ops.yaml`
  2. `cp ~/repos/bravo-skills/skills/bravo-ops-config/bravo.yaml <vault>/bravo/_ops.yaml`
  3. `cp ~/.claude/skills/delta-ops-config/delta.yaml <vault>/delta/_ops.yaml`
  4. Verify each new file parses: `python3 -c "import yaml; yaml.safe_load(open('<vault>/acme/_ops.yaml'))"`
  5. `cd <vault>/acme && /ops status` -- confirm team, language, terminology match the originals
  6. Repeat step 5 in `<vault>/bravo/` and `<vault>/delta/`
  7. **Do not** delete the old `*-ops-config` skill files yet -- they still work as fallback until v1.17.0
  
  After migration, new orgs (e.g. `dolutions`, `mindtastic`) get a config by dropping a `_ops.yaml` in their vault folder -- no skill repo, no symlink, no SKILL.md.

## [1.15.10] - 2026-04-16

### Fixed
- **`md2pdf` orphaned headings fix:** Headings (h2/h3/h4) no longer appear alone at the bottom of pages. New `wrap_heading_sections()` function wraps each heading + its following content (up to ~3000 chars) in a `<section class="heading-group">` with `break-inside: avoid`. CSS updated with `break-after: avoid`, adjacent sibling rules, and heading-group container styling. Weasyprint's limited support for `page-break-after: avoid` is now worked around at the HTML level.

## [1.15.9] - 2026-04-15

### Added
- **`ecosystem.yaml` shared contract:** Machine-readable single source of truth for type enums, skill metadata, schema versions, and contact classification. Referenced by core-skills-visualisation and landing page to prevent drift. Includes: insight types (content + evolution), contact classification levels, skills registry with badges and subcommands, output artifacts, visualisation feature list.
- **`scripts/check-ecosystem-alignment.sh`:** Version alignment checker that reads ecosystem.yaml and verifies visualiser CLAUDE.md and landing page i18n reference the same core-skills version. Run after version bumps to detect drift.

## [1.15.8] - 2026-04-15

### Added
- **Contact classification taxonomy (CR-009):** New `classification` field in `_meta.yaml` with four levels: `family`, `personal`, `professional` (default), `confidential`. New `private` convenience boolean for backward compatibility with `_tasks.yaml` filtering. Folder naming convention documented (`a1-*`/`a2*` = family). Privacy defaults in `base.yaml` auto-classify contacts by folder name pattern when `_meta.yaml` is absent.
- **`analytics` privacy filtering updated (CR-009):** `/analytics contacts` excludes `family` and `personal` contacts. Classification resolved from: `_meta.yaml` field > `private` field > folder name pattern > `professional` default.
- **`daily-dashboard` contact-level filtering (CR-009):** Generic mode shows all classifications. Org/shared mode excludes `family`, `personal`, and `confidential` contacts. Task-level `private` field continues to work independently.
- **`insights` classification awareness (CR-009):** Insights still extracted from all contacts regardless of classification. Visualisation app responsible for filtering. Privacy scrubbing rules unchanged.
- **`ops-config` schema v1.3 (CR-009):** New `privacy_defaults` config block in `base.yaml`. Contact-meta-schema bumped to v1.1 with `classification` and `private` fields.

## [1.15.7] - 2026-04-15

### Added
- **`analytics` skill:** Vault-level content analytics -- file creation trends, skill adoption, contact engagement, content distribution, and unprocessed backlog detection. Analyses file metadata (names, dates, paths), not file contents. Outputs dated snapshots to `_analytics/` folder in vault root with automatic archiving of older snapshots. Subcommands: `overview` (vault-wide metrics, growth trajectory, distributions), `skills` (per-skill adoption over time, structured vs unstructured ratio), `contacts` (engagement timelines, network growth, lifecycle patterns), `backlog` (unprocessed .txt files, missing _insights.yaml, stale inbox items), `help`. Uses path-first classification to avoid keyword miscount (~17% improvement over pure keyword matching). Privacy-aware via `_meta.yaml` `classification` field. Standalone skill -- no dependency on ops-base or ops-config.

## [1.15.6] - 2026-04-15

### Added
- **`md2pdf --outbox NAME` mode:** One-command outbox packaging. Creates `<vault>/_outbox/YYMMDD-NAME/`, PDFs every input markdown into that folder (or one combined PDF if `--combined` is also given), and generates a `_manifest.md` skeleton (status/kanal/kontakt/projekt + Innehåll table) plus a `YYMMDD-NAME-mejl.txt` email stub with subject + Bilagor listed and body left empty. NAME follows the contact convention (`förnamn-efternamn_organisation`). Vault root is auto-detected by walking up from cwd for `_outbox/` or `_contacts/` markers, with `$OBSIDIAN_VAULT` fallback and `--vault PATH` override. Optional `--subject TEXT` pre-fills the email Ämne line. Warns (non-fatal) if `_contacts/<NAME>/` is missing in the vault. Replaces the manual 4-step process of dated-folder creation, per-file PDF runs, hand-written manifest, and hand-written email stub.

### Added
- **`md2pdf` skill:** Markdown-to-PDF converter using weasyprint. Professional A4 styling with page numbers, tables, typography. Mermaid diagrams rendered as high-res PNG (SVG foreignObject not supported by weasyprint). Supports individual files, combined output, and custom CSS. Dependencies: weasyprint, markdown (Python), mmdc (npm, optional).

## [1.15.4] - 2026-04-07

### Added
- **`ops-config` swedish_chars sub-tree inheritance (CR-007):** New `language_inheritance` config block in `base.yaml`. By default, files written under `_projects/**`, `_contacts/**`, `_private/**`, or `_inbox/**` automatically inherit `swedish_chars: strict` from base regardless of whether the folder has its own CLAUDE.md. Catches sub-trees like `_projects/<client>/` that previously slipped through enforcement and accumulated character drift. Override per folder via CLAUDE.md.
- **`ops-config` swedish_substitutions.yaml:** New data file with the seed substitution list (verbs, prepositions, nouns, adjectives) loaded from MEMORY.md. Single source of truth for both `/ops normalize` and the `/insights` pre-write validator. Each entry has `from`, `to`, `category`, optional `ambiguous` flag for cases like `ar`/`är` and `bor`/`bör` where the ASCII form could be a different word.
- **`ops` `/ops normalize` subcommand (CR-007):** Lint pass that scans markdown and YAML files for known Swedish character drift and restores correct characters. Supports single files or recursive folder scans. Flags: `--dry-run` (preview diff), `--strict-no-ambiguous` (skip ambiguous substitutions). Skips code blocks, inline code, URLs, file paths, YAML keys, and lines marked `<!-- no-normalize -->`. Updates folder CHANGELOG.md when applying.
- **`insights` pre-write Swedish character validator (CR-007):** Before writing any `_insights.yaml` entry with Swedish text in `summary`/`rationale`/`context`, scan against the substitution map. Refuses to write on non-ambiguous violations; warns on ambiguous ones. The structural validation that the MEMORY.md reminder cannot provide.
- **`ops-base` Step 7 swedish_chars resolution order documented:** New explicit 4-step resolution rule (folder CLAUDE.md → venture config → inheritance glob → base default). Points to `swedish_substitutions.yaml` as the canonical substitution list and to `/ops normalize` for after-the-fact remediation.
- **`ops-config` schema v1.2:** Bumped from v1.1 to reflect addition of `language_inheritance` config block and the substitution data file.

## [1.15.3] - 2026-04-07

### Changed
- **`transcript` Structure rule reordered (CR-006):** New canonical section order is **Nästa steg → Beslut → Konklusion → Diskussion → Bakgrund**. Action items first (a reader scanning at 08:30 needs what they own first, not narrative). Konklusion is the wrap-up of the actions/decisions above, not a discussion summary. Bakgrund moves to the bottom (reference, not navigation).
- **`transcript` Beslut/Decisions section is now mandatory.** Always include the section, even if there were no formal decisions -- in that case write `*(Inga formella beslut -- diskussionen var orienterande.)*` or the English equivalent. Honest absence is searchable; silent omission is not.
- **`transcript` Action Item Table format standardised:** Required 5-column markdown table format with `#`, `Åtgärd/Action`, `Ägare/Owner`, `Prio/Priority`, `Deadline`. If owner or deadline is unknown, write `?` rather than omitting the column. The visualisation app and `/daily-dashboard` parse this table -- variants break them.
- **`transcript` canonical heading names locked.** Pick one Swedish + one English term per concept: Nästa steg/Next Steps, Beslut/Decisions, Konklusion/Outcome, Diskussion/Discussion, Bakgrund/Background, Blockers. Banished variants (will not be produced in new files): Sammanfattning, Executive Summary, Summary, Action Items, Åtgärdspunkter, Huvudpunkter, Key Discussion Points, Decisions Made.
- **`transcript` Konklusion length floor removed.** A short meeting can still have a 1-sentence outcome. Always include the section, however brief. The undocumented ~110-word floor is removed.
- **`ops-base` canonical heading order documented** with the same rules as `/transcript`. Applies to both Concise and Detailed Strategic two-tier summary formats.
- **`daily-dashboard` meeting status detection** now recognises canonical headings (Nästa steg, Beslut, Konklusion, Diskussion + English equivalents). Legacy headings (Sammanfattning, Executive Summary, Action Items, etc.) are kept in the detection list for read-only back-compat with pre-CR-006 files.

### Added
- **`transcript` Template variants by meeting length (CR-006):** Three modes -- Concise (<30 min), Standard (30-90 min, default), Extended (>90 min). Skill picks variant by estimating duration from transcript metadata. Override with `/transcript --concise` or `/transcript --extended`.
- **`ops-config` base.yaml strings:** New canonical heading keys under `transcript`: `decisions`, `outcome`, `discussion`, `background`, `blockers`, `no_decisions_marker`, `action_table_headers`. Both English and Swedish defaults.

### Migration
- **Existing files keep their headings.** This change applies to new files only. The daily-dashboard's section detection retains the legacy heading variants for back-compat reads. No bulk migration is performed.

## [1.15.2] - 2026-04-07

### Changed
- **`preparation` agenda-card-first format (CR-005):** Restructured prep document template around a 60-second walk-in card on top (agenda + open actions), with deep-dive content below the fold separated by a horizontal rule. Top-of-file is now self-sufficient -- a reader who only sees the walk-in card can lead the meeting.
- **`preparation` Agenda Tag System (CR-005):** Each agenda item must start with one of five tags: `[DECISION]`, `[DEMO]`, `[STATUS]`, `[QUESTION]`, `[FYI]` (Swedish: BESLUT/DEMO/STATUS/FRÅGA/FYI). Item text after the tag must be a question or deliverable, not a topic noun phrase. Tags resolve from `strings.agenda_tags` in org config.
- **`preparation` Step 2.5 cross-reference scan is now mandatory** with explained relevance. Each cross-reference link must include a one-sentence explanation of why it matters; bare links are forbidden. Skip the section entirely if no relevant lateral mentions found.
- **`preparation` walk-in card prioritisation rule:** Maximum 5 items in the walk-in card -- they must be the most critical, not the first 5 reported. Items 6+ go in an "Övriga punkter" section after the deep dives.
- **`preparation` single-document principle:** A prep file may not reference another prep file as required reading. If two prep streams converge, merge them.
- **`preparation` Background section moved to bottom** of the document. It is reference material, not navigation.

### Added
- **`preparation` Step 0 frozen-prep check (CR-005):** Before writing or modifying a prep file, refuse if the meeting date is in the past (with `--force` override). Prevents mid-meeting contamination of prep files. Live updates belong in the transcript file, not the prep file.
- **`ops` bidirectional supersede linkage (CR-005):** When `/ops` marks a prep file as superseded, it now also writes a `*Preparation: [filename](path)*` back-link into the meeting summary's metadata footer. Readers can navigate prep -> transcript or transcript -> prep.
- **`ops-config` base.yaml strings:** New keys `preparation.cross_references`, `preparation.their_actions`, `preparation.deep_dive_separator`, and the `agenda_tags` table (English + Swedish defaults).

## [1.15.1] - 2026-04-06

### Changed
- **`ops` prepare filename:** Include organization/project name in preparation filenames (`YYMMDD-preparation-[org/project]-[type].md`) to distinguish preparations created the same day for different orgs/projects. H1 heading also includes org/project prefix.

## [1.15.0] - 2026-04-04

### Added
- **Skill evolution loop (CR-004):** Three-step feedback loop — capture, compile, improve. Skills silently log execution feedback (`edge_case`, `correction`) to `_insights.yaml`. New `/insights compile` finds patterns. New `/insights propose` generates SKILL.md improvement diffs. Configurable `auto_apply` for fully automatic evolution. Inspired by Bosma's Promptware and Karpathy's LLM Knowledge Base patterns.
- **`ops-base` Step 9:** Execution feedback capture — silently logs edge cases and user corrections to `_insights.yaml` when `evolution.enabled` is true. Inherited by all ops-based skills.
- **`transcript` Step 4.5:** Execution feedback capture — same as ops-base Step 9, for standalone transcript processing.
- **`insights` subcommands:** `compile`, `compile since YYMMDD`, `propose`, `propose apply [file|all]`.
- **`ops-config` schema:** New `evolution` section under `workflows.knowledge_extraction` with `enabled`, `auto_apply`, `compile_threshold`, `propose_threshold`.
- **`ops-config` base.yaml:** New insight types `edge_case`, `correction`, `skill_pattern` added to default types list. Evolution config defaults added.
- **`docs/proposals/`:** Directory for skill improvement proposals generated by `/insights propose`.
- **`ops-config` schema v1.1:** Bumped from v1.0 to reflect addition of `evolution` config section and execution feedback types.

## [1.14.1] - 2026-04-04

### Changed
- **CR index:** Renumbered self-evolution loop CR-001→CR-004 for chronological consistency. Registered CR-003 (inbox) as implemented.

## [1.14.0] - 2026-03-24

### Added
- **`ops` Verticals support (Step 9.5):** After meeting processing, /ops now checks for configured vertical documents -- living documents that aggregate insights across multiple meetings on a single strategic topic. When topic keywords from the meeting match a vertical's trigger, the user is prompted to update it. Verticals are config-driven via `workflows.verticals` in org config.
- **`ops-config` schema:** Added `verticals` section under `workflows` with fields: `path`, `name`, `topics`, `trigger` (if_mentioned/always).

## [1.13.2] - 2026-03-15

### Changed
- **`transcript` Structure rule:** Added "Conclusion first, details second" requirement. Summaries must now lead with the actual outcome/decision, followed by next steps, then background sections (labeled with "Bakgrund:" prefix). Anti-pattern guidance added to avoid "Sammanfattning" that describes discussion rather than conclusion.
- **`transcript` Name Resolution:** Added explicit rule to never trust transcript spellings. Names must be resolved against filename, `_meta.yaml`, and org config before use throughout summary content.

## [1.13.1] - 2026-03-12

### Added
- **`ops` ATTACHMENTS AND MEDIA section:** Guidance for handling PDFs, presentations, and binary files referenced in meetings. Includes detection triggers, placement convention (`.attachments/`), naming format (`YYMMDD-description.ext`), linking format for meeting summaries, and workflow steps for asking user and suggesting moves.

## [1.13.0] - 2026-03-08

### Added
- **`inbox` skill:** Universal entry point for unstructured content (voice memos, quick notes, emails, raw text). Auto-classifies and routes to the appropriate downstream skill (`/transcript`, `/ops`, `/tasks`). Subcommands: `/inbox [content]`, `/inbox status`, `/inbox process [id]`, `/inbox help`. Stores items in `_inbox/` with `_inbox.yaml` index. Supports web UI via core-skills-visualisation.
- **README.md:** Added inbox skill to skill table, dependency tree, overview table, and choosing guide.

## [1.12.1] - 2026-03-04

### Fixed
- **`tasks/skill.md` anonymization:** Replaced real company names, personal names, and project identifiers with generic placeholders in all examples and documentation

## [1.12.0] - 2026-03-04

### Changed
- **Distributed `_tasks.yaml` system (v2):** Tasks are now tracked in per-folder `_tasks.yaml` files (like `_insights.yaml`) instead of a single central file. Replaces `task-priority-matrix.md` entirely.
  - `tasks/skill.md`: Rewritten for v2 schema -- per-folder discovery, `--all` aggregation, `context`/`scope` fields, local file creation
  - `ops/SKILL.md`: Step 5 `task_yaml` replaces `task_matrix`; Step 9 task import targets local `_tasks.yaml`; fallback creates v2 file
  - `daily-dashboard/SKILL.md`: Multi-file scanning for tasks; groups by context; updated org mode task discovery and priority tracker links
  - `transcript/SKILL.md`: Step 4 task import targets local folder `_tasks.yaml` (not vault root); creates v2 file if missing
  - `ops-base/SKILL.md`: Task management section updated for per-folder `_tasks.yaml` convention

## [1.11.2] - 2026-03-04

### Changed
- **Vault folder structure redesign:** Updated all skills to use new `_contacts/`, `_projects/`, `_private/` convention instead of `=*/` prefix pattern
  - `transcript/SKILL.md`: Contact folder discovery now checks `_contacts/` directory
  - `preparation/SKILL.md`: Folder matching uses `_contacts/firstname-lastname/` format
  - `daily-dashboard/SKILL.md`: Scan locations, contact name extraction (hyphen-separated), symlink paths updated
  - `insights/SKILL.md`: Scan paths and examples use `_contacts/` and `_projects/` prefixes
  - `tasks/skill.md`: Example vault path updated from `=privat/` to `_private/`
  - All skill README.md files updated to match
- `README.md`: Version to 1.11.2

## [1.11.1] - 2026-03-04

### Changed
- **Privacy enforcement in `_insights.yaml`:** Added explicit rules to `transcript` Step 3.5, `insights` Extraction Reference, and `ops` Step 5.5 -- NEVER include personal names or company names in `summary`, `rationale`, or `tags` fields. Includes bad/good examples.
- **Swedish character enforcement strengthened:** Added YAML-specific reminders to `transcript`, `insights`, and `ops` skills -- `_insights.yaml` fields are equally prone to missing å, ä, ö as markdown files.
- Anonymized bad-example snippets in `transcript` and `insights` skills (replaced real names with generic placeholders)
- `transcript/SKILL.md`: Removed specific user name reference from Step 4 task import description
- `README.md`: Version to 1.11.1

## [1.11.0] - 2026-03-04

### Added
- **`insights` skill:** Knowledge extraction manager for retroactive insight extraction
  - `reprocess [target]`: Extract insights from existing YYMMDD-*.md transcript files
    - Target: folder path, `all` (all CHANGELOG.md folders), `since YYMMDD` (date filter)
    - Same extraction logic as transcript Step 3.5 (types, threshold, dedup)
    - Progress reporting per folder, summary at end
  - `scan-claude-md`: Extract embedded knowledge from CLAUDE.md files in vault
    - Type mapping: decisions, preferences, learnings, patterns from structured sections
    - Re-extracts when CLAUDE.md is modified after last extraction
  - `status`: Show insights statistics (counts, top folders, reprocessing opportunities)
  - `help`: Usage guide with examples

### Changed
- `README.md`: Added insights skill to skills table, dependency diagram, comparison, workflows, interaction diagram, version to 1.11.0

## [1.10.0] - 2026-03-03

### Added
- **Knowledge Extraction (`_insights.yaml`):** Silent accumulation layer that captures durable insights from meetings and conversations
  - `transcript` Step 3.5: Scans summaries for decisions, preferences, learnings, opportunities, and patterns
  - `ops` Step 5.5: Same extraction with additional ops-specific sources (domain additions, agenda resolutions)
  - Per-folder `_insights.yaml` files alongside CHANGELOG.md
  - Deduplication by source file, configurable threshold, max 10 insights per meeting
  - Never surfaces in skill output -- visualization app is the only consumer
- **`ops-config` base.yaml:** `knowledge_extraction` workflow config (enabled by default)
- **`ops-config` base.yaml:** `strings.insights` and `strings_sv.insights` i18n blocks

## [1.9.0] - 2026-03-03

### Added
- `preparation`: Step 2.5 -- Cross-Context Scan. After gathering context from the contact's folder, scans recent `YYMMDD-*.md` files across all `=*/` folders (last 7 days) for mentions of the contact, company, or key topics. Adds a `{strings.preparation.cross_references}` section to the preparation document when relevant mentions are found. Skips when fewer than 3 contact folders or no matches.
- `README.md`: Daily Workflow Guide section -- consolidated overview of which skills to run before, during, and after meetings throughout a workday

## [1.8.3] - 2026-02-26

### Added
- **`ops` subcommand: `/ops help`** -- shows usage guide, skill correlation, config loading, and common patterns

### Changed
- Anonymized all documentation: replaced company names, personal names, infrastructure details, and GitHub URLs with generic placeholders
- `ops/SKILL.md`: Added `help` subcommand definition, argument-hint updated
- `README.md`: Updated /ops description, workflow comparison, skill selection table, version to 1.8.3
- `README.md`: Rewrote skill selection guide, added quick-start table, updated interaction/lifecycle diagrams to show /ops as primary path

## [1.8.2] - 2026-02-26

### Added
- **`ops` subcommand: `/ops status`** -- shows available org configs, active config for current directory, team, workflows, and base defaults
- **`ops` Step 9: Post-Processing** -- optional task import and dashboard refresh after meeting processing
  - `post_processing.task_import`: Extract action items from summary, match/import to `_tasks.yaml`
  - `post_processing.dashboard_refresh`: Regenerate org dashboard after all updates
- **`ops` usage guidance:** "WHEN TO USE /OPS vs /TRANSCRIPT" section in SKILL.md
- **`ops-config` schema:** `post_processing` section (task_import + dashboard_refresh)
- **`ops-config` base.yaml:** `post_processing` defaults (both disabled)

### Changed
- `ops/SKILL.md`: Added SUBCOMMANDS section (`/ops status`), argument-hint updated, added `post_processing` to config table, added Step 9, added usage guidance
- `ops-config/README.md`: Updated to reference `/ops` instead of removed domain skills
- `README.md`: Updated /ops description with status subcommand, workflow comparison, skill selection table, task flow diagram, config list, version to 1.8.2

## [1.8.1] - 2026-02-25

### Removed
- `engagement-ops` skill (moved to [bravo-skills](https://github.com/bravo-org/bravo-skills) -- consulting-specific, not core)

## [1.8.0] - 2026-02-25

### Added
- **`ops` skill:** Unified meeting and operations processing, config-driven for any organization
  - Replaces `project-ops` (core-skills), `bravo-ops` (bravo-skills), `management-ops` and `marketing-ops` (acme-skills)
  - Summary format driven by `summary_sections` config or TWO-TIER default
  - Configurable file updates (1-5 files), action propagation, agenda management
  - Domain additions applied from org config
  - Fallback to base.yaml when no org config exists
- **`ops-config` schema additions:**
  - `summary_sections`: Custom meeting summary structure (table/subsections/freeform)
  - `status_terminology`: Domain-specific work and resolution status terms
  - `issue_id_format`: Structured issue ID pattern
  - `workflows.agenda_management`: Post-meeting agenda updates (enabled, file, section)
- **`ops-config` base.yaml defaults:** Empty summary_sections, empty status_terminology, null issue_id_format, agenda_management disabled

### Removed
- `project-ops` skill (replaced by `/ops` with project-level config)

### Changed
- `ops-base`: Updated description and references to point to `/ops` instead of domain-specific skills
- `README.md`: Updated skills table, dependency diagram, comparison section, workflow diagrams for `/ops`

## [1.7.5] - 2026-02-24

### Removed
- `cr` skill (moved to [bravo-skills](https://github.com/bravo-org/bravo-skills))

## [1.7.4] - 2026-02-23

### Changed
- **`transcript` Step 3:** CHANGELOG update is now mandatory -- always creates or updates CHANGELOG.md in target folder. If no CHANGELOG exists, one is created automatically with entries for all existing files in the folder.

## [1.7.3] - 2026-02-21

### Added
- **`tasks` skill:** New personal task tracker with cross-project correlation
  - Central `_tasks.yaml` index at vault parent level
  - Source linking back to meetings/decisions
  - Automatic carry-forward of incomplete tasks
  - Privacy model (`private: true/false`) for shared vs personal tasks
  - Project tagging for cross-project views
  - Structured YAML format with history tracking
  - Commands: `show`, `add`, `done`, `import`, `weekly`, `archive`, `migrate`
- **`transcript` Step 4:** Task import integration
  - Offers to import action items to `_tasks.yaml` after saving transcript
  - Auto-detects project from file path
  - Links tasks back to source meeting
  - Respects existing task schema
- **`daily-dashboard` task integration:**
  - Reads active tasks from `_tasks.yaml`
  - Displays in "Teamfokus" section grouped by priority
  - Shows overdue, P0, P1, P2 with source links
  - Includes completed tasks from `_tasks-history.md`
  - Task counts in Quick Stats table

### Changed
- `README.md`: Added comprehensive skill interaction documentation with state diagrams
- `transcript/skill.md`: Added Step 4 (Task Import), updated meeting lifecycle diagram
- `daily-dashboard/skill.md`: Added Personal Task Integration section, updated templates and execution steps

### Architecture
- Tasks flow: `/transcript` extracts action items -> offers import -> `_tasks.yaml` -> `/daily-dashboard` displays
- Central task index enables cross-project visibility while respecting per-project filtering
- Privacy model separates personal tasks from shared team views

### Notes
- **Person+project folder pattern validated:** Merged contact+project folders using the pattern `=person-project/`. Transcript skill routes via CLAUDE.md routing table. No skill code changes required.

## [1.7.2] - 2026-02-19

### Changed
- `daily-dashboard`: Org mode now writes to `_Dashboard-{org}.md` (e.g. `_Dashboard-acme.md`) instead of `_Dashboard.md`. Generic mode keeps `_Dashboard.md`. Both coexist without collision.

## [1.7.1] - 2026-02-19

### Fixed
- `update-skills`: All git commands now use `git -C <repo-path>` instead of relying on shell working directory. Prevents operating on the wrong repository when processing multiple repos sequentially.
- `update-skills`: Added safety rule 9 -- explicit `-C` flag requirement for every git command

## [1.7.0] - 2026-02-19

### Added
- **String tables (i18n):** `ops-config` schema and `base.yaml` now include `strings` (English) and `strings_sv` (Swedish) blocks for configurable section headers, annotations, labels, and filename keywords
- **Lifecycle integration:** `/transcript` Step 1.5 links back to preparation files when one exists for the same contact + date
- **Standup discovery:** `/daily-dashboard` now categorizes `standup`/`daily-standup` files in a dedicated "Standup/Projekt" section
- **Dashboard deduplication:** When both preparation and transcript exist for same contact + date, only the transcript is shown (preparation suppressed)
- **README howto:** "How Skills Work Together" section documenting meeting lifecycle, file discovery, config-driven strings, and CHANGELOG conventions

### Changed
- `ops-config/schema.md`: Added `strings` section definition with resolution order documentation
- `ops-config/base.yaml`: Added `strings` and `strings_sv` default blocks
- `preparation/SKILL.md`: Template annotated with `{strings.*}` references, string resolution section added
- `transcript/SKILL.md`: String resolution section, Step 1.5 lifecycle link, metadata footer, lifecycle diagram
- `daily-dashboard/SKILL.md`: String resolution section, expanded 3-category file classification, deduplication logic, standup scanning in org mode
- `README.md`: Added "How Skills Work Together" section, version bump to 1.7.0

### Notes
- `bravo-ops` uses `YYYY-MM-DD` date format instead of `YYMMDD` -- not addressed in this release but noted for future alignment
- All changes are backwards-compatible: skills without config loaded fall back to current hardcoded strings

## [1.6.4] - 2026-02-19

### Added
- `preparation` skill for creating structured meeting preparation documents
  - Takes a contact name + optional date: `/preparation david tomorrow`
  - Reads previous transcripts, preparations, and CHANGELOG from the contact's `=*/` folder
  - Generates briefing with context, numbered discussion topics, open action items, and suggested agenda
  - Supports post-meeting updates with `[UTFALL]` annotations
  - Output follows `YYMMDD-förberedelse-*.md` naming convention, auto-discovered by `/daily-dashboard`

### Changed
- `daily-dashboard`: Rewritten to support two modes -- generic and org
  - Generic mode (default): scans current working directory for `YYMMDD-*.md` files in `=contact/` folders
  - Org mode: pass an org name (e.g. `/daily-dashboard acme`) to load org config and use project-specific discovery
  - New argument format: `[org] [today|tomorrow|YYMMDD]`
  - New symlink types: `_PREP-*` for preparations, `_TODAY-*` for meetings
  - Persistent symlinks (`_MGMT-*`, `_MKT-*`, etc.) only created in org mode
  - Swedish-language dashboard in generic mode
- `transcript`: Added cross-reference to `/preparation` skill and naming convention documentation

## [1.6.3] - 2026-02-17

### Changed
- `daily-dashboard`: Added casing convention (title case for status labels, e.g. "Completed" not "COMPLETED")
- `daily-dashboard`: Added "Tomorrow" section to template with daily standup placeholder
- `daily-dashboard`: Added completed meeting example to template

## [1.6.2] - 2026-02-17

### Added
- `daily-dashboard` skill for daily meeting and task dashboard generation
  - Creates mobile-friendly `_Dashboard.md` with meeting links and embeds
  - Creates desktop symlinks for quick access (`_TODAY-*`, `_MGMT-*`, `_MKT-*`, `_MOBILE-*`)
  - Auto-discovers meetings by date (YYMMDD format)
  - Extracts critical items from priority matrices
  - Standalone skill, no dependency on ops-base

## [1.6.1] - 2026-02-15

### Changed
- Moved origin to `your-username/core-claude-skills` (public)
- Deleted old `bravo-org/core-skills` GitHub repo
- Updated all documentation URLs across core-skills, acme-skills, and bravo-skills

## [1.6.0] - 2026-02-15

### Removed
- `management-ops` skill (moved to [acme-skills](https://github.com/acme-org/acme-claude-skills))
- `marketing-ops` skill (moved to [acme-skills](https://github.com/acme-org/acme-claude-skills))
- `bravo-ops` skill (moved to [bravo-skills](https://github.com/bravo-org/bravo-skills))
- `ops-config/acme.yaml` (moved to acme-skills as `acme-ops-config`)
- `ops-config/bravo.yaml` (moved to bravo-skills as `bravo-ops-config`)

### Changed
- core-skills is now purely generic: ops-base, ops-config (schema + base only), transcript, project-ops, cr, update-skills
- Updated update-skills sources table with acme-skills and bravo-skills repos
- Updated README with new skill table, dependency diagram, and related repos
- Updated ops-base config docs to reflect org configs as separate skills
- Version bump to 1.6.0

## [1.5.0] - 2026-02-15

### Changed
- Renamed repository from `bravo-skills` to `core-skills` to reflect its role as the generic foundation
- Replaced all relative cross-skill paths (`../ops-base/`, `../ops-config/`) with skill-name references (`~/.claude/skills/`) that resolve through symlinks regardless of repo location
- Updated config resolution pattern: org configs now live in their own skill directories (`{org}-ops-config/{org}.yaml`) instead of `ops-config/{org}.yaml`
- Updated update-skills sources table with new repo name and URLs
- Updated all documentation (README.md, README-local-setup.md) with new repo name
- Version bump to 1.5.0

## [1.4.0] - 2026-02-15

### Added
- `update-skills` skill for skill repo management
  - 4 operations: update (default), status, check, install
  - Multi-remote support with version safety (commit graph ancestor check before pull)
  - Repo discovery via self-discovery, symlink scanning, and sources table matching
  - Automatic symlink creation for new skills after pull
  - Symlink health auditing (broken, missing, orphaned detection)
  - Repo installation with automatic remote configuration
  - Standalone: no dependency on ops-base or ops-config
- Bootstrapping shortcut in README: clone + single symlink + `/update-skills update`

### Changed
- Made repo paths flexible: removed hardcoded `~/Projects/` from sources table and all documentation
  - Repos are now discovered dynamically via symlink resolution (self-discovery + symlink scanning)
  - `install` clones repos as siblings of `core-skills` (base directory detected from `update-skills` symlink target)
  - Bootstrapping instructions now work from any directory
- Updated README.md with update-skills in skills table, comparison section, dependency diagram, and installation instructions
- Simplified README installation section: replaced 9-symlink manual setup with 4-line quick start using `/update-skills` bootstrapping
- Removed Remotes section from public README (internal detail)
- Added `README-local-setup.md` for NAS-first setup on local network machines (clone from NAS, dual-remote config)
- Version bump to 1.4.0

## [1.3.0] - 2026-02-15

### Added
- `cr` skill for change request lifecycle management
  - 10 operations: create, status, promote, branch, list, next, show, deps, version, audit
  - Draft/Proposed templates with status lifecycle enforcement (Draft -> Proposed -> Planned -> Implemented -> Archived)
  - CR index management with automatic README.md updates
  - Git branch creation for Proposed CRs (kebab-case branches, snake_case filenames)
  - Integrity auditing with auto-fix (orphaned files, broken links, status mismatches)
  - Project-agnostic: CR directory path configurable via CLAUDE.md

### Changed
- Updated README.md with cr skill in skills table, comparison section, dependency diagram, and installation instructions
- Version bump to 1.3.0

## [1.2.1] - 2026-02-12

### Added
- Comprehensive skill comparison section in README
  - Overview table (organization, language, files updated, domain focus)
  - Shared features via ops-base
  - Detailed differences between each skill
  - Workflow comparison diagrams
  - Skill selection guide
  - Instructions for adding new organizations

## [1.2.0] - 2026-02-12

### Added
- `ops-config` configuration system for organization-agnostic skills
  - `schema.md`: YAML schema definition for org configs
  - `base.yaml`: Default fallback configuration
  - `acme.yaml`: Acme organization (English, full team, responsibility matrix)
  - `bravo.yaml`: Bravo organization (Swedish, action propagation enabled)
- Structured extraction format in `transcript` skill
  - YAML-based extraction output for domain skills
  - Enables consistent parsing across all ops skills

### Changed
- `ops-base`: Added configuration resolution logic and workflow orchestration
- `management-ops`: Now reads team/terminology from acme.yaml config
- `marketing-ops`: Now reads team/terminology from acme.yaml config
- `bravo-ops`: Now reads team/terminology from bravo.yaml config
- Updated README.md with config system documentation and architecture diagram

### Architecture
- Skills are now organization-agnostic via layered config system
- Config resolution: project-level > org-level > base defaults
- Transcript serves as universal extraction layer for domain skills

## [1.1.0] - 2026-02-12

### Added
- `bravo-ops` skill for Bravo business operations
  - Swedish-language output for all documentation
  - Integrates with Bravo styrning/ templates (mall-motesreflektion.md)
  - Decision propagation to BRAVO.md, actions to ALEX.md/HANK.md
  - Customer sentiment tracking, delivery status monitoring
  - Extends ops-base framework

### Changed
- Updated README.md with bravo-ops in skills table and dependency diagram

## [1.0.1] - 2026-02-12

### Added
- `project-ops` skill for development standup processing
  - 5-file update workflow (summary, task-priority-matrix, README, CHANGELOG, meetings index)
  - 8-section detailed meeting format
  - Development-specific sections (Completed, In Progress, Technical Updates, Issues, Decisions, Actions, Version Status, Status Summary)
  - Extends ops-base framework

### Changed
- Updated README.md with project-ops in skills table and dependency diagram

## [1.0.0] - 2026-02-11

### Added
- Initial release with 4 skills:
  - `ops-base` - Shared operational framework
  - `transcript` - Transcription processing
  - `management-ops` - Executive management documentation
  - `marketing-ops` - Marketing operations documentation
