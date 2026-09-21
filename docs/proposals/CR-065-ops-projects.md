# CR-065: `/ops projects` — which folders are pipelines, and which are just material

| Field | Value |
|-------|-------|
| **CR Number** | CR-065 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-21** |
| **Priority** | Medium |
| **Complexity** | Low — reads what already exists, adds no schema |
| **Estimated Scope** | `skills/ops/SKILL.md` new subcommand, new `skills/ops/list_projects.py` |
| **Related CRs** | CR-061 (`/ops brief`), CR-057 (`carry_forward`), CR-011 (config chain) |
| **Contract** | None |
| **Breaking Changes** | No. Read-only |

---

## Executive Summary

**A folder under `_projects/` may be a running pipeline or a pile of material, and nothing says which.**

Measured on one vault: **24 project-shaped folders, 4 carrying an ops config, 3 with the working loop
wired.** From the outside they are indistinguishable — same depth, same naming, several with a CHANGELOG
and a `meetings/` folder full of transcripts. One is a retired analytics effort with no meetings at all;
another runs a daily standup. Both look like projects.

`/ops projects` lists them by **what is actually wired**, so a session can tell before it starts.

## Motivation

### The registry answers a different question

The vault's project registry is hand-written and authoritative for **intent** — what a person is
driving, with status and sponsor. It is deliberately not derived, and it should stay that way.

**"What am I driving" and "what is wired" are different questions**, and conflating them breaks the
first: a registry that only listed pipeline-ready folders would drop the ideas, the dormant efforts and
the things that are correctly just a CHANGELOG. This command answers the second and **points at the
registry for the first** rather than restating it.

### The cost of guessing

A session opening a folder with `meetings/` and a CHANGELOG reasonably assumes the loop applies, runs
`/ops brief`, and gets a report shaped by defaults that folder never declared. The output is not wrong
so much as **meaningless**, and nothing in it says so.

The opposite error is worse: assuming a folder is *not* wired and hand-writing an agenda beside a
generator that would have produced one.

## What it reports

Folders grouped by how far they are wired, because the grouping *is* the answer:

1. **Loop wired** — `carry_forward` declared. `/ops brief` and `build_agenda.py` work here.
2. **Configured, no loop** — an ops config exists but declares no working loop. `/ops` processes
   meetings; the agenda and carry-forward steps do not apply.
3. **Material only** — no config. A folder of notes, transcripts or documents. **Not a pipeline, and
   that is often correct** — a discussion topic that runs nowhere is a legitimate thing for a vault to
   hold.
4. **Empty or dormant** — no config, no meetings, no changelog movement.

Per row: config present, whether the loop is wired, how many dated meeting files, and **when the record
last moved** — which separates a dormant project from a quiet one better than a file count does.

## What it does not do

- **No judgement about whether a folder should be wired.** It reports the state; whether a pile of
  transcripts deserves a pipeline is a decision for a person.
- **No writes.** No cache, no generated index — the same reasoning as `/ops brief`: an orientation
  artifact that persists can go stale and then lie.
- **Does not replace or regenerate the project registry.** That file carries intent and is hand-written
  by design. This command links to it.

## Verification

1. A vault with folders in all four states groups them correctly.
2. A folder with `carry_forward` appears under *loop wired*.
3. A folder with a config but no `post_processing` appears under *configured, no loop*.
4. Last-movement dates come from the changelog where there is one, the newest meeting file otherwise.
