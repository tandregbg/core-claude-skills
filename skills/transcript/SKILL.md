---
name: transcript
description: Process and summarize transcriptions from calls, meetings, or voice recordings. Use when user provides a transcription, mentions processing a transcript, or wants to summarize a recorded conversation.
user-invocable: true
argument-hint: [transcription text or file path]
---

# Transcript Processing Skill

Process the provided transcription following these steps:

## String Resolution

Template strings marked as `{strings.section.key}` are resolved at runtime.

**Resolution order:**

1. Org config `strings` section (if loaded)
2. Language-matched defaults from `base.yaml`:
   - `swedish` -> `strings_sv`
   - `english` -> `strings`
   - `input` -> match detected transcript language
   - `per_claude_md` -> look up the **target file path** in the project CLAUDE.md LANGUAGE POLICY table
3. Hardcoded strings already in template (fallback)

---

## Step 0.5: Load Applicable Rules (CR-013)

Before creating the summary, load any promoted **rules** from the `_insights.yaml` chain in scope:

1. **Walk up from CWD** collecting `_insights.yaml` files at each level (max depth 6, skip `.archive/`, `clones/`).
2. **Filter to rules:** entries where `confidence: rule` AND `status: active`.
3. **Cap to 20 entries** — if more, prefer highest `confirmation_count`, ties broken by most recent confirmation date.
4. **Build a one-line-per-rule preamble** in the form `[type] summary`. Treat the preamble as additional standing instructions for this run.

**How rules influence transcript output:**
- `[preference]` rules guide tone, length, and format choices in the summary.
- `[decision]` rules guide naming, language, and structural defaults.
- `[pattern]` rules guide what to look for during extraction (e.g., "Bob raises customer-success topics last" → ensure that section is captured even if mentioned briefly).

Do not echo the preamble in the output. Rules influence content, not chrome.

**Scoping:** Only rules in the CWD's parent chain apply. **No rules found:** skip silently.

---

## Step 1: Create the Summary

### Heading Format
1. Check for date in filename or metadata (YYMMDD, YYYYMMDD, YYYY-MM-DD, etc.)
2. Format: `# Summary: [FILENAME] [DATE] - [MAIN TOPIC]`
3. If no date found: `# Summary: [FILENAME] - [MAIN TOPIC]`

### Structure (CR-006: action-first ordering)

**Critical: Action items first, decisions second, outcome third, discussion fourth, background last.**

A reader scanning a meeting summary at 08:30 the next morning needs to find what they own *first*, not a narrative recap. The canonical section order is:

1. **Nästa steg / Next Steps** -- Action items with owners and deadlines (table format, see Action Item Table below). This is what the reader scans first.
2. **Beslut / Decisions** -- What was decided in this meeting, with rationale. **Always include this section** even if there were no formal decisions -- in that case write `*(Inga formella beslut -- diskussionen var orienterande.)*` or the English equivalent. Honest absence is searchable; silent omission is not.
3. **Konklusion / Outcome** -- 1-2 sentences summarizing what changed as a result of this meeting. This is the wrap-up of the action items + decisions above, not a narrative of the discussion.
4. **Diskussion / Discussion** -- Notes, points raised, context. The narrative of what was talked about goes here, not in the Konklusion.
5. **Bakgrund / Background** -- Reference material moves to the bottom. Background is *reference*, not *navigation*.

**Canonical heading names (CR-006):**

| Concept | Swedish | English |
|---|---|---|
| Action items | `Nästa steg` | `Next Steps` |
| Decisions | `Beslut` | `Decisions` |
| Outcome | `Konklusion` | `Outcome` |
| Discussion | `Diskussion` | `Discussion` |
| Background | `Bakgrund` | `Background` |
| Blockers | `Blockers` | `Blockers` |

Pick **one Swedish + one English term per concept** and use it consistently. The following variants are **banished** -- do not produce them in new files: `Sammanfattning`, `Executive Summary`, `Summary`, `Action Items`, `Åtgärdspunkter`, `Huvudpunkter`, `Key Discussion Points`, `Decisions Made`. (Existing files keep their headings -- the daily-dashboard recognises old variants for read-only purposes.)

**Action Item Table format (CR-006):**

The Nästa steg / Next Steps section MUST use this 5-column table format:

```markdown
## Nästa steg

| # | Åtgärd | Ägare | Prio | Deadline |
|---|--------|-------|------|----------|
| 1 | Kontakta leverantören om data-export | Anna | P1 | 260410 |
| 2 | Skicka kravspec till designbyrån | Erik | P2 | 260415 |
```

If owner or deadline is unknown, write `?` rather than omitting the column. The visualisation app and `/daily-dashboard` parse this table -- variants break them silently.

**Konklusion length:** there is **no minimum length** for Konklusion. A 96-word internal session can still have a 1-sentence outcome. Always include the section, however brief.

**Formatting rules:**
- Use `---` to separate main sections
- Use `##` for section headings (sentence case)
- Use bullet points for content within sections
- Adapt section length to information relevance:
  - Short sections: as little as 1 point if relevant
  - Central topics: as many points as needed

**Anti-pattern to avoid:** Writing a Konklusion that narrates the discussion ("Alex konfronterade Carol, Carol erkände delvis, Alex betonade...") instead of stating the outcome ("Carol ska boka uppföljningsmöte; Alex omplanerar samtalet."). The Konklusion is **outcome-tense** (decided / will / ska / shall), not narrative-tense (said / argued / discussed).

### Template Variants by Meeting Length (CR-006)

| Variant | When | Required sections |
|---|---|---|
| **Concise** | <30 min meetings, internal task sessions, dataspec reviews | Nästa steg, Beslut, Konklusion (skip Diskussion + Bakgrund unless substantive) |
| **Standard** | 30-90 min meetings, most contact samtal, standups | Full canonical structure (Nästa steg -> Beslut -> Konklusion -> Diskussion -> Bakgrund) |
| **Extended** | >90 min meetings, board, strategy, multi-topic | Full structure + per-topic numbered subsections under Diskussion + Strategic Alignment if applicable |

The skill picks a variant by estimating meeting duration from transcript metadata (timestamps, length, participant count). Default to **Standard**. Override with `/transcript --concise` or `/transcript --extended`.

### Content Rules
- Identify and create headings for all distinct subject areas
- Exclude personal reflections, sensitive information, private discussions
- Prioritize concrete facts, business ideas, projects, technical details
- Preserve key terms and technical terminology
- Maintain original language throughout

### Name Resolution (critical)

**Never trust transcript spellings.** Transcription services often misspell names (e.g., "Thomas" instead of "Alex", "Andre" instead of "André"). Always resolve names before writing the summary:

1. Check the filename for correct spelling
2. Check `_contacts/*/_meta.yaml` for `display_name`
3. Check org config `team[]` for canonical names
4. Use the resolved canonical name throughout the summary

This applies to ALL occurrences of the name -- not just filenames, but every mention in the summary content.

### Metadata Footer

End the summary with:

```markdown
*{strings.metadata.created}: [YYYY-MM-DD]*
```

### Output Filename
Default format: `YYMMDD-participant-topic-description.md`
Example: `250721-samtal-Alex-Bob-strategisk-genomgang.md`

**Participant name resolution:**
1. Match transcript speaker names against `_contacts/*/_meta.yaml` (display_name, aliases)
2. Match against org config `team[]` (name, aliases) if loaded
3. Fallback: title-case the name from transcript

Use the resolved canonical name (with correct Swedish characters) in the filename. For example, if the transcript says "dave" but `_contacts/david-ekberg/_meta.yaml` has `display_name: "David Ekberg"`, the filename should use `David-Ekberg`.

If the project has a CLAUDE.md that defines specific filename patterns (MEETING FILENAME FORMAT section), follow those conventions instead. For example, management 1-on-1s, weekly meetings, board meetings, and marketing meetings may each have their own naming pattern.

---

## Step 1.5: Link to Preparation (if exists)

After determining the target folder (from Step 2 context clues or participant detection), check if a preparation file exists for the same contact and date:

- Look for `YYMMDD-förberedelse-*.md` or `YYMMDD-preparation-*.md` in the target folder (where YYMMDD matches the transcript date)
- Also check for keyword `{strings_sv.filename_keywords.preparation}` and `{strings.filename_keywords.preparation}` to handle both languages

If found, add a cross-reference line near the top of the summary (after the H1 heading):

```markdown
**{strings.changelog.preparation_label}:** [filename](path/to/preparation)
```

This links the transcript back to the preparation that preceded it, completing the meeting lifecycle.

---

## Step 2: Ask About File Organization

After creating the summary content, ask the user:

**Where should I save this file?**

### Participant Name Resolution

Before presenting options, resolve participant names from the transcript:

1. Extract speaker names from transcript (speaker labels, names mentioned)
2. For each name, run the resolution algorithm:
   - Check `_contacts/*/_meta.yaml` for `display_name` or `aliases` match
   - Check org config `team[]` for `name` or `aliases` match
   - Matching is case-insensitive with Swedish character folding ("Andre" matches "André")
3. Use resolved canonical names in:
   - Filename generation
   - Summary content (replace messy transcript names)
   - CHANGELOG entries

### Routing Options

Check for context clues and present options:

1. **CLAUDE.md routing (if available):** Consult the project CLAUDE.md's MEETING ROUTING table and suggest the appropriate folder based on participants and topic detected in the transcript
2. **Participant folder (if detected):** If a `_contacts/` directory exists at the vault root, match the resolved participant name against folders inside it. Also check for contact folders (`participant_name/`) in the current directory.
3. **Save to a specific path:** Let user specify
4. **Just output the summary:** Don't save to file

If both CLAUDE.md routing and contact folders are available, present both suggestions and let the user choose.

### Creating _meta.yaml (optional)

When routing to a contact folder that lacks `_meta.yaml`, offer to create one:

```
Contact folder lacks metadata. Create _meta.yaml with:
  display_name: "[Resolved Name]"
  aliases: ["[transcript name]"]
? [yes] no
```

See [Contact Metadata Schema](../ops-config/contact-meta-schema.md) for full specification.

If a `CHANGELOG.md` exists in the target location, update it with the new entry.

If NO `CHANGELOG.md` exists in the target location, create one automatically. The CHANGELOG serves as an index of all transcripts and documents in the folder. When creating a new CHANGELOG, scan the target folder for existing transcript/document files and include them as entries (oldest first within each year section, newest year section first).

---

## Step 3: CHANGELOG Update (always)

Always update or create the CHANGELOG. This step is not optional.

If the project has domain-specific CHANGELOGs (consult CLAUDE.md), update the relevant one rather than a root CHANGELOG.

### Entry Format
```markdown
- **YYMMDD: {strings.changelog.transcript_label} Participant(s)** - ONE sentence summary of main topics. *(keyword1, keyword2, ... max 15 keywords)* -> [filename.md]
```

### Rules
- Add new entry at top of appropriate year section
- Maximum 15 keywords in parentheses
- ONE concise sentence (max 2 if absolutely necessary)
- Include link to actual transcript file
- Organize chronologically (newest first)

---

## Structured Extraction (for Domain Skills)

When invoked by a domain skill (management-ops, marketing-ops, bravo-ops, project-ops), transcript can output structured data for further processing.

### Extraction Format

```yaml
extraction:
  date: YYYY-MM-DD              # From filename or content
  time: HH:MM                   # If mentioned
  duration: minutes             # If mentioned
  language: detected            # en/sv/mixed

participants:
  - name: string                # Resolved canonical name (from _meta.yaml or team[])
    transcript_name: string     # Original name as it appeared in transcript
    role: string                # If detected
    speaking_share: percentage  # Estimated

content:
  topics:
    - title: string
      summary: string
      participants: [names]
      importance: high/medium/low

  decisions:
    - decision: string
      rationale: string         # If provided
      owner: string             # If assigned
      deadline: string          # If mentioned

  action_items:
    - action: string
      owner: string
      deadline: string          # If mentioned
      priority: P0-P3           # If mentioned
      context: string           # Brief context

  issues:
    - issue: string
      reported_by: string
      severity: string          # If mentioned
      status: string            # open/resolved/blocked

  metrics:
    - name: string
      value: string
      context: string
      trend: up/down/stable     # If mentioned

  blockers:
    - blocker: string
      owner: string
      dependency: string        # External dependency

raw_summary: |
  # Traditional markdown summary
  (Full formatted summary as per Step 1)
```

### Usage by Domain Skills

Domain skills can:
1. Invoke transcript for extraction
2. Receive structured YAML
3. Apply domain-specific formatting
4. Add domain-specific sections
5. Execute configured workflows

This separation allows:
- Consistent extraction logic across all skills
- Domain skills focus on formatting and output
- Easier testing and maintenance

---

## Language

### Language Determination

When an org config is loaded with `language: per_claude_md`, the output language is determined by the **target file path** -- not the transcript language. Look up the target path in the project CLAUDE.md LANGUAGE POLICY table. For example, a Swedish transcript from a mobile standup saved to `projects/acme-mobile-v3/meetings/` must produce an English summary if the LANGUAGE POLICY says that path is English.

When no org config exists, or when `language: input`, maintain the same language as the original transcription.

### Swedish Character Enforcement

When the output is in Swedish, ALL Swedish words MUST use correct å, ä, ö characters. Never substitute with a or o. This applies to the summary, CHANGELOG entry, and any other output.

Common mistakes to avoid:
- "pagaende" -> "pågående", "foretag" -> "företag", "fran" -> "från"
- "fore" -> "före", "nasta" -> "nästa", "behovs" -> "behövs", "kravs" -> "krävs"
- "anvandning" -> "användning", "mote" -> "möte", "losning" -> "lösning"
- "manader" -> "månader", "forberedelse" -> "förberedelse", "karnteam" -> "kärnteam"

If the organization config has `swedish_chars: strict`, this enforcement is mandatory for all Swedish text regardless of the `language` setting.

---

## Step 3.5: Knowledge Extraction (silent)

After creating the summary and updating the CHANGELOG, scan the summary for durable insights worth accumulating. This step writes to `_insights.yaml` in the same folder as the CHANGELOG -- it is a silent accumulation layer that never surfaces in any skill output.

### What to extract

| Type | Captures | Example |
|------|----------|---------|
| `decision` | Choice + rationale | "Chose Flutter over native for shared codebase" |
| `preference` | Working style | "Prefers short standups over long weekly meetings" |
| `learning` | What worked/didn't | "Two-week sprints too long -- switch to weekly" |
| `opportunity` | Ideas not yet actioned | "Could build SaaS from internal tool" |
| `pattern` | Recurring themes | "Budget discussion deferred three meetings in a row" |
| `quote` | Memorable verbatim quote | "Ska du lyckas i affar sa maste du gneta. I varenda liten del av businessen." |

### Threshold

Only extract insights that are:
- **Non-obvious** -- not something anyone in the meeting would already know
- **Durable** -- likely still relevant in 3+ months
- **Specific** -- includes enough context to be useful without the source

**Quotes:** Extract memorable, pithy statements that capture a philosophy, a hard-won lesson, or a strong opinion. The `summary` field should contain the verbatim quote (cleaned up for readability but preserving the speaker's voice). The `rationale` field provides context (who said it, what triggered it). Keep the original language -- if said in Swedish, store in Swedish.

If fewer than 1 insight meets the threshold, skip this step silently. No output, no mention.

### Privacy and language rules for _insights.yaml

**Privacy:** NEVER include personal names or company names in `summary`, `rationale`, or `tags` fields. The `context` field and `source.file` already provide the connection to who/what. Write insights as generic, reusable knowledge that reads well in the visualisation dashboard without exposing individuals or organizations.

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

**Swedish characters:** When writing Swedish content in `_insights.yaml`, ALL Swedish words MUST use correct å, ä, ö characters. YAML files are equally prone to missing Swedish characters as markdown files. Verify before writing: "prissättning" not "prissattning", "övergång" not "overgang", "förändring" not "forandring", etc.

### Process

1. Scan the summary for decisions with rationale, stated preferences, learnings, opportunities, and patterns
2. For each qualifying insight, create an entry following the `_insights.yaml` format (see below)
3. If `_insights.yaml` already exists in the target folder, append to it and increment `next_id`
4. If it does not exist, create it with `version: 1` and `context` set to the contact/project name
5. **Dedup:** Check existing entries by `source.file` -- if insights from this transcript file already exist, skip to avoid duplicates

### `_insights.yaml` format

Schema version 2 (CR-013) adds the optional `confidence`, `confirmation_count`, `confirmations[]`, and `contradicted_by[]` fields. v1 readers ignore them.

```yaml
version: 2
last_updated: YYMMDD
context: "contact_or_project_name"

insights:
  - id: 1
    type: decision        # decision | preference | learning | opportunity | pattern | quote
    date: YYMMDD
    summary: "One sentence"
    rationale: "One sentence why/context"
    source:
      file: "YYMMDD-samtal-*.md"
      section: "Section name"
    tags: [max, five, keywords]
    status: active        # active | superseded | archived
    superseded_by: null
    # CR-013 lifecycle (all optional; default confidence: hypothesis)
    confidence: hypothesis    # hypothesis | rule
    confirmation_count: 1
    confirmations: []         # [{source, date}], populated on promotion
    contradicted_by: []       # [{source, date}], populated on demotion

next_id: 2
```

**When `/transcript` writes new insights:** always emit them as `confidence: hypothesis` with `confirmation_count: 1`. Promotion to `rule` happens later via `/insights compile`. Do not promote inline — Step 3.5 only extracts; lifecycle transitions are batched.

### Output

Brief confirmation only:

```
Extracted [N] insights to _insights.yaml:
- [type] summary sentence
- [type] summary sentence
```

### Skip conditions

- No CHANGELOG.md in the target folder (no established project context)
- Pure standup transcript (short status updates without decisions)
- User explicitly said "skip insights"

---

## Step 4: Task Import (if applicable)

After saving the summary, check if action items were extracted for the user (typically the person running the skill).

### Detection

Look for action items in:
1. The "Nästa steg" or "Next Steps" section of the summary
2. The "Åtgärder" or "Action Items" section
3. Any `- [ ]` checkboxes assigned to the user

### Task Import Offer

If action items are found, target the **local `_tasks.yaml`** in the contact/project folder where the transcript was saved (not vault root). Create with v2 schema if missing:

```
Found [N] action items for [User]:
1. [Task description]
2. [Task description]
...

Add to task tracker? [yes] no select
```

**Options:**
- `yes` -- Import all action items
- `no` -- Skip task import
- `select` -- Choose which items to import

### Import Process

For each task to import:

1. **Find local `_tasks.yaml`** in the folder where the transcript was saved. If none exists, create with v2 schema:
   - `version: 2`
   - `context`: derived from folder name (e.g., `erik-lindgren_techco`)
   - `scope`: `project`
   - `tasks: []`
   - `next_id: 1`
2. **Assign defaults:**
   - `priority`: P1 (default for meeting action items)
   - `source.type`: `meeting`
   - `source.file`: Relative path to the saved transcript
   - `source.section`: Section where task was found
   - `created`: Today's date (YYMMDD)
   - `status`: `pending`
   - `private`: `false` (meeting tasks are shared)
3. **Get next ID** from `next_id` field
4. **Append task** to `tasks` array
5. **Increment `next_id`**
6. **Write updated `_tasks.yaml`**

### Import Confirmation

After import:

```
Tasks #[start]-#[end] created:
- #52 Initiera brand/webb-möte (P1, acme)
- #53 Planera Carols vecka (P1, acme)
...

Source: [transcript.md](path/to/transcript.md)
```

### Skip Conditions

Do NOT offer task import if:
- No action items found for the user
- User declined import previously in same session

### Integration with /tasks skill

This step integrates with the `/tasks` skill:
- Same `_tasks.yaml` format
- Same source linking convention
- Tasks appear in `/daily-dashboard` automatically

See `~/.claude/skills/tasks/skill.md` for the complete task schema.

---

## Step 4.5: Execution Feedback (silent)

If `workflows.knowledge_extraction.evolution.enabled` is true (check `base.yaml` or org config), silently log noteworthy execution events to `_insights.yaml` in the target folder. This step produces no visible output.

**What to capture:**

| Type | When | Example |
|------|------|---------|
| `edge_case` | Ambiguous input required guessing or user disambiguation | Name matched multiple contacts, language detection uncertain, unclear target folder |
| `correction` | User corrected or overrode skill output | Changed save location, corrected participant name, modified summary content |

**When NOT to capture:** Normal, successful execution. Most invocations produce zero feedback entries. Only log when something unexpected happened or the user intervened.

**Entry format:**
```yaml
- id: [next_id]
  type: edge_case          # or correction
  date: YYMMDD
  summary: "One sentence describing what happened"
  detail: "How it was resolved"
  source:
    file: "YYMMDD-samtal-*.md"
    skill: transcript
    step: "step number where it occurred"
  tags: [max, five, keywords]
  status: active
```

Follow the same `_insights.yaml` format, dedup rules, and privacy rules as Step 3.5 knowledge extraction.

---

## Related: Task Tracking

Action items extracted from transcripts can be tracked in the central task system (`_tasks.yaml`). The `/tasks` skill provides:
- Task viewing and filtering (`/tasks show`)
- Manual task addition (`/tasks add`)
- Completion tracking (`/tasks done`)
- Weekly reviews (`/tasks weekly`)

The `/daily-dashboard` skill pulls active tasks from `_tasks.yaml` for display in the "Teamfokus" section.

---

## Related: Preparation Documents

Meeting preparation documents follow the naming convention `YYMMDD-förberedelse-*.md` (or `YYMMDD-preparation-*.md` in English). Use `/preparation <contact>` to create them, or create them conversationally. They are saved to the relevant contact folder inside `_contacts/`.

The `/daily-dashboard` skill automatically discovers preparation files by scanning for this filename pattern, so no special action is needed beyond following the naming convention.

### Meeting lifecycle

```
/preparation david    -> YYMMDD-förberedelse-*.md
       |
    [meeting happens]
       |
/transcript            -> YYMMDD-samtal-*.md (links back to preparation)
       |                   |
       |                   +-> offers task import -> _tasks.yaml
       |
/daily-dashboard       -> shows transcript (preparation suppressed if both exist)
                          pulls tasks from _tasks.yaml
```

When a transcript is saved to the same folder as a preparation for the same date+contact, Step 1.5 adds a wikilink cross-reference. The `/daily-dashboard` then shows the transcript in the meetings section and suppresses the preparation to avoid duplication.

Action items extracted during transcript processing can be imported to `_tasks.yaml`, where they're automatically picked up by `/daily-dashboard` for display in the task sections.
