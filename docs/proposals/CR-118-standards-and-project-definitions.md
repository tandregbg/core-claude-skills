# CR-118 — Company standards and project definitions: two levels, one direction of authority

| | |
|---|---|
| **Status** | **Implemented 2026-10-09** |
| **Contract** | additive — `standards:` (org config), `definitions:` (project config) |
| **Date** | 2026-10-09 |
| **Area** | `ops` (`definitions()` in `build_agenda.py`, `/ops orient`, `process` writing terms, `check`), `ops-config/schema.md` |
| **Related CRs** | CR-107, CR-114 (terms the card uses), CR-089 (terms in the skill's own vocabulary) |

## What happened

In one fortnight a project coined or sharpened about ten working terms (blocker vs dependency, release gap, canary,
current source, the issue lifecycle), while the organisation's standards held an older, partly conflicting set and
a separate list of contested business terms waited for owners. Nothing in the skill knew either level existed, so
a term decided in a project could quietly become a second company definition, and a general term could stay local
forever. **[E]**

## Change

1. **Declared levels.** `standards:` in an org config names the standards folder (its README is the index);
   `definitions:` beside `carry_forward` names the project's own terms file.
2. **Status per project term:** *local* or *proposed upward*, in a table with a *Status* column.
3. **`process` writes terms to the project file, never to the standards.** The first question for a new term is
   whether another product would need it; if so it is *proposed upward* and named in the organisation's open list.
   Promotion is a company decision, recorded where the organisation records decisions.
4. **`/ops orient`** prints both levels, with the project file's counts (local, proposed upward, without a status).
5. **`/ops check`** reports a project term that also appears in the standards without a *narrower than* link, a term
   row without a status, and a *proposed upward* term not named in the open list.

## Tests

`tests/test_cr118_definitions.py`: both levels resolved; only *Status* tables counted; nothing declared said.
