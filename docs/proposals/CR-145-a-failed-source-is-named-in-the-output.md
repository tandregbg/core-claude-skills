# CR-145 — A failed or missing source is named in the output, and direct messages can be declared

| | |
|---|---|
| **Status** | **Implemented v1.92.5** (2026-10-22) |
| **Contract** | additive — chat entries may be marked `kind: direct`; the agenda header names failed fetches |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`build_agenda.py` source lines, `ops-config` `chats:`), the chat archiver (separate repo) |
| **Related CRs** | CR-047 (the chat archive), CR-087 (recordings), CR-088 (a fetch record says whether it worked), CR-117 (the *Built from* line), CR-140 (pre-flight) |

## What happened

1. **Direct messages were invisible.** An operator sent four one-to-one questions after a meeting, to the
   people who owed the answers. The archive reads only declared group chats, so the replies could not be
   seen by the assistant; the operator had to relay them. The answers were later found, by luck, in the
   project chat where the people had posted them.
2. **A fetch failed for a morning** (*none of 5 repositories could be read*) and the agenda's repository
   section used older data without saying so; only the fetch's own status file knew.
3. **Two recordings of one meeting** existed in the recording store (a notetaker's and the operator's own).
   Nothing in the config says which is the source, so the assistant chose the notetaker's, the one with named
   speakers, and mentioned the other in the raw file's header.

## Proposal

1. **`chats:` entries may be `kind: direct`** with a person, read for replies since a send. It appears in the
   *Built from* line like any chat. The archiver gets the matching option.
2. **A failed fetch is a line in the agenda header**: *repository data is from <time>; the last fetch failed*.
3. **A recording source states its preference** (`prefer: named-speakers`) and a second recording of the
   same meeting is listed in the details file, not silently dropped.
4. **A connected recording store is declared like any source** (`transcripts: store: …`) so the check
   (CR-140) can say *checked* instead of *not checked*, and the close-out step can pull the transcript
   itself. Whether a given project declares it stays the operator's decision.

## Acceptance

- A direct reply since a send appears in the digest source list.
- A failed fetch is visible in the header.
- Two recordings of one meeting are both listed, one marked used.
