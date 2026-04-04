# ops-config

Base configuration system for the ops skills framework.

## Purpose

Provides the **schema definition** and **base defaults** for ops configuration. Organization-specific configs live in their own skill directories (e.g. `acme-ops-config`, `bravo-ops-config`).

## Config Resolution Order

Configs are resolved in priority order (first match wins):

1. **Project-level**: `.claude/ops-config.yaml` in the project root
2. **Org config skill**: `~/.claude/skills/{org}-ops-config/{org}.yaml`
3. **Base defaults**: `~/.claude/skills/ops-config/base.yaml`

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

### Creating New Org Configs

Create a new skill directory `{org}-ops-config` in an org-specific repo:

1. Create `{org}-ops-config/SKILL.md` (not user-invocable, description only)
2. Copy `base.yaml` as `{org}.yaml` starting point
3. Set `organization` and `language`
4. Define `team` with roles and areas
5. Add organization-specific `terminology`
6. Configure `workflows` as needed
7. Symlink into `~/.claude/skills/`

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
