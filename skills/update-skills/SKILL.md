---
name: update-skills
description: Manage skill repo updates, symlink health, and installation. Fetches from multiple remotes with version safety, creates symlinks for new skills, audits symlink state.
user-invocable: true
argument-hint: [update|status|check|install <repo>]
---

# /update-skills -- Skill Repository Management

Manage skill repo updates, symlink health, and new skill installation across multiple source repositories and remotes.

Parse the user's argument to determine the operation. Default to `update` if no argument given.

**Standalone skill** -- no dependency on ops-base or ops-config.

**English output only** -- this is a technical utility.

---

## Known Sources

This table identifies repos and their remote URLs. Local paths are discovered dynamically at runtime (see Repo Discovery below).

| Repo | origin | local |
|------|--------|-------|
| `core-skills` | `https://github.com/your-username/core-claude-skills.git` | `ssh://git@nas.local//srv/git/core-skills.git` |
| `acme-skills` | `https://github.com/acme-org/acme-claude-skills.git` | `ssh://git@nas.local//srv/git/acme-skills.git` |
| `bravo-skills` | `https://github.com/bravo-org/bravo-skills.git` | `ssh://git@nas.local//srv/git/bravo-skills.git` |
| `generic-design-system-kit` | `https://github.com/bravo-org/generic-design-system-kit.git` | -- |

---

## Repo Discovery

Repo locations are discovered dynamically -- no hardcoded paths. Three mechanisms combined:

1. **Self-discovery** -- resolve the `update-skills` symlink (`~/.claude/skills/update-skills`) to find where `core-skills` is cloned. The parent of that repo's root becomes the **base directory** for sibling repos (e.g. if `core-skills` lives at `/home/ubuntu/src/core-skills`, the base directory is `/home/ubuntu/src`).
2. **Symlink scanning** -- scan all entries in `~/.claude/skills/`, resolve each symlink to its real path, walk up to find the git root (`git -C <path> rev-parse --show-toplevel`), collect unique git roots. Any repo found this way that is NOT in the sources table is included but noted as "discovered" (no known remotes beyond what git reports).
3. **Sources table** -- provides repo names and remote URLs. Matched against discovered repos by directory basename. Used for `install` (clone URLs) and remote verification.

---

## Version Safety (Commit Graph Ancestor Check)

Before pulling from any remote, verify it is safe using `git merge-base`:

```bash
git -C <repo-path> fetch <remote>
git -C <repo-path> merge-base --is-ancestor HEAD <remote>/<branch>
```

**Interpretation:**
- Exit code 0 (HEAD is ancestor of remote): **safe** -- remote is ahead, fast-forward possible
- Exit code 1 (HEAD is NOT ancestor of remote): **unsafe** -- remote is behind local or has diverged
- Exit code 128 or fetch failure: **unreachable** -- remote is down or not accessible

**Pull logic per repo:**

1. Check for dirty working tree (`git -C <repo-path> status --porcelain`). If dirty: **skip repo entirely**, warn the user.
2. `git -C <repo-path> fetch --all` (continue even if some remotes fail -- note which ones are unreachable)
3. Determine the current branch (`git -C <repo-path> symbolic-ref --short HEAD`)
4. For each remote that has `<remote>/<branch>`:
   a. Run the ancestor check (`git -C <repo-path> merge-base --is-ancestor HEAD <remote>/<branch>`)
   b. If safe: count commits ahead (`git -C <repo-path> rev-list HEAD..<remote>/<branch> --count`)
   c. If unsafe: record as "behind or diverged"
   d. If unreachable: record as "unreachable"
5. **Decision:**
   - If no remote is ahead: "Already up to date"
   - If exactly one remote is ahead: pull from it (`git -C <repo-path> pull <remote> <branch>`)
   - If multiple remotes are ahead and they point to the same commit: pull from any (prefer `origin`)
   - If multiple remotes are ahead but point to different commits: pull from the one that is furthest ahead (most commits ahead of local HEAD)
   - If remotes have diverged from each other (neither is ancestor of the other): **warn the user, do not pull, ask for guidance**
6. After pull: report what happened (commits pulled, from which remote)

---

## Operations

### 1. `update` (default) -- Fetch and pull all repos

**Trigger**: `/update-skills` or `/update-skills update`

**Steps:**

1. **Discover repos** -- self-discovery + symlink scanning + sources table matching
2. **For each repo:**
   a. Verify the local path exists. If not: warn and skip (suggest `install`)
   b. Check for dirty working tree. If dirty: warn and skip
   c. Fetch all remotes
   d. Apply version safety logic (see above)
   e. Pull if safe
3. **Scan for new skills** -- after pulling, compare `skills/*/` directories in each repo against existing symlinks in `~/.claude/skills/`
4. **Create symlinks for new skills** -- for each skill directory that has no corresponding symlink:
   - Show the user what will be created: `~/.claude/skills/<name> -> <repo-path>/skills/<name>`
   - Create the symlink: `ln -s <repo-path>/skills/<name> ~/.claude/skills/<name>`
5. **Report summary:**
   ```
   ## Update Summary

   ### core-skills
   - Pulled 3 commits from origin/main
   - New skill symlinked: update-skills

   ### generic-design-system-kit
   - Already up to date
   - All symlinks present

   ### Symlink Health
   - 10 active, 0 broken, 0 orphaned
   ```

---

### 2. `status` -- Show current state

**Trigger**: `/update-skills status`

**Steps:**

1. **Discover repos**
2. **For each repo, report:**
   - Repo name and local path
   - Current branch and HEAD commit (short hash + message)
   - Version (read from README.md or package.json if available -- look for `**Version:**` pattern)
   - Remotes (name, URL, reachable/unreachable)
   - Skills provided (list of `skills/*/` directories)
   - Working tree status (clean/dirty)
3. **Symlink state:**
   - List all symlinks in `~/.claude/skills/`
   - For each: show target, whether target exists, which repo it belongs to
4. **Format as a structured report:**
   ```
   ## Skill Repository Status

   ### core-skills (v1.5.0)
   Path: <discovered-path>/core-skills
   Branch: main @ a1b2c3d "v1.5.0: Rename to core-skills"
   Tree: clean
   Remotes:
     origin: https://github.com/your-username/core-claude-skills.git
     local:  ssh://git@nas.local//srv/git/core-skills.git
   Skills: ops-base, ops-config, transcript, management-ops, marketing-ops,
           project-ops, bravo-ops, cr, update-skills

   ### generic-design-system-kit
   Path: <discovered-path>/generic-design-system-kit
   Branch: main @ d4e5f6g "Latest commit message"
   Tree: clean
   Remotes:
     origin: https://github.com/bravo-org/generic-design-system-kit.git
   Skills: brand-design-system, brand-webapp-structure

   ### Symlinks (10 active)
   All symlinks valid. No broken or orphaned links.
   ```

   Replace `<discovered-path>` with the actual resolved path at runtime.

---

### 3. `check` -- Verify symlink health

**Trigger**: `/update-skills check`

**Steps:**

1. **Scan `~/.claude/skills/`** -- list all entries
2. **For each entry, check:**
   - Is it a symlink? (vs regular directory)
   - Does the symlink target exist?
   - Does the target contain a skill definition file? (case-insensitive match: `SKILL.md`, `Skill.md`, or `skill.md`)
   - Which repo does it belong to?
3. **Cross-reference with repos** -- for each known repo, check if all `skills/*/` directories have symlinks
4. **Categorize findings:**

   **Healthy:** Symlink exists, target exists, skill definition file present (any casing of `skill.md`)

   **Broken:** Symlink exists but target does not exist (repo moved/deleted?)

   **Missing:** Skill directory exists in repo but no symlink in `~/.claude/skills/`

   **Orphaned:** Symlink in `~/.claude/skills/` points to a path that is not inside any known repo

   **Not a symlink:** Entry in `~/.claude/skills/` is a regular directory (not managed by this system)

5. **Report** (paths shown are the actual resolved paths at runtime):
   ```
   ## Symlink Health Check

   Healthy (10):
     ops-base -> <repo-path>/core-skills/skills/ops-base
     transcript -> <repo-path>/core-skills/skills/transcript
     ...

   Missing (0):
     (none)

   Broken (0):
     (none)

   Orphaned (0):
     (none)
   ```

6. **Offer fixes** -- if any Missing or Broken found:
   - Missing: "Create symlink for <name>?"
   - Broken: "Remove broken symlink <name>?" (ask first -- never auto-remove)

---

### 4. `install <repo>` -- Clone and set up a repo

**Trigger**: `/update-skills install <repo-name-or-url>`

**Steps:**

1. **Determine the base directory:**
   - Resolve the `update-skills` symlink to find the `core-skills` repo root
   - The parent of that root is the base directory (e.g. if `core-skills` is at `/home/user/src/core-skills`, base directory is `/home/user/src`)

2. **Resolve the repo:**
   - If argument matches a repo name in the sources table: use the origin URL, clone target is `<base-dir>/<repo-name>`
   - If argument is a URL: extract repo name from URL, clone target is `<base-dir>/<repo-name>`
   - If argument matches neither: ask the user for the clone URL

3. **Check if already installed:**
   - If the clone target exists and is a git repo: report "Already installed" and run `update` on it instead
   - If the clone target exists but is not a git repo: warn and abort

4. **Clone:**
   ```bash
   git clone <origin-url> <base-dir>/<repo-name>
   ```

5. **Add additional remotes** (if known from sources table):
   ```bash
   git -C <base-dir>/<repo-name> remote add local <local-url>
   ```

6. **Create symlinks** for all skill directories found in the cloned repo:
   - Scan `<base-dir>/<repo-name>/skills/*/` for directories containing a skill definition file (any casing of `skill.md`) or README.md
   - For each, create: `ln -s <base-dir>/<repo-name>/skills/<name> ~/.claude/skills/<name>`
   - If a symlink already exists with that name: warn (name conflict), do not overwrite

7. **Report:**
   ```
   ## Installed: generic-design-system-kit

   Cloned to: <base-dir>/generic-design-system-kit
   Remotes: origin (GitHub)
   Skills symlinked:
     brand-design-system -> ~/.claude/skills/brand-design-system
     brand-webapp-structure -> ~/.claude/skills/brand-webapp-structure
   ```

---

## Safety Rules (always enforced)

1. **Never auto-remove symlinks.** Broken or orphaned symlinks are reported but only removed with explicit user confirmation.
2. **Never pull with dirty working tree.** If `git status --porcelain` returns output, skip the repo and warn.
3. **Never push.** This skill only fetches and pulls. Pushing is the user's responsibility.
4. **Never force-pull.** Only fast-forward merges. If fast-forward is not possible, warn and skip.
5. **Ask before fixing.** When `check` finds issues, present findings and ask before making changes.
6. **Skip unreachable remotes gracefully.** NAS may be offline -- log it, continue with other remotes.
7. **No destructive git operations.** No `reset --hard`, no `clean -f`, no `checkout .`, no `branch -D`.
8. **Symlink conflicts are never overwritten.** If a symlink name already exists, warn and skip.
9. **Always use `git -C <repo-path>`.** Never rely on shell working directory. Every git command must explicitly specify the repo path using the `-C` flag to prevent operating on the wrong repository.
