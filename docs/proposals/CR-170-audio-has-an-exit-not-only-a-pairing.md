# CR-170 — Audio has an exit, not only a pairing

| | |
|---|---|
| **Status** | **Implemented v1.94.0** (2026-11-03), contract 48 |
| **Contract** | additive — `audio_transcript_pairing` gains a disposition half; one pointer convention, one check |
| **Date** | 2026-11-03 |
| **Area** | `ecosystem.yaml` (`audio_transcript_pairing`, `vault_conventions`), `inbox` (`survey.py`), `ops` (`check`) |
| **Related CRs** | CR-012 (inbox schema, the pairing), CR-024 (`.ephemeral/`), CR-169 (the drop zones), CR-035 |

## What happened

`audio_transcript_pairing` is an **invariant**, and it is half a rule:

> *"Audio in `_inbox/.audio/<basename>.m4a` and the matching transcript at `_inbox/<basename>.md` are
> paired by basename. Tools that rename one must rename the other."*

It says where audio **is** and says nothing about where it **goes**. The transcript half has a
declared lifecycle — the entry is routed and the file moves to `.archive/`. The audio half has none,
so the folder only ever grows.

**[E] Measured on one vault, 2026-11-03.**

| | |
|---|---|
| `_inbox/.audio/` | **64 files, 1.6 GB** |
| Period | 14 days, never emptied |
| Growth | **~115 MB/day** |
| Files whose transcript was already archived | 15 — the audio stayed behind |

**The cause is a broken chain, and it is not vault-specific.** A watcher copied every memo to a NAS
archive until it was retired on 2026-10-14; the recorder that replaced it captured audio and wrote the
inbox entry, but **nothing took over the exit**. The archive's own filenames date the break: 363 files
named `YYMMDD_HHMMSS` stop exactly on 2026-10-14, and the 69 that arrive after it carry the recorder's
default names in irregular bursts — a person moving them by hand.

**Any suite that swaps a capture tool has this failure available to it**, because the pairing rule is
the only thing the contract says about audio, and a new capture tool satisfies it on day one.

**[E] 27 of the 64 existed only in the vault** — including **8 meeting recordings from a second machine
that had never been in the chain at all.** For those the inbox was not a staging area; it was the only
copy. A sweep written without this rule would have deleted them.

**[E] Raw audio carries no read restriction.** The same vault read-locks `.transcripts/` and
totally locks `.handoff/` — and the source of both sat unprotected in a cloud-synced folder. The
locks are on the derivatives, not on the original.

## The verification method is part of the proposal

Deciding an audio file is safe to remove is a question about **sound**, not about bytes, and the
obvious test gives the wrong answer.

**[E]** Of 64 pairs, 37 already existed in the archive and **none of them was byte-identical**: each
differed in 160–200 bytes, scattered across fragment headers (`mfhd`) and the trailing `moov` atom —
container timestamps and sequence numbers rewritten by whatever last muxed the file. A byte compare
calls every one of them a different recording. A threshold on *how many bytes differ and how near the
end* is worse: it passed on small files and failed on large ones, because the tail is proportional.

**The test that holds is to compare the `mdat` payloads** — walk the ISO-BMFF boxes, concatenate every
`mdat`, hash that. Metadata may differ; the sound may not. On the measured set: **64 of 64 identical**,
and that is what made the removal defensible.

## Proposal

1. **`audio_transcript_pairing` gains a disposition half.** When the entry is routed, the audio leaves
   `<inbox>/.audio/`. Where it goes is declared per vault (`vault_conventions.audio_archive`), and the
   contract declares only that **a destination must exist and the inbox is not it**.

2. **The pointer travels with the file.** The entry keeps `audio_path` pointing at the archived
   location, with the previous path and the move date retained. An archive whose filenames cannot be
   resolved back to a conversation is a heap:

   ```yaml
   audio_path: //host/share/archive/261029-100234.m4a
   audio_path_was: _inbox/.audio/261029-100234.m4a
   audio_archived: '261103'
   ```

   **[E]** On the measured archive, 69 of 495 files carried a recorder's default name
   (`Inspelning 28.m4a`) and were unaddressable; the only thing that could resolve them was the vault's
   own register.

3. **Removal requires a verified counterpart, compared on `mdat`.** No file leaves the vault on a size
   match or a byte compare. A pair that does not verify is reported, never removed.

4. **`check` reports audio whose entry is archived** — the file whose transcript has moved on and whose
   sound stayed behind. That is the countable form of the whole defect.

## What this is not

**Not a retention policy.** How long a vault keeps audio, and whether it keeps it at all, stays the
vault's. The contract says only that the inbox is a doorway for it, as CR-025 says for everything else.

**Not a capture-tool requirement.** The exit may be a tool, a scheduled job or a person — but it is
declared, so its absence is visible. On the measured vault the absence was invisible for five weeks
and cost 1.6 GB in a synced folder.

## Acceptance

- The contract states that routed audio leaves the inbox, and that the destination is declared.
- An entry whose audio has moved carries a resolvable pointer and its previous path.
- `check` lists audio whose entry is already archived.
- The reference verification compares `mdat` payloads; a size or byte comparison is documented as
  insufficient, with the reason.

## As implemented (v1.94.0)

**The verification method shipped as code, not as prose.** `skills/inbox/audio_verify.py` walks the
ISO-BMFF box tree, concatenates every `mdat` payload in order and hashes that; it compares one pair,
or a whole folder against an archive. The method was the part of this CR that decides whether a file
may be deleted, and a method that lives only in a paragraph is one every caller re-implements.

Three decisions taken while writing it, each because the alternative fails quietly:

- **A file with no `mdat` is hashed whole, and the basis is part of the answer.** A WAV or an MP3 has
  no `mdat`; silently hashing a different thing is how a verification stops verifying. A comparison
  whose two sides used different bases never reports verified.
- **A truncated file is read as far as it goes rather than raising.** A partially synced file is
  exactly the case worth reporting, and an exception would have hidden it.
- **The tool reports and never removes.** It prints `[VERIFIED]`, `[DIFFERENT]` or
  `[NO COUNTERPART]`, and says so in its own output. Deciding what leaves the vault stays with the
  operator (CR-103), and 27 of the 64 measured files existed only in the vault.

21 new tests, including the measured situation rebuilt on disk: two files with identical sound and
different container metadata, asserted to be **not byte-identical and still verified**.
