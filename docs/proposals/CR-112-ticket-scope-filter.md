# CR-112 — A declared ticket board can be narrowed to the project's part of it

| | |
|---|---|
| **Status** | **Proposed** 2026-10-08 |
| **Contract** | additive — one optional key, `external_systems.jira[].scope`, read by `build_agenda.py` and `project_brief.py`; the archiver may honour it too (companion change, ticket archiver) |
| **Date** | 2026-10-08 |
| **Area** | `ops` (`build_agenda.py` `from_jira`, `project_brief.py`), `ops-config/schema.md` · **optional companion change in the ticket archiver** (separate repo) |
| **Related CRs** | CR-054 (`external_systems`), CR-074 (the `.jirameta/` archive), CR-084 (tickets in the sources block), CR-110 (identifier matching uses ticket keys) |

Marks: **[E]** observed in a running series · **[H]** not yet run.

## What happened

A mobile project's tickets live in the organisation's single R&D board. The project's own tickets are the
ones carrying one **component**; the board holds every team's work. The project declared the board so the
agenda could read it, and had to write in a comment: *"the archive will be broader than the project — filter
on component when reading."* Nothing in the skill can do that. **[E]**

Without a filter, the agenda's ticket block, the *Probably closed* evidence and `orient`'s counts all read
the whole department: a backend ticket closed by another team appears as evidence about this project.

The same project's earlier hand queries had to use a substring match on the component field, because the
field is a list and one ticket carried two components; an exact match missed it. **[E]**

## Proposal

### 1. Declare the scope beside the board

```yaml
external_systems:
  jira:
    - key: ABC
      name: The R&D board (mobile part)
      reads: [issues, releases]
      scope:
        components: [mobile-apps]     # any of these; matched against the issue's component list
        exclude_components: [legacy-mobile]   # optional
        labels: []                    # optional, any of these
```

`scope` is a **filter on reading**, applied wherever the archive is read: the sources block counts, the
ticket block, *Probably closed* evidence, `orient`. **Membership is list-contains, never equality** — an
issue with two components is in scope if either is listed.

### 2. The sources block says it is filtered

`tickets  ABC (scoped: component mobile-apps) · 125 of 9,400 · fetched <time> ok` — the reader sees that a
filter applies and how much it removed. An empty result under a scope that matches nothing prints
`scope matched 0 issues — check the component name`, not an empty block.

### 3. Companion: the archiver may archive only the scope

The ticket archiver may read the same `scope` and fetch only matching issues (one JQL clause). Optional —
the read-side filter is what guarantees correctness; archiving less is an economy.

## Verification

1. A project declaring `scope.components: [X]` shows only issues whose component list contains `X`,
   including issues with two components.
2. A closed ticket outside the scope never appears as *Probably closed* evidence.
3. A misspelled component prints the zero-match warning.
