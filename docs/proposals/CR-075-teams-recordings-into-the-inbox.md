# CR-075 — Teams recordings into `_inbox/.audio/`, for processing here

| | |
|---|---|
| **Status** | Proposed |
| **Contract** | no change (25) |
| **Date** | 2026-09-23 |
| **Area** | `teams-chat-cli`, `_inbox/.audio/`, the inbox schema |
| **Related CRs** | **CR-012** (audio/markdown pairing), **CR-024** (`_inbox/.files/`), CR-047 (`.teamschats/`), CR-022 (inbox schema) |

## What this is

Not "add a Graph scope", and not a transcript fetcher. The point is the **media**: a
Teams meeting recording is *source material this vault has no way to reach*, and the
transcript is what the existing skills produce from it.

That direction matters, and not only architecturally. **Teams' own transcript is
lower quality than what the existing transcription route produces** — an assessment from
using both, and the whole reason the media is the thing worth fetching. Taking
Microsoft's transcript would mean importing the worse artefact and discarding the source
that could produce the better one.

So: fetch the recording, put the source in `_inbox/`, and let the existing chain —
capture, pair, process — do what it already does for every other recording. The vault
keeps the raw material and keeps its own transcriber.

## What this is not: a bot in the meeting

Worth stating early, because it is the first thing an administrator will picture and the
picture is wrong.

This **does not attend meetings**. Nothing joins, nothing listens, nothing appears in a
participant list, and no meeting behaves differently because this exists. It reads a
recording **afterwards**, and only if recording was already enabled in that meeting by
the people in it.

Every guard that already governs meeting recordings therefore still applies, untouched:
someone had to turn recording on, everyone present saw the recording banner, and the
tenant's retention policy already governs the file. This reaches an artefact the
organisation deliberately created — it creates nothing and observes nothing new.

That is a materially smaller ask than the "AI notetaker" this superficially resembles,
and the difference is worth making explicitly rather than leaving an administrator to
assume the larger thing.

## Why `_inbox/`, and why nothing new is needed

The destination already exists and already has the right shape:

| | |
|---|---|
| `_inbox/.audio/` | Raw audio, paired by basename with `_inbox/<id>.md` (CR-012). Writers today: Trillian. Readers: Trillian, Deep Thought, the user |
| `_inbox/<id>.md` | The stub that makes it a real inbox item — `type: audio`, `source.audio_path`, `audio_duration_sec`, all already in the schema |
| `.archive/.audio/` | Where it goes after processing, alongside the transcript |

A Teams recording is the **same kind of object from a different capture device**.
Trillian records on a phone; this would record what Teams already recorded. One writer
more, no new path, no new schema field, no contract change.

The dot-folder matters here for a practical reason the schema already states: *audio
bloats sync*. `.audio/` is excluded from Obsidian's pane and easy to exclude from sync,
which is exactly what meeting video needs.

## What it would do

```
teamschatcli recording <chat>       # fetch the meeting's recording
```

writing:

```
_inbox/.audio/260923-webapp-standup.m4a     the media
_inbox/260923-webapp-standup.md             the stub: type: audio, source: teams,
                                            participants, meeting subject, duration
```

Then nothing special happens, which is the point: the existing route produces the
transcript, the same as for any other recording. **The vault's own chain remains the
transcriber.**

### How the file actually gets transcribed — verified, not assumed

Trillian owns the trip from `.audio/` to a transcript: it uploads to Deep Thought, polls
for completion and writes the result back into `_inbox/<id>.md`.

Its *capture* side watches the macOS Voice Memos sandbox, which would be useless here.
But its **retry path does not** — `CaptureRetry.pendingIds()` scans `_inbox/` for stubs
whose frontmatter carries a retryable `dt_job_status`, checks `.audio/<id>.m4a` exists,
and sends those. It is driven by *the stub*, not by where the audio came from.

That is the seam this CR depends on, and it means:

- A correctly written stub plus its `.m4a` is picked up with **no change to Trillian**.
- The stub must carry the fields that path reads — `id`, `created`, and a
  `dt_job_status` in a retryable state — or the file sits in `.audio/` forever,
  archived but never transcribed. **This is the failure mode to test first.**
- `created` must be at or after Trillian's retry watermark, which exists specifically so
  a historical backlog is never swept up. A recording of an older meeting may need the
  watermark considered rather than assumed.

Worth noting: this is the same arrangement `BackfillSync` already handles from the other
direction (a transcript with no local audio). The pairing rule is CR-012's, and both
directions of the pair now have a producer.

## Audio, not video, where the choice exists

Graph exposes a recording's content; where an audio-only rendition is available it should
be preferred. A vault wants the part that transcribes and searches. Video is large,
syncs badly, and answers no question the audio does not — and if only video is offered,
the audio should be extracted locally rather than the video kept.

## Scopes

Tested against a live project chat on 2026-09-23 with the current grant:

| Call | Result today | Needs |
|---|---|---|
| `/me/onlineMeetings` | **403** | `OnlineMeetings.Read` |
| `/me/onlineMeetings/getAllRecordings` | **403** | `OnlineMeetingRecording.Read.All` |
| `/me/onlineMeetings/getAllTranscripts` | **403** | `OnlineMeetingTranscript.Read.All` |
| Download a chat attachment | **401** | `Files.Read` |

`OnlineMeetings.Read` + `OnlineMeetingRecording.Read.All` is the pair this CR needs,
with `OnlineMeetingTranscript.Read.All` as a second, lower-priority request (see below).
Both are **delegated and user-scoped**: `getAllRecordings` under `/me` returns the
signed-in user's own meetings, so `.All` means *all of that user's meetings*, not the
tenant's. The name still reads alarming, an administrator is right to stop at it, and
`docs/ADMIN-NOTE.md` says so plainly rather than smoothing it — papering over that is how
a request gets refused twice.

**`OnlineMeetingTranscript.Read.All` is the backup lane, not the main one.** Teams'
transcript is the lower-quality artefact, so it is never the preferred input — but it is
worth having when the recording is not:

- recording was enabled and the transcript kept, while the recording itself has aged out
  of the tenant's retention window
- the recording is too large or too slow to move, and a rough transcript today beats a
  good one next week
- a transcription run fails and something is needed to work from meanwhile

Requested **second**, and framed that way to whoever grants it: the fallback for when
the source media cannot be had, not the thing the tool runs on. If only one of the two
is granted, `OnlineMeetingRecording.Read.All` is the one that matters — a recording
yields a good transcript, a transcript yields nothing better than itself.

The stub records which lane produced the file, because a reader six months later needs to
know whether they are looking at the good transcript or the fallback:
`source: teams-recording` against `source: teams-transcript`, and a transcript arriving
by the backup lane is marked so nothing silently treats it as equivalent.

`Files.Read` (chat attachments) remains a separate, smaller ask on its own merits.

## The obligation this creates

A meeting recording is the most sensitive material this tool has ever touched. Two
constraints belong in the design rather than in a later incident:

- **Retention.** `.audio/` is "kept indefinitely by default, user-configurable
  retention". For a phone memo that is fine. For a recording of colleagues it deserves a
  deliberate answer, made when this is built rather than when the folder is large.
- **Other people are in it.** A recording is not the user's alone in the way a voice memo
  is. The mitigation is real but partial: recording was already switched on deliberately,
  everyone present saw the banner, and this reads only meetings the user attended. What it
  does not mitigate is *location* — a copy lands outside the systems where the tenant's
  retention decision is enforced, in personal iCloud. That is the real question in this
  CR, and it is not a technical one.

## The larger shape this belongs to

This CR is one link in something bigger, and it is the link where the something-bigger
becomes visible. The chain is: *an organisation with many meetings* → raw material →
Deep Thought → extracted knowledge in the vault → insights and decisions.

The three existing archives are not three storage folders that happen to share a layout;
they are **three channels into one place** — what was said, what shipped, what is
planned. This proposes the fourth and most sensitive: what was said *in the room*, which
is the part that was never written down anywhere.

**Two steps in the middle, and they are not the same step.** The transcription backend
extracts *text from conversation* — audio in, transcript out, one conversation at a time,
knowing nothing about the vault. The skills then do the *judgement*, inside the user's
session, with the contract, the project's config and prior insights in context: what is a
decision, whose task it is, what belongs in a recap.

That boundary is why this CR is shaped as it is. Swap the transcriber and the chain still
works — better or worse text, same processing — which is exactly why Teams' own transcript
can serve as a **backup lane** rather than being a threat. Swap the judgement layer and
there is no chain left, only a pile of transcripts. The media is worth fetching because it
feeds the replaceable step; the irreplaceable step is already here.

That is worth naming because each CR reads reasonably on its own, and the accumulation
does not follow from any one of them. What is emerging is an apparatus that collects an
organisation's working day into a personal knowledge base. That may be exactly right —
it is the point of the vault — but it should be a **decision**, not the sum of reasonable
steps. The private architecture map carries the same note, and the question neither
answers: where is the line between *my working material* and *the organisation's material
that happens to pass through me*?

## Why the answer might be no

If the meetings worth processing are already being captured another way, this buys
convenience rather than capability — a weak reason to hold a permission whose name gets
re-read at every access review, and a weaker one to put colleagues' recorded voices under
personal file sync.

The question to settle first: **which meetings are not already captured, and is a copy in
a personal vault the right place for them?**

## Scope / non-goals

- **No contract change.** `_inbox/.audio/` gains a writer; its path, schema and lifecycle
  are unchanged. `type: audio`, `source.audio_path` and `audio_duration_sec` already
  exist (CR-012, CR-022).
- **Does not transcribe, and does not change Trillian.** Trillian's retry path already
  picks up any stub with retryable status and audio on disk; this writes a stub in that
  shape. If it turns out a change *is* needed there, it belongs in Trillian's own CR
  series, not here.
- **Teams' transcripts are a fallback, not a substitute.** Fetched only when the
  recording cannot be had, marked as such in the stub, and never preferred over a locally
  produced transcript. The tool must not quietly take the easier path when both exist.
- **Does not add scopes to `SCOPES` before consent** — that breaks `login` for everyone
  until granted. Afterwards it is one line plus `teamschatcli login --force`, since a
  cached token still carries the old scopes.
