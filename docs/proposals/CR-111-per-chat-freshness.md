# CR-111 — Per-chat freshness: *quiet* and *not swept* are different answers

| | |
|---|---|
| **Status** | **Proposed** 2026-10-08 |
| **Contract** | additive — one optional field per chat in `<venture>/.teamschats/<chat>/_chat.json` (`last_swept`), read by `build_agenda.py` and `project_brief.py`; the archiver change lives in the chat archiver's own repo |
| **Date** | 2026-10-08 |
| **Area** | `ops` (`build_agenda.py` sources block, `project_brief.py` archive block), `vault_conventions` (`.teamschats/<chat>/_chat.json`) · **companion change in the chat archiver** (separate repo) |
| **Related CRs** | CR-047 (the chat archive), CR-071 (read every declared chat), CR-084 (sources block), CR-088 (fetch record at the archive root — and its stated assumption, *"per-subject freshness is already in the snapshot dates"*) |

Marks: **[E]** observed in a running series · **[H]** not yet run.

## What happened

A project declares three chats. For two weeks every agenda printed, for two of them:

```
chat  <name>   newest — · 0 since the note · fetched 07:30 ok
```

Both chats' `_chat.json` said `last_fetch` was **two weeks earlier**, and both stopped on the same minute.
The owner asked whether everything from the chats had been retrieved; nobody could say from the agenda. **[E]**

Reading the archiver showed why: its sweep lists chats and **skips any chat whose last activity predates the
window** (`--since week`), without touching that chat's record. So a skipped chat keeps an old `last_fetch`
forever, and the archive-root `_fetch.json` (CR-088) says `ok` because the run succeeded. **[E]**

The likely reading is that both chats were simply quiet — but **"quiet" and "not swept" print identically**,
and the second is the one that hides lost messages.

## Cause

CR-088 put the fetch record at the archive root and reasoned that per-chat freshness is in the snapshot
dates. A snapshot date answers *"when was the last message?"*, not *"when did anyone last look?"*. A chat
nobody looked at and a chat nobody wrote in have the same newest snapshot.

## Proposal

### 1. The archiver records every chat it considered (companion change, chat archiver)

On each sweep, for **every** chat it listed — fetched or skipped — write `last_swept` (UTC) into that chat's
`_chat.json`, plus `last_activity` as reported by the platform. A skipped chat gets `last_swept` with no new
messages. A chat that was not listed at all (removed, access lost) gets nothing, and so goes stale visibly.

### 2. The sources block reads per chat (ops)

For each declared chat, print one of three states — never a bare `ok`:

| `_chat.json` says | Printed |
|---|---|
| `last_swept` within the sweep interval, no messages since the note | `quiet · swept <time>` |
| messages since the note | `<n> since the note · swept <time>` |
| `last_swept` older than one day, or absent | `NOT SWEPT since <date>` — and listed under **Fetch problems** in `/ops orient` |

The archive-root `_fetch.json` still decides the global line (a failed login stays the first thing shown).

### 3. Absent field, old archiver

Where `last_swept` is absent (an archiver without this change), print `last fetched <last_fetch>` and the
note `sweep record not available` — never `ok`. The ambiguity is stated, not hidden.

## Verification

1. A declared chat with no messages for two weeks prints `quiet · swept <today>` once the archiver writes
   `last_swept`.
2. A declared chat the account has left prints `NOT SWEPT since <date>` and appears in `orient`'s fetch
   problems.
3. With the old archiver, both chats in finding 1 print `last fetched <date> · sweep record not available`.
