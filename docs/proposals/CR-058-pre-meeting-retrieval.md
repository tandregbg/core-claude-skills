# CR-058: retrieve before the agenda; request the recap rather than producing it

| Field | Value |
|-------|-------|
| **CR Number** | CR-058 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-21** (retrieval). The recap amendment is a proposal |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `skills/ops/SKILL.md` Step 9, `skills/ops/build_agenda.py`. **No new config key** |
| **Related CRs** | **CR-054** (`external_systems`) and **CR-055** (`.githubmeta/`) — both consumed here, **CR-047** (`.teamschats/`), CR-057 (carry-forward) |
| **Contract** | **None.** Consumes contract 16 as it stands. This CR deliberately adds nothing to the schema |
| **Breaking Changes** | No. Retrieval is inert unless a folder declares `external_systems` |

---

## Executive Summary

Two changes with one cause: **the transcript is not the whole record of what happened.**

1. **Retrieve before generating the agenda and facilitator sheet** — the series chat and the declared
   repository hold decisions, links and state changes that were never said out loud, and mostly never
   will be.
2. **The recap is requested, not produced automatically** — a recap assembled from the transcript alone
   is structurally incomplete, and only a human knows whether a given one needs more.

**This CR introduces no configuration.** An earlier draft proposed a `sources:` key; it was withdrawn on
discovering CR-054 had landed the same concept as `external_systems` — committed, contract-bumped and
already declared by both projects. **Two names for one concept is the worse outcome**, and the reasoning
that motivated `sources` (inputs are not post-processing) is already satisfied: `external_systems` is
top-level.

## Motivation

### The evidence

On 2026-09-21 a QA lead posted the agreed browser and device matrix to the series chat at 07:23, with a
link to the wiki page holding it. The standup ran at 10:30. **It is in no transcript**, so it reached
neither the daily note nor the recap — a decision the team had made, invisible to the record.

The same morning, a repo query showed **17 issues had changed state since the previous note**, the day
after that project migrated its bug tracking into GitHub Issues. **Almost none were assigned.** Neither
fact came up in the meeting, and neither would have.

### `chats:` is a retrieval source, not only a send destination

CR-054 declares `chats:` so a dispatcher knows **where to post**. Today that is its only consumer, and
the declaration is read only at send time. **The same declaration answers a second question — where to
look** — and nothing was asking it. A channel a team posts decisions into is an input to the record
whether or not anyone treats it as one.

### Why this is structural rather than an oversight

A meeting record is built from a recording. Everything asynchronous — chat, issues, releases, documents
— is invisible to it by construction. The gap is not that someone forgot to mention something; it is
that **the loop has one input where the work has three.**

### Why the recap must be requested

The recap-artifact proposal generates it as a post-processing step. That is right for the mechanism and
wrong for the trigger. The recap is the one artifact that **leaves the building**: it reaches people who
were not there and who will read it once. Assembled automatically from the narrowest of the three
inputs, it will be confidently incomplete — and **its incompleteness is invisible to its readers**, who
have no transcript to check it against.

**Offer it; say what it would carry; let a human ask.** The same rule already applied to transcript
source selection: where inputs are partial or duplicated, the machine lists and the human chooses.

## Changes

### 1. Retrieval in `build_agenda.py`, reading `external_systems`

Resolved through the normal config chain — `.claude/ops-config.yaml`, then the folder's `_ops.yaml`.

**The chat folder is resolved by platform id, not by name.** `external_systems.chats[].id` is matched
against `_chat.json` in the CR-047 archive. A second hand-written folder name would be a third place for
the same fact to drift.

### 2. Both sources are read from their archive — neither reaches the network

`.teamschats/` (CR-047) and `.githubmeta/` (CR-055) are siblings by design, so the reader treats them as
siblings: **an archiver writes, this reads.** An earlier draft called a client live for issues, which
duplicated the archiver and was asymmetric with how chats were already read. It now reads
`<venture>/.githubmeta/<slug>/`.

Three things follow, and they are the argument for the archive over a live call:

- **An agenda generates with no credential and no connectivity.** The morning it is needed is the worst
  time to discover a token expired.
- **`reads:` is honoured where it is recorded.** The archiver already writes the declared scope into
  `_repo.json`; the reader checks it there. Verified across two projects — one declaring
  `[docs, issues, releases]` returns issues, one declaring `[docs, releases]` returns
  `issues not in declared reads — skipped`. **A skipped source that announces itself is honest; a
  silent one looks like an empty result.**
- **A snapshot is a reading taken at a moment, not an event log** — CR-055 is explicit about this. If
  the newest snapshot predates the last note, the block says *"older than the last note — not
  refreshed"* rather than presenting stale rows as news.

### 3. Best effort, always

A missing client, an unreadable repository, an absent archive each produce one line and the agenda is
still generated. *An agenda that does not appear because a network call failed is worse than one without
its context block.*

### 4. The agenda carries facts; the facilitator sheet turns them into questions

The retrieved block is deliberately flat. An issue that moved with nobody assigned, or a decision taken
in chat that half the room has not seen, becomes a question in the facilitator sheet — which is not
generated, because turning facts into the right question is the facilitator's job.

### 5. Amendment to the recap-artifact proposal

`recap_artifact` should generate **on request**. After the pass, offer the recap and state what it would
carry; do not write it unasked.

> **Numbering note.** That proposal is numbered CR-054 on the branch
> `cr-048-post-meeting-recap-artifact`, which **collides with main's CR-054** (`external_systems`,
> v1.46.0). The branch's CR-054 and CR-055 both need renumbering before merge — CR-059 onward is free.
> Referenced here by title rather than number for that reason.

## What this does not propose

- **No new config key.** Withdrawn in favour of `external_systems`.
- **No write access, and no fetching.** This reads two archives. It does not call a chat platform or a
  code host, open an issue, comment, or send anything. Refreshing the archives is the archivers' job.
- **No commit or PR retrieval.** Issues and chat cover the observed gap; commit lists are noisy.
- **No polling.** Retrieval happens when an agenda is generated, and not otherwise.
- **No change to manifest status after a send.** That stays manual, and deliberately: the click is where
  a human reads the posted message. Settled elsewhere; not reopened here.

## The gap this closes, stated precisely

`external_systems` was committed with one consumer outside the skills — a project panel, and
pre-selecting a chat when sending. **Nothing in `/ops` read it.** This makes `build_agenda.py` the first
skill-side consumer of the declaration, and the first reader of **both** archives it points at, which is
the difference between a declared key and a used one.

## Evidence

First run against a coordination project: **1 chat message** — an agreed test matrix, posted 07:23 the
previous day, in no transcript — and **24 issues** that had changed state, the majority unassigned.
