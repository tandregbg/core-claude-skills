# CR-073 — `.handoff/` in Marvin: a listing, not a reader

| | |
|---|---|
| **Status** | Accepted 2026-09-22; built as marvin CR-013 |
| **Contract** | no change (24) |
| **Date** | 2026-09-22 |
| **Area** | Marvin (dispatching surface), `.handoff/` |
| **Related CRs** | **CR-033** (declares `.handoff/` and its total block), CR-036 (singleton placement), CR-038 (structural isolation) |

## The question

`_outbox/` has a surface in Marvin: list the items, read one, act on it. `.handoff/` is
structurally similar — dated markdown files, one bounded subject each, forty of them at vault
root — so the natural question is whether it gets the same treatment for little effort.

## Why the obvious answer is wrong

It would be about an hour's work, and it should not be done.

`.handoff/` carries a **total block** (CR-033): untouched by ops, insights, analytics, sweep, lint
and normalize; never indexed; read only when a human names one. It is the strictest surface in the
contract — stricter than `.transcripts/`, which is merely read-blocked.

The reason is not tidiness. A handoff snapshot is **outward-facing and self-carrying**: it is built
to be handed to a different session, or a different person, with no vault context attached. Some
carry a confidentiality boundary block stating what may not be repeated onward. Marvin's own
CLAUDE.md already draws the conclusion: *"They must never appear in any Marvin view ... surfacing
one in a browsable UI could route restricted content past the constraint that governs it."*

So a full `_outbox`-style surface — render the body, act on it — is not a small feature with a
caveat. It is the one thing the surface exists to prevent.

## What is proposed instead

The narrowest useful thing, and nothing beyond it: **a listing that names what exists and opens
nothing.**

- A page listing each snapshot's **filename, subject and date** — all of which are already in the
  filename, so no file is opened to build it.
- **No body rendering, no preview, no search inside, no excerpt.** Clicking a row reveals the path
  and a copy button, the way the outbox path card already works.
- `.handoff/_archive` excluded, as CR-033 requires.
- The page is reached deliberately (its own route, not a card on the dashboard), because "read only
  when a human asks for one by name" should be true of the surface as well as the file.

This answers the real question a person has — *did I write a handoff about this, and what is it
called* — without the tool ever reading the content. The block stays intact: Marvin learns nothing
from a snapshot that is not already in its name.

## Why this is still worth doing

Forty snapshots is past the point where a person remembers what exists. Today the only way to find
out is `ls` in a dot-folder that Obsidian hides. A name-only index is genuinely useful and costs
the contract nothing.

## Scope / non-goals

- **No contract change.** `.handoff/` keeps its writers and readers exactly as CR-033 declares them.
  Listing filenames is not reading, and this CR does not add Marvin as a reader.
- Does **not** render, quote, excerpt, index or search snapshot content — now or later. A future
  request to "just show a preview" is a request to undo the block, and should be refused here rather
  than negotiated per-field.
- Does not write. `.handoff/` is written once by `/handoff` and frozen; nothing else touches it,
  including to rename (which is why `.handoff/_archive` keeps its underscore against the
  archive-naming rule — CR-033 exception by necessity).

## The alternative, stated so it is a decision and not an oversight

If a browsable reader is genuinely wanted, the honest route is to amend CR-033 — decide the total
block is too strong, say why, and declare what replaces it. That is a contract conversation about
confidentiality, not a Marvin feature. It is not proposed here, and "least effort" is the wrong
reason to reach for it.


---

## Outcome (2026-09-22)

Accepted as argued: no `_outbox`-style surface, a name-only listing instead. Built in Marvin as
**CR-013** — route `/handoff`, rows carrying date, subject and filename parsed from the filename,
a path to copy, and `os.scandir` as the whole of the access.

Two things the build added that this CR did not anticipate:

- **A snapshot is sometimes a folder**, not one `.md` — a bundle carrying its own supporting
  files, which is the self-contained shape CR-033 describes. The first version listed 39 of 40 and
  hid a real one. Both forms list now, bundles marked with a file count.
- **The no-read constraint is a test**, not a comment: it patches `open`/`read_text`/`read_bytes`
  and fails if any fires. Verified by adding a preview and watching it fail. The realistic
  regression is not someone deciding to undo the block — it is "just add a preview" looking small
  in review.

Nothing in the contract changed, as proposed.
