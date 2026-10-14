---
name: company
description: A company profile with an open contract and an optional private template. Keeps a current, source-backed picture of an organisation in `<org>/_company/` that people and agents can act on: create the skeleton, collect sources, check for drift, build one readable profile, export derived files. The structure is open; a question set, if you have one, is read from `company.template:` and is not part of this repository.
user-invocable: true
argument-hint: <init | intake | check | build | export> [org] [| help]
---

# /company -- the company profile (CR-125)

Agents that write for a company (a proposal, a landing page, an agenda, an ad) keep re-deriving the same facts:
what the company is, who it sells to, what it may claim, how it sounds. `/company` keeps those facts in one
place, with the source of each, so every other skill can read them instead of asking again.

**Open and optional.** This skill carries the *structure*: where the profile lives, what its files are called,
what they carry, the rules, the checks. It carries **no questions and no method**. What to ask, in which order,
to what standard, comes from an optional template you point at with `company.template:`. Without one the skill
still works with the plain skeleton; it tells you so. Nothing in this repository reproduces a template.

The contract is `references/contract.md`; read it before writing a profile file.

---

## When to use it

| You want | Use |
|---|---|
| The standing facts about a company, with sources, readable by agents | `/company` |
| What was said and decided in a meeting | `/transcript`, `/ops process` |
| A living document with one person | `/correspondence` |
| Where one project stands | `/ops orient <folder>` |

A profile is **current truth about the company**, not a record of events. It is regenerated or edited when
the facts change; events go to the meeting archive.

---

## Subcommands

### `init <org>`

Creates `<org>/_company/` with the plain skeleton for the configured level (`company.level`, default `light`):
one file per facet in play, `README.md`, `AUDIT-LOG.md`, empty `sources.yaml` and `brands.yaml`, `.intake/`.
Run `python3 ~/.claude/skills/company/company_tool.py init <org-folder> --vertical <v> [--level L] [--language xx]`.
It never overwrites an existing folder. With `company.template:` set, read the question set from there and say
which; without it, say that no question set is attached and stop at the skeleton.

### `intake <org>`

1. **Sources first.** Fill `sources.yaml`: every place a fact may come from (vault paths, hosts, repositories,
   URLs, dropped material in `.intake/`), each with `authority` and the facets it `feeds`; and an `exclude` list
   of what is off-limits, with a reason. Read sources in place and never edit them.
2. **Synthesis.** For each facet in play, list per item: what is established (with source markers), what
   conflicts (both values, both sources, never resolved silently), what is missing, what needs a decision.
   Summarise the understanding for the owner to confirm before writing facet text.
3. **Write each facet** from its sources, one facet at a time, within its own scope; link to other facets
   instead of repeating them. Open items read `_Not provided yet._` Apply the never-say list.
4. **Decisions** are not made by the skill. Mark them and hand them to the owner; record the owner's answer as
   a dated `interview:<date>` source.

### `check [org]`

Report only; nothing is rewritten.

```
python3 ~/.claude/skills/company/company_tool.py check <vault-or-org-folder> [--copies] [--max-age-days N] [--json]
```

The script reports a stale facet (no review or generation within `company.max_age_days`, default 365, or status
`stale`), schema errors in the frontmatter and in `sources.yaml` / `brands.yaml`, a facet marked `draft-locked` or
`final` with no sources, a **credential-looking value anywhere in a profile**, and with `--copies` any profile
file outside `_company/`. Then read the files for what a program cannot decide:

- a **status claim** ("active", "live") with no recent evidence, or a paused business written as running;
- a **fact without a source marker**, or a number without a date and a definition;
- a **contradiction between facets**, or a never-say breach;
- a guide judged "missing" because the folder holding it was excluded: check `exclude` before concluding.

Offer fixes; apply none without being asked.

### `build [org]`

Assembles the facets in play into one readable profile for a person or an agent: in facet order, sources
resolved, gaps and conflicts kept visible. Writes to `exports/` only if asked; the facet files remain the source.

### `export <target> [org]`

Writes a derived file for another system into `exports/<target>/`. Derived means regenerated, never hand-edited.
The first target is an external search-visibility tracker: the subject, one buying category, named competitors
(companies only, never the brand itself), six to twelve organic buying situations that do not name the brand,
and a short context line per market language. Where search data exists it beats the profile. Service keys are
referenced from `company.services`, never written into an export.

### `help`

Print this skill's subcommands, the contract's location (`references/contract.md`), and whether `company.template:` is set.

---

## Configuration

`company:` in `<org>/_ops.yaml` or the vault's `_config/base.yaml` (defaults in `ops-config/base.yaml`):

```yaml
company:
  level: light            # public | light | medium | full
  language: en
  max_age_days: 365       # a facet older than this is reported stale
  template: null          # path or address of an optional private template; null = the plain skeleton
  services: {}            # references only: {ranking: {account: acme, key_ref: "env:RANKING_KEY"}}
```

A key **value** in any profile, `sources.yaml`, `brands.yaml` or repository is an error.

---

## Readers

`/ops` (orient, prepare, check) and `/preparation` load the facets relevant to the task when a `_company/`
exists for the organisation, and say nothing when it does not. A reader never writes to a profile. Skills in
other repositories that write for a company (brand imagery, website scaffolding, change-request intake) read
the same folder under the same contract.

## Privacy

A profile is customer data. It lives in the organisation's own area, is never an example in a skill or a test,
and never carries credentials or private one-to-one content. Examples here use invented companies.
