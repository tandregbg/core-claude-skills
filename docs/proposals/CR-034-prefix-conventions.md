# CR-034: `_` vs `.` prefix conventions and the audit lifecycle

| Field | Value |
|-------|-------|
| **CR Number** | CR-034 |
| **Date** | 2026-09-07 |
| **Author** | User + Claude Code |
| **Status** | Implemented |
| **Implementation Date** | 2026-09-07 (v1.36.0) |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `ops` skill (sweep check 9), `outbox` skill, `ecosystem.yaml` `vault_conventions:` |
| **Related CRs** | CR-010 (vault file conventions), CR-024 (`.ephemeral`, file drops), CR-025 (single inbox/outbox), CR-032 (canonical source in manifest) |
| **Depends On** | CR-010 |
| **Breaking Changes** | No (documents existing practice; one rename) |

---

## Executive Summary

The vault uses two prefixes consistently — `_` and `.` — but **no document states the
rule.** It was mapped 2026-09-07 from actual structure: 9 `_` folders and 7 `.` folders at
root, **77 `.archive` folders**, 2 269 prefixed files. The convention held; the definition
did not exist.

**The rule answers one question:** *is this surface **read** in everyday work?*
Yes → `_`. No → `.`

It is not importance — `.handoff/` is highly sensitive, `.knowledge/` is valuable. Nor is
it who writes it.

### Two axes, not one

The first draft of this CR conflated them, and its own most-read example broke the rule.
They are independent:

| Axis | Question | Governs |
|---|---|---|
| **Read frequency** | Is it read in everyday work? | **The prefix** |
| **Write ownership** | Human, generated, or mixed? | A declared property |

**`_insights.yaml` settles it.** It is machine-written by `/insights`, yet carries an
underscore — because several skills *read* it automatically. **Generated does not imply
dot.**

### The known exception

**`.knowledge/` would take an underscore under this rule.** It is read frequently and its
`INDEX.md` is the documented first stop for any knowledge question. It keeps the dot for
compatibility: the name is established in CR-027, `INDEX.md`, vault `CLAUDE.md` and every
`[[wiki]]` link, and renaming costs more than the consistency gains.

It is declared as an exception **with its reason stated** rather than hidden behind a rule
it breaks. A contract that names its exception is honest; one that conceals it is not.

**Do not cite `.knowledge/` as precedent** for dot-prefixing a new read surface.

**Current problems:**

1. **No canonical rule** — new folders get a prefix by imitation, not by decision. Two
   `_archive` folders existed against 77 `.archive`. And without a stated rule the
   read/write axes blur: `.knowledge/` took a dot for being *generated*, which is not a
   prefix criterion.
2. **The audit lifecycle is undefined.** An audit document lives in `_inbox` while in use,
   but nothing said where it goes afterwards — so completed audits stayed, becoming a
   second source of truth competing with the triage.
3. **`_inbox` has no ceiling.** CR-025 says "a door, not a dwelling", but no number.
4. **Blocked surfaces are enumerated, not typed.** Skills know `.transcripts` and
   `.handoff` by name; they do not know that *blocked* is a category with rules. And
   `.knowledge/` was miscategorised as blocked — its constraint is write-side, not read-side.

---

## Proposed Changes

### 1. Codify the prefix test in `ecosystem.yaml`

Add to the existing `vault_conventions:` block:

```yaml
prefix_conventions:
  underscore:
    meaning: live system surface, worked in daily
    test: "do I open this in everyday work?"
    folders: [_inbox, _outbox, _contacts, _products, _private, _config,
              _infrastructure, _analytics]
    files: structure-bearers only (_meta.yaml, _manifest.md, _tasks.yaml,
           _insights.yaml, _INDEX-*, _PLAN-*)
  dot:
    meaning: read rarely, on demand, or never
    dormant: [.archive, .notes, .ephemeral]
    blocked:                       # read access itself is constrained
      .transcripts: read-block — never read back unattended, never quoted
      .handoff: total block — never indexed, read only when named
  known_exception:
    .knowledge: read often (INDEX.md is the first stop) so the rule says
                underscore; keeps the dot for compatibility with CR-027.
                NOT blocked — its constraint is write-side.
  write_ownership:                 # separate axis, never a prefix reason
    human: [_inbox/_capture.md, _inbox/_frame.md, _meta.yaml, .handoff]
    generated: [.knowledge/wiki, _INDEX-maskiner.md, _INDEX-koppling.md]
    mixed: [_tasks.yaml, _insights.yaml]
  rules:
    - archive is always .archive, never _archive
    - a dated post never takes _ — it takes YYMMDD-
    - _ on a file means "this file exists in every folder of this kind"
    - generated does not imply dot (see _insights.yaml)
```

### 2. Define the audit lifecycle

**An audit lives in `_inbox` only while in use.** Once its decisions are made and
executed → `_inbox/.archive/`.

Rationale: an audit that stays after execution becomes a second source of truth. Observed
2026-09-07 — a triage audit carried both the user's decisions *and* the original question
list those decisions had already answered, which made the document unreadable.

### 3. `_inbox` ceiling: three files

The working document, one active audit, one active review document. **More than three means
something has taken up residence** — which CR-025 forbids in principle but does not measure.

`/ops sweep` check 9 should warn above three.

### 4. Separate *stale* from *junk*

- **Stale** — was current, now outdated → `.archive` *(never delete)*
- **Junk without destination** → `.ephemeral` *(may die, swept after 14 days)*

These have been conflated. A stale review list is not ephemeral; it is history.

### 5. Type the blocked surfaces

Skills must treat `blocked:` as a category, not a list of names. A new blocked surface
should inherit the behaviour without each skill being patched.

---

## Out of Scope

- `_temp/` versus `.ephemeral/` overlap — 22 items, needs a human decision on whether it
  is working material or junk. Flagged, not resolved.
- `.handoff/_archive` keeps its `_` — the total block means it is not touched, including
  to be renamed. Exception by necessity.

---

## Implementation Notes

**Already done in the reference vault (2026-09-07):**
- `_config/naming-prefix.md` written as vault canon
- Linked from `INDEX.md` and vault `CLAUDE.md`
- `_contacts/<contact>/_archive` renamed to `.archive`
- `_temp/._analys-index.md` (macOS resource file) deleted

**Remaining:** the `ecosystem.yaml` block, the sweep check, and the audit-lifecycle rule
in the `ops` skill.
