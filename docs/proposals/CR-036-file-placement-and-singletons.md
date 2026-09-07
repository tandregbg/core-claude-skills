# CR-036: File placement classes and singleton surfaces

| Field | Value |
|-------|-------|
| **CR Number** | CR-036 |
| **Date** | 2026-09-07 |
| **Author** | User + Claude Code |
| **Status** | Proposed |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `ecosystem.yaml` `vault_conventions`, `ops` skill (sweep check 9) |
| **Related CRs** | CR-010 (vault file conventions), CR-025 (single inbox/outbox), CR-027 (`.knowledge/`), CR-033 (`.handoff/`), CR-034 (prefix conventions) |
| **Depends On** | CR-034 |
| **Breaking Changes** | No (documents existing practice; two folders flagged for a decision) |

---

## Executive Summary

CR-010 declares *which* files the suite produces. It does not declare **how many of each
should exist, or where.** CR-025 answers it for `_inbox`/`_outbox` alone. Everything else
is by imitation, and the counts show the drift:

| File | Count | At root? |
|---|---|---|
| `README.md` | **269** | no |
| `CHANGELOG.md` | **174** | no |
| `_manifest.md` | 137 | no |
| `_insights.yaml` | 104 | no |
| `_tasks.yaml` | 81 | no |
| `.archive/` | 78 | yes |
| `CLAUDE.md` | 41 | yes |
| `INDEX.md` | 10 | yes |
| `_ops.yaml` | 5 | no |
| `.handoff/` · `.knowledge/` | **1 each** | yes |

**Two signals that placement is not governed:**

- **130 of 174 `CHANGELOG.md` sit in folders with no `.archive/`** — history is being kept
  where nothing is retired.
- **269 `README.md`** is more than the number of folders a reader would ever open.

Meanwhile `.handoff/` and `.knowledge/` are correctly singleton — but by practice, not by
contract, so nothing prevents a second one appearing.

---

## Proposed Changes

### 1. Three placement classes

Every declared file belongs to exactly one:

| Class | Rule | Members |
|---|---|---|
| **singleton** | **Exactly one, at vault root.** A second instance is a finding | `INDEX.md`, `_inbox/`, `_outbox/`, `_config/`, `.handoff/`, `.knowledge/` |
| **per_folder** | Appears in every folder of its kind | `_meta.yaml`, `_insights.yaml`, `_tasks.yaml`, `_manifest.md`, `.archive/` |
| **per_boundary** | Appears where the boundary it describes actually applies | `CLAUDE.md`, `_ops.yaml`, `CHANGELOG.md`, `README.md` |

### 2. Why `.handoff/` and `.knowledge/` are singleton — the principle

Not convention. **Each would contradict its own purpose if scoped to a folder.**

**`.handoff/`** is outward-facing, self-carrying, and holds no vault links (CR-033). It
does not belong to a folder — it has *left* the structure. A `<org>/.handoff/` would make
the snapshot inherit a context it is built to survive without.

**`.knowledge/`** synthesises across sources; `INDEX.md` is the single documented entry
point (CR-027). A `<org>/.knowledge/` would prevent exactly the cross-source synthesis
that justifies the layer.

**The general test for singleton status:**

> Would a second, scoped instance of this surface defeat the reason the surface exists?

Yes → singleton. This is stronger than "there happens to be one".

### 3. Candidates the same test flags

| Surface | Instances | Assessment |
|---|---|---|
| `.transcripts/` | 2 *(root + one org)* | **Should be singleton.** It carries a read-block. Two blocked surfaces are harder to enforce than one, and a skill honouring the root while missing the scoped copy is a silent failure |
| `.ephemeral/` | 4 | **Weaker case.** Content may die, so plurality is less dangerous — but it means four sweep points instead of one, and CR-024 defines one retention window |

Both are flagged for decision, not resolved here. Resolving `.transcripts/` requires
moving content out of a read-blocked surface, which needs explicit human authorisation.

### 4. `CHANGELOG.md` and `README.md` get conditions

**`CHANGELOG.md`** — only where history is actually kept: contacts, organisations,
projects, products. **A CHANGELOG in a folder that never retires anything is noise.**
Current state: 130 of 174 have no sibling `.archive/`.

**`README.md`** — only where a folder needs explaining **to someone other than its
author**. 269 instances means it is being written reflexively.

Neither is enforced retroactively. The rule governs new folders and is a sweep *warning*,
not an error.

### 5. `INDEX.md` scope

Root (the vault entry point) plus generated registers. Three current instances sit inside
`.ephemeral/` and will die with it — no action needed.

---

## Out of Scope

- Retroactive removal of surplus `README.md`/`CHANGELOG.md`. Cost exceeds benefit; the
  rule is forward-looking.
- Moving `.transcripts/` content — needs authorisation, and read-blocked material must not
  be relocated by a skill acting on its own.

---

## Implementation Notes

Add `placement:` to each path in `vault_conventions.paths`, plus a
`singleton_surfaces` rule carrying the test from §2. `/ops sweep` check 9 already watches
structural deviations — extend it to report a second instance of a singleton surface as a
finding, and a CHANGELOG without a sibling `.archive/` as a warning.
