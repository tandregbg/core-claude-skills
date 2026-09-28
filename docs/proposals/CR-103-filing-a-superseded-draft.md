# CR-103 — Filing what was never sent: `close --all-resolved`, and superseded drafts into `.archive/`

| | |
|---|---|
| **Status** | Proposed |
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
