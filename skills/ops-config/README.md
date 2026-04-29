# ops-config

Base configuration system for the ops skills framework.

## Purpose

Provides the **schema definition** and **base defaults** for ops configuration. Organization-specific configs live in their own skill directories (e.g. `acme-ops-config`, `bravo-ops-config`).

## Config Resolution Order

Configs are resolved in priority order (first match wins):

1. **Project-level**: `.claude/ops-config.yaml` in the project root
2. **Folder-local** (CR-011): nearest `_ops.yaml` walking up from CWD until vault root. Vault root is detected by walking up until `_inbox/`, `_outbox/`, or `.obsidian/` is found, or via `VAULT_ROOT` env var.
3. **Vault-wide** (CR-011, optional): `<vault-root>/_config/base.yaml` if present
4. **Skill defaults**: `~/.claude/skills/ops-config/base.yaml`

### Deprecated: skill-based org configs

The previous chain step "Org config skill: `~/.claude/skills/{org}-ops-config/{org}.yaml`" is **deprecated as of v1.16.0**. If a `*-ops-config` skill is still present (`~/.claude/skills/acme-ops-config/`, `bravo-ops-config/`, `delta-ops-config/`), it remains a fallback between step 3 and step 4 with a one-time deprecation warning per session. The fallback is removed entirely in v1.17.0.

Migration: copy `<skill>/{org}.yaml` -> `<vault>/<org>/_ops.yaml`. See CHANGELOG `[1.16.0]` `### Migration` for the exact steps.

## Files

| File | Purpose |
|------|---------|
| `schema.md` | Configuration schema definition |
| `base.yaml` | Default fallback values |

## Usage

### In the /ops Skill

The `/ops` skill reads config to:
- Determine output language
- Access team structure for attribution
- Apply organization-specific terminology
- Execute configured workflows (file updates, action propagation, agenda management, post-processing)

### Creating New Org Configs (CR-011)

Drop a `_ops.yaml` in the org's vault folder:

1. `cp ~/.claude/skills/ops-config/base.yaml <vault>/<org>/_ops.yaml`
2. Set `organization` and `language`
3. Define `team` with roles and areas
4. Add organization-specific `terminology`
5. Configure `workflows` as needed
6. Done -- `/ops` finds it automatically when CWD is anywhere under `<vault>/<org>/`.

No skill repo, no symlink, no SKILL.md. The data lives next to the content it describes. Configs sync with the vault (iCloud/Obsidian Sync) so editing on one Mac propagates to the others.

The contract for which files are read where is documented in [`ecosystem.yaml`](../../ecosystem.yaml) under `vault_conventions:` (CR-010).

### Project-Level Overrides

Projects can override any config value by creating `.claude/ops-config.yaml`:

```yaml
# Example: Override language for a specific project
language: swedish

# Example: Add project-specific team members
team_additions:
  - name: Jay
    role: Development Lead
    areas: [mobile, flutter, testing]
```

## Schema Version

Current schema: v1.0

See `schema.md` for complete schema definition.
