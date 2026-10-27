# CR-153 — A declared Jira board is read in the shape the archive has, and mapped to the card's four words

| | |
|---|---|
| **Status** | **Proposed** (2026-10-22) |
| **Contract** | `contract_version` 46 → 47, `ops_config` 1.7 → 1.8 (**additive**): optional `external_systems.jira[].states` and `.always.keys`; `scope` is CR-112's key and is implemented here. A project that declares neither behaves as today, except that the reader stops returning a false zero. **Another CR in flight may take 47 and 1.8 first; whichever implements first takes them** |
| **Date** | 2026-10-22 |
| **Area** | `ops` (`build_agenda.py` `from_jira` and the release-blockers section, `project_brief.py`, `check`), `ops-config` (`schema.md`), `ecosystem.yaml` (`schemas`) · **a companion change in the ticket archiver** (the ticket archiver's own repository) |
| **Related CRs** | **CR-112** (narrowing a board to the project's part: implemented here, this CR depends on it), **CR-136** (the movement block reads the archive: it reads `states`), CR-074 (the `.jirameta/` archive), CR-084 and CR-101 (the agenda reads its declared sources; a skipped source announces itself), CR-107 and CR-114 (the card, release blockers from the label), CR-088 (`_fetch.json`), CR-110 (identifier matching uses ticket keys) |
| **Vault standard** | the organisation's `ops/_standards/work-tracking.md` §2, *One structure, any tracker* (proposed, 22 Oct 2026), and its decided row 27 |

Marks: **[E]** observed in a running series · **[H]** not yet run.

## What happened

On 22 Oct 2026, release day of a mobile app, the standup card read **"None carried as `[blocker]`"** and the sources
block read **"tickets: 0 changed"**. At the same time a Jira issue at priority **Blocker**, raised the evening before
by the company's CEO — incoming calls lost, the app opens on the wrong screen — was open and had been archived at
04:30 that morning. The release was held for it in the meeting. The card learned of it only because a person read the
Jira archive by hand. **[E]**

Three causes, each measured on the live archive (`<venture>/.jirameta/<board>/`, 2026-10-22, 500 issues):

1. **The reader returns nothing, and says zero.** `from_jira()` reads `updated`, `status` and `assignee` at the top level of
   each issue. The archive stores the raw Jira objects, so these are under `fields`. Run against the real snapshot the
   reader found **0 issues updated since 19 Oct; 114 had been**. An unreadable archive and a quiet board print the same
   line, which is the failure CR-074 recorded in the reader's own docstring. **[E]**
2. **The archive cannot say which issues are the project's.** The fields requested are
   `key, summary, status, assignee, reporter, priority, issuetype, created, updated, resolutiondate, labels, parent`.
   There is **no `components` and no `fixVersions`**: **0 of 500** issues can be matched to the project's component,
   so CR-112's `scope` could not be honoured even if it were implemented. The query is the whole R&D project, capped at
   500, and every run ends `partial (1 of 1 boards hit the issue cap)`. **[E]**
3. **There is nothing that turns a ticket's priority or status into the card's words.** A project that tracks in
   GitHub declares `labels:` (`blocker`, `gap`, `awaiting_test`, `blocked`, CR-114) and gets *Release blockers*,
   the release gap and *fixed, waiting for a test*. A project that tracks in Jira has no equivalent, so the section
   says "None carried" whatever the board holds. The company standard now says the tracker may differ by product and the
   structure may not (`work-tracking.md`, *One structure, any tracker*). **[E]**

**The board is wider than the project, in the other direction too.** On the same archive **eight open issues carry priority *Blocker***,
across all teams, and only two concern the mobile release. A rule that shows every *Blocker* would fix the missing blocker
and create six wrong ones. **[E]**

## Proposal

### 1. Read the archive in the shape it has

`from_jira()` reads the Jira object: `fields.updated`, `fields.status.name`, `fields.priority.name`,
`fields.assignee.displayName`, `fields.components[].name`, `fields.fixVersions[].name`, `fields.labels`, `fields.parent`.
The current top-level keys are kept as a fallback, so a differently shaped archive still reads. The ticket's state is the
status **name**, not the stringified object. This change needs no configuration and corrects the false zero for every
project that declares a board.

### 2. An unreadable archive is stated, never counted as zero

If a snapshot holds issues and **none** yields a readable `updated`, the sources block prints
`tickets  ABC  archive unreadable: no issue carried an updated date (shape ?)` and the agenda carries a *Config*
finding. A quiet board prints a count, an unreadable one prints that it is unreadable.

### 3. Map the register to the card's four words, as `labels:` does for a repository

```yaml
external_systems:
  jira:
    - key: ABC
      name: "The R&D board (mobile part)"
      reads: [issues, releases]
      scope:                          # CR-112: a filter on reading
        components: [mobile-apps-v3]
        exclude_components: []
        labels: []
        fix_versions: []
      states:
        blocker:        { priority: [Blocker] }
        gap:            { priority: [Blocker, Critical] }
        awaiting_test:  { status: [Fixed, "Ready for QA", "In Verification"] }
        blocked:        null          # a person owing a step is a dependency, raised in the room (D-88)
      always:                         # issues outside `scope` that matter to this release, named by a person
        keys: [ABC-9407, ABC-9558]
```

- **Release blockers** (CR-114) lists the open issues matching `states.blocker`: key, summary, assignee, age in days, and the
  source (`from Jira`). Carried `[blocker]` lines follow as *Other blockers carried*, as today.
- **The release gap** is the open issues matching `states.gap`, split into *still to fix* and *fixed, waiting for a test*
  (`states.awaiting_test`), the same two parts the repository series gives (the web app's D-99).
- **The round** routes an open blocker or an awaiting-test issue to its assignee's row, as it does for the repository series.
- **Matching is list-contains on names, case-insensitive**, and a value that appears in no archived issue prints
  `states.awaiting_test: "Ready for QA" matched 0 issues — check the status name`, not an empty block.

### 4. `always` is a list of keys a person named, not a rule about priority

A scope by component is only as good as the component field, and a backend ticket that blocks the release belongs to another
team and may not carry the project's component (here: the push-notification issue and a hold re-INVITE backend issue).
**`always.keys` names such issues, and an issue named there is read whatever its component.** It is a list of keys, and
nothing else: **a rule on priority alone is rejected**, because on the measured board **eight open issues carry priority
*Blocker* across all teams and two concern this release.** "Every Blocker, any component" would put six unrelated issues on a
release card, and a card that is wrong in that direction is read as noise and then ignored.

Two sources of keys, both written by people:

1. **`always.keys` in the declaration**, kept by the project.
2. **Ticket keys named in the newest note's carried lines**, which the room maintains already. A key a carried line names is read
   from the archive whatever its component, so the carried list is the list; no second list is needed for what the room is
   already tracking. A carried key absent from the archive prints `SNTLRND-9710 named in a carried line, not in the archive`
   rather than being skipped.

**The card's *Release blockers* are the issues in `scope`, or named by either source, that match `states.blocker`.** The sources
block states the widening and the remainder: `tickets ABC (scoped: component mobile-apps-v3, + 2 named by key) · 7 open at priority
Blocker outside scope and not named`. **No names, only the count**, so the card stays short; `/ops check` lists the unnamed ones by
key (point 7), and a person decides whether any belongs to the release and adds the key.

### 5. `scope`, as CR-112 specified it

CR-112's key is implemented as written: membership is list-contains, never equality (an issue with two components is in
scope if either is listed); the sources block reads `tickets ABC (scoped: component mobile-apps-v3) · 125 of 9,400 ·
fetched 06:30 ok`; a scope that matches nothing prints a warning, not an empty block. **This CR supersedes CR-112's
"proposed" status; CR-112 is closed as folded in.**

### 6. Companion change in the ticket archiver (separate repository)

Not core-skills' to make, named here as the prerequisite and **reported, not worked around, when absent**:

1. **Request the fields.** Add `components` and `fixVersions` to `ISSUE_FIELDS`.
2. **Narrow the query from the declared `scope` and `always.keys`**: `project = "KEY" AND resolution = Unresolved AND
   (component in (…) OR key in (…))`, so the project's part fits under the cap and the run ends `ok`, not `partial`. It also
   counts, without fetching, the open issues at priority *Blocker* outside both, so the reader can state the remainder.
3. **Archive recently resolved issues** (resolved in the last N days, N = `--since`), so a closure is visible. Today the snapshot
   holds open issues only and no issue carries a `resolutiondate` (CR-136 measured the same).
4. **Record the scope in `_project.json`**, so a reader knows what the snapshot excludes.

Until the archiver carries `components`, a `scope.components` declaration prints
`scope.components needs the archive to carry components (archiver 0.1.2 does not)`. **`always.keys` and the carried keys work
without it**, but only for issues that happen to be in the capped snapshot until the archiver adds `key in (…)` to its query
(point 6.2); a named key missing from the archive is reported, never dropped.

### 7. What `/ops check` and `/ops orient` gain

- **`check`:** a declared board whose newest snapshot is older than `movement.days` (report only; the fix is an archiver run
  on the machine that fetches); a `states` value or an `always.keys` entry matching no archived issue; a declared board with no `states`
  while `layout: card` (the card cannot show its release blockers from this source); **and the open issues at priority *Blocker*
  that are outside `scope` and named by no key, listed by key** (report only), so the person who owns the list can add the ones
  that belong to the release.
- **`orient`:** the tickets line states the scope, the count read, the fetch result and the readable-issue count.

### 8. Where the mapping is documented

`ops-config/schema.md` gains the `states`, `always` and `scope` keys. The vault standard `work-tracking.md` carries the
company-level meaning of the four words; this CR is the mechanism. The skill states **no status or priority names**: they
are the project's, and a project writes them once.

## What this does not do

- **No write to Jira**, no comment, no transition. The archiver stays read-only.
- **No descriptions or comments** are archived (the archiver's stated limit).
- **No claim about throughput.** That needs the archiver to archive resolved issues and page past the cap (point 6.3); this CR
  names it and does not print a zero in its place (CR-136, point 4).
- **No per-person counts** (CR-150): the assignee is shown on an open blocker so the round can route it, never aggregated.
- **No change to a project that tracks in GitHub.** `labels:` is untouched.

## Verification

1. **A fixture archive in the real shape** (nested `fields`, a status object, a priority object): the reader finds the issues
   updated since a given day. The current reader finds none; the corrected one finds all. **[E]**
2. **A blocker is shown when it is in scope or named.** A fixture with an open *Blocker* issue in the project's component
   produces a *Release blockers* row; a *Blocker* issue in another component produces **no row** and counts in the remainder
   (`1 open at priority Blocker outside scope and not named`); the same issue named in `always.keys`, or by key in a carried
   line, produces a row. A fixture with none produces `*None open at priority Blocker in scope or named*`, stated by name,
   rather than the old unconditional "None carried".
3. **`scope` is list-contains.** An issue with components `[A, B]` is in scope for `[B]`; an issue outside is not, unless a key
   names it.
   **A declaration with `always` and no `keys` (priority alone) is rejected** with a message saying why.
4. **A misspelled name is reported** (`"Ready for Qa"` is matched case-insensitively; `"Ready for QAA"` prints the zero-match line).
5. **An unreadable archive is stated.** A snapshot whose issues carry no `updated` anywhere prints *archive unreadable*,
   not `0 changed`.
6. **A project that declares neither `states` nor `scope`** produces the same agenda as before, plus the corrected counts.
7. **The live check:** re-run on the 22 Oct 2026 archive with `always.keys` naming the push-notification issue, the card lists
   the incoming-call issue (named in a carried line) and the push-notification issue under *Release blockers*, and states that
   six other open *Blocker* issues lie outside scope and are not named.

## Rollout

1. **Point 1 and 2 first**: no configuration, corrects the false zero everywhere. Ships on its own.
2. **Points 3 and 4 with `states` and `always.keys`**: the project declares its mapping and names the outside issues; the card's release blockers become true.
3. **Point 5 with the archiver's point 6.1 and 6.2**: scope by component, a mobile-sized query that fits under the cap.
4. **CR-136** then reads `states` for the ticket series.

## Open questions

- **Which statuses are "awaiting test"?** The board has *Fixed*, *Ready for QA*, *In Verification*, *Ready for Production*. The
  proposal maps the first three; *Ready for Production* is after QA and is treated as done for the gap. The project confirms.
- **Which priorities count as the gap?** *Blocker* and *Critical* follow the web app's `gap: [blocker, critical]`. The company
  label standard (Q4 in `work-tracking.md`) separates severity from priority; this CR reads whichever the board uses.
- **Does the board's priority field mean the release?** A *Blocker* priority on another team's ticket may not block *this*
  release. Only a person naming its key brings it onto the card (in `always.keys` or in a carried line), and the room decides;
  nothing here moves a ticket into the carried list by itself.
- **After the release**, `scope.fix_versions` can narrow the view to the next one; the key is declared now and used when
  a project wants it.

## Evidence

- A mobile project's standup of 22 Oct 2026 (summary §5-§7, §9): the room found there was no ticket for the call-drop issues; the decision that Jira is the only mobile tracker.
- The agenda for that day: *Release blockers* hand-written from the archive; the sources block's `tickets  declared  read · 0 changed`.
- The archive: the board's snapshot of 2026-10-22 (500 issues, `truncated`), `_fetch.json` (`partial`, `1 of 1 boards hit the issue cap`).
- The archiver's field list and JQL (`ISSUE_FIELDS` and the fetch query).
