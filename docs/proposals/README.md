# Change Requests (Proposals)

Tracking spec for core-skills changes. Each CR is a single markdown file in this directory.

Existing CRs are also tracked in [CHANGELOG.md](../../CHANGELOG.md) as `(CR-NNN)` mentions in the `### Added` / `### Changed` lines once implemented.

Next available CR number: **CR-071**

---

## Proposed (Ready to Implement)

| CR | Area | Priority | Summary |
|----|------|----------|---------|
| CR-069 | `ops-base` | Medium | **Implemented v1.70.0.** Add a generic **Status/Results Report** standard beside TWO-TIER — measurement-driven (data source + period) vs the summary format's event-driven (transcript). Scorecard-first trend, partial-period guard, reconciliation invariants, honest provenance + blind spots, a warn-not-fail freshness gate, owner-ranked actions. Business-agnostic; producing skills reference it. Additive (21→22). |
| CR-042 | `ops-config` schema | Low | Four keys a coordination project needs and the schema does not define — cadence (as a timezone **pair**, since the anchored end matters across DST), tracks, phases (which may be inherited from the shadowed codebase), and systems of record. Undeclared keys make a config file look authoritative while being partly inert |

| CR-047 | `/outbox` | Medium | **Implemented v1.65.0.** Archiving an item that was decided against. `archive` requires a sent status, so anything marked superseded, replaced or withdrawn can never be filed and accumulates indefinitely — it was resolved, just not by being sent. Proposes a terminal `avskriven` state, archivable when `## Utfall` states why, plus a `RESOLVED, NOT SENT` section in `list` and an `--all-resolved` batch mode |

| CR-048 | `tasks` schema | Medium | **Implemented v1.40.0.** The status enum was defined in the skill but not in `ecosystem.yaml`, so nothing could check it. Three dialects grew in the gap — `open`/`done`, `todo`/`waiting`, and one-off words like `superseded` and `obsolete` — and a reader that knew only the canonical set counted finished tasks as outstanding. Declares `task_statuses` split into `active` and `finished`, plus the rule that a reader tolerates an unknown status rather than treating it as active |

| CR-049 | ecosystem contract | Medium | **Implemented v1.41.0.** `system_file_language` covered file names but not what is inside them, and two tools had drifted: a dispatcher hardcoding the vault's status words, and a sync tool using display strings as dictionary keys in 38 places. Declares `identifier_language` — identifiers English, display text data in a settings file, and where the two were one string the label keeps the spelling |

| CR-050 | ecosystem contract | Medium | **Implemented v1.42.0.** Nothing described how the parts connect — only how each touches files — so "where is the full picture documented" had no single answer. Declares `components:` with reads, writes, depends_on and direction, as roles rather than product names. Writing it surfaced two undeclared vault files. `check-components.py` verifies the graph against `vault_conventions` from the alignment check |

| CR-051 | vault conventions | Low | **Implemented v1.43.0.** `_infrastructure/` was named in `prefix_conventions` but never declared as a path. Declares it, and its counterpart `_architecture/` for the software system — the generic `components:` block is the source, and that folder is where the roles map onto actual repositories. Both SINGLETON |

| CR-052 | ecosystem contract | Low | **Implemented v1.44.0.** The inventory scanner writes vault files but was not in the components graph, and `_INDEX-*.md` was undeclared. Declares both. The scanner is the one component bridging the machine map and the software map — input infrastructure, output a vault file. Also fixes `check-components.py`, which let a write phrased as prose name an undeclared file |

| CR-053 | `/outbox` schema + contract wording | Medium | **Implemented v1.45.0.** Two things one question exposed. The contract named a manifest's fields by their Swedish labels, which reads as Swedish identifiers in a public document. And the status-note field was used by 104 live manifests while documented nowhere. Declares it, and permits a dispatcher to write it: recording what it did is observation, not judgement |

| CR-054 | `ops-config` schema | Medium | **Implemented v1.46.0.** A folder had no way to declare which chat its work is posted to or which repository it concerns, so a dispatcher guessed from a live listing and a person relied on recognising a name. Declares `external_systems` with `chats:` and `repos:`, resolved by the normal config chain. A declaration and never a credential, hand-written so no tool can append to it. Partially addresses the "systems of record" key proposed in CR-042 |

| CR-055 | vault conventions | Medium | **Implemented v1.47.0.** CR-054 let a folder declare the repositories it concerns, but nothing read them. Declares `<venture>/.githubmeta/` and the component that fills it — the sibling of `.teamschats/`, same layout, with a day's file a snapshot rather than a merge since issue state is a reading not an event |

| CR-068 | vault conventions | Medium | **Implemented v1.69.0, breaking (contract 21).** `<venture>/.chats/` becomes `<venture>/.teamschats/`. "Chats" stopped being unambiguous once Claude Code transcripts were also called chats, and only `teamschatcli` ever wrote the folder — the name now says whose messages are in it, the way its sibling `.githubmeta/` does. `external_systems.chats` is deliberately NOT renamed: that key names a class of system, not a path |

_Specs for CR-042 and CR-047 are tracked outside this repo (they carry vault evidence); rows here are generic._

---

## Implemented

Implemented CRs are tracked in [CHANGELOG.md](../../CHANGELOG.md). Highest implemented: **CR-070** (`management-only` classification, v1.71.0).

CR-017–CR-030 were drafted and implemented 2026-07-07/10 from a private vault-usage audit and live usage; the full CR specs contain vault-specific evidence and are tracked privately (not in this repo), so their rows carry generic notes only.

| CR | Title | Version | Notes |
|----|-------|---------|-------|
| CR-070 | A third `classification` value — `management-only` | v1.71.0 (2026-09-22) | Named recipients rather than a group; the first two values scale a group, the third leaves group distribution. CR-066 had settled the enum by surveying live manifests, which establishes what values are *called* but not how many exist — the next item staged needed one the survey could not have seen, and was written with an undeclared value by an author following a standard that already defined three levels. Permissiveness order declared explicitly, since warn-on-widening needs it. Also lands the field in the `/outbox` manifest schema, where CR-066 had not reached |
| CR-046 | Two content shapes the insight taxonomy has no slot for | v1.38.0 (2026-09-20) | `metric` added — a measurement where the number *is* the claim, with optional value/unit/baseline/period/trend, and excluded from rule promotion since a repeating measurement is a time series. It had been landing in `learning`, which had grown to 36% of a corpus and stopped discriminating; the extraction contract already emitted a metrics block with nowhere to store it. The second half — a parameter bounding a decision not yet made — was deferred on thin evidence |
| CR-038 | Generated-view isolation and system-file language | v1.36.1 (2026-09-08) | A generated read view among its own sources needs a hidden subfolder, not a skip flag (CR-033 showed skip-lists get missed); the dot then means *unreachable by scanners*, a third meaning beside dormant and blocked. System files take English names, two exceptions declared |
| CR-037 | Rule hierarchy and conflict resolution for `vault_conventions` | v1.36.0 (2026-09-07) | Thirteen rules from seven CRs sat in a flat list; two disagreed about the same surface and the inconsistency shipped. Three levels (invariant/rule/guideline, 6/6/1) declared per rule; conflict order; exceptions must be **named** in `exceptions:`; equal-specificity conflict = contract defect, report don't choose |
| CR-036 | File placement classes and singleton surfaces | v1.36.0 (2026-09-07) | CR-010 declared *which* files exist, never how many or where. Three classes (singleton/per_folder/per_boundary); singleton test is principled — *would a scoped instance defeat the surface's purpose?*; `.transcripts`/`.ephemeral` consolidated; CHANGELOG/README gain conditions (130 of 174 CHANGELOGs had no sibling `.archive/`) |
| CR-035 | `_tasks.yaml` as source of truth for the personal working document | v1.36.0 (2026-09-07) | Supersedes CR-022 in part. Markdown working doc reached 438 lines, 273-char median task line, 56 % non-task content. Tasks → YAML (v2 + `triage_id`); markdown becomes a generated view; `_capture.md` as write path. Median 273 → 87 chars, view 438 → 52 lines |
| CR-034 | `_` vs `.` prefix conventions and the audit lifecycle | v1.36.0 (2026-09-07) | The prefix answers **read frequency**, never write ownership (`_insights.yaml` is machine-written yet underscored). `.knowledge/` and `.handoff/_archive` declared exceptions; dot surfaces typed dormant vs blocked; audit lives in `_inbox` only while in use |
| CR-031 | `/analytics pipeline` — outcome layer, horizontal quarter pivot, per-day averages | v1.33.2 (2026-07-27) | Insights/tasks/changelog/outbox counted via field-level scans; grouped chain table; active-day density; mandatory measurement notes; classification fixes |
| CR-030 | Guard modes + rollout to sibling repos | v1.33.1 (2026-07-10) | `guard.mode secrets-only` for private repos (keys-only, no false positives on infra content); shared hook via absolute hooksPath; cross-repo history audit clean |
| CR-029 | Invented-examples allowlist + scheduled repo privacy watch | v1.33.0 (2026-07-10) | Name-like tokens must match the public allowlist of fake names; privacy-scan.sh in hook + weekly sweep; baseline adjudicated |
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
| CR-056 | `/outbox` naming | Low | **Implemented v1.48.0.** `<context>` in a staged folder name was never defined, so four items in one vault interpreted it four ways in five days. The right side names the subject of the send, not a file inside it; the left names the recipient, not the project |
| CR-057 | `ops` Step 9 | Medium | **Implemented v1.49.0.** Nothing compared an agenda against what the meeting produced. Adds `carry_forward` and `build_agenda.py`, which counts how many consecutive sessions each unlanded item has carried and escalates at three. Owner comes from a defined position; anything else is UNOWNED, which is the finding |
| CR-058 | `ops` Step 9 | Medium | **Implemented v1.49.0** (retrieval; the recap amendment is proposed). Reads the chat and repo archives declared in `external_systems` before the agenda — first skill-side consumer of CR-054, first reader of CR-047 and CR-055 together. No credential, no network, no new configuration |
| CR-059 | `ops` Step 9 | Medium | **Implemented v1.50.0.** The outbound digest for people who were not in the room. Shipped with one amendment: generated **on request**, not as a side effect — it is the only Step 9 artifact that leaves the building, and from the transcript alone it is confidently incomplete in a way its readers cannot check. Renumbered from CR-054 |
| CR-061 | `ops` new subcommand | Medium | **Implemented v1.55.0.** `/ops brief` — one read-only pass answering where a recurring project stands: loop position, chain integrity, what is carrying and unowned, archive freshness, staged-and-unsent, last record movement. `/bod` for a coordination project. Reads only what already exists; the gap was that nothing read it together |
| CR-063 | `ecosystem` + `ops` help | Low | **Implemented v1.60.0.** A loop step names its `command`, and `/ops help` renders the declaration instead of becoming a fourth hand-written copy. The checker holds `manual` and `command` against each other, and a step silent about being neither now fails |
| CR-065 | `ops` new subcommand | Medium | **Implemented v1.66.0.** `/ops projects` — groups project-shaped folders by how far each is wired: loop wired, configured without a loop, material only, dormant. Does not replace a hand-written registry: intent and wiring are different questions |

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

*Last updated: 2026-09-21 — CR-047 through CR-055 implemented (v1.39.0–v1.47.0). Earlier: CR-040, CR-041, CR-043, CR-044, CR-045 (v1.37.0–v1.37.3); CR-042 proposed. CR-017 onward: specs tracked outside this repo.*
