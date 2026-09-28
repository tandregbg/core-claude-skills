# CR-103 — Filing what was never sent: `close --all-resolved`, and superseded drafts into `.archive/`

| | |
|---|---|
| **Status** | **Implemented 2026-09-28, v1.86.0** — contract 37 |
| **Contract** | additive — one parseable note form for `avskriven`, one filing destination; no new field |
| **Date** | 2026-09-28 |
| **Area** | `outbox` (`close`, `list`, manifest schema), `ops` staging (status vocabulary) |
| **Related CRs** | CR-047 (`avskriven`: resolved without being sent; proposed `--all-resolved`), CR-102 (a new version is a new item), CR-032 (`Kanonisk källa`) |

## What happened

A reply was drafted and staged as one outbox item. The same day the reply was rewritten after a
decision changed, staged as a second item, and sent. The first draft stayed in `_outbox/` marked
ready to send. It was later marked `avskriven` with the note *"ersatt av <the second item>"* through
a dispatching surface — the correct status — and then there was nothing more to do with it:

- **`close` needs one item at a time.** CR-047 proposed `close --all-resolved` for exactly this; only
  `close --all-sent` exists. Resolved-but-unsent items therefore accumulate until someone closes them
  by name.
- **A superseded draft is filed like correspondence.** `close` moves an item into the contact's or
  project's folder, beside what was actually sent. A draft that was never sent and was replaced is not
  part of that history; filed there, it reads as a second message that went out.
- **The draft's status was written in a word the schema does not have** (`redo att skicka` rather than
  `klar-att-skicka`). A tool reading the declared values treats it as unknown.

## Proposal

### 1. `close --all-resolved`

Closes every item whose status is `avskriven …`, on the same terms as `close <item>` (CR-047: `##
Utfall` must say why — written by the skill from the status note when it is absent). Reports each
item and where it went. `--all-sent` is unchanged; `close --all` runs both.

### 2. Superseded drafts go to the contact's `.archive/`

When an `avskriven` note starts with the parseable form **`ersatt av <item-name>`** (declared in the
outbox schema; the dispatching surface writes it from its vocabulary file), the item is a superseded
draft:

- It is filed to `<contact-or-project folder>/.archive/<YYMMDD>-<subject>-superseded/`, not beside
  the correspondence. Nothing is deleted; a dot-folder keeps it out of routine reading (CR-034) while
  the reasoning stays traceable.
- `## Utfall` is written as *"Ersatt av <item-name> (<its status>)"*, and the replacing item's
  manifest gets one appended line under `## Tidslinje`: *"Ersätter <item-name> (avskriven <date>)"*
  — an append to a settled manifest, which CR-102 permits.
- If the named item does not exist in `_outbox/` or among closed items, the draft is filed as an
  ordinary `avskriven` item and the missing reference is reported.

### 3. Staging writes only declared status words

`/ops` and `/outbox`, when staging, write `status` only from the schema's list (`draft`,
`klar-att-skicka`). `/ops sweep`'s outbox check reports any manifest whose status is not one of the
declared forms, naming the file and the closest declared value — a report, never a rewrite.

### 4. `list`

`RESOLVED, NOT SENT` (CR-047) shows superseded drafts with *"superseded by <item>"*, so the pending
view and the resolved view say the same thing the dispatching surface shows.

## What this does not do

- **Delete.** The rule stays "never delete files, only move" (Behaviour rules). A superseded draft is
  moved out of sight, not removed.
- **Decide that something is superseded.** A person marks it; the skill files it.
- **Change `close --all-sent`.**

## Acceptance

- Two items for one contact, the first `avskriven` with `ersatt av <second>` and the second `skickad`:
  `close --all-resolved` files the first to `<contact>/.archive/…-superseded/` with `## Utfall`
  written, and appends the `Tidslinje` line to the second without touching its field block.
- An `avskriven` item without the `ersatt av` form is closed as today, into the contact folder.
- `/ops sweep` reports a manifest with `Status: redo att skicka` and names `klar-att-skicka`.

## Outcome (2026-09-28, v1.86.0)

Implemented as proposed, contract 36 -> 37 (the status vocabulary and the superseded form are now
declared in `ecosystem.yaml` on `_outbox/<item>/_manifest.md`: `status_forms`, `status_forms_rule`,
`superseded_note`). Shipped in the same pending release as CR-101 and CR-102.

- **The deterministic part is code:** `skills/outbox/resolved.py` lists withdrawn items, parses the
  `ersatt av` form, finds the replacing item (in `_outbox/`, else among closed items by folder name or
  by the `_outbox/<name>` origin line), and prints the plan -- archive sub-path, outcome line, timeline
  line -- plus undeclared status words with the closest declared one. It never moves, writes or
  deletes; the skill shows the plan and moves after confirmation.
- **Decided during implementation:** `close` now writes the item's origin into its timeline
  (``stängd från `_outbox/<name>` ``). A closed item is usually renamed, so without that line a draft
  closed after its replacement could not find it and would be misfiled as an ordinary withdrawal.
- **Closest declared form** uses a short synonym table first ("redo"/"klar" -> `klar-att-skicka`)
  and a strict fuzzy match second; a word with no likely meaning (a blocking marker, say) gets no
  guess rather than a wrong one.
- **Command name:** the sweep is `/ops check` since v1.79.0; the proposal's "/ops sweep" means that.
- **Verified read-only on one vault:** the helper found the one real superseded draft, its replacing
  item (already sent, still in `_outbox/`), and planned `.archive/<date>-<subject>-superseded/`; it
  also listed the undeclared status words in use. Nothing was moved.

**Correction (2026-09-28), found by the first read-only run on a real outbox.** The plan printed the
manifest's free-text project field as a folder, and suggested `skickad` for a status reading "not
sent". The helper now offers only existing folders (project by the field's leading slug; contacts by
the name before any parenthesis) and never suggests a negated word. Tests pin both.
