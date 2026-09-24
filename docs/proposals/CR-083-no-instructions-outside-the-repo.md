# CR-083 — No instructions outside the repo

| | |
|---|---|
| **Status** | Proposed |
| **Contract** | none (process + one config default) |
| **Date** | 2026-09-24 |
| **Area** | `docs/RELEASING.md`, `insights` (`evolution.proposals_path`), the private companion folder |
| **Related CRs** | CR-026 (public/private membrane), CR-028 (evolution proposals path), CR-078 (documentation belongs to its owner) |

## The rule

**Everything that tells a skill or a person how to work lives in this repo.** The private companion
folder holds **data** — never instructions.

## Why this needs saying

CR-026 created a private companion folder in the vault (`<vault>/_private/core-skills/`) because
the repo is public and early CR specs carried real names, customers and hosts as evidence. The split
was about **privacy**, and it was right.

It has since drifted into holding **process**:

| What is there | What it is | Problem |
|---|---|---|
| `push-denylist.txt` | Data — identifiers the pre-push guard blocks | None. Must stay private |
| `audits/` | Evidence | None, if nothing links to it as a rule |
| `proposals/CR-001…046` | Full CR specs with evidence | Historical. From CR-047 on, specs are written name-free in the repo — the split already ended in practice |
| `README.md` | **Process:** CR status discipline, machine setup for the guard | Instructions outside the repo |
| `proposals/generated/` | **Where `/insights` writes proposed skill changes** (`evolution.proposals_path`, CR-028) | Instructions-to-be, generated outside the repo, reviewed nowhere the repo can see |

A session reading the repo cannot see the README, and a proposal written to `generated/` never enters
the index. **Two places saying how to work is one place too many** — CR-078's test applies: if this
changed tomorrow, which repo's commit would change it? This one.

## Proposal

1. **Move the README's process into `docs/RELEASING.md`** — the guard setup (`core.hooksPath`,
   `guard.denylist` pointing at a path outside the repo) and the status discipline. The private
   README shrinks to one line: *data for the pre-push guard; no instructions live here.*
2. **`evolution.proposals_path` defaults into the repo** (`docs/proposals/generated/`, gitignored
   until reviewed). Generated proposals are written name-free, the same rule every CR since CR-047
   follows, and the pre-push guard covers them on the way out.
3. **CR-001…046 in the private folder are frozen.** Not moved, not linked as current. The public index
   already carries their titles.
4. **Vault configs stop pointing at the private folder for anything but the denylist.** The vault-wide
   override of `proposals_path` is removed.

## What stays private, and why

- **The denylist** — publishing it publishes exactly what it protects.
- **Evidence** — audits and transcripts that motivated a CR. A CR may say *observed in one vault*;
  it never needs the names to be right.

## Acceptance

- No file outside this repo instructs a skill or an operator.
- `grep -r proposals_path` in a vault's config returns nothing, or the repo default.
- The private folder's README is one line.
