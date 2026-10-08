# CR-110 — *Probably closed* matches on identifiers, not on shared words

| | |
|---|---|
| **Status** | **Proposed** 2026-10-08 |
| **Contract** | none — behaviour of `probably_closed()` only; no config key, no file shape |
| **Date** | 2026-10-08 |
| **Area** | `ops` (`build_agenda.py` `probably_closed`) |
| **Related CRs** | CR-084 (the carry-forward check against the sources), CR-101 (evidence ordering and counter-evidence), CR-107 (moved *Probably closed* to the appendix and named this CR: *"a stricter matcher … is left for its own CR"*) |

Marks: **[E]** observed in a running series · **[H]** not yet run.

## What happened

1. CR-107 measured **12 of 12** *Probably closed* matches wrong across three agendas: unrelated updates,
   documentation PRs, work merged before the meeting. **[E]**
2. In another project, a carried line naming a block of backend tickets and an API endpoint was listed as
   probably closed on **two consecutive agendas**, both times against the same merged pull request — a
   client fix for a city picker and a sign-up keyboard. A person corrected it by hand both times. **[E]**

## Cause

The matcher counts **shared words of four characters or more** between the carried line and the evidence
string, and accepts two. The evidence string is built as `"<owner>/<repo> PR #<n> merged <title>"`, so it
always contains the **repository name**, and titles in a ticket-tracked team usually open with the
**ticket prefix**. In the observed case the two shared words were the ticket prefix (here a four-letter key) and
`mobile` from the repository name — words every line and every pull request in that project share.

CR-101 fixed *which* evidence wins; it did not fix *what counts as a match*. Ordering cannot rescue a match
that should never have been made.

## Proposal

### 1. Match on identifiers first

Extract identifiers from the carried line and from the evidence:

| Identifier | Pattern |
|---|---|
| Ticket key | `[A-Z][A-Z0-9]+-\d+`, and ranges written `KEY-9343-9348` expanded to each key |
| Issue / PR number | `#\d+` |
| Version | `\d+\.\d+\.\d+` |
| Path or endpoint | a backticked token containing `/` |

**A match requires at least one shared identifier.** Where the carried line has identifiers and none is
shared, there is no match — however many words overlap.

### 2. Words only as a fallback, and without the noise

When the carried line has **no** identifier, fall back to words, excluding:

- tokens of the declared repository names and of the project's folder slug;
- ticket prefixes (the part before `-` in any ticket key seen in the archives);
- a short stop list of process words (`fix`, `merged`, `release`, `update`, `issue`, `follow`, `mobile`,
  `backend`, `app` — extendable in config as `carry_forward.match_stopwords`).

The threshold stays at two shared words.

### 3. Evidence must post-date the note

Evidence dated **before the previous note** is ignored: work merged before the meeting was already known in
the room and cannot have closed an item that meeting carried. CR-107 counted this as one of its failure
classes.

### 4. Say how it matched

The evidence cell names the reason: `id ABC-9346`, `#352`, or `words: picker, keyboard`. A reader sees at
once whether a match rests on an identifier or on vocabulary.

## Verification

Replay the agendas CR-107 measured and the two agendas in finding 2:

1. The backend-ticket line no longer matches the city-picker PR (no shared identifier).
2. A line carrying `#352` matches a merged PR titled `… (#352)` and nothing else.
3. Evidence merged before the previous note never appears.
4. The 12-of-12 set: report how many matches survive and how many of those a person confirms.
