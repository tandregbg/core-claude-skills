# CR-056: staged folders name the subject, not the artifact inside them

| Field | Value |
|-------|-------|
| **CR Number** | CR-056 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-21** — written for the record after a direct edit |
| **Priority** | Low |
| **Complexity** | Low (documentation of an existing rule) |
| **Estimated Scope** | `skills/outbox/SKILL.md` — one new section |
| **Related CRs** | **CR-054** (`recap_artifact`, `stage_to`), CR-055 (`classification`), CR-047 (`outbound_dispatch`), CR-053 (fields by identifier) |
| **Contract** | No contract change — clarifies a documented convention, adds no key and no mechanism |
| **Breaking Changes** | No. Existing folders keep working; the rule applies to new ones |

---

## Executive Summary

**`/outbox` already documented `YYMMDD-<contact-or-project>_<context>/` and never said what `<context>`
means.** Left undefined, four staged items in one vault interpreted it four ways in five days, and one
named its folder after a file it later no longer contained.

This CR adds a *Naming convention for staged folders* section stating the rule, its one exception, and
the reasoning. **It documents; it changes no behaviour and no schema.** Recorded because the edit was
made directly to `SKILL.md` and a direct edit with no CR is how a convention becomes folklore — the
failure this repo's own pipeline exists to prevent.

## Motivation

### What went wrong

Between 16 and 21 September, three projects in one vault staged the same class of artifact — a
post-meeting recap — and produced three shapes:

| Staged as | Problem |
|---|---|
| `260916-team-a-v3-kickoff` | No underscore. Left side names the **project**, so the folder cannot say who it is for |
| `260918-team-a-v3-weekly-status` | Same |
| `260921-team-b_standup-recap` | Correct shape, but the right side names **a file**, not the send |
| `260921-team-c_design-review-recap` | Same |

A fifth, `260916-team-a_kickoff`, held **five files** — a recap, a one-pager, two facilitator
documents and a chat message. Had it been named after its recap, the name would have been wrong for four
of the five. It was not, and that is what made the rule visible.

### Why `<context>` is not self-explanatory

The vault splits cleanly down the middle, and both readings are defensible from the existing text:

| Subject-named | Artifact-named |
|---|---|
| `260916-team-e_topic-with-three-parts` | `260916-group-f_deck-v2` |
| `260918-person-d_review-debrief` | `260915-team-c_preread` |

The skill's own archived-folder examples do both in one table: `260427-acme` *or* `260427-partnership`
(subject) next to `260427-reflektion` (artifact). **A rule that permits both produces both**, and nobody
is at fault for either.

## Proposed Changes

### 1. New section in `skills/outbox/SKILL.md`

Placed immediately before *Naming convention for archived folders*, because the two are a pair — one
governs staging, the other archiving, and the archiving rule already assumes the staged shape.

**The rule.** `YYMMDD-<recipient>_<subject>/` — the underscore splits **who** from **what**.

**The right side names the subject of the send, not the artifact inside it.** A staged item is a
*folder*: it holds a `_manifest.md` and one or more files, and the manifest already enumerates them.
Naming the folder after one of its files is a claim that stops being true the moment a second file
arrives — an attachment, a deck, a second cut for a different audience.

**The exception: when the artifact type *is* the subject.** A board deck sent as a deck, a pre-read sent
as a pre-read — the recipient asked for that thing and nothing else is coming. `_deck-v2` and `_preread`
are legitimate. `_recap` almost never is: a recap is what the file is, not what the send is about.

**The left side names the recipient, not the project.** The project is recoverable from the content and
from the manifest's project field; **who it goes to is the one thing a folder listing cannot otherwise
tell you**, and a listing is how `/outbox list` and every human scanning the directory read it.

### 2. Nothing else

No config key, no schema field, no new behaviour, no contract bump. `/outbox archive` already renames on
the way out and already asks before doing so.

## What this does not propose

- **No migration.** Existing folders are valid; three pre-September recap folders were deliberately left
  alone. Renaming settled history buys nothing and breaks references.
- **No enforcement.** `/ops sweep` could flag a staged folder whose right side matches a filename inside
  it, but a lint for a naming preference is not worth the false positives.
- **No change to archived-folder naming.** That section stands as written.

## Evidence

Applied on 2026-09-21 across three projects at once — six folders, references updated in eight files:

```
260917-team-b_standup-recap  ->  260917-team-b_standup
260921-team-b_standup-recap  ->  260921-team-b_standup
260917-team-a_standup-recap     ->  260917-team-a_standup
260918-team-a_standup-recap     ->  260918-team-a_standup
260921-team-a_standup-recap     ->  260921-team-a_standup
260921-team-c_design-review-recap  ->  260921-team-c_design-review
```

**All three projects were changed together, deliberately.** Each of the four divergences found that day
began the same way: one project adopting a shape the others did not have. Fixing one would have recreated
the condition being fixed.

## A finding adjacent to this CR, for CR-054

While applying it, `its sibling project`'s `recap_artifact.stage_to` was found to read
`_outbox/YYMMDD-team-b-standup-recap.md` — **a loose file**, which the vault standard it cites rules
out explicitly: *"a loose `.md` carries no channel, no recipient and no status — it shows as no status and
cannot be routed."*

A config key pointing at the one shape its own standard forbids, in the only project that declared the
key. **CR-054 should validate `stage_to` as a directory path** — a trailing `/`, or a check at the point
of use — because the value is currently unread by any skill and therefore unchecked by anything. Fixed by
hand in that project; the general case belongs in CR-054.
