# CR-010: Vault file conventions in `ecosystem.yaml`

| Field | Value |
|-------|-------|
| **CR Number** | CR-010 |
| **Date** | 2026-04-27 |
| **Author** | Alex + Claude Code |
| **Status** | Proposed |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `ecosystem.yaml`, schema doc |
| **Related CRs** | CR-011 (org-config move), CR-012 (`_inbox/` schema), CR-009 (contact classification) |
| **Depends On** | None |
| **Breaking Changes** | No (pure documentation, no behaviour change) |

---

## Executive Summary

`ecosystem.yaml` is already the shared contract for type enums, skill metadata, and schema versions. It does NOT yet declare the file-shape conventions of the vault itself: which files appear at vault root vs per-folder, who writes them, who reads them, what schema each one follows.

Both **Marvin** (renamed core-skills-visualisation, runs on Mac, reads vault YAML) and **Trillian** (the future VaultPulse + voice-memo-watcher merger, writes to `_inbox/`) need this contract to be machine-readable. So do future tools: a CLI, an MCP server, a third-party skill, an external import script.

This CR adds a `vault_conventions:` block to `ecosystem.yaml` that documents the canonical file conventions. **Pure documentation. No code change.** It formalises what is already implicit.

**Current Problems:**
1. Each tool reads vault files based on hardcoded paths and assumed shapes — a rename or schema bump means manual updates in N places.
2. No canonical answer to "what files appear in the vault, what shape are they, who owns them?" — implicit knowledge that is not transferable.
3. Trillian and Marvin (per the suite charter at `vault-pulse/docs/the-guide-architecture.md`) need a contract to read against. Without it, integration is informal.

---

## Problem Analysis

### What `ecosystem.yaml` currently declares

```yaml
contract_version: 1
core_skills_version: "1.15.10"

schemas:
  ops_config: "1.3"
  contact_meta: "1.1"
  tasks: 2
  insights: 1

insight_types: { ... }
contact_classification: { ... }
skills: { ... }
output_artifacts:
  per_folder: [_insights.yaml, _tasks.yaml, CHANGELOG.md]
  vault_root: [_analytics/, _inbox/, _outbox/, _Dashboard.md, _tasks.yaml, _tasks-history.md]
visualisation_features: { ... }
```

`output_artifacts` is the closest thing today, but it's just a list of names — no schema link, no writer/reader declaration, no semantics.

### What a complete contract needs

For each file the suite cares about:

- **Path pattern** — vault-relative path (e.g., `_inbox/<id>.md`, `<folder>/_tasks.yaml`)
- **Purpose** — one-line description
- **Schema** — link to schema doc and version
- **Writers** — which skill(s) or component(s) produce this file
- **Readers** — which skill(s) or component(s) consume this file
- **Lifecycle** — append-only / versioned / replaced / archived

This lets a new tool (Trillian, Marvin, future skills, external scripts) discover what files exist and what they look like by reading one YAML.

---

## Proposed Solution

Add a `vault_conventions:` block to `ecosystem.yaml`. Structure:

```yaml
# Vault file conventions — what files appear in a user's vault, who writes them,
# who reads them. Authoritative for any tool that reads or writes vault files.
vault_conventions:
  # Vault-root files and folders
  vault_root:
    - path: "_inbox/"
      purpose: "Capture: unprocessed input awaiting classification"
      schema: "docs/schemas/inbox.md"  # CR-012 will create this
      writers: ["/inbox", "trillian", "deep-thought"]
      readers: ["/inbox", "trillian", "marvin"]
      lifecycle: "append; items move to .archive/ after processing"

    - path: "_inbox/.audio/"
      purpose: "Raw audio files captured by Trillian, awaiting transcription"
      schema: null  # raw m4a, no schema
      writers: ["trillian"]
      readers: ["trillian", "user (manual)"]
      lifecycle: "ephemeral — deleted after transcript confirmed (configurable retention)"

    - path: "_outbox/"
      purpose: "Delivery: PDFs and packages ready to send"
      schema: null  # filesystem layout, not YAML
      writers: ["/md2pdf", "user (manual)"]
      readers: ["vaultpulse/trillian", "mail.app", "user"]
      lifecycle: "user-managed; nothing auto-deletes"

    - path: "_config/"
      purpose: "Vault-wide overrides for skill defaults (optional)"
      schema: "skills/ops-config/schema.md"
      writers: ["user (manual)"]
      readers: ["/ops", "/insights", "/tasks", "/analytics"]
      lifecycle: "stable; rarely changes"

    - path: "_analytics/"
      purpose: "Dated snapshots of vault-level analytics"
      schema: null  # markdown reports + YAML data files
      writers: ["/analytics"]
      readers: ["marvin", "user"]
      lifecycle: "append; older snapshots auto-archived"

    - path: "_tasks.yaml"
      purpose: "Vault-root task aggregation (optional, legacy from v1)"
      schema: "tasks v2"
      writers: ["/tasks"]
      readers: ["/tasks", "/daily-dashboard", "marvin"]
      lifecycle: "deprecated in favour of per-folder _tasks.yaml; kept for back-compat"

    - path: "_Dashboard.md"
      purpose: "Daily dashboard composition"
      schema: null  # markdown, structure documented in /daily-dashboard SKILL.md
      writers: ["/daily-dashboard"]
      readers: ["user", "marvin"]
      lifecycle: "regenerated daily"

  # Per-folder files (any folder in the vault may contain these)
  per_folder:
    - path: "<folder>/_ops.yaml"
      purpose: "Per-folder operations config (org config, team, language, etc.)"
      schema: "skills/ops-config/schema.md"
      writers: ["user (manual)"]
      readers: ["/ops", "/insights", "/tasks", "/analytics", "/daily-dashboard"]
      lifecycle: "stable; rarely changes"
      added_by: "CR-011"

    - path: "<folder>/_tasks.yaml"
      purpose: "Per-folder open tasks (v2 distributed)"
      schema: "tasks v2"
      writers: ["/tasks", "/transcript", "/ops"]
      readers: ["/tasks", "/daily-dashboard", "marvin"]
      lifecycle: "live; tasks added/completed/archived in place"

    - path: "<folder>/_insights.yaml"
      purpose: "Extracted decisions, learnings, patterns, evolution feedback"
      schema: "insights v1"
      writers: ["/insights", "/ops", "/transcript"]
      readers: ["/insights", "/analytics", "marvin"]
      lifecycle: "append-mostly; auto-applied edits via /insights propose"

    - path: "<folder>/_meta.yaml"
      purpose: "Folder metadata (esp. for _contacts/<name>/ folders)"
      schema: "contact-meta v1.1"
      writers: ["user (manual)", "/ops"]
      readers: ["/ops", "/insights", "/analytics", "/daily-dashboard"]
      lifecycle: "stable"

    - path: "<folder>/_summary.yaml"
      purpose: "Folder-level summary (CR-008, generated by Ollama)"
      schema: "docs/schemas/summary-yaml.md"
      writers: ["scripts/generate_summaries.py"]
      readers: ["marvin", "user"]
      lifecycle: "regenerated when stale (cron-restart 04:00 daily)"

    - path: "<folder>/CHANGELOG.md"
      purpose: "Per-folder changelog of structural changes"
      schema: null  # plain markdown
      writers: ["/ops normalize", "user", "/ops"]
      readers: ["user"]
      lifecycle: "append"

  # Conventions that govern multiple files
  rules:
    - id: "vault_relative"
      rule: "All paths are vault-relative. The vault root is determined by walking up from CWD until _inbox/, _outbox/, or .obsidian/ is found, or by VAULT_ROOT env var, or by a tool-specific override."

    - id: "single_inbox_outbox"
      rule: "Exactly one _inbox/ and exactly one _outbox/ per vault, both at vault root. Per-folder inboxes/outboxes are not part of this contract."

    - id: "config_resolution_order"
      rule: "/ops resolves config in this order: project-level .claude/ops-config.yaml > nearest <folder>/_ops.yaml walking up from CWD > <vault>/_config/base.yaml > skill base.yaml. First match wins."

    - id: "yaml_naming"
      rule: "Folder-level metadata files use leading underscore (_tasks.yaml, _insights.yaml, _ops.yaml). Hidden/transient files use leading dot (.archive/, _inbox/.audio/)."
```

### Why a separate `vault_conventions:` block (not extending `output_artifacts`)

`output_artifacts` is a flat list. `vault_conventions` is a structured contract with writer/reader semantics. Different shape, different audience (tool authors vs. version-bump checkers). Keep them separate.

### Schema file references

This CR cross-references three schema files. Two exist (`skills/ops-config/schema.md`, `docs/schemas/summary-yaml.md`); one is created by CR-012 (`docs/schemas/inbox.md`). For now, `docs/schemas/inbox.md` is referenced as a forward link; if CR-012 is rejected, this CR can ship with `schema: null` for `_inbox/<id>.md` and document the shape inline.

---

## Implementation Plan

### Phase 1: Add the block to ecosystem.yaml

1. Edit `ecosystem.yaml` — add `vault_conventions:` block (the YAML above).
2. Bump `contract_version: 1` → `contract_version: 2` to signal the schema extension. Document in a comment.
3. Update CHANGELOG.md under `[1.16.0]` (next release): "Added: `vault_conventions` block in ecosystem.yaml documenting canonical vault file shapes per CR-010."

### Phase 2: Verify alignment

1. Run `scripts/check-ecosystem-alignment.sh` to confirm version alignment with downstream consumers (visualiser, landing page).
2. Update `core-skills-visualisation` (Marvin) CLAUDE.md to reference `vault_conventions` as the source of truth for which files to parse.

### Phase 3: Document and announce

1. Add a section to `README.md` introducing `vault_conventions` as the formal contract.
2. Cross-link from suite charter at `vault-pulse/docs/the-guide-architecture.md` §6.

---

## Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `ecosystem.yaml` | Modify | Add `vault_conventions:` block. Bump `contract_version` to 2. |
| `CHANGELOG.md` | Modify | `[1.16.0]` entry under `### Added`. |
| `README.md` | Modify | Reference `vault_conventions` in the contract section. |
| `core-skills-visualisation/CLAUDE.md` | Modify (separate repo) | Note that `vault_conventions` is the source of truth for parsed files. |

---

## Testing Plan

### Test Case 1: alignment script passes

- Run `scripts/check-ecosystem-alignment.sh`.
- Verify it does not error on the new block (likely just unknown block — OK).

### Test Case 2: human-readable

- Read the `vault_conventions` block end-to-end without referring to docs.
- Confirm any tool author could discover what files exist and what they look like.

### Test Case 3: round-trip with downstream consumer

- Marvin (visualisation) parses `ecosystem.yaml` (already does for `skills:` and `insight_types:`).
- Add a 5-line check in Marvin: read `vault_conventions.per_folder[].path` and confirm parsed files match the actual `glob` patterns in the parsers. If a parser exists for a file not in the contract, flag drift.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `contract_version` bump breaks downstream | Low | Low | Visualiser checks for compatibility; bump is additive, no field removed. |
| Cross-reference to CR-012 schema file is dangling if CR-012 lands later | Medium | Low | Document inline in `vault_conventions` comments as fallback; remove forward link if CR-012 is delayed. |
| Drift between contract and reality (someone adds a new vault file without updating contract) | Medium | Medium | Marvin's parser-vs-contract drift check (Test Case 3) catches this on next Marvin update. |

---

## Rollback

1. Remove the `vault_conventions:` block from `ecosystem.yaml`.
2. Revert `contract_version` to 1.
3. Revert CHANGELOG entry.
4. No other consumers depend on this block during Phase 1, so rollback is clean.

---

## Success Criteria

1. `vault_conventions:` block exists in `ecosystem.yaml` and parses cleanly.
2. Every file produced or consumed by core-skills today is documented in the block.
3. Marvin's CLAUDE.md references `vault_conventions` as the file-shape reference.
4. The suite charter at `vault-pulse/docs/the-guide-architecture.md` §6 cross-links here.
5. A future tool author (e.g., the Trillian implementer) can read `ecosystem.yaml` alone and know what files to write to and read from.

---

## References

- Suite charter: `vault-pulse/docs/the-guide-architecture.md` §6 (viewing surfaces) and §13 (references)
- Existing `ecosystem.yaml` at `core-skills/ecosystem.yaml`
- Schema doc: `core-skills/skills/ops-config/schema.md`
- Schema doc: `core-skills/docs/schemas/summary-yaml.md`
- Future schema doc (CR-012): `core-skills/docs/schemas/inbox.md`
- Alignment script: `core-skills/scripts/check-ecosystem-alignment.sh`
