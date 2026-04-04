---
name: preparation
description: Create structured meeting preparation documents. Pulls context from previous transcripts and conversations in the contact's folder to build a comprehensive briefing with talking points, open threads, and suggested agenda.
user-invocable: true
argument-hint: <contact name> [YYMMDD|today|tomorrow]
---

# /preparation -- Meeting Preparation

Generate a structured preparation document for an upcoming meeting or call. Pulls context from previous interactions stored in the contact's folder.

**Standalone skill** -- works with any vault that uses a `_contacts/` directory containing contact folders (e.g. `_contacts/firstname-lastname/`).

**Integration:** Output files follow the `YYMMDD-{strings.filename_keywords.preparation}-*.md` naming convention (`förberedelse` in Swedish, `preparation` in English), which `/daily-dashboard` picks up automatically.

---

## Argument Parsing

1. **Contact name** (required): Name of the person. Matched using the name resolution algorithm:
   - First, check `_contacts/*/_meta.yaml` for `display_name` or `aliases` matches
   - Then, match against folder names inside `_contacts/`:
     - Exact match: `david` matches `_contacts/david-ekberg/` (partial match on first name)
     - Full match: `erik sandberg` matches `_contacts/erik-sandberg/`
     - Fuzzy: `bob l` matches `_contacts/bob-lindgren/`
   - Matching is case-insensitive with Swedish character folding ("Andre" matches "André")
   - If ambiguous, list matching folders and ask the user to choose

2. **Date** (optional): When the meeting is. Default: today.
   - `today` or no argument -> current date
   - `tomorrow` -> next day
   - `YYMMDD` -> specific date (e.g. `260220`)

### Examples

```
/preparation david                    -> David's folder, today's date
/preparation david tomorrow           -> David's folder, tomorrow
/preparation erik sandberg 260219    -> Erik Sandberg's folder, specific date
/preparation bob l 260220           -> Bob Lindgren's folder, Feb 20
```

---

## Execution Steps

### Step 0: Frozen Prep Check (CR-005)

**Before** writing or modifying any preparation file, check the file's target meeting date:

- **Meeting date is today or in the future** -> proceed normally
- **Meeting date is in the past** -> refuse with this message:

  > This prep file is for a past meeting (YYMMDD). Mid-meeting or post-meeting notes belong in the transcript file. Use `/transcript` or `/ops` to capture them. To override, pass `--force`.

**Rationale:** preparation files must be **frozen at meeting time**. Mutating a prep doc with mid-meeting updates destroys the trace and contaminates the document. Live notes belong in the transcript file, which is the canonical post-meeting record.

The `--force` override exists for legitimate fix-ups (e.g., correcting a typo found post-meeting) but should be rare.

### Step 1: Locate Contact Folder

Find the matching folder inside `_contacts/` at the vault root using the name resolution algorithm.

**Resolution order:**
1. Scan `_contacts/*/_meta.yaml` files for `display_name` or `aliases` match
2. Match against folder names (case-insensitive, partial first name, fuzzy)
3. Swedish character folding: "Andre" matches "André"

**When match found:**
- If `_meta.yaml` exists, use `display_name` for document headings and filenames
- If no `_meta.yaml`, derive display name from folder name (title-case, hyphen -> space)

**If no match found:**
- Suggest creating the folder: `_contacts/firstname-lastname/`
- Ask the user for the canonical name spelling (display_name)
- Offer to create `_meta.yaml` with display_name and any aliases

**Creating `_meta.yaml` (optional but recommended):**
```yaml
version: 1
display_name: "David Ekberg"
aliases:
  - "Dave"
  - "David E"
```

See [Contact Metadata Schema](../ops-config/contact-meta-schema.md) for full specification.

### Step 2: Gather Context

Read existing files in the contact folder to build context:

1. **CHANGELOG.md** (if exists) -- scan for recent entries to understand interaction history
2. **Recent transcripts** -- read the 2-3 most recent `YYMMDD-samtal-*.md`, `YYMMDD-call-*.md`, or other `YYMMDD-*.md` files (sorted by date, newest first). Search for both Swedish and English filename keywords.
3. **Previous preparations** -- read any existing `YYMMDD-förberedelse-*.md` or `YYMMDD-preparation-*.md` files, especially the most recent one for continuity
4. **Other files** -- note any other relevant documents (project files, notes, etc.)

Extract from these sources:
- Open action items (unchecked `- [ ]` items)
- Decisions made in recent meetings
- Topics discussed recently
- Unresolved questions or threads
- Relationship context (role, company, how you know each other)
- Previous meeting outcomes vs. preparations (what was expected vs. what actually happened)

### Step 2.5: Cross-Context Scan -- mandatory with explained relevance (CR-005)

After gathering context from the contact's own folder, scan the vault for **lateral mentions** relevant to this meeting. This step is **mandatory** when the vault has 3+ contact folders -- the prior optional treatment caused the skill to silently skip cross-references in most prep files.

**Procedure:**

1. Glob `YYMMDD-*.md` files across the vault (last 60 days by date prefix). Include `_contacts/*/`, venture meeting folders, and `_projects/*/`.
2. **Exclude** files from the target contact's own folder -- those are *history*, not lateral references. We want references *elsewhere*.
3. Grep the result set for: the contact's display name, the contact's company name, and the 2-3 top topic keywords from the upcoming meeting context (gathered in Step 3).
4. For each hit, **read the matching section** and write **one line**:

   ```
   - [filename](path) -- [one-sentence explanation of why this is relevant to the upcoming meeting]
   ```

5. The explanation is **mandatory**. A bare link with no explanation is **forbidden** -- it forces the reader to open the file to know if it matters, which defeats the purpose. If you cannot articulate the relevance in one sentence, do not include the link.

**Skip the entire section (omit the heading) if:**
- The vault has fewer than 3 contact folders
- No relevant lateral mentions found after the procedure above

**Do NOT** add an empty "Cross-references" header. Either the section has explained references, or it does not exist.

### Step 3: Ask for Additional Context

After gathering file-based context, ask the user. Use the resolved language (see Language section below) for this prompt:

**Swedish (default):**
> Jag har läst igenom [N] filer i [contact]s mapp. Här är vad jag har som underlag:
>
> - Senaste samtalet: [date] -- [brief summary]
> - Öppna punkter: [list key open items]
> - [Any other relevant context found]
>
> **Vad handlar morgondagens/dagens samtal om?** Ge mig gärna:
> - Anledning till samtalet (uppföljning, nytt ämne, planerat möte?)
> - Specifika frågor du vill ta upp
> - Eventuell ny information sedan senast (mejl, händelser, etc.)

**English:**
> I've read through [N] files in [contact]'s folder. Here's what I have as context:
>
> - Latest conversation: [date] -- [brief summary]
> - Open items: [list key open items]
> - [Any other relevant context found]
>
> **What is tomorrow's/today's meeting about?** Please share:
> - Reason for the meeting (follow-up, new topic, scheduled?)
> - Specific questions you want to raise
> - Any new information since last time (emails, events, etc.)

If the user provides additional context (email threads, voice notes, specific topics), incorporate that.

### Step 4: Generate Preparation Document

Create the file using the template below.

### Step 5: Save and Report

1. Save to `_contacts/contact-folder/YYMMDD-{keyword}-[context].md` where `{keyword}` is the resolved filename keyword (`förberedelse` for Swedish, `preparation` for English -- see Output Filename section)
2. Offer to update CHANGELOG.md if one exists in the contact folder
3. Report what was created

---

## Document Template (CR-005: agenda-card-first)

Two-tier structure:

- **Top of file (60-second walk-in card):** Agenda + Open actions. Self-sufficient -- a reader who only sees this can lead the meeting.
- **Below the fold:** Context, cross-references, deep-dive sections, background. Read if you have 5 more minutes.

A horizontal rule (`---`) separates the two tiers visually and conceptually.

```markdown
# {strings.changelog.preparation_label}: [{strings.meeting_types.call}|{strings.meeting_types.meeting}] Alex-[Contact Name] -- [DD] [month] [YYYY][, HH:MM if known]

## {strings.preparation.agenda}

1. [{tag}] [One-sentence question or deliverable]
2. [{tag}] [One-sentence question or deliverable]
3. [{tag}] [One-sentence question or deliverable]
4. [{tag}] [One-sentence question or deliverable]
5. [{tag}] [One-sentence question or deliverable]

[5 items max in the walk-in card. Top 5 must be the most critical -- if there are more, they go in an appendix below.]

## {strings.preparation.open_actions}

**{strings.preparation.your_actions}:**
- [ ] [Action item -- status/context]

**{strings.preparation.their_actions}:**
- [ ] [Their action item -- what to follow up on]

---

## {strings.preparation.deep_dive_separator}

## {strings.preparation.context}

[2 sentences max: When was last contact? What was discussed? What has changed since?]

## {strings.preparation.cross_references}

[Only include if Step 2.5 found relevant lateral mentions. Each line must include an explanation of why it matters -- bare links are forbidden.]

- [filename](path) -- [one-sentence explanation of why this is relevant to the upcoming meeting]

## 1. [{tag}] [Agenda item 1 title]

[Deep-dive content for agenda item 1: framing, options, what to push for, anticipated objections.]

**Suggested framing:** [How you might open this topic]
**Key question:** [The actual decision point]
**If they push back:** [Counter-frame or fallback]

## 2. [{tag}] [Agenda item 2 title]

[Deep-dive for item 2.]

## [N]. [More deep-dive sections as needed -- one per agenda item]

## {strings.preparation.background}

- [3-5 bullets on the relationship and longest-running threads]
- [Their role, company, what you collaborate on]

*{strings.metadata.created}: [YYYY-MM-DD]*
```

### Template Notes

- **Walk-in card on top**: The agenda + open actions block at the top of the file is self-sufficient. If a reader has only 60 seconds before the meeting, they read this and walk in prepared. Everything below the `---` is context they can read if they have more time.
- **Tagged questions, not topics**: Each agenda item must start with a tag (`[DECISION]`, `[DEMO]`, `[STATUS]`, `[QUESTION]`, `[FYI]`) and be phrased as a question or a clear deliverable -- NOT a noun phrase like "ProjectX status". See Agenda Tag System below.
- **5 items max in the walk-in card**: If the meeting needs more topics, the top 5 are the most critical (P0 blockers, decisions that must happen today). Additional items go in a numbered "Appendix" or "Övriga punkter" section below the deep dives.
- **Open actions visible without scrolling**: Split by person (`Yours` / `Theirs`). The reader needs to see what they owe before walking in.
- **Background moves to the bottom**: It's reference material, not navigation. A reader doesn't need to know the relationship history to lead the meeting -- they need to know what to ask.
- **Cross-references with explanation**: Each cross-reference link must explain *why* the link matters in one sentence. Bare links are forbidden (see Step 2.5).
- **Deep-dive sections include framing, not just facts**: For each agenda item, suggest how to open the topic, what the actual decision point is, and how to handle pushback. This is the difference between *briefing* (backward) and *preparation* (forward).

---

## Agenda Tag System (CR-005)

Every agenda item in the walk-in card must start with one of these five tags. The tag tells the reader the *intent* of the item without reading the deep-dive section.

| Tag | Use when | Example |
|-----|----------|---------|
| `[DECISION]` | A choice needs to be made in this meeting | `[DECISION] Ska vi pausa ProjectX eller köra parallellt?` |
| `[DEMO]` | Something to show or walk through | `[DEMO] Data-export -- visa flödet` |
| `[STATUS]` | Update or sign-off needed | `[STATUS] Designbudget -- sign-off idag` |
| `[QUESTION]` | Information you need from them | `[QUESTION] Vad blockerar API-migreringen?` |
| `[FYI]` | Briefing only, no action expected | `[FYI] USA-konvertering siffror` |

**Resolved labels** come from `strings.agenda_tags` in the org config (English defaults: DECISION/DEMO/STATUS/QUESTION/FYI; Swedish: BESLUT/DEMO/STATUS/FRÅGA/FYI).

**Format rules:**
- One tag per item, written in square brackets at the start
- Item text after the tag must be a **question or deliverable**, not a topic noun phrase
- Bad: `[STATUS] ProjectX` -- no question, no deliverable
- Good: `[STATUS] ProjectX -- klart för Fortnox-integration?`

**Why this matters:** The audit found that ~40% of preparation files were unusable in a 2-minute walk-in because the agenda was a list of topics rather than a list of questions. Tags + question framing fix both problems at once.

---

## Single-Document Principle (CR-005)

A preparation file must be **self-contained**. It is not allowed to reference another preparation file as required reading.

If two prep streams converge (e.g., a weekly sync that needs both topic A and topic B context), **merge them into a single prep document** rather than creating two and linking. The reader should never need to open a second prep file to walk into the meeting.

Cross-references to *transcripts*, *meeting summaries*, *strategic docs*, or *vertical docs* are fine -- those are reference material. Cross-references to *other prep files* are not.

---

## Prioritisation Rules (CR-005)

The walk-in card holds **at most 5 agenda items**. They must be the **most critical** items, not the first 5 reported.

**Procedure for selecting the top 5:**

1. Collect all candidate agenda items from gathered context + user input
2. Tag each candidate with priority signals: P0 blockers, time-sensitive decisions, items where the user is waiting on the contact
3. Sort by criticality
4. Top 5 go in the walk-in card
5. Items 6+ go in an "Övriga punkter" / "Additional items" section **after the deep dives**, NOT in the walk-in card

A 17-item agenda card (the audit found one in the wild) is a failure. If you have 17 candidate items, the prep file's job is to help the reader prioritise -- not to list them all at the top.

---

## Output Filename

Format: `YYMMDD-{strings.filename_keywords.preparation}-[context].md`

The filename keyword is resolved from the string table based on the determined language:
- **Swedish:** `förberedelse` -> `260219-förberedelse-samtal-Alex-David-Ekberg.md`
- **English:** `preparation` -> `260219-preparation-daily-standup.md`

**Contact name in filename:**
- If `_meta.yaml` exists, use `display_name` (e.g., "David Ekberg" -> `David-Ekberg`)
- Otherwise, derive from folder name (title-case, hyphen -> space -> hyphen)
- Always use correct Swedish characters in names (e.g., "André" not "Andre")

The `[context]` part should be descriptive but concise. Examples:

Swedish:
- `260219-förberedelse-samtal-Alex-David-Ekberg.md`
- `260220-förberedelse-samtal-Alex-Bob-Lindgren.md`
- `260219-förberedelse-möte-erik-sandberg-antigravity-doable.md`

English:
- `260303-preparation-daily-standup.md`
- `260219-preparation-meeting-erik-sandberg.md`

Use lowercase with hyphens. Include participants and optionally the main topic if there is a clear focus.

---

## CHANGELOG Update

If a `CHANGELOG.md` exists in the contact folder, offer to add an entry:

```markdown
- **YYMMDD: {strings.changelog.preparation_label} [type] [Contact]** - [ONE sentence describing key topics]. *(förberedelse, keyword1, keyword2, ...)* -> [filename.md]
```

---

## Post-Meeting Lifecycle

### Automatic: Superseded by /ops

When `/ops` processes a meeting transcript for the same date and folder, it automatically adds a superseded marker to the top of the preparation file:

```markdown
> **Superseded** by [YYMMDD-meeting-summary.md](YYMMDD-meeting-summary.md)
```

The preparation file is **not** moved or archived -- it stays in place to preserve cross-reference links. The marker makes it immediately clear that the meeting has been processed. Monthly cleanup can later archive old superseded preparations in bulk.

### Manual: Post-Meeting Update (Optional)

Separately, the user may ask to update the preparation with outcomes. When this happens:

1. Add `{strings.annotations.outcome}` annotations to relevant sections with what actually happened
2. Add a `## {strings.preparation.new_actions_post}` section
3. Add a `## {strings.preparation.reflections}` section if useful
4. Update the footer: `*{strings.metadata.updated}: [date] ({strings.preparation.post_meeting_note})*`
5. Update CHANGELOG if applicable

This turns the preparation into a complete meeting record that combines preparation + outcome.

---

## String Resolution

Template strings marked as `{strings.section.key}` are resolved at runtime.

**Resolution order:**

1. **Org config `strings` section** (if loaded via `/ops`, `/daily-dashboard orgname`, or project config)
2. **Language-matched defaults from `base.yaml`:**
   - `swedish` -> `strings_sv`
   - `english` -> `strings`
   - `input` -> match detected language of existing files in the target folder
   - `per_claude_md` -> look up the target file path in the project CLAUDE.md LANGUAGE POLICY table (see Language section below)
3. **Hardcoded strings** already in template (fallback -- current Swedish defaults)

When no config is loaded (standalone use in a personal vault), the hardcoded Swedish strings apply unchanged.

---

## Language

### Language Determination (priority order)

Determine the output language **before** generating any content. Check these rules top-to-bottom, use the first match:

1. **Org config `language: per_claude_md`** -- Look up the **target file path** in the project CLAUDE.md LANGUAGE POLICY table. The table maps file locations to languages. For example, if CLAUDE.md says `projects/acme-mobile-v3/meetings/` -> English, then a preparation file saved there MUST be in English. This is the most common source of language errors -- always check the target path, not just the vault default.

2. **Org config `language: english` or `language: swedish`** -- Use the explicitly configured language.

3. **Org config `language: input`** -- Match the detected language of existing files in the target folder.

4. **No org config, target folder has existing files** -- Match the language of existing files in the folder (check the most recent 2-3 files).

5. **No org config, no existing files** -- Default to **Swedish** (personal vault convention).

### Rules

- When language resolves to **English**: use English strings, English filename keyword (`preparation`), English headings, English content
- When language resolves to **Swedish**: use Swedish strings, Swedish filename keyword (`förberedelse`), Swedish headings, Swedish content. Swedish text MUST use correct characters (å, ä, ö) -- never substitute
- **Technical terms** and **proper nouns** stay as-is regardless of language
- **Status labels** (IN PROGRESS, TODO, COMPLETE, etc.) stay English regardless of language
- Bold formatting for questions and action items in either language

### Common mistakes to avoid in Swedish output
- "forberedelse" -> "förberedelse"
- "mote" -> "möte"
- "pagaende" -> "pågående"
- "atgard" -> "åtgärd"
- "nasta" -> "nästa"
- "samtalsamnen" -> "samtalsämnen"
- "oppna" -> "öppna"

### Why This Matters

The `/preparation` skill can be invoked from different contexts:
- **Personal vault** (`_contacts/` folders) -- typically Swedish
- **Org vault via `/ops`** (e.g., `acme/projects/*/meetings/`) -- language depends on CLAUDE.md policy
- **Direct invocation** in a project folder -- check folder conventions

The same skill must produce the correct language for each context. When in doubt, check the CLAUDE.md LANGUAGE POLICY for the target vault.

---

## Notes

- The skill works with the `_contacts/contact-name/` folder structure -- no special setup needed
- Also works within org vaults (e.g., `acme/projects/*/meetings/`) when invoked via `/ops` -- language is determined by the org config and CLAUDE.md policy
- Previous preparations provide continuity: the skill checks what was prepared last time and what actually happened
- The `/daily-dashboard` skill automatically discovers files with `förberedelse` or `preparation` in the filename (scans for both keywords)
- Preparations can be created days in advance -- they will show up in the dashboard on the target date
- The numbered topic sections are the most valuable part -- they structure the conversation and prevent important items from being missed
- Full meeting lifecycle: `/preparation` (before) -> meet -> `/ops` or `/transcript` (after) -> preparation auto-marked as superseded
