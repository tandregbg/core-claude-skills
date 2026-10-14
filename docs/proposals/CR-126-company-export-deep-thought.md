# CR-126 — `/company export deep-thought`: the company profile becomes the platform's context

| | |
|---|---|
| **Status** | **Proposed 2026-10-14**, build after 2026-10-27 (committed locally; not pushed, like 1.91.0) |
| **Contract** | additive, `contract_version` to the next free number (written as 43 to 44 before CR-127 and CR-128 took 44 and 45, so 45 to 46 if built next), `ops_config` 1.6 to 1.7. A new export target and an optional `company.deep_thought:` block. A vault that sets nothing behaves as before |
| **Date** | 2026-10-14 |
| **Area** | `skills/company` (`export`), `skills/company/references/contract.md` (section 7), `ops-config` (`company.deep_thought`), `docs/schemas/` (two export schemas), tests |
| **Related CRs** | CR-125 (the profile and its contract), Deep Thought DT-CR-745 (a tag's context can be owned by the vault), DT-CR-740 (the other direction, `_context.md`), record-me-macos MAC-CR-007 (sends the export), MAC-CR-003 |
| **Spec** | **The full version is tracked outside this repository.** The owner's decisions of 2026-10-14, the tag mapping and which organisations are synced name real organisations and accounts; this file carries the design and the contract only |

## Decisions taken (2026-10-14)

| Question | Decision |
|---|---|
| Build when | **After a dated hold (2026-10-27)**, as CR-125. Not built, not pushed before |
| Who sees it on the platform | Every member of the account: accepted |
| The owner's own company | Is the **account** context (`target: account`) |
| `notes` / `domain_note` | Taken **directly** from the facets' summary paragraphs, cut at a sentence boundary; no model |
| One organisation | Deliberately **not** synced (`target: none`) |

Each opted-in organisation maps to a platform tag of the same slug; the owner's own company maps to the
account. The mapping was read against the live tags on the day it was decided, and one tag had to be
created for it.

## What happened

record-me for Mac is the gateway between Deep Thought, which processes recordings in the cloud, and
core-skills, which works on them in the vault. The company profiles CR-125 produced are the best-sourced
description of each organisation: names, products, people and what may be claimed. Deep Thought's extraction
uses a much smaller, structured context per tag (`vertical_profile`) and per account (`account_profile`), today
typed by hand and drifting from the vault. Two decisions the same day: **one owner per tag** (a tag's context
comes from the vault or from Deep Thought, never both; DT-CR-745) and **one organisation is not synced at all**.

## Proposal

### 1. Opt-in per organisation (`<org>/_ops.yaml`)

```yaml
company:
  deep_thought:
    target: tag            # tag | account | none (default none)
    tag: acme              # the Deep Thought tag slug, when target is tag
```

Nothing is exported for an organisation without this block, or with `target: none`. `/company check` reports an
organisation with `target: tag` and no `tag`, and a block in an organisation whose `_ops.yaml` marks it as not to be
shared outside the vault — the case that prompted the rule: material that stays in the vault by the owner's
decision, written there as `target: none`.

### 2. The export (`<org>/_company/exports/deep-thought/`)

`/company export deep-thought [<org>]` writes, per opted-in organisation, one JSON file in Deep Thought's shape:

- `vertical-profile-<vertical>.json` (target `tag`): `display_name` and `organization {name, aliases}` from
  `brands.yaml`; `domain` (one line) from `offering` and `positioning`; `vocabulary` from brand, product and
  domain names in `brands.yaml` plus the words-to-use list of `messaging`; `regulars` (name, role, org) from the
  people the `company` facet names with a role; `not_persons` from product and brand names that look like names;
  `notes` (at most 2,000 characters) from the `company` and `positioning` summaries; `output_language` from
  `company.language`.
- `account-profile-<vertical>.json` (target `account`): `primary_organization`, `affiliations` (one per opted-in
  organisation, the owner's role there from its `company` facet), `domain_note` (at most 2,000 characters).
- A header in each: `contract_version`, `vertical`, `generated`, `export_hash` (SHA-256 of the body), and the
  profile files and their `reviewed` dates it was built from.

The two shapes are checked against `docs/schemas/deep-thought-vertical-profile.schema.json` and
`deep-thought-account-profile.schema.json`, copied from Deep Thought's validators with the version they came from.

### 3. What never goes into the export

- Facets `strategy` and `gtm`, and anything from a source with `authority: draft` or under `exclude` in
  `sources.yaml`.
- A facet whose `reviewed` is empty, unless `/company export deep-thought --unreviewed` is given (then the header
  says so).
- Every line is filtered by the never-say list (contract rule 6); numbers are left out (they date and need their
  definitions; extraction does not need them).
- No source paths outside the header; no key values (contract rule 10 and section 5).

### 4. Who sends it

Not core-skills. The export is a file; record-me for Mac (MAC-CR-007) reads `exports/deep-thought/`, sends what
changed by `export_hash`, and records the result in `exports/deep-thought/.sent.json` (owned by the app). The
skill never calls Deep Thought. Without record-me, the file is still useful to read or to paste.

### 5. Contract text (section 7)

A second target: `deep-thought`, its two files, the opt-in, the exclusions above, and that the platform holds a
copy marked as owned by the vault, read-only there, so the profile stays the place to change it.

## Implementation steps

1. `company_tool.py export deep-thought`: deterministic extraction from frontmatter, `brands.yaml` and the marked
   summary sections; no network, no LLM for the structured fields. The `notes` and `domain_note` text is the
   facets' own summary paragraphs, cut at a sentence boundary.
2. The two schemas; `ops-config` `company.deep_thought` with comments; `/company check` lines.
3. Tests with an invented company: opt-out writes nothing; a `strategy` sentence and a never-say word never appear;
   `notes` is at most 2,000 characters; the hash is stable for an unchanged profile.
4. Release: CHANGELOG, contract 44. **No push until the owner says so** (as CR-125).

## Open questions

1. One of the mapped tags is **personal** scope; per-tag context is for account-scope tags only (DT-CR-740 A5).
   Move it to account scope before the first send, or send nothing for it.

## Not in scope

The other direction (Deep Thought to vault, DT-CR-740 / MAC-CR-003); the landing page (after the build, with the
1.91.0 page when the push hold lifts).
