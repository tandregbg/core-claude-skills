# CR-038: Generated-view isolation and system-file language

| Field | Value |
|-------|-------|
| **CR Number** | CR-038 |
| **Date** | 2026-09-08 |
| **Author** | User + Claude Code |
| **Status** | Implemented |
| **Implementation Date** | 2026-09-08 (v1.36.1) |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `ecosystem.yaml` `vault_conventions`, `preparation` skill |
| **Related CRs** | CR-027 (`.knowledge/`), CR-033 (`.handoff/` skip-lists), CR-034 (prefix conventions), CR-035 (generated views), CR-036 (placement classes) |
| **Depends On** | CR-034, CR-036 |
| **Breaking Changes** | No |

---

## Executive Summary

Two rules, both discovered by trying to place one new file.

**1. A generated read view that lives among its own sources needs structural
isolation, not a flag.** The obvious placement for a per-folder situational view was
`<folder>/_status.md` — underscore, because the user reads it. That satisfies CR-034 but
creates a circularity: `.md` files in contact and meeting folders are scanned by several
skills, so a generated view can be read back as source material and synthesised into a
view of itself.

The first fix considered was a `skip_scan:` flag. **CR-033 already proved that fails** —
four skills reached `.handoff/` despite an explicit skip-list, because they globbed on the
`YYMMDD-` filename prefix rather than consulting the list. A per-folder markdown file
sitting among meeting documents is *easier* to hit by accident than one in a dot-folder.

`.knowledge/wiki/` solved the same problem structurally: a hidden folder no scanner walks
into. Applied at folder scope that gives **`<folder>/.status/current.md`**.

**The dot here does not mean rarely read.** The user opens it deliberately. It means
*unreachable by scanners* — a third meaning the prefix carries, distinct from both dormant
and blocked.

**2. System files carry English names.** Content stays in the working language; the
filename does not. Four files created the previous day broke this without a rule existing
to break — they were named in Swedish because the content was.

---

## Proposed Changes

### 1. `generated_view_isolation` (level: rule)

A generated read view among its own sources goes in a hidden subfolder, not beside them.
Naming that repeats what the path already states (`status-<contact>.md` inside
`<contact>/.status/`) is rejected: the path is the identity, and a name embedding the
folder name breaks when the folder is renamed — which happens, as when a person's meeting
series moves between organisational axes.

### 2. `system_file_language` (level: rule)

English names for system and structure files. **Forward-looking**, with two declared
exceptions:

- **Derived registers with Swedish names** are read by scripts; renaming costs more than
  the consistency gains.
- **Generated wiki articles** keep the language of the corpus they summarise.

### 3. Renames applied

| Before | After |
|---|---|
| `_config/prioritering.md` | `_config/priority.md` |
| `_config/namnkonvention-prefix.md` | `_config/naming-prefix.md` |
| `_inbox/_ram.md` | `_inbox/_frame.md` |

Twenty files updated, zero broken links. One over-reach corrected: the bulk rename also
renamed the generated wiki article, which falls under the second exception.

### 4. Overview table in preparation documents

Separately observed: a preparation document had reached **337 lines across ten numbered
sections**, each already carrying a role tag (`[DECISION]`, `[MUST RESOLVE TODAY]`,
`[IF TIME ALLOWS]`). The structure was sound; it was not **surveyable** — finding what had
to close that day meant paging through the whole file.

The fix is not a summary and not a second file: a **table of what already exists**, one row
per section, ordered by urgency rather than by number, placed first in the document. A
separate condensed file would be a second source of truth about the same meeting.

**Recommend this become a mandatory opening section in the `preparation` skill** rather
than an ad-hoc addition.

---

## Out of Scope

- Retroactive renaming of the derived Swedish-named registers.
- Making the overview table generated rather than written — the ordering is a judgement
  about urgency, which a generator cannot make.
