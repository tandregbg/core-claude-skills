# CR-088 — An archive says when it was last fetched, and whether that worked

| | |
|---|---|
| **Status** | **Implemented (unreleased)** — contract 31; version assigned at release |
| **Contract** | additive (30 → 31) — one declared file per archive root, `_fetch.json` |
| **Date** | 2026-09-25 |
| **Area** | `vault_conventions` (archive paths), `ops` (`build_agenda.py` sources block, `/ops brief`), `components:` (messaging client, repo/ticket archivers) |
| **Related CRs** | CR-084 (the agenda states its sources and prints `STALE`), CR-055 (`.githubmeta/`), CR-068 (`.teamschats/`), CR-074 (`.jirameta/`), CR-071 (a missing source must announce itself). Outside this repo: vault-tools **CR-001** (the scheduled runner), marvin **CR-016** (the freshness panel) |

## What happened

The archives the loop depends on — `.teamschats/`, `.githubmeta/`, `.jirameta/` — are about to be
filled on a schedule rather than by hand (vault-tools CR-001). CR-084 already prints each source's
age at the top of an agenda and marks it `STALE` when its newest snapshot is older than the last
note.

That comparison is between two **data** dates. It cannot tell apart three states that call for
three different responses:

| State | Right response |
|---|---|
| Fetched this morning; nothing has happened since the note | none — the source is current and empty |
| Not fetched since last week | run the fetch |
| Fetch failed at 06:30 — login expired | a person must log in; re-running does nothing |

All three print as `STALE — older than the note`. Once fetching is scheduled, the third becomes the
usual way a source goes stale, and it is the one a skill can least guess at, because the archive
looks exactly as it did the day before.

## Proposal

### 1. Declare `_fetch.json` at each archive root

```
<venture>/.teamschats/_fetch.json
<venture>/.githubmeta/_fetch.json
<venture>/.jirameta/_fetch.json
```

```json
{
  "source": "jira",
  "last_attempt": "2026-09-25T06:30:04+02:00",
  "last_success": "2026-09-24T12:30:11+02:00",
  "result": "auth_required",
  "detail": "401 from /rest/api/3/myself",
  "host": "fetch-host",
  "tool": "jirametacli 0.3.1"
}
```

| Field | Rule |
|---|---|
| `result` | `ok` \| `partial` \| `auth_required` \| `error` \| `timeout`. A reader treats an unknown value as `error` |
| `last_success` | kept across failures, so "when was this last true" survives a bad night |
| `detail` | one line, for a person. **Never a token, a URL with a signature, or message content** |
| `host` | which machine wrote it, so a second fetcher shows up as a second host rather than as noise |

**Written by the fetcher, not by the scheduler.** A fetch run by hand records itself exactly as a
scheduled one does, and the file means the same thing whoever started the run. Written atomically
(`.tmp` + rename), like `_summary.yaml`.

**Why at the archive root, not per chat or repo:** one fetch run covers every declared subject in
the venture, and it fails as a whole (the login is per account, not per chat). Per-subject freshness
is already in the snapshot dates CR-084 reads.

### 2. Readable, unlike its folder

The archive folders are dot-folders, excluded from routine reading by rule (CR-034). `_fetch.json`
is declared **readable by any tool**: it holds timestamps and a status, nothing from the source. A
reader opens this one file by name and nothing else in the folder.

### 3. The agenda uses it (CR-084 sources block)

```
Sources — built 260925 07:12 from:
  chat        <series chat>      newest 260924 16:02   read · fetched 07:00 ok
  repo        <org>/<repo>       snapshot 260925       read · fetched 06:00 ok
  tickets     <board>            snapshot 260924       STALE — fetch failed 06:30: login required
```

- `STALE` stays, and gains its **reason** when `_fetch.json` gives one.
- A source whose fetch succeeded after the note, with no newer data, is **current**, not stale.
  That is the first of the three states above, and it stops being a false alarm.
- No `_fetch.json` at all: printed as `fetch not recorded`, never omitted (CR-071). This is also how
  the change rolls out, since existing archives have no file until their fetcher is updated.

`/ops brief` reports any source with `result` other than `ok`, once, at the top.

## What this does not do

- Does not schedule anything. When fetching happens is vault-tools' concern (CR-001).
- Does not declare where attachments or meeting media go. `teams-chat-cli files` writes outside
  the vault by design, and meeting recordings are out of scope.
- Does not make any skill fetch. Skills read archives; they never fill them.

## Acceptance

- `ecosystem.yaml` declares `_fetch.json` under each of the three archive paths, with its writers
  (the three fetchers) and `readers: any`. `contract_version` 31.
- `check-components.py` passes with the fetchers listed as writers.
- An agenda built while Jira's `_fetch.json` says `auth_required` prints the reason on the tickets
  line.
- An agenda built from an archive with no `_fetch.json` prints `fetch not recorded`.

## Outcome (2026-09-25, unreleased)

- `ecosystem.yaml`: `contract_version` 31. `<venture>/.teamschats/_fetch.json`,
  `.githubmeta/_fetch.json` and `.jirameta/_fetch.json` declared, `readers: any tool`, each written by
  its archiver component; the three components and the outbound chat CLI list the record in `writes`.
  The two metadata archivers' `kind` now reads "run on demand or on a schedule".
- `build_agenda.py`: `fetch_record()`, `fetch_status()`, `fetched_since()`. Every archive-backed
  sources line carries its fetch status; `STALE` carries the reason; a source fetched successfully
  since the note is current with no newer snapshot; no record prints `fetch not recorded`. An
  unreadable record is an error, not an absence — on a synced vault a listed file can fail on open.
- `project_brief.py`: `Fetch problems` first, once, for any declared source whose result is not
  `ok`; each archive's fetch status in the Archives block.
- `tests/test_cr088_fetch_record.py`: 10 tests, including the three states end to end.
- Not done here, by design: the fetchers writing the file (their own repositories) and the scheduler.
