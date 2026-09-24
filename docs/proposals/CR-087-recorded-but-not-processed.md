# CR-087 — A session that was recorded but never written up

| | |
|---|---|
| **Status** | Proposed |
| **Contract** | additive — one optional key, `external_systems.transcripts` |
| **Date** | 2026-09-24 |
| **Area** | `ops` (`brief`, THE DAILY LOOP step 5), `ops-config` schema |
| **Related CRs** | CR-054 (`external_systems`), CR-061 (`/ops brief`), CR-084 (the agenda states its sources), CR-085 (raw source archive) |

## What happened

Two recurring series met on the same morning. Both were recorded; both recordings reached the
transcript store within minutes. Neither was processed. Hours later, the operator asked whether
anything was left before closing the session — and `/ops brief` reported both loops as healthy:
*newest note yesterday, chain intact, next agenda not generated.*

Every line was true. The one fact that mattered — **a session had happened and left no note** — was
not on the page, because nothing the brief reads knows that a meeting took place. It reads notes,
agendas, archives and the outbox; the recording lives in none of them.

The cost is not the missing note. It is the next agenda: built from the newest note, it silently
skips a session, re-raises what that session closed, and carries none of what it opened.

## Why this is not fixed by processing sooner

Processing stays manual on purpose — a person chooses between duplicate recordings (THE DAILY LOOP,
step 4). This CR does not automate that. It closes the gap *around* the manual step: **the step can
be skipped, and nothing notices.**

## Proposal

### 1. Declare the transcript store

```yaml
external_systems:
  transcripts:
    store: <name of the transcript store>
    match: ["<series name>", "<chat or meeting title>"]   # how a recording is recognised as this series
```

Optional. Where absent, nothing changes and the brief says `transcripts: NOT DECLARED`, per the
CR-084 rule that a missing source announces itself.

### 2. `/ops brief` reports recorded-but-unprocessed sessions

A new line in the **Loop** block:

```
  Loop
    newest note     260923-daily-standup.md  (1d ago)
    recorded        260924 — 2 recordings, NO NOTE        ← process before the next agenda
    next session    260925 — agenda NOT GENERATED
```

- A recording **matches the series** by `match`, and counts when it is **newer than the newest note**.
- Several recordings of one session are listed together, with id, duration and transcript variant —
  **never chosen between**. Choosing stays human.
- Nothing is fetched by the script. The listing comes from the session running the brief, through the
  store's own read tool, or from a store archive where one exists — the same boundary CR-058 draws for
  chats and repos.

### 3. Generating an agenda over an unprocessed session warns first

`build_agenda.py` (and `/ops prepare` in a wired project, CR-082) refuses to build the next agenda
silently when a matching recording is newer than the newest note. It prints the recording and asks for
the note first, or an explicit `--skip-unprocessed` stating that the session is being passed over.
A skipped session is then a decision on the record, not an accident.

## What this does not do

- Choose a recording, or process one.
- Treat every recording as a session — `match` decides, and an unmatched recording is not reported.
- Replace `/ops brief`'s other blocks.

## Acceptance

- With a matching recording newer than the newest note, `/ops brief` prints `recorded … NO NOTE`
  with every candidate recording listed and none chosen.
- `build_agenda.py` in that state stops and names the recording unless `--skip-unprocessed` is given.
- A folder with no `external_systems.transcripts` prints `NOT DECLARED` and behaves as today.
