# Change Requests (Proposals)

Tracking spec for core-skills changes. Each CR is a single markdown file in this directory.

Existing CRs are also tracked in [CHANGELOG.md](../../CHANGELOG.md) as `(CR-NNN)` mentions in the `### Added` / `### Changed` lines once implemented.

Next available CR number: **CR-013**

---

## Proposed (Ready to Implement)

| CR | Title | Priority | Description |
|----|-------|----------|-------------|
| [CR-012](CR-012-inbox-schema.md) | Formal `_inbox/` schema + `.audio/` subfolder | Medium | `docs/schemas/inbox.md`; document `_inbox/.audio/` for Trillian-captured audio |

---

## Implemented

Implemented CRs are tracked in [CHANGELOG.md](../../CHANGELOG.md). Highest implemented: **CR-011** (org-config move, v1.16.0).

| CR | Title | Version | Notes |
|----|-------|---------|-------|
| [CR-011](CR-011-org-config-move.md) | Org-config move from skill repos to vault folders | v1.16.0 (2026-04-29) | Phase 1+2 done. New chain: project > folder-local `<vault>/<org>/_ops.yaml` > vault-wide `_config/base.yaml` > skill base.yaml. Pre-v1.16.0 `*-ops-config` skill chain deprecated, removed v1.17.0 (Phase 5, deferred). |
| [CR-010](CR-010-vault-conventions.md) | `vault_conventions:` block in `ecosystem.yaml` | v1.16.0 (2026-04-29) | contract_version 1 -> 2; authoritative path/writer/reader/lifecycle declarations for vault files |
| CR-009 | Contact classification taxonomy | v1.15.8 | `_meta.yaml` `classification` field with four levels |
| CR-008 | (folder summary generator) | (in code at `scripts/generate_summaries.py`) | Generates `_summary.yaml` per folder via Ollama |
| CR-007 | Swedish character enforcement | v1.15.4 | `swedish_chars: strict`, sub-tree inheritance, `/ops normalize` |
| CR-006 | Transcript structure rule | v1.15.3 | Canonical heading order: Nästa steg → Beslut → Konklusion → Diskussion → Bakgrund |
| CR-005 | Preparation agenda-card format | v1.15.2 | 60-second walk-in card on top, deep-dive below |
| CR-004 | Skill evolution loop | v1.15.0 | Three-step feedback: capture, compile, improve |
| CR-003 | `/inbox` skill | v1.13.0 | Universal entry point for unstructured content |
| CR-001 | (early CRs) | (various) | Tracked in CHANGELOG by mention |

(CR-002 is not used; renumbering kept history intact.)

---

## Archived

Currently empty. Move CRs here that are explicitly retired or superseded.

---

## Conventions

- File name: `CR-NNN-kebab-case-title.md`
- One CR per file
- Status lifecycle: Draft → Proposed → Implemented → Archived
- When implemented: log under the relevant version in `CHANGELOG.md` with a `(CR-NNN)` mention
- The `.applied/` subfolder is for `/insights propose` skill-improvement proposals (CR-004, separate concept from CRs in this index)

---

*Last updated: 2026-04-29 — CR-011 implemented Phase 1+2 (resolution chain rewrite + Alex's vault migrated: acme, bravo, delta). Phase 5 (retire `*-ops-config` skills) deferred to v1.17.0.*
