# CR-128 — A raw transcript archived at delivery is adopted, not written again

| | |
|---|---|
| **Status** | **Implemented 2026-10-20** (Unreleased; proposed 2026-10-17) |
| **Contract** | additive, `contract_version` +1. New optional keys on a raw file (`inbox`, `written_by`) and on an inbox item (`raw_transcript`, `dt_filename`, `recorded_at`, `duration_sec`, `language`, `speakers`, `dt_tags`). A vault without them behaves as before |
| **Date** | 2026-10-17 |
| **Area** | `ops-base` (RAW SOURCE ARCHIVE), `transcript`, `inbox`, `ops` (`check`), `docs/schemas/inbox.md` (CR-012) |
| **Related CRs** | CR-085 (the raw archive), CR-012 (the `_inbox/` contract); record-me-macos MAC-CR-011 part 4 (the app writes the raw file at delivery) |

## What happened

The owner, 2026-10-17, after a review of what record-me for Mac writes: the raw transcript should be archived when
it arrives, so that it is "actually handled right" even before, or without, a `/transcript` run. Until now
`.transcripts/<summary stem>-raw.md` exists only once a summary has been filed; a recording nobody files is in
`_inbox/` alone. record-me for Mac (MAC-CR-011) will therefore write the raw file at delivery, in this
contract's shape, with an empty `summary` and `written_by: record-me-mac`. Without this CR, `/transcript` would
then write a second raw file for the same recording.

## Proposal

### 1. The pending raw file (written by a client)

```yaml
---
type: raw-transcript
date: YYMMDD
source: deep-thought
source_id: <document id in the store>
source_file: <capture id>.m4a
duration: <seconds>
variant: diarization_text_named | text
summary:                       # empty: not filed yet
summaries: []
disposition: pending -- archived by <client> at delivery; ...
created_files: []
inbox: _inbox/<capture id>.md
written_by: record-me-mac
---

<verbatim text>
```

Named `<capture id>-raw.md` until it is adopted. The inbox item points at it with `raw_transcript:`.

### 2. RAW SOURCE ARCHIVE adopts it

Before writing a raw file, the archive step looks for one already there: the inbox item's `raw_transcript:`,
else a file in `.transcripts/` with the same `source_id`. When it finds one with an empty `summary`:

- **One recording, one summary:** rename it to `<summary stem>-raw.md` and fill `summary`, `summaries`,
  `disposition` and `created_files`. Keep `written_by` and `source_id`. **The body is never edited**; the
  verbatim rule applies to the adopted text exactly as to text written here.
- **Several recordings in one summary:** the one merged raw file of CR-085 is written with each adopted body
  unchanged under its own separator and metadata line; each adopted file is then removed, only after the merged
  file has been written and its bodies compared byte for byte.
- **A raw file with a filled `summary`** (already adopted): a second summary from the same recording appends
  to `summaries` and `created_files`; nothing is renamed.

### 3. Other keys the inbox item now carries

`/transcript` names the summary from `dt_filename` (the store's suggested name) when the user has not named it,
mapped to the `YYMMDD-summary-<description>.md` convention (its date prefix replaced by the recording's
`YYMMDD`); `recorded_at`, `duration_sec`, `language` and `speakers` fill the summary's header instead of
being re-derived. Missing keys: as today.

### 4. `/ops check`

Reports raw files with `written_by:` and an empty `summary` older than 14 days ("archived, never filed"), with
the inbox item each points to. Report only.

**Read-lock exemption.** A vault may read-lock `.transcripts/` (raw text is read back only on explicit request).
This check is the one named exception: it opens `*-raw.md` by name and reads only the first 64 KiB, the
frontmatter, never the body or the summary text. A vault that keeps the lock should state this exemption
in its own instructions; otherwise run `/ops check --only` with the other checks.

## Acceptance

- A pending raw file plus `/transcript` on its inbox item: one raw file, renamed to the summary stem, fields
  filled, body byte-identical.
- Two pending raw files merged into one summary: one merged file, both originals gone, bodies identical.
- No pending file (a pasted transcript): CR-085 unchanged.
- `/ops check` lists a 20-day-old pending raw file.

## Not in scope

The client side (MAC-CR-011); Deep Thought.

## As built

- `skills/ops-base/raw_archive.py`: `find` (inbox `raw_transcript:`, else `source_id` in `.transcripts/`),
  `adopt_one` (rename + fill, or append for an already adopted file), `adopt_merged` (merged file, bodies
  compared, originals removed last), and an `adopt` CLI. Frontmatter is edited line by line.
- `ops-base` RAW SOURCE ARCHIVE gains "Adopt before you write"; `transcript` Step 2.5 points to it and names the
  summary from `dt_filename`; `docs/schemas/inbox.md` lists the new optional keys.
- `/ops check`: hygiene check `raw` (`hygiene_check.py`), report only, 14 days by the raw file's `date`.
- `ecosystem.yaml` contract 44 to 45 (the CR's own "+1"; numbering remains the maintainer's call).
- Tests: `tests/test_cr128_adopt_raw.py`.
- Review fixes (follow-up commit): merged bodies are compared per slot, byte for byte (empty and substring
  bodies included); a merged file answers `find` for each of its ids (`source_id: a, b`); mixed pending and
  adopted input adopts the pending files and appends the summary to the adopted ones; frontmatter ending at EOF
  and CRLF files are handled (CRLF kept on write); path and summary scalars are YAML-quoted when needed and
  read back unquoted; `summary: ""`, `''`, `null` or a bare comment count as pending in both the adoption and
  `/ops check` (one parser, `raw_archive.get`); the `source_id` match no longer falls back on `external_id`;
  `check_raw` reads the head only and falls back on the file's age when `date` is missing or invalid.
- Not done: the filename mapping from `dt_filename` is prose in `transcript`, not code.
