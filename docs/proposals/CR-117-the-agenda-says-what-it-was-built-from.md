# CR-117 — The agenda says what it was built from, first

| | |
|---|---|
| **Status** | **Implemented 2026-10-09** |
| **Contract** | none — card-layout output only; one new line in the sources block |
| **Date** | 2026-10-09 |
| **Area** | `ops` (`build_agenda.py`: the card's first line, the post, the sources block) |
| **Related CRs** | CR-084 (the sources block), CR-107 (the card; sources moved to the details file), CR-114, CR-116 (declared reports) |

## What happened

CR-107 moved the sources block to the details file, so the card no longer said what it rested on. The
operator asked for that note back at the top, by hand, on the second day of the card. **[E]**

## Change

- **The card opens with a *Built from* line:** each declared source with its age in a word (*today*,
  *2d old*, *fetched 08:45*, *9 msgs*), then **Not used or stale**: undeclared sources, unread ones, reports
  two or more days old on a daily series, and a recordings store declared without an archive. A link to the
  details file follows.
- **It is parsed from the sources block,** so the two cannot disagree. A dated history file behind a stable
  `current` report is not listed twice.
- **The post carries a short version** (names only).
- **Recordings are not listed in *Built from*** (v1.89.7): they feed the note, not the agenda.
- **The sources block gains a `record` line** when `external_systems.transcripts` is declared: *archive read*,
  or *declared, no archive — prepare checks the store by hand*.

## Tests

`tests/test_cr117_built_from.py`.
