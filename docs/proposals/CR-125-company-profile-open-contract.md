# CR-125 — `/company`: a company profile with an open contract and an optional private template

| | |
|---|---|
| **Status** | **Implemented 2026-10-14, v1.91.0** (committed locally; not pushed) |
| **Contract** | additive, `contract_version` 42 to 43, `ops_config` 1.5 to 1.6. A new optional path `<org>/_company/`, new optional `company:` block in ops-config. A vault that sets nothing behaves as before |
| **Date** | 2026-10-14 |
| **Area** | `ecosystem.yaml` (`vault_conventions`), new skill `company`, `ops-config` (`company:`), `ops` (`check`), readers: `ops`, `preparation`, `cr-intake`, `website-create` |
| **Related CRs** | CR-123 (`profile:` already means meeting/podcast in ops-config, hence `facet:` here), CR-122 (report-only check pattern), CR-026 (release guard) |
| **Companions** | An optional private template repository and a token-gated read service, both outside this repository |

## What happened

Agents that write for a company (a proposal, a landing page, an agenda, an ad) keep re-deriving the same
facts: what the company is, who it sells to, what it may and may not claim, how it sounds. Five company
profiles were built by hand in one vault; the same failures recurred in each:

- an older sales document presented as proof without checking it against the engagement record;
- a profile saying "active" for a business its owner has paused;
- a published site breaking the brand's own written rules, and the profile describing the rules as the site;
- a guide judged "missing" because the folder holding it was excluded from the scan;
- service keys written into the profile.

None of this needs a particular method of brand strategy. It needs a place, a file contract and a few checks.
The method (which questions to ask, in which order, to what standard) is a separate asset that some users
will own and others will license; it must be possible to use the skill with no method at all.

## Decisions (taken 2026-10-13/14)

| Question | Decision |
|---|---|
| Open or closed? | **The structure and process are open** (this repository). **A question set, if one is used, is a separate private template** the skill reads from a path or an address; this repository carries none |
| Folder name | `_company/` (not `_profile/`) |
| Frontmatter key | `facet:` (not `profile:`, which CR-123 uses for the project profile) |
| Skill name | `/company` |
| Secrets | Never in a profile. A profile names a key by reference, one key per paying account, never per profile |
| Examples | Invented companies only. Real profiles are customer data and never appear here |

## Proposal

### 1. The path and the files (`<org>/_company/`)

One folder per organisation, next to its other top-level folders. A file per **facet**; a facet is a
subject the company must be able to state. The names and one-line purposes are the contract:

| Facet | Purpose |
|---|---|
| `essence` | The core: why the company exists, where it is heading, what it stands for |
| `company` | Who and what it is: owners, roles, numbers, siblings, current focus |
| `offering` | What is sold now: status, version, price, what is decided next |
| `positioning` | Where it stands: segments, value, differentiation, competitors, what it may claim |
| `messaging` | What it says: the message framework, the words to use and avoid |
| `gtm` | How it wins: audience, journey, qualification, channels, partners, pipeline |
| `strategy` | Where it goes: direction, bets decided or draft, open questions, horizon |
| `brand` | How it sounds and looks: voice, rules, vocabulary, visual rules, images |
| `public` | Only what outsiders can already see |

Each file carries frontmatter: `vertical`, `facet`, `level` (`public` | `light` | `medium` | `full`), `status` (`draft` |
`synthesis-locked` | `draft-locked` | `final` | `stale`), `generated`, `reviewed`, `language`, `sources`. Every fact in the body
carries a source marker. Numbers carry a date and a definition. Open items are listed with a reason, never
guessed.

Support files: `README.md` (state and open questions), `AUDIT-LOG.md` (what was checked against what),
`sources.yaml` (where the facts came from and which folders were excluded), `brands.yaml` (brand
assets and rules; unknown values are written `unknown`, never omitted), `exports/<target>/` (derived
files for other systems).

### 2. The contract (`skills/company/references/contract.md`)

Facet names and purposes, the frontmatter keys, the source-marker rule, the `sources.yaml` and
`brands.yaml` schemas (JSON Schema, in `docs/schemas/`), the level definitions as *how much must be
answered*, not *what is asked*. No question text.

### 3. `ecosystem.yaml`

`vault_conventions`: the path `<org>/_company/`, its purpose, the file patterns and the frontmatter keys.
`contract_version` 42 to 43, with the explanatory comment block the earlier bumps carry.

### 4. `ops-config`: the `company:` block

```yaml
company:
  level: light            # light | medium | full
  language: en
  max_age_days: 365       # a facet older than this is reported stale
  template: null          # path or address of an optional private template; null = built-in skeleton
  services:               # references only
    ranking: {key_ref: "password-manager:item-name"}
```

Key **values** anywhere in a profile, `brands.yaml`, `sources.yaml` or a repository are an error.

### 5. Verbs

| Verb | What it does |
|---|---|
| `/company init <org>` | Creates `_company/` with the skeleton for the configured level. With `template:` set, takes the question list from there; without, writes the plain skeleton and says so |
| `/company intake <org>` | Collects sources (documents, site, transcripts, engagement records), writes `sources.yaml`, drafts facets with source markers, lists open items |
| `/company check [<org>]` | Report only. Stale facets; files outside `_company/` that duplicate it; schema errors in `sources.yaml` and `brands.yaml`; a key value in a profile; a facet marked `decided` without a source; a status claim ("active") with no recent evidence |
| `/company build <org>` | Assembles the facets into one readable profile for a person or an agent |
| `/company export <target>` | Writes a derived file for another system into `exports/<target>/`. First target: an external search-visibility tracker (subject, needs, queries). Derived, so regenerated, never edited |

### 6. `/ops check` and readers

`/ops check` gains one line that runs the `/company check` rules at vault level. Readers (`ops`,
`preparation`, `cr-intake`, `website-create`) load the relevant facets when a `_company/` exists and
say nothing when it does not. A reader never writes to a profile.

### 7. Privacy and the boundary

- This repository contains **no question text, no method wording and no schema from any private
  template**. The skill reads the template from `company.template:`; without it the skeleton is the
  plain one in section 1.
- The release guard (CR-026) denylist is extended **in the same change and before the first push**
  with the identifiers of the private template and its sources. The extension lives in the private
  archive, not here.
- Examples, tests and fixtures use invented companies.
- Profiles are customer data and live only in the vault, which is never committed.

## Implementation steps

1. Add the skill (`skills/company/SKILL.md`, `references/contract.md`) and `docs/schemas/` for
   `sources.yaml` and `brands.yaml`.
2. `ecosystem.yaml`: path, patterns, keys; contract 43.
3. `ops-config/base.yaml`: the `company:` block, with comments.
4. `/company check` and the `/ops check` line; reader lines in the four skills.
5. `/company export` with the one target.
6. Tests: the skill runs with `template: null`; `check` flags a planted key value, a stale facet and a
   duplicate outside `_company/`; `git grep` against the private denylist is empty.
7. Release: CHANGELOG, README version, `ecosystem.yaml` version, alignment script; one commit.
   **No push until the owner says so.**

## Not in scope

- The private template, its builder and the read service (separate repositories).
- Any change to the landing page (a separate request).
- Moving existing profiles into `_company/` (vault work, not a code change).

## Acceptance

- A vault with no `company:` block and no `_company/` behaves exactly as before.
- `/company init` without a template produces a valid skeleton and a message that no question set is attached.
- `/company check` reports each planted defect in section 5 and writes nothing.
- No file in this repository contains text from a private template; the release guard passes.

## As built (2026-10-14)

- The nine facets above replace the first draft's seven (`audience` is part of `gtm`; `company`, `offering` and
  `public` are facets). Frontmatter keys follow the profiles already written by hand.
- `/company check` splits in two: `company_tool.py check` decides what a program can (stale, schema, locked
  without sources, credential value, copies with `--copies`); the agent does the judgement checks (a status
  claim with no recent evidence, a fact without a source marker).
- Readers in this repository: `ops` (`prepare`, `orient`, `check`) and `preparation`. Skills in other
  repositories read the same folder under the same contract.
- Examples and tests use invented companies. Real profiles were only ever read, never copied, to test the
  checker.
