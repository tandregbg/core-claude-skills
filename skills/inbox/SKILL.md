---
name: inbox
description: Universal entry point for unstructured content. Classifies, stores in _inbox/, and hands off to the appropriate downstream skill.
user-invocable: true
argument-hint: [content, file path, or subcommand: status|process [id|all]|triage [refresh|status]|survey|help]
---

# Inbox Skill

Universal capture and classification for unstructured content. Accepts voice memos, quick notes, raw text, forwarded emails -- classifies and routes to the appropriate downstream skill.

## Vault Location

```
vault/_inbox/
  _inbox.yaml           # Derived index (rebuilt from frontmatter)
  YYMMDD-HHMMSS[-slug].md   # Active items (frontmatter is canonical)
  .audio/               # Raw audio captured by record-me for Mac, paired by basename
    YYMMDD-HHMMSS[-slug].m4a
  .files/               # File drops: input files with a vault destiny (CR-024)
    YYMMDD-HHMMSS[-slug].<ext>
  .archive/             # Processed items (moved here after downstream skill runs)
    .audio/             # Audio archived alongside transcript
    .files/             # Source files that don't accompany their output
```

**Schema**: see [`docs/schemas/inbox.md`](../../docs/schemas/inbox.md) for
the canonical `<id>.md` frontmatter shape, `.audio/` convention, and
lifecycle states. The schema is the source of truth; this SKILL.md
documents skill behaviour. Other tools (record-me for Mac, Deep Thought, Marvin,
external skills) write directly to `_inbox/` against the schema; `/inbox`
is one of several producers.

## Subcommands

**Renamed in v1.79.0 (CR-089); `/inbox process` was removed in v1.81.0.** An old name is not recognised: say that it is now `/inbox route`, and do not run it.

### `/inbox [content]` -- Default: Capture + Classify

Accept raw content (pasted text, file path, or inline text), classify it, store in `_inbox/`, and suggest the downstream skill.

**Processing flow:**

1. **Parse input** -- detect content type:
   - Multiple speakers, timestamps, speaker labels -> `voice_memo`
   - "From:", "Subject:", email headers -> `email`
   - File path provided -> read the file, detect type from content
   - **Binary or non-markdown file path** (PDF, CSV/xlsx, image, media, archive) -> `file_drop` (CR-024): move/copy the file into `_inbox/.files/<id>.<ext>` and create the paired stub with `source.file_path` and a type-based classification guess (PDF/document → summarize into a folder; CSV/xlsx → project data; image/media → attachment). Files >~25 MB: flag the size and offer process-in-place + reference-stub archiving instead of moving the blob. Full convention in [`docs/schemas/inbox.md`](../../docs/schemas/inbox.md) "File drops".
   - Short text, no structure -> `quick_note`
   - Everything else -> `raw_text`

2. **Auto-classify** -- determine which downstream skill should process this:

   | Signal | Classification | Target Skill |
   |--------|---------------|-------------|
   | Speaker labels, timestamps, dialogue format | `transcript` | `/transcript` |
   | Org team member names (from ops-config), meeting context | `ops` | `/ops` |
   | **Sender header, no dialogue: a report, newsletter, automated digest, or any mail whose value is its content rather than an exchange** | `content` | `/ops process` (writes a `content` file, **not** a summary — CR-105) |
   | **A thread: someone wrote, you replied, they replied again** | `correspondence` | `/ops process` (writes a `correspondence` file — CR-080) |
   | "TODO", "remind me", imperative sentences, action items | `task` | `/tasks add` |
   | Short observation, no action context | `note` | None (already saved) |
   | Idea, brainstorm, "what if" | `idea` | Appended to an `_ideas.md` -- see step 6 |

   Assign confidence: `high` (clear signals), `medium` (some signals), `low` (ambiguous).

   **`content` vs `transcript` (CR-105).** Step 1 detects `email` as a content *type*; this is
   where it goes. The distinction is not the channel but the shape: a transcript lost its
   structure and the pipeline recovers it (who spoke, how names are spelled), while incoming
   material arrives structured — it has a **sender, not participants**, and no facilitator.
   Routing it as a meeting invents an event that never happened. A mail that *is* an exchange
   between people about a decision is **correspondence**, the row below (CR-080, revived
   2026-10-01). The test between them is simply whether anyone replied.

3. **Determine routing** -- consult CLAUDE.md MEETING ROUTING for folder suggestions:
   - Match participant names using the name resolution algorithm:
     - Check `_contacts/*/_meta.yaml` for `display_name` or `aliases` match
     - Check config `team[]` for internal team members
     - Matching is case-insensitive with Swedish character folding
   - Identify org context from ops-config team lists
   - Suggest target folder (e.g., `_contacts/david-ekberg/`, `acme/meetings/management/`)
   - See [Contact Metadata Schema](../ops-config/contact-meta-schema.md) for name resolution details

4. **Confirm with user** -- present classification + routing summary:
   ```
   Classification: transcript (high confidence)
   Target skill: /transcript
   Target folder: _contacts/david-ekberg/

   OK to proceed? (or override)
   ```
   Wait for user confirmation or override. Keep it brief -- one question, then go.

5. **Store in `_inbox/`**:
   - Write content to `_inbox/YYMMDD-HHMMSS[-slug].md` with frontmatter per [`docs/schemas/inbox.md`](../../docs/schemas/inbox.md)
   - Set `id`, `created`, `classification`, `confidence`, `status: pending`, and routing fields in frontmatter
   - Rebuild `_inbox.yaml` index from the new frontmatter
   - If the input was paired audio, set `source.audio_path` and ensure the audio is at `_inbox/.audio/<id>.m4a`

6. **Execute the downstream skill automatically:**
   - `transcript` -> Run `/transcript` with the content, passing the target folder
   - `ops` -> Run `/ops` with the content, passing the config
   - `task` -> Run `/tasks add [extracted description]`
   - `note` -> Already saved, no downstream skill needed
   - `idea` -> **Append one line to an `_ideas.md`** (see "Ideas" below) instead of leaving an orphan item in `_inbox/`
   - **Do NOT just print instructions** -- actually invoke the skill and let it run
   - The downstream skill handles all its own processing (summary, changelog, task import, insights, history)

7. **Archive the inbox item** after the downstream skill completes:
   - Set frontmatter `status: processed`, `processed_at` to now (ISO 8601), `processed_by` to the downstream skill name, `output_file` to its output path
   - Move the .md file to `_inbox/.archive/<id>.md` and set `archived_to`
   - If paired audio exists, also move `_inbox/.audio/<id>.m4a` to `_inbox/.archive/.audio/<id>.m4a`
   - Rebuild `_inbox.yaml` to reflect the new state

### Ideas

An `idea` is the owner's own thinking, not someone else's input. It gets **one line appended
to an `_ideas.md`** -- no inbox item, no frontmatter, no archive cycle, no task.

**Which file:**

| The idea names | Append to |
|---|---|
| A project with its own `_ideas.md` | that project's file |
| An organisation with one at its root | that org's file (e.g. `<org>/_ideas.md`) |
| Nothing placeable | **`_inbox/_ideas.md`** -- the default |

**Rules:**
- **Append verbatim, one line.** Do not reword, expand, classify or add a date unless the
  owner wrote one. The value of the surface is that writing costs nothing.
- **Never create an `_ideas.md` that does not exist** -- fall back to `_inbox/_ideas.md`.
  New files are the owner's decision, not the skill's.
- **Never route an idea into a project's task ledger, an issue tracker or a changelog.**
  These files exist precisely because they have no automatic input into project work; an
  idea becomes a task only when the owner writes it into `_capture.md` themselves.
- **Do not ask which file** when the content places itself. One line, done -- a confirmation
  prompt costs more than the filing saves.

**When unsure, use the default.** `_inbox` is a door, not a home: an idea can be routed out
later, and a wrong guess is worse than an unsorted one.

### `/inbox status` -- Show Inbox State

Display counts by status (per [schema](../../docs/schemas/inbox.md)):
```
Inbox Status:
  pending:    3 items
  processing: 1 item
  processed:  5 items (will archive on next process run)
  skipped:    1 item
  archived:   12 items (in .archive/)
  ---
  Active:     4 items (pending + processing + skipped)
  Orphan audio: 1 file (audio in .audio/ with no matching .md yet)
```

Also show classification breakdown of active items, flag any orphan
audio waiting in `.audio/` for a matching transcript, and flag orphan
**file drops** in `.files/` with no paired stub (offer to register them,
CR-024).

### `/inbox route [id|all]` -- Route stored items to their skill (was `process`)

Process one item by ID, or all unprocessed items (status `new` or `classified`) with `all`.

**Single item (`/inbox route <id>`):**

1. Read the item's frontmatter and body from `_inbox/<id>.md`
2. If `classification` is missing or `confidence: low`, run classification (Step 2 from default flow); update frontmatter
3. Show classification and target, ask user to confirm or override
4. Set frontmatter `status: processing`
5. **Execute the downstream skill** -- actually run `/transcript`, `/ops`, or `/tasks add` as appropriate
6. After the downstream skill completes, update frontmatter:
   - `status: processed`, `processed_at`, `processed_by`, `output_file`
7. Move `<id>.md` to `_inbox/.archive/<id>.md` (and paired audio to `.archive/.audio/<id>.m4a` if present); set `archived_to`
   - **File drops (CR-024):** the source file in `.files/` moves WITH the output -- to the target folder's `.attachments/` when it should accompany the content (ask if unclear), else to `_inbox/.archive/.files/<id>.<ext>`. Record the final path in the stub before archiving it.
8. Rebuild `_inbox.yaml` from current frontmatter

**All items (`/inbox route all`):**

1. Glob `_inbox/*.md`, read each frontmatter, filter to `status: pending` or `processing`. **Skip working documents** (registered `type: working_doc` / tag `do-not-process` per the [schema](../../docs/schemas/inbox.md) CR-022 section) -- they are surfaces, not captures
2. If no items to process, report "Inbox is empty" and stop
3. Read and classify all items, then present a single confirmation table:
   ```
   | ID                       | Title          | Classification | Target      | Folder              |
   |--------------------------|----------------|----------------|-------------|---------------------|
   | 250428-091803-bob        | samtal med bob | transcript     | /transcript | _contacts/bob/      |
   | 250428-103044-sara       | samtal med sara| transcript     | /transcript | _contacts/sara/     |
   ```
   Ask: "Process all? (or list IDs to skip/override)"
4. **Execute each item sequentially** -- for each confirmed item:
   a. Set frontmatter `status: processing`
   b. Run the downstream skill with the body content and target folder
   c. Let the skill complete its full processing (summary, changelog, tasks, insights)
   d. Update frontmatter: `status: processed`, `processed_at`, `processed_by`, `output_file`, `archived_to`
   e. Move `<id>.md` to `.archive/`; move paired audio (if any) to `.archive/.audio/`
   f. Brief status line: "Item 250428-091803-bob done -- processed as transcript -> _contacts/bob/"
5. Rebuild `_inbox.yaml` once at the end
6. Print final summary: "Processed N items, M archived, K orphan audio still pending"

**Key principle:** `/inbox route` is an automation pipeline, not a suggestion engine. It actually runs the downstream skills. Human-in-the-loop is limited to:
- Confirming the classification table before execution begins
- Any validation questions the downstream skill itself needs (e.g., `/transcript` may ask about participants, `/ops` may ask about config) -- pass these through to the user as they come up

### `/inbox triage [refresh|status]` -- Triage working-surface upkeep (CR-022)

Operates on the vault's registered **triage doc** (see the
[schema](../../docs/schemas/inbox.md) CR-022 section: an `_inbox/` working
document with `type: working_doc`, `status: keep`, tag `do-not-process`).
If no triage doc is registered, say so and stop -- this subcommand never
creates one uninvited (offer to register an existing file if the user asks).

**Design principle (blocking): mechanical upkeep only.** Never reorder,
reword, re-bucket, or classify items. Sorting INKORG is the human's
thinking step, not the skill's.

**`refresh`** (default):

1. **Week anchor:** update the `Veckoankare:` line's date and week number to
   today. Preserve the standing-context text after them verbatim -- only the
   date/week tokens change. If bucket headings carry week numbers
   (e.g. `DENNA VECKA (v.26)`), update those tokens too.
2. **Archive done items:** move every `[x]` bullet (with its sub-bullets) to
   `_inbox/.archive/YYMMDD-triage-klart.md` -- create with a `# KLART-arkiv`
   header if missing, append under a `## YYMMDD` heading, keep the bullet
   text verbatim plus a `(arkiverad YYMMDD)` suffix.
3. **Report INKORG age:** list INKORG items that have sat unsorted >7 days
   (report only -- sorting is the human's job).
4. **Flag plaintext credentials:** scan for password/API-key-looking lines
   (per the schema's no-secrets rule) and report them with the
   recommendation to replace with a password-manager reference. Never
   auto-remove. **Skip lines ending in `<!-- secret-ok -->`** — that marker
   is the owner's recorded decision to keep the credential inline; offer to
   stamp it when the user says a flagged line should stay.
5. **Report:** one summary line per action class (anchor updated, N items
   archived, M INKORG items aging, K credential flags). Show the diff of
   what moved.

**`status`:** read-only -- items per section, INKORG count + oldest item
age, `[x]` items awaiting archive, week-anchor date vs today, link to the
KLART archive.

**Optional external mirror (CR-017).** A vault MAY point the triage doc at an
external actions surface (e.g. a task app) for a focused *today/tomorrow* view.
This is a **local, per-vault integration** -- its script, credentials, and
target IDs live outside this repo (a local script dir + a gitignored secret;
a config pointer under the vault's own config layer). Two directions, both
**human-gated**, mirroring the mechanical-upkeep principle above:

- **push** -- mirror the current actionable *today/tomorrow* items outward,
  after showing a preview. One-way, additive, deduped against what's already
  there. It never invents dates: an item ships only if the line itself marks
  it today/tomorrow.
- **reconcile** -- read the external surface back and, for items completed
  there, **propose** marking the matching triage line `[x]`; the human
  approves before anything is written. Never an automatic merge -- the triage
  doc stays the system of record, consistent with "sorting is the human's
  step, not the skill's."

This skill documents the *contract* (gated push + gated reconcile, secret-free,
triage-path read from the registered `file:`); it ships **no** provider code.

### `/inbox survey` -- The task audit's shape (CR-138)

The audit of the open task ledger is **generated**, not written. It is
`skills/inbox/survey.py`, and this section is its contract: a reader should be
able to reproduce the file from here without opening the script. Before CR-138
the whole format existed only as code, so any surface that lost the code --
another session, the same session past a compaction, another assistant -- met
the requirement by building something plausible instead. **The drift was caught
by the operator, not by any check.**

**The failure to name, in one line: a subset presented in this file's name is a
regression.** The audit's claim is completeness; a document that shows some of
the open entries under the audit's filename reads as reasonable unless the row
count is checked against the ledger, which nobody does.

**Relationship to the triage doc.** Both render `_inbox/_tasks.yaml`, and they
are not duplicates. `daglig-triage.md` answers *what do I do now* and is
deliberately cut to the dated and the prioritised; this audit answers *what is
there* and is complete. Drop either and the other does not cover it -- the
triage cannot surface an entry it filters out, and the audit is far too long to
work from daily.

**The views.** Five, selected by flag, all read-only and all printing to stdout
(the operator redirects; the script writes no file). The flags are not exclusive
and `main()` tests them in a fixed order, so a combination silently picks one
view: **`--migration` wins over `--table`, which wins over `--undated`, which
wins over the default.**

| Invocation | What it renders |
|---|---|
| *(no flag)* | JSON: the register, the ledger and the folder reconciled three ways |
| `--markdown` | The same reconciliation as prose -- the situation half of an audit |
| `--table` | The same per-state buckets as JSON, keyed by state name. Not operator-facing |
| `--table --markdown` | **The operator-facing task audit.** Every open entry, one row each, with a proposed bucket and an empty `Godta` column |
| `--undated` | JSON: only the entries with neither date nor age, keyed by context |
| `--undated --markdown` | The working list of those entries -- one heading each, with three tick-boxes (`GÖRA` / `REFERENS` / `ÖVERSPELAD`) to write in |
| `--migration` | The context -> venture worksheet, venture column first. A map of the context *values*, not of the entries |

`--markdown` alone is the situation half; it is `--table` that makes it the
audit. `--table` and `--undated` without `--markdown` print JSON -- but
**`--migration` does not consult `--markdown` at all**: its branch prints the
worksheet unconditionally, so `--migration` and `--migration --markdown` emit
the same bytes and the flag is a no-op on that path. Written here because the
asymmetry is in the code and reads as an oversight from the other three views.

#### The shape of `--table --markdown`

| Element | Rule |
|---|---|
| Filename | The script prints to stdout. The operator redirects it to a **stable filename** (a vault convention, e.g. `_inbox/_uppgifter.md`) -- it is meant to stay open, not to accumulate dated copies. The header says so and repeats the command that regenerates it |
| Grouping | `## <Verksamhet> -- N poster`, then ``### `<kontext>` -- N · projekt **<Projekt>**``. Unmapped contexts gather under `## Utan post i kartan`; the project is named when the context maps to one in PORTFÖLJEN (CR-162) |
| States | The five states are unchanged and each entry is still in exactly one, but **a state is no longer a section** (CR-162). It travels with the row in `Läge`: `förfallen`, `prio utan datum`, `ingen ålder`, `odaterad`, `framåt YYMMDD` |
| Row | Eight cells: `# \| Verksamhet \| Projekt \| Läge \| Uppgift \| Förslag \| \| Godta` (CR-162). **The signal column's header cell is empty** -- the `✓`/`?` mark appears only in the body rows, and a reader looking for a `✓/?` heading will not find one. The cells are the id with its priority, the venture, the project, the state, the task truncated, the proposed bucket, the signal mark, and the operator's column. `Verksamhet` and `Projekt` are a dash where the context maps to neither |
| A forward-dated entry | **Carries a `Godta` cell like any other** (CR-162). It was previously a three-cell row in a flat `DATERADE FRAMÅT` section with nothing to decide; that section no longer exists, so the exception has nothing to attach to, and the entry is decidable -- its date can be wrong. Its `Läge` reads `framåt YYMMDD` and its proposal is `LÅT STÅ` |
| `Läge` (was `Ålder`) | `<N> d` for an overdue entry. For every other state the cell is a dash: `age_days` is set only when the due date has passed, so the undated states carry no age. The code falls back to the due date when the age is falsy; for a well-formed `due` that entry is never in an undated state, so **the operator sees no date here** -- with one exception: a `due` the date parser cannot read (not `YYMMDD`, or outside the calendar) leaves `age_days` unset and the raw value is printed in this column. A date in this cell therefore means the entry's `due` is malformed |
| Coverage | **Every open entry appears exactly once.** The count in the header is the ledger's own open count. A subset is a different document and must say so in its own name |
| Header | A movement line (what closed today, shown only when something did), the open count, the proposals tallied by kind, `✓` against `?`, the `Godta` legend, and a per-state summary table of where the proposals fall |
| `Godta` | Left **empty** by the generator. Empty means the proposal stands; the operator writes a date (`261027`), `R` for reference, `Ö` for write-off or `S` for leave standing |
| `✓` / `?` | Whether the proposal has a signal in the entry's own text (`✓`) or is a guess from its shape (`?`). The operator reads the guesses first |
| Buckets | `NYTT DATUM`, `SÄTT DATUM`, `AVSKRIV`, `REFERENS`, `LÅT STÅ`. A prose heuristic with one exception: an entry the ledger declares `recurring: true` is always proposed `LÅT STÅ`, with the signal mark `✓`, unless it is overdue (CR-163). Otherwise a heuristic, and labelled as one in the header: *"Förslagen är en läsning av texten, inte ett beslut."* The operator overrides any row |
| Outside the table | A short `### Utanför tabellen` list for what is wrong with the register itself rather than with an entry -- undeclared status words, a registered file still waiting -- each with its own proposal and `Godta` cell |

**The state travels with the row, it does not define the sections** (CR-162). The
sections are ventures, context beneath them; the state is readable per row through
`Läge` and the proposed bucket. `--migration` remains a different question, and the
two are still not to be merged: it maps context *values* to ventures and projects,
carries no `Godta` column, and its decisions belong in
`_config/verksamhet-karta.yaml`. The audit is per entry and decidable.

**What this subcommand never does.** It writes nothing, enforces nothing and
decides nothing. A check that the file holds as many rows as the ledger has open
entries would be cheap, but it is a separate decision and does not exist.

### `/inbox help` -- Usage Guide

Print this usage guide:

```
/inbox [content]        Capture, classify, and route content
/inbox status           Show inbox counts by status
/inbox route [id|all] Process one or all stored items
/inbox triage [refresh|status]  Triage working-surface upkeep (CR-022)
/inbox survey           The generated task audit -- see the section above (CR-138)
/inbox help             This help text

Content types detected: voice_memo, email, quick_note, raw_text, clipboard
Classifications: transcript, ops, task, note, idea

Items are stored in vault/_inbox/ and tracked in _inbox.yaml.
After processing with the downstream skill, items are archived.
```

## `_inbox.yaml` -- derived index

`_inbox.yaml` is a derived index, rebuilt from the frontmatter of every
`_inbox/*.md`. It exists for fast batch listing (Marvin, `/inbox status`)
without parsing every markdown file.

The canonical metadata for any single item lives in that item's
frontmatter, not here. If frontmatter and index disagree, frontmatter wins.

`/inbox` rebuilds the index on every `status` or `process` invocation.
External tools writing items directly into `_inbox/<id>.md` MAY also append
to the index, but they are not required to -- the next `/inbox` call picks
up new files from frontmatter automatically.

See [`docs/schemas/inbox.md`](../../docs/schemas/inbox.md) for the index
schema (`version: 2`, post-CR-012). v1 files are detected and rewritten
lazily on first run.

## Content File Format

Markdown with **YAML frontmatter** (canonical metadata) and a body. See
[`docs/schemas/inbox.md`](../../docs/schemas/inbox.md) for the full
frontmatter spec.

Filename: `YYMMDD-HHMMSS[-slug].md` where:
- `YYMMDD-HHMMSS` is creation timestamp (vault-local)
- `slug` is optional, kebab-case, derived from a short title

Minimal valid frontmatter:

```yaml
---
id: 250428-091803
created: 2026-04-28T09:18:03+02:00
status: pending
---
```

`/inbox` populates additional fields (classification, target_skill,
target_folder, confidence) when the item is classified.

## Integration

- **Reads** ops-config for team member recognition and org routing
- **Reads** CLAUDE.md MEETING ROUTING for folder suggestions
- **Reads** `_contacts/` folder structure for participant matching
- **Executes** downstream skills (`/transcript`, `/ops`, `/tasks`) -- not just suggestions
- **Marvin** (formerly core-skills-visualisation) provides a web UI for the same data (create, view, classify, archive)
- **record-me for Mac** (formerly Trillian) writes raw audio to `_inbox/.audio/` and frontmatter-only stub markdown to `_inbox/<id>.md`; the matching transcript arrives later from Deep Thought
- **Deep Thought** writes transcript markdown back to `_inbox/<id>.md` with `source.external_id` set to the DT job id

## Archive Policy

Follows the core-skills archive pattern: never delete, always archive.
- Processed markdown moves to `_inbox/.archive/<id>.md`
- Paired audio (if any) moves to `_inbox/.archive/.audio/<id>.m4a`
- The pairing-by-basename rule is preserved across the move
- `_inbox.yaml` retains the item entry with `status: processed` and `archived_to` set
- Archive is browsable but not shown in active views
- Retention for archived audio is user-configurable (default: keep indefinitely; future `/inbox prune --older-than Nd` will reclaim space)

## Rules

- Confirm classification with user before executing -- one brief confirmation, then go
- **Execute downstream skills automatically** after confirmation -- do not just print instructions
- Minimize questions -- classify, confirm, execute, archive. No back-and-forth.
- **Frontmatter is canonical**; `_inbox.yaml` is a derived index. If they disagree, frontmatter wins.
- Use the `YYMMDD-HHMMSS[-slug]` identifier format (per [schema](../../docs/schemas/inbox.md))
- One content file per inbox item; pair with `.audio/<id>.m4a` if audio captured
- Items created via Marvin web UI, record-me for Mac, or Deep Thought follow the same schema
- After downstream skill completes, archive the inbox item automatically (and its paired audio)
