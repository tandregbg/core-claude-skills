# CR-084 — The agenda states its sources, checks what it carries, and hands the track on

| | |
|---|---|
| **Status** | **Implemented 2026-09-24, v1.76.0** |
| **Contract** | additive — new optional keys under `people[]` and `carry_forward`; `external_systems.jira` read, not redefined |
| **Date** | 2026-09-24 |
| **Area** | `ops` (`build_agenda.py`, `lint`), `ops-config` schema |
| **Related CRs** | CR-054 (`external_systems`), CR-055 (`.githubmeta/`), CR-057 (carry-forward), CR-058 (pre-meeting retrieval), CR-071 (read every declared source), CR-074 (`.jirameta/`), CR-082 (one way to make an agenda) |

## What happened

One daily series, one morning. The generated agenda was put on screen and the room reacted:

- **Items already done led the agenda.** Three carried items had shipped or moved the previous day —
  a CDN fix deployed, a font fix live in production, offline discussions moved into the issue tracker.
  Each was visible in the repo or the chat. The agenda carried them anyway, because carry-forward is
  never compared with anything.
- **An item one session old sat above the round.** The facilitator's own objection: *one day old should
  not be on top.* The project owner's rule for the top block: *important points that are still open,
  then go around the table.*
- **The track column was empty.** The project asks every person to state their track first. Yesterday's
  note recorded it on every line; today's agenda asked again from blank.
- **The issue-tracker status at the bottom was one line** — the repo snapshot predated the last note —
  and **the ticket system was absent entirely.** The archive for it exists (CR-074); nothing reads it.
- **The round had the wrong people.** A person present at every session had no row; a person absent from
  every session had one. The roster is declared by hand and nothing compared it with who attended.
- **A vault-only identifier led the agenda for four sessions** and was skipped each time, because its
  owner could not resolve it. It existed in the coordination register and nowhere the team works.
- **Nothing on the page said what the agenda was built from**, or how old each input was.

Every one of these reads as correct on the page. That is the failure class: **an agenda that looks
complete and is built from partial or stale inputs.**

## Proposal

### 1. Sources block first

Before the carried items, one line per declared input with its freshness:

```
Sources — built 260924 07:12 from:
  note        260923-daily-standup.md                  read
  chat        <series chat>          newest 260923 10:24   read · 6 messages since the note
  repo        <org>/<repo>           snapshot 260922       STALE — older than the note
  tickets     <board>                —                      NOT DECLARED
```

`STALE` and `NOT DECLARED` are printed, never omitted. A missing source that announces itself is honest;
a silent one looks like an empty result (the CR-071 rule, applied to the whole agenda).

### 2. Status block last — repo and tickets, per track

The appendix becomes **status**, not only *what moved*: open issues and tickets per track, what moved
since the last note, and what has no assignee. Reads `.githubmeta/` (CR-055) and `.jirameta/` (CR-074)
where `external_systems` declares them. **Honour `reads:` as scope**, and say so where a scope is not
declared.

### 3. Check carry-forward against the sources

For each carried item, look for evidence in the chat and repo archives since the last note (closed
issue, merged PR, a message saying *deployed / live / fixed / moved*). Where found, print the item under
**Probably closed — confirm** with the evidence and its source, instead of carrying it. **Never drop it
silently** — a human confirms in the room, and the next note records the close.

### 4. Order by age

- **Top block:** items carried **more than one session**, and any at the escalation threshold.
- **Items raised last session** go into the owner's row in the round, not above it.

### 5. The track is handed on

- `people[].track` — optional, the person's default track, declared in the project config.
- The round's Track column is filled from **yesterday's note first** (the track tag on that person's
  lines), then from `people[].track`, and is marked as *carried* so the room confirms rather than
  re-answers. **`areas` is never used** — areas are not tracks, which is how the column was once filled
  with the wrong thing.

### 6. Roster checked against attendance

`/ops lint` compares `people[]` with the notes' participant lines over the last N sessions and reports:
present every time but not in the roster; in the roster but absent every time (suggest `adjacent: true`).
**Report only** — the roster is the project's to change.

### 7. Carry-forward names only what the team can find

`/ops lint` flags carried items whose only identifier is vault-local (a register id the team does not
use). Every carried line should reference something in an official source — an issue, a ticket, a doc
path in the repo, a chat message, a session — or state the matter in plain words.

## What is skill and what is project

Stated so a second user of the skill can tell what they are configuring and what they are getting:

| Belongs to the **skill** (same for every project) | Belongs to the **project** (its config and templates) |
|---|---|
| Sources block, status block, their order | Which chats, repos and ticket boards are declared |
| Carry-forward check, age ordering, track hand-on | `people[]`, `track`, `adjacent`, `round_columns` |
| Lint checks (roster, vault-only ids, suffix) | Track names and the taxonomy behind them |
| — | Recap and chat-post templates |

`/ops help` and `/ops brief` print this split for the active project, so it is visible rather than
remembered.

## Acceptance

- An agenda whose repo snapshot predates the last note says `STALE` in its first block.
- A carried item with a matching closed issue or *deployed* message appears under *Probably closed —
  confirm*, with its source.
- An item raised last session is in its owner's row, not above the round.
- The Track column is prefilled from yesterday's note and marked as carried.
- A folder declaring a ticket board gets its status at the bottom; one that does not gets `NOT DECLARED`.
- `/ops lint` reports a roster that does not match attendance, and a carried item with only a vault-local
  identifier.

---

## Outcome (2026-09-24, v1.76.0)

All seven land. The sources block prints `STALE` and `NOT DECLARED` rather than omitting them;
`from_jira()` reads the `.jirameta/` archive that CR-074 created and nothing had read since;
`probably_closed()` separates carried items the sources say have moved — **never dropping one**,
because a machine that closes items silently is worse than one that repeats them.

The track column is filled from the previous note's round table first and the declared default
second. **`areas` is no longer read for it at all** — that substitution was the defect, not a
shortcut: an area is what somebody works on, a track is the axis the round runs along.

Two lint checks added as reports, not fixes: a roster that does not match attendance, and a carried
item whose only identifier is vault-local. Both are the project's to change; a skill editing who
belongs in a room is not a lint fix.
