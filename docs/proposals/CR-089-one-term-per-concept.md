# CR-089 — One term per concept, and the loop's verbs are the commands

| | |
|---|---|
| **Status** | **Implemented 2026-09-26, v1.79.0** — contract 32 |
| **Contract** | **not additive** (31 → 32) — two skills leave the registry, two loop steps are renamed, subcommands are renamed. Every rename keeps its old name as an alias for one release |
| **Date** | 2026-09-26 |
| **Area** | `ecosystem.yaml` (new `terms:`, `skills`, `working_loop`, `vault_conventions`), every user-invocable skill's subcommands, `ops-config` strings and filename keywords, `scripts/check-ecosystem-alignment.sh`, README, `docs/SKILLS-COMPARISON.md`. Outside this repo: the landing page (2.0), and every component that invokes a renamed command |
| **Related CRs** | CR-021 (slug contract), CR-034 (prefix conventions), CR-062 / CR-077 (the loop and orientation rendered from the contract), CR-082 (one way to make an agenda), CR-088 (fetch record — already says *fetch*) |

## What happened

An audit of the suite against its own landing page found the same defect in four places: **one
concept, several words, and nothing that compares them.**

**1. Three vocabularies for one sequence.** The loop the landing page leads with names its steps
`orient`, `archive`, `agenda`, `process`, `check`. The commands a person types for the same steps are
`/ops brief`, an external archiver, `/ops prepare` (or `/preparation`), `/ops`, `/ops lint` +
`/ops sweep`. Several steps point at a script path instead of a command. A reader learns one set of
words on the loop page and a second at the prompt.

**2. Competing words for one artifact.** Counted across `skills/`, `ecosystem.yaml` and the README:

| Concept | Words in use |
|---|---|
| What *process* writes | summary 263 · the note 26 · sammanfattning 16 |
| What *prepare* writes | agenda 239 · preparation 226 · förberedelse 57 |
| A commitment with an owner | task 542 · action 211 · action item 58 · åtgärd 17 |
| Where tasks live | register 59 · ledger 45 — and *register* also names the generated `_INDEX-*` files |
| A promoted insight / a contract rule | rule 226, for both |
| *archive* | the archivers' fetched copy · the `.archive/` retirement folder · `/outbox archive` |

**3. The same verb meaning different things.** `normalize` fixes Swedish characters in `/ops` and
migrates a schema in `/insights`. `process` routes stored items in `/inbox` and would write the
meeting note in `/ops`.

**4. The declared subcommands drifted from the skills.** `ecosystem.yaml` lists six `/ops`
subcommands; the skill has nine (`brief`, `projects`, `project new` are missing). The landing page
renders the contract, so it publishes the gap faithfully. **Nothing compares a SKILL.md to the
contract** — `check-ecosystem-alignment.sh` compares versions, the skill count and the component
graph.

Two further findings from the same pass:

- **Two skills sit outside the loop.** `daily-dashboard` has no recent output on the one production
  vault measured (last written five months ago) yet seven skills still reference its refresh step.
  `md2pdf` is referenced by no other skill and belongs to no loop step.
- **The alignment check verifies a retired site.** It reads the landing page's version from a mount
  of the Flask build (`app.py`, `static/i18n/en.json`). The live site is the 2.0 rebuild, which has
  neither file, so the check reports `[OK]` against a version no one is served.

## Decisions (taken 2026-09-26)

1. **Identifiers are English; attributes are localized.** Skill names, subcommands, loop steps,
   config keys, term ids — English, always. Headings, labels, strings — localized, **but only from
   the `sv:` (or other language) column of `terms:`**. A localized word not declared there is drift.
2. **Filename role keywords are identifiers**, so English. The description part of a filename stays
   in the working language with å/ä/ö (CR-021 unchanged): `YYMMDD-<role>-<description>.md`.
3. **Forward only.** No existing file is renamed or edited. Old keywords are declared as `legacy:`
   and read by every reader; the check flags only files dated on or after the release.
4. **A declared series name wins.** A `note_suffix` / `agenda_suffix` in config is never rewritten
   to the new keyword — a series that changed shape mid-history would read as a broken chain.
5. **`/ops`, `/transcript` and `/preparation` keep their names**, declared in `terms:` as command
   names. `/ops` is the major part of the suite and typed daily; `/transcript` names what it receives
   (it does not transcribe — `/transcription` would claim a job done upstream).
6. **The loop's verbs are the command verbs.** Every loop step a person runs maps to exactly one
   command with the same verb; the rest are declared `manual` or `external`, as today.
7. **`rule` stays with the insight lifecycle** (hypothesis → rule). The contract's rules become
   **conventions**.
8. Swedish attributes: carry-forward → **överföring**, ledger → **uppgiftsregister**.

## Proposal

### 1. `terms:` in `ecosystem.yaml`

One entry per concept. `file:` is present where the term is also a filename role keyword.

```yaml
terms:
  # places
  - {id: vault,        en: vault,        sv: valv}
  - {id: venture,      en: venture,      sv: verksamhet,     avoid: [org, organisation]}
  - {id: project,      en: project,      sv: projekt,        avoid: [pipeline]}
  - {id: contact,      en: contact,      sv: kontakt}
  - {id: config,       en: config,       sv: konfiguration,  avoid: [org config, ops config]}
  # meetings
  - {id: meeting,      en: meeting,      sv: möte}
  - {id: series,       en: series,       sv: serie}
  - {id: session,      en: session,      sv: session,        note: "a Claude Code session only"}
  - {id: transcript,   en: transcript,   sv: transkript,     avoid: [raw transcript]}
  - {id: summary,      en: summary,      sv: sammanfattning, verb: process,
     file: summary,    legacy_file: [samtal, sammanfattning, möte], avoid: [the note, minutes]}
  - {id: agenda,       en: agenda,       sv: agenda,         verb: prepare,
     file: agenda,     legacy_file: [förberedelse, preparation], avoid: [prep]}
  - {id: facilitator-sheet, en: facilitator sheet, sv: facilitatorsblad, verb: facilitate,
     file: facilitator, avoid: [facilitator notes, facilitator file]}
  - {id: carry-forward, en: carry-forward, sv: överföring,   verb: carry,
     avoid: [carried items, carry-over]}
  - {id: recap,        en: recap,        sv: recap,          verb: recap, file: recap}
  - {id: priorities,   en: priorities,   sv: prioriteringar, file: priorities}
  # work and knowledge
  - {id: task,         en: task,         sv: uppgift,        avoid: [action item, åtgärd, todo]}
  - {id: ledger,       en: ledger,       sv: uppgiftsregister, note: "matches workflows.task_ledger"}
  - {id: index,        en: index,        sv: index,          note: "the generated _INDEX-* files",
     avoid: [register]}
  - {id: insight,      en: insight,      sv: insikt}
  - {id: rule,         en: rule,         sv: regel,          note: "an insight confirmed often enough to be loaded as a standing instruction"}
  - {id: convention,   en: convention,   sv: konvention,     note: "the contract's rules for the vault"}
  - {id: wiki,         en: wiki,         sv: wiki,           verb: compound, avoid: [knowledge base]}
  - {id: handoff,      en: handoff,      sv: överlämning,    file: handoff, avoid: [snapshot]}
  # movement and retirement
  - {id: fetch,        en: fetch,        sv: hämta,          note: "external system into a local archive",
     avoid: [archiver]}
  - {id: archive,      en: archive,      sv: arkiv,          note: "the fetched local copy only"}
  - {id: snapshot,     en: snapshot,     sv: ögonblicksbild, note: "a dated file inside an archive"}
  - {id: retire,       en: retire,       sv: pensionera,     note: "to .archive/ or a tombstone"}
  - {id: close,        en: close,        sv: stänga,         note: "a resolved outbox item, filed with its recipient"}
  # command names kept as names (decision 5)
  - {id: ops,          en: ops,          kind: command_name}
  - {id: preparation,  en: preparation,  kind: command_name, note: "the config-free form of /ops prepare"}
```

`avoid:` words are matched case-insensitively on word boundaries. A term's own `note:` explains an
unavoidable overlap rather than exempting it.

### 2. The naming rule

- **A skill is a noun**: the place or object it owns. Declared exceptions are `kind: command_name`.
- **A subcommand is a verb**, or `<object> <verb>` where a skill manages several kinds of object.
- **The default action also has an explicit name.**
- **One verb, one meaning, across all skills.** `status` shows state · `list` lists items ·
  `migrate` upgrades a schema · `help` shows usage. Every user-invocable skill has `help`.
- **Anything outside the loop is named for what it repairs or explains**, never with a loop verb.

### 3. The loop, renamed

| Step | Was | Command |
|---|---|---|
| declare | declare | `/ops project new` · `/ops status` (resolved config) |
| orient | orient | `/ops orient` |
| **fetch** | archive | external |
| **prepare** | agenda | `/ops prepare` · `/preparation` without config |
| facilitate | facilitate | manual |
| meet | meet | external |
| process | process | `/ops process` (the default) · `/transcript` without config |
| carry | carry | written by process, checked by `/ops check` |
| recap | recap | manual |
| send | send | `/outbox list` |
| deliver | deliver | external |
| record | record | manual |
| compound | compound | `/insights compile`, `/insights synthesize` |
| check | check | `/ops check <folder>` · `/ops check` |

Each step's `command:` names a command, never a script path. Scripts remain what a command runs.

### 4. Subcommand renames (old names are aliases for one release)

| Old | New | Why |
|---|---|---|
| `/ops [content]` | `/ops process` (still the default) | the loop verb, made visible |
| `/ops brief <folder>` | `/ops orient <folder>` | the loop verb |
| `/ops lint <folder>` | `/ops check <folder>` | the loop verb; folder scope |
| `/ops sweep` | `/ops check` | the loop verb; vault scope |
| `/ops projects` | `/ops project list` | pairs with `/ops project new` |
| `/ops status` | `/ops status`, extended | adds each project's **resolved config, layer by layer, validated against `schema.md`** — the only place a person can see what every project is configured to do |
| `/insights normalize` | `/insights migrate` | same meaning as `/tasks migrate`; frees `normalize` |
| `/inbox process` | `/inbox route` | it routes; frees `process` |
| `/outbox archive` | `/outbox close` | frees *archive*; `--all-sent` unchanged |
| `/tasks show` | `/tasks list` | the shared verb |
| — | `help` on `/tasks`, `/transcript`, `/preparation`, `/update-skills` | every invocable skill has it |

`/ops normalize` keeps its name: with `/insights` no longer using it, it means one thing.

### 5. Filename role keywords

New files: `summary`, `agenda`, `facilitator`, `recap`, `priorities`, `handoff`. Dual-mode prepare
stops being English-only by accident and becomes English by rule, in every language.

Every reader that matches role keywords — supersede marking, companion-artifact exclusion, `check`,
`orient`, `project list` — reads `file` **and** `legacy_file`. On one production vault that is
over 1,000 existing files kept readable without a rename.

### 6. Retire `daily-dashboard`

Remove the skill, its registry entry, the `_Dashboard*.md` entries in `vault_conventions`, and the
refresh step in the seven skills that reference it. `workflows.post_processing.dashboard_refresh` is
read for one release and ignored with a one-line deprecation note, so no config fails. Existing
dashboard files are left for the operator to retire (ops-base Retirement Convention).

### 7. Move `md2pdf` out of the suite

To the operator's personal skill repository. `--outbox` keeps working: it writes a manifest per the
contract, which any tool may do. `/update-skills` keeps creating its symlink from the new repo.

After 6 and 7 the registry holds **10 user-invocable skills and 2 shared modules**.

### 8. Registry order follows the loop

`inbox, preparation, transcript, ops, outbox, tasks, handoff, insights, analytics, update-skills`.
The landing page renders in declared order, so this is the only place order is set.

### 9. Close the unchecked link

`check-ecosystem-alignment.sh` gains three checks, each printing `[OK]` / `[DRIFT]`:

1. **Subcommands** — every `### \`<name>\`` subcommand heading in a SKILL.md appears in that skill's
   `subcommands:`, and every declared subcommand has a heading. Aliases are declared as such.
2. **Terms** — no `avoid:` word in `skills/`, the README or `docs/SKILLS-COMPARISON.md`, outside
   code blocks and quoted history (CHANGELOG, `docs/proposals/`).
3. **Landing page** — read the 2.0 build's version endpoint and its hand-written content directory,
   not the Flask files. An unreachable site is `[SKIP]`, reported as unverified (as today).

### 10. Prefix convention

Drop `_PLAN-*` from the examples in the prefix convention. Root-level shortcut symlinks are not
structure-bearing files that recur per folder; a vault that wants them declares them itself.

## Outside this repo

| Where | What |
|---|---|
| Landing page 2.0 | Rebuild; replace the hard-coded "fourteen parts, twelve with a command" in both languages with a count; render `terms:` in the A–Z index with definition, Swedish form, loop verb and command; move `/the-contract/rules` to `/the-contract/conventions` with a 301 |
| Components that invoke renamed commands (the dashboard, the capture app, the vault tools, the operator's other skill repos) | Switch to the new names within the alias release |
| The operator's vault | `CLAUDE.md` files and configs that name renamed commands; the root shortcut symlinks, if the operator retires them |

## What this does not do

- Rename or edit any existing file in a vault.
- Rename `/ops`, `/transcript` or `/preparation`.
- Change any declared `note_suffix` or `agenda_suffix`.
- Reduce the size of `/ops`. It now spans five loop steps under consistent names; splitting it is a
  separate question.

## Acceptance

- `ecosystem.yaml`: `contract_version` 32; `terms:` present; `working_loop` steps `fetch` and
  `prepare`; every step's `command:` names a command or the step is `manual`/`external`; registry
  holds 10 + 2 in loop order.
- Each renamed subcommand works under both names; the old name prints a one-line notice naming the new.
- A new `/transcript` run writes `YYMMDD-summary-…`; a folder holding `…-samtal-…` files is still read
  as one series by `orient` and `check`.
- `check-ecosystem-alignment.sh` reports `[DRIFT]` when a SKILL.md subcommand heading is missing from
  the contract, and when `the note` is added to a SKILL.md.
- The landing page shows 12 skills in loop order with no hard-coded count.
- **Proposed release: minor (1.79.0)** — to be confirmed by the maintainer.

## Outcome (2026-09-26, v1.79.0)

Implemented as proposed, with four deviations found while doing it:

- **`avoid:` holds only phrases that can be replaced mechanically.** `org`, `pipeline`, `register`,
  `snapshot`, `prep`, `todo` and `minutes` each have a legitimate second meaning in the skills (the
  config key `organization`, the project `registry:`, an archive snapshot), so they are explained in
  the term's `note:` instead of being banned. **`action item` and `åtgärd` are not banned either:
  `Action` / `Åtgärd` is the action-table column in the template contract (CR-018)**, and renaming a
  contract heading would report every existing series as forked at the release date.
- **`/ops check` takes one optional argument.** A folder runs the folder checks (was `lint`); no
  argument runs the vault checks (was `sweep`); `--vault <scope>` runs the vault checks on a subtree.
  Otherwise `check <path>` could not tell a lint folder from a sweep scope.
- **`/tasks migrate` was removed from the contract, not documented.** It was declared from the
  first contract and never existed in the skill.
- **The landing page check reads the live site's `/version.json`.** The mount it read held the
  retired Flask build and reported `[OK]`. Its first run: live site built from v1.77.0 / contract 30.

Done in this repo: `terms:`, the two rules (`filename_role_keyword`, `one_term_per_concept`), loop and
registry, every SKILL.md, `base.yaml` / `schema.md` (filename keywords English; dashboard keys and
strings retired), README, `docs/SKILLS-COMPARISON.md`, `scripts/check-terms.py` with tests, the
alignment check. `md2pdf` committed to the personal skill repository.

**Not done here** — each is a separate commit in its own place: rebuilding and deploying the landing
page (and the hard-coded count text and `/the-contract/rules` route there); the components that
invoke renamed commands (the aliases cover them for this release); the vault's own `CLAUDE.md` files.
