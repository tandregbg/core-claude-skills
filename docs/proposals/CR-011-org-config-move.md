# CR-011: Org-config move from skill repos to vault folders

| Field | Value |
|-------|-------|
| **CR Number** | CR-011 |
| **Date** | 2026-04-27 |
| **Author** | Alex + Claude Code |
| **Status** | Implemented (Phase 1+2; Phase 5 deferred to v1.17.0) |
| **Implementation Date** | 2026-04-29 |
| **Priority** | Medium |
| **Complexity** | Low-Medium |
| **Estimated Scope** | `/ops` skill resolution, three org configs migrated, three skills retired |
| **Related CRs** | CR-010 (vault_conventions), CR-009 (contact classification — touches ops-config) |
| **Depends On** | None (CR-010 documents the convention but CR-011 can land without it) |
| **Breaking Changes** | Yes — `/ops` config resolution order changes; existing `*-ops-config` skills become deprecated |

---

## Executive Summary

Today, organization-specific configuration (`team`, `language`, `swedish_chars`, `terminology`, `responsibility_matrix`) lives in dedicated skill repositories: `acme-ops-config/acme.yaml`, `bravo-ops-config/bravo.yaml`, `delta-ops-config/delta.yaml`. Each is a one-file skill whose entire purpose is to register one YAML file with Claude Code. Three repos, three SKILL.md files, three symlinks — to express three small YAML files describing folders that already exist in the user's vault.

Move each org-config YAML into the vault folder it describes:

- `acme-skills/skills/acme-ops-config/acme.yaml` → `<vault>/acme/_ops.yaml`
- `bravo-skills/skills/bravo-ops-config/bravo.yaml` → `<vault>/bravo/_ops.yaml`
- `~/.claude/skills/delta-ops-config/delta.yaml` → `<vault>/delta/_ops.yaml`

Update `/ops` skill resolution to read folder-local `_ops.yaml` walking up from CWD, then fall back to existing chain. Retire the three `*-ops-config` skills.

**Current Problems:**
1. Three skill repos exist solely to register one YAML file each — pure scaffolding with no logic.
2. Adding a new org (`dolutions`, `mindtastic` — both already have vault folders without configs) requires creating a new skill repo, making this a high-friction action.
3. Distribution friction — a new user installing the suite would need to clone all three `*-ops-config` skill repos for symlink discovery to work, adding install steps.
4. Config drifts from vault content — when working in `<vault>/acme/meetings/`, the team list lives in `~/repos/acme-skills/skills/acme-ops-config/acme.yaml`, a completely separate filesystem location owned by a different repo.

---

## Problem Analysis

### What `*-ops-config` skills actually contain

Per investigation (2026-04-27):

```
acme-ops-config/
  SKILL.md         (registration metadata only, not user-invocable)
  acme.yaml     (the actual config: team, language, swedish_chars, terminology, workflows)

bravo-ops-config/
  SKILL.md         (same)
  bravo.yaml         (same)

delta-ops-config/
  SKILL.md         (same)
  delta.yaml      (same)
```

Each is a "skill" in name only. The SKILL.md does nothing except declare existence. The YAML is data.

### Current `/ops` config resolution

Per `core-skills/skills/ops-config/README.md`:

```
1. Project-level: .claude/ops-config.yaml in project root
2. Org config skill: ~/.claude/skills/{org}-ops-config/{org}.yaml
3. Base defaults: ~/.claude/skills/ops-config/base.yaml
```

Step 2 is what changes. The skill-discovery mechanism (look in `~/.claude/skills/`) gets replaced with a vault-walk (look in `<vault>/<folder>/_ops.yaml`).

### Why the move is the right shape

1. **The data already lives in the folder it describes.** When processing a Acme meeting, the file lives at `<vault>/acme/meetings/...`. Today its team list lives in a separate repo entirely. Co-location is more correct.
2. **No more skill repos for pure data.** `acme-skills` and `bravo-skills` can keep existing for *real* skills, but they shed the config burden.
3. **Adding new orgs becomes weightless.** Drop a `_ops.yaml` in the folder. Done.
4. **Configs sync with the vault.** Edit on one machine, sync via iCloud/Obsidian Sync, available everywhere — same as everything else.
5. **Distribution becomes obvious.** A new user installing the suite never needs to know `*-ops-config` skills exist.

---

## Proposed Solution

### Phase 1: Update `/ops` skill resolution chain

New chain, in priority order:

1. **Project-level** (unchanged): `.claude/ops-config.yaml` in CWD
2. **Folder-local** (NEW): walk up from CWD until a `_ops.yaml` is found anywhere on the path. The closest one wins.
3. **Vault-wide** (NEW): `<vault-root>/_config/base.yaml` if present
4. **Skill defaults** (unchanged): `~/.claude/skills/ops-config/base.yaml`

The vault root for step 2-3 is found by walking up from CWD until `_inbox/`, `_outbox/`, or `.obsidian/` is found, or via `VAULT_ROOT` env var, or via per-tool override.

**Backward compatibility:** the existing org-config skill chain (step 2 in the old chain) is removed in v1.16.0. The three `*-ops-config` skills emit a one-time deprecation warning when their symlink is still in `~/.claude/skills/` after upgrade. After v1.17.0, the warning becomes an error and the user must remove the symlinks.

### Phase 2: Migrate the three org configs

Manual migration steps the user runs once (or a `scripts/migrate-org-configs.sh` we can ship):

1. `cp ~/repos/acme-skills/skills/acme-ops-config/acme.yaml <vault>/acme/_ops.yaml`
2. `cp ~/repos/bravo-skills/skills/bravo-ops-config/bravo.yaml <vault>/bravo/_ops.yaml`
3. `cp ~/.claude/skills/delta-ops-config/delta.yaml <vault>/delta/_ops.yaml`
4. Verify each new `_ops.yaml` parses with `python3 -c "import yaml; yaml.safe_load(open('...'))"`.
5. Run a quick `/ops status` smoke test in each org folder to confirm the new resolution finds the right config.
6. After confirmation, `rm` (or `unlink` for symlinks) the old `*-ops-config` symlinks in `~/.claude/skills/`.
7. Optional: archive the old `*-ops-config` directories in their source repos to a `.archive/` subfolder (don't delete in case rollback is needed).

### Phase 3: Vault-wide overrides via `_config/base.yaml`

(Optional, fits cleanly with the same change.) Some users may want vault-wide overrides that apply across all folders without duplicating in each `_ops.yaml`. The new resolution chain step 3 looks at `<vault-root>/_config/base.yaml`. If it exists, its values override skill defaults but yield to folder-local `_ops.yaml`. This keeps the door open for future config layering without making it required.

### Phase 4: Update `ops-config` skill docs

1. `skills/ops-config/README.md` — rewrite the "Config Resolution Order" and "Creating New Org Configs" sections.
2. `skills/ops-config/schema.md` — note that the schema is now read from `<folder>/_ops.yaml` and `<vault>/_config/base.yaml`.
3. Add a deprecation notice for the old skill-based discovery.

### Phase 5: Drop the org-config skills

After v1.17.0 (one release after Phase 1-4 ship):

1. Archive `acme-skills/skills/acme-ops-config/` → `acme-skills/.archive/`
2. Same for bravo-skills and delta-ops-config
3. Remove the corresponding symlinks from `~/.claude/skills/`
4. Update each org-skills repo's README to note the migration

---

## Implementation Plan

### Phase 1 — `/ops` resolution chain (this CR's main code change)

1. Edit `skills/ops/SKILL.md` — find the section that documents the resolution order. Update to the new four-step chain.
2. Edit `skills/ops-base/SKILL.md` — same (this is referenced by /ops, /transcript, /preparation).
3. Add a new "How config is found" section to `skills/ops-config/README.md` documenting:
   - Project-level `.claude/ops-config.yaml`
   - Folder-local `_ops.yaml` (walking up from CWD)
   - Vault-wide `_config/base.yaml`
   - Skill `base.yaml`

### Phase 2 — migrate org configs

Documented above. Alex runs once on his Mac. No code change needed.

### Phase 3 — `_config/` support (optional, can defer)

If we ship Phase 3 with this CR, also document `<vault>/_config/base.yaml` in:
- `skills/ops-config/README.md`
- `ecosystem.yaml` `vault_conventions:` (CR-010)

### Phase 4 — docs

1. Rewrite `skills/ops-config/README.md` config resolution section.
2. Update `README.md` (top-level) if it mentions org-config skills.
3. CHANGELOG entry under `[1.16.0]` `### Changed` and `### Migration`.

### Phase 5 — retirement (one release later)

Don't do in this CR. Tracked as a follow-up: archive the three `*-ops-config` directories after v1.17.0 ships and Alex confirms migration is stable.

---

## Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `skills/ops/SKILL.md` | Modify | Update config resolution section |
| `skills/ops-base/SKILL.md` | Modify | Update config resolution section |
| `skills/ops-config/README.md` | Modify | Rewrite resolution order; remove "Creating New Org Configs" section |
| `skills/ops-config/schema.md` | Modify | Note new resolution paths |
| `CHANGELOG.md` | Modify | `[1.16.0]` entry: Changed, Migration |
| `<vault>/acme/_ops.yaml` | Create | (in vault, not repo) Migrated from acme-ops-config |
| `<vault>/bravo/_ops.yaml` | Create | (in vault, not repo) Migrated from bravo-ops-config |
| `<vault>/delta/_ops.yaml` | Create | (in vault, not repo) Migrated from delta-ops-config |
| `~/.claude/skills/{acme,bravo,delta}-ops-config` | Remove (later) | Defer to Phase 5 |

---

## Testing Plan

### Test Case 1: `/ops status` in folder with `_ops.yaml`

- `cd <vault>/acme && /ops status`
- Expected: detects Acme team, language, terminology from `<vault>/acme/_ops.yaml`.
- Verify against the values that were in the old `acme-ops-config/acme.yaml`.

### Test Case 2: `/ops status` in deeply nested folder

- `cd <vault>/acme/meetings/management/ && /ops status`
- Expected: walks up, finds `<vault>/acme/_ops.yaml`, applies it.

### Test Case 3: `/ops status` in folder with no `_ops.yaml`

- `cd <vault>/dolutions && /ops status` (no config exists today — currently falls through to base).
- Expected: walks up, no `_ops.yaml` found, no `_config/base.yaml`, falls through to skill `base.yaml`. Generic config used.

### Test Case 4: project-level override still wins

- `cd /tmp/some-non-vault-project && echo 'organization: TestOrg' > .claude/ops-config.yaml && /ops status`
- Expected: project-level wins. Vault walk doesn't apply since not in a vault.

### Test Case 5: vault-wide `_config/base.yaml`

- Create `<vault>/_config/base.yaml` with `language: english`.
- `cd <vault>/acme && /ops status` — expected: uses acme `_ops.yaml` (which says `language: per_claude_md`), not vault-wide base (since folder-local wins).
- `cd <vault>/dolutions && /ops status` — expected: uses vault-wide `language: english` (since no folder-local `_ops.yaml`).

### Test Case 6: deprecation warning

- After Phase 1 lands, with `~/.claude/skills/acme-ops-config/` symlink still present:
- `/ops status` in `<vault>/acme`
- Expected: warning printed: "Found legacy `acme-ops-config` skill. Run `unlink ~/.claude/skills/acme-ops-config` after migrating to `<vault>/acme/_ops.yaml` (CR-011)."

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration of YAML files goes wrong (missing fields, wrong location) | Low | Medium | Verify with `/ops status` smoke test in each org folder before deleting old files |
| Walking-up logic has corner cases (symlinks, absolute paths from outside vault) | Medium | Low | Test with deeply nested paths and symlinked folders. Document expected behaviour in SKILL.md. |
| Old skill-based discovery still resolves and causes conflicting config | Low | Medium | Phase 5 retirement is explicit; deprecation warning makes drift visible until then. |
| User sees no team data after migration because resolution path doesn't find file | Medium | Medium | Test Case 1-3 catches this. If still unclear, document fallback: explicit `--config <path>` override on `/ops`. |
| New users (no migration history) install the suite, are confused that config goes in vault folders | Low | Low | Document in `ops-config/README.md` and suite charter. New-user docs go to "drop a `_ops.yaml` in your org folder." |

---

## Rollback

1. Revert the resolution-chain code change in `skills/ops/SKILL.md` and `skills/ops-base/SKILL.md`.
2. Restore the `*-ops-config` skill docs to their pre-CR-011 wording.
3. Symlinks in `~/.claude/skills/` were never removed in this CR (Phase 5 is separate), so they still resolve.
4. The new `<vault>/<folder>/_ops.yaml` files can stay in place — the old chain just won't read them. They become inactive data until rollback is reverted again.

Net rollback risk: low. The migration is additive (new files in vault); the resolution change is a pure swap; no data is destroyed.

---

## Success Criteria

1. `/ops status` from `<vault>/acme/` returns the same team and terminology as before the migration.
2. `/ops status` from `<vault>/acme/meetings/management/` finds the same config (walks up).
3. `/ops status` from a folder with no `_ops.yaml` falls through gracefully to defaults.
4. Project-level `.claude/ops-config.yaml` continues to win over folder-local `_ops.yaml`.
5. Migration script (or manual steps) leaves no orphan files; old `*-ops-config` symlinks emit deprecation warnings.
6. CHANGELOG documents the migration with explicit migration steps for any other user (future Alex re-installs, future contributors).
7. After Phase 5 (one release later), the three `*-ops-config` skill directories are archived and the symlinks removed cleanly.

---

## References

- Suite charter: `vault-pulse/docs/the-guide-architecture.md` (esp. §3 components, §11 open question Q1 about umbrella naming — independent of this CR but related context)
- Current `/ops` resolution: `core-skills/skills/ops-config/README.md`
- Current org configs:
  - `~/repos/acme-skills/skills/acme-ops-config/acme.yaml`
  - `~/repos/bravo-skills/skills/bravo-ops-config/bravo.yaml`
  - `~/.claude/skills/delta-ops-config/delta.yaml`
- Vault-relative path conventions: CR-010 `vault_conventions:` block (when it lands)
- Schema: `core-skills/skills/ops-config/schema.md`
