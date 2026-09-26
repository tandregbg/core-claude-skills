# CR-092 — A convention's middle level is a *standard*, and the block is `conventions`

| | |
|---|---|
| **Status** | **Implemented 2026-09-26, v1.80.0** — contract 33 |
| **Contract** | **not additive** (32 → 33) — one enum value and one block key renamed; readers accept the old spelling for one release |
| **Date** | 2026-09-26 |
| **Area** | `ecosystem.yaml` (`vault_conventions.rules`, every entry's `level`, the CR-037 hierarchy comment, `terms:`), `/ops check` (vault) severity mapping. Outside this repo: the landing page's conventions page (`Rules.astro`) |
| **Related CRs** | CR-037 (the level hierarchy), CR-089 (one term per concept — left this collision open on purpose) |

## What happened

CR-089 decided that **`rule` belongs to the insight lifecycle** (hypothesis → rule, CR-013) and that
the contract's rules for the vault are **conventions**. It renamed the landing page's
`/the-contract/rules` accordingly. Two uses of the word survive inside the contract itself:

| Where | Today | The collision |
|---|---|---|
| `vault_conventions.rules` | the block key holding the 18 conventions | a list of conventions called `rules` |
| each entry's `level` | `invariant` \| `rule` \| `guideline` — 11 of 18 are `rule` | a convention whose level is *rule*, beside an insight whose state is *rule* |

The second is the one that misleads. "Rule" at the middle level means *holds generally; exceptions
must be named* (CR-037). An insight at `rule` means *confirmed often enough to be loaded as a standing
instruction*. A reader of the conventions page meets the first, a reader of `_insights.yaml` the
second, and `terms:` can only declare one of them.

## Proposal

### 1. The middle level is `standard`

```
invariant  never broken; no exception possible
standard   holds generally; exceptions must be NAMED in exceptions: and justified
guideline  intended shape; judgement may override
```

*Standard* carries the right weight: stronger than guidance, weaker than an invariant, and it is
what a person departs from **with a stated reason**. Conflict resolution becomes
`invariant > standard > guideline`; nothing else in CR-037 changes.

### 2. The block key is `conventions`

`vault_conventions.rules` → `vault_conventions.conventions`. The ids inside are unchanged.

### 3. One release of both spellings

- Readers accept `level: rule` as `standard`, and `vault_conventions.rules` when `conventions` is
  absent. `/ops check` (vault) maps both to the same severity.
- `check-components.py` fails on `level: rule` from the release after, so the old value cannot
  come back.

### 4. `terms:`

Add `{id: standard, en: standard, sv: standard, note: "a convention's middle level (CR-037)"}`; add
`"level: rule"` to no `avoid:` list — the check reads prose, and the enum is guarded by the component
check above.

## Outside this repo

| Where | What |
|---|---|
| Landing page | `Rules.astro`: read `conventions` (fall back to `rules`), `LEVELS` key `standard` with labels "Standard — broken with a reason" / "Standard — bryts med skäl"; rebuild and deploy |
| Marvin | Nothing reads the level today (checked); note it in contract tracking |

## What this does not do

- Rename the insight state `rule`, or any insight file.
- Rename any convention id.
- Change what any level means.

## Acceptance

- `ecosystem.yaml`: `contract_version` 33; `vault_conventions.conventions`; no entry with
  `level: rule`; the CR-037 comment reads `invariant > standard > guideline`.
- The landing page's conventions page groups 6 invariants, 11 standards, 1 guideline.
- A contract with `level: rule` still renders during the alias release.
- **Proposed release: minor (1.80.0)**, which can also remove CR-089's one-release aliases — to be
  confirmed by the maintainer.

## Outcome (2026-09-26, v1.80.0)

Implemented as proposed. `ecosystem.yaml`: key `conventions`, 11 levels `standard`, the CR-037
comment, orientation `sources:` paths, `standard` in `terms:`, contract 33. `/ops status` now names
`conventions.single_inbox_outbox` and `conventions.prefix_conventions` (it still said `yaml_naming`,
a key replaced by contract 3). `check-components.py` refuses the old key and level in this repo's
contract; `tests/test_cr092_conventions.py`. Landing page: reads `conventions`, falling back to
`rules`, and maps a `rule` level to `standard`; rebuilt and deployed.

**Decided at implementation:** released as 1.80.0 **without** removing CR-089's aliases. Removing
them is only safe once the components and machines still on the old names have moved.
