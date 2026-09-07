# CR-034: `_` vs `.` prefix conventions and the audit lifecycle

| Field | Value |
|-------|-------|
| **CR Number** | CR-034 |
| **Date** | 2026-09-07 |
| **Author** | User + Claude Code |
| **Status** | Proposed |
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

**The rule is a single distinction:**

| Prefix | Meaning |
|---|---|
| `_` | **Live system surface** — worked in daily, sorts first |
| `.` | **Dormant or blocked surface** — hidden in Finder and Obsidian |

**The test:** *do I open this folder in everyday work?* Yes → `_`. No → `.`

It is not importance. `.handoff/` is highly sensitive; `.knowledge/` is valuable. The
distinction is whether the surface is **live working material or resting**.

**Current problems:**

1. **No canonical rule** — new folders get a prefix by imitation, not by decision. Two
   `_archive` folders existed against 77 `.archive`.
2. **The audit lifecycle is undefined.** An audit document lives in `_inbox` while in use,
   but nothing said where it goes afterwards — so completed audits stayed, becoming a
   second source of truth competing with the triage.
3. **`_inbox` has no ceiling.** CR-025 says "a door, not a dwelling", but no number.
4. **Blocked surfaces are enumerated, not typed.** Skills know `.transcripts` and
   `.handoff` by name; they do not know that *blocked* is a category with rules.

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
    meaning: dormant or blocked surface, hidden from Finder and Obsidian
    dormant: [.archive, .notes, .ephemeral]
    blocked:
      .transcripts: read-block — never read back unattended, never quoted
      .handoff: total block — untouched by ops, insights, lint, sweep
      .knowledge: generated — hand-editing forbidden, owned by /insights synthesize
  rules:
    - archive is always .archive, never _archive
    - a dated post never takes _ — it takes YYMMDD-
    - _ on a file means "this file exists in every folder of this kind"
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
- `_config/namnkonvention-prefix.md` written as vault canon
- Linked from `INDEX.md` and vault `CLAUDE.md`
- `_contacts/<contact>/_archive` renamed to `.archive`
- `_temp/._analys-index.md` (macOS resource file) deleted

**Remaining:** the `ecosystem.yaml` block, the sweep check, and the audit-lifecycle rule
in the `ops` skill.
