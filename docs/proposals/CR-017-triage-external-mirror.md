# CR-017: Triage external mirror — gated push + reconcile

| Field | Value |
|-------|-------|
| **CR Number** | CR-017 |
| **Date** | 2026-07-22 |
| **Status** | Implemented |
| **Related CRs** | CR-022 (triage working-surface, in the vault-private CR set); CR-012 (inbox schema) |
| **Skills touched** | `inbox` (SKILL.md triage section) |
| **Breaking Changes** | No |

## Summary

`/inbox triage` maintains a per-vault working document (CR-022). Some vaults want
a focused *today/tomorrow* view of that document on an external actions surface
(a task app). This CR documents the **contract** for such a mirror as an optional,
per-vault, human-gated integration — without shipping any provider code in this
public repo.

## Motivation

The triage doc is free-form markdown and the owner's system of record. A one-way
"push everything" export would create a second source of truth; a naive two-way
sync would need hidden IDs injected into a hand-edited file and real conflict
resolution. Neither belongs in a public skill. But a **gated** push + a **gated**
reconcile give most of the value with none of the merge risk, and they compose
cleanly with the existing mechanical-upkeep principle.

## Contract (what the skill documents)

- **push** — mirror current actionable *today/tomorrow* items outward after a
  preview; one-way, additive, deduped; ships an item only if the line itself
  marks it today/tomorrow (never invents dates).
- **reconcile** — read the surface back; for items completed there, **propose**
  marking the matching triage line `[x]`; human approves before any write.
  Never auto-merges — the triage doc stays the system of record.
- **Secret-free & local** — the provider script, credential, and target IDs live
  outside this repo (local script dir + gitignored secret + a pointer in the
  vault's own config layer). The triage path is read from the registered `file:`
  in the inbox index, so a rename that updates the registration keeps working.

## Non-goals

- No provider/API code in this repo (that is a local integration).
- No automatic two-way sync, no hidden ID injection into the triage doc.
- Not enabled by default: absent local config, the mirror simply does not exist.

## Rollback

Documentation-only in this repo (`git revert`). Local provider scripts are
independent and unaffected.

## References

- SKILL.md `inbox` → triage section, "Optional external mirror (CR-017)".
- CR-022 (triage working-surface upkeep) in the vault-private CR set.
