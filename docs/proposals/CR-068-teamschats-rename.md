# CR-068 — `.chats/` becomes `.teamschats/`

| | |
|---|---|
| **Status** | Implemented v1.69.0 |
| **Contract** | 20 → 21 (**breaking**) |
| **Date** | 2026-09-22 |
| **Related CRs** | **CR-047** (declared `.chats/`), **CR-055** (`.githubmeta/`, its sibling), CR-058 (reads both) |

## The problem

`<venture>/.chats/` was declared by CR-047 when there was one kind of chat. There
are now two: Teams messages, and the Claude Code transcripts under
`~/.claude/projects/`, which everyone also calls chats. A folder named `.chats/`
in a vault does not say which it holds, and the wrong guess is silent — a reader
looking for session transcripts finds Teams JSON and concludes the archive is
broken.

The folder was never generic in the first place. Only `teamschatcli fetch` writes
it, and the objects inside are Graph message payloads. The name claimed a breadth
the content never had.

## The change

`<venture>/.chats/` → `<venture>/.teamschats/`.

This matches `.githubmeta/`, declared by CR-055 as its deliberate sibling: same
layout, and the source named in the folder. Two archives written by two external
CLIs now name their providers the same way.

**`external_systems.chats` is unchanged.** That is a config key naming a *class*
of system, and a venture may declare chats from a provider that is not Teams. The
key stays generic because the concept is; the path is specific because the writer
is. Anything renaming both has misread the change.

## Breaking, and why it was not staged

A client on contract 20 reading `<venture>/.chats/` finds nothing — no error, an
empty archive. That is the worst failure shape, so the alternative was a
transition period with both paths readable.

It was not worth it. Every reader is in this repo or in `~/repos`: the two `/ops`
scripts, `teams-chat-cli`'s `DATA_DIR`, and three documents. All were changed in
the same pass, before anything wrote to the old path again. A compatibility
window for a set of clients you can enumerate is ceremony.

## What changed

| Where | What |
|---|---|
| The vault | `<venture>/.chats/` → `<venture>/.teamschats/` (36 chats, 169 files) |
| `~/.config/teams-graph/config.toml` | `DATA_DIR` |
| `skills/ops/build_agenda.py` | 3 references |
| `skills/ops/project_brief.py` | 2 references |
| `ecosystem.yaml` | 9 path references; the 3 `external_systems.chats` keys untouched |
| `skills/ops/SKILL.md`, `README.md`, CR-058, CR-063, proposals README | prose |
| `marvin/CLAUDE.md`, `vault-tools/ECOSYSTEM.md`, `vault-tools/SETUP.md` | prose |
| `teams-chat-cli/README.md`, `github-meta-cli` docstrings | prose |

Backed up first: `~/Projects/_archive/260922-chats-before-rename.tar.gz`.

**CHANGELOG entries and the historic contract notes keep the old path.** They
record what the folder was called when they were written, and rewriting history
to match the present is how a changelog stops being evidence.

## Verifying

```bash
teamschatcli chats | tail -1          # resolves the new DATA_DIR
grep -rn '\.chats/' ecosystem.yaml    # only external_systems.chats remains
```
