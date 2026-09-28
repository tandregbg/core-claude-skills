# CR-102 — Rewriting a manifest keeps what the dispatcher wrote

| | |
|---|---|
| **Status** | **Implemented 2026-09-28, v1.86.0** — contract 36 |
| **Contract** | additive (35 → 36, or the next free number if another CR takes 36 first) — one rule on `_outbox/<item>/_manifest.md`; no new field |
| **Date** | 2026-09-28 |
| **Area** | `ops` (staging a recap or agenda into `_outbox/`), `outbox` (manifest schema), `vault_conventions` |
| **Related CRs** | CR-101 (a generated agenda is a draft; written in parallel the same day, same `ops` area), CR-047 (the dispatcher records what it did, never what it means), CR-053 (the status-note field), CR-064/066 (the dispatcher's other permitted fields) |

## What happened

A recap was staged in `_outbox/`, and the person sent it to a team chat through the dispatching
surface. Three minutes later a skill session, still working on the same meeting, rewrote that item's
manifest (and a sibling item's) to add a cross-reference. The rewrite was built from the skill's own
template, which carries no `Status` ("a human presses send"). The dispatcher saved `Status: skickad`
and a status note at almost the same moment. The file that survived was the skill's. The send had
happened, and the manifest said it had not.

Nothing in the rules was broken. `/ops` says: *"Author the manifest; never write `status` or
`status-note`."* The session did not write them. **It left them out of a file that already had
them, which erases them just as well.** "Never write" was specified; "keep what is there" was not.

## Why this matters more than one lost line

The status is the only record that something left the vault. `/outbox close --all-sent` archives by
it, the sweep's outbox-aging check counts by it, and a person deciding whether to chase a reply reads
it. A manifest that silently reverts to "not sent" invites a second send of the same message to the
same group, which is the one mistake an outbox exists to prevent.

The collision is also easy to reproduce. Skills stage an item and keep working on the same meeting
in the same session; the person sends from another surface as soon as it looks right. Two writers,
one file, seconds apart, and a synced vault where the last writer wins.

## Proposal

### 1. The rule, in `vault_conventions` on `_outbox/<item>/_manifest.md`

> **A manifest that already exists is edited, never regenerated.** A skill that changes an existing
> manifest changes only the lines it means to change, and carries every other line through verbatim.
> In particular the dispatcher-owned fields (`status`, `status_note`, `channel`, `contact`) are never
> dropped, reordered out of the field block, or reset to a template value by a skill.
> `level: invariant` — a violation loses the only record of a send.

### 2. `/ops` and `/outbox`: how to edit, not only what not to write

In `/ops` (staging) and `/outbox` (schema section), beside the existing "never write `status`":

- **Staging a new item** writes the manifest from the template, as today.
- **Changing an item that already has a manifest:** read it, edit the specific lines or sections in
  place, write it back. Never rewrite the file from the template.
- **Read immediately before writing, and compare.** If the manifest changed since the skill last read
  it (a status appeared, a field changed), stop and report instead of writing over it. A few seconds
  between reading and writing is exactly the window the collision above fell into.
- **A manifest whose `status` is past draft** (`klar-att-skicka`, `skickad …`, `avskriven …`) is
  treated as settled: body sections may be appended to (`## Utfall`, `## Tidslinje`), but the field
  block is left alone, and staging a *new version* of the material goes into a new item.

### 3. Sweep check

`/ops sweep`'s outbox-aging check gains one finding: **a manifest with no `status` in an item whose
folder or post log shows it was sent.** Where the dispatcher keeps a post log, that is a cheap
cross-check; where it does not, the finding is skipped and says so.

## What this does not do

- Does not add a lock file or a lease. The rule and the read-before-write compare are enough for two
  writers seconds apart; a lock is a second mechanism to go stale.
- Does not let skills write `status`. The send is a human act, recorded by the surface that did it.
- Does not change the dispatcher. On its side, the surface this came from now reads the manifest back
  after saving and reports a lost field instead of "saved" — the other half of the same fix.

## Acceptance

- Editing a staged manifest that carries `Status: skickad …` and a status note (e.g. adding a
  cross-reference to a sibling item) leaves both lines byte-identical and in the field block.
- A skill asked to update a manifest that changed after it last read it reports the change and does
  not write.
- `vault_conventions` carries the rule with `level: invariant`; `check-components.py` passes; contract 36.

## Outcome (2026-09-28, v1.86.0)

Implemented as proposed, contract 36:

- `vault_conventions` gains `manifest_edit_in_place` (`level: invariant`, `applies_to:
  _outbox/<item>/_manifest.md`); the manifest's own `lifecycle` points to it.
- `/ops` staging: the edit-in-place, read-before-write and settled-manifest rules follow the existing
  "never write `status`" paragraph, with the reason: not writing a field is not keeping it.
- `/outbox` schema: a section "Editing an existing manifest" states the same rule for the skill that
  owns the vocabulary, and notes that `close` follows it for the lines it does not mean to change.
- The sweep's outbox-aging check reports sent items with no status where the dispatcher keeps a record
  of what it posted, and says `not checked (no dispatch record)` where it does not. No tool or path is
  named: the record is the dispatcher's, and this contract does not own its format.

Acceptance 1 and 2 are behaviour of a skill following instructions, so they are verified by running
the next staging edit against a manifest that carries a status, not by a unit test.

