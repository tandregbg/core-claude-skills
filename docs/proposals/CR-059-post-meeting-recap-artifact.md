# CR-059: `recap_artifact` — the outbound post-meeting digest as a first-class post-processing step

| Field | Value |
|-------|-------|
| **CR Number** | CR-059 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-21, v1.50.0** — with one amendment, below |
| **Implementation Date** | 2026-09-21 |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `ops` skill Step 9, `ops-config/base.yaml`, `ops` Config table |
| **Related CRs** | CR-014 (priorities artifact), CR-006 (summary format), CR-011 (org-config chain), **CR-047** (`outbound_dispatch`), **CR-049** (identifier language), **CR-053** (fields by identifier, status-note) |
| **Contract** | Written against contract_version 15 |
| **Source standard** | An org's `ops/_standards/post-meeting-recap.md` v1.2 (§2b source boundary) -- vault-side, not in this repo |
| **Depends On** | — |
| **Breaking Changes** | No |
| **Renumbered** | Was CR-054 on this branch. **CR-054 and CR-055 were taken on main** by `external_systems` (v1.46.0) and `.githubmeta/` (v1.47.0) while this branch sat unmerged. Renumbered 2026-09-21 to CR-059/CR-060 |

---

## Amendment at implementation: generated on request

The proposal below places the recap in Step 9 beside the priorities artifact, which implies it is
produced after every qualifying meeting. **It is not.** As shipped, the skill **offers** a recap and
states what it would carry, then waits.

The reason is one the proposal itself half-states in §5 without following through. A recap is the only
Step 9 artifact that **leaves the building** — it reaches people who were not in the room and who will
read it once. §5 establishes that its content must be bounded to one transcript; what follows from that,
and is not said, is that the transcript is **the narrowest of the three inputs a project actually has.**
The chat archive and the repo archive hold decisions the room never said aloud — a test matrix agreed in
chat at 07:23 on the morning of 2026-09-21 reached neither the meeting record nor its recap.

So a recap assembled automatically is not merely incomplete; it is **confidently incomplete, and
invisibly so to its readers**, who have no transcript to check it against. Only a human knows whether a
given week's recap needs what the room did not say.

Everything else below is implemented as written. The gate on content (§1) still applies **after** the
request: being asked for a recap does not make one warranted.

---

## Executive Summary

**A documented config key that no skill reads is the same failure as an undocumented habit — it just looks solved.**

A vault-level standard (`ops/_standards/post-meeting-recap.md`, v1.0, 2026-09-17) defines the **post-meeting recap**: the short outbound digest posted to a chat channel or sent as plain-text email so people who were not in the room learn what changed. It was generalised from a per-series template after the same format worked unchanged for a second series.

That standard specifies a config hook, `workflows.post_processing.recap_artifact`, and states the rationale plainly: *"Declared, not remembered. A convention that lives only in someone's habit produces a recap after the meetings they happen to think of."*

**The hook does not exist.** `recap_artifact` appears in no skill file — not `ops/SKILL.md`, not `ops-base/SKILL.md`, not `ops-config/base.yaml`. Step 9 implements `task_import`, `dashboard_refresh`, `priorities_artifact`, `verticals` and `rolling_plans`, and stops there. The key has already been written into one project's ops-config, where it is inert.

**So the standard currently overstates what is wired**, and a second project in the same vault running the same kind of standup has no recap mechanism at all — no `post_processing` block, therefore no priorities artifact either.

This CR implements the missing step, completing a symmetry Step 9 already half-expresses: the **summary** is the archive, the **priorities artifact** is for the people doing the work, and the **recap** is for the people who need to know and were not there.

---

## Motivation

CR-014 established that the comprehensive summary is archive material and that a working team needs a *second*, slimmer artifact. That reasoning was correct and incomplete: it split the internal audience in two and left the external one unserved.

The three audiences, and the question each asks:

| Artifact | Audience | Question | Status |
|---|---|---|---|
| Summary | The record | *What happened, in full?* | Step 3 |
| Priorities artifact | People doing the work | *What do I do next?* | Step 9, CR-014 |
| **Recap** | **People who need to know and were absent** | ***What changed for me?*** | **Not implemented** |

**The recap is not a shortened summary.** It is written for someone who will read it once, was not there, and needs to know what is now different — which is why it leads with whatever most changes the reader's world rather than with what came first in the meeting, and why it ends with a single ask.

The observed failure without it: a cadence change and an ownership change were agreed in a session, the recap was drafted by hand, and it was still sitting unstaged four days later — by which time the first meeting under the new cadence had already happened.

---

## Proposed Changes

### 1. `recap_artifact` — new Step 9 sub-section in `ops/SKILL.md`

Placed after *Generate Post-Meeting Priorities Artifact*, mirroring its shape.

**Trigger:** `workflows.post_processing.recap_artifact.enabled: true`. Default `false`; opt in per project or meeting type.

**Gate — this is the important half.** Unlike the priorities artifact, the recap is **not** produced after every meeting. Generate one only when the meeting produced something an absent reader must act on or know:

- a schedule, ownership or scope change
- a release that landed, or a date that moved
- a finding that changes how the work should be understood
- an ask of the wider team

**Skip otherwise, and say so.** A recap that restates the working list trains people to stop reading recaps, which costs more than the missing recap.

**Output:** stage to `_outbox/YYMMDD-<series>-recap.md`, with a one-line header carrying the format, the classification and where to begin pasting. Do not post; staging is the skill's boundary.

**Shape:** three to five bold-labelled blocks, then one ask. No tables — they break in chat clients and are unreadable in plain-text email. Target thirty seconds.

### 2. Config schema

```yaml
workflows:
  post_processing:
    recap_artifact:
      enabled: false                  # default
      channel: teams                  # the value written to the manifest's channel field
      classification: team-wide       # team-wide | team-only | management-only
      sections: [shipping, what-we-learned, customer-data]
      dashboard_url: null             # appended as the closing line when set
      stage_to: _outbox/<item>/       # folder + _manifest.md, never a loose file
```

`sections` is a **preset, not a constraint** — a menu the generator starts from, which it may depart from when the meeting's content does not fit the labels. Forcing content into a label is worse than inventing one.

### 3. Stage a folder with a manifest -- and name fields by identifier

**The staged artifact is `_outbox/<item>/` containing the recap body and a `_manifest.md`.** A loose `.md` carries no channel, no recipient and no status, so it cannot be routed.

**`outbound_dispatch` (CR-047) already declares what delivers staged material and what it may write.** A dashboard reads `_outbox/`, previews an item and dispatches it through a channel, writing back **`status`, `status-note`, `channel` and `contact` only**. It never authors a manifest, decides what a status means, or archives.

**Name the fields by identifier, not by the label a vault writes them under (CR-049, CR-053).** Identifiers are English; the words a person reads are data in a vocabulary file, and the label keeps its existing spelling. **Most of what a recap needs is already in the schema:**

| Recap needs | Field identifier |
|---|---|
| Which channel | `channel` |
| Who it goes to | `contact`, `recipients` |
| Subject (email) | `subject` |
| Language | `language` |
| Supersedes an earlier staged item | `replaces` |
| Where the source lives | `source` |
| Lifecycle state | `status` |
| What actually happened on send | `status-note` |

**So `recap_artifact` must not define its own channel or recipient vocabulary.** `channel:` in the config selects *which value to write*; it does not create a parallel enumeration. The generator authors the manifest and **never writes `status` or `status-note`** -- those record what the dispatching surface did first-hand.

**This is the specific failure the boundary exists to prevent:** a second schema beside the first, with two implementations to keep in step.

**What remains this CR's business is rendering** -- how the body is written once the channel is known:
- **teams** -- `**bold**` labels and bullets, one message
- **email** -- `UPPERCASE` labels, `- ` bullets never nested, bare links on their own line, no greeting or sign-off

The subject belongs in `subject`, not repeated at the top of the body. **Note the email channel composes a draft and never sends** -- a human presses send -- so an email recap must read as finished at the moment it is staged.

### 4. `classification` is decided before writing, and gates content

Default `team-wide`. Regardless of level, a recap never carries: personnel matters, raw financials, security methods, regulatory-exposure wording, commercial terms under negotiation, or individual criticism.

**A project-assignment change is not a personnel matter** — who owns which workstream is information the team needs. Frame it around the work.

### 5. The source boundary -- the generator's hardest constraint

**Everything in a generated recap must come from the session being processed.** No content from earlier meetings, no carrying-forward of items that never got communicated, however true and however useful.

**This is the constraint most likely to be violated, because two other rules point the other way:**

- The shape rule says *the first block carries whatever most changes the reader's world -- if the cadence changed, that is block one.* That governs **ordering within a session**, not eligibility.
- The craft rule says *reframe, do not just report.* That means **saying what was said more clearly**, not adding what was not said.

A generator reasoning audience-first -- *"what does the absent reader need to know?"* -- answers from its whole context, including previous sessions it has processed. The question is ***"what did THIS meeting produce that the absent need to know?"*** and only then what to lead with.

**Three implementation requirements:**

1. **Bound the content to the transcript being processed.** Prior summaries may inform framing and terminology; they may not supply claims.
2. **An unsent recap does not merge forward.** A recap that missed its window has expired. Either it is staged late carrying its own date, or the still-live parts go out as a **separate notice** -- never folded into the next session's recap, which would make that session appear to have decided things it never discussed.
3. **Verify before staging.** Each claim traces to something said. Oblique references do not count -- *"maybe better on Thursday"* does not establish a cadence.

**This was observed, not theorised.** On 2026-09-21 a hand-written recap led with a cadence change announced four days earlier and an ownership change from the same earlier session, neither mentioned in the meeting being reported. A human caught it on first read. **A generator running unsupervised would repeat it every time, silently** -- which is the strongest argument for encoding the boundary rather than leaving it to judgement.

*Codified in the source standard as §2b (v1.2, 2026-09-21).*

### 6. `ops-config/base.yaml`

Add `recap_artifact.enabled: false` so the key is schema-known and `/ops status` can report it alongside the other post-processing steps.

### 7. `/ops status`

Extend the `post_processing` line to include recap state, e.g.
`post_processing: task_import (enabled), priorities_artifact (enabled), recap_artifact (enabled, teams/team-wide)`.

---

## Out of Scope

- **Posting or sending.** The skill authors the material and the manifest; **a dispatching surface reads `_outbox/` and delivers** (CR-047), writing back `status`, `status-note`, `channel` and `contact` only. The skill never sends and never writes those fields. On the email channel nothing is sent at all -- a draft is composed and a human presses send.
- **The manifest schema.** Field names, status vocabulary and which fields are editable belong to the `/outbox` skill. This CR consumes that schema; it does not extend it.
- **Archiving.** `/outbox archive` moves the folder and sets `Status: arkiverad`. Several steps with judgement calls -- deliberately not automated.
- **Per-recipient personalisation.** One message, one audience, one classification.
- **Retro-fitting existing series.** Enabling is per-project and deliberate.
- **The vault-level standard itself.** `post-meeting-recap.md` is a vault-side document and stays there; this CR implements the mechanism it assumes, and the standard's §9 should be amended to point at the CR until it ships.

---

## Verification

1. A project with `recap_artifact.enabled: true` whose meeting contains a cadence change produces a staged `_outbox/` file with the header, blocks and a single ask.
2. The same project, after a routine status meeting with nothing reaching beyond the room, produces **no** recap and states why.
3. `channel: email` produces UPPERCASE labels, a subject line, no markdown emphasis, and bare links.
4. `/ops status` reports the recap state.
5. A project with no `post_processing` block is unaffected.
6. **Source boundary:** a session that decides nothing new, following a session whose recap was never sent, produces **no recap** -- it does not surface the earlier session's content.
7. **Staged shape:** the output is a folder containing the body and a `_manifest.md` with `status`, `channel` and `contact` populated -- not a loose `.md`.
8. **No second schema:** the generator writes the declared fields by identifier, under the vault's existing labels, and never writes `status` or `status-note`.

---

## Notes

Two projects in one vault motivated this, and they should be enabled differently. One runs a twice-weekly standup with a wide absent audience and wants `teams` / `team-wide`. The other coordinates a focus project whose task ledger is deliberately external -- its ops-config forbids a local `_tasks.yaml` -- which makes the outbound digest *more* load-bearing there, not less: with no local ledger, the recap and the priorities artifact are the only vault-side record of what the session committed to.
