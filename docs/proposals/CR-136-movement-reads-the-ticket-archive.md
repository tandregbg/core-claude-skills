# CR-136 — The movement block reads the ticket archive, not only a repository

| | |
|---|---|
| **Status** | **Proposed** (2026-10-20) |
| **Contract** | `contract_version` 46 → 47, `ops_config` 1.7 → 1.8 (**additive** — one optional key, `movement.from`; a project that declares nothing behaves exactly as today). Another CR in flight may take 1.8 first; whichever implements first takes it |
| **Date** | 2026-10-20 |
| **Area** | `ops` (`build_movement.py`, the movement block in `build_agenda.py`, `check`), `ops-config` (`schema.md`, `movement.from`), `ecosystem.yaml` (`schemas`) · **a prerequisite change lives in the ticket archiver (separate repo)** |
| **Related CRs** | CR-107 (the movement block and the card), CR-074 (the `.jirameta/` archive), CR-112 (narrowing a declared board to the project's part — **this CR depends on it**), CR-084 (the agenda reads its declared sources), CR-088 (the archive's `_fetch.json` record), CR-114/CR-116/CR-117 (sources, report series, *Built from* and their ages), CR-127 (the ledger's closing day — the same question asked of the vault's own records) |

## What happened

`build_movement.py` (CR-107) answers the two questions a standup card needs — *how many are open* and
*what moved* — by reading a declared repository live and rebuilding history from its issue events. It
works, and it is the only place in the skill set where delivery volume over time exists.

**It has exactly one source: a repository.** A project whose work is tracked in a ticket system gets no
movement block at all. Of three coordination projects running the same daily loop in one vault, one
declares a repository with labels and has the series; the other two track their work in a ticket board
and have nothing — not a thin series, not a stated absence, nothing on the card.

The archive those two would need **already exists and is already read.** CR-074 declared
`<venture>/.jirameta/`, and `from_jira()` in `build_agenda.py` reads it for the agenda's ticket lines.
Its docstring records the same class of bug this CR closes:

> The archive has existed since CR-074 and nothing read it, so a project that tracks its work in a
> ticket system had that half of its status missing from every agenda — silently, because an
> undeclared source and an empty one look identical on the page.

`build_movement.py` contains no reference to the archive. The reader exists, the data exists, and the
one consumer that would turn it into a series does not look.

## What the archive can and cannot answer

Measured on a live archive, 2026-10-20: fourteen daily files, the first from 2026-10-08, each holding
per-issue `created`, `updated`, `resolutiondate`, `status`, `priority`, `labels`, `assignee`, plus a
`changed` list (321 entries that day) and a `truncated` marker.

| Question | Answerable today | Why |
|---|---|---|
| How many are open, per day | **Yes**, over the archived window only | Each day's file is a snapshot; there is no event feed to rebuild earlier days from |
| Open by priority, status, label, assignee | **Yes**, same window | Present per issue in every snapshot |
| What moved since yesterday | **Yes** | The `changed` list, and a diff of two snapshots |
| How much was closed — throughput | **No** | The snapshot holds **only open issues** (`truncated: ["open"]`, 500-issue cap) and **zero issues carry a `resolutiondate`**. Nothing closed is in the archive |
| Inflow before the archive began | **Partly** | `created` reaches back years for issues still open; issues opened and closed before the first archived day are absent entirely |

**So this CR delivers the open-volume series and refuses to invent the rest.** Throughput needs a
change in the archiver — archive resolved issues, and page past the cap — which is a separate repository
and not core-skills' to make. This CR names it as the prerequisite and reports its absence rather than
printing a zero.

## Proposal

### 1. The movement block builds from whatever the project declares

```yaml
workflows:
  post_processing:
    carry_forward:
      movement:
        out: status/movement        # unchanged
        days: 14                    # unchanged
        from: [repo, tickets]       # NEW, optional. Default: whatever is declared
```

Default behaviour with `from` absent: a declared repository carrying `labels:` gives the repository
series, as today; a declared board with no such repository gives the ticket series; both declared gives
both, in that order. **A project that declares neither keeps getting no block** — and that is already
reported by the configuration check, which is where an undeclared source belongs.

### 2. Same output shape, same file names

The ticket series writes the files the repository series writes — `<out>/YYMMDD-issue-movement.md` and
`<out>/snapshots/YYMMDD.json` — so one reader serves both and the day-over-day comparison is unchanged.
A snapshot records its `source` (`repo` or `tickets`) and the board key. Where both sources run, the
snapshot holds one entry per source rather than two files.

The archive is read **locally and never fetched**: the same contract `from_jira()` already honours
(CR-074, CR-084). No network call is added anywhere in this CR.

### 3. Narrowing is CR-112's key, not a new one

A board usually carries far more than one project. The series uses `external_systems.jira[].scope`
(CR-112) to take the project's part of it, and nothing else — **a second filter for the same job is how
two numbers for one project appear.** Where `scope` is absent, the series counts the whole board and
says so in its own line, rather than presenting a board-wide count as the project's.

### 4. Four checks, printed pass or fail — never silent

The repository series prints three checks and this is why it is trustworthy. The ticket series prints
four:

1. **The archive is fresh.** The newest archived day is the agenda's day, else the block says `STALE`
   with the age in days.
2. **The fetch succeeded.** The archive's `_fetch.json` (CR-088) carries `result`; anything other than a
   full success is printed verbatim — `partial (1 of 1 boards hit the issue cap)` reads as a limit, and a
   limit a reader can see is not a defect.
3. **The window is stated.** The series says which day it starts from and that nothing before it exists.
   A chart that begins on an arbitrary Thursday must say why.
4. **Throughput is unavailable, by name.** While the archive holds no closed issues, the outflow line
   reads `closed: not available from this archive (open issues only)` and names the archiver change
   needed. **It never prints `0`.** A zero is a measurement; an absence is not, and the two look
   identical on a card.

### 5. What `/ops check` gains

One report-only finding: a project that declares a board, runs the daily loop with `layout: card`, and
has **no archived day inside `movement.days`** — the archive is stale or the archiver never ran for that
board. Report only; the fix is an archiver run on another machine.

## What this is not

- **Not a chart.** The skill set writes records. What a series is drawn with, and where, is the project's
  own business.
- **Not a throughput series.** It cannot be one until the archive holds closed issues. Saying so on the
  card is the deliverable; pretending otherwise is the thing being prevented.
- **Not a second register.** Nothing is created, assigned or closed from here. The series counts what the
  team's own system says, which is the rule the coordination projects already run on.
- **Not a network reader.** The repository series reads live because a repository API is cheap and
  authenticated per user. A ticket board is archived by its own tool, and this CR does not change that.

## Implementation steps

1. `build_movement.py`: factor the writer and the block renderer away from the GitHub loader; add a
   loader that reads the archived days for a declared board, honouring `scope` (CR-112).
2. The four checks, and `source` in the snapshot.
3. `movement.from` in `ops-config/schema.md`; the configuration check reports an unknown value.
4. The `/ops check` finding.
5. Tests against a fixture archive: a truncated day, a day missing from the window, a `partial` fetch
   record, a board without `scope`, and an archive with no closed issues — each must produce its stated
   line and not a number.

## Open questions

1. **Does the archiver change land first?** If the archive gains closed issues before this is built,
   check 4 inverts: the outflow line becomes real and the fixture for it becomes the interesting test.
   The order does not block this CR — the open-volume series is useful alone — but it changes what ships.
2. **Two sources, one project.** Where a project genuinely tracks in both a repository and a board, two
   series on one card may be one too many for a five-minute standup. The card may need to name one as
   primary; that is a question for the first project that has both, not a decision to take now.
