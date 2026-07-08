---
name: ops-base
description: Shared operational framework for meeting documentation, task management, and workflow processes. Base module referenced by the /ops skill.
user-invocable: false
---

# Operations Base Framework

Shared standards for operational documentation across all ops-skills.

**IMPORTANT:** The project CLAUDE.md is the single source of truth for vault-specific details. This skill defines generic frameworks and workflows; CLAUDE.md defines where things go.

---

## CONFIGURATION SYSTEM

Domain skills use a layered configuration system for organization-specific settings.

### Config Resolution Order

1. **Project-level:** `.claude/ops-config.yaml` in the project root
2. **Folder-local** (CR-011): nearest `<folder>/_ops.yaml` walking up from CWD until vault root. Vault root = nearest ancestor containing `_inbox/`, `_outbox/`, or `.obsidian/` (or `VAULT_ROOT` env override).
3. **Vault-wide** (CR-011, optional): `<vault-root>/_config/base.yaml`
4. **Skill defaults:** `~/.claude/skills/ops-config/base.yaml`

First match wins. Later layers provide fallback values.

**Deprecated (v1.16.0, removed v1.17.0):** the previous step "Org config skill: `~/.claude/skills/{org}-ops-config/{org}.yaml`" is deprecated. If still present, it acts as a fallback between steps 3 and 4 with a one-time deprecation warning. Migrate by copying the YAML into the matching `<vault>/<org>/_ops.yaml`.

### Config Usage

When processing content, domain skills should:

1. **Determine organization** from:
   - Explicit `organization` field in project CLAUDE.md
   - Project folder name pattern (e.g., `acme-*` -> acme)
   - Participant names matching team members in configs

2. **Load config** following resolution order

3. **Apply config values:**
   - `language`: Determines output language (english/swedish/input)
   - `team`: For participant recognition and attribution
   - `responsibility_matrix`: For owner assignments
   - `terminology`: For consistent term usage
   - `workflows.update_files`: Which files to update
   - `workflows.action_propagation`: Whether to propagate actions
   - `domain_additions`: Extra sections to include

### Available Configs

Organization configs live in the vault folder they describe: `<vault>/<org>/_ops.yaml` (CR-011). The base fallback config `base.yaml` is in `~/.claude/skills/ops-config/`. Optional vault-wide overrides go in `<vault>/_config/base.yaml`.

Pre-CR-011 skill-based configs (`*-ops-config` skills under `~/.claude/skills/`) are deprecated and removed in v1.17.0.

See `~/.claude/skills/ops-config/schema.md` for complete schema definition.

---

## MEETING DOCUMENTATION

### Summary Format

Follow the **TWO-TIER SUMMARY FORMAT** defined in the project CLAUDE.md. That document defines the base structures for both Concise and Detailed Strategic summaries. The `/ops` skill may add supplementary sections via config `domain_additions` or use a custom `summary_sections` structure.

When processing a meeting:
1. Determine if Concise or Detailed Strategic format applies (use criteria from CLAUDE.md)
2. Follow the structure defined in CLAUDE.md for the chosen format
3. Apply any domain-specific additions from the active ops-skill

### Canonical Heading Order (CR-006)

Regardless of which format variant is used, the standard sections **must appear in this order**:

1. **Nästa steg / Next Steps** -- action items first (table format with `#`, `Åtgärd/Action`, `Ägare/Owner`, `Prio/Priority`, `Deadline`)
2. **Beslut / Decisions** -- always include, even if `*(Inga formella beslut)*`
3. **Konklusion / Outcome** -- 1-2 sentences, no minimum length
4. **Diskussion / Discussion** -- narrative content
5. **Bakgrund / Background** -- reference material at the bottom

Use these **canonical heading names only** -- do not produce variants like `Sammanfattning`, `Executive Summary`, `Summary`, `Action Items`, `Åtgärdspunkter`, `Huvudpunkter`, `Key Discussion Points`, or `Decisions Made` in new files. See `/transcript` SKILL.md for the full canonical heading table and Action Item Table format.

### Template Variants by Meeting Length (CR-006)

| Variant | When | Required sections |
|---|---|---|
| **Concise** | <30 min meetings, internal task sessions | Nästa steg, Beslut, Konklusion |
| **Standard** | 30-90 min meetings, most contact samtal, standups | Full canonical structure |
| **Extended** | >90 min meetings, board, strategy, multi-topic | Full structure + per-topic numbered subsections |

Default to Standard. There is **no minimum length** for the Konklusion section -- a short meeting still has an outcome.

### Template Contracts (CR-018)

Recurring meeting series erode format rules by **silent template forking**, not random noise: the model pattern-matches the previous file of the same series, so one deviating file re-seeds the whole series (a dropped table column, a reintroduced banished heading), and every subsequent file is internally consistent -- which is exactly why per-file review never catches it. The counter-measure is a declared per-meeting-type **shape contract**, checked at save time.

**Registry** (org or folder-local config, `workflows.meeting_templates`): each entry declares a `match` glob for the series and the expected shape; a `default` entry covers everything unmatched (falling back to the CR-006 canonical order and the `strings` action-table headers):

```yaml
workflows:
  meeting_templates:
    mode: warn                      # warn (default) | strict
    weekly-management:
      match: "meetings/management/2*-Weekly-*"
      headings: [Nästa steg, Beslut, Konklusion, Diskussion, Bakgrund]
      action_table: ["#", "Åtgärd", "Ägare", "Prio", "Deadline"]
```

**The check** (run by `/ops` and `/transcript` as the last pre-save step, after Swedish-character validation). Resolve the matching contract (most specific `match` wins, else `default`) and verify exactly three things:

1. **H2 heading sequence** equals the contract's `headings` (order and canonical names; banished variants fail).
2. **Action-table header row** equals the contract's `action_table`.
3. **Empty Beslut carries the marker**: a `## Beslut` section with no decisions must contain the `no_decisions_marker` string -- absence-by-omission fails.

**On mismatch:** `mode: warn` (default) -- save, report the exact diff to the user, log an `edge_case`. `mode: strict` -- show the diff and ask before saving. A deliberate format change is made by **editing the contract**, never by letting a file drift: that turns an accidental fork into an explicit, reviewable decision.

Orgs with no `meeting_templates` config get the `default` CR-006 contract in warn mode -- the check is never fully off.

---

## TASK MANAGEMENT

### Priority Levels
- **P0:** Critical blocker affecting operations/revenue
- **P1:** High priority, needed this week
- **P2:** Important, needed within 2 weeks
- **P3:** Research/exploration, flexible timing

### Status Indicators
- BLOCKED - External dependency
- IN PROGRESS - Active work
- ON TRACK - Progressing well
- TODO - Planned, not started
- PLANNED - Future sprint
- COMPLETE - Finished

### Task Document Lifecycle

Consult the project CLAUDE.md for task document locations within the relevant ops/ domain.

#### 1. Creation (Pre-Meeting)
**Content:**
- Investigation areas
- Research questions
- Technical requirements
- Decision points

#### 2. Active Period
- Update progress regularly
- Link to related documents
- Track dependencies

#### 3. Post-Meeting
- Mark completed items
- Create new task doc for follow-ups
- Archive when complete or after 30 days

### Per-Folder _tasks.yaml (v2)

Tasks are tracked in distributed `_tasks.yaml` files (v2 schema) at each folder level. Each file has `context` (folder identity) and `scope` (root/org/project/personal). The `/tasks` skill manages these files, and the visualisation app aggregates them.

| File | Signals | Used by |
|------|---------|---------|
| `_tasks.yaml` | Folder with tracked tasks | `/tasks`, `/ops`, `/daily-dashboard`, visualisation |

---

## DOCUMENTATION STRUCTURE

Consult the project CLAUDE.md for:
- **Vault structure** and folder organization (VAULT STRUCTURE section)
- **Meeting routing** -- which meetings go where (MEETING ROUTING table)
- **File naming conventions** -- YYMMDD patterns per meeting type (MEETING FILENAME FORMAT section)
- **Ops routing** -- which operational docs go where (OPS ROUTING table)
- **Archive policy** and locations (ARCHIVE POLICY section)
- **Team structure** and responsibility matrix (TEAM section)

### General Naming Rules (slug contract, CR-021)
- All filenames use `YYMMDD-` prefix -- **always this format, never ISO** (`2026-03-12-`). A folder may only deviate if its own CLAUDE.md explicitly declares another format.
- Use hyphens between words
- **Diacritics: keep å/ä/ö in filenames.** Never transliterate (`mote`), never digit-substitute (`m0te`), never mix policies within one filename (`förberedelse-...-utlosen`). CR-007 covered file *content*; this extends it to the filename -- run the same driftword check against the slug before saving.
- **Role keyword is mandatory:** the resolved `{strings.filename_keywords}` word (`samtal`/`förberedelse`/`sammanfattning`/`standup`, or English equivalents) must appear in the slug so the file's role is machine-readable. A preparation must never be named like a summary -- `/daily-dashboard` and `/outbox` route by these keywords.
- Proper names are capitalized (e.g., `Alex-Bob`); all other slug tokens are lowercase
- Only CHANGELOG.md and README.md are uppercase; all other files use lowercase
- See CLAUDE.md's MEETING FILENAME FORMAT for specific patterns per meeting type
- Retroactive cleanup is **opt-in only** via `/ops normalize --filenames <folder>` (renames + rewrites inbound references it can find); never rename existing files implicitly -- links point at current names

---

## WORKFLOW PROCESSES

### Meeting Workflow
1. **Prepare** - Review context, create agenda
2. **Record** - Capture decisions and actions
3. **Process** - Create structured summary
4. **Update** - CHANGELOG, tasks, priority matrix
5. **Archive** - Move completed items

### Change Log Format
```markdown
## [YYYY-MM-DD] - Description
**Meeting:** Duration | **Participants:** Names
**Summary:** [Link](path/to/summary.md)

**Key Changes:**
- Area: Change description
- Area: Change description
- Status: NEW/ONGOING/RESOLVED
```

---

## ARCHIVE POLICY

Consult the project CLAUDE.md for archive policy. General rules:
- **Never delete, always archive** -- move to `.archive/` within the relevant domain folder
- Archive completed tasks after 30 days
- Archive meetings older than 6 months (keep weekly management meetings permanently)
- Organize by year/month
- Maintain audit trail

### `.ephemeral/` contract (CR-024)

`<vault>/.ephemeral/` is the one place exempt from never-delete: **disposable working material with no vault destiny** -- session scratch, repo snapshots, intermediate artifacts of one-off analyses. Rules:

- Nothing in `.ephemeral/` is ever input to vault content, and no vault file may reference a path inside it.
- `/ops sweep` (check 6) flags content older than 14 days; deletion is the expected outcome, not archiving.
- If something in `.ephemeral/` turns out to have a vault destiny after all, it exits through `_inbox/.files/` (see `docs/schemas/inbox.md`, CR-024) like any other input file.
- The routing rule at drop time: **vault destiny → `_inbox/.files/`; no destiny → `.ephemeral/`.** Made consciously, once, instead of by gravity.

---

## RETIREMENT CONVENTION (CR-019)

Skills handle "create new home" well and "retire old home" never -- every relocation of a living artifact (a dashboard, rolling plan, meeting series, task ledger, or output path change) tends to leave the old artifact in place, current-looking and silently frozen. Readers cannot tell "moved" from "abandoned" from "still authoritative".

**The rule:** any relocation of a living artifact MUST, in the same operation:

1. **Leave a tombstone at the old path** -- one line prepended to the old file (or a stub README in the old folder):
   ```markdown
   > **Flyttad (YYMMDD):** se [new-path](relative/link/to/new-path)
   ```
2. **Log the move** in the affected folder's CHANGELOG.
3. **Update or remove stale pointers** the skill itself created (root symlinks, dashboard links).

This applies to skills moving their own output (e.g. `/daily-dashboard` changing output location must tombstone the old dashboard, not leave two live-looking copies) and to user-driven moves processed through a skill (e.g. a 1-on-1 series moving to a new folder gets a forward-pointer README in the old one). `/ops sweep` detects violations after the fact; this convention prevents them at move time.

---

## CROSS-REFERENCING

### Link Standards
- Previous meeting: `[See: YYMMDD-Meeting.md]`
- Task document: `[Tasks: ../tasks/YYMMDD.md]`
- Changelog entry: `[CHANGELOG: YYYY-MM-DD]`
- Use relative paths for reliability

---

## OUTPUT INSTRUCTIONS

When processing content:

1. **Load configuration:**
   - Determine organization from context
   - Load config following resolution order
   - Fall back to base.yaml if no match

2. **Identify content type:**
   - Meeting transcript -> Create appropriate summary format
   - Task description -> Create task document
   - General input -> Create relevant documentation

3. **For meetings:**
   - Determine if Concise or Detailed Strategic format (see CLAUDE.md TWO-TIER SUMMARY FORMAT)
   - Extract participants, decisions, action items
   - Match participants to `team` from config for attribution
   - Include relevant metrics if mentioned
   - Consult CLAUDE.md for correct filename pattern and output location
   - Apply `domain_additions` sections from config

4. **For tasks:**
   - Assign priority level (P0-P3)
   - Set initial status
   - Identify dependencies
   - Use `responsibility_matrix` from config for owner assignment
   - Consult CLAUDE.md for task document location within relevant ops/ domain

5. **Execute workflows:**
   - Update files listed in `workflows.update_files`
   - If `workflows.action_propagation.enabled`, propagate to target files

6. **Apply language:**
   - `english`: Output in English regardless of input
   - `swedish`: Output in Swedish regardless of input
   - `input`: Match the transcript's language
   - `per_claude_md`: Follow the project CLAUDE.md LANGUAGE POLICY for per-file-type rules

7. **CRITICAL -- Swedish character enforcement (when `swedish_chars: strict`):**

   **`swedish_chars: strict` resolution at write time (CR-007):**
   1. If the target folder has its own CLAUDE.md with explicit `swedish_chars`, use that
   2. Else if the folder is under an ops-aligned venture (e.g., `acme/`, `delta/`, `echo/`), use that venture's config
   3. Else if the folder matches a `language_inheritance.apply_swedish_chars_strict_to` glob from base.yaml (default: `_projects/**`, `_contacts/**`, `_private/**`, `_inbox/**`), **inherit `strict` from base**
   4. Else use base default (which is `strict` since CR-007)

   This means files written under `_projects/bravo-project/` or any other sub-tree without its own CLAUDE.md are still subject to strict-mode enforcement.

   **Enforcement rules:**
   - **BEFORE writing ANY file**, verify that every Swedish word uses correct å, ä, ö
   - NEVER write "for" when you mean "för", "ar" when you mean "är", "pa" when you mean "på"
   - This is a BLOCKING requirement -- do not write files with missing Swedish characters
   - The full substitution list lives in `~/.claude/skills/ops-config/swedish_substitutions.yaml`
   - To remediate existing files written before CR-007, use `/ops normalize <file>` (see ops/SKILL.md)
   - Common mistakes to catch:
     - för (NOT "for"), är (NOT "ar"), på (NOT "pa"), från (NOT "fran")
     - möte (NOT "mote"), nästa (NOT "nasta"), första (NOT "forsta")
     - företag (NOT "foretag"), pågående (NOT "pagaende"), behövs (NOT "behovs")
     - månader (NOT "manader"), lösning (NOT "losning"), användning (NOT "anvandning")
     - kräver (NOT "kraver"), förberedelse (NOT "forberedelse"), kärnteam (NOT "karnteam")
     - besökare (NOT "besokare"), återanvändbar (NOT "ateranvandbar")
     - leverantör (NOT "leverantor"), affärsutveckling (NOT "affarsutveckling")
     - välgörenhet (NOT "valgorenhet"), varumärke (NOT "varumarke")
     - domän (NOT "doman"), mätare (NOT "matare"), stöd (NOT "stod")
     - André (NOT "Andre"), ändamål (NOT "andamal"), ägande (NOT "agande")
   - English technical terms, status labels, and proper nouns stay English regardless
   - This rule applies to ALL output: summaries, CHANGELOG entries, priority matrices, dashboards, ops-configs, CLAUDE.md

8. **Always include:**
   - Suggested CHANGELOG entry
   - Cross-references to related documents
   - Next steps or follow-up items

9. **Execution feedback capture (silent):**
   If `workflows.knowledge_extraction.evolution.enabled` is true, silently log noteworthy execution events to `_insights.yaml` in the target folder. This step produces no visible output.

   **What to capture:**

   | Type | When | Example |
   |------|------|---------|
   | `edge_case` | Ambiguous input required guessing or user disambiguation | Name matched multiple contacts, unclear meeting routing, language detection uncertain |
   | `correction` | User corrected or overrode skill output after seeing it | Changed file location, corrected participant names, modified summary structure |

   **When NOT to capture:** Normal, successful execution. Most invocations produce zero feedback entries. Only log when something unexpected happened or the user intervened.

   **Entry format:**
   ```yaml
   - id: [next_id]
     type: edge_case          # or correction
     date: YYMMDD
     summary: "One sentence describing what happened"
     detail: "How it was resolved"
     source:
       file: "transcript-or-summary-filename.md"
       skill: ops              # or transcript, inbox, etc.
       step: "step number where it occurred"
     tags: [max, five, keywords]
     status: active
   ```

   Follow the same `_insights.yaml` format, dedup rules, vocabulary guard, and reusability rules as knowledge extraction (Step 5.5 in /ops, Step 3.5 in /transcript).
