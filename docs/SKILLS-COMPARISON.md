# Skills: comparison and interaction

Reference for choosing between the skills and seeing how they hand off to each
other. Split out of the README in v1.55.1, where it was 713 of 993 lines and
buried everything else.

**For how a project actually runs**, see the README — this document answers
*which skill*, not *what happens when*.

The suite is ten user-invocable skills and two shared modules (`ops-base`,
`ops-config`) that `/ops` loads. All ten are in the overview; `inbox` and
`handoff` are detailed in their own `SKILL.md`.

- [Overview](#overview)
- [What They Share (via ops-base)](#what-they-share-via-ops-base)
- [Skill Details](#skill-details)
- [Workflow Comparison](#workflow-comparison)
- [Choosing the Right Skill](#choosing-the-right-skill)
- [Daily Workflow Guide](#daily-workflow-guide)
- [Quick Start: After a Meeting](#quick-start-after-a-meeting)
- [How Skills Work Together](#how-skills-work-together)

---

## Overview

| Skill | Organization | Language | Files Updated | Domain Focus |
|-------|--------------|----------|---------------|--------------|
| `inbox` | Any | Input language | _inbox/ (capture + classify) | Universal content capture |
| `preparation` | Any | Swedish/input | 1-2 | The agenda, config-free form of `/ops prepare` |
| `transcript` | Any | Input language | 1-2 + tasks + insights | The summary, config-free form of `/ops process` |
| `ops` | Any (config-driven) | Per config | Per config (1-5) + insights | Meetings, standups, ops |
| `outbox` | Any | Input language | _outbox/ + _contacts/<contact>/ | Outgoing material lifecycle |
| `tasks` | Any | Input language | 2 (_tasks.yaml + history) | Personal task tracking |
| `handoff` | Any | Input language | .handoff/ (frozen snapshots) | Context for a different work session |
| `insights` | Any | Input language | _insights.yaml (per folder) | Retroactive knowledge extraction |
| `analytics` | Any | Swedish/input | _analytics/ (snapshots) | Vault-level content metrics |
| `update-skills` | Any | English | 0 (manages symlinks/repos) | Skill repo management |

Rows follow the registry order in `ecosystem.yaml`, which is the order of the working loop.
Organization-specific skills extend `ops-base` and live in their own repos.

## What They Share (via ops-base)

All domain skills inherit from `ops-base`:

- **Priority system:** P0 (critical) through P3 (research)
- **Status indicators:** BLOCKED, IN PROGRESS, ON TRACK, TODO, COMPLETE
- **Meeting formats:** Two-tier summary (Concise vs Detailed Strategic)
- **Template contracts (CR-018):** per-meeting-type shape contracts checked before every save -- heading order, action-table columns, empty-decision marker. Format changes happen by editing the contract, never by silent drift.
- **Task lifecycle:** Creation > Active > Post-meeting > Archive
- **CHANGELOG format:** Standardized entry structure
- **Archive policy:** Never delete, always archive to `.archive/`
- **Retirement convention (CR-019):** relocating any living artifact leaves a tombstone pointer at the old path -- migrations never leave live-looking corpses
- **Slug contract (CR-021):** filenames keep å/ä/ö, always `YYMMDD-` prefixed, always carry a machine-readable role keyword
- **Cross-referencing:** Link standards for meetings, tasks, changelogs

## Skill Details

### transcript (standalone)

- **Purpose:** Universal extraction layer -- the config-free form of `/ops process`
- **Output:** The summary (`YYMMDD-summary-*.md`) + CHANGELOG, `_insights.yaml` (knowledge extraction)
- **Format (CR-006, v1.15.3):** Action-first canonical structure -- Nästa steg → Beslut → Konklusion → Diskussion → Bakgrund. Beslut section is mandatory (write `*(Inga formella beslut)*` if empty). 5-column task table. Three template variants by meeting length (Concise / Standard / Extended).
- **Special:** Provides structured YAML extraction for domain skills. Step 3.5 silently extracts durable insights (decisions, preferences, learnings, opportunities, patterns) to `_insights.yaml`.
- **Operations:** `/transcript [content]` (paste text or provide file path), `/transcript --concise`, `/transcript --extended`, `/transcript help`
- **Use when:** Processing any transcript without domain-specific formatting

### ops (config-driven)

- **Purpose:** Unified meeting and operations processing
- **Output:** Configurable -- the summary only (default), or up to 5 files (summary, CHANGELOG, README, task-priority-matrix, meetings/README), plus optional post-processing (task import to `_tasks.yaml`), plus `_insights.yaml` (knowledge extraction)
- **Config-driven:** Summary sections, status terms, domain additions, action propagation, agenda management, post-processing, knowledge extraction, verticals all controlled by config
- **Replaces:** project-ops, bravo-ops, management-ops, marketing-ops
- **Operations:** `/ops process <content>` (the default -- `/ops <content>` does the same), `/ops prepare [type]` (writes the agenda), `/ops orient <folder>` (CR-061, was `brief` -- read-only: where a project stands before work resumes), `/ops check <folder>` (CR-018, was `lint` -- find where a meeting series' format forked), `/ops check` (CR-019/023/025, was `sweep` -- read-only closure/staleness audit across nine debt classes; `--vault <scope>` for a subtree), `/ops project list` (was `projects`), `/ops project new <name>`, `/ops normalize <path>` (CR-007 -- restore Swedish characters; `--names` applies the people roster, CR-017; `--filenames` fixes slug drift, CR-021), `/ops status` (includes each project's resolved config), `/ops help`
- **Use when:** Any meeting type -- standups, management meetings, marketing reviews, business syncs. The default choice -- use `/transcript` only when you explicitly don't want config machinery.

### update-skills (standalone)

- **Purpose:** Skill repo management and maintenance
- **Output:** No files created in projects -- manages symlinks and git state
- **Operations:** update, status, check, install, help
- **Special:** Multi-remote version safety (ancestor check before pull), symlink health auditing, auto-discovery of repos via symlink scanning
- **Use when:** Updating skills to latest, setting up a new machine, checking symlink health, installing new skill repos

### preparation (standalone)

- **Purpose:** Structured meeting preparation from contact history, optimised for walk-in usability -- the config-free form of `/ops prepare`
- **Output:** The agenda, `YYMMDD-agenda-*.md` (optionally CHANGELOG). Older files named `förberedelse`/`preparation` are never renamed and are still read.
- **Operations:** `<contact name> [date]`, `help`
- **Format (CR-005, v1.15.2):** Two-tier structure -- 60-second walk-in card on top (agenda + open actions), deep dives below the fold separated by a horizontal rule. Agenda items use a 5-tag system (`[DECISION]`/`[DEMO]`/`[STATUS]`/`[QUESTION]`/`[FYI]`, Swedish: BESLUT/DEMO/STATUS/FRÅGA/FYI) and must be questions or deliverables, not noun phrases. Maximum 5 items in the walk-in card -- prioritised by criticality.
- **Special:** Step 0 frozen-prep check refuses mid-meeting edits to past-dated agendas. Step 2.5 cross-reference scan is mandatory with explained relevance -- bare links forbidden. Single-document principle: an agenda may not require reading another agenda. Background moves to bottom (reference, not navigation). Bidirectional supersede linkage when `/ops` processes the meeting transcript.
- **Use when:** Preparing for an upcoming call or meeting with a contact

### tasks (standalone)

- **Purpose:** Personal task tracking with cross-project correlation
- **Output:** `_tasks.yaml` (active tasks), `_tasks-history.md` (completed log)
- **Operations:** `list` (default, was `show`), `add`, `done`, `import`, `weekly`, `archive`, `help`
- **Special:** Central index at vault parent, source linking to meetings, privacy model (`private: true/false`), project tagging, automatic carry-forward. Integrates with `/transcript` and `/ops` (import).
- **Use when:** Tracking tasks from meetings, managing personal tasks across projects, reviewing weekly progress

### insights (standalone)

- **Purpose:** Retroactive knowledge extraction from existing corpus + the compile half of the knowledge loop
- **Output:** `_insights.yaml` (per folder, same format as transcript Step 3.5)
- **Operations:** `reprocess [target]`, `scan-claude-md`, `compile`, `migrate [path] [--apply]` (CR-020, was `normalize` -- migrate drifted/legacy files to the current schema, dry-run default), `synthesize [topic]`, `propose`, `propose apply`, `status`, `help`
- **Special:** Backfills insights from historical transcripts and CLAUDE.md files. Dedup by `source.file` -- safe to run repeatedly. Does not duplicate extraction logic -- references `/transcript` Step 3.5 as authoritative source. `compile` runs the CR-013 lifecycle (hypothesis → rule promotion, contradiction demotion) and stamps `last_compiled` so synthesis staleness is detectable (CR-020). Names are allowed in entries; prefer name-free summaries when an insight generalizes (CR-020 reusability note).
- **Use when:** Setting up insights for a folder that predates the knowledge extraction feature, extracting embedded knowledge from CLAUDE.md files, running the periodic compile pass, or migrating pre-schema insight files

### analytics (standalone)

- **Purpose:** Vault-level content analytics — longitudinal trends, not daily snapshots
- **Output:** `_analytics/YYMMDD-*.md` snapshot files (overview, skill-adoption, contact-engagement, backlog-report)
- **Operations:** `overview` (default), `skills`, `contacts`, `pipeline`, `backlog`, `help`
- **Special:** Reads file metadata only (names, dates, paths) — never file contents. Path-first classification avoids keyword miscount. Privacy-aware via `_meta.yaml`. Historical snapshots archived automatically.
- **Use when:** Understanding vault growth trends, tracking skill adoption, analysing contact engagement patterns, finding unprocessed content

### outbox (standalone, v1.16.3)

- **Purpose:** Lifecycle management for outgoing material staged in `<vault>/_outbox/`
- **Output:** No new files -- moves outbox folders into `_contacts/<contact>/YYMMDD-<theme>/` and updates manifest, CHANGELOG, `_tasks.yaml`
- **Operations:** `list` / `status` (default -- classifies items as PENDING / RESOLUTION-READY / DRAFT / WITHOUT MANIFEST), `close <folder>` (was `archive` -- move + update references), `close --all-sent` (CR-019 -- close every sent item in one batch, selection confirmed up front), `help`
- **Special:** Reads `_manifest.md` as canonical state file -- an item is "resolution-ready" when `Status: skickad ...` AND all `Svar förväntas på` are checked AND `Utfall` is populated. Strips the contact-name prefix from the folder name when closing (it's redundant inside the contact's own folder). Multi-contact fan-out (ambassador-style) prompts the user for duplicate-vs-shared-archive strategy. Never auto-completes tasks. Searches vault for stray references to the old path and rewrites them.
- **Use when:** An outbox item has been sent, replied to, and resolved -- and the central `_outbox/` should be cleaned up. Or use `list` to audit what's pending.

## Workflow Comparison

```
transcript:       Input -> Summary -> CHANGELOG -> (knowledge extraction -> _insights.yaml)
                                 -> (offer task import)

ops:              Input -> Summary -> (per config: CHANGELOG, README, task matrix, meetings index)
                                   -> (knowledge extraction -> _insights.yaml)
                                   -> (per config: action propagation, agenda management)
                                   -> (per config: task import to _tasks.yaml)
                                   -> (per config: check verticals -- suggest updates to living documents)

ops status:       /ops status -> scan <vault>/*/_ops.yaml -> report active + available configs,
                                 each project's resolved config

ops orient:       /ops orient <folder> -> read-only: loop position, carry-forward, archives, outbox -> report

ops check:        /ops check <folder> -> check files vs template contracts -> report series forks by date
                  /ops check          -> 9 closure-debt checks (indexes, ledgers, corpses, outbox,
                                         duplicates, residue, triage, contract alignment,
                                         structure conformance) -> report + offered fixes

ops project:      /ops project list   -> which folders are projects, which are just material
                  /ops project new    -> create a project, then register it

ops help:         /ops help -> print usage guide with skill correlation

update-skills:    /update-skills         -> fetch -> ancestor check -> pull -> symlink new
                  /update-skills status   -> scan repos + symlinks -> report
                  /update-skills check    -> audit symlinks -> report -> offer fixes
                  /update-skills install  -> clone -> add remotes -> symlink all

preparation:      /preparation david           -> find _contacts/david-*/ -> read history -> ask context -> the agenda
                  /preparation erik 260219     -> specific contact + date -> the agenda

insights:         /insights reprocess _contacts/bob-smith -> read transcripts -> extract insights -> _insights.yaml
                  /insights reprocess all       -> scan all CHANGELOG.md folders -> batch extract
                  /insights reprocess since YYMMDD -> date-filtered batch extract
                  /insights scan-claude-md      -> scan CLAUDE.md files -> extract knowledge -> _insights.yaml
                  /insights compile             -> read edge_case/correction entries -> find patterns -> skill_pattern
                                                   + hypothesis→rule promotion + last_compiled stamp
                  /insights compile since YYMMDD -> compile only recent feedback
                  /insights migrate [--apply]   -> migrate drifted/legacy _insights.yaml to current schema (dry-run default)
                  /insights synthesize [topic]  -> cluster corpus semantically -> wiki articles + INDEX.md (read-first, no RAG)
                  /insights propose             -> read skill_patterns -> generate SKILL.md proposals
                  /insights propose apply       -> apply proposal -> update SKILL.md + CHANGELOG
                  /insights status              -> scan _insights.yaml files -> report counts + evolution stats
                  /insights help                -> print usage guide

tasks:            /tasks list                   -> active tasks grouped by project/priority (the default)
                  /tasks add "description"      -> interactive task creation
                  /tasks done 5                 -> mark task complete -> move to history
                  /tasks import meeting.md      -> extract tasks -> add to _tasks.yaml
                  /tasks weekly                 -> generate weekly review (completed, carried forward, blocked)

analytics:        /analytics                    -> vault overview (default)
                  /analytics overview           -> file counts, growth, distribution, busiest dates
                  /analytics skills             -> skill adoption over time, structured vs unstructured ratio
                  /analytics contacts           -> contact engagement timelines, network growth
                  /analytics pipeline           -> input -> meeting docs -> outcomes chain, ratios, per-day averages
                  /analytics backlog            -> unprocessed .txt files, missing insights, stale inbox
                  /analytics help               -> print usage guide
```

## Choosing the Right Skill

**Rule of thumb:** Use `/ops` for any meeting that belongs to a project or organization. Use `/transcript` for personal calls and ad-hoc recordings without an org context. When in doubt, use `/ops` -- it falls back gracefully when no config exists.

| Scenario | Skill |
|----------|-------|
| Meeting with config (Acme, Bravo, etc.) | `/ops` |
| Standup, weekly sync, board meeting | `/ops` |
| Personal call, no org context | `/transcript` |
| Ad-hoc voice recording, quick summary only | `/transcript` |
| See what configs are available | `/ops status` |
| Learn how /ops works and relates to other skills | `/ops help` |
| Prepare before a meeting (the agenda) | `/ops prepare`, or `/preparation` without config |
| See where a project stands before work resumes | `/ops orient <folder>` |
| List which folders are projects | `/ops project list` |
| Track tasks across projects | `/tasks list` |
| Review weekly task progress | `/tasks weekly` |
| Answer a knowledge question ("what have I learned about X?") | Read `.knowledge/INDEX.md` first, then only the relevant wiki article(s) |
| Render the insights corpus into wiki articles + index | `/insights synthesize` |
| Backfill insights for existing transcripts | `/insights reprocess` |
| Extract knowledge from CLAUDE.md files | `/insights scan-claude-md` |
| Check insight coverage across vault | `/insights status` |
| Compile execution feedback into patterns | `/insights compile` |
| Generate skill improvement proposals | `/insights propose` |
| Apply a skill improvement proposal | `/insights propose apply` |
| Update skills, check symlinks, install repos | `/update-skills` |
| Quick capture of unstructured content | `/inbox` |
| Drop a file (PDF/CSV/media) for processing into the vault | `/inbox <file path>` (lands in `_inbox/.files/`) |
| Park disposable scratch that should never enter the vault | `.ephemeral/` (swept after 14 days) |
| Find stray/variant inbox-outbox folders in the tree | `/ops check` (check 9) |
| Don't know which skill to use | `/inbox` (classifies and routes for you) |
| See what's pending in the outbox | `/outbox list` |
| Close a sent-and-replied outbox folder into the contact folder | `/outbox close <folder>` |
| Close everything already sent in one batch | `/outbox close --all-sent` |
| Audit the vault for staleness and closure debt | `/ops check` (`--vault <scope>` for a subtree) |
| Find where a recurring meeting's format silently forked | `/ops check <folder>` |
| Refresh the daily triage doc (week anchor, done-archive) | `/inbox triage refresh` |
| Migrate old/drifted `_insights.yaml` files to the current schema | `/insights migrate` |
| Apply the canonical-name roster to a folder's files | `/ops normalize --names <folder>` |
| Fix Swedish-character drift in filenames | `/ops normalize --filenames <folder>` |
| Restore Swedish characters in hand-written docs | `/ops normalize <path>` |
| See vault-wide content trends and growth | `/analytics overview` |
| Understand which skills produce the most content | `/analytics skills` |
| See contact engagement frequency and timelines | `/analytics contacts` |
| Find unprocessed transcriptions or insight gaps | `/analytics backlog` |

## Daily Workflow Guide

A typical workday using the skill ecosystem. All steps are optional -- use what fits.

```
  MORNING                    BEFORE MEETING              MEETING              AFTER MEETING                 ONGOING
  ───────                    ──────────────              ───────              ─────────────                 ───────

  /ops orient <folder>       /ops prepare or             [Record/            /ops process [transcript]     /tasks list
  /tasks list                /preparation <contact>       take notes]        or /transcript [text]         /tasks done N
       │                          │                                               │
       ▼                          ▼                                               ├── knowledge extraction
  Where a project            The agenda: context,                                 │   -> _insights.yaml
  stands, active tasks       open items, carry-forward                            ├── task import offered
  (read-only)                from previous calls                                  └── agenda marked
                                                                                      superseded
```

### Morning -- start of day

| Step | Skill | What you get |
|------|-------|-------------|
| 1 | `/ops orient <folder>` | Read-only: where a project stands before work resumes -- loop position, whether the next agenda exists, carry-forward items, archive freshness, staged outbox items |
| 1b | `/tasks list` | Active tasks grouped by project and priority |

### Before each meeting

| Step | Skill | What you get |
|------|-------|-------------|
| 2 | `/ops prepare [type]`, or `/preparation <contact> [date]` without config | The agenda: context from previous calls, open tasks, suggested agenda items, cross-references from other contacts |

### After each meeting

| Step | Skill | When to use |
|------|-------|-------------|
| 3a | `/ops process [transcript]` | Org meetings (standups, syncs, reviews) -- full processing with config-driven file updates |
| 3b | `/transcript [transcript]` | Personal calls, ad-hoc recordings -- the summary without config |
| 3c | `/engagement-ops [content]` | Consulting engagements -- phase-aware documentation (bravo-skills) |
| 4 | Accept task import (offered by 3a/3b) | Tasks flow into `_tasks.yaml` and show up in `/tasks list` |

### Throughout the day

| Skill | When |
|-------|------|
| `/tasks list` | Check what needs doing |
| `/tasks done N` | Mark completed items |
| `/tasks add "description"` | Capture ad-hoc tasks |
| `/cr create "title"` | Track a change request (bravo-skills) |

### Connections that happen automatically

- `/ops` marks earlier agendas as superseded
- Both `/ops` and `/transcript` offer to import tasks into `_tasks.yaml`
- Both `/ops` and `/transcript` silently extract durable insights to `_insights.yaml` (decisions, preferences, learnings, opportunities, patterns)
- `/ops orient` and `/ops check` find agendas and summaries by filename role keyword (`agenda`, `summary`), and still read older files named `förberedelse`/`preparation`/`samtal`
- `/ops` checks configured verticals (living topic-longitudinal documents) for topic matches and suggests updates
- `/preparation` Step 2.5 scans other contact folders for **lateral** cross-references (last 60 days, mandatory with explained relevance per CR-005)
- `/preparation` Step 0 refuses to mutate agendas dated in the past -- mid-meeting notes go in the transcript file
- `/ops` writes a `*Preparation: [link]*` back-link in the summary footer when superseding an agenda (bidirectional traceability per CR-005)

## Quick Start: After a Meeting

| You have... | Run | What happens |
|-------------|-----|-------------|
| Transcript from an Acme management meeting | `/ops process [paste transcript]` | The summary in meetings/management/, CHANGELOG, task import |
| Notes from a marketing standup | `/ops process [paste notes]` | The summary in meetings/marketing/, CHANGELOG updated |
| Recording from a personal call (no org) | `/transcript [paste transcript]` | The summary + CHANGELOG in target folder |
| Nothing yet -- meeting is tomorrow | `/preparation david` | The agenda, with context from previous conversations |
| Morning -- where does a project stand? | `/ops orient acme` | Read-only state: loop position, carry-forward items, archives, staged outbox items |

## How Skills Work Together

### Complete Skill Interaction Diagram

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
│             │              │              │              │ (no config) │
│ YYMMDD-     │              │ _contacts/*/ │              │ the summary │
│ agenda-*    │              │ meetings/    │              └──────┬──────┘
└─────────────┘              └──────┬───────┘                    │
                                    ▲                            │ writes
                                    │ creates (summary, CHANGELOG,│
                                    │ README, task matrix,        ▼
                                    │ meetings index)    ┌────────────────┐
                              ┌─────┴────────┐  writes   │ _insights.yaml │  writes
                              │     /ops     │─────────▶│ (per folder)   │◀─────────┐
                              │ (config-     │           └────────────────┘          │
                              │  driven)     │                  ▲              ┌─────┴────────┐
                              └──────┬───────┘                  │ writes       │  /insights   │
                                     │                          │              │  (backfill + │
                                     │                    /transcript          │  CLAUDE.md)  │
                                     │                    (Step 3.5)           └──────────────┘
                        task import  │
                                     ▼
                             ┌──────────────┐
                             │    tasks     │
                             │              │
                             │ _tasks.yaml  │
                             │ _tasks-      │
                             │ history.md   │
                             └──────────────┘

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

### Meeting + Task Lifecycle (State Diagram)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MEETING + TASK LIFECYCLE                              │
└─────────────────────────────────────────────────────────────────────────────┘

State 1: PREPARATION
┌──────────────────────────────────────────────────┐
│ /preparation david                               │
│                                                  │
│ Input: Contact name + date                       │
│ Reads: Previous transcripts, CHANGELOG           │
│ Output: the agenda, YYMMDD-agenda-*.md           │
└──────────────────────────────────────────────────┘
                         │
                         ▼
                  [Meeting happens]
                         │
                         ▼
State 2a: /OPS (primary -- any org meeting)
┌──────────────────────────────────────────────────┐
│ /ops process [content]                           │
│                                                  │
│ Input: Transcript or notes                       │
│ Creates: The summary + per-config files          │
│   (CHANGELOG, README, task matrix, meetings idx) │
│ Post-processing: Task import                     │
└──────────────────────────────────────────────────┘

State 2b: /TRANSCRIPT (lightweight -- personal/ad-hoc)
┌──────────────────────────────────────────────────┐
│ /transcript [content]                            │
│                                                  │
│ Input: Transcript text                           │
│ Creates: YYMMDD-summary-*.md + CHANGELOG         │
│ Offers: Task import (Step 4)                     │
└──────────────────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
State 3a: TASK IMPORT              State 3b: NO TASKS
┌─────────────────────┐            ┌─────────────────────┐
│ User accepts import │            │ User declines       │
│                     │            │                     │
│ Tasks ->            │            │ Lifecycle ends      │
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
│ /tasks list        - View active tasks           │
│ /tasks done N      - Complete task -> history    │
│ /tasks weekly      - Review progress             │
└──────────────────────────────────────────────────┘
          │
          ▼
State 5: ORIENT (before the next meeting)
┌──────────────────────────────────────────────────┐
│ /ops orient <folder>                             │
│                                                  │
│ Read-only. Reports:                              │
│ - Loop position (newest summary, next agenda)    │
│ - Chain integrity + carry-forward items          │
│ - Archive freshness, staged outbox items         │
│ - Most recent CHANGELOG entry                    │
└──────────────────────────────────────────────────┘
```

### Data File Relationships

```
Vault Parent Directory (e.g., ~/Documents/User/)
│
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
│   │   │   └── 260220-summary-Alex-Frank.md  <- /transcript
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
        ├── 260220-agenda-Alex-David.md               <- /preparation
        ├── 260220-summary-Alex-David.md              <- /transcript
        ├── 260113-samtal-Alex-David.md               <- older file, legacy keyword, still read
        ├── CHANGELOG.md                                 <- both skills
        └── _insights.yaml                               <- /ops, /transcript, /insights
```

### File discovery

Readers find meeting files by the role keyword in `YYMMDD-<role>-<description>.md` (CR-021, CR-089):

| Filename role keyword | What it is | Produced by | Read by |
|-----------------------|------------|-------------|---------|
| `agenda` (older: `förberedelse`, `preparation`) | The agenda | `/ops prepare`, `/preparation` | `/ops process` (supersede), `/ops orient`, `/ops check` |
| `facilitator` | The facilitator sheet (dual-mode prepare) | `/ops prepare` | `/ops process` (supersede) |
| `summary` (older: `samtal`, `sammanfattning`, `möte`) | The summary | `/ops process`, `/transcript` | `/ops orient`, `/ops check`, `/ops project list` |

The keyword is English in every language; the description part keeps å/ä/ö. Older files are never renamed -- every reader accepts the legacy keywords, so a folder mixing `samtal` and `summary` files reads as one series. A `note_suffix` / `agenda_suffix` declared in config wins over the default keyword.

### Task flow

```
Source               Skill              Storage              Display
──────               ─────              ───────              ───────

Meeting          /transcript           _tasks.yaml      /tasks list
tasks         ───────────────────▶   (active tasks)  ─────────────────▶  grouped by
                   Step 4                                                 project/priority

Meeting          /ops                  _tasks.yaml      /tasks list
tasks         ───────────────────▶   (active tasks)  ─────────────────▶  grouped by
                   Step 9                                                 project/priority

Manual           /tasks add            _tasks.yaml      /tasks list
entry        ───────────────────▶   (active tasks)  ─────────────────▶  grouped by
                                                                          project/priority

Task             /tasks done        _tasks-history.md  /tasks weekly
completion   ───────────────────▶   (append-only)   ─────────────────▶  completed
                                                                         section
```

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

### Config-driven strings

Section headers, annotations (`[UTFALL]`), and metadata labels are configurable via ops-config:

```yaml
# In your config (e.g. acme.yaml):
strings:
  annotations:
    outcome: "[RESULTAT]"     # Override default [UTFALL]
  metadata:
    created: "Skapad"         # Override default "Dokument skapat"
```

Resolution: config > language defaults (`strings_sv` / `strings`) > hardcoded fallback.

### Knowledge Extraction (`_insights.yaml`)

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
      file: "260303-summary-Alex-Bob.md"
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

### Skill Evolution (feedback loop)

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

### CHANGELOG entries

Each skill adds its own CHANGELOG entry when saving to a contact folder:

```
- **YYMMDD: Förberedelse samtal David** - Diskussionspunkter... -> [file.md]
- **YYMMDD: Samtal Alex-David** - Huvudämnen... -> [file.md]
```

Two entries per meeting event (agenda + summary) is intentional -- they represent different lifecycle stages.

### Cross-project task correlation

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
- `/tasks list` -- all projects
- `/tasks list acme` -- filter by project

**Privacy:**
- `private: true` -- never shown in shared views
- `private: false` -- appears in shared views

---
