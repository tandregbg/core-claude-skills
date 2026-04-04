# Update Skills

Manage skill repo updates, symlink health, and installation across multiple source repositories.

## Usage

```
/update-skills [operation] [arguments]
```

If no operation is specified, defaults to `update`.

## Operations

| Command | Description |
|---------|-------------|
| `/update-skills` | Fetch, pull, and symlink new skills from all repos |
| `/update-skills update` | Same as above (explicit) |
| `/update-skills status` | Show repos, versions, remotes, symlink state |
| `/update-skills check` | Verify symlink health (broken, missing, orphaned) |
| `/update-skills install <repo>` | Clone a repo and create all symlinks |

## Sources

The skill maintains a sources table for repo identity and remote URLs. Local paths are discovered dynamically at runtime.

| Repo | origin (GitHub) | local (NAS) |
|------|-----------------|-------------|
| `core-skills` | `https://github.com/your-username/core-claude-skills.git` | `ssh://git@nas.local//srv/git/core-skills.git` |
| `acme-skills` | `https://github.com/acme-org/acme-claude-skills.git` | `ssh://git@nas.local//srv/git/acme-skills.git` |
| `bravo-skills` | `https://github.com/bravo-org/bravo-skills.git` | `ssh://git@nas.local//srv/git/bravo-skills.git` |
| `generic-design-system-kit` | `https://github.com/bravo-org/generic-design-system-kit.git` | -- |

Additional repos are discovered automatically by scanning symlinks in `~/.claude/skills/`.

## Repo Discovery

Repo locations are discovered dynamically -- no hardcoded paths:

1. **Self-discovery** -- resolves the `update-skills` symlink to find where `core-skills` is cloned. The parent of that repo root becomes the base directory for sibling repos.
2. **Symlink scanning** -- resolves each symlink in `~/.claude/skills/` to its git root to discover all repos.
3. **Sources table** -- provides repo names and remote URLs. Matched against discovered repos by directory basename.

This means repos can live anywhere on disk. You can also manually clone and symlink a third-party skill repo, and `/update-skills` will include it in future updates.

## Version Safety

Before pulling from any remote, the skill verifies safety using `git merge-base --is-ancestor`:

- **HEAD is ancestor of remote** (exit 0): safe to pull -- remote has new commits
- **HEAD is NOT ancestor** (exit 1): remote is behind or diverged -- skip and warn
- **Fetch fails** (exit 128): remote is unreachable -- skip and continue

When multiple remotes exist (e.g. GitHub + NAS):
- If both are ahead and point to the same commit: pull from either (prefers `origin`)
- If both are ahead but differ: pull from the one furthest ahead
- If remotes have diverged from each other: do not pull, warn user

This prevents accidentally pulling backwards if one remote hasn't been pushed to yet.

## Update Flow

```
1. Discover repos (self-discovery + symlink scan + sources table)
2. For each repo:
   a. Skip if dirty working tree
   b. git fetch --all (tolerate unreachable remotes)
   c. Ancestor check per remote
   d. Pull from safest remote (fast-forward only)
3. Scan for new skill directories
4. Create symlinks for any new skills found
5. Report summary
```

## Symlink Health Check

`/update-skills check` categorizes every symlink:

| State | Meaning | Action |
|-------|---------|--------|
| **Healthy** | Symlink exists, target exists, SKILL.md present | None |
| **Broken** | Symlink target does not exist | Report, offer to remove (with confirmation) |
| **Missing** | Skill directory in repo but no symlink | Report, offer to create |
| **Orphaned** | Symlink points outside any known repo | Report only |
| **Not a symlink** | Regular directory in skills folder | Report only |

## Bootstrapping (New Machine)

To set up skill repos on a fresh machine, clone `core-skills` anywhere you like:

```bash
# 1. Clone core-skills (any directory works)
git clone https://github.com/your-username/core-claude-skills.git /path/to/core-skills

# 2. Create just the update-skills symlink
mkdir -p ~/.claude/skills
ln -s /path/to/core-skills/skills/update-skills ~/.claude/skills/update-skills

# 3. Let update-skills handle the rest
# In a new Claude Code session:
/update-skills update
```

The `update` operation will detect all skill directories in the cloned repo and create the remaining symlinks automatically.

To install additional repos (cloned as siblings next to `core-skills`):

```
/update-skills install generic-design-system-kit
```

## Safety Guarantees

- Never auto-removes symlinks (asks first)
- Never pulls with dirty working tree
- Never pushes to any remote
- Never force-pulls (fast-forward only)
- Never overwrites existing symlinks
- Skips unreachable remotes gracefully (NAS may be offline)
- No destructive git operations
