# Change Requests (Proposals)

Tracking spec for core-skills changes. Each CR is a single markdown file in this directory.

Existing CRs are also tracked in [CHANGELOG.md](../../CHANGELOG.md) as `(CR-NNN)` mentions in the `### Added` / `### Changed` lines once implemented.

Next available CR number: **CR-029**

---

## Proposed (Ready to Implement)

_None._

---

## Implemented

Implemented CRs are tracked in [CHANGELOG.md](../../CHANGELOG.md). Highest implemented: **CR-028** (local-only evolution + semantic release gate, v1.32.0).

CR-017–CR-028 were drafted and implemented 2026-07-07/10 from a private vault-usage audit and live usage; the full CR specs contain vault-specific evidence and are tracked privately (not in this repo), so their rows carry generic notes only.

| CR | Title | Version | Notes |
|----|-------|---------|-------|
| CR-028 | Local-only evolution + semantic release gate | v1.32.0 (2026-07-10) | `evolution.proposals_path` (vault-private); mandatory semantic review step in RELEASING.md; history audited (zero secrets ever); fresh-clone guard reminder in update-skills |
| CR-027 | Knowledge synthesis — `/insights synthesize` + wiki layer | v1.31.0 (2026-07-10) | Semantic vault-wide clustering → topic articles + auto-maintained INDEX (read-first, no RAG); human-edited marker; experiment gating the future knowledge-lint |
| CR-026 | Release process + privacy push-guardrails | v1.30.0 (2026-07-08) | `docs/RELEASING.md` + fail-closed pre-push guard (built-in secret patterns + private denylist via `git config guard.denylist`) |
| CR-025 | Structure conformance as `/ops sweep` check 9 | v1.29.0 (2026-07-08) | Fuzzy stray-inbox/outbox matcher (exact names miss real strays); `structure_exemptions` config; `/ops status` health step upgraded |
| CR-024 | File-drop lifecycle (`_inbox/.files/`) + `.ephemeral` contract | v1.28.0 (2026-07-08) | Generalizes `.audio/` pairing to any input file; source moves with output to `.attachments/`; `.ephemeral` = declared no-destiny scratch |
| CR-023 | Ecosystem alignment as an `/ops sweep` check | v1.27.0 (2026-07-08) | Sweep check 8 runs the alignment script read-only; `[SKIP]` = unverified, not clean; off unless `workflows.sweep.alignment_check` configured |
| CR-022 | Triage working surface — contract + read integrations | v1.26.0 (2026-07-07) | `_inbox/` working-doc contract; `/inbox triage`; preps/dashboard/task-import/sweep integrations, all read-around |
| CR-021 | Filename slug policy (diacritics, casing, role keywords) | v1.25.0 (2026-07-07) | Slug contract in ops-base; driftword check runs on filenames; `/ops normalize --filenames` backfill |
| CR-019 | `/ops sweep` closure/staleness audit + retirement convention | v1.24.0 (2026-07-07) | Six closure-debt classes detected read-only; tombstone rule on artifact relocation; `/outbox archive --all-sent` |
| CR-018 | Meeting-type template contracts + pre-save shape lint | v1.23.0 (2026-07-07) | `workflows.meeting_templates` registry; 3-point pre-save check (warn/strict); `/ops lint` finds series forks |
| CR-017 | People roster + committed-spelling consistency | v1.22.0 (2026-07-07) | `people:` config block; folder-precedent near-miss check for names and anomalous domain terms; `/ops normalize --names` |
| CR-020 | Insights schema reconciliation + compile activation | v1.21.0 (2026-07-07) | Privacy rule retired → reusability note; `quote` canonized; write-time vocabulary guard; `/insights normalize`; `last_compiled` stamp |
| [CR-016](CR-016-proper-noun-verification.md) | Proper-noun verification + ASR-vocabulary hint | v1.20.0 (2026-06-05) | Known-entity set, `Name?` flagging, `⚠ Namn att verifiera` note; `/preparation` recording-names hint |
| [CR-015](CR-015-undiarized-transcript-owner-safety.md) | Undiarized-transcript owner safety | v1.19.0 (2026-06-05) | Fail-safe `?`/`Name?` owners when no speaker labels; edge_case logging |
| [CR-013](CR-013-insight-lifecycle.md) | Hypothesis → rule lifecycle for `_insights.yaml` | v1.17.0 (2026-05-10) | `confidence` field, promotion/demotion passes in `/insights compile`, rules preamble in `/ops`+`/transcript` |
| [CR-014](CR-014-rolling-plans.md) | Rolling plans — participant-triggered per-axis living docs | v1.18.0 (2026-06-04) | Generic `workflows.rolling_plans` in `/ops` (participant trigger, mirrors `verticals`) + read-only `/daily-dashboard` surface + scaffold template. Additive; no org hardcoding. |
| [CR-012](CR-012-inbox-schema.md) | Formal `_inbox/` schema + `.audio/` subfolder | v1.16.0 (2026-04-29) | `docs/schemas/inbox.md` is the canonical contract. Frontmatter is canonical, `_inbox.yaml` is derived. Identifier upgraded to `YYMMDD-HHMMSS[-slug]`. `.audio/` pairing-by-basename rule formalised. |
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
- When implemented: log under the relevant version in `CHANGELOG.md` with a `(CR-NNN)` mention, AND move the CR's row from Proposed to Implemented in this index **in the same commit** (CR-020: the index drifted for months because this step was implicit)
- CR specs containing private vault evidence are tracked outside this repo; their rows here carry generic titles only
- The `.applied/` subfolder is for `/insights propose` skill-improvement proposals (CR-004, separate concept from CRs in this index)

---

*Last updated: 2026-07-10 — CR-028 implemented (v1.32.0, privacy posture completed). CR-017–CR-028 specs tracked outside this repo.*
