---
name: transcript
description: Process and summarize transcriptions from calls, meetings, or voice recordings. Use when user provides a transcription, mentions processing a transcript, or wants to summarize a recorded conversation.
user-invocable: true
argument-hint: [transcription text or file path]
---

# Transcript Processing Skill

Process the provided transcription following these steps:

> **Råmaterial-spärr (raw-transcript lock):** Step 2.5 sparar alltid det inmatade råmaterialet tyst i en central `.transcripts/`-mapp i vault-roten. Filer i `.transcripts/` är ett **tyst arkiv**: de får ALDRIG läsas tillbaka, citeras, summeras om, eller matas in i `_insights.yaml`/sammanfattningar — om inte användaren EXPLICIT ber om råmaterialet (t.ex. "visa råtexten", "vad sa han ordagrant", "öppna råfilen"). Alla steg som vandrar mappar (Step 0.5 rules-walk, Step 3.5 insights) ska hoppa över `.transcripts/` precis som de hoppar över `.archive/`.

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

1. **Walk up from CWD** collecting `_insights.yaml` files at each level (max depth 6, skip `.archive/`, `.transcripts/`, `clones/`).
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

**Owner attribution on undiarized input (CR-015):** an owner cell may hold a bare name **only** when an identifiable speaker explicitly takes the action. When the transcript has no speaker labels (see *Speaker attribution* below), a first-person cue alone ("jag skickar…", "då gör vi…") does **not** identify who - write `?` (or `Name?` for a likely-but-unconfirmed owner) rather than committing to a confident guess. Failing safe with `?` is correct; a confident wrong owner is not.

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

**Template-contract check (CR-018):** as the last pre-save step (after Swedish-character validation), verify the summary against the matching shape contract from `workflows.meeting_templates` (else the `default` CR-006 contract): H2 heading sequence, action-table header row, and empty-Beslut marker. `warn` mode (default) saves + reports the diff + logs an `edge_case`; `strict` asks first. See ops-base "Template Contracts (CR-018)" for the registry format and rationale.

### Content Rules
- Identify and create headings for all distinct subject areas
- Exclude personal reflections, sensitive information, private discussions
- Prioritize concrete facts, business ideas, projects, technical details
- Preserve key terms and technical terminology
- Maintain original language throughout

### Name Resolution (critical)

**Never trust transcript spellings.** Transcription services often misspell names (e.g., "Andre" instead of "André", "Asa" instead of "Åsa"). Always resolve names before writing the summary:

1. Check the filename for correct spelling
2. Check org config `people[]` roster for `canonical` + `aliases` (CR-017 -- covers non-contact persons: colleagues-of-counterparts, remote team members, recurring third parties)
3. Check `_contacts/*/_meta.yaml` for `display_name` and `aliases`
4. Check org config `team[]` for canonical names
5. Use the resolved canonical name throughout the summary

This applies to ALL occurrences of the name -- not just filenames, but every mention in the summary content.

### Speaker attribution & undiarized transcripts (critical, CR-015)

Name Resolution above fixes *spelling*. It does **not** tell you *who said what*. Many sources (e.g. a Deep Thought paste, or any raw recorder export) arrive as a **single continuous stream with no speaker labels**. On such input, who-said-what and therefore **who owns each action item are inferred, not observed** -- and confident inference is the single most common attribution error this skill makes.

**Detect the condition first.** Before assigning any owner, decide whether the transcript is *diarized* (has speaker labels / turn markers like `Tomas:` / `Speaker 1:`) or *undiarized* (one narrative blob). State the result to yourself; it changes the rules below.

**On undiarized transcripts:**
- Treat every owner as a hypothesis. A first-person cue ("jag ska skicka…", "då branchar vi ut…") tells you an action exists, **not who will do it** -- the speaker is unlabeled.
- Prefer **failing safe**: write the owner as `?`, or `Name?` when context makes one participant clearly likely but unconfirmed. Do **not** upgrade `Name?` to `Name` without explicit evidence.
- Use surrounding context to raise confidence where it is genuinely high (e.g. "du är ansvarig för X" addressed to a named participant, or an action only one party could own), but when two readings are equally plausible, choose `?`.
- This rule composes with the Action Item Table rule above -- they must agree.

**Final owner self-check (before save).** Re-read the `Nästa steg` table once. For each row ask: *was this owner explicitly claimed by, or explicitly assigned to, an identifiable speaker?* If not, downgrade the cell to `?` / `Name?`. A wrong-but-confident owner is worse than an honest `?`.

**Capture the gap.** When a transcript is undiarized, log it as an `edge_case` in Step 4.5 so the evolution loop can see how often this source shape occurs. If the user later corrects an owner, log that as a `correction` (Step 4.5).

**Root fix (out of skill scope, worth noting to the user).** The durable remedy is *diarized input* -- a speaker-labeled transcript. When one is available (e.g. a Fathom export, or once upstream diarization lands), use it as the source and this whole section becomes a no-op.

### Proper-noun verification (critical, CR-016)

Name Resolution above corrects the *spelling* of names it can **match**. It does not protect against the opposite failure: a proper noun the transcriber **garbled into something plausible that matches nothing**. Transcription services are unreliable on company and personal names in both directions -- a real surname becomes a different real-looking surname, a company name becomes a phonetic near-miss. These slip through *because* they read fine. Treat every betydelsebärande proper noun as **unverified until matched**, not as fact.

**Why this matters more than it looks (failure-mode principle).** The dangerous ASR errors are not the obvious garble -- those you catch on sight. They are the *plausible* substitutions that read cleanly and match nothing. A confident wrong name is worse than an honest `Name?`: it propagates downstream into every summary, extraction and deliverable built on this transcript. Spend scrutiny on proper nouns and semantic swaps, not on obvious noise.

**Build the known-entity set** from the sources the skill already uses:
- org config `people[]` roster -- `canonical` + `aliases` (CR-017)
- org config `team[]` -- `name` + `aliases`
- `_contacts/*/_meta.yaml` -- `display_name`, `aliases`, `company`
- org config `terminology[].term`
- the filename

**For each person or company name in the summary:**
- **Matches the known set** -> use the canonical spelling (existing Name Resolution behavior).
- **Matches nothing** -> it is unverified. Do **not** silently commit it. Either mark the mention `Name?` (mirroring the CR-015 owner convention), or collect the unverified names into a short trailing note: `> ⚠ Namn att verifiera: <names>`. Prefer the inline `Name?` for a single uncertain mention; use the trailing note when several names are unverified.
- Never upgrade `Name?` to a bare name without explicit confirmation (filename, a known entry, or the user).

**Always correct company and personal names by hand in deliverables** -- this rule flags them; it does not guarantee them.

**Capture the gap.** When you flag one or more unverified proper nouns, log it as an `edge_case` in Step 4.5. If the user later corrects a name, log that as a `correction` (Step 4.5).

Default-on and additive: when every proper noun resolves against the known set, this section is a no-op.

### Committed-spelling consistency (critical, CR-017)

CR-016 verifies names against the *configured* known-entity set. It has no memory of what this pipeline **previously committed** -- so an ASR variant of an already-established name ("Robi" for a person the folder has called "Ravi" for months) sails through as a plausible new name, and the corpus ends up spelling one person three ways across consecutive documents of the same meeting series. A reader can see the inconsistency instantly; per-file processing cannot. This check adds the missing folder memory.

**Before saving the summary:**

1. **Extract person-like tokens** from the draft (names in the action table, participant list, and body).
2. **Scan folder precedent:** the target folder's ~10 most recent `YYMMDD-*.md` files plus its `CHANGELOG.md`, collecting previously committed person names.
3. **Near-miss detection:** for each draft name not already resolved via the known-entity set, compare against the precedent names (case-insensitive; edit distance ≤2 on tokens ≥4 chars; also catch initial-letter swaps like J/Y common in ASR).
4. **On a near-miss hit:**
   - If the precedent spelling resolves via the `people[]` roster / known-entity set → **use the established spelling**, silently.
   - If neither form is in any roster → do NOT silently introduce the new variant. Flag both forms in the `⚠ Namn att verifiera` note: `"Robi" -- tidigare skrivet "Ravi" (260630) -- samma person?` and use the *earlier* spelling in the body (precedent wins until the user says otherwise).
5. **Domain-term anomaly check (same mechanism, not just names):** when a token is a proper noun that is *contextually anomalous* (e.g. a geographic name committed where the series' precedent tables use a metrics term like *churn*), prefer the folder's precedent term and flag the substitution. This class is an ASR mishearing that lands on a real word -- invisible to spellcheck and entity matching alike, and the most expensive to catch late because it propagates into summaries, action tables, and CHANGELOGs looking perfectly plausible.

**Capture the gap:** log an `edge_case` when a near-miss is flagged, a `correction` when the user resolves one. Recurring flags for the same name are the signal to add it to the `people[]` roster -- that is the durable fix, and once added this section goes quiet for that name.

**No-op conditions:** new folder with no precedent files; every name resolves via the known-entity set on first pass.

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

**Slug contract (CR-021):** the filename follows the same Swedish-character rule as the content -- keep å/ä/ö in every slug token (`möte`, not `mote`/`m0te`; `utlösen`, not `utlosen`), run the driftword check against the slug before saving, always use the `YYMMDD-` prefix, and always include the role keyword (`samtal`/`förberedelse`/... ) so the file's role is machine-readable. See ops-base General Naming Rules.

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

## Step 2.5: Archive Raw Transcript (silent, always)

After the summary has a target folder (Step 2), silently archive the **verbatim raw input** -- the original transcription text exactly as it was provided, before any cleaning. This preserves a way back to the source. It is a quiet memory archive, never an active part of the workflow.

**Skip only if:** the user explicitly said "spara inte råmaterialet" / "don't save the raw", OR Step 2 chose "Just output the summary" (option 4) with no target folder.

### Where

Central folder in the **vault root**: `<vault-root>/.transcripts/`. Create it if missing.

Find the vault root by walking **up** from the summary's target folder until you reach the directory that contains `_inbox`/`_outbox`/`_contacts` (the same root-detection other skills use). The raw file always lands in this single central folder, regardless of which contact/project folder the summary was saved to.

### Filename

Mirror the summary's filename stem, with a `-raw` suffix:

```
YYMMDD-samtal-[Names]-[topic]-raw.md
```

(Same stem as the summary so the pair is trivially matched.)

### Content

Plain readable markdown (no gzip). Frontmatter block + verbatim raw text:

```markdown
---
type: raw-transcript
date: YYMMDD
source: deep-thought            # or "pasted" / "file"
summary: ../_contacts/<folder>/YYMMDD-samtal-...md   # relative link to the summary
created_files:                  # every file this run created or updated
  - ../_contacts/<folder>/YYMMDD-samtal-...md
  - ../_contacts/<folder>/_insights.yaml
  - ../_contacts/<folder>/_tasks.yaml
---

<verbatim raw text exactly as it was provided, unedited>
```

If **multiple recordings** were provided in one run (they merged into one summary), store **all** of them in the same raw file with clear separators (`## Inspelning 1`, `## Inspelning 2`, ...). Include each recording's original metadata line (filename, timestamp) if present.

### Back-link

Add a `raw:` line near the top of the **summary** file so the raw archive is reachable from the summary. Use the same discreet style as the Step 1.5 preparation cross-reference, e.g.:

```markdown
**Råmaterial:** [.transcripts/YYMMDD-...-raw.md](../../.transcripts/YYMMDD-...-raw.md)
```

(Adjust the relative path to the summary's actual depth from the vault root.)

### Silent output

Confirm with a single line only -- do not echo the raw content:

```
Råmaterial arkiverat: .transcripts/YYMMDD-...-raw.md (visas ej om inte explicit efterfrågat).
```

### Read-back lock

Files in `.transcripts/` must NEVER be read back, quoted, re-summarized, or fed into `_insights.yaml`/summaries unless the user EXPLICITLY asks for the raw material ("visa råtexten", "vad sa han ordagrant", "öppna råfilen"). The CHANGELOG (Step 3) must NOT link the raw file -- keep it out of the running log; traceability lives in the raw file's own frontmatter and the summary's `raw:` line.

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
| `quote` | Memorable verbatim quote | "Ska du lyckas i affär så måste du gneta. I varenda liten del av businessen." |

### Threshold

Only extract insights that are:
- **Non-obvious** -- not something anyone in the meeting would already know
- **Durable** -- likely still relevant in 3+ months
- **Specific** -- includes enough context to be useful without the source

**Quotes:** Extract memorable, pithy statements that capture a philosophy, a hard-won lesson, or a strong opinion. The `summary` field should contain the verbatim quote (cleaned up for readability but preserving the speaker's voice). The `rationale` field provides context (who said it, what triggered it). Keep the original language -- if said in Swedish, store in Swedish.

If fewer than 1 insight meets the threshold, skip this step silently. No output, no mention.

### Reusability and language rules for _insights.yaml

**Reusability (CR-020 -- replaces the former privacy rule):** Names are **allowed** in insight entries. The vault is private, and `quote` entries need attribution by construction. (The old rule -- "never include personal or company names in `summary`, `rationale`, or `tags`" -- was retired in the 2026-04-07 audit and formally removed by CR-020.) What remains is a *reusability preference*: when an insight generalizes beyond the person who sparked it, prefer name-free phrasing in `summary` and `tags` so the entry reads well in cross-folder views -- the `context` field and `source.file` already carry the who/what. Names in `rationale` are always fine (that is where quote attribution lives). Classification-aware rendering is the visualisation app's job (CR-009), not the writer's.

Generalizes -- prefer name-free:
```yaml
summary: "Switched from hourly billing to t-shirt-sized estimates to handle AI-driven efficiency gains"
tags: [pricing, billing, t-shirt-sizing, business-model]
```

Person-specific -- names are fine:
```yaml
summary: "Prefers supporting plans over driving them"
rationale: "Tim, reflecting on his role in the partner discussion"
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

### Write-time vocabulary guard (CR-020)

Before writing any entry to `_insights.yaml`, verify:

- `type` is one of: `decision | preference | learning | opportunity | pattern | quote | edge_case | correction | skill_pattern`. Never invent variants (`decision-pattern`, `principle`, `outcome`, `design` are known past drift -- map to the nearest canonical type instead).
- `confidence` (when present) is `hypothesis` or `rule` -- never `high`/`medium`/`confirmed`/`supported`. A re-confirmed insight keeps `confidence: hypothesis` and bumps `confirmation_count`; it does not rename its confidence.
- `date` is `YYMMDD` (never ISO `YYYY-MM-DD`), `id` is an integer, and `next_id` equals `max(id)+1` after the write.
- `tags` has at most 5 entries.

Fix silently when unambiguous (e.g. ISO date → YYMMDD); ask the user when not. This guard applies wherever insights are written: `/transcript` Step 3.5/4.5, `/ops` Step 5.5, and all `/insights` subcommands.

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
- `triage` -- (CR-022) append the items to the vault's registered triage doc instead, as open bullets under its INKORG section with a source link to the transcript. Offer this alternative when the items are personal/ad-hoc (no natural org/project folder) and a triage doc is registered (`_inbox/` working document, `type: working_doc` + tag `do-not-process` -- see `docs/schemas/inbox.md`). One item = one home: triage doc OR `_tasks.yaml`, never both.

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
| `edge_case` | Ambiguous input required guessing or user disambiguation | Name matched multiple contacts, language detection uncertain, unclear target folder, transcript lacks speaker labels (owners inferred -- CR-015), unresolved proper noun flagged for verification (CR-016), near-miss variant of a previously committed name or domain term (CR-017) |
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

Follow the same `_insights.yaml` format, dedup rules, vocabulary guard, and reusability rules as Step 3.5 knowledge extraction.

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
