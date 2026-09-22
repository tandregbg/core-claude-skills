# CR-072: A wired loop that is not a project folder is invisible to the command that lists wired loops

| Field | Value |
|-------|-------|
| **CR Number** | CR-072 |
| **Date** | 2026-09-22 |
| **Author** | User + Claude Code |
| **Status** | **Implemented** in v1.72.0 (2026-09-22) |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `skills/ops/list_projects.py`, the `/ops` SKILL.md `projects` section, `ecosystem.yaml` (contract 24, `ops_config` 1.4) |
| **Related CRs** | CR-065 (`/ops projects`), CR-067 (same silent-misclassification shape), CR-057 (carry-forward), CR-011 (config chain) |
| **Contract** | contract_version 24 |
| **Breaking Changes** | No -- additive declaration; a client on 23 ignores the block |

---

## Executive Summary

`/ops projects` answers one question: **what is wired.** It scans `_projects` and `_products`.

A recurring series does not have to live there. An org-level weekly lives in a meetings tree, and on
the vault this was found on it is the **most** heavily wired loop in the vault -- agenda generated from
the previous note's carry-forward, notes with an enforced `## Carried forward` contract, a recap
staged through the outbox, sixty-eight dated notes, its own changelog, tasks and insights files. It
appears in the listing not at all.

**A command that reports what is wired, and silently omits the most wired thing, is worse than no
command.** Its output is complete-looking. A reader has no way to tell that the scan had a scope.

Three defects, one asked for and two found while fixing it:

| # | Defect | Symptom |
|---|---|---|
| 1 | Scan scope is the two project trees | A series outside them is never examined |
| 2 | `carry_forward` read from the folder's own config only | A series inherits its loop from an ancestor config, so a running loop reads as **no loop** |
| 3 | Notes and last-movement read `<folder>/meetings/` only | A folder holding dated notes **directly** reports zero notes and *never moved* |

Defect 3 was not suspected. It moved three folders out of *empty or dormant* on the test vault, one of
which had been written to **four days earlier** and was reported as having no content at all.

## The declaration

```yaml
series:
  name: <what the series is called>
  cadence: weekly
```

**Declared, never inferred.** The tempting implementation -- treat any folder with an ops config and
dated notes as a series -- classifies every org root as a series, including the vault's own. The
declaration is cheap, is written once, and says a true thing about the folder that nothing else records.

**`cadence` is displayed**, because escalation thresholds are counted in sessions. `escalate_after: 3`
is three weeks on a weekly and three months on a quarterly. The number is unreadable without it, and
this is the same argument CR-057 made when it added `escalate_after_days` beside the session count.

## Why the chain walk is scoped to declared series

Defect 2's obvious fix -- resolve `carry_forward` up the chain for **every** folder -- is wrong, and
tested wrong on the vault before it was written.

An org-level `carry_forward` block is typically written **for one named series**: its `note_suffix`
names that series' filenames. Let sibling project folders inherit it and they are all reported as loop
wired. On the test vault that would have promoted two correctly-classified projects into *loop wired*,
promising an agenda that `build_agenda.py` would never produce for them.

**That is CR-067 in the opposite direction.** CR-067 fixed a disabled block reading as enabled;
this is an inherited block reading as owned. **Over-reporting a loop is the worse error of the two:**
an under-reported loop is found the moment someone runs the agenda command, while an over-reported one
is found when an item has already fallen through the agenda that was never generated.

So the declaration licenses the walk. A folder that says *I am a series* is also saying *my loop
config lives up the chain* -- which is exactly what is true, and exactly what nothing could previously
express.

## Changes

1. **`find_series(root)`** -- collects folders whose ops config carries a top-level `series:` mapping.
   Skips dot-directories and the standard skip set.
2. **`series_chain(d, root)`** -- nearest-wins walk up to the vault root for `post_processing.carry_forward`. Called only for declared series.
3. **`carry_forward_of(cfg)`** -- extracted from `classify`, so the CR-067 absent-vs-declared-without-a-flag rule is stated once and used by both paths.
4. **`classify(d, root)`** -- counts dated notes in `<folder>/meetings/` when it exists and in the folder itself when it does not; carries the series block through for display.
5. **`last_movement(d)`** -- same subfolder-or-folder rule.
6. **Listing** -- series rows are tagged `[series: <cadence>]`. **`wired` must not quietly read as
   `project`:** one is a standing meeting with no end, the other a thing that closes, and the listing is
   read by people deciding what to pick up.

## Measured, before and after

| | Before | After |
|---|---|---|
| Folders scanned | 39 | 40 |
| Loop wired | 3 | 4 |
| Configured, no loop | 2 | 2 (unchanged -- the chain walk did not leak) |
| Material only | 20 | 23 |
| Empty or dormant | 14 | 11 |

The three folders that moved out of *empty or dormant* hold three, one and one dated notes
respectively, plus a README each. None was empty. One had moved four days before the run.

## What this CR does not do

**It does not make a series a project.** The two are different kinds of thing: a project has exit
criteria and an archive with a tombstone; a standing series has neither and should not acquire them to
satisfy a listing. Nothing is moved on disk, no routing rule changes, and no second register is created
beside the one the vault already keeps.

**It does not resolve the config chain for project folders.** That is a real open question -- a
project whose loop is genuinely declared at org level is still misreported -- but it cannot be answered
by inheritance alone, because the org block names its series. It needs the org block to say whether it
is generic or series-specific, which is a separate CR and a separate contract change.
