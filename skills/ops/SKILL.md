---
name: ops
description: Process meeting content into structured documentation -- summaries, decision tracking, action propagation, file updates. Config-driven for any organization. Replaces project-ops, bravo-ops, management-ops, marketing-ops.
user-invocable: true
argument-hint: [status | help | prepare [type] | normalize <path> | lint <folder> | sweep | meeting content, transcript, or standup notes]
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
   - From the detected vault root, scan for stray inbox/outbox directories using the **CR-025 fuzzy matcher** (same as `/ops sweep` check 9): `_inbox`, `_outbox`, `.inbox`, `.outbox`, any `*inbox*`/`*outbox*` directory, and localized forms (`inkorg*`/`utkorg*`), case-insensitive, skipping `.archive/`/`.transcripts/`/`.handoff/`/`clones/`/`node_modules/`. Anything other than `<vault>/_inbox` and `<vault>/_outbox` is a stray; flag each unless listed in `workflows.sweep.structure_exemptions` (exempt paths get a one-line note with their reason). Exact-name matching is not enough -- real-world strays have appeared as `.inbox` and `_outbox-archive`.
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

**Render the working loop from `working_loop` in `ecosystem.yaml` — do not restate it here.** That block
is the declaration both the README and the landing page render; a hand-written fourth copy in a help
command is the one most likely to go stale **and the least likely to be caught**, because a help command
is read precisely by people who cannot tell that it is wrong.

**Render orientation FIRST, from `orientation` in `ecosystem.yaml` (CR-077) — do not restate it
here either.** A person who types `help` is more often lost in the substrate than in the sequence:
where to start a session, what the folders are, what is in the context window. Present the entries
in declared order, each as its `question` then its `answer`, under a heading that marks them as
orientation rather than commands. Then the loop.

**Include:**

0. The orientation entries, in declared order
1. One-line description of what /ops does
2. Available commands: `/ops [content]`, `/ops prepare [type]`, `/ops brief <folder>`, `/ops status`,
   `/ops lint <folder>`, `/ops sweep`, `/ops normalize <path>`, `/ops help`
3. **The working loop, grouped by `phase` in declared order.** Per step:
   - the `label` and what it `does`
   - **`command`** where the step has one — the thing a person actually types
   - **`consumes` → `produces`**, because the question after *which command* is always *what does it
     need and what do I get*, and the declaration already holds both
   - where a step is `manual`, show its **`why_manual` in place of a command**. That substitution is the
     most useful line in the output: it tells the reader nothing is missing
   - where a step is `external`, say so — the archivers and the meeting itself are not skills
4. Config loading summary (3-line version, point to `/ops status` for details)
5. Common usage patterns (examples including prepare)

**Output:** Markdown printed directly. No files created, and nothing is executed — `/ops help` describes
the loop, it never runs a step.

**The declaration is checked** (`check-components.py`): a step cannot be both `manual` and commanded,
cannot be silent about being neither, and cannot name a vault path nothing declares. So a command that
drifts fails the check rather than misleading a reader.

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
- The lead's expectations from prior handover or 1-on-1s
- Time-box discipline cues ("standup has run 25 min recently, target 30, hard stop 35")
- "Watch for" cues during the meeting (e.g., "Dana defaulting to 'I'll check after standup' on R2 blockers -- push for concrete commitment now")
- "Things NOT to surface in this forum" list (vertical/board topics, personnel matters, etc.)
- Decisions the facilitator owns and the framing for each (esp. when filling in for someone)
- Post-standup follow-ups the facilitator drives
- Pre-meeting backstory from 1-on-1s or lunches with subset of attendees

**Critical rule:** the agenda file does NOT mention or hint at the facilitator file. The visible document must not advertise that a private one exists. Cross-references go from facilitator → agenda only, not the other direction.

**Critical rule:** if the same content fits both files, it goes in the agenda file. The facilitator file should only contain content that would change behaviour or expose sensitive context if shared with the team.

---

#### Step P0: Which agenda does this project use? (CR-082)

**Run this before P1, and print the answer before writing anything.**

Resolve `carry_forward` through the normal config chain (`config()` in `build_agenda.py` —
nearest declaration wins, walking up).

| `carry_forward.enabled` | The agenda comes from |
|---|---|
| **true** — the loop is wired | **`build_agenda.py`.** The template in P3 is NOT used for the agenda |
| absent or **false** | P1–P5 as described below |

**When the loop is wired:**

```bash
python3 ~/.claude/skills/ops/build_agenda.py --dir <project>/meetings [--date YYMMDD]
```

It writes `YYMMDD-<agenda_suffix>.md` and the chat post, carrying what the transcript cannot:
the carried-forward block with session counts, the round from the declared roster, and the
*Since the last standup* block from the archives. **Hand-writing the agenda in a wired project
silently drops all three** — the agenda looks complete and is missing the half that comes from
outside the room.

In **dual** mode the facilitator file is still written here, as a layer **on top of** the
generated agenda: read the generated file, add only facilitator content. Never regenerate the
agenda's own content into it.

**Stop if a session was recorded and never written up (CR-087).** Where the folder declares
`external_systems.transcripts`, a recording newer than the newest note means a session happened and
left no note. The next agenda is built from that note, so building now **drops the session
entirely** — re-raising what it closed and carrying none of what it opened. Process it first, or pass
`--skip-unprocessed` so that skipping is a decision on the record rather than an accident.

**Check for an existing preparation before writing (CR-086).** Glob the target folder and its
siblings for a preparation, agenda or facilitator file matching this meeting's **date and
participants**. If one exists, report it and offer: open it, regenerate it from current sources, or
write anyway. `build_agenda.py` already refuses to overwrite an agenda; the hand-prepared path had no
equivalent, and a second prep for the same meeting is indistinguishable from the first until someone
opens both.

**Announce the path before saving** — which route was taken (generated or template) and the
exact filenames to be written. A hand-written agenda in a wired project then cannot happen
silently; it is the one outcome the run states out loud.

---

#### Step P1: Gather Context

1. **Load org config** (same as normal /ops flow)
2. **Read recent meetings:**
   - Find last 1-3 meeting summaries in the target folder
   - Extract action items assigned to each team member
   - Note decisions made, blockers identified
3. **Read the task ledger** (resolve `workflows.task_ledger` first -- see ops-base, CR-040):
   - `local`: pull active tasks per person from `_tasks.yaml` (status: pending, in_progress, blocked)
   - `external`: read the declared `pointer` if it is reachable; otherwise state in the prep that open
     work lives in `system` and was not read. **Never fall back to an ancestor `_tasks.yaml`**
   - Identify blockers and their owners
4. **Read CHANGELOG.md:**
   - Scan recent entries for context
5. **Triage scan (CR-022):** if the vault has a registered triage doc (`_inbox/` working document, `type: working_doc` + tag `do-not-process`), pull open bullets whose bracket-tag second segment resolves to this meeting's participants (`[Möte · X]`, `[Uppföljning · X]`, ...) into the prep's agenda/open-actions, and stamp each pulled bullet `→ i prep YYMMDD` -- the only write allowed to the triage doc (same rule as `/preparation` Step 2.4). Skip silently when no doc or no matches.

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
| `--names` | (CR-017) Instead of Swedish characters, normalize person names: apply the org `people[]` roster (aliases → canonical) across the target's `.md` files and CHANGELOG. Reports each substitution for confirmation before writing; never runs implicitly. |
| `--filenames` | (CR-021) Instead of file content, normalize filenames against the slug contract (restore å/ä/ö, fix digit-transliterations like `m0te`, unify date prefix to YYMMDD). Dry-run lists `old → new`; on apply, renames AND updates inbound references found in the same tree (CHANGELOG.md, README.md, supersede stamps, wikilinks). |

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

### `projects` -- which folders are pipelines, and which are just material (CR-065)

**Trigger:** `/ops projects` · `python3 ~/.claude/skills/ops/list_projects.py [--root <vault>]`

**Read-only.** A folder under a projects tree may be a running loop or a pile of transcripts, and from
the outside they are indistinguishable — same depth, same naming, several with a CHANGELOG and a
`meetings/` folder. Measured on one vault: **40 project-shaped folders, 5 configured, 4 with the loop
wired.**

Grouped by how far each is wired, because **the grouping is the answer**:

| Group | Means |
|---|---|
| **Loop wired** | `carry_forward` declared — `/ops brief` and `build_agenda.py` work here |
| **Configured, no loop** | `/ops` processes meetings; agenda and carry-forward do not apply |
| **Material only** | No config. Notes, transcripts, documents — **not a pipeline, and often correctly so** |
| **Empty or dormant** | No config, no dated notes, no changelog |

Per row: dated meeting count and **when the record last moved** — read from the changelog where there is
one, because *a changelog entry is a deliberate act and an mtime is whatever a sync did last*.

**A series IS its meetings folder; a project HAS one (CR-072).** Both counts read the subfolder when it
exists and the folder itself when it does not. Reading only the subfolder reported folders holding
dated notes directly as having none and as never having moved — on one vault, three folders sat in
*empty or dormant* while one of them had been written to four days earlier.

**A recurring series declares itself.** A weekly that lives in a meetings tree rather than under
`_projects/` is invisible to a scan that only knows the project trees, however completely its loop runs.
A top-level `series:` block opts the folder in:

```yaml
series:
  name: <what the series is called>
  cadence: weekly          # shown in the listing
```

**Declared, never inferred** — every folder carrying an org config would otherwise read as a series,
including the org root. The declaration does two things: it brings the folder into the scan, and it
**licenses resolving `carry_forward` up the config chain**, because a series inherits its loop from an
ancestor config and reading only its own file reports a running loop as *no loop*.

**The chain walk is not applied to project folders**, deliberately. An org-level `carry_forward` block
is typically written for one named series — its `note_suffix` names that series — so letting every
sibling project inherit it would report loops that do not exist. That is the CR-067 failure in the
opposite direction, and over-reporting a loop is worse than under-reporting one: the agenda it promises
is never generated and nobody finds out until an item has fallen through.

**The cadence is shown because escalation thresholds are counted in sessions.** `escalate_after: 3` is
three weeks on a weekly and three months on a quarterly. The number means nothing without it.

**It does not replace a project registry.** A hand-written registry carries **intent** — what a person
is driving, with status and sponsor — and is authoritative for it. *"What am I driving"* and *"what is
wired"* are different questions, and answering the first from the second would drop every idea, dormant
effort and discussion topic that correctly runs nowhere. This command links to the registry rather than
restating it.

**Pairs with `/ops brief`:** projects is wide and shallow, brief is one project deep.

---

### `project new <name>` -- create a project, then register it (CR-086)

**Trigger:** `/ops project new <name> [--from-meeting <summary>] [--pre-phase-of <project>/<track> --exit "<criterion>"] [--graduates <plan>#<row>]`

**`/ops projects` stays read-only.** A read-only command that sometimes writes is harder to trust
than two commands, and that guarantee is why the existing one is safe to run without thinking.

#### Step N1: Check before creating

Refuse if the folder exists. **Glob for near-names and ask** — a project created under a second
spelling is invisible to everything that looks for the first, and the two then accumulate material
in parallel.

#### Step N2: Scaffold five artefacts

In the organisation's projects tree, resolved from config:

| File | Content |
|---|---|
| `README.md` | Roles line, `STARTING` + creation date, cadence, language; a *Scope / Out of scope* table; a *Meetings* table |
| `_ops.yaml` | Organisation, language, `people[]` **seeded from the organisation roster with its aliases — never re-typed**, workflows, optional `carry_forward` |
| `_tasks.yaml` | v2 header, empty `tasks:` |
| `CHANGELOG.md` | Header plus a "Project created" entry |
| `meetings/` | Empty |

A hand-copied roster is where a misspelling enters and then resolves to nobody.

**`--from-meeting`**: the first CHANGELOG entry and the README's meetings row point at that summary.

**`--pre-phase-of <project>/<track> --exit "<criterion>"`**: writes the pre-phase block into the
README — what blocks the parent track today, the exit criterion, and that the flow hands over when it
is met — plus a note in `_ops.yaml` naming the **parent's** register as the source of open questions.
A pre-phase that keeps its own register is a second register for one body of work.

> This is a README convention, not a declared lifecycle. There is one known instance of the shape, and
> a lifecycle declared on a single case is a guess. If a second appears wanting the same three parts
> (exit criterion, handover, tombstone), that earns its own CR.

#### Step N3: Register it — declared, never hardcoded

```yaml
registry:
  projects:
    - path: <register file>        # vault-root portfolio, or an organisation index
      section: <table heading>
      mode: propose | write
  structure_docs:
    - <file whose folder tree lists projects>
```

**Declared at both layers and merged by the config chain.** A vault may hold a cross-venture
portfolio at its root and a per-organisation index inside each organisation; both are registers a new
project must appear in. A project in an organisation that declares an index gets two rows; one in an
organisation that declares none gets the portfolio row only. **An organisation without an index is
not misconfigured** — it has one register.

**`mode: propose` is the default for a hand-written register.** Show the row, write on confirmation.

| The skill fills | Left for a person, marked |
|---|---|
| Name, venture, type, status (`New <date>`) | The owner's role, sponsor/mode, where it runs |

The division is about what can be **known**, not about effort. A role column can legitimately contain
a question — an owner writing *"contributing?"* about their own involvement is recording an open
question, and a skill filling that cell would turn a question into an assertion. Judgement columns are
written as marked placeholders, so an unfilled one is visible rather than merely empty.

**Idempotent.** If a row for this project already exists — another session got there — verify the link
and do nothing else. This is what makes two sessions harmless rather than merely unlikely.

**Unconfigured means skip, silently.**

#### Step N4: Graduation (`--graduates <plan>#<row>`)

Annotate the row **in place** — *moved to `<project>` on `<date>`; linked, not copied, the row stays as
history* — in **every** plan that carries it, and seed the new README's background from the row.

The golden rule made executable: one item, one owner, one document. A row copied rather than linked
becomes two rows that disagree within a week.

---

### `brief` -- where a recurring project stands, before work resumes (CR-061)

**Trigger:** `/ops brief <folder>` · `python3 ~/.claude/skills/ops/project_brief.py --dir <folder>/meetings`

**Read-only. Writes nothing, fetches nothing, judges nothing.**

`/ops status` reports which *config* applies. `/ops sweep` audits closure debt across a vault. This
reports one folder's **current state** — the question a session asks when it opens a project cold and
would otherwise rebuild the answer from four files, losing whatever nobody wrote down.

Six blocks, each reading files that already exist — preceded, when there is one, by **Fetch problems**
(CR-088): any declared source whose archive `_fetch.json` records a result other than `ok`, reported
once, first. An expired login is the usual way a scheduled archive goes stale and the one thing in the
brief only a person can fix; re-running the fetch does nothing.


1. **Loop position** — newest note, next session, **whether that agenda exists yet.** The common failure
   is not a missing note but a missing next agenda, and nothing else surfaces it.
2. **Chain integrity** — whether the newest note ends with `## Carried forward`. The one failure in the
   loop that announces nothing: without it the next agenda carries zero items and looks correct.
3. **What is carrying** — each item with sessions, age and owner. `UNOWNED` is counted and named,
   because an item nobody is named against is the one that falls through an agenda that lists it.
4. **Archive freshness** — newest snapshot per declared chat and repository, and each archive's fetch
   record (`fetched 07:00 ok`, `fetch failed 06:30: login required`, or `fetch not recorded`). **A stale
   archive is worse than none:** retrieval still produces a block and it reads as current. The snapshot
   says how old the data is; the fetch record says whether that is because nothing happened.
5. **Staged, not sent** — `_outbox/` folders naming this project whose status is not sent, with age. A
   file in a meetings folder carries no status; this is the only place an unsent item shows.
6. **Record movement** — the changelog's most recent entry. *When did anyone last write this project
   down*, not *when was a file touched*.

**It is `/bod` for a coordination project**, and the parallel is deliberate: both read state before work
begins and neither writes. The expensive mistake is not doing the wrong work — it is doing the right
work against a picture that was true yesterday.

A folder with no `post_processing` block still gets blocks 1, 5 and 6.

---

### `lint` -- Check existing files against template contracts (CR-018)

**Trigger:** `/ops lint <folder>`

Read-only version of the CR-018 pre-save template-contract check, run across a folder's existing files. Use it to detect **template forking in a recurring series** -- the drift class where each file is internally consistent but the series silently changed shape at some point.

**Steps:**

1. Resolve the contract registry (`workflows.meeting_templates` from the merged config; `default` = CR-006 canonical).
2. For each `YYMMDD-*.md` meeting summary in the folder (skip preps, agendas, emails, `.archive/`): resolve its contract by `match` glob and run the three checks (heading sequence, action-table header row, empty-Beslut marker).
2b. **`agenda_suffix` names the project (CR-082).** Where `carry_forward` is declared, check that
   `agenda_suffix` contains the project's folder slug. A default or generic suffix
   (`agenda-daily-standup`) produces filenames that say nothing about where they came from — and an
   agenda leaves its folder routinely: staged in `_outbox/`, attached to a chat post, forwarded.
   Report it with the rename as the offered fix; **never rename implicitly**
   (`/ops normalize --filenames` stays the only route, and existing files are left alone).
3. **Group findings by series and by first-deviating date** -- the output should read "this series forked at YYMMDD", not a flat per-file list:

2c. **The roster matches who actually attends (CR-084).** Compare `people[]` with the participant
   lines of the last N notes and report two mismatches: **present every time but not in the roster**
   (they have no row in the round, so nothing they carry is ever routed to them), and **in the roster
   but absent every time** (suggest `adjacent: true`, which keeps the name for resolution and takes
   the row out of the round). **Report only** — the roster is the project's to change, and a skill
   editing who belongs in a room is not a lint fix.

2d. **Carried items name something the team can find (CR-084).** Flag a carried line whose only
   identifier is vault-local — a register id that exists in coordination notes and nowhere the team
   works. Such an item leads the agenda and is skipped every session, because the person who owns it
   cannot resolve what it refers to. Every carried line should reference an issue, a ticket, a path in
   the repo, a chat message or a session — or state the matter in plain words.

```
/ops lint meetings/management

weekly-management (14 files checked):
  OK through 260519. Forked at 260526:
  - action_table: missing column "Prio" (260526, 260605, 260702 -- 3 files)
  - heading "Sammanfattning" (banished) prepended (same 3 files)
  1-on-1 files (22 checked): all OK.

To accept the new shape: declare it in workflows.meeting_templates.
To fix the files: edit manually or re-run /ops on the source transcripts.
```

4. **Never rewrites files.** Lint reports; the user decides between amending the contract (accept the fork as deliberate) and fixing the files.

5. **Carry-forward chain check** -- only where `workflows.post_processing.carry_forward.enabled`.

   For each `YYMMDD-<note_suffix>.md` in the folder, check the note ends with a `## Carried forward`
   section. **This is the one failure in the meeting loop that is silent.** A note missing the section
   does not error, does not warn, and produces a next agenda with zero carried items that looks
   perfectly correct — the chain ends and the output stays plausible. Every other defect in the loop
   announces itself.

   Report the **break**, not the file count — the chain is what matters:

   ```
   /ops lint <project>/meetings

   carry-forward chain (5 notes checked):
     Chain intact 260916 -> 260919. BROKEN at 260921:
     - 260921-daily-standup.md has no "## Carried forward" section
     - so 260922's agenda was generated from 260919 and is 2 sessions stale

     260918: section present but empty
       -- "nothing carried" is a real answer; say it in the section rather than omitting it.
   ```

   **An empty section is a finding, not an error.** A day where nothing carried is legitimate and worth
   recording; an *omitted* section is indistinguishable from a day nobody wrote up. Only the omission
   breaks the chain.

   **A reappearing item keeps its count.** The counter counts *appearances*, not consecutive ones — an
   item carried on the 16th, dropped from the 19th and carried again on the 21st is on its third
   session, not its first. An earlier version broke on the first absence, which let a genuinely stuck
   item hide indefinitely by skipping every third session.

   Two rules make that safe. **A note with no carry-forward section is skipped, not counted as an
   absence** — that note says nothing about any item, and reading its silence as *resolved* is the same
   mistake in a different place. And an item missing for more than `MAX_GAP` sessions (default 2) is
   treated as a **fresh raise**, because *carried in March, back in September* is a new problem wearing
   an old name.

   **Gaps are reported, not hidden** — `3 · skipped 1`. A gap has two readings that look identical from
   here: a note that dropped the item by mistake, or an item resolved and later re-raised. Only a person
   can tell them apart, so the count stands and the ambiguity is shown.

---

### `sweep` -- Closure/staleness audit (CR-019)

**Trigger:** `/ops sweep [scope]` (default scope: vault root; depth 6; skip `.archive/`, `.transcripts/`, `.handoff/`, `clones/`, `node_modules/`, `.ephemeral/`)

Skills append reliably but never reconcile: indexes lag, ledgers rot, migrations leave live-looking corpses, sent outbox items never get archived. Bookkeeping follows attention, not structure -- so nothing catches the abandoned lane until a human stumbles on it. `/ops sweep` is the missing sweeper: one read-only pass that detects the closure-debt classes and **offers** fixes (report-only by default; every fix is confirmed, never automatic).

**The nine checks:**

1. **Index lag** -- README.md / meetings/README.md whose newest referenced date lags the folder's newest `YYMMDD-*` file or CHANGELOG head entry by >14 days. CHANGELOGs are the heartbeat; READMEs are the lag indicator -- compare them per folder.
2. **Ledger rot** -- `_tasks.yaml` with open tasks whose `last_updated` lags folder activity by >30 days; `_insights.yaml` whose `last_compiled` stamp is absent or >30 days older than its newest entry (compile never ran / is stale).
   **Resolve the ledger mode first (CR-041).** Read `workflows.task_ledger.mode` before judging a missing `_tasks.yaml`:
   - `local` (default): as above, unchanged.
   - `external`: the rot check is **skipped and replaced by two others** -- (a) **incoherent declaration**: `system` or `pointer` absent, or the pointer unresolvable; that is the real failure mode for this shape, and it is silent otherwise. (b) **The duplicate the declaration exists to prevent**: a folder declaring `external` that nonetheless contains a `_tasks.yaml`. Report both as findings with the same weight as rot.
   - `none`: skip.
   `_insights.yaml` staleness is checked in **every** mode -- the knowledge layer is local regardless of where the work is tracked.
   Rationale worth keeping in the report: a *declared* absence is deliberate, an *undeclared* one is indistinguishable from neglect. Reporting a correctly-configured folder as broken every week is worse than not checking it -- the first time the sweep is right and nobody believes it, the check has stopped working.
3. **Migration corpses** -- artifacts that look live but were superseded by a move: root symlinks/files whose same-purpose counterpart elsewhere is fresher (dashboards, `_TODAY-*`); folders inactive >60 days whose participant/topic stream demonstrably continues in a sibling folder. Offered fix: a **tombstone** (see ops-base Retirement Convention).
4. **Outbox aging** -- run the `/outbox list` logic: sent-but-unarchived items, manifest-less items, **manifests missing `Kanonisk källa` (CR-032)**, and items pending >30 days. Offered fix: `/outbox archive --all-sent`. The `Kanonisk källa` finding matters because without it nobody can tell whether a folder is a disposable rendering or the only copy of the material -- which is what made a bulk clean-up unsafe in the 260828 audit (86 items, 3 of 71 manifests named a source).
5. **Sync duplicates** -- `* 2.*` / `* 3.*` files whose base file exists. Report size+mtime comparison side by side; **never auto-delete** (the larger "duplicate" is sometimes the newer content).
6. **Unrouted residue** -- `unsorted/` folders with files >30 days old; `.ephemeral/` content >14 days old; root-level files matching paste conventions (`__*`, `xxx -*`, `Namnlös*`, untitled).
7. **Triage hygiene (CR-022)** -- if a triage doc is registered: INKORG items unsorted >7 days, `[x]` items not yet moved to the KLART archive, week anchor >7 days stale, plaintext-credential-looking lines (no-secrets rule; lines marked `<!-- secret-ok -->` are a recorded owner decision and are skipped). Offered fix: `/inbox triage refresh` (which handles all but the sorting -- that stays human).
8. **Contract alignment & repo privacy (CR-023/CR-029)** -- if `workflows.sweep.alignment_check.command` and/or `workflows.sweep.privacy_scan.command` are configured (maintainer machines only; **absent → skip silently**): run each command (read-only by construction) and parse its `[OK]`/`[DRIFT]`/`[FINDING]`/`[SKIP]` verdict lines. The privacy scan watches the whole public-repo tree continuously — denylist identifiers, secret patterns, and name-like tokens missing from the invented-examples allowlist — so a leak that somehow lands is caught within a week, not at the next audit. Report each `[DRIFT]` component with expected-vs-actual version and a pointer to the update runbook (documented in the alignment script's header). **`[SKIP]` is reported as *unverified*, not clean** -- an unreachable component (e.g. a stale mount) is itself a finding, and has previously hidden six releases of drift. Never auto-applies fixes: cross-repo version references and live deploys are human-confirmed changes. The alignment command stays the single source of truth for the component list; the sweep is the scheduled reader that guarantees its output is actually seen.
9. **Structure conformance (CR-025)** -- enforce the CR-010 single-inbox/outbox rule with a **fuzzy matcher**, because reality drifts through variants that exact-name checks miss: scan for directories matching `_inbox`, `_outbox`, `.inbox`, `.outbox`, any `*inbox*`/`*outbox*`, and localized forms (`inkorg*`/`utkorg*`), case-insensitive. Everything except the vault-root `_inbox/` + `_outbox/` pair is a finding -- **including empty scaffolds** (they re-seed the habit). Paths in `workflows.sweep.structure_exemptions` are skipped with a one-line `(exempt: <path> -- <reason>)` note: deliberate exceptions are recorded once and respected. Offered fixes (never auto-applied): merge pending items into the central folder *via the normal `/inbox`/`/outbox` flows* so manifests and indexes stay true; archive already-resolved material to its destination folder; delete empty scaffolds; or add a `structure_exemptions` entry if the exception is deliberate. Rationale worth repeating in the report: a second outbox means the central pending list lies.

10. **Unregistered project (CR-086)** -- a folder carrying an `_ops.yaml` but **no row in any register declared under `registry:`** is a finding, with the proposed row as the offered fix. This is what catches a project created before `/ops project new` existed, or created by hand after it. Registers are resolved through the normal config chain, so both a vault-root portfolio and a per-organisation index count; **a vault that declares no register skips this check silently** rather than reporting every project. Never auto-applies: a hand-written register carries judgement columns (role, sponsor, mode) the sweep cannot fill, and a row proposed with those blank is the point -- it shows what is missing instead of inventing it.

**Output:** one report grouped by class, each finding with its offered fix as a command or concrete action. End with a one-line scoreboard (`9 classes: 5 clean, 3 with findings (14 items), 1 skipped`) so repeat runs are comparable. Young folders are exempt via the age thresholds -- a fresh project reports nothing.

**Wiring:** suitable for a weekly scheduled run that drops its report into `_inbox/` as a triage item (closing the loop through the existing daily-triage habit). The sweep itself never mutates content.

---

## THE DAILY LOOP, END TO END

What actually runs, in order, for a recurring series. **Three of these steps are not `/ops`**, and two
are deliberately not automated at all — those are the interesting ones.

### Before the meeting

**0. `/ops brief` — where did this leave off?** One read-only pass: loop position, whether the next
agenda exists, chain integrity, **whether a session was recorded and never written up** (CR-087), what
is carrying and what is unowned, how stale the archives are, what is staged and unsent. Run it when picking a project up cold, before deciding what the session is for.

**1. Refresh the archives — external CLIs, not skills.**

```
<the chat archiver>     ->  <venture>/.teamschats/        (CR-047)
<the repo archiver>     ->  <venture>/.githubmeta/   (CR-055)
```

Both are local CLIs run on demand, each authenticated in its own right. **No skill fetches.** A skill
reads what an archiver wrote, which is why an agenda can be generated with no credential and no
connectivity — see Step 9, Pre-Meeting Retrieval.

**2. Generate the agenda.**

```
python3 ~/.claude/skills/ops/build_agenda.py --dir <project>/meetings [--date YYMMDD]
```

Reads the previous note's `## Carried forward`, counts consecutive sessions per item, and pulls the
*Since the last standup* block from both archives. Refuses to overwrite an existing agenda.

**`/ops prepare` in a wired project runs exactly this** — see `prepare`, Step P0. There is one way
to make an agenda here, not two.

**3. `prepare` drafts the facilitator sheet; the facilitator owns it.** (CR-082)

The agenda carries facts; the sheet turns them into questions, and which question to ask is judgement.
The sheet also holds person-axis material — who to draw out, what is likely to be avoided — which is
precisely what must never be staged anywhere it could be sent.

**A draft is judgement offered, not judgement made.** `prepare` in dual mode writes it as a layer on
top of the generated agenda; the facilitator then edits it, and the edit is the point. What must not
happen is the sheet being treated as finished output — it is the one artifact in this loop whose value
comes from a person having disagreed with it.

### After the meeting, the same day

**4. Choose the transcript source. List, then let a human pick.**

Two recordings of one meeting is the normal case, not the exception — one per capturing tool, differing
in length and speaker resolution. Present `document_id`, title, duration and transcript variant with a
recommendation; **do not choose.** Record the chosen id in the note, so the record says which recording
it came from.

**5. `/ops` — one pass produces the note, the registers and one CHANGELOG line.**

Step 9 then runs post-processing as configured. **The note ends with `## Carried forward`** — that
section is what tomorrow's agenda is built from, so a note without it silently ends the chain.
`/ops lint` checks that chain; it is the only defect in this loop that does not announce itself.

**6. The recap is offered, not written** — see Step 9, *Generate Post-Meeting Recap*. Say what it would
carry and wait to be asked. It is the one artifact that leaves the building; assembled automatically
from the narrowest of the three inputs it is confidently incomplete, and invisibly so to readers who
have no transcript to check it against.

**7. `/outbox` — stage it, and let the manifest carry the send record.**

```
_outbox/YYMMDD-<recipient>_<subject>/     _manifest.md + the recap
```

**The `Status` field is the only record that a recap was actually posted.** A human sends it and marks
it sent; nothing writes that unprompted, because the click is where the posted message gets read.

### What each step must not do

| Step | Must not |
|---|---|
| Retrieval | Fetch. It reads archives; refreshing them is the archivers' job |
| Agenda | Be hand-edited, or overwrite an existing one |
| Facilitator sheet | Be staged in `_outbox/`, or be sent as drafted without a facilitator having edited it |
| Transcript | Be chosen by the machine when duplicates exist |
| Recap | Be written unasked, or keep a second copy outside `_outbox/` |
| Manifest status | Be advanced by a tool |

### Where it is manual, and why

**Steps 3, 4 and 6 stay in human hands, and should.** The facilitator sheet is judgement
about people — drafted by `prepare` (CR-082) but never finished by it;
choosing between duplicate transcripts is a judgement the machine cannot make honestly;
and the recap is asked for rather than produced. None of the three is an unbuilt feature.

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
| `workflows.meeting_templates` | Per-meeting-type shape contracts + lint mode (`warn`/`strict`) -- see ops-base Template Contracts (CR-018) |
| `workflows.post_processing` | Task import, dashboard refresh, optional priorities artifact (`priorities_artifact.enabled`), **recap on request** (`recap_artifact.enabled`), and **carry-forward -> next agenda** (`carry_forward.enabled`, see `build_agenda.py`) after meeting |
| `workflows.rolling_plans` | Participant-triggered per-axis living planning docs (update after a matching 1-on-1) |
| `domain_additions` | Extra sections to add to summaries |
| `templates` | Custom template paths |
| `strings` | i18n string overrides |

---

## PROCESSING FLOW

### Step 0.5: Load Applicable Rules (CR-013)

Before parsing the input, load any promoted **rules** from the `_insights.yaml` chain in scope:

1. **Walk up from CWD** collecting `_insights.yaml` files at each level (max depth 6, skip `.archive/`, `.handoff/`, `clones/`).
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
  - Match against org config `people[]` roster (canonical, aliases) for recurring non-contact persons (CR-017)
  - Match against org config `team[]` (name, aliases) for internal team
  - Match against `_contacts/*/_meta.yaml` (display_name, aliases) for external contacts
  - Use resolved canonical names in output (correct spelling, Swedish characters)
  - **Committed-spelling consistency (CR-017):** before saving the summary AND before writing CHANGELOG/README entries, run the folder-precedent near-miss check from `/transcript` ("Committed-spelling consistency" section) -- compare draft names and anomalous proper nouns against the target folder's recent files and CHANGELOG; use the established spelling when it resolves, flag both forms when it doesn't, never silently introduce a spelling variant. CHANGELOGs are how misspellings propagate; this check gates them too.
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
| `task_yaml` | _tasks.yaml | Update/create per-folder task file (v2 schema). **Skipped entirely when `workflows.task_ledger.mode` is not `local` (CR-040)** |
| `meetings_index` | meetings/README.md | Add entry to meeting index |

For `changelog`, follow the format in ops-base. Always reference the meeting summary file.

### What the skill does, and what a project configures (CR-084)

Printed by `/ops help` and `/ops brief` for the active project, so the split is visible rather than
remembered. A second user of this skill needs to know which half is theirs.

| The skill — the same for every project | The project — its config and templates |
|---|---|
| The sources block, the status block, and their order | Which chats, repositories and ticket boards are declared |
| The carry-forward check against the sources | `people[]`, with `track` and `adjacent` |
| Ordering by age; handing the track on | `round_columns` |
| The lint checks (roster, vault-only ids, suffix) | Track names and the taxonomy behind them |
| — | Recap and chat-post templates |

**`people[].track`** is the person's default track — used only when the previous note does not
already carry one. `areas` is a different thing and is never read as a track: an area is what
somebody works on, a track is the axis the round runs along.

### Step 5.4: Archive the Raw Source (silent, always) (CR-085)

**Run the RAW SOURCE ARCHIVE contract in `ops-base`.** Same definition `/transcript` Step 2.5 runs —
`.transcripts/<summary-stem>-raw.md`, frontmatter plus verbatim input, the `Råmaterial:` back-link in
the summary, one confirmation line, the read-back lock, and the skip conditions.

**Do not restate the contract here.** `/ops` is documented as a superset of `/transcript` and went
without this step precisely because the contract lived in one skill instead of the shared base.

Where the input came from a transcript store rather than pasted text, record the store's **document
id**, original filename, duration and transcript variant — the id is what ties the archive to the
recording rather than merely proving something was said.

**One session, several folders:** one raw file for the input, `summaries:` listing each summary it
fed, `disposition:` stating the split. A part routed to a frozen snapshot is named there and never
linked.

### Step 5.5: Knowledge Extraction (silent)

After updating files, scan the meeting summary for durable insights worth accumulating. This step writes to `_insights.yaml` in the same folder as the CHANGELOG -- it is a silent accumulation layer that never surfaces in any skill output.

**Same extraction logic as `/transcript` Step 3.5** (insight types, threshold, format, dedup). See the transcript skill for the full `_insights.yaml` schema and extraction criteria.

**Reusability (CR-020):** Names are allowed in insight entries (the former no-names privacy rule is retired). Prefer name-free phrasing in `summary`/`tags` when the insight generalizes -- `context` and `source.file` carry the who/what; names in `rationale` are always fine. Apply the write-time vocabulary guard from `/transcript` Step 3.5 (canonical types only, `confidence` = `hypothesis|rule`, YYMMDD dates, integer ids, max 5 tags).

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
4. **Template-contract check (CR-018):** resolve the meeting's shape contract from `workflows.meeting_templates` (most specific `match` wins, else `default` = CR-006 canonical) and verify heading sequence, action-table header row, and empty-Beslut marker before saving. `mode: warn` (default): save + report the diff + log `edge_case`; `mode: strict`: ask first. See ops-base "Template Contracts" for the full rule. Deliberate format changes are made by editing the contract, not by letting a file drift.
5. Include suggested CHANGELOG entry
6. Include cross-references to related documents
7. Include next steps or follow-up items

### Step 9: Post-Processing

If `workflows.post_processing` is configured:

#### Task Import (if `task_import.enabled`)
1. Extract action items from the meeting summary (same logic as /transcript Step 4)
2. **Resolve the task ledger (CR-040)** before anything else:
   - `mode: local` (default): find the local `_tasks.yaml` in the folder where the meeting summary was saved (or nearest ancestor). Create with v2 schema if missing.
   - `mode: external`: **no ledger file is read, created, or walked to.** Steps 3-6 below do not apply. Instead, present the extracted action items split in two -- those whose next action is implementation (recorded **by reference** in the summary using `reference_field`, e.g. a CR id or issue key, and offered to the user to raise in `system` if no reference exists yet), and those whose next action is a decision, an owner or an escalation (offered to the folder's declared coordination surface). State the system of record once in the summary so a reader of that file alone can find the work.
   - `mode: none`: action items stay in the summary; no import is offered.
3. Match extracted items against existing tasks -- update status/notes for tasks mentioned
4. Present NEW action items and offer to import (yes/no/select)
5. For imported tasks: assign defaults (P1, source = meeting file, context from folder)
6. Mark completed items from the meeting in the local _tasks.yaml
7. **Triage target for personal items (CR-022):** when an action item is personal/ad-hoc (owned by the user, no natural org/project folder) and the vault has a registered triage doc, offer "lägg i triage-INKORG" as an alternative target -- append the item as an open bullet under INKORG with a source link to the meeting file. One item = one home: it goes to the triage doc OR a `_tasks.yaml`, never both.

#### Pre-Meeting Retrieval (if `external_systems` is declared)

**A transcript only carries what was said out loud in the room.** Decisions posted to the chat, issues
opened or closed overnight, a document linked at 07:23 — none of it reaches the record, and most of it
never comes up in the meeting either. Observed 2026-09-21: a QA lead posted the agreed browser and
device matrix to the series chat hours before the standup; it appears in no transcript.

**Retrieve before generating the agenda and the facilitator sheet, not after.**

Sources come from **`external_systems`** (CR-054, contract 16) — resolved by the normal config chain,
`.claude/ops-config.yaml` then the folder's `_ops.yaml`. **Do not invent a second key for this.**

```yaml
external_systems:
  chats:
    - id: "19:meeting_...@thread.v2"     # the platform's own identifier
      name: "Webapp-v3 project (standup)"
      default: true
  repos:
    - url: "github.com/Org/repo"
      reads: [docs, issues, releases]    # metadata only, never the code
```

**`chats:` is a retrieval source, not only a send destination.** A dispatcher reads it to know where to
post; this step reads the same declaration to know where to *look*. The archive under `<venture>/.teamschats/`
(CR-047) stores `_chat.json` carrying the platform id, so the folder is resolved **by matching that id**
rather than by a second hand-written name that would drift.

**Read EVERY declared chat (CR-071).** `default:` answers *"where does this project post?"* — one answer,
and the dispatcher's. Retrieval asks *"what was said anywhere that bears on this session?"*, which has no
default. A project running across three chats whose agenda reads one produces a block that is
complete-looking and partial. Report the count **per chat** when more than one carried traffic: an
undivided total does not say where to go and read. A declared chat that is not in the archive prints as a
problem and is **never counted as a message** — same rule as `reads:` below, a skipped source that
announces itself is honest; a silent one looks like an empty result.

**Read the archives; do not fetch.** `<venture>/.teamschats/` (CR-047) and `<venture>/.githubmeta/` (CR-055)
are siblings by design — an archiver writes, this reads. So an agenda generates **with no credential and
no connectivity**, and the morning it is needed is not when a token turns out to have expired.

**`reads:` is a declared scope, not a capability.** The archiver records the declared scope in
`_repo.json`; honour it there. Report issues **only** where `issues` is listed, and say so where it is
not — a skipped source that announces itself is honest; a silent one looks like an empty result.

**A snapshot is a reading taken at a moment, not an event log.** If the newest one predates the last
note, say so rather than presenting stale rows as news.

`build_agenda.py` writes a **Since the last standup — not said in the room** block into the agenda.
Both sources are **best effort**: a failure prints one line and the agenda is still generated, because
an agenda missing because a network call failed is worse than one missing its context block.

**What to do with it:** the agenda carries the facts; the **facilitator sheet** is where they turn into
questions. An issue that moved with nobody assigned, or a decision taken in chat that half the room has
not seen, is exactly what the round will otherwise skip.

#### Carry-Forward (if `carry_forward.enabled`)

**The gap this closes:** a series writes an agenda, holds the meeting, records a note -- and nothing
compares them. Items fall through silently, and the same item can lead the agenda twice without anyone
noticing it was skipped twice. Observed 2026-09-21: six of seventeen agenda items fell through, and
**every one without a named owner fell**.

1. **The daily note ends with `## Carried forward`** -- one line per item that did not land. This is a
   contract, not a habit: the section is what the next agenda is built from, so a note without it
   silently ends the chain. **`/ops lint` verifies it** (lint step 5) -- write the section even on a day
   when nothing carried, because an empty section and an absent one mean different things.

   **Where nothing carried, say so in the section.** An omitted section is indistinguishable from a note
   nobody finished.

   **The section is cumulative: it lists everything still open at the end of that session, not only what
   that session produced.** The name means what it says — an item carries until it closes. This matters
   because the next agenda reads **the newest note only**: a short extra session that listed only its own
   two items would silently drop everything still open from the week before. Writing the section is
   therefore a review of the standing list, not a summary of the last hour.

   *(This is the one place the loop's rules pull in different directions. The recap is bounded to its
   session — §2b of the recap standard — because it reports what happened. The carry-forward section is
   cumulative because it reports what remains. Same series, opposite rule, and conflating them produces
   either a recap that invents history or a chain that loses items.)*

   **`note_suffix` may be a list** where a series has more than one filename shape — a weekly plus its
   extra sessions, or a series renamed mid-history. Matching only the main shape silently drops the rest,
   and **an extra session is where the most urgent items tend to live**.

   ```
   - **<item>** — <note> · **<owner>**
   - **<Name>:** <what they owe>
   ```

2. **Owner is read from a defined position, never guessed from prose.** Trailing bold after the last
   middot, or the label itself when it is a person's own line. **Anything else is `UNOWNED`, and that
   is a finding rather than a formatting slip** -- an item with no owner is precisely the one that falls
   through an agenda that lists it.

3. **Generate the next agenda** -- do not hand-write it:

   ```
   python3 ~/.claude/skills/ops/build_agenda.py --dir <project>/meetings [--date YYMMDD]
   ```

   It counts how many **consecutive** prior notes carried each item and puts them at the top of the
   agenda, before the round.

4. **Escalate on sessions OR elapsed days, whichever trips first.** `escalate_after` (default 3) and
   `escalate_after_days` (default 14).

   **A session is not a unit of time.** Three sessions is three days on a daily standup and up to three
   months on a fortnightly one, so a session count alone escalates far too late on an irregular series —
   which is precisely where items go missing. Measured across four real series, none was regular:
   nominally-weekly meetings showed gaps of 7, 14, 21 and 26 days, and a fortnightly one had a 59-day
   gap. On that series an item could carry for two months and still read as `2`, below threshold and
   invisible.

   The days rule is effectively inert on a daily series, where sessions trip first. It exists for
   everything else.

   At either threshold the agenda says so itself: *an item that survives three
   agendas is not an agenda problem -- it has no owner who is present, or it is not actually being
   asked for.* Agenda position alone does not get an item raised.

5. **The facilitator's close is the control**: read back what carries and whose name is on each. An item
   read back without a name is the one that will be on the agenda again.

Config lives in `workflows.post_processing.carry_forward`, resolved by the **normal chain** -- a
project's `.claude/ops-config.yaml`, then a folder's `_ops.yaml`, nearest first. **A recurring series is
not always a project:** an org-level meetings folder has no project config, only an `_ops.yaml` further
up, and looking for the former alone finds nothing and falls back to defaults silently.

**`note_suffix` takes a `*` wildcard**, because real filenames are not uniform -- one series carries a
week number (`coreteam-weekly-w38`), another carries participants who change
(`bi-weekly-Ann-Bo-Cai[-Dee]`). An exact match finds neither.

**Companion artifacts are excluded by name** -- agendas, preparations, priorities, facilitator sheets,
appendices, recaps, staged messages. A greedy wildcard otherwise swallows them: `coreteam-weekly-w*`
matches the `-appendix` file, `bi-weekly-*` matches the `-preparation`. Treating a preparation as a note
would read next week's intentions as last week's record. The round table is built from the `people` roster, so the
mechanism is identical across series and only the labels differ.

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

#### Generate Post-Meeting Recap (if `recap_artifact.enabled`) -- ON REQUEST

The third audience. The **summary** is the archive, the **priorities artifact** is for the people doing
the work, and the **recap** is for people who need to know and were not there. Format is a vault-side
standard (`ops/_standards/post-meeting-recap.md`); this section governs when it is produced and what it
must not do.

**Trigger:** `workflows.post_processing.recap_artifact.enabled: true`. Default `false`.

**Read the declared standard before writing, every time — and never write from a previous recap.**
The format belongs to a vault-side document, not to this skill: **this skill states no word, bullet or
block counts and must never acquire any**, because how much a recap contains is a property of what the
session produced and of the venture's own contract, not of the tool. So the shape has to be fetched, not
remembered.

Two failure modes, both observed on 2026-09-22:

- **Writing from the last recap instead of the standard.** The previous file is a *precedent*, and a
  precedent that already drifted hands the drift on with full confidence. Measured on one series: four
  consecutive recaps each ran several times the budget its own standard set, each written from the one
  before it, growing every day, and nothing noticed. A template that merely *points at* the standard is
  not the standard, and neither is yesterday's file.
- **Not applying the rules that can be checked.** Where the standard states something countable, count
  it before staging and put the measurement in the manifest. An unverified claim of conformance is
  what let four recaps drift in a row; a number in the manifest makes the next comparison possible.

Where a venture's own deviation and its standard pull against each other, say so rather than silently
picking one — that conflict is the venture's to resolve, and it recurs every session until it is.

**Offer it; do not write it.** Unlike every other Step 9 artifact, the recap is **generated on request**.
State that a recap looks warranted and what it would carry, then wait. It is the one artifact that
leaves the building -- it reaches people who were not in the room and who read it once. Assembled from
the transcript alone it is **confidently incomplete, and invisibly so to its readers**, who have no
transcript to check it against. The chat archive and the repo archive hold things the room never said,
and only a human knows whether a given week's recap needs them.

**Then gate it on content.** Even when asked, a recap is warranted only where the meeting produced
something an absent reader must act on or know:

- a schedule, ownership or scope change
- a release that landed, or a date that moved
- a finding that changes how the work should be understood
- an ask of the wider team

**Otherwise say so and stop.** A recap that restates the working list trains people to stop reading
recaps, which costs more than the missing recap does.

**The source boundary -- the hardest constraint.** Everything in a recap comes from **the session being
processed**. Two other rules point the other way and must not be read as licence:

- *The first block carries whatever most changes the reader's world* governs **ordering within a
  session**, not eligibility.
- *Reframe, do not just report* means **saying what was said more clearly**, not adding what was not
  said.

Reasoning audience-first -- *"what does the absent reader need to know?"* -- answers from everything in
context, including earlier sessions. The question is ***"what did THIS meeting produce that the absent
need to know?"*** Three requirements follow: bound claims to this transcript (earlier summaries may
inform framing, never supply facts); **an unsent recap has expired, not accumulated** -- it goes out
late carrying its own date or the live parts go as a separate notice, never folded into the next one;
and every claim traces to something said, since an oblique remark does not establish a decision.

*Observed, not theorised: a hand-written recap once led with a cadence change announced four days
earlier, in a session that never mentioned it. A human caught it on first read. A generator running
unsupervised repeats that silently, every time.*

**Staging.** A folder, never a loose file:

```
_outbox/YYMMDD-<recipient>_<subject>/     _manifest.md + the recap body
```

The folder names the **subject of the send**, the left side the **recipient** -- `/outbox` owns that
rule. **Author the manifest; never write `status` or `status-note`.** Those record what a dispatching
surface did first-hand, and the send itself is a human act.

**Do not define a channel or recipient vocabulary here.** `channel:` in the config selects which value
to write into the manifest's existing field; it does not create a parallel enumeration. A second schema
beside the first is two implementations to keep in step.

**Rendering, once the channel is known:**

| Channel | Body |
|---|---|
| chat | `**bold**` labels, bullets, one message |
| email | `UPPERCASE` labels, `- ` bullets never nested, bare links on their own line, no greeting or sign-off |

The subject belongs in the manifest's `subject` field, not repeated at the top of the body. **An email
recap must read as finished the moment it is staged** -- that channel composes a draft and a human
presses send.

**Classification is decided before writing and gates content.** Default team-wide. At every level a
recap never carries personnel matters, raw financials, security methods, regulatory-exposure wording,
commercial terms under negotiation, or individual criticism. **A project-assignment change is not a
personnel matter** -- who owns which workstream is what the team needs; frame it around the work.

**Config:**

```yaml
workflows:
  post_processing:
    recap_artifact:
      enabled: false                # default
      channel: teams                # written into the manifest's channel field
      classification: team-wide     # team-wide | team-only | management-only
      sections: [shipping, what-we-learned, customer-data]
      dashboard_url: null           # appended as the closing line when set
```

`sections` is a **preset, not a constraint** -- a menu to start from. Forcing content into a label is
worse than inventing one.

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
- **Slug contract (CR-021):** keep å/ä/ö in filenames (never transliterate or digit-substitute), always `YYMMDD-` prefix, always include the role keyword (`samtal`/`förberedelse`/`agenda`/`facilitator`/...), run the Swedish driftword check against the slug before saving. Full contract in ops-base General Naming Rules; retroactive cleanup via `/ops normalize --filenames`.

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
- For _tasks.yaml: create with v2 schema (version: 2, context from folder, scope from path) -- **unless `workflows.task_ledger.mode` is `external` or `none`, in which case it is never created (CR-040)**
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
