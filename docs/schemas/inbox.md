# `_inbox/` schema

The vault inbox is the universal entry point for unstructured content. Files
landing in `_inbox/` are captured by humans, by Trillian (vault-pulse), by
Deep Thought callbacks, or by any future skill or external tool. The `/inbox`
skill classifies and routes them; downstream skills (`/transcript`, `/ops`,
`/tasks`) consume them.

This document is the **canonical contract** for what an inbox file looks like
on disk. Tools writing to `_inbox/` must conform to this schema. Tools
reading from `_inbox/` may rely on it.

**Producers**: `/inbox` (skill), Trillian (vault-pulse), Deep Thought
callbacks, Marvin web UI, any future external tool.

**Consumers**: `/inbox`, `/transcript`, `/ops`, `/tasks`, Marvin web UI, MCP
clients.

**Skills MUST treat each `<id>.md` as the source of truth for its own
metadata.** `_inbox.yaml` (described below) is a derived index, rebuildable
from frontmatter. If frontmatter and index disagree, frontmatter wins.

---

## Layout

```
_inbox/
  _inbox.yaml                          # Derived index (cache, rebuildable)
  YYMMDD-HHMMSS[-slug].md              # Active items (one per inbox entry)
  .audio/                              # Hidden subfolder for raw audio
    YYMMDD-HHMMSS[-slug].m4a           # Paired with same-basename .md
  .files/                              # File drops: input files with a vault destiny (CR-024)
    YYMMDD-HHMMSS[-slug].<ext>         # Paired with same-basename .md stub
  .archive/                            # Processed items (existing convention)
    YYMMDD-HHMMSS[-slug].md
    .audio/
      YYMMDD-HHMMSS[-slug].m4a         # Audio archived alongside transcript
    .files/
      YYMMDD-HHMMSS[-slug].<ext>       # Source files that should NOT accompany their output
```

The leading dot on `.audio/` and `.archive/` keeps them out of Obsidian's
file pane and makes them easy to exclude from sync (audio bloats sync; only
transcripts need to travel between machines).

Exactly one `_inbox/` per vault, at vault root. Per-folder inboxes are not
part of this contract.

---

## File identifier

```
<YYMMDD>-<HHMMSS>[-<slug>]
```

- `YYMMDD` is creation date in vault-local time.
- `HHMMSS` is creation time in vault-local time.
- `slug` is optional, kebab-case, derived from a short title or content
  hint. Omit when no useful title exists yet.
- If two items share the same second (rare), append `_2`, `_3`, etc.

The identifier is also the filename basename (without extension). It pairs
the markdown and audio: `_inbox/250423-142214-meeting.md` and
`_inbox/.audio/250423-142214-meeting.m4a` are the same item.

Examples:

```
250423-142214-meeting-notes      # transcript with descriptive slug
250424-091803                    # short voice memo, no slug yet
250428-150000-test_2             # second item captured in the same second
```

---

## `_inbox/<id>.md` -- frontmatter schema

```yaml
---
# Required
id: 250423-142214-meeting-notes      # str: stable, matches filename basename
created: 2026-04-23T14:22:14+02:00   # str: ISO 8601 with timezone offset
classification: transcript            # str: see classification enum below
status: pending                       # str: pending|processing|processed|skipped

# Strongly recommended
confidence: high                      # str: high|medium|low (classifier confidence)

# Optional -- source attribution
source:
  type: audio                         # str: audio|email|paste|file|api|manual
  origin: voice_memo                  # str: free-form, e.g. voice_memo|dropbox|gmail|api|web_ui
  audio_path: _inbox/.audio/250423-142214-meeting-notes.m4a   # str: vault-relative
  audio_duration_sec: 142             # int
  ingestion_tool: trillian            # str: trillian|deep-thought|user|web_ui|...
  external_id: dt_abc123              # str: identifier in upstream system

# Optional -- routing intent (suggested by /inbox classifier; may be overridden)
target_skill: /transcript             # str: /transcript|/ops|/tasks|null
target_folder: _contacts/david-ekberg # str: vault-relative folder hint

# Optional -- user-supplied title or tags
title: "Samtal med David"             # str: short human-readable title
tags: [board-prep, q2-2026]           # list of str

# Filled when status moves to processed (set by /inbox)
processed_at: null                    # str: ISO 8601 or null
processed_by: null                    # str: skill name (e.g. /transcript) or null
output_file: null                     # str: vault-relative path of downstream output or null
archived_to: null                     # str: vault-relative path inside .archive/ or null
---

Markdown body of the captured content.
```

### Field rules

- **`id`** must equal the filename basename (without `.md`). A tool renaming
  one must rename the other.
- **`created`** is ISO 8601 with timezone. Tools without local timezone
  awareness may emit `Z` (UTC).
- **`classification`** values:

  | Value | Meaning | Typical target_skill |
  |-------|---------|----------------------|
  | `voice_memo` | Audio capture, may or may not have transcript yet | `/transcript` |
  | `transcript` | Multi-speaker transcribed dialogue | `/transcript` or `/ops` |
  | `email` | Forwarded email or pasted message | `/ops` or `/tasks` |
  | `quick_note` | Short observation, no action | none |
  | `raw_text` | Pasted text, classifier didn't fit it elsewhere | none |
  | `task` | Imperative, action item, "TODO" | `/tasks` |
  | `idea` | Brainstorm, "what if" | none |

  `classification` may be `null` if the item is awaiting classification (e.g.
  Trillian wrote audio + a stub markdown before `/inbox` ran).

- **`status`** values:

  | Value | Meaning |
  |-------|---------|
  | `pending` | Captured, not yet processed |
  | `processing` | Currently being handled by a downstream skill |
  | `processed` | Done; will be archived next |
  | `skipped` | Explicitly set aside by the user; kept for review, not archived |

- **`source.audio_path`** is vault-relative. Convention: `_inbox/.audio/<id>.m4a`.
  Pairing is by basename, not by this field -- the field is a convenience
  pointer.
- **`tags`** are free-form. Tools may use them for filtering but should not
  rely on a controlled vocabulary.

### Forgiving by design

Consumers must treat all fields except `id`, `created`, and `status` as
optional. A minimal valid file:

```yaml
---
id: 250428-091803
created: 2026-04-28T09:18:03+02:00
status: pending
---
```

This is valid. `/inbox` will classify it on the next run.

---

## `_inbox/.audio/<id>.m4a` -- audio convention

Raw audio captured by Trillian (or any future capture tool) lands in
`_inbox/.audio/`. The file format is whatever the capture tool produces;
`.m4a` is the convention for Apple Voice Memos and the iOS record-me app.

**Pairing rule**: `_inbox/.audio/<id>.m4a` and `_inbox/<id>.md` are paired
by basename. Tools that rename one MUST rename the other. The frontmatter
field `source.audio_path` is a convenience pointer; pairing is canonical
by basename.

**Orphan audio is allowed**. Trillian writes audio to `.audio/` as soon as
capture finishes. Deep Thought writes the transcript markdown later
(seconds to minutes). During that window, only the audio exists. `/inbox`
should:

- List orphan audio in status output (e.g. "1 audio awaiting transcript").
- Not auto-classify or auto-process orphan audio -- wait for the markdown.

**Retention** is user-configurable. Default: keep audio indefinitely (paired
with archived transcript in `.archive/.audio/`). A future
`/inbox prune --older-than 30d` subcommand can reclaim space. The schema
itself takes no position on retention.

---

## File drops -- `.files/` (CR-024)

`_inbox/.files/` generalizes the `.audio/` pattern to **any input file with
a vault destiny** -- a PDF to summarize, a CSV that becomes project data, an
export that will accompany content. `_inbox` is a door, not a residence:
files pass through on their way to their real home.

- **Drop:** put the file in `_inbox/.files/` (Finder, scp, mail save). Any
  filename is accepted at drop time; registration renames to the standard
  `YYMMDD-HHMMSS[-slug].<ext>` identifier.
- **Register:** `/inbox` (on capture, or lazily on the next `status`/
  `process` run) creates a stub `_inbox/<id>.md` pairing by basename --
  same mechanics as audio stubs -- with `source.file_path`, a type-based
  classification guess (PDF/document → summarize into a folder; CSV/xlsx →
  project data; image/media → attachment), and `status: pending`.
- **Process:** the downstream skill runs with the file as input. On
  completion the source file **moves with its output**: into the target
  folder's `.attachments/` (the placement `/ops` already defines) when it
  should accompany the content, else to `_inbox/.archive/.files/`. The stub
  records `output_file` and the file's final path.
- **Size guard:** files above ~25 MB are flagged at registration; prefer
  process-in-place + archiving a *reference stub* (path, hash, one-line
  description) over dragging the blob through iCloud-synced folders.
- **Orphans:** files in `.files/` with no stub are listed by
  `/inbox status`, same as orphan audio.

**Boundary (the routing rule):** if a file will produce or accompany vault
content, it enters through `_inbox/.files/`. If it has **no vault destiny**
(session scratch, repo snapshots, intermediate artifacts), it belongs in
`.ephemeral/` at vault root and is allowed to die there (see the
`.ephemeral/` contract in ops-base; `/ops sweep` ages it out after 14
days). Should something in `.ephemeral/` turn out to matter after all, it
exits through `_inbox/.files/` like anything else.

---

## Lifecycle

```
[ external tool writes audio + (optional) frontmatter-only md ]
            |
            v
[ status: pending -- appears in /inbox status ]
            |
            v
[ /inbox process -- classifies (if needed), routes, sets status: processing ]
            |
            v
[ downstream skill (/transcript, /ops, /tasks) processes the body ]
            |
            v
[ status: processed -- /inbox sets processed_at, processed_by, output_file ]
            |
            v
[ /inbox moves md to .archive/<id>.md and audio to .archive/.audio/<id>.m4a ]
```

State transitions are owned by `/inbox`. Other tools may write `pending`
items but must not advance status on their own; advancement happens through
`/inbox process`.

---

## Working documents & the triage surface (CR-022)

Not everything in `_inbox/` is a capture waiting to be processed. A
**working document** is a living file that *stays* in `_inbox/` as a
human working surface and is exempt from the lifecycle above.

**Registration:** `_inbox.yaml` entry with `type: working_doc`,
`status: keep`, and tag `do-not-process`. Frontmatter is optional for
working docs (they are never auto-processed, so there is no state to
carry). `/inbox process all` and every downstream skill MUST skip them.

**The triage doc** is the canonical working document: a rolling daily
sorting surface between capture and the systems of record. At most one
triage doc per vault.

**Design principle: skills adapt to the triage doc; the triage doc never
adapts to skills.** It is markdown, human-ordered, and paste-fast — that
low ceremony is *why* it stays alive where structured files rot. Skills
read around it; the only writes ever allowed are (a) the explicitly
invoked `/inbox triage refresh` mechanical upkeep and (b) a one-line
`→ i prep YYMMDD` stamp when a preparation pulls an item. Never reorder,
never reword, never re-bucket.

**Section vocabulary** (matched case-insensitively; Swedish canonical /
English equivalent; extra sections are allowed and ignored):

| Section | English | Meaning |
|---|---|---|
| `INKORG` | INBOX | Unsorted capture — paste here, human sorts later |
| `PRIO` | NOW | Do now / tomorrow |
| `DENNA VECKA` | THIS WEEK | This week's buckets |
| `EJ DENNA VECKA / SENARE` | LATER | Deferred |
| `UPPFÖLJNINGAR` | FOLLOW-UPS | Sent material / people to check on |
| `BESLUT ATT FATTA` | DECISIONS | Reasoning-in-progress, not tasks |

**Item shape:** checkbox bullets with bracket tags `[Område · Undernivå]`
(e.g. `[Möte · Bob]`, `[E-post · Carol]`, `[Uppföljning · David]`). Tags
are free-form; skills match the second segment against contact/team names
via standard name resolution.

**Week anchor:** a `Veckoankare:` line near the top (today + week number +
standing context). `/inbox triage refresh` keeps it current.

**Done-archive:** completed (`[x]`) items move to
`_inbox/.archive/YYMMDD-triage-klart.md` (append-only, never delete).

**Graduation rule (one item = one home):** when a triage bullet becomes
real work in a folder — a task in a `_tasks.yaml`, an outbox item, prep
content — it MOVES there with a link stamp left behind. It never forks
into two live copies. Triage is the personal system of record; per-folder
`_tasks.yaml` is the org/project system of record; this rule is the bridge.

**No-secrets rule:** the triage doc should not carry credentials (the
vault syncs through iCloud). Quick capture that includes a password gets a
password-manager reference stub instead; skills touching the doc flag
plaintext-credential lines rather than preserving them silently.

**Deliberate exception (`<!-- secret-ok -->`):** the owner may decide a
credential stays inline. A line ending in `<!-- secret-ok -->` is a
recorded decision — `/inbox triage refresh` and `/ops sweep` skip it
instead of re-flagging on every run (mirrors the `<!-- no-normalize -->`
convention in `/ops normalize`). Flag once, respect the answer.

---

## `_inbox.yaml` -- derived index

`_inbox.yaml` is a cache built from the frontmatter of all `_inbox/*.md`
files. It exists for fast reading by Marvin and `/inbox status` without
parsing every markdown file.

```yaml
version: 2                  # int: bumped from 1 when CR-012 lands
last_updated: 260429        # YYMMDD
items:
  - id: 250423-142214-meeting-notes
    title: "Samtal med David"
    classification: transcript
    status: pending
    file: 250423-142214-meeting-notes.md
    audio: _inbox/.audio/250423-142214-meeting-notes.m4a   # null if no audio
    created: 2026-04-23T14:22:14+02:00
    confidence: high
    routing:
      target_skill: /transcript
      target_folder: _contacts/david-ekberg
    processed_at: null
    output_file: null
```

`/inbox` rebuilds this file from frontmatter on every status/process call.
External tools writing pending items into `_inbox/<id>.md` MAY also append
to `_inbox.yaml`, but it is not required -- the next `/inbox` invocation
will pick up the new file from frontmatter and update the index.

If `_inbox.yaml` and frontmatter disagree, frontmatter wins. Tools that
inspect inbox state should prefer reading frontmatter for any specific
item; `_inbox.yaml` is for batch listing.

`version: 1` of `_inbox.yaml` (pre-CR-012) had a different schema -- see
the v1.13.0-v1.15.x `/inbox` skill SKILL.md for that shape. `/inbox`
detects v1 and rewrites it to v2 lazily on first run.

---

## Reading the file

```python
import yaml, frontmatter, glob

for path in sorted(glob.glob('_inbox/*.md')):
    item = frontmatter.load(path)
    if item.get('status') == 'pending':
        print(item['id'], item.get('classification', 'unclassified'))
```

Skills should treat a malformed frontmatter block as "unclassified, pending"
rather than failing -- the schema is forgiving by design.

---

## Versioning

This schema is version 1 (the file format -- not to be confused with
`_inbox.yaml`'s version). Breaking changes increment this version; consumers
should ignore frontmatter blocks they don't understand and fall through to
the minimal-required-fields contract.

The schema is referenced from `ecosystem.yaml` `vault_conventions:` for
`_inbox/` and `_inbox/.audio/` (CR-010, contract_version 2).

---

## Why hidden subfolders

The `.audio/` and `.archive/` folders use leading dots so:

- Obsidian's file pane skips them (no clutter for the user).
- iCloud / Obsidian Sync can be configured to exclude them (audio is heavy;
  archived transcripts are static).
- macOS Finder hides them by default.
- Tools that walk the inbox can detect raw vs processed at a glance.

This convention is consistent with the rest of the suite: `.archive/` is
already the established hidden-archive pattern in `_contacts/`,
`_projects/`, and per-folder ops outputs.
