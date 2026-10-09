# CR-116 — Report series kept in the vault are declared sources, like repo reports

| | |
|---|---|
| **Status** | **Implemented 2026-10-09** |
| **Contract** | additive — `external_systems.vault_reports` |
| **Date** | 2026-10-09 |
| **Area** | `ops` (`build_movement.py` `vault_reports()`, `build_agenda.py` sources block and card), `ops-config/schema.md` |
| **Related CRs** | CR-114 (repo reports with `current`/`owner`), CR-084 (a missing source announces itself) |

## What happened

A project's agenda baseline was reviewed source by source. Two daily report series that bear directly
on it — kept in the vault, not in the repo — were read by hand on the days someone remembered, and
never on the others. **[E]** The reports declaration (CR-107, CR-114) could only read a repo.

## Change

`external_systems.vault_reports`: `name`, `dir` (relative to the project root, or found walking up),
`pattern` (a dated series), optional `current` (a stable file in that dir), optional `owner`. Read
locally, never fetched. Each appears in the details file's Sources block with the newest file and its
age (or *updated today* / *STALE* for `current`), and on the card's *Status sources* line; `owner`
puts it in that person's round minute — the same handling as repo reports.

A same-day rerun suffix (`YYMMDDb`) sorts as newest. A missing folder prints *NOT FOUND*.

## Tests

`tests/test_cr116_vault_reports.py`: newest of a dated series with its age (a rerun suffix wins),
a missing folder said, the owner carried.
