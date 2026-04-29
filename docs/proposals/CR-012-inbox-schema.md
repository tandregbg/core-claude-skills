# CR-012: Formal `_inbox/` schema and `.audio/` subfolder convention

| Field | Value |
|-------|-------|
| **CR Number** | CR-012 |
| **Date** | 2026-04-27 |
| **Author** | Alex + Claude Code |
| **Status** | Implemented |
| **Implementation Date** | 2026-04-29 |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | New schema doc, `/inbox` skill update, ecosystem.yaml link |
| **Related CRs** | CR-010 (vault_conventions), CR-003 (original inbox skill) |
| **Depends On** | CR-010 (this CR adds the schema file `vault_conventions:` references) |
| **Breaking Changes** | No (formalises existing implicit conventions; backward-compatible) |

---

## Executive Summary

The `/inbox` skill was added in CR-003 (v1.13.0) as the "universal entry point for unstructured content." It already classifies and routes inputs. What it does NOT have is an **explicit, documented schema** for what an `_inbox/<id>.md` file looks like — frontmatter shape, required fields, optional fields, where audio attachments go.

This CR formalises:

1. The `_inbox/<id>.md` file shape (frontmatter + body) in a dedicated schema doc.
2. The `_inbox/.audio/<id>.m4a` subfolder convention for raw audio captured by Trillian (the future VaultPulse + voice-memo-watcher merger).
3. The lifecycle: capture → classify → process → archive.
4. The relationship between an audio file and its transcript (paired by basename).

Without this schema, Trillian and Deep Thought have no contract to write against, and any tool that wants to read `_inbox/` has to reverse-engineer the format from the `/inbox` SKILL.md narrative.

**Current Problems:**
1. The `_inbox/` shape is documented in prose inside `/inbox/SKILL.md` but never in a structured schema. Tool authors (Trillian, Marvin, future skills) have to read narrative to reconstruct the contract.
2. There's no convention for raw audio captured by Trillian — should it live in `_inbox/`, `_inbox/.audio/`, `_inbox/audio/`, somewhere else? Today: ad-hoc.
3. No formal way to pair an audio file with its transcript when both arrive in `_inbox/` at different times (audio captured Mac-side, transcript arrives later from Deep Thought).

---

## Problem Analysis

### What `/inbox` does today

Per `core-skills/skills/inbox/SKILL.md`:

- Accepts content (text, file path, raw text, voice memo transcript)
- Auto-classifies by content shape (`voice_memo`, `email`, `quick_note`, `transcript`, etc.)
- Routes to downstream skill (`/transcript`, `/ops`, `/tasks`)
- Stores items in `_inbox/`
- Archives processed items to `_inbox/.archive/`

### What's missing

**(a) The frontmatter shape.** `/inbox/SKILL.md` shows examples but doesn't declare a schema. A tool writing to `_inbox/` (e.g., Trillian, Deep Thought) has to guess at fields.

**(b) Audio-vs-transcript pairing.** When Trillian captures audio and routes it to Deep Thought, audio lands in the vault first (instantly) and the transcript arrives later (seconds-to-minutes later from DT). Both files need to coexist, and tools need to know they're paired.

**(c) Subfolder convention for non-markdown files.** `_inbox/<id>.md` is for processed/transcribed text. Where does the raw audio go? Three candidates:
- Same folder, mixing types (`_inbox/<id>.m4a` next to `_inbox/<id>.md`)
- A subfolder (`_inbox/audio/<id>.m4a`) — visible
- A hidden subfolder (`_inbox/.audio/<id>.m4a`) — Obsidian skips it from the file pane, sync tools can be configured to skip it

The hidden subfolder pattern (`.audio/`) is the right choice for two reasons:
- Audio bloats sync (5MB×N memos vs 5KB×N transcripts) — keeping it out of Obsidian/iCloud sync as a default makes the vault travel light
- The `/inbox` skill operates on markdown files; raw audio is implementation detail, not user-facing content

**(d) The lifecycle.** The skill archives processed items to `_inbox/.archive/`. But should the audio be deleted, retained, or moved to `.archive/.audio/`? Today: ad-hoc.

---

## Proposed Solution

### A new schema doc at `docs/schemas/inbox.md`

Define the canonical `_inbox/<id>.md` shape:

```markdown
---
# Required fields
id: 250423-142214-meeting-notes      # Stable identifier matching filename
created: 2026-04-23T14:22:14+02:00   # When this entered the inbox (ISO 8601)
classification: transcript            # voice_memo|email|quick_note|raw_text|transcript|note|idea
confidence: high                      # high|medium|low
status: pending                       # pending|processing|processed|skipped

# Optional fields
source:
  type: audio                         # audio|email|paste|file|api
  origin: voice_memo                  # voice_memo|dropbox|api|manual|...
  audio_path: _inbox/.audio/250423-142214.m4a   # If paired with audio
  audio_duration_sec: 142
  ingestion_tool: trillian            # trillian|deep-thought|user|...
  external_id: dt_abc123              # ID in external system (DT job, etc.)

target_skill: /transcript             # Suggested downstream skill
target_folder: _contacts/david-ekberg # Suggested routing destination

processed_at: null                    # Filled when status moves to processed
processed_by: null                    # Skill that handled it
archived_to: null                     # Path inside .archive/ when archived
---

# Body

Markdown body of the captured content. For transcripts, this is the
transcript text. For voice memos, this is the transcribed text or a
brief description if not yet transcribed. For quick notes, the note text.

Speakers, timestamps, and structure follow the conventions of whichever
classification this is.
```

### `_inbox/.audio/` subfolder convention

```
_inbox/
├── 250423-142214-meeting-notes.md   ← processed transcript (markdown)
├── 250424-091803-quick-thought.md   ← short voice memo, transcribed
├── _inbox.yaml                       ← index (existing in /inbox skill)
├── .archive/                         ← processed items move here (existing)
│   ├── 250420-103015-old-thing.md
│   └── .audio/
│       └── 250420-103015-old-thing.m4a    ← audio archived alongside transcript
└── .audio/                           ← raw audio waiting for transcript
    ├── 250423-142214-meeting-notes.m4a
    └── 250424-091803-quick-thought.m4a    ← may exist briefly before transcript
```

**Rules:**
- A `.md` and `.m4a` are paired by **basename** (the filename portion before the extension).
- If audio exists but transcript doesn't yet, that's "in flight" — the inbox shows both.
- When the transcript arrives, the `.md` is written; the audio in `.audio/` stays paired (frontmatter `source.audio_path` points at it).
- When `/inbox process` archives an item, the markdown moves to `.archive/<id>.md` and the audio moves to `.archive/.audio/<id>.m4a`. Pairing preserved.
- Configurable retention: optionally delete archived audio after N days while keeping the transcript indefinitely.

### Identifier format

`<YYMMDD>-<HHMMSS>[-<slug>]` — sortable, time-based, unique per second.

- `250423-142214-meeting-notes`
- `250424-091803` (no slug — short voice memo, no descriptive filename yet)

If two items share the same second (rare), append `_2`, `_3`, etc.

### Lifecycle

```
[ external tool writes audio + frontmatter-only md ]
            │
            ▼
[ status: pending — appears in /inbox status ]
            │
            ▼
[ /inbox process — classifies, routes, updates status ]
            │
            ▼
[ status: processing — downstream skill (/transcript, /ops, /tasks) processes ]
            │
            ▼
[ status: processed — file moves to .archive/<id>.md, audio to .archive/.audio/<id>.m4a ]
```

States:
- `pending` — captured, not yet processed
- `processing` — actively being handled by a downstream skill
- `processed` — done, archived
- `skipped` — explicitly skipped by user (kept for review)

### Update `/inbox` skill

Update `skills/inbox/SKILL.md` to:
1. Reference `docs/schemas/inbox.md` as the source of truth for file shape.
2. Document the `.audio/` subfolder convention.
3. Document the lifecycle states explicitly.
4. Update examples to include realistic frontmatter.

### Link from `ecosystem.yaml`

Once CR-010 lands, the `vault_conventions:` block can reference `docs/schemas/inbox.md` for the `_inbox/<id>.md` and `_inbox/.audio/<id>.m4a` paths. (CR-010 already includes a forward link.)

---

## Implementation Plan

### Phase 1: Write the schema doc

1. Create `docs/schemas/inbox.md` with the schema above.
2. Include both `<id>.md` shape and `.audio/<id>.m4a` convention.
3. Include lifecycle diagram and state transitions.
4. Include retention policy options.

### Phase 2: Update the `/inbox` skill

1. Add a "Schema" section to `skills/inbox/SKILL.md` linking to `docs/schemas/inbox.md`.
2. Update the "Vault Location" section to include `.audio/` and `.archive/.audio/`.
3. Update the "Subcommands" section to document state transitions.
4. Update example frontmatter to match the new schema.

### Phase 3: Cross-references

1. CR-010's `vault_conventions:` block already references `docs/schemas/inbox.md` — no change needed there once CR-012 lands.
2. Update `core-skills/CHANGELOG.md` under `[1.16.0]`: "Added: formal schema for `_inbox/<id>.md` and `.audio/` subfolder convention per CR-012."

### Phase 4: Migration of existing inbox items (if any)

If Alex's vault already has items in `_inbox/` with informal frontmatter, audit them:

1. List `_inbox/*.md`.
2. For each, check if frontmatter conforms to the new schema.
3. For non-conforming items, either rewrite frontmatter to match, or move to `.archive/` if no longer needed.

This is a one-time manual step on Alex's vault. Other users with no existing inbox items skip this.

---

## Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `docs/schemas/inbox.md` | **CREATE** | New schema doc with frontmatter spec, `.audio/` convention, lifecycle |
| `skills/inbox/SKILL.md` | Modify | Reference schema doc; document `.audio/`; document lifecycle states |
| `CHANGELOG.md` | Modify | `[1.16.0]` entry under `### Added` |
| (Alex's vault, one-time) | Audit | Confirm existing `_inbox/` items match new schema; rewrite/archive any drifted ones |

---

## Testing Plan

### Test Case 1: schema doc is sufficient for a tool author

- Read `docs/schemas/inbox.md` end-to-end.
- Confirm a developer building Trillian (or any external tool) could write conforming files into `_inbox/` and `_inbox/.audio/` from the schema alone, without reading the `/inbox` SKILL.md narrative.

### Test Case 2: existing inbox skill still works

- Run `/inbox <some content>`.
- Verify it produces a `_inbox/<id>.md` matching the new schema.

### Test Case 3: existing items continue to work

- Run `/inbox status` — confirm any pre-CR-012 items in the inbox are still listed.
- Run `/inbox process <existing-id>` — confirm processing still completes (the schema is forgiving of missing optional fields).

### Test Case 4: paired audio + transcript

- Manually drop `_inbox/.audio/250428-150000-test.m4a` and `_inbox/250428-150000-test.md` (with `source.audio_path` set).
- Run `/inbox status` — confirm the item shows as paired.
- Run `/inbox process 250428-150000-test` — confirm the markdown archives to `.archive/`, audio to `.archive/.audio/`.

### Test Case 5: orphan audio (audio without transcript yet)

- Drop `_inbox/.audio/250428-160000-pending.m4a` only (no `.md` yet — Trillian writes audio before DT replies).
- Run `/inbox status` — confirm the orphan audio shows as "in flight" or similar (skill behaviour to define — could be: list audio-only items separately).

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing `_inbox/` items in Alex's vault don't match new schema | Medium | Low | Phase 4 audit; schema is forgiving (most fields optional); items can be migrated case-by-case |
| `.audio/` subfolder convention conflicts with future Obsidian sync settings | Low | Low | Hidden by leading dot; Obsidian and most sync tools already skip `.`-prefixed folders by default |
| Pairing logic (audio + transcript by basename) is fragile if filenames drift | Medium | Medium | Document basename rule explicitly; tools that rename one file must also rename the other; `/inbox` could enforce this with a `--rename` subcommand later |
| Tools writing to `_inbox/` ignore the schema and write malformed frontmatter | Medium | Medium | `/inbox` skill validates frontmatter on read; logs warnings for non-conforming items; doesn't reject (graceful degradation) |
| Retention policy for archived audio is unclear (delete? keep forever?) | Low | Low | Document as user-configurable; default keep-forever; future skill subcommand `/inbox prune --older-than 30d` for cleanup |

---

## Rollback

1. Delete `docs/schemas/inbox.md`.
2. Revert `skills/inbox/SKILL.md` changes.
3. Existing `_inbox/<id>.md` files continue to work — the schema doc was descriptive of existing convention plus minor formalisation; rollback removes the formal doc but doesn't break in-place files.
4. The `_inbox/.audio/` subfolder, if any audio was placed there, can stay — it's just a folder; nothing parses it in an old `/inbox` skill, so it's inert.

Net rollback risk: very low.

---

## Success Criteria

1. `docs/schemas/inbox.md` exists and is complete (frontmatter spec, `.audio/` convention, lifecycle states, retention policy).
2. `/inbox` SKILL.md references the schema doc as the source of truth.
3. CR-010's `vault_conventions:` block successfully cross-links here.
4. A future Trillian implementer can read `docs/schemas/inbox.md` alone and produce conforming files.
5. Existing `_inbox/` items continue to work without forced migration.
6. CHANGELOG documents the schema addition with example frontmatter.

---

## References

- Suite charter: `vault-pulse/docs/the-guide-architecture.md` §6 (Trillian writes `_inbox/.audio/`), §7 (data flow scenarios)
- CR-003 (v1.13.0): original `/inbox` skill addition
- CR-010 (proposed): `vault_conventions:` block that references this schema
- Existing skill: `core-skills/skills/inbox/SKILL.md`
- Existing schema docs (style reference): `core-skills/docs/schemas/summary-yaml.md`
- Trillian merger CR (TBD): `vault-pulse/docs/change-requests/CR-005-trillian-merger.md` (not yet drafted) — will be the consumer that writes to `_inbox/.audio/`
