---
name: inbox
description: Universal entry point for unstructured content. Classifies, stores in _inbox/, and hands off to the appropriate downstream skill.
user-invocable: true
argument-hint: [content, file path, or subcommand: status|process [id|all]|triage [refresh|status]|help]
---

# Inbox Skill

Universal capture and classification for unstructured content. Accepts voice memos, quick notes, raw text, forwarded emails -- classifies and routes to the appropriate downstream skill.

## Vault Location

```
vault/_inbox/
  _inbox.yaml           # Derived index (rebuilt from frontmatter)
  YYMMDD-HHMMSS[-slug].md   # Active items (frontmatter is canonical)
  .audio/               # Raw audio captured by Trillian, paired by basename
    YYMMDD-HHMMSS[-slug].m4a
  .archive/             # Processed items (moved here after downstream skill runs)
    .audio/             # Audio archived alongside transcript
```

**Schema**: see [`docs/schemas/inbox.md`](../../docs/schemas/inbox.md) for
the canonical `<id>.md` frontmatter shape, `.audio/` convention, and
lifecycle states. The schema is the source of truth; this SKILL.md
documents skill behaviour. Other tools (Trillian, Deep Thought, Marvin,
external skills) write directly to `_inbox/` against the schema; `/inbox`
is one of several producers.

## Subcommands

### `/inbox [content]` -- Default: Capture + Classify

Accept raw content (pasted text, file path, or inline text), classify it, store in `_inbox/`, and suggest the downstream skill.

**Processing flow:**

1. **Parse input** -- detect content type:
   - Multiple speakers, timestamps, speaker labels -> `voice_memo`
   - "From:", "Subject:", email headers -> `email`
   - File path provided -> read the file, detect type from content
   - Short text, no structure -> `quick_note`
   - Everything else -> `raw_text`

2. **Auto-classify** -- determine which downstream skill should process this:

   | Signal | Classification | Target Skill |
   |--------|---------------|-------------|
   | Speaker labels, timestamps, dialogue format | `transcript` | `/transcript` |
   | Org team member names (from ops-config), meeting context | `ops` | `/ops` |
   | "TODO", "remind me", imperative sentences, action items | `task` | `/tasks add` |
   | Short observation, no action context | `note` | None (already saved) |
   | Idea, brainstorm, "what if" | `idea` | None (already saved) |

   Assign confidence: `high` (clear signals), `medium` (some signals), `low` (ambiguous).

3. **Determine routing** -- consult CLAUDE.md MEETING ROUTING for folder suggestions:
   - Match participant names using the name resolution algorithm:
     - Check `_contacts/*/_meta.yaml` for `display_name` or `aliases` match
     - Check org config `team[]` for internal team members
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
   - `ops` -> Run `/ops` with the content, passing the org config
   - `task` -> Run `/tasks add [extracted description]`
   - `note`/`idea` -> Already saved, no downstream skill needed
   - **Do NOT just print instructions** -- actually invoke the skill and let it run
   - The downstream skill handles all its own processing (summary, changelog, task import, insights, history)

7. **Archive the inbox item** after the downstream skill completes:
   - Set frontmatter `status: processed`, `processed_at` to now (ISO 8601), `processed_by` to the downstream skill name, `output_file` to its output path
   - Move the .md file to `_inbox/.archive/<id>.md` and set `archived_to`
   - If paired audio exists, also move `_inbox/.audio/<id>.m4a` to `_inbox/.archive/.audio/<id>.m4a`
   - Rebuild `_inbox.yaml` to reflect the new state

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

Also show classification breakdown of active items, and flag any orphan
audio waiting in `.audio/` for a matching transcript.

### `/inbox process [id|all]` -- Process Stored Items

Process one item by ID, or all unprocessed items (status `new` or `classified`) with `all`.

**Single item (`/inbox process <id>`):**

1. Read the item's frontmatter and body from `_inbox/<id>.md`
2. If `classification` is missing or `confidence: low`, run classification (Step 2 from default flow); update frontmatter
3. Show classification and target, ask user to confirm or override
4. Set frontmatter `status: processing`
5. **Execute the downstream skill** -- actually run `/transcript`, `/ops`, or `/tasks add` as appropriate
6. After the downstream skill completes, update frontmatter:
   - `status: processed`, `processed_at`, `processed_by`, `output_file`
7. Move `<id>.md` to `_inbox/.archive/<id>.md` (and paired audio to `.archive/.audio/<id>.m4a` if present); set `archived_to`
8. Rebuild `_inbox.yaml` from current frontmatter

**All items (`/inbox process all`):**

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

**Key principle:** `/inbox process` is an automation pipeline, not a suggestion engine. It actually runs the downstream skills. Human-in-the-loop is limited to:
- Confirming the classification table before execution begins
- Any validation questions the downstream skill itself needs (e.g., `/transcript` may ask about participants, `/ops` may ask about org config) -- pass these through to the user as they come up

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

### `/inbox help` -- Usage Guide

Print this usage guide:

```
/inbox [content]        Capture, classify, and route content
/inbox status           Show inbox counts by status
/inbox process [id|all] Process one or all stored items
/inbox triage [refresh|status]  Triage working-surface upkeep (CR-022)
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
- **Trillian** (vault-pulse) writes raw audio to `_inbox/.audio/` and frontmatter-only stub markdown to `_inbox/<id>.md`; the matching transcript arrives later from Deep Thought
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
- Items created via Marvin web UI, Trillian, or Deep Thought follow the same schema
- After downstream skill completes, archive the inbox item automatically (and its paired audio)
