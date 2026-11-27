# CR-180 — `_callcards/`: one folder of short person cards, and a cross-section of who is next

| | |
|---|---|
| **Status** | **Implemented v1.98.0, contract 52** (2026-11-27). Proposed 2026-11-19 |
| **Contract** | New declared path `_callcards/` in `vault_conventions` (configurable through the config chain), a card format, and the folder added to the set every folder walk skips. Additive |
| **Date** | 2026-11-19 |
| **Area** | `ecosystem.yaml` (`vault_conventions` paths + skip rule), `ops-base` (folder-walk skip list), vault-side renderer (outside this repo) |
| **Related CRs** | **CR-038** (`.status/` — generated view isolation; this CR deliberately departs from it, see *Why not `.status/`*), **CR-033** (skip-lists missed by prefix globs), **CR-034** (prefix canon), **CR-005** / **CR-082** / **CR-107** (the per-meeting preparation card — a different object, see *Not a preparation*), CR-171 (display filenames live in config) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E]** A user keeping long-running strategy documents per person (50 kB each, ten sections, a log of every
conversation) asked for the opposite artefact: **a card that can be read in one minute before the next
conversation** — what the situation is, what to do and say, what *not* to say (source protection), what to
ask, and what is open with a date.

**[E]** Two existing surfaces came close and neither fits:

| Surface | Why it is not the card |
|---|---|
| The strategy document | Written to go back to, not to read on the way in |
| `<folder>/.status/current.md` (CR-038) | Built from insights and summaries, not from the strategy, so source-protection rules never reach it; one view per **folder**, so two people sharing a folder share one view; overwritten whole on every run |

**[E]** The user's binding constraint was physical: **one folder, pinned as a favourite on a phone.** A
dot-folder cannot be: the vault's editor and the phone's file app both hide it.

## The proposal

### 1. One folder, one card per contact folder

```
_callcards/
  _index.md                         the cross-section: today · tomorrow · this week · rolling
  <contact-folder-name>.md          one card per contact folder, named as the folder, lower-cased
  .archive/                         cards whose contact fell out of the window
```

- **The card's filename is the contact folder's name, lower-cased** — including any company or product
  suffix (`first-last_company.md`) and any non-ASCII letters. The folder name is already the identity
  everywhere else; lower-casing is the only transformation, because a list read on a phone with mixed
  case looks broken where some vaults capitalise organisational folders. Two folders that lower-case to
  the same name are reported, never merged. A folder holding several people yields one file with one
  section per person.
- **Frontmatter carries provenance:** `source:` (the contact folder, and the strategy document when one
  exists) and `derived: YYMMDD`. A renamed folder leaves a card whose `source:` no longer resolves — the
  renderer reports it rather than guessing.

### 2. The card format

Five headings, fixed, in this order. **At most 15 bullets per person.** Display labels come from the
vault's vocabulary (CR-171); the identifiers are:

| Identifier | Answers |
|---|---|
| `situation` | Where things stand, in three lines |
| `do_say` | What works with this person — formats, framings |
| `do_not_say` | Source protection and known traps. **Copied, never inferred** |
| `ask` | The open questions for the next conversation |
| `open` | Dated items, by task id — the card points at the task, it does not restate it |

`do_not_say` is the reason the card exists. It is **copied** from the strategy document when there is one;
when there is none, the heading says so (`no source-protection rules recorded`) rather than letting a model
infer rules about what may be said to whom.

### 3. Ownership: the renderer writes, nobody else

**One file, one writer.** The card is regenerated from its sources; it is never edited by hand and never
written by a session alongside the renderer. A session that updates a strategy document triggers a
re-render of that one card in the same step. A card that disagrees with its strategy document is stale by
definition — the strategy wins.

### 4. The cross-section

`_index.md` lists the contacts **in the window**: a conversation today through N days ahead (default 7),
or rolling contact (default: at least two conversations in the last 60 days). One line per contact —
when, one line of situation, the link. Cards for contacts that leave the window move to `.archive/`;
nothing is deleted.

### 5. The skip rule

`_callcards/` joins `.handoff/`, `.transcripts/` and `.status/` as **a path every folder walk skips**: no
parse, index, summarise, sweep, lint or insight extraction. It is a view of the vault, and a view read back
as source would synthesise a view of itself.

## Why not `.status/`

CR-038 put generated views in hidden subfolders because **[E]** skip-lists were missed by skills globbing on
the `YYMMDD-` prefix (CR-033). This CR keeps the purpose and gives up the mechanism, for a stated reason:
the reader is a phone, and a hidden folder cannot be pinned. The structural protection is replaced by
three weaker ones, all required:

1. **Declared skip path** in the contract, read by every walker (this CR).
2. **No card ever carries a `YYMMDD-` prefix or a role keyword** (`summary`, `agenda`, `preparation`) —
   the exact patterns that leaked `.handoff/`.
3. **One root folder rather than one per contact**, so a walker has a single path to exclude instead of a
   per-folder pattern to remember.

**[H]** Whether this is enough is not yet run. `/ops check` should report any skill output that cites a
`_callcards/` path as a source.

## Not a preparation

The preparation card (CR-005, CR-082, CR-107) is **per meeting**: dated, staged, frozen after the meeting.
A call card is **per person and rolling**: undated, overwritten, never closed. They answer different
questions — *what is this meeting for* versus *who is this person to me right now* — and the preparation
may cite the call card, never the reverse.

## What this repository changes

- `ecosystem.yaml`: declare `_callcards/` under `vault_conventions` paths (purpose, writers: the renderer;
  readers: user only; lifecycle: regenerated, archived when out of window, never indexed) and add it to
  the folder-walk skip rule. The path is a default; a vault may rename it through the config chain.
- `ops-base`: add the path to the walk skip list.
- No skill writes cards. The renderer is vault-side.

## Open

- The window (7 days ahead, 2 conversations in 60 days) is a first guess. **[H]**
- Whether `/preparation` should link the call card at the top of a new preparation.
