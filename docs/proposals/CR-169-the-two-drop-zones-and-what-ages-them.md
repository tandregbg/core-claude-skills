# CR-169 — The two drop zones, and what ages them

| | |
|---|---|
| **Status** | **Implemented v1.94.0** (2026-11-03), contract 48 |
| **Contract** | additive — `stale_vs_junk` gains the second drop zone; one new check, no new surface |
| **Date** | 2026-11-03 |
| **Area** | `ecosystem.yaml` (`stale_vs_junk`, `vault_conventions`), `ops` (`check`) |
| **Related CRs** | CR-024 (`.ephemeral/`, the 14-day sweep), CR-025 (one inbox, one outbox), CR-035, the `audit_lifecycle` rule |

## What happened

The contract declares one drop zone and the vaults use two.

`stale_vs_junk` says: *"A document that WAS current and is now outdated is archived to `.archive/`
(never deleted). Material with no vault destination goes to `.ephemeral/` and may die (swept after
14 days, CR-024)."* That is `.archive` against `.ephemeral` — **stale against junk.**

The second distinction is not in the contract at all. One vault's `CLAUDE.md` carries it:

> **Fildroppar:** fil med vault-destination → `_inbox/.files/`; utan destination → `.ephemeral/`.
> **Beslutet tas vid droppen, inte av gravitationen.**

That is `.files` against `.ephemeral` — **destined against undestined**, decided at drop time. It is
the rule that makes `.ephemeral`'s sweep safe: anything that may die was declared to have no home
when it arrived. Without it the sweep is a guess.

**[E] Measured on one vault, 2026-11-03.** Both zones had failed, in opposite directions:

| | `_inbox/.files/` | `.ephemeral/` |
|---|---|---|
| Entries | 8 | 44 |
| Volume | 52 MB | — |
| Past its rule | **all of them** — no ageing rule exists | **33 of 44** past the 14-day sweep |
| Oldest | 2026-09-29 (35 days) | May 2026 |

**`.files/` has no ageing rule, so nothing it holds can ever be late.** It carries an implicit promise
— *this file has a home and someone will route it there* — and the promise had been open five weeks.

**And at least one entry was mis-filed at drop time**: a pre-release build of an application,
owned by its own repository, which has no vault destination and belonged in `.ephemeral/`, where it
would have been swept in September. Filed in `.files/` it is immortal.

**[E]** `audit_lifecycle` measures the three-content-file ceiling in `_inbox/`. Nothing measures either
drop zone. A rule nobody counts is how both mappings drifted into the opposite failure.

## Proposal

1. **`stale_vs_junk` gains the drop-zone test.** Three destinations, one question each:

   | Destination | The question it answers |
   |---|---|
   | `.archive/` | Was it current and is now outdated? Never deleted |
   | `<inbox>/.files/` | Does it have a vault destination it has not reached yet? **In transit** |
   | `.ephemeral/` | Does it have no vault destination? May die, swept after 14 days |

   With the sentence the measured vault already carries: **the decision is taken at the drop, not by
   gravity.** It is the reason the sweep is safe.

2. **`check` reports age in both zones**, with different meanings: an entry in `.files/` older than a
   declared threshold is a **promise nobody kept** (it has a home and never went there); an entry in
   `.ephemeral/` older than 14 days is **a sweep that has not run**. Report only — neither moves nor
   deletes anything, per CR-103.

3. **The `.files/` threshold is declared, not invented** (`vault_conventions`, default 14 days to match
   the sweep). A vault that stages large material deliberately can raise it.

## What this is not

**Not an automatic sweep.** `.ephemeral/` may die, but deciding *when* stays with the operator; the
contract says `check` reports and never rewrites. The defect measured here is an unreported backlog,
not an unexecuted deletion.

**Not a new surface.** Both folders exist in the vaults already; only one of them exists in the
contract.

## Acceptance

- `stale_vs_junk` names three destinations and the question that routes to each.
- `check` lists aged entries in both zones, each with the reason its age means something different.
- A file with no vault destination filed in `.files/` is reportable — today it is invisible.

## As implemented (v1.94.0)

All three acceptance lines hold, and two things were found while implementing them.

**The contract's own prose carried a retired command.** The `.ephemeral/` entry read *"/ops sweep
flags content >14 days"* — `sweep` was renamed `check` in 1.79.0 (CR-089), three releases earlier.
`check-terms.py` watches the skills and the README for retired command names and has never read
`ecosystem.yaml`, so the contract was the one surface where the rename could rot unseen. Corrected,
and a test now walks `vault_conventions` for every retired name.

**The threshold is declared on both entries, not in one place with a cross-reference.**
`stale_after_days: 14` sits on `_inbox/.files/` and on `.ephemeral/`, with a test asserting the two
are equal. Two numbers that must agree, written once each, beat one number and a sentence saying the
other zone uses it too — a reader of either entry gets the answer without following a link, and the
test is what stops them drifting.

14 new tests.
