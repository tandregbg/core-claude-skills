# correspondence

**Version:** 1.0.0

Record a two-way thread with a person -- email, chat or message exchange -- as a living document.

> **Note:** This skill is for **threads where someone replied**. One-way incoming material (a
> report, a newsletter, an automated digest) is `content`, handled by `/ops process`. A recording
> is a transcript, handled by `/transcript`.

## Usage

```
/correspondence                       # paste the thread when prompted
/correspondence <path>                # read the thread from a file
```

Paste the thread, or point at a file containing it. The skill proposes a folder and filename,
asks **one** question -- new file or update of an existing one -- and writes.

## The distinguishing test

Not the channel. **Whether anyone replied.**

| | Shape | Skill |
|---|---|---|
| A recording of an event you were in | transcript | `/transcript` |
| A report that arrived and nobody answered | content | `/ops process` |
| A thread where turns alternate | **correspondence** | **this skill** |

## Three rules

1. **No participant list.** A thread has a sender and recipients *per turn*, not a cast.
2. **cc is informed, not engaged** -- and may not own an action item.
3. **The raw mail is not kept.** The record carries sender, recipients, timestamps and substance.
   `.transcripts/` is for transcripts.

## Routing

**The subject of the thread decides the folder, not the sender.** A thread with a supplier about
a project belongs in the project; a thread with the same supplier about terms belongs in their
contact folder.

## Why these rules

See `CR-080` in `docs/proposals/`. Decision 6 -- whether to keep the raw wire form -- was settled
on 2026-10-01 after a three-thread exchange with an external consultant was written to
`.transcripts/` with `type: raw-transcript` by the ordinary route. Nobody chose that; it is what
the pipeline does with input it is handed, and the seal meant for recordings silently widened to
cover private correspondence with a third party.

## Scope

Email, chat and message threads. The **calendar half of CR-080 remains deferred**.
