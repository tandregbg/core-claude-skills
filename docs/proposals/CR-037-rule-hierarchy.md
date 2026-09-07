# CR-037: Rule hierarchy and conflict resolution for `vault_conventions`

| Field | Value |
|-------|-------|
| **CR Number** | CR-037 |
| **Date** | 2026-09-07 |
| **Author** | User + Claude Code |
| **Status** | Implemented |
| **Implementation Date** | 2026-09-07 (v1.36.0) |
| **Priority** | High |
| **Complexity** | Low |
| **Estimated Scope** | `ecosystem.yaml` `vault_conventions`, `ops` skill (sweep severity) |
| **Related CRs** | CR-010, CR-025, CR-027, CR-033, CR-034, CR-035, CR-036 |
| **Depends On** | CR-036 |
| **Breaking Changes** | No (reorganises existing rules; adds no new constraint) |

---

## Executive Summary

`vault_conventions.rules` now holds **thirteen rules from seven CRs in a flat list.**
Nothing states which is stronger, what happens when two apply to the same surface, or how
a tool should weight a violation.

**This is not hypothetical — it failed today.** `prefix_conventions` said dot means "not
read in everyday work"; `dot_surface_levels` listed `.knowledge/` as blocked and generated.
Both applied to the same folder, they disagreed, and nothing resolved it. The
inconsistency shipped in a commit before a reader caught it.

A flat list of thirteen also cannot be implemented consistently: a sweep has no basis for
reporting one violation as a finding and another as a warning.

---

## Proposed Changes

### 1. Three levels, with stated strength

| Level | Meaning | Exceptions | Sweep |
|---|---|---|---|
| **invariant** | **Never broken.** A violation is a structural defect | **None possible** | finding |
| **rule** | Holds generally. Exceptions exist but must be **named and justified in the contract** | Declared per case | finding, unless the surface is a declared exception |
| **guideline** | The intended shape. Judgement may override | Not tracked | warning |

**Assignment of the current thirteen:**

**invariant** — `single_inbox_outbox` · `vault_relative` · `config_resolution_order` ·
`dot_surface_levels` *(the blocked half — read constraints are absolute)* ·
`singleton_surfaces` · `audio_transcript_pairing`

**rule** — `prefix_conventions` *(one declared exception: `.knowledge/`)* ·
`placement_classes` · `write_ownership` · `stale_vs_junk` · `audit_lifecycle`

**guideline** — `changelog_readme_conditions` · the three-file `_inbox` ceiling

### 2. Conflict resolution, in order

1. **Higher level wins.** invariant > rule > guideline.
2. **Within a level, the more specific wins.** A rule naming a path beats one naming a class.
3. **A declared exception beats the rule it exempts** — but only for the named surface, and
   never against an invariant.
4. **If two rules of equal specificity conflict, that is a contract defect.** Report it;
   do not choose. Silent resolution is how the `.knowledge/` inconsistency survived review.

### 3. Every rule declares its level

```yaml
- id: "prefix_conventions"
  level: rule
  exceptions: [".knowledge/"]
  rule: "…"
```

`level:` is mandatory. A rule without one is a contract defect, not a guideline by default —
the absence must be loud.

### 4. What this makes possible

**A sweep can weight severity from the contract** rather than a hardcoded list, and a new
rule inherits the right severity from its level.

**Exceptions become auditable.** `.knowledge/` is currently exempted in prose; as
`exceptions: [".knowledge/"]` it can be verified — and a second undeclared exception shows
up as a violation instead of passing as precedent.

---

## Out of Scope

- New constraints. This reorganises what CR-010 through CR-036 already state.
- Per-skill enforcement beyond the sweep severity mapping.

---

## Implementation Notes

Add `level:` to all thirteen rules, `exceptions:` where one exists, and a
`rule_hierarchy` block carrying §2. Then extend `/ops sweep` to read `level:` for severity
instead of its current implicit weighting.

**Reason this is High priority despite Low complexity:** the flat list has already
produced one shipped inconsistency. Each added rule raises the chance of the next.
