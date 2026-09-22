# CR-074 — `<venture>/.jirameta/`, a third archive in the same shape

| | |
|---|---|
| **Status** | Implemented v1.72.1 |
| **Contract** | 24 → 25 (**additive** — one new declared path) |
| **Date** | 2026-09-22 |
| **Area** | `vault_conventions`, `external_systems`, a new CLI in `vault-tools` |
| **Related CRs** | **CR-055** (`.githubmeta/`, the pattern this follows), CR-047 (`.teamschats/`), CR-054 (`external_systems`), CR-058 (the reader that consumes both), CR-071 (read every declared source) |

## The problem

A project's work is recorded in three places and the vault archives two of them. Teams chats land
in `<venture>/.teamschats/` (CR-047) and repository metadata in `<venture>/.githubmeta/` (CR-055),
so an agenda can be built from what was *said* and what *shipped*. What was **tracked** — the issue
board — is missing, and it is the half that says what is planned rather than what already happened.

The gap shows up as a person reciting ticket status from memory in a standup whose other two inputs
are archived and dated.

## What exists already

Two Jira tools, both predating the archives, both reaching the API directly and writing nothing to
the vault:

| | |
|---|---|
| a Jira CLI + dashboard | JQL for resolved/unresolved, fields `key,summary,status,assignee,priority,created,resolutiondate` |
| a Jira chat tool | a local cache plus a chat interface over it |

They prove the access works and the credentials exist. Neither is the thing this CR asks for: a
**vault archive**, dated, in the shape the other two already use, that `/ops` can read without a
network call.

## The change

Declare `<venture>/.jirameta/`, written by a `jira-meta-cli` in `vault-tools`, laid out exactly as
`.githubmeta/`:

```
<venture>/.jirameta/<project-key>/
    _project.json                  what this folder is: key, name, URL, when first seen
    <project-key>-YYYY-MM-DD.json  the day's raw issue objects
    <project-key>-YYYY-MM-DD.md    the same, rendered for reading
    status.md                      current state, rewritten each fetch
```

Three archives, one shape. A reader that already walks `.githubmeta/` needs no new idea to walk
this, and `project_brief`'s Archives block gains a third line at no structural cost.

**Driven by declaration, not discovery.** A folder names its boards in `_ops.yaml` under
`external_systems.jira`, mirroring `external_systems.repos`:

```yaml
external_systems:
  jira:
    - key: SON
      name: The platform board
      reads: [issues, sprints]
      default: true
```

Nothing is fetched that a folder has not declared, which is what keeps an archive a record of one
project's work rather than a mirror of the tracker.

## Following CR-055's decisions rather than re-deciding them

- **Metadata, never content.** Issue keys, summaries, status, assignee, priority, dates,
  transitions. Not attachments, not full comment threads.
- **`status.md` is rewritten, not accumulated** — issue state is a *reading*, so the current board
  is a snapshot and the dated files are the record. `.teamschats/` has no equivalent because a day's
  messages are a fact, not a reading.
- **Dot-folder**, so every existing dot-prefix filter excludes it by rule rather than by luck.
- **PER_BOUNDARY**, belonging to the venture whose tracker it is.
- **Read-only.** The archiver never transitions an issue or writes a comment. A dispatching surface
  may surface it; nothing derived from it writes back to Jira.

## Authentication, and the one place this differs from CR-055

`github-meta-cli` shells out to `gh` and holds no credential — explicitly "a second credential for
the same account is a second thing to rotate, a second thing to leak."

Jira has no equivalent. Atlassian's CLI is not installed and not a standard tool here, so this needs
an API token: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, as the existing CLI already uses.
That is a real cost and should be stated rather than discovered during setup.

Mitigations: reuse the token that tool already has rather than minting a second; keep it in a
`0600` `.env` outside the vault, the pattern `todoist-task-pipeline` established; document it in
`vault-tools/SETUP.md` beside the others so the answer to "what credentials does this machine hold"
stays one page. A read-scoped token if Atlassian offers one for the account.

## Why a new CLI rather than extending one of the two

The existing CLI is a dashboard with its own database and version line, and the other is a chat
interface over a cache. Adding vault-archive semantics to either couples the archive's lifecycle to
an app's. The archivers are deliberately small, single-purpose and boring, which is why two of them
already share one shape. A third belongs beside them in `vault-tools`, not inside a dashboard.

Worth noting for whoever builds it: the existing retriever's JQL and field list are a working
starting point, and its `.env` holds the token this would reuse. Both tools live outside this repo;
the private architecture map names them.

## Scope / non-goals

- **Additive.** One new declared path and one new `external_systems` key. No existing path, schema
  or reader changes; a folder declaring no Jira board is unaffected.
- Does **not** write to Jira, ever.
- Does not replace either existing tool. They answer live questions interactively; this writes a
  dated record for a reader that must not make network calls.
- Sprint/board modelling is left to the implementation. `reads:` exists so a folder can say
  `issues` without committing the archive to a sprint concept its board may not use.

## Verifying it, when built

```sh
gmc --vault "$VAULT" show          # the sibling, for comparison
jira-meta-cli --vault "$VAULT" show   # declared boards, last fetch, archived days
python3 skills/ops/project_brief.py --dir <project>   # a third Archives line
```


---

## Implementation notes (2026-09-22)

Built as `vault-tools/jira-meta-cli` 0.1.0 and verified against the live tracker, not
only fixtures — a working token was recovered from a host that runs one of the existing
tools. Three things the build found that the proposal did not anticipate:

**The search endpoint this would have used is gone.** `/rest/api/3/search` answers
**410 Gone**; `search/jql` replaces it and pages by token (`nextPageToken`/`isLast`)
rather than by offset with a total. The proposal cited an existing tool's JQL as a
working starting point — that tool is broken against today's API and nobody had noticed,
because it fails only when run. A test pins the new endpoint.

**A capped fetch must say so.** Two real boards held more open issues than the fetch cap
and returned exactly the cap. An archive recording 500 of 900 open issues reads as a
complete board, and every count drawn from it is wrong. Both rendered views now carry
`partial: yes` and the fetch output says `(capped)`.

**`reads: []` is not the same as no `reads:`.** Absent means unspecified, so the default
applies; empty means read nothing. A falsy check collapsed them and fetched issues from a
board that had asked for none.

Thirty tests, no network: `tests/fixtures/board.json` was recorded from a real board and
scrubbed — invented keys and summaries, real structure.
