# CR-157 — When the archiver reads less than the project declared, the source line says so

| | |
|---|---|
| **Status** | **Proposed** (2026-10-22) |
| **Contract** | additive — a comparison between a declared read scope and the archive's recorded one; the source line gets a reason |
| **Date** | 2026-10-22 |
| **Area** | `ops` (`build_agenda.py`: the repository source and its line in the details file), `ops-config` (`external_systems.repos[].reads`) |
| **Related CRs** | CR-055 (the repository metadata archive), CR-088 (a fetch record says whether it worked), CR-117 (the agenda says what it was built from), CR-145 (a failed source is named) |

## What happened

A project declared seven more repositories, each with `reads: [pulls, releases]`. The next morning the agenda's sources
block read `repo: <name>: neither issues nor pulls in declared reads — skipped … NOT READ` for one of them. The message
is wrong in two ways: it says *declared reads*, but the project **had** declared pulls; and it does not say that the
reads which count are the ones the **archiver recorded** for that repository (here: documents only), which come from
the archiver's own configuration, not from the project's.

A project cannot widen what an archiver fetches by editing its own config. Nothing tells the operator that, and a
line that says *skipped* about a repository the operator thinks they enabled reads as a bug in the project.

## Proposal

1. **Compare the project's declared `reads` with the archive's recorded `reads`** for each declared repository.
2. **When the archive reads less, the source line says exactly that**: *the archive reads only <x>; the project asked
   for <y>; the archiver's own configuration decides*. When the archive reads nothing the generator can use, it adds
   which kind is missing (issues or pull requests).
3. **When the archive reads more than declared, the declaration wins** for what the generator uses, and the line is
   silent about the surplus.
4. **The pre-flight check (CR-140) reports the same mismatch** before a build.
5. **The message does not call it an error**: it is a difference to resolve in one of two places.

## Acceptance

- A repository declared with `pulls` whose archive records `docs` only produces the line above, naming both lists.
- A repository whose archive reads what was declared produces no extra line.

## Not in scope

Changing the archiver's configuration from the project. That stays the archiver's.
