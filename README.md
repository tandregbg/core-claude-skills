# core-skills

**Version:** 1.16.0

Claude Code skills for operational documentation, transcript processing, task tracking, knowledge extraction, and team coordination.

## What's new in v1.15.2-v1.15.4 (2026-04-07)

Three audit-driven improvements landed together. The full audit lives in [`docs/audits/2026-04-07-skills-output-audit.md`](docs/audits/2026-04-07-skills-output-audit.md).

- **CR-005 (v1.15.2) -- Preparation agenda-card-first format.** Prep documents are now structured around a 60-second walk-in card on top (agenda + open actions), with deep-dive content below the fold. Agenda items must be tagged questions (`[DECISION]`/`[DEMO]`/`[STATUS]`/`[QUESTION]`/`[FYI]`), not topic noun phrases. Walk-in card max 5 items, prioritised by criticality. Step 0 frozen-prep check refuses mid-meeting edits. Step 2.5 cross-reference scan is mandatory with explained relevance. Single-document principle: no required-reading chains between prep files. `/ops` writes bidirectional supersede links so prep <-> transcript navigation works in both directions.
- **CR-006 (v1.15.3) -- Summary heading reorder and standardise.** New canonical section order for transcript/ops summaries: **Nästa steg → Beslut → Konklusion → Diskussion → Bakgrund**. Action items first (a reader scanning at 08:30 needs what they own first, not narrative). Beslut/Decisions section now mandatory with explicit "no formal decisions" marker if empty. Action item tables use a fixed 5-column format. Canonical heading names locked -- variants like Sammanfattning, Executive Summary, Action Items, Åtgärdspunkter, Huvudpunkter, Decisions Made will not be produced in new files (legacy files keep their headings; daily-dashboard recognises both for back-compat). Konklusion length floor removed -- short meetings still get a 1-sentence outcome. Three template variants by meeting length: Concise (<30 min) / Standard (30-90 min, default) / Extended (>90 min).
- **CR-007 (v1.15.4) -- Swedish character inheritance + `/ops normalize`.** New `language_inheritance` config block in `base.yaml` automatically inherits `swedish_chars: strict` into `_projects/`/`_contacts/`/`_private/`/`_inbox/` regardless of whether the folder has its own CLAUDE.md. Catches sub-trees that previously slipped through enforcement. New `/ops normalize <path>` subcommand for hand-written docs that bypassed the pipeline -- restores Swedish characters using the new `swedish_substitutions.yaml` data file. Supports `--dry-run` and `--strict-no-ambiguous`. The `/insights` skill gains a pre-write Swedish character validator that refuses to write entries containing known character drift in `summary`/`rationale`/`context` fields. Schema bumped 1.1 → 1.2.



## Skills included

| Skill | Description | User-invocable |
|-------|-------------|----------------|
| `ops-base` | Shared operational framework (meeting formats, task management, workflows, archive policy). Base module referenced by other ops skills. | No |
| `ops-config` | Configuration system -- schema definition and base defaults for organization-specific settings. | No |
| `transcript` | Process and summarize transcriptions from calls, meetings, or voice recordings. Action-first canonical structure (Nästa steg → Beslut → Konklusion → Diskussion → Bakgrund). Three template variants by meeting length. Provides structured extraction for domain skills. Offers task import. Extracts durable insights to `_insights.yaml`. | Yes (`/transcript`) |
| `ops` | Unified meeting and operations processing -- config-driven for any organization. Subcommands: `/ops status` shows available org configs, `/ops prepare` creates pre-meeting preparation, `/ops normalize` restores Swedish characters in hand-written docs, `/ops help` shows usage guide. Extracts durable insights to `_insights.yaml`. Replaces project-ops, bravo-ops, management-ops, marketing-ops. | Yes (`/ops`) |
| `update-skills` | Skill repo management -- fetch/pull with version safety, symlink creation, health auditing, repo installation. Standalone. | Yes (`/update-skills`) |
| `daily-dashboard` | Daily meeting and task dashboard generator -- works generically from any vault or with org-specific config. Creates dashboard file and desktop symlinks. Integrates with task tracker. | Yes (`/daily-dashboard`) |
| `preparation` | Create meeting preparation documents with a 60-second walk-in agenda card on top and deep-dive content below the fold. Tagged questions ([DECISION]/[DEMO]/[STATUS]/[QUESTION]/[FYI]) instead of topic noun phrases. Mandatory cross-reference scan with explained relevance. Frozen at meeting time -- no mid-meeting edits. | Yes (`/preparation`) |
| `tasks` | Personal task tracker with cross-project correlation. Central task index, source linking, automatic carry-forward, privacy model. | Yes (`/tasks`) |
| `insights` | Knowledge extraction manager and skill evolution engine. Backfills `_insights.yaml`, compiles execution feedback into patterns, proposes SKILL.md improvements. Subcommands: `reprocess`, `scan-claude-md`, `compile`, `propose`, `status`, `help`. | Yes (`/insights`) |
| `inbox` | Universal entry point for unstructured content. Classifies voice memos, quick notes, emails, raw text and routes to the appropriate downstream skill (`/transcript`, `/ops`, `/tasks`). Stores in `_inbox/` with web UI support. | Yes (`/inbox`) |
| `md2pdf` | Convert markdown files to styled PDFs. Supports Mermaid diagrams (rendered as PNG), tables, professional A4 typography. Individual or combined output. `--outbox NAME` packages PDFs into `<vault>/_outbox/YYMMDD-NAME/` with auto-generated manifest and email stub. | Yes (`/md2pdf`) |
| `analytics` | Vault-level content analytics -- file creation trends, skill adoption, contact engagement, content distribution, unprocessed backlog detection. Analyses file metadata (names, dates, paths), not contents. Outputs to `_analytics/` folder. Subcommands: `overview`, `skills`, `contacts`, `backlog`, `help`. | Yes (`/analytics`) |

## Shared contract: `ecosystem.yaml`

[`ecosystem.yaml`](ecosystem.yaml) is the single source of truth for the suite. Marvin (formerly core-skills-visualisation), the landing page, Trillian (vault-pulse), and any future external tools should read it instead of hard-coding skill lists, schema versions, or vault file paths.

It declares:

- **Schema versions** -- `ops_config`, `contact_meta`, `tasks`, `insights`
- **Insight type enums** -- content vs evolution
- **Contact classification** -- levels, defaults, folder pattern defaults (CR-009)
- **Skills registry** -- user-invocable + non-invocable, with badges and subcommands
- **`vault_conventions`** (CR-010, contract_version >= 2) -- authoritative declaration of every file the suite produces or consumes in a user's vault. Each entry documents path pattern, purpose, schema link, writers, readers, and lifecycle. Three sections: `vault_root`, `per_folder`, and cross-cutting `rules` (vault-relative paths, single inbox/outbox, config resolution order, naming, audio/transcript pairing).
- **Visualisation features** -- the page list Marvin renders

The contract is versioned (`contract_version: 2`). Bumps are additive when possible -- older clients ignore unknown blocks; newer clients get the additional structured declarations. Run [`scripts/check-ecosystem-alignment.sh`](scripts/check-ecosystem-alignment.sh) after editing to verify Marvin's CLAUDE.md and the landing page reference the same `core_skills_version`.

## Architecture

Skills are **organization-agnostic**. They use a layered configuration system (rewritten in v1.16.0 -- CR-011):

1. **Project-level** (`.claude/ops-config.yaml`) -- overrides for specific projects
2. **Folder-local** (`<vault>/<org>/_ops.yaml`) -- per-org config, walked up from CWD until vault root
3. **Vault-wide** (`<vault>/_config/base.yaml`, optional) -- overrides shared across all folders
4. **Base defaults** (`~/.claude/skills/ops-config/base.yaml`) -- fallback values

Pre-v1.16.0 chain (`~/.claude/skills/{org}-ops-config/{org}.yaml`) is deprecated, removed in v1.17.0. See CHANGELOG `[1.16.0]` `### Migration` for one-time migration steps.

The project's `CLAUDE.md` remains the single source of truth for vault-specific details (folder structure, meeting routing, file naming conventions).

### Configuration

Domain skills read from their org config for:
- `language`: Output language (english/swedish/input)
- `team`: Participant recognition and attribution
- `responsibility_matrix`: Owner assignments
- `terminology`: Domain-specific terms
- `workflows`: Which files to update, action propagation, post-processing (task import, dashboard refresh), knowledge extraction, verticals

As of v1.16.0 (CR-011), org configs live in `<vault>/<org>/_ops.yaml` -- co-located with the content they describe. This repo provides `base.yaml` as fallback and `schema.md` as the schema definition.

### Skill dependencies

```
core-skills (this repo)
  ops-config (schema + base defaults)
  ops-base (shared standards) <-- reads config
    +-- ops (extends ops-base, config-driven, replaces all domain ops skills)
  transcript (extraction layer) --> offers task import, writes _insights.yaml
  preparation (standalone -- meeting preparation)
  daily-dashboard (standalone -- generic + org mode) <-- reads _tasks.yaml
  tasks (standalone -- personal task tracker) <-- writes _tasks.yaml
  update-skills (standalone -- repo management)
  insights (standalone -- extraction manager + evolution engine) --> reads transcripts + CLAUDE.md, writes _insights.yaml, compiles patterns, proposes SKILL.md changes
  analytics (standalone -- vault metrics) --> reads file metadata (names, dates, paths), writes _analytics/
  inbox (standalone -- universal capture) --> classifies + routes to transcript/ops/tasks
```

`/ops` is config-driven: behaviour changes based on org config (`bravo-ops-config`, `acme-ops-config`, etc.) and project-level overrides. Organization configs live in separate repos.

---

## Skill Comparison

### Overview

| Skill | Organization | Language | Files Updated | Domain Focus |
|-------|--------------|----------|---------------|--------------|
| `transcript` | Any | Input language | 1-2 + tasks + insights | Generic extraction |
| `ops` | Any (config-driven) | Per config | Per config (1-5) + insights | Meetings, standups, ops |
| `update-skills` | Any | English | 0 (manages symlinks/repos) | Skill repo management |
| `daily-dashboard` | Any | Swedish/per config | 1 + symlinks | Meeting/task dashboard |
| `preparation` | Any | Swedish/input | 1-2 | Meeting preparation |
| `tasks` | Any | Input language | 2 (_tasks.yaml + history) | Personal task tracking |
| `insights` | Any | Input language | _insights.yaml (per folder) | Retroactive knowledge extraction |
| `analytics` | Any | Swedish/input | _analytics/ (snapshots) | Vault-level content metrics |
| `inbox` | Any | Input language | _inbox/ (capture + classify) | Universal content capture |

Organization-specific skills extend `ops-base` and live in their own repos.

### What They Share (via ops-base)

All domain skills inherit from `ops-base`:

- **Priority system:** P0 (critical) through P3 (research)
- **Status indicators:** BLOCKED, IN PROGRESS, ON TRACK, TODO, COMPLETE
- **Meeting formats:** Two-tier summary (Concise vs Detailed Strategic)
- **Task lifecycle:** Creation > Active > Post-meeting > Archive
- **CHANGELOG format:** Standardized entry structure
- **Archive policy:** Never delete, always archive to `.archive/`
- **Cross-referencing:** Link standards for meetings, tasks, changelogs

### Skill Details

#### transcript (standalone)

- **Purpose:** Universal extraction layer
- **Output:** Single summary file + CHANGELOG, `_insights.yaml` (knowledge extraction)
- **Format (CR-006, v1.15.3):** Action-first canonical structure -- Nästa steg → Beslut → Konklusion → Diskussion → Bakgrund. Beslut section is mandatory (write `*(Inga formella beslut)*` if empty). 5-column action item table. Three template variants by meeting length (Concise / Standard / Extended).
- **Special:** Provides structured YAML extraction for domain skills. Step 3.5 silently extracts durable insights (decisions, preferences, learnings, opportunities, patterns) to `_insights.yaml`.
- **Operations:** `/transcript [content]` (paste text or provide file path), `/transcript --concise`, `/transcript --extended`
- **Use when:** Processing any transcript without domain-specific formatting

#### ops (config-driven)

- **Purpose:** Unified meeting and operations processing
- **Output:** Configurable -- summary only (default), or up to 5 files (summary, CHANGELOG, README, task-priority-matrix, meetings/README), plus optional post-processing (task import to `_tasks.yaml`, dashboard refresh), plus `_insights.yaml` (knowledge extraction)
- **Config-driven:** Summary sections, status terms, domain additions, action propagation, agenda management, post-processing, knowledge extraction, verticals all controlled by org config
- **Replaces:** project-ops, bravo-ops, management-ops, marketing-ops
- **Operations:** `/ops [content]` (default), `/ops prepare [type]`, `/ops normalize <path>` (CR-007 -- restore Swedish characters in hand-written docs), `/ops status`, `/ops help`
- **Use when:** Any meeting type -- standups, management meetings, marketing reviews, business syncs. The default choice -- use `/transcript` only when you explicitly don't want org config machinery.

#### update-skills (standalone)

- **Purpose:** Skill repo management and maintenance
- **Output:** No files created in projects -- manages symlinks and git state
- **Operations:** update, status, check, install
- **Special:** Multi-remote version safety (ancestor check before pull), symlink health auditing, auto-discovery of repos via symlink scanning
- **Use when:** Updating skills to latest, setting up a new machine, checking symlink health, installing new skill repos

#### daily-dashboard (standalone)

- **Purpose:** Daily meeting and task dashboard generation
- **Output:** `_Dashboard.md` file + desktop symlinks (`_PREP-*`, `_TODAY-*`, and `_MGMT-*`/`_MKT-*` in org mode)
- **Operations:** `[org] [today|tomorrow|YYMMDD]` -- generic mode (scan cwd) or org mode (load config)
- **Special:** Two modes -- generic (scans `_contacts/` folders for dated files) and org mode (loads `<vault>/<org>/_ops.yaml` for project-specific discovery, CR-011). Discovers preparations and transcripts automatically by filename pattern.
- **Use when:** Starting your day, preparing for meetings, need quick access to today's files

#### preparation (standalone)

- **Purpose:** Structured meeting preparation from contact history, optimised for walk-in usability
- **Output:** `YYMMDD-förberedelse-*.md` file (optionally CHANGELOG)
- **Operations:** `<contact name> [date]`
- **Format (CR-005, v1.15.2):** Two-tier structure -- 60-second walk-in card on top (agenda + open actions), deep dives below the fold separated by a horizontal rule. Agenda items use a 5-tag system (`[DECISION]`/`[DEMO]`/`[STATUS]`/`[QUESTION]`/`[FYI]`, Swedish: BESLUT/DEMO/STATUS/FRÅGA/FYI) and must be questions or deliverables, not noun phrases. Maximum 5 items in the walk-in card -- prioritised by criticality.
- **Special:** Step 0 frozen-prep check refuses mid-meeting edits to past-dated prep files. Step 2.5 cross-reference scan is mandatory with explained relevance -- bare links forbidden. Single-document principle: a prep file may not require reading another prep file. Background moves to bottom (reference, not navigation). Bidirectional supersede linkage when `/ops` processes the meeting transcript.
- **Use when:** Preparing for an upcoming call or meeting with a contact

#### tasks (standalone)

- **Purpose:** Personal task tracking with cross-project correlation
- **Output:** `_tasks.yaml` (active tasks), `_tasks-history.md` (completed log)
- **Operations:** `show`, `add`, `done`, `import`, `weekly`, `archive`, `migrate`
- **Special:** Central index at vault parent, source linking to meetings, privacy model (`private: true/false`), project tagging, automatic carry-forward. Integrates with `/transcript` (import) and `/daily-dashboard` (display).
- **Use when:** Tracking action items from meetings, managing personal tasks across projects, reviewing weekly progress

#### insights (standalone)

- **Purpose:** Retroactive knowledge extraction from existing corpus
- **Output:** `_insights.yaml` (per folder, same format as transcript Step 3.5)
- **Operations:** `reprocess [target]`, `scan-claude-md`, `status`, `help`
- **Special:** Backfills insights from historical transcripts and CLAUDE.md files. Dedup by `source.file` -- safe to run repeatedly. Does not duplicate extraction logic -- references `/transcript` Step 3.5 as authoritative source.
- **Use when:** Setting up insights for a folder that predates the knowledge extraction feature, or extracting embedded knowledge from CLAUDE.md files

#### analytics (standalone)

- **Purpose:** Vault-level content analytics — longitudinal trends, not daily snapshots
- **Output:** `_analytics/YYMMDD-*.md` snapshot files (overview, skill-adoption, contact-engagement, backlog-report)
- **Operations:** `overview` (default), `skills`, `contacts`, `backlog`, `help`
- **Special:** Reads file metadata only (names, dates, paths) — never file contents. Path-first classification avoids keyword miscount. Privacy-aware via `_meta.yaml`. Historical snapshots archived automatically.
- **Use when:** Understanding vault growth trends, tracking skill adoption, analysing contact engagement patterns, finding unprocessed content

### Workflow Comparison

```
transcript:       Input -> Summary -> CHANGELOG -> (knowledge extraction -> _insights.yaml)
                                 -> (offer task import)

ops:              Input -> Summary -> (per config: CHANGELOG, README, task matrix, meetings index)
                                   -> (knowledge extraction -> _insights.yaml)
                                   -> (per config: action propagation, agenda management)
                                   -> (per config: task import to _tasks.yaml, dashboard refresh)
                                   -> (per config: check verticals -- suggest updates to living documents)

ops status:       /ops status -> scan *-ops-config -> report active + available configs

ops help:         /ops help -> print usage guide with skill correlation

update-skills:    /update-skills         -> fetch -> ancestor check -> pull -> symlink new
                  /update-skills status   -> scan repos + symlinks -> report
                  /update-skills check    -> audit symlinks -> report -> offer fixes
                  /update-skills install  -> clone -> add remotes -> symlink all

daily-dashboard:  /daily-dashboard              -> generic: scan cwd for dated files -> dashboard
                  /daily-dashboard acme      -> org mode: load config -> project discovery -> dashboard
                  /daily-dashboard YYMMDD       -> specific date dashboard + symlinks
                  (all modes)                   -> read _tasks.yaml -> display in Teamfokus

preparation:      /preparation david           -> find _contacts/david-*/ -> read history -> ask context -> generate briefing
                  /preparation erik 260219    -> specific contact + date -> preparation document

insights:         /insights reprocess _contacts/bob-smith -> read transcripts -> extract insights -> _insights.yaml
                  /insights reprocess all       -> scan all CHANGELOG.md folders -> batch extract
                  /insights reprocess since YYMMDD -> date-filtered batch extract
                  /insights scan-claude-md      -> scan CLAUDE.md files -> extract knowledge -> _insights.yaml
                  /insights compile             -> read edge_case/correction entries -> find patterns -> skill_pattern
                  /insights compile since YYMMDD -> compile only recent feedback
                  /insights propose             -> read skill_patterns -> generate SKILL.md proposals
                  /insights propose apply       -> apply proposal -> update SKILL.md + CHANGELOG
                  /insights status              -> scan _insights.yaml files -> report counts + evolution stats
                  /insights help                -> print usage guide

tasks:            /tasks                        -> show active tasks grouped by project/priority
                  /tasks add "description"      -> interactive task creation
                  /tasks done 5                 -> mark task complete -> move to history
                  /tasks import meeting.md      -> extract action items -> add to _tasks.yaml
                  /tasks weekly                 -> generate weekly review (completed, carried, blocked)

analytics:        /analytics                    -> vault overview (default)
                  /analytics overview           -> file counts, growth, distribution, busiest dates
                  /analytics skills             -> skill adoption over time, structured vs unstructured ratio
                  /analytics contacts           -> contact engagement timelines, network growth
                  /analytics backlog            -> unprocessed .txt files, missing insights, stale inbox
                  /analytics help               -> print usage guide
```

### Choosing the Right Skill

**Rule of thumb:** Use `/ops` for any meeting that belongs to a project or organization. Use `/transcript` for personal calls and ad-hoc recordings without an org context. When in doubt, use `/ops` -- it falls back gracefully when no config exists.

| Scenario | Skill |
|----------|-------|
| Meeting with org config (Acme, Bravo, etc.) | `/ops` |
| Standup, weekly sync, board meeting | `/ops` |
| Personal call, no org context | `/transcript` |
| Ad-hoc voice recording, quick summary only | `/transcript` |
| See what org configs are available | `/ops status` |
| Learn how /ops works and relates to other skills | `/ops help` |
| Prepare before a meeting | `/preparation` |
| Track action items across projects | `/tasks` |
| Review weekly task progress | `/tasks weekly` |
| Daily overview with meeting links and tasks | `/daily-dashboard` |
| Backfill insights for existing transcripts | `/insights reprocess` |
| Extract knowledge from CLAUDE.md files | `/insights scan-claude-md` |
| Check insight coverage across vault | `/insights status` |
| Compile execution feedback into patterns | `/insights compile` |
| Generate skill improvement proposals | `/insights propose` |
| Apply a skill improvement proposal | `/insights propose apply` |
| Update skills, check symlinks, install repos | `/update-skills` |
| Quick capture of unstructured content | `/inbox` |
| Don't know which skill to use | `/inbox` (classifies and routes for you) |
| Restore Swedish characters in hand-written docs | `/ops normalize <path>` |
| See vault-wide content trends and growth | `/analytics overview` |
| Understand which skills produce the most content | `/analytics skills` |
| See contact engagement frequency and timelines | `/analytics contacts` |
| Find unprocessed transcriptions or insight gaps | `/analytics backlog` |

### Daily Workflow Guide

A typical workday using the skill ecosystem. All steps are optional -- use what fits.

```
  MORNING                    BEFORE MEETING              MEETING              AFTER MEETING                 ONGOING
  ───────                    ──────────────              ───────              ─────────────                 ───────

  /daily-dashboard           /preparation <contact>      [Record/            /ops [transcript]             /tasks show
       │                          │                       take notes]        or /transcript [text]         /tasks done N
       ▼                          ▼                                               │
  Review today's             Briefing with context,                               ├── knowledge extraction
  meetings, tasks,           open items, agenda                                   │   -> _insights.yaml
  preparations               from previous calls                                  ├── task import offered
                                                                                  ├── preparation marked
                                                                                  │   superseded
                                                                                  └── dashboard refresh
                                                                                      (if configured)
```

#### Morning -- start of day

| Step | Skill | What you get |
|------|-------|-------------|
| 1 | `/daily-dashboard` (or `/daily-dashboard <org>`) | Overview: today's meetings, preparations, active tasks, quick-access symlinks |

#### Before each meeting

| Step | Skill | What you get |
|------|-------|-------------|
| 2 | `/preparation <contact> [date]` | Briefing with context from previous calls, open action items, suggested agenda, cross-references from other contacts |

#### After each meeting

| Step | Skill | When to use |
|------|-------|-------------|
| 3a | `/ops [transcript]` | Org meetings (standups, syncs, reviews) -- full processing with config-driven file updates |
| 3b | `/transcript [transcript]` | Personal calls, ad-hoc recordings -- lightweight summary |
| 3c | `/engagement-ops [content]` | Consulting engagements -- phase-aware documentation (bravo-skills) |
| 4 | Accept task import (offered by 3a/3b) | Action items flow into `_tasks.yaml`, show up in tomorrow's dashboard |

#### Throughout the day

| Skill | When |
|-------|------|
| `/tasks show` | Check what needs doing |
| `/tasks done N` | Mark completed items |
| `/tasks add "description"` | Capture ad-hoc tasks |
| `/cr create "title"` | Track a change request (bravo-skills) |

#### Connections that happen automatically

- `/daily-dashboard` discovers preparations and meeting files by filename pattern
- `/ops` marks earlier preparations as superseded
- `/ops` can refresh the dashboard after processing (when `post_processing.dashboard_refresh` is enabled)
- Both `/ops` and `/transcript` offer to import action items into `_tasks.yaml`
- Both `/ops` and `/transcript` silently extract durable insights to `_insights.yaml` (decisions, preferences, learnings, opportunities, patterns)
- `/daily-dashboard` reads `_tasks.yaml` and shows tasks in the "Teamfokus" section
- `/ops` checks configured verticals (living topic-longitudinal documents) for topic matches and suggests updates
- `/preparation` Step 2.5 scans other contact folders for **lateral** cross-references (last 60 days, mandatory with explained relevance per CR-005)
- `/preparation` Step 0 refuses to mutate prep files dated in the past -- mid-meeting notes go in the transcript file
- `/ops` writes a `*Preparation: [link]*` back-link in the meeting summary footer when superseding a prep file (bidirectional traceability per CR-005)

### Quick Start: After a Meeting

| You have... | Run | What happens |
|-------------|-----|-------------|
| Transcript from a Acme management meeting | `/ops [paste transcript]` | Summary in meetings/management/, CHANGELOG, task import, dashboard refresh |
| Notes from a marketing standup | `/ops [paste notes]` | Summary in meetings/marketing/, CHANGELOG updated |
| Recording from a personal call (no org) | `/transcript [paste transcript]` | Summary file + CHANGELOG in target folder |
| Nothing yet -- meeting is tomorrow | `/preparation david` | Briefing with context from previous conversations |
| Morning -- need today's agenda | `/daily-dashboard acme` | Dashboard with meetings, tasks, quick-access links |

### How Skills Work Together

#### Complete Skill Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SKILL INTERACTION MAP                              │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │  ops-config  │
                              │  (base.yaml) │
                              └──────┬───────┘
                                     │ provides defaults
                                     ▼
┌─────────────┐              ┌──────────────┐              ┌─────────────┐
│ preparation │──creates────▶│    Files     │◀────creates──│  transcript │
│             │              │              │              │  (lightweight│
│ YYMMDD-     │              │ _contacts/*/ │              │  no config) │
│ förberedelse│              │ meetings/    │              └──────┬──────┘
└─────────────┘              └──────┬───────┘                    │
                                    ▲                            │ writes
                                    │ creates (summary, CHANGELOG,│
                                    │ README, task matrix,        ▼
                                    │ meetings index)    ┌────────────────┐
                              ┌─────┴────────┐  writes   │ _insights.yaml │  writes
                              │     /ops     │─────────▶│ (per folder)   │◀─────────┐
                              │ (config-     │           └────────────────┘          │
                              │  driven)     │                  ▲              ┌─────┴────────┐
                              └──┬───────┬───┘                  │ writes       │  /insights   │
                                 │       │                      │              │  (backfill + │
                                 │       │                /transcript          │  CLAUDE.md)  │
                                 │       │                (Step 3.5)           └──────────────┘
                    task import  │       │  dashboard refresh
                                 ▼       ▼
                         ┌──────────────┐  ┌─────────────────┐
                         │    tasks     │  │ daily-dashboard │
                         │              │  │                 │
                         │ _tasks.yaml  │──▶ _Dashboard.md  │
                         │ _tasks-      │  └────────┬────────┘
                         │ history.md   │           │
                         └──────────────┘           │ creates
                                                    ▼
                                           ┌─────────────────┐
                                           │    Symlinks     │
                                           │ _TODAY-*, etc.  │
                                           └─────────────────┘

                                           ┌─────────────────┐
                                           │  /analytics     │
                                           │                 │
                                           │ reads ALL file  │
                                           │ metadata (names,│
                                           │ dates, paths)   │
                                           │                 │
                                           │ writes:         │
                                           │ _analytics/*.md │
                                           └─────────────────┘

Data Flow:
  ─────▶  creates/writes
  ──────▶ reads
  ─ ─ ─▶  optional (per config)
```

#### Meeting + Task Lifecycle (State Diagram)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MEETING + TASK LIFECYCLE                              │
└─────────────────────────────────────────────────────────────────────────────┘

State 1: PREPARATION
┌──────────────────────────────────────────────────┐
│ /preparation david                              │
│                                                  │
│ Input: Contact name + date                       │
│ Reads: Previous transcripts, CHANGELOG           │
│ Output: YYMMDD-förberedelse-*.md                │
│                                                  │
│ Dashboard: Shows in "Förberedelser" section     │
└──────────────────────────────────────────────────┘
                         │
                         ▼
                  [Meeting happens]
                         │
                         ▼
State 2a: /OPS (primary -- any org meeting)
┌──────────────────────────────────────────────────┐
│ /ops [content]                                   │
│                                                  │
│ Input: Transcript or notes                       │
│ Creates: Summary + per-config files              │
│   (CHANGELOG, README, task matrix, meetings idx) │
│ Post-processing: Task import + dashboard refresh │
│                                                  │
│ Dashboard: Shows in "Samtal/Möten" section       │
└──────────────────────────────────────────────────┘

State 2b: /TRANSCRIPT (lightweight -- personal/ad-hoc)
┌──────────────────────────────────────────────────┐
│ /transcript [content]                            │
│                                                  │
│ Input: Transcription text                        │
│ Creates: YYMMDD-samtal-*.md + CHANGELOG           │
│ Offers: Task import (Step 4)                     │
│                                                  │
│ Dashboard: Shows in "Samtal" (preparation hidden)│
└──────────────────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
State 3a: TASK IMPORT              State 3b: NO TASKS
┌─────────────────────┐            ┌─────────────────────┐
│ User accepts import │            │ User declines       │
│                     │            │                     │
│ Action items ->     │            │ Lifecycle ends      │
│ _tasks.yaml         │            │ (for this meeting)  │
│                     │            │                     │
│ Source: transcript  │            └─────────────────────┘
│ Status: pending     │
└─────────────────────┘
          │
          ▼
State 4: TASK TRACKING
┌──────────────────────────────────────────────────┐
│ /tasks (ongoing)                                 │
│                                                  │
│ /tasks show        - View active tasks           │
│ /tasks done N      - Complete task -> history    │
│ /tasks weekly      - Review progress             │
│                                                  │
│ Dashboard: Shows in "Teamfokus" section          │
└──────────────────────────────────────────────────┘
          │
          ▼
State 5: DASHBOARD VIEW
┌──────────────────────────────────────────────────┐
│ /daily-dashboard                                 │
│                                                  │
│ Aggregates:                                      │
│ - Meetings (from YYMMDD-*.md files)             │
│ - Tasks (from _tasks.yaml)                       │
│ - Completed (from _tasks-history.md)             │
│ - Priority links (from project matrices)         │
│                                                  │
│ Output: _Dashboard.md + symlinks                 │
└──────────────────────────────────────────────────┘
```

#### Data File Relationships

```
Vault Parent Directory (e.g., ~/Documents/User/)
│
├── _Dashboard.md              <- /daily-dashboard (generic)
├── _Dashboard-acme.md      <- /daily-dashboard acme
├── _tasks.yaml                <- /tasks, /ops (import), /transcript (import)
├── _tasks-history.md          <- /tasks done
├── _analytics/                <- /analytics (snapshots)
│   ├── YYMMDD-vault-overview.md
│   ├── YYMMDD-skill-adoption.md
│   ├── YYMMDD-contact-engagement.md
│   ├── YYMMDD-backlog-report.md
│   └── .archive/              <- older snapshots
│
├── acme/                   <- Project vault
│   ├── meetings/
│   │   ├── board/
│   │   │   └── 260220-samtal-Alex-Frank.md  <- /transcript
│   │   ├── management/
│   │   │   ├── 260224-Acme-Weekly-Management-Meeting.md  <- /ops
│   │   │   ├── CHANGELOG.md                                 <- /ops
│   │   │   └── _insights.yaml                               <- /ops, /transcript, /insights
│   │   └── marketing/
│   │       └── 260225-Grace-Alex-ppc-review.md              <- /ops
│   ├── ops/
│   │   └── management/
│   │       ├── priority-matrix.md   <- /ops
│   │       └── README.md            <- /ops
│   └── README.md                    <- /ops (meetings index)
│
└── _contacts/                  <- Contact folders
    └── david-ekberg/
        ├── 260220-förberedelse-samtal-Alex-David.md  <- /preparation
        ├── 260220-samtal-Alex-David.md               <- /transcript
        ├── CHANGELOG.md                                 <- both skills
        └── _insights.yaml                               <- /ops, /transcript, /insights
```

#### File discovery

`/daily-dashboard` finds files by scanning for `YYMMDD-*.md` patterns:

| Filename contains | Dashboard section | Produced by |
|-------------------|-------------------|-------------|
| `förberedelse` / `preparation` | Förberedelser | `/preparation` |
| `standup` / `daily-standup` | Standup/Projekt | `/ops` |
| Anything else (`samtal`, etc.) | Samtal/Möten | `/transcript`, `/ops` |

**Generic mode:** Scans cwd recursively. Works with `_contacts/` folders and `meetings/` directories.
**Org mode:** `/daily-dashboard acme` loads org config for project-specific paths and persistent symlinks.

#### Task flow

```
Source               Skill              Storage              Display
──────               ─────              ───────              ───────

Meeting          /transcript           _tasks.yaml      /daily-dashboard
action items  ───────────────────▶   (active tasks)  ─────────────────▶  Teamfokus
                   Step 4                                                 section

Meeting          /ops                  _tasks.yaml      /daily-dashboard
action items  ───────────────────▶   (active tasks)  ─────────────────▶  Teamfokus
                   Step 9                                                 section

Manual           /tasks add            _tasks.yaml      /daily-dashboard
entry        ───────────────────▶   (active tasks)  ─────────────────▶  Teamfokus
                                                                          section

Task             /tasks done        _tasks-history.md  /daily-dashboard
completion   ───────────────────▶   (append-only)   ─────────────────▶  Slutfört
                                                                         section
```

Note: `/ops` Step 9 can also trigger `/daily-dashboard` refresh automatically when `post_processing.dashboard_refresh` is enabled in the org config.

```
Knowledge Extraction (silent -- runs alongside task flow):

Source               Skill              Storage                     Display
──────               ─────              ───────                     ───────

Meeting          /transcript           _insights.yaml          core-skills-
summary      ───────────────────▶   (per folder,             visualisation
                   Step 3.5          alongside CHANGELOG)  ─────▶  /insights
                                                                    page
Meeting          /ops                  _insights.yaml
summary      ───────────────────▶   (per folder,
                   Step 5.5          alongside CHANGELOG)

Existing         /insights             _insights.yaml
transcripts  ───────────────────▶   (per folder,
                   reprocess         alongside CHANGELOG)

CLAUDE.md        /insights             _insights.yaml
files        ───────────────────▶   (per folder,
                   scan-claude-md    alongside CHANGELOG)
```

Knowledge extraction is deduped by source file, threshold-based (skips trivial conversations), and limited to 10 insights per meeting. `/insights reprocess` backfills from existing transcripts; `/insights scan-claude-md` extracts from CLAUDE.md files. `_insights.yaml` files are never read by any skill -- only by the visualisation app.

#### Config-driven strings

Section headers, annotations (`[UTFALL]`), and metadata labels are configurable via ops-config:

```yaml
# In your org config (e.g. acme.yaml):
strings:
  annotations:
    outcome: "[RESULTAT]"     # Override default [UTFALL]
  metadata:
    created: "Skapad"         # Override default "Dokument skapat"
```

Resolution: org config > language defaults (`strings_sv` / `strings`) > hardcoded fallback.

#### Knowledge Extraction (`_insights.yaml`)

`/ops` (Step 5.5) and `/transcript` (Step 3.5) silently extract durable knowledge from new conversations. `/insights` backfills from existing transcripts (`reprocess`) and extracts embedded knowledge from CLAUDE.md files (`scan-claude-md`). All three write to `_insights.yaml` -- a pure accumulation layer that never appears in any skill output. **Marvin** (formerly `core-skills-visualisation`, renamed per its CR-010) is the only consumer.

**What gets extracted:**

| Type | Captures | Example |
|------|----------|---------|
| `decision` | Choice + rationale | "Chose Flutter over native for shared codebase" |
| `preference` | Working style | "Prefers short standups over long weekly meetings" |
| `learning` | What worked/didn't | "Two-week sprints too long -- switch to weekly" |
| `opportunity` | Ideas not yet actioned | "Could build SaaS from internal tool" |
| `pattern` | Recurring themes | "Budget discussion deferred three meetings in a row" |

**Threshold:** Only non-obvious, durable, specific insights are extracted. Standups, trivial status updates, and conversations with no qualifying insights are silently skipped.

**File format:** Per-folder `_insights.yaml`, placed alongside `CHANGELOG.md`:

```yaml
version: 1
last_updated: 260303
context: "contact_or_project_name"

insights:
  - id: 1
    type: decision
    date: 260303
    summary: "Chose weekly sprints over two-week cycles"
    rationale: "Team feedback showed faster iteration improved morale"
    source:
      file: "260303-samtal-Alex-Bob.md"
      section: "Process decisions"
    tags: [sprints, process, team]
    status: active           # active | superseded | archived
    superseded_by: null

next_id: 2
```

**Deduplication:** Insights are deduped by `source.file` -- processing the same transcript twice does not create duplicate entries.

**Configuration:** `workflows.knowledge_extraction` in `base.yaml` controls behaviour (enabled by default, configurable types, max 10 per meeting).

**Data flow:**

```
Source                                    Storage               Consumer
──────                                    ───────               ────────

/transcript (Step 3.5)  ──┐
                          ├── _insights.yaml ──▶  Marvin (web dashboard)
/ops (Step 5.5)  ─────────┤   (per folder)          /insights page
                          │
/insights reprocess  ─────┤
                          │
/insights scan-claude-md ─┘
```

#### Skill Evolution (feedback loop)

Skills silently capture execution feedback (edge cases, user corrections) to `_insights.yaml` alongside content insights. The `/insights` skill compiles this feedback into patterns and proposes SKILL.md improvements.

```
Capture                        Compile                    Improve
───────                        ───────                    ───────

/transcript (Step 4.5) ──┐
                         ├── edge_case     /insights    skill_pattern    /insights     SKILL.md
/ops (Step 9)  ──────────┤   correction ──▶ compile ──▶ entries     ──▶  propose  ──▶ updated
                         │   entries        (on demand)                  (on demand    (manual or
                         │   in                                          or auto)      auto_apply)
                         │   _insights.yaml
                         │
                         └── source.skill field distinguishes from content insights
```

**Configuration:** `workflows.knowledge_extraction.evolution` in `base.yaml`:

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `true` | Capture execution feedback |
| `auto_apply` | `false` | Auto-apply proposals to SKILL.md |
| `compile_threshold` | `3` | Min occurrences to compile a pattern |
| `propose_threshold` | `5` | Min occurrences to generate a proposal |

**Execution feedback types:**

| Type | Captures | Written by |
|------|----------|------------|
| `edge_case` | Ambiguous input, disambiguation needed | `/transcript` Step 4.5, `/ops` Step 9 |
| `correction` | User corrected or overrode output | `/transcript` Step 4.5, `/ops` Step 9 |
| `skill_pattern` | Compiled recurring pattern | `/insights compile` |

Proposals are stored in `docs/proposals/` and applied via `/insights propose apply`.

#### CHANGELOG entries

Each skill adds its own CHANGELOG entry when saving to a contact folder:

```
- **YYMMDD: Förberedelse samtal David** - Diskussionspunkter... -> [file.md]
- **YYMMDD: Samtal Alex-David** - Huvudämnen... -> [file.md]
```

Two entries per meeting event (preparation + transcript) is intentional -- they represent different lifecycle stages.

#### Cross-project task correlation

Tasks in `_tasks.yaml` are tagged with `project`:

```yaml
tasks:
  - id: 1
    task: "Review contract"
    project: acme          # <- project tag
    tags: [legal, urgent]
    source:
      file: "acme/meetings/board/260220-meeting.md"
    ...

  - id: 2
    task: "Update website copy"
    project: bravo              # <- different project
    tags: [marketing]
    source:
      file: "bravo-projects/meetings/260218-sync.md"
    ...
```

**Viewing:**
- `/tasks show` -- all projects
- `/tasks show acme` -- filter by project
- `/daily-dashboard acme` -- shows only `project: acme` tasks

**Privacy:**
- `private: true` -- never shown in shared views
- `private: false` -- appears in team dashboards

---

### Adding a New Organization (v1.16.0+, CR-011)

1. `cp ~/.claude/skills/ops-config/base.yaml <vault>/<org>/_ops.yaml`
2. Set `organization`, `language`, `team`, `responsibility_matrix`, `terminology`
3. Configure `workflows` (which files to update, action propagation)
4. Done -- `/ops` finds it automatically when CWD is anywhere under `<vault>/<org>/`. No skill repo, no SKILL.md, no symlink.

The config syncs with the vault (iCloud/Obsidian Sync), so editing on one machine propagates everywhere.

---

## Installation

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed

### Quick start

Clone the repo anywhere you like, then create one symlink:

```bash
# Clone to any directory (~/Projects, ~/src, /opt, etc.)
git clone https://github.com/your-username/core-claude-skills.git core-skills

# Create the bootstrap symlink
mkdir -p ~/.claude/skills
ln -s "$(pwd)/core-skills/skills/update-skills" ~/.claude/skills/update-skills
```

Then in Claude Code, run `/update-skills update` -- it creates all remaining symlinks automatically.

### Updating

```
/update-skills update
```

Or manually: `cd /path/to/core-skills && git pull` (symlinks pick up changes automatically).

### Adding a new skill

1. Create `skills/new-skill/SKILL.md` (required) and optionally `README.md`
2. Run `/update-skills update` to create the symlink, or manually: `ln -s /path/to/core-skills/skills/new-skill ~/.claude/skills/new-skill`
3. Commit and push
