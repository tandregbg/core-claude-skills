# CR-063: a loop step names its command, and `/ops help` renders the declaration

| Field | Value |
|-------|-------|
| **CR Number** | CR-063 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-21** |
| **Priority** | Low |
| **Complexity** | Low |
| **Estimated Scope** | `ecosystem.yaml` `working_loop`, `scripts/check-components.py`, `skills/ops/SKILL.md` help section |
| **Related CRs** | **CR-062** (`working_loop` — extended here), CR-057, CR-058, CR-061, CR-050 (`components:`) |
| **Contract** | Additive optional field on an existing block. No version bump to the contract itself |
| **Breaking Changes** | No |

---

## Executive Summary

CR-062 declared the loop so the README and the landing page could render one source instead of two
hand-written copies. **It stopped one step short of the question a person actually asks:** *which command
do I run.*

A step says what it does — *"the agenda generator"* — and not how to invoke it. So a session wanting to
act on the loop still reads a skill file, and `/ops help`, which promises a "processing flow summary",
would become the **fifth** hand-written description of the same twelve steps.

This adds an optional `command:` to the steps that have one and renders `/ops help` from the declaration
rather than restating it.

## Motivation

### The fifth copy

Before CR-062 the loop lived in the README, `ops/SKILL.md`, and the landing page. CR-062 folded two into
a declaration. `/ops help` is the next candidate to drift, and its own spec already commits it to
describing the flow.

**The cost of a stale copy here is higher than elsewhere**, because a help command is read exactly by
the people who do not already know the answer, and who therefore cannot tell that it is wrong.

### No command is the honest marker for manual

`manual: true` and `why_manual` already exist. Adding `command:` makes the two consistent from the other
direction: **a step with no command is a step a person performs.** The assertion and the evidence sit in
the same record, and the checker can compare them — which is stronger than either alone.

## Changes

### 1. `command:` on steps that have one

Optional, a single string. Absent where the step is a human act or an external tool the vault does not
own.

```yaml
- id: agenda
  phase: before the session
  label: the agenda generator
  command: "python3 ~/.claude/skills/ops/build_agenda.py --dir <project>/meetings"
  consumes: ["<venture>/.teamschats/", "<venture>/.githubmeta/", "the note"]
  produces: ["the agenda"]
```

### 2. The checker holds the two claims against each other

Two new rules in `check-components.py`:

- **A step marked `manual` must not carry a `command`.** If it can be run, it is not manual — and a
  manual step with a command is a contradiction a reader resolves by guessing.
- **A step with neither `command` nor `manual` must say so deliberately** via `external: true`, for the
  archivers and the meeting itself. Otherwise a step with no command silently reads as an unfinished
  feature — the same failure `why_manual` was added to prevent, one field over.

### 3. `/ops help` renders from `working_loop`

Grouped by phase, in declared order. **Each step shows what it consumes and produces**, because the
question after *which command* is always *what does it need and what do I get* — and the declaration
already holds both.

Manual steps show their `why_manual` where a command would be. That single substitution is the most
useful line in the output: it tells a reader that nothing is missing.

## What this does not do

- **No new loop.** It is the same twelve steps; only the rendering and one field are new.
- **No execution.** `/ops help` prints; it never runs a step.
- **No per-project commands.** The declaration carries the generic invocation. Which project it points
  at is the caller's business.

## Verification

1. Every step with `command` runs as written from a project folder.
2. `check-components.py` fails a step that is both `manual` and commanded.
3. `check-components.py` fails a step with neither `command`, `manual` nor `external`.
4. `/ops help` output matches the declaration's order, phases, commands and manual reasons.
