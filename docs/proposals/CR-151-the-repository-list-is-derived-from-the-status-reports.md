# CR-151 — The repository list is derived from the status author's reports, and proposed for confirmation

| | |
|---|---|
| **Status** | **Implemented v1.92.5** (2026-10-22) |
| **Contract** | additive — a helper that proposes a `repos:` declaration; nothing is declared without the operator's confirmation |
| **Date** | 2026-10-21 |
| **Area** | `ops` (a new helper beside `build_agenda.py`; SKILL.md), `ops-config` (`external_systems.repos`) |
| **Related CRs** | CR-055 (the repository metadata archive), CR-116 (report series are declared sources), CR-140 (a pre-flight check), CR-147 (carried lines re-read from their source) |

## What happened

A project declared **one** repository as its source, the portal's own. The agenda, the movement block and the
digest therefore read that repository only. In practice the release the project was working toward depended on at
least seven others: the public site, the proxy, the core API, two microservice repositories, a configuration
repository and the database. The only place that said so was the daily status report written by the person who runs the
release, in a table of backend merges, in the release-branch paragraphs, and in the blocker list.

The operator and an assistant found the gap when a question arose about **whose work was visible**. A count taken on
the declared repository alone showed several people with nothing merged. Over the other repositories the same people
had merged work every week. The first reading had been wrong, and nobody had been told so.

**[E]** Counting repository mentions in twelve consecutive daily reports (1 to 21 October) gave a clear shape in a few
minutes: one repository in every report, two in all but one, then a middle group named on five to eleven days, then
nothing else that was not an ordinary word. The list could have been proposed from the reports rather than from memory.

## Proposal

1. **A helper reads the declared status reports** (CR-116) over a window (default 14 working days) and counts the
   repositories they name: as `owner/repo`, as `repo#number` or `repo PR #number`, and in tables whose first column is
   a repository.
2. **It proposes a `repos:` block**: each repository with the number of days it was named, the number of distinct pull
   requests or issues cited, and a one-line purpose copied from the report's own words. Ordinary words that match a
   repository name (a repository called `scripts`, a word `billing`) are listed separately as *probably prose*.
3. **Nothing is written without a yes.** The operator confirms, removes or adds; the helper then writes the block with a
   comment naming its basis and date. A repository that cannot be read (no access, not found under the organisation)
   is listed as such.
4. **Read scope is conservative.** New entries default to `reads: [pulls, releases]`; issues are added by the operator.
5. **A re-run is a proposal again.** It compares the declared list with the reports and names additions and
   repositories not mentioned for a long time. It never removes an entry itself.
6. **The pre-flight check (CR-140) warns** when a report names a repository on more than N days that the project does not
   declare.

## Acceptance

- Run on twelve daily reports, the helper proposes the repositories named on several days and lists ordinary words
  separately.
- An undeclared repository named on many days produces a warning in the pre-flight.
- No configuration changes unless the operator says yes.

## Not in scope

Reading the work trackers behind those repositories (Jira and the like). That is a separate source, with its own access
question.
