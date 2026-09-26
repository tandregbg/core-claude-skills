# CR-093 — Distribute skills as plugins through a marketplace, piloted on a small repo first

| | |
|---|---|
| **Status** | **Phase 1 done 2026-09-26** (pilot observed, test install removed) — phase 2 **Proposed**, awaiting decision |
| **Contract** | none in phase 1. Phase 2 would change every command name (plugin prefix) and is a separate decision |
| **Date** | 2026-09-26 |
| **Area** | installation and updates (`update-skills`, README install section, landing page install page), every hard-coded `~/.claude/skills/<skill>/…` path |
| **Related CRs** | CR-089 (command names kept: `/ops`, `/transcript`, `/preparation`; one-release aliases), CR-078 (documentation belongs to the component that owns the behaviour) |

## What happened

The suite is installed by symlinking each skill directory into `~/.claude/skills/` and updated by
`/update-skills`, a skill in this repo that pulls every discovered repo and repairs the symlinks.
It works, but it is a mechanism this suite maintains itself, and it leaves one step no tool closes:
**a new machine, or a machine that missed a release, has to be brought in line by hand.** The
CR-089 follow-up hit exactly that — two machines were fixed, any third one still needs a pull and a
symlink repair before the command aliases can be removed.

Claude Code now has its own mechanism for this: **plugins, distributed through a marketplace.**
Several are already in use on the maintainer's machines, and one organisation the maintainer works
in runs its own internal marketplace.

## What the platform offers (from the documentation, 2026-09-26)

| | Plugin + marketplace |
|---|---|
| Definition | `.claude-plugin/marketplace.json` lists plugins; each plugin has `.claude-plugin/plugin.json`. One repo can be both |
| Private repos | Supported; HTTPS through the git credential helper |
| Invocation | **Always namespaced: `/<plugin>:<skill>`.** An unprefixed `/ops` reaches a personal skill, not a plugin skill |
| Updates | `claude plugin update <plugin>@<marketplace>`; auto-update per marketplace (off by default for non-official ones) |
| Versioning | `version` in `plugin.json` pins users to it; omitted, the plugin tracks commits |
| On disk | `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`; `${CLAUDE_PLUGIN_ROOT}` resolves to it, including inside skill Markdown |
| New machines | `extraKnownMarketplaces` and `enabledPlugins` in `settings.json` provision them |
| Maintainer loop | load the working copy with `--plugin-dir`, or add the repo as a local-path marketplace (loads in place) |

## What it would cost this suite (phase 2)

1. **Every command gets a prefix.** `/ops` becomes `/<plugin>:ops`. This reverses a CR-089 decision
   and reaches everything that names a command: skills, the contract's `working_loop`, the landing
   page, other tools, and every vault's `CLAUDE.md` files.
2. **About 20 hard-coded `~/.claude/skills/<skill>/…` paths** (mostly in `ops`: its scripts,
   `ops-config/base.yaml`, the substitution list) must become `${CLAUDE_PLUGIN_ROOT}/…`. A skill
   that reads another skill's file needs both to be in one plugin.
3. **`update-skills` loses its main job**, and the install instructions change.
4. **A machine must never have both** — the symlinked copy and the plugin — or every skill exists
   twice under two names.

## Proposal

### Phase 1 — pilot on a small personal skill repository

A private repo with three skills, where a prefix costs almost nothing and no other tool depends on
the command names. Add a marketplace and a plugin manifest; validate; install; observe. Record for
each item below whether it held.

| # | Question | How it is checked |
|---|---|---|
| 1 | Does `claude plugin validate` accept one repo as both marketplace and plugin? | run it |
| 2 | Are the skills in `skills/` discovered without listing them? | `claude plugin details` after install |
| 3 | What are they called — `/<plugin>:<skill>`? | the inventory |
| 4 | Where do the files land? | the cache path |
| 5 | Does a private GitHub source install with the existing credentials? | `marketplace add` from GitHub |
| 6 | What happens beside a symlinked skill of the same name? | both present during the test |
| 7 | Does `${CLAUDE_PLUGIN_ROOT}` resolve inside a SKILL.md? | in a session (manual) |
| 8 | How does an update arrive? | a commit, then `marketplace update` + `plugin update` |

### Phase 2 — decide for this suite

Only after phase 1, and as its own decision: keep symlinks for the maintainer and **add** a
marketplace for other users; or move entirely; or stay. Each option states what it does to the
command names.

## What this does not do

- Change any command name, path or install instruction in this repo.
- Remove `update-skills`.
- Install a plugin permanently on any machine during the pilot.

## Acceptance (phase 1)

- The pilot repo carries a valid marketplace and plugin manifest.
- Each of the eight questions has an observed answer, or says why it could not be observed.
- The test install is removed afterwards, so no machine has two copies.

## Outcome — phase 1 (2026-09-26)

Piloted on a private personal skill repository with three skills, one of them large. The repo
received `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json` (no `version`, so the
plugin tracks commits), was installed from GitHub, observed, updated once, and uninstalled.

| # | Question | Observed |
|---|---|---|
| 1 | One repo as marketplace and plugin | **Yes.** `claude plugin validate` passes; one warning, *no version specified*, which is the intended commit-tracking mode |
| 2 | Skills discovered without listing | **Yes.** All three `skills/<name>/SKILL.md` found with no `skills` key in `plugin.json` (`claude plugin details`: 3 skills, ~250 tokens always-on) |
| 3 | Names | **`/<plugin>:<skill>`** — read from a fresh session's init event |
| 4 | On disk | `~/.claude/plugins/cache/<marketplace>/<plugin>/<12-char commit>/` |
| 5 | Private GitHub source | **Yes**, cloned over SSH with the machine's existing key. `marketplace add` also **writes the marketplace into user settings** |
| 6 | Beside a symlinked skill of the same name | **Both load, silently.** Every skill appears twice, `<skill>` and `<plugin>:<skill>`. No warning, no precedence notice |
| 7 | `${CLAUDE_PLUGIN_ROOT}` in a SKILL.md | **Not observed.** Testing it means writing the variable into a skill the symlinked copy also reads, where it would not resolve. Documented to work; verify in phase 2 on a copy |
| 8 | An update arriving | `claude plugin update <plugin>@<marketplace>` alone fetched the new commit and moved the version (`63db…` → `83e7…`); **it applies after a restart**. The old version stays in the cache |

**Cleanup findings.** `plugin uninstall` and `marketplace remove` leave the version directories in
the cache; they were removed by hand. User settings were left clean by `marketplace remove`.

**What this means for phase 2.**

- The mechanics hold: private source, discovery, update and provisioning are all built in, and would
  close the "a third machine must be fixed by hand" gap for good.
- **The name prefix is the cost, and it is not optional.** Item 6 adds a second one: during any
  transition where a machine has both, every command exists twice. A migration therefore has to be
  one step per machine — remove the symlinks, install the plugin — never both.
- A skill that needs its own files (a script, a style sheet) must reference them through
  `${CLAUDE_PLUGIN_ROOT}`, and that path does not resolve for a symlinked copy. **A skill cannot
  serve both installation modes unchanged** — so "keep symlinks for the maintainer, offer the plugin
  to others" requires either a path that works in both, or a maintainer who also runs the plugin
  (loading the working copy with `--plugin-dir`).

The pilot repository keeps its manifests, and its README documents the plugin route and the
never-both rule. Its active installation is still the symlinks.
