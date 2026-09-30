# CR-105 — Incoming material is content, not a meeting

| | |
|---|---|
| **Status** | **Implemented 2026-09-30** |
| **Contract** | additive — one `terms:` entry, one `filename_keywords` key, one `/inbox` classification row; no existing key changes |
| **Date** | 2026-09-30 |
| **Area** | `ecosystem.yaml` (`terms:`), `ops-config/base.yaml`, `/inbox` classification, `/ops process` |
| **Related CRs** | **CR-080** (email and calendar as source types — the larger, still-blocked proposal this carves a piece out of), CR-089 (one term per concept), CR-016 (proper-noun verification), CR-018 (template contracts), CR-012 (inbox schema) |

## What happened

A vendor's weekly SEO report — an automated mail, one sender, no recipients beyond the account
holder — was processed into a project's `meetings/` folder as a meeting summary. It was the
thirty-third such file in that one folder. Reports, audits, newsletters and tracking notifications
had all been filed as meetings, borrowing a declared `meeting_type` whose own config names a
facilitator and a participant list neither of them has.

Nothing looked wrong. The output was good; the analysis was right. **The error is invisible in the
artifact and only shows in aggregate**: the folder that should answer *"what did we meet about?"*
answers with thirty-three events that never happened, and every count, `/ops check` sweep and
orientation pass over that folder inherits it.

## Why `/transcript` and `/ops` both accept it today

CR-080 diagnosed this precisely and is quoted here because the wording is exact:

> An email arrives … There is no skill that takes it. What happens instead is that `/transcript`
> gets used, because it is the skill that turns "something someone said" into a summary in the
> right folder. **That is the wrong instrument, and it is wrong in a way that is easy to miss**
> because the output looks fine.

`/inbox` already detects `email` as a content type in step 1. Its classification table has no row
for it, so **detection leads nowhere** and the item is routed as something else. That missing row
is the whole defect.

## Why this ships and CR-080 does not

CR-080 remains `Proposed`, and its decision 6 is an explicit stop:

> **This is a prerequisite, not a detail.** A raw email is materially more sensitive than a
> transcript … Deciding it by default, in code, is how the wrong answer gets made permanent.

That reasoning holds and is not touched here. **The observation is that the blocked decisions do
not apply to the common case.** CR-080's six decisions concern threads, participant roles, cc
attribution, calendar recurrence and the raw form. A one-way automated report has none of them:

| CR-080 decision | This case |
|---|---|
| 1. Thread as the unit | No thread. One standalone mail |
| 2. Routing per *ärende* | Already resolved — the report names its project |
| 3. `cc` is not a participant | No `cc`, no participants at all |
| 4. What the gate asks | No merge candidate, so nothing to ask |
| 5. Calendar cases | Not a calendar object |
| **6. The raw form** | **Not settled here.** No raw mail is stored; the content file records sender, period and figures, exactly as a pasted report does today |

So this CR takes the part that is unblocked — **a name for the artifact, and somewhere for the
classification to land** — and leaves correspondence between people to CR-080.

## What was added

1. **`terms:` gains `content`** (`ecosystem.yaml`), Swedish `underlag`, file keyword `content`:
   *incoming material the vault received and did not produce: a report, a newsletter, an automated
   digest. Not a meeting — it has a sender, not participants, and no facilitator.*
2. **`filename_keywords.content`** in `strings` and `strings_sv` (`ops-config/base.yaml`), so the
   role keyword is machine-readable in both languages per CR-089.
3. **One `/inbox` classification row**: sender header, no dialogue → `content` → `/ops process`,
   with a note distinguishing it from `transcript` and deferring true correspondence to CR-080.
4. **`/ops process` documents the content variant**: filename, header, action-table ownership, and
   that it does **not** go in `meetings/`.

## The rule that carries the weight

**A summary records an occurrence; content records something received.** The test is not the
channel but the shape: a transcript arrives having *lost* structure and the pipeline recovers it
(who spoke, how a name is spelled). Incoming material arrives *with* its structure — a sender in a
header, a period, figures — and the pipeline's job is to add the reading and the actions.

Two consequences follow, and both are load-bearing:

- **No participant machinery runs.** No diarisation recovery, no ASR near-miss check against folder
  precedent, no owner downgraded to `?`. The sender is correct as given. CR-016 still applies to
  names *inside* the content.
- **Every action owner is ours.** The sender owns nothing; they will never read the file. A row
  owned by the sender is a routing error.

## Scope / non-goals

- **Does not replace or pre-empt CR-080.** Correspondence between people — threads, replies, cc
  attribution, the raw form — is untouched and still blocked on decision 6.
- **Does not store raw mail.** Nothing new is retained, so no sealed surface is needed and no
  existing surface changes meaning.
- **Does not rename existing files.** Forward only, per CR-089. The thirty-three files already in
  `meetings/` stay where they are and are still read; new material lands correctly.
- **Does not add a vault-wide folder.** Placement follows the project's declared `verticals:` path,
  or a sibling folder. A source type is not a place.
- **The folder is not necessarily called `content/`.** Found during the first application: the
  marketing project already has `ops/content/`, meaning *material we produce* — the opposite of
  material we received. The term names the artifact, not the folder; where the name is taken,
  `reports/` is the fallback. A collision would have been worse than the original defect.

## Evidence

The prompting case is a Semrush Position Tracking weekly mail, 2026-09-30, filed in a marketing
project's `meetings/` alongside thirty-two other non-meetings. The first file written under this
CR is the same report, re-filed as content.
