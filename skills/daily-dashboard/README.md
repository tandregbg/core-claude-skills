# daily-dashboard

Daily meeting and task dashboard generator for Obsidian vaults.

## Usage

```
/daily-dashboard                  # Generic mode, today's date
/daily-dashboard today            # Same as above
/daily-dashboard tomorrow         # Tomorrow's preparations
/daily-dashboard 260219           # Specific date (YYMMDD)
/daily-dashboard acme          # Org mode with Acme config
/daily-dashboard acme 260219   # Org mode + specific date
```

## Two Modes

### Generic Mode (default)

Scans the current working directory recursively for files matching `YYMMDD-*.md`. Categorizes by filename keywords:

- `förberedelse` / `preparation` in filename -> Preparations section
- Everything else -> Meetings/Summaries section

Contact names are extracted from `_contacts/contact-folder/` parent directories.

Works with any vault that uses `_contacts/` folder conventions.

### Org Mode

Pass an org name as the first argument (e.g. `acme`). Loads the org config from `~/.claude/skills/{org}-ops-config/{org}.yaml` and uses project-specific discovery paths, team structure, and persistent symlinks.

## What It Creates

1. **`_Dashboard.md`** -- Mobile-friendly Obsidian file with links to preparations, meetings, and tasks
2. **Symlinks** -- Desktop quick-access links in the vault parent directory:
   - `_PREP-*.md` -- today's preparations (generic + org mode)
   - `_TODAY-*.md` -- today's meetings (generic + org mode)
   - `_MGMT-*`, `_MKT-*`, `_MOBILE-*` -- persistent project symlinks (org mode only)

## Vault Structure

- Generic mode: cwd = vault root, dashboard written to parent directory
- Org mode: vault detected from CLAUDE.md or config, dashboard written to parent directory
