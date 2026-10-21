# CR-150 — The generator never aggregates by person, and a lint keeps team-facing files clean of it

| | |
|---|---|
| **Status** | **Implemented v1.92.4** (2026-10-21) |
| **Contract** | additive — a lint rule and one config key (`metrics_document`); generated output gains no per-person totals |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`build_agenda.py` appendix, digest; `lint`), `ops-config` |
| **Related CRs** | CR-143 (generated text uses the roster), CR-148 (the compact layout), CR-142 (inferences) |

## What happened

A project settled a rule on 21 October: counts of work per person (issues or tickets closed, commits, lines of code,
any comparison of named people on output) belong in **one owner-only document**, never in the files the team reads or
that the person leading the meeting reads aloud. The reasons: the numbers mislead (lines reward volume, closures reward
splitting work, and part of the code is written in agent sessions), and a person leading may be one of the people counted.

Two places can break the rule without anyone meaning to. The agenda's details file **lists the author of every moved
issue and pull request**, which is useful for tracing and needs only one more `GROUP BY` to become a leaderboard. And
status reports the generator *reads* may already carry per-person counts, which a digest could copy.

## Proposal

1. **The generator never emits a per-person total** in any team-facing output: the agenda, the details, the post, the
   recap, the weekly status. The appendix may list the author of each item for traceability, with no count per author.
2. **A digest that reads a source with per-person figures says so**, in one line (*per-person figures present in the
   source, not copied*), and copies none.
3. **`metrics_document:` may be declared in the config** as the owner-only path. It is exempt from the lint, is never
   linked from a team-facing file, and the generator never writes to it.
4. **`lint` flags a team-facing file** that contains a table whose rows are people and whose columns are counts, or a
   line pairing a person with a count of issues, pull requests, commits or lines. The finding names the file and the
   line and does not repeat the figure.
5. **A person's name beside an item** (an owner, an assignee) is not a finding: that is accountability for a task.

## Acceptance

- The details file lists authors without totals, and `lint` passes on it.
- A hand-added table of people against pull-request counts in an agenda makes `lint` fail, naming the line.
- A source report with per-person counts produces the one-line note and no copied figures.

## Not in scope

Collecting the metrics. How a project measures, from which sources, over which windows, is the project's own method
and lives in its owner-only document.
