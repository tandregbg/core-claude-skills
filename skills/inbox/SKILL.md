---
name: inbox
description: Universal entry point for unstructured content. Classifies, stores in _inbox/, and hands off to the appropriate downstream skill.
user-invocable: true
argument-hint: [content, file path, or subcommand: status|process [id|all]|help]
---

# Inbox Skill

Universal capture and classification for unstructured content. Accepts voice memos, quick notes, raw text, forwarded emails -- classifies and routes to the appropriate downstream skill.

## Vault Location

```
vault/_inbox/
  _inbox.yaml           # Index: metadata + lifecycle state
  YYMMDD-type-slug.md   # Active items
  .archive/             # Processed items (moved here after downstream skill runs)
```

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
   - Write content to `_inbox/YYMMDD-type-slug.md`
   - Update `_inbox.yaml`: add item with status `classified`
   - Use YYMMDD date format, type as the category, slug from title

6. **Execute the downstream skill automatically:**
   - `transcript` -> Run `/transcript` with the content, passing the target folder
   - `ops` -> Run `/ops` with the content, passing the org config
   - `task` -> Run `/tasks add [extracted description]`
   - `note`/`idea` -> Already saved, no downstream skill needed
   - **Do NOT just print instructions** -- actually invoke the skill and let it run
   - The downstream skill handles all its own processing (summary, changelog, task import, insights, history)

7. **Archive the inbox item** after the downstream skill completes:
   - Set `status: done`, `processed.date` to today
   - Set `processed.output_file` to the path of the downstream skill's output
   - Move the .md file to `_inbox/.archive/`

### `/inbox status` -- Show Inbox State

Display counts by status:
```
Inbox Status:
  New:        3 items
  Classified: 1 item
  Done:       5 items
  Archived:   12 items
  ---
  Active:     4 items (non-archived)
```

Also show classification breakdown of active items.

### `/inbox process [id|all]` -- Process Stored Items

Process one item by ID, or all unprocessed items (status `new` or `classified`) with `all`.

**Single item (`/inbox process 3`):**

1. Read the item metadata and content file
2. If not yet classified, run classification (Step 2 from default flow)
3. Show classification and target, ask user to confirm or override
4. **Execute the downstream skill** -- actually run `/transcript`, `/ops`, or `/tasks add` as appropriate
5. After the downstream skill completes, update `_inbox.yaml`:
   - Set `status: done`, `processed.date` to today
   - Set `processed.output_file` to the path of the downstream skill's output
6. Move the .md file to `_inbox/.archive/`

**All items (`/inbox process all`):**

1. Load `_inbox.yaml` and filter items with status `new` or `classified`
2. If no items to process, report "Inbox is empty" and stop
3. Read and classify all items, then present a single confirmation table:
   ```
   | ID | Title | Classification | Target | Folder |
   |----|-------|---------------|--------|--------|
   | 1  | samtal med bob | transcript | /transcript | _contacts/bob/ |
   | 2  | samtal med sara | transcript | /transcript | _contacts/sara/ |
   ```
   Ask: "Process all? (or list IDs to skip/override)"
4. **Execute each item sequentially** -- for each confirmed item:
   a. Run the downstream skill with the content and target folder
   b. Let the skill complete its full processing (summary, changelog, tasks, insights)
   c. Update `_inbox.yaml`: status=done, processed.date, processed.output_file
   d. Move the .md file to `_inbox/.archive/`
   e. Brief status line: "Item 1 done -- processed as transcript -> _contacts/tim/"
5. Print final summary: "Processed N items, M archived"

**Key principle:** `/inbox process` is an automation pipeline, not a suggestion engine. It actually runs the downstream skills. Human-in-the-loop is limited to:
- Confirming the classification table before execution begins
- Any validation questions the downstream skill itself needs (e.g., `/transcript` may ask about participants, `/ops` may ask about org config) -- pass these through to the user as they come up

### `/inbox help` -- Usage Guide

Print this usage guide:

```
/inbox [content]        Capture, classify, and route content
/inbox status           Show inbox counts by status
/inbox process [id|all] Process one or all stored items
/inbox help             This help text

Content types detected: voice_memo, email, quick_note, raw_text, clipboard
Classifications: transcript, ops, task, note, idea

Items are stored in vault/_inbox/ and tracked in _inbox.yaml.
After processing with the downstream skill, items are archived.
```

## `_inbox.yaml` Schema

```yaml
version: 1
last_updated: YYMMDD
next_id: 1
items:
  - id: 1
    title: "Descriptive title"
    type: voice_memo          # voice_memo | quick_note | email | raw_text | clipboard
    classification: transcript # null | transcript | ops | task | note | idea
    status: new               # new | classified | done | archived
    file: "YYMMDD-type-slug.md"
    created: YYMMDD
    source_method: skill       # skill | web_ui
    routing:
      target_skill: null       # null | transcript | ops | tasks
      target_folder: null      # vault-relative path
      confidence: null         # null | high | medium | low
    processed:
      date: null
      output_file: null
    tags: []
```

## Content File Format

Standard markdown. Self-contained, renderable in Obsidian. No frontmatter required -- the yaml index handles all metadata.

Filename: `YYMMDD-type-slug.md` where:
- `YYMMDD` is creation date
- `type` is the content type (voice-memo, quick-note, email, raw-text, clipboard)
- `slug` is a short descriptive slug from the title

## Integration

- **Reads** ops-config for team member recognition and org routing
- **Reads** CLAUDE.md MEETING ROUTING for folder suggestions
- **Reads** `_contacts/` folder structure for participant matching
- **Executes** downstream skills (`/transcript`, `/ops`, `/tasks`) -- not just suggestions
- **core-skills-visualisation** provides a web UI for the same data (create, view, classify, archive)

## Archive Policy

Follows the core-skills archive pattern: never delete, always archive.
- Processed files move to `_inbox/.archive/`
- `_inbox.yaml` retains the item entry with `status: archived`
- Archive is browsable but not shown in active views

## Rules

- Confirm classification with user before executing -- one brief confirmation, then go
- **Execute downstream skills automatically** after confirmation -- do not just print instructions
- Minimize questions -- classify, confirm, execute, archive. No back-and-forth.
- Use YYMMDD date format consistently
- One content file per inbox item
- Items created via the web UI (source_method: web_ui) follow the same schema
- After downstream skill completes, archive the inbox item automatically
