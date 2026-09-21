# Changelog

All notable changes to core-skills will be documented in this file.

<!-- Release process: docs/RELEASING.md (CR-026) is authoritative.
Short form: implement generic -> private CR spec updated same session ->
CHANGELOG/README/ecosystem bump -> alignment check -> commit -> push
(pre-push guard scans added lines) -> webpage+Marvin on version change. -->

## [1.61.0] - 2026-09-21

### Added

- **The loop declares both of its ends.** Rendering it for the first time showed it stopping short at
  each — obvious in the output, invisible in the declaration.

  **Input.** A transcript was produced only by `meet`, as though the meeting were the sole route in. It
  is not: a recorder into a knowledge base read over MCP, a file dropped in, or text pasted straight into
  the session. **The loop does not care which** — it cares that the source is *named in the note*,
  because two recordings of one meeting is the normal case and a note that cannot say which one it came
  from cannot be corrected against it.

  **Output.** The loop ended at `_outbox/<item>/_manifest.md` — a file, not a person. New `deliver` step
  (external): a dashboard reads `_outbox/`, previews the staged item and delivers it over the channel its
  manifest declares — a chat workspace through the messaging client, or an email draft a person presses
  send on. It writes back `status`, `status-note`, `channel` and `contact` **only**, per the dispatch
  contract; it never authors a manifest, decides what a status means, or archives.

  `record` now consumes *the message, delivered* rather than the manifest, so the chain ends where the
  material reaches someone. Thirteen steps; `check-components.py` passes.

## [1.60.0] - 2026-09-21

### Added

- **A loop step names its command, and `/ops help` renders the declaration (CR-063).** CR-062 declared
  the loop so the README and landing page could render one source. It stopped one step short of the
  question a person actually asks: *which command do I run.* A step said *"the agenda generator"* and not
  how to invoke it, so `/ops help` — whose own spec commits it to describing the flow — was about to
  become the **fourth** hand-written copy of the same twelve steps. **The cost of a stale copy is highest
  there**, because a help command is read by the people who cannot tell that it is wrong.

  Optional `command:` on the nine steps that have one. `/ops help` now renders by phase in declared
  order, each step showing its command and its **`consumes` → `produces`** — the question after *which
  command* is always *what does it need and what do I get*, and the declaration already held both.

  **Manual steps show `why_manual` where the command would be.** That substitution is the most useful
  line in the output: it tells the reader nothing is missing.

### Changed

- **`check-components.py` holds the two claims against each other.** A step cannot be both `manual` and
  commanded — if it can be run it is not manual, and a reader resolves that contradiction by guessing.
  And a step with no `command`, no `manual` and no `external` now fails: silence reads as an unfinished
  feature, which is the failure `why_manual` exists to prevent, one field over. Both verified against a
  deliberately broken declaration.

## [1.59.0] - 2026-09-21

### Added

- **`working_loop` — the steps a person takes, declared (CR-062).** Twelve steps in
  order, grouped by phase, each naming what it consumes and produces. The three manual
  ones are marked and each says **why** it is manual, because a step marked manual and
  not explained reads as an unbuilt feature.
  - **Declared rather than drawn twice.** The README and the landing page both render
    a diagram of this loop. Two hand-written copies are two things to keep true — which
    is exactly how the README's release list went seventeen versions stale.
  - `check-components.py` now validates it: a step cannot name a vault path nothing
    declares, cannot consume what no step produces, and cannot be marked manual
    without a reason. Two entries failed on the first run and were fixed.

## [1.58.0] - 2026-09-21

### Fixed

- **The gap-explainer rendered on every agenda that had any item older than a day.** The carried-item
  tuple grew from four fields to five in v1.53.0 and one unpacking was left as `*_, g`, which from then
  on read the **age** where it meant the **gap count**. So a footnote explaining what `skipped` means
  appeared under tables where no item was skipped. A wrong explanation is worse than none: it teaches the
  reader a column that is not there.

- **A round table with no roster and no extra columns rendered malformed and empty** — a header with one
  cell, a separator with two, and a blank row. A table is only worth its space when it has rows; with no
  roster the section now carries the prompt alone.

### Changed

- **Carried items are split into what is owed *into* this session and what is still carrying.** Sixteen
  undifferentiated rows is a wall, and the five raised at the last session — the actionable ones — sorted
  to the bottom because the sort ranks by session count. The split puts them first and labels both
  groups; below two items the table stays single.

## [1.57.0] - 2026-09-21

### Fixed

- **`/ops brief` finds a series' staged items where the series is not a folder (CR-061 follow-up).** The
  outbox match compared a manifest's project field against the folder the config was found in — which,
  for an org-level series, is the **venture**, not the series. The block simply never appeared, and an
  empty block is indistinguishable from nothing staged. New optional `carry_forward.project` names the
  series as a manifest writes it. On the first run with it set, one series showed **two recaps blocked,
  one of them for 27 days.**

- **An item staged ahead of its session no longer reports a negative age.** Staging an agenda before the
  meeting is the normal case; `-1d` reads as a bug rather than as *not yet due*. Future dates render as
  `in 1d`.

## [1.56.0] - 2026-09-21

### Added

- **`note_suffix` may be a list, and takes a wildcard per entry.** A series can legitimately carry more
  than one filename shape — a weekly plus its extra sessions, or a series renamed mid-history. Matching
  only the main shape silently drops the rest, and **an extra session is where the most urgent items tend
  to live**: one twelve-minute extra had six actions, three of them due into the next session, and none
  was visible to the chain.

### Changed

- **The carry-forward section is cumulative, and that is now stated.** It lists everything still open at
  the end of a session, not only what that session produced. The name means what it says — an item
  carries until it closes.

  It matters because the next agenda reads **the newest note only**. Widening the pattern to include
  extra sessions made a short extra the newest note, so a section listing only its own two items would
  have **silently dropped everything still open from the week before**. Writing the section is a review
  of the standing list, not a summary of the last hour.

  **This is the one place the loop's rules pull in opposite directions**, and conflating them breaks
  something either way: the recap is bounded to its own session because it reports what *happened*; the
  carry-forward section is cumulative because it reports what *remains*. A cumulative recap invents
  history; a bounded carry-forward loses items.

## [1.55.0] - 2026-09-21

### Added

- **`/ops brief` — where a recurring project stands, before work resumes (CR-061).** A session opening a
  project cold had no way to ask. `/ops status` reports which *config* applies; `/ops sweep` audits a
  whole vault; `/bod` does exactly this job but for a **software** project — app log, running version,
  health check — none of which a coordination project has. So orientation meant opening the changelog,
  the newest note and the open questions and inferring the rest: four files, performed identically every
  session, with whatever nobody wrote down simply lost.

  Six read-only blocks: loop position (including **whether the next agenda exists yet** — the common
  failure is not a missing note but a missing agenda), chain integrity, what is carrying with sessions
  and age and how many are `UNOWNED`, archive freshness, **staged-and-unsent**, and the changelog's last
  entry. It writes nothing, fetches nothing and judges nothing.

  Everything it reads was already machine-readable. **The gap was that nothing read it together** — the
  same session that wrote this had earlier worked an hour from a stale checkout because no step asked,
  and found a recap written on a Friday and never sent because a file in a meetings folder carries no
  status.

### Fixed

- **A series whose config lives further up now labels itself correctly.** An org-level meetings folder
  resolves its config from a venture `_ops.yaml`, so the folder name was the venture, not the series.
  The declared `title` is used where there is one.

## [1.54.0] - 2026-09-21

### Fixed

- **Carry-forward config is resolved by the normal chain, and `note_suffix` takes a wildcard.** Both
  found while enabling the mechanism on two series that are not projects.

  **A recurring series is not always a project.** The lookup checked only a project's
  `.claude/ops-config.yaml`, so an org-level meetings folder — which has no project config, only an
  `_ops.yaml` further up — found nothing and fell back to defaults **silently**. It now walks both,
  nearest first.

  **Real filenames are not uniform.** One series carries a week number (`coreteam-weekly-w38`), another
  carries participants who change (`bi-weekly-Ann-Bo-Cai[-Dee]`). An exact `note_suffix` finds
  neither, so it now takes a `*` wildcard.

  **And a wildcard alone is not enough.** It matches greedily: `coreteam-weekly-w*` swallowed that
  series' `-appendix` file and `bi-weekly-*` swallowed its `-preparation`. Companion artifacts are now
  excluded by name — agendas, preparations, priorities, facilitator sheets, appendices, recaps, staged
  messages. **Treating a preparation as a note would read next week's intentions as last week's
  record**, which is worse than finding nothing.

## [1.53.0] - 2026-09-21

### Added

- **Carry-forward escalates on sessions *or* elapsed days, whichever trips first.** `escalate_after_days`
  under `carry_forward`, default 14.

  **A session is not a unit of time.** Three sessions is three days on a daily standup and up to three
  months on a fortnightly one — so a session count alone escalates far too late on an irregular series,
  which is precisely where items go missing. Measured across four real series before adding this, and
  **none of them was regular**: nominally-weekly meetings showed gaps of 7, 14, 21 and 26 days, and a
  fortnightly series had a 59-day gap in its record. On that series an item could carry for two months
  and still read as `2` — below threshold and invisible, which is the exact failure the escalation
  exists to catch, reintroduced by measuring in the wrong unit.

  The days rule is effectively inert on a daily series, where sessions trip first. It exists for
  everything else. Age is shown in the table from seven days, so the count and its meaning are visible
  together rather than one standing in for the other.

## [1.52.0] - 2026-09-21

### Fixed

- **The agenda generator honours a declared schedule instead of assuming daily.** Not every standup is
  daily. A twice-weekly Monday/Thursday series generating a Tuesday agenda produces a file nobody opens
  — and worse, the carry-forward chain then looks broken on Thursday, because the Tuesday file is the
  newest thing in the folder with no note behind it. A cadence mismatch would have manufactured the
  exact failure the chain check was added to detect.

  The next session is read from `carry_forward.schedule_days`, falling back to any
  `meeting_types.*.schedule.days` already declared, and finally to the next weekday. Found when enabling
  the mechanism on a second series whose cadence had changed from daily five days earlier — the config
  said so, nothing had read it.

## [1.51.0] - 2026-09-21

### Fixed

- **A reappearing carry-forward item keeps its count (CR-057 follow-up).** The session counter counted
  *consecutive* appearances and broke on the first absence, so an item carried on the 16th, dropped from
  the 19th and carried again on the 21st read as brand new and its escalation clock restarted. **A
  genuinely stuck item could hide indefinitely by skipping every third session** — which is the exact
  outcome the escalation exists to prevent.

  It now counts appearances. Two rules make that safe: a note with **no carry-forward section is
  skipped rather than counted as an absence** — that note says nothing about any item, and reading its
  silence as *resolved* is the same mistake in a different place — and an item missing for more than two
  sessions is treated as a fresh raise, because *carried in March, back in September* is a new problem
  wearing an old name.

  **Gaps are reported rather than hidden** (`3 · skipped 1`). A gap has two readings that are identical
  from here — a note that dropped the item by mistake, or one resolved and later re-raised — so the
  count stands and the ambiguity is shown to the person who can resolve it.

  Measured on a real series: two items that both read as **1** under the old logic are **4** and
  **3 · skipped 1**, and both now trip the escalation.

## [1.50.0] - 2026-09-21

### Added

- **The post-meeting recap, generated on request (CR-059).** Step 9's third audience: the summary is the
  archive, the priorities artifact is for the people doing the work, the recap is for people who need to
  know and were not there. `recap_artifact` under `workflows.post_processing`, default off.

  **Shipped with one amendment to the proposal: it is offered, not produced.** Every other Step 9
  artifact runs as a side effect of the pass. The recap does not, because it is the only one that
  **leaves the building** — it reaches people who were not in the room and who read it once. The
  proposal's own §5 bounds its content to a single transcript; what follows, and the proposal does not
  say, is that the transcript is **the narrowest of the three inputs a project has**. The chat and repo
  archives hold decisions the room never said aloud. So an automatic recap is not merely incomplete but
  **confidently incomplete, and invisibly so to its readers**, who have no transcript to check it
  against.

  The content gate still applies after the request: a recap is warranted only where the meeting produced
  a schedule, ownership or scope change, a release or moved date, a reframing finding, or an ask of the
  wider team. Otherwise say so and stop — a recap that restates the working list trains people to stop
  reading recaps.

  **The source boundary is the hardest constraint and is spelled out**, because two other rules read as
  licence to break it: *the first block carries what most changes the reader's world* governs ordering
  within a session, not eligibility; *reframe, do not just report* means saying what was said more
  clearly, not adding what was not said. An unsent recap has **expired, not accumulated** — it goes out
  late carrying its own date, never folded into the next one.

  Staged as a folder with a manifest, never a loose file. The generator **authors the manifest and never
  writes `status` or `status-note`** — those record what a dispatching surface did first-hand, and the
  send is a human act. It defines no channel or recipient vocabulary of its own; `channel:` selects
  which value to write into the existing field.

### Fixed

- **`carry_forward` and `recap_artifact` are now schema-known in `ops-config/base.yaml`.** `carry_forward`
  shipped in v1.49.0 without being declared there — the same defect CR-059 was written to name: a
  documented key that no default declares looks solved while `/ops status` cannot report it.

## [1.49.0] - 2026-09-21

### Added

- **The agenda is generated from what did not land (CR-057).** A series wrote an agenda, held the
  meeting, recorded a note — and nothing compared them. Measured on one project: of seventeen agenda
  items, six fell through, and the correlation was not with position on the page. Two items led the
  agenda on two consecutive sessions and were skipped both times. **Every item that fell had no named
  owner present.** `carry_forward` under `workflows.post_processing`, plus `skills/ops/build_agenda.py`,
  which reads the newest note's `## Carried forward` section and writes the next agenda with those items
  above the round, each showing how many **consecutive** sessions it has carried. At the threshold the
  agenda says so itself: an item surviving three agendas has no owner who is present, or is not actually
  being asked for. Owner is read from a defined position, never guessed from prose — anything else is
  `UNOWNED`, and that is the finding rather than a parse failure.

- **Retrieval before the agenda, from the declared archives (CR-058).** A transcript carries only what
  was said out loud. On 2026-09-21 a test matrix agreed in the series chat at 07:23 appears in **no
  transcript**, reaching neither the note nor the recap; the same morning two dozen issues had changed
  state, almost none assigned. `build_agenda.py` writes a *Since the last standup — not said in the
  room* block from `external_systems` (CR-054) — **the first skill-side consumer of that declaration**,
  and the first reader of both archives it points at. `chats:` is a **retrieval source**, not only a
  send destination. Both sources are **read from their archives** — `.chats/` (CR-047) and
  `.githubmeta/` (CR-055) — so an agenda generates with no credential and no connectivity; the chat
  folder resolves by **platform id** rather than a second hand-written name; `reads:` is honoured where
  the archiver recorded it; and a snapshot older than the last note says so rather than passing stale
  rows off as news. Adds no configuration.

### Changed

- **The recap is requested, not produced automatically (CR-058).** Proposed as an amendment to the
  recap-artifact CR. The recap is the one artifact that leaves the building; assembled automatically
  from the narrowest of three inputs it is confidently incomplete, and invisibly so to readers with no
  transcript to check it against.

## [1.48.0] - 2026-09-21

### Changed

- **Staged folders name the subject, not the artifact inside them (CR-056).** `/outbox` documented
  `YYMMDD-<contact-or-project>_<context>/` and never said what `<context>` means. Left undefined, four
  staged items in one vault interpreted it four ways in five days, and one named its folder after a file
  it later no longer contained. The right side names the **subject of the send**; a staged item is a
  folder whose `_manifest.md` already enumerates its contents. The exception is where the artifact type
  *is* the subject — a deck sent as a deck, a pre-read as a pre-read. The left side names the
  **recipient**, not the project: the project is recoverable from the content and the manifest, while
  who it goes to is the one thing a folder listing cannot otherwise tell you.

## [1.47.0] - 2026-09-21

### Added

- **`<venture>/.githubmeta/` is declared, with the component that writes it (CR-055).**
  A repository metadata archive: issues with their state and dates, releases, commit
  subjects, a docs listing. **Metadata only — never the code**, because a vault holds
  the record of work rather than the work.
  - The sibling of `<venture>/.chats/`, and deliberately the same shape: a folder per
    subject, a manifest saying what the folder is, dated raw data, a dated `.md` for
    reading. Two archives answering the same kind of question should not need two
    mental models.
  - **One difference, stated rather than discovered:** a day's file is a *snapshot*,
    not a merge. Chat messages are events and accumulate; issue state is a reading
    taken at a moment, so the later fetch of a day is the truth rather than twice the
    data.
  - This is what makes CR-054's `repos:` block readable by something other than a
    dashboard — the gap that CR-054 itself named: *a documented config key that no
    tool reads is the same failure as an undocumented habit.*

## [1.46.0] - 2026-09-21

### Added

- **`external_systems` in the ops config (CR-054).** A folder declares the systems its
  work actually lives in: the chats it posts to, and the repositories it concerns.
  Resolved by the existing config chain, so an org declares once and a project
  overrides.
  - **Why:** a recap staged in `_outbox/` has to reach a specific chat, and nothing said
    which. The chat was picked from a live list of seventy by recognising the name —
    which works until it does not, and leaves no record of where a project posts.
  - **A declaration, not a credential.** No tokens. It says *which* chat and *which*
    repository; how a tool authenticates stays in that tool's own config. That
    separation is what lets the block live in a vault file at all.
  - **Hand-written.** A tool may read it and offer what it finds; it must never append a
    chat it happened to send to, because that turns an accident into a declaration.
  - `reads:` under a repository is a scope — `docs`, `issues`, `releases`, `pulls`. The
    intent is metadata, never cloning a codebase into the vault.
  - A missing block is not a defect. A tool falls back to what it did before.

## [1.45.0] - 2026-09-21

### Changed

- **The manifest's fields are named by identifier, not by label (CR-053).** Five entries
  described them as "Status, Kanal, Kontakt" — the Swedish labels a vault writes them
  under. In a public contract that reads as Swedish identifiers, and it invites exactly
  the mistake `identifier_language` was written to prevent: a tool hardcoding the label.
  They are now `status`, `channel`, `contact` and `canonical source`, with one entry
  stating that the written form follows the vault language and belongs in a
  vocabulary file.
  - The `identifier_language` rule now says this applies to the contract itself.

### Added

- **The status-note field is declared, and a dispatcher may write it.** It was in use by
  **104 of the live vault's manifests** while appearing in no schema — it grew in
  practice. `Status` is parsed by a pattern; the note is read by people and carries what
  actually happened: the channel, the time, a published URL, why a send was partial.
  - The dispatcher's permitted writes go from three fields to four. The boundary the
    `never` clause draws is unchanged and now stated explicitly: **it may record what it
    DID first-hand, because that is observation; it may not write what the outcome MEANS
    for the item.** The outcome section and the reply checklist stay the skill's, which
    is what makes archiving the skill's too.

## [1.44.0] - 2026-09-21

### Added

- **The inventory scanner is a component, and `_INDEX-*.md` is a declared path (CR-052).**
  A local script sweeps the machines a vault describes and regenerates the registers
  saying what runs where. It writes vault files and was not in the graph.
  - It is the one component that **bridges the two maps**: its input is
    infrastructure and its output is a vault file. That is why declaring it also
    settles where the boundary runs.
  - The registers are GENERATED in the `write_ownership` sense — a hand edit is lost
    on the next sweep.

### Fixed

- **`check-components.py` let a prose write pass unchecked.** An entry phrased as
  "the generated registers at vault root" named a file without looking like a path,
  so nothing verified it — which is how the scanner's write passed on the first
  attempt while declaring nothing. Prose is still allowed, but any vault-file shape
  inside it is now checked.

## [1.43.0] - 2026-09-21

### Added

- **`_infrastructure/` and `_architecture/` declared (CR-051).** Two vault-root
  surfaces that answer the same question one layer apart: `_infrastructure/` documents
  the machines — topology, connectivity, who operates what from where — and
  `_architecture/` documents the software system: which components exist, which
  repository holds each, what reads and writes the vault.
  - `_infrastructure/` has been named in `prefix_conventions` since CR-034 but was
    never declared as a path, so nothing said who writes it or what it holds.
  - Both are SINGLETON by the CR-036 test: each describes the system as a whole, so a
    folder-scoped copy would describe nothing.
  - The split matters for what each may contain. `components:` in this file is the
    source and is deliberately generic — "a dashboard", "a messaging client" — because
    this file is public. `_architecture/` is where those roles map onto actual
    repositories, hosts and employers, which is exactly what this contract must not
    carry.

## [1.42.0] - 2026-09-21

### Added

- **`components:` — how the parts connect (CR-050).** `vault_conventions` declares how
  each part touches *files*. This declares how the parts touch *each other*: what
  imports what, what calls a third-party service, and which direction each dependency
  runs. Six components, as roles rather than product names, so an installation maps its
  own tools onto them.
  - **Writing it found two undeclared vault files.** `_inbox/_inbox.yaml` — a real
    register with a v2 schema, written by two skills and a dashboard — was in no
    declaration at all, and `_outbox/<item>/_manifest.md` was covered only by its
    parent folder although two different parties write it. Both are declared now.
  - `scripts/check-components.py` verifies every path a component claims against
    `vault_conventions`, checks `depends_on` for cycles, and requires the fields a
    reader relies on. It runs from the alignment check, so the two blocks cannot drift
    apart silently — which is exactly how those two paths stayed undeclared.
  - The rule the graph encodes: **two components that only share a vault file are not
    dependent on each other.** The file is the contract between them. That is why a
    dashboard and a task pipeline can both write the task ledger without knowing the
    other exists.

## [1.41.0] - 2026-09-21

### Added

- **`identifier_language` rule (CR-049).** Identifiers are English; the words a person
  reads are data. Schema fields, enum values, status keys, config keys, dictionary keys
  and variable names are what a second tool must agree with to interoperate, so they
  carry one language. Display text stays in the vault's working language and lives in a
  settings or vocabulary file.
  - The existing `system_file_language` rule covered file *names* only. This covers
    what is inside them, which is where the drift actually was: a dispatcher hardcoding
    the vault's Swedish status words, and a sync tool using Swedish display strings as
    dictionary keys in 38 places.
  - Where the two were historically the same string, the **label** keeps the existing
    spelling. Renaming a key costs nothing; renaming a label changes what an external
    system or a person sees.

## [1.40.0] - 2026-09-21

### Added

- **The task status enum is declared (CR-048).** `schemas.tasks: 2` named a version
  but nothing said which statuses were legal, so three other dialects grew in the gap:
  `open`/`done` written by an external task pipeline, `todo`/`waiting` in operational
  files, and one-off words like `superseded`, `paused` and `obsolete`. The schema in
  the tasks skill has always said `pending | in_progress | blocked | completed |
  cancelled`; declaring it in `ecosystem.yaml` is what makes it checkable by a tool
  that never opens the skill.
  - Split into `active` and `finished` rather than one flat list, because every
    consumer asks one of those two questions rather than testing a specific word.
  - Carries the rule that made the drift harmful in practice: **a reader should
    tolerate an unknown status rather than treat it as active.** A dashboard counting
    only `completed` as finished showed finished tasks as outstanding and put some on
    its overdue list.

## [1.39.0] - 2026-09-21

### Added

- **`outbound_dispatch` declares how staged material actually leaves the vault (CR-047).**
  `_outbox/` has always been where outgoing work is staged, but nothing in the contract said
  what delivers it. External tools now read and write vault paths without appearing anywhere a
  client could discover them. The block names the dispatching tools, the channels they use, and
  what each is permitted to write -- one field of one file, in the dispatcher's case.
- **`<venture>/.chats/` is declared.** A chat archive written by an external CLI: raw provider
  message objects plus a rendered `.md` per day. A dot-folder so the vault's own tooling ignores
  the raw data. Its placement is PER_BOUNDARY -- it belongs to the venture whose account the
  chats came from, never to `_private/`, because the axis is whose material it is rather than
  how sensitive it is.

### Changed

- **`_outbox/` declaration brought up to date.** It described PDFs awaiting send and named
  `mail.app` as a reader. It now states the real contract: one folder per send event, each with
  a `_manifest.md` carrying Status, Kanal, Kontakt and Kanonisk källa, which is what any
  dispatcher reads.
- **contract_version 9.** Additive; clients on 8 ignore the new block.

### Known gaps

- **An item decided against can never be archived.** `/outbox archive` requires a sent status,
  so anything marked superseded, replaced or withdrawn stays in `_outbox` indefinitely -- it was
  resolved, just not by being sent. Recorded in `outbound_dispatch.known_gaps` with a proposal:
  treat a stop-marked manifest as archivable when `## Utfall` states why, since Utfall is
  already the outcome field and "not sent, because X" is an outcome. Owner is the `/outbox`
  skill -- a dispatcher inventing a status the skill does not recognise would be worse than the
  gap.

## [1.38.1] - 2026-09-20

### Fixed

- **The landing-page check stops reporting a version it was never going to find.** The page's
  what's-new title carries the `{v}` placeholder, substituted at render time with the version it
  fetches from the published contract. The check greps the title for a literal `vN.N.N`, found
  none, and reported `[DRIFT] vunknown` on every run -- including runs where the live page was
  correctly showing the current version. A placeholder cannot drift, so it is now reported as
  aligned, with the reason stated.
- **Why it matters beyond the noise:** `/ops sweep` check 8 reads these verdict lines, so the
  false alarm reached the weekly sweep, where it competed for attention with real findings. This
  is CR-041's argument applied to the check itself -- reporting a healthy component as broken
  every week is worse than not checking it.

## [1.38.0] - 2026-09-20

### Added

- **`metric` is a canonical insight type (CR-046).** A measurement where *the number is the claim*
  had no slot in the taxonomy and landed in `learning`, which had grown to 36% of one corpus
  (944 of 2 570 entries) and stopped working as a retrieval filter. The gap was already visible in
  the code: `/transcript`'s Structured Extraction emits a `metrics:` block with `name`/`value`/
  `context`/`trend` and nothing downstream could store it.
- **Five optional fields on a `metric` entry** -- `value`, `unit`, `baseline`, `period`, `trend` --
  so the figure stays machine-readable instead of being trapped in prose. All optional; an entry
  with only `summary` is valid.
- **A write-time test that needs no judgement:** remove the number from the summary. Nothing left
  means `metric`; a claim that still stands means `learning` citing evidence.

### Changed

- `contract_version` 7 → **8**. Additive: clients on 7 ignore the new enum member.
- `metric` is **excluded from CR-013 promotion**, alongside `opportunity`, `quote` and the evolution
  types. The same measurement recurring three times is a time series, not a standing instruction;
  trend questions belong in `/analytics`, which reads source systems rather than the insight corpus.
- `workflows.knowledge_extraction.types` in `base.yaml` gained `metric` -- and `quote`, which had
  been missing since it became canonical in v1.21.0. Nothing enforced the list, so quote extraction
  worked anyway; the omission would have bitten the first reader that trusted it.

### Deferred

- `constraint` (the other half of CR-046) is **not** implemented. A parameter that bounds a decision
  not yet made is a real shape, but the evidence is two independent uses six months apart against
  119 candidate measurements. Named in the CR, revisit after another quarter of corpus growth.
- `reference` -- provenance notes ("where did this go, which copy is authoritative") -- remains
  without a home. Recorded in the CR so the next reviewer does not rediscover it.

## [1.37.4] - 2026-09-16

### Changed
- **`Kanonisk källa` is now REQUIRED in outbox manifests (CR-032).** Every manifest must
  state where its material actually lives: either a path (the attachment is a rendering and
  the outbox copy is disposable) or `ingen (originalet bor här)` (the material exists nowhere
  else, so the folder must be archived rather than deleted).

  **Why:** an audit found 86 outbox items where only 3 of 71 manifests named a source. That
  made a routine question — *"is this a copy or the original?"* — unanswerable without opening
  every folder. PDFs turned out to be renderings, but the mail texts and manifests existed only
  in `_outbox/`, so a bulk clean-up would have destroyed material. The field moves that
  determination to **creation time**, where the author knows the answer, instead of to
  clean-up time, where nobody does.

- **`/ops sweep` check 4 now flags manifests missing the field**, alongside the existing
  sent-but-unarchived and aging findings.

- **`archive` warns but does not abort** on a missing field — refusing would strand legacy
  folders.

## [1.37.3] - 2026-09-12

### Added

- **`check-ecosystem-alignment.sh` verifies `contract_version` against its own comment block
  (CR-045).** The highest `# contract_version N` documented in the file must equal the
  `contract_version:` value below it. Closes the gap CR-044 named: the field drifted for five days
  and four releases because nothing read it back. Placed first among the checks — it is about the
  contract itself, not a component's reference to it.
- Distinct verdicts for the degenerate cases (no comment lines to check against; unparseable field).

### Why it is cheap

Every bump was already written in a fixed shape, which made the comments a checkable declaration
rather than prose. No new config, no new file, and `/ops sweep` check 8 already parses this script's
`[OK]`/`[DRIFT]` lines — so the check reaches the weekly sweep the moment it exists.

Verified in both directions: resetting the field to `2` reproduces the historical bug and the check
reports *field says 2, comments document 7*. Had it existed on 2026-09-07 it would have failed on the
first run after CR-034.

## [1.37.2] - 2026-09-12

### Fixed

- **`contract_version` corrected 2 → 7 (CR-044).** The field had never been changed since the file
  was created; CR-034 through CR-038 each documented a bump in a comment without touching the value,
  and Marvin's notes described version 6. Nothing reads the field back, so nothing caught it.
- Comment block reordered descending, with a correction note recording that no client was ever
  served 3, 4, 5 or 6.

### Changed

- **`placement_classes`: PER_FOLDER presence may be CONDITIONAL (CR-040).** A folder declaring
  `workflows.task_ledger.mode` `external` or `none` legitimately has no `_tasks.yaml`; readers must
  not treat that absence as an empty or stalled folder. The `<folder>/_tasks.yaml` lifecycle says the
  same. Without this the contract and the skill disagreed, and the contract is what third-party
  clients read.

### Known gap

- Nothing verifies `contract_version`. The alignment check compares `core_skills_version` across
  three components and never looks at the contract version — which is exactly why it could sit wrong
  for five days. A follow-up should assert it against the highest bump documented in its own comment
  block.

## [1.37.1] - 2026-09-12

### Added

- **Allow-lines in the private push denylist (CR-043).** A line starting with `!` is an ERE whose
  matches are masked before any deny-pattern runs, for the narrow case where one identifier inside
  an otherwise-blocked domain is public by design. The hook enforces a left word-boundary itself
  (`(^|[^A-Za-z0-9_.-])`), so a longer label ending with the allowed one stays blocked.
  `scripts/privacy-scan.sh` applies identical semantics — the guard and its scheduled auditor must
  not disagree about what is allowed.
- **README links to the project's landing page** from the version line.

### Why

ERE has no lookbehind, so "block this domain except this one host" cannot be written as a regex
without enumerating an eleven-character label's mismatch positions. A fragile pattern in a
security control is worse than the gap it closes — so the exception became a mechanism, with the
boundary enforced by the hook rather than trusted to the pattern author.

## [1.37.0] - 2026-09-12

### Added

- **`workflows.task_ledger` — declared system of record per folder (CR-040).** Three modes:
  `local` (default, unchanged behaviour), `external` (work is tracked in a declared system —
  name, pointer and reference field required), `none` (summaries only). Config schema v1.3 → v1.4.
- **ops-base: *Task-ledger resolution*** — the rule, the mode table, the config shape, and the
  generalised one-item-one-home constraint.
- **ops-config schema** — `task_ledger` block with guidance on when each mode applies.
- **Sweep: two new findings replacing rot under `external` (CR-041)** — an incoherent declaration
  (missing `system`/`pointer`, or an unresolvable pointer), and the duplicate the declaration exists
  to prevent (a folder declaring `external` that still carries a local ledger).

### Changed

- **`/ops` resolves the ledger before touching it**, at four points: prep context gathering
  (Step P1), the `task_yaml` row of the update-files table (Step 5), task import (Step 9), and the
  create-if-missing fallback. Under `external`, no `_tasks.yaml` is read, created, or resolved via an
  ancestor; action items are split into implementation items (recorded by reference, and offered to
  be raised in the system of record when no reference exists) and coordination items.
- **`/ops sweep` check 2 resolves the ledger mode before judging a missing `_tasks.yaml` (CR-041).**
  `_insights.yaml` staleness is still checked in every mode — the knowledge layer is local wherever
  the work is tracked.
- **`/analytics pipeline` excludes non-`local` folders from tasks-per-meeting (CR-041)** and names
  them as *external ledger* instead of leaving a zero that reads as a gap. It does not read the
  external system.

### Why

The ancestor walk was the dangerous half. Creating an unwanted ledger is visible; silently writing a
folder's coordination items into a **parent's** ledger is not — they land where nobody looks, and the
folder reads as having no open work. Declaring the absence also separates *deliberate* from
*neglected*, which the sweep's ledger-rot check cannot otherwise distinguish.

CR-041 ships with CR-040 rather than after it: a declaration the two *reading* skills do not
understand would have reported a correctly-configured folder as broken in its first weekly sweep, and
a check that cries wolf stops being believed before it is ever right.

## [1.36.1] - 2026-09-08

### Added
**Generated-view isolation (CR-038).** Placing one new file surfaced a rule that was
missing. A per-folder situational view — meeting cadence, insight counts, open items —
would obviously be `<folder>/_status.md`: underscore, because the user reads it. That
satisfies CR-034 but creates a circularity, since `.md` files in those folders are scanned
by several skills, so a generated view can be read back as source and synthesised into a
view of itself.

The first fix considered was a `skip_scan:` flag. **CR-033 already proved that fails** —
four skills reached `.handoff/` despite an explicit skip-list, because they globbed on the
`YYMMDD-` prefix instead of consulting the list. A markdown file sitting among meeting
documents is *easier* to hit by accident than one in a dot-folder.

`.knowledge/wiki/` solved this structurally. Applied at folder scope:
**`<folder>/.status/current.md`**. The dot does not mean rarely read here — the user opens
it deliberately. It means **unreachable by scanners**, a third meaning distinct from both
dormant and blocked.

**System-file language (CR-038).** System and structure files carry English names
regardless of content language: `_config/priority.md`, `_config/naming-prefix.md`,
`_inbox/_frame.md`, `.status/current.md`. Forward-looking, with two declared exceptions —
derived registers read by scripts, and generated wiki articles that keep the language of
the corpus they summarise.

### Changed
- Three files renamed to English; twenty files updated, zero broken links.
- Naming that repeats the path is rejected: `status-<contact>.md` inside
  `<contact>/.status/` states the identity twice and breaks when a folder is renamed —
  which happens when a person's meeting series moves between organisational axes.

### Noted
A preparation document had reached **337 lines across ten sections**, each already tagged
`[DECISION]` / `[MUST RESOLVE TODAY]` / `[IF TIME ALLOWS]`. The structure was sound but not
**surveyable** — finding what had to close that day meant paging through the file. The fix
is neither a summary nor a second file, but a table of what already exists, one row per
section, ordered by urgency rather than number, placed first. Recommended as a mandatory
opening section in `preparation`.

## [1.36.0] - 2026-09-07

### Added
**Prefix conventions and dot-surface levels (CR-034).** `ecosystem.yaml` now states the
rule that governed both prefixes in practice but was never written down: **the prefix
answers whether the surface is READ in everyday work.** Underscore = read routinely,
dot = read rarely or never.

**Read frequency and write ownership are separate axes.** `_insights.yaml` settles it:
machine-written by `/insights`, yet underscored, because several skills read it
automatically — **generated does not imply dot**. Write ownership becomes its own declared
property per path, since a generated surface edited by hand loses its next regeneration
silently.

**`.knowledge/` is declared a known exception.** It is read frequently and its `INDEX.md`
is the documented first stop for knowledge questions, so the rule says underscore; it
keeps the dot for compatibility with CR-027 and every `[[wiki]]` link. Stated with its
reason rather than hidden behind a rule it breaks — and it is **not** blocked, its
constraint is write-side. Mapped from 9 underscore folders, 7 dot folders,
**77 `.archive` folders** and 2 269 prefixed files.

Dot surfaces are now a **typed category** rather than a list of names — dormant
(`.archive/`, `.notes/`, `.ephemeral/`) versus blocked (`.transcripts/` read-block,
`.handoff/` total block, `.knowledge/wiki/` generated). A new blocked surface inherits the
behaviour without patching each skill.

**Audit lifecycle.** An audit lives in `_inbox/` only while in use; once its decisions are
executed it moves to `_inbox/.archive/`. An audit left in place becomes a competing source
of truth against the working document. `_inbox/` normally holds at most three files —
CR-025 forbids dwelling in principle but never measured it.

**Stale is not junk.** Outdated material is archived; material with no destination goes to
`.ephemeral/` and may die.

**`CONTEXT.md` declared as a root singleton (CR-036).** A vault's `INDEX.md` answers
*where things live* — but nothing answered *what applies right now*: which track is
full-time, which is paused, which commitments are the author's own hands-on work rather
than something they steer, which decisions are open and against what deadline. That
context was spread across a personal goals file, a week-anchor fragment and several
registers, so orienting in it meant reading four places.

`CONTEXT.md` is hand-written, updated when something material changes rather than on a
schedule, and **singleton by the CR-036 test**: there is one context, not one per folder.
It carries the frame, the operative commitments that compete for the same resource, what
is blocked on others, and the open decisions — and defers all counts to their sources,
which always win.

**Contract audit against a live vault, and three fixes.** Running the levelled rules over a
real vault found one **invariant breach** the flat list had never surfaced: a second
`_outbox` inside a folder one level down, holding an unsent package weeks old. The
exemption declared in that folder's `_ops.yaml` covered a *different* path — so nothing
had flagged it. Invariants admit no exception: the package moved to the root `_outbox`,
the folder is gone.

**`.handoff/_archive` is now a declared exception** rather than prose. It keeps its
underscore against *archive-is-always-`.archive`* because `.handoff/` carries a total block
(CR-033) — no skill touches the surface, including to rename it. Exception by necessity;
per CR-037 an exception must be **named** in `exceptions:` to be valid, and it was not.

**The `_inbox` ceiling was a defect in the rule, not the vault.** It counted all files,
then the CR-035 migration legitimately added four system files. Corrected: the ceiling
counts **content** files; declared system files (`_capture.md`, `_frame.md`, `_inbox.yaml`,
`_tasks.yaml`) are infrastructure of the surface, not material passing through it.

**Rule hierarchy and conflict resolution (CR-037).** `vault_conventions.rules` had grown to
**thirteen rules from seven CRs in a flat list** — nothing stated which was stronger, what
happened when two applied to the same surface, or how a tool should weight a violation.

**This failed in practice the same day:** `prefix_conventions` said dot means "not read in
everyday work" while `dot_surface_levels` listed `.knowledge/` as blocked and generated.
Both applied, they disagreed, and the inconsistency shipped in a commit before a reader
caught it.

Three levels, each rule declaring its own: **invariant** (never broken, no exception
possible), **rule** (holds generally; exceptions must be **named** in `exceptions:` and
justified), **guideline** (intended shape, judgement may override). Current split: 6 / 6 / 1.

Conflict order: higher level wins · within a level the more specific wins · a declared
exception beats the rule it exempts, only for the named surface and never against an
invariant · **two rules of equal specificity in conflict is a contract defect — report it,
do not choose.**

A rule without `level:` is a contract defect rather than a guideline by default: the
absence must be loud. This also lets a sweep weight severity **from the contract** instead
of a hardcoded list, and makes exceptions auditable — a second undeclared exception now
shows as a violation instead of passing as precedent.

**File placement classes and singleton surfaces (CR-036).** CR-010 declared *which* files
the suite produces but never **how many of each, or where** — CR-025 answered it for
`_inbox`/`_outbox` alone, leaving everything else to imitation. Counts showed the drift:
**269 `README.md`**, **174 `CHANGELOG.md`** of which **130 sit in folders with no
`.archive/`** — history kept where nothing is retired.

Three classes: **singleton** (exactly one, at root — a second instance is a finding),
**per_folder** (every folder of its kind), **per_boundary** (where the boundary applies).

**The singleton test is principled, not a headcount:** *would a second, folder-scoped
instance defeat the reason the surface exists?* `.handoff/` is outward-facing and holds no
vault links, so a scoped copy would make the snapshot inherit a context it is built to
survive without. `.knowledge/` synthesises across sources, so a scoped copy would prevent
the synthesis that justifies the layer.

**`.transcripts/` flagged** — it carries a read-block and exists in two places; two blocked
surfaces are harder to enforce than one. Not resolved: moving read-blocked content needs
explicit authorisation and must never be done by a skill on its own.

**`_tasks.yaml` as source of truth for the personal working document (CR-035).** Supersedes
CR-022 in part. The markdown working document had grown to 438 lines with a **273-character
median task line** and 56 % non-task content — every row carried task, history, reference
data and reasoning in one sentence, which markdown cannot separate.

Tasks move to `_inbox/_tasks.yaml` (standard v2 schema plus `triage_id` to preserve
external-sync identity); the markdown file becomes a **generated view** showing only
overdue, today, tomorrow, P0/P1 without a date, and the coming week. `_inbox/_capture.md`
is the free-form write path — the original "door, not a dwelling" intent applied to tasks.

Median `task:` length dropped **273 → 87 characters**; the view went **438 → 52 lines**.

### Changed
- `vault_conventions.rules`: `yaml_naming` **replaced** by `prefix_conventions` rather than
  supplemented, so there is one description instead of two overlapping ones.
- `_inbox/<working-doc>.md` declared **generated** — tools must no longer write to it.
- Contract version noted as 3 in the header comment.

## [1.35.1] - 2026-08-28

### Fixed
- **`.handoff/` enforcement completed across the remaining scanning skills (CR-033).** The v1.35.0 contract added the skip to every skill that names an explicit skip-list, but four skills discover files by other means and were still exposed. Frozen handoff snapshots use the same `YYMMDD-` filename prefix as meeting documents, so they matched: **`/preparation` Step 2.5** globs `YYMMDD-*.md` across the vault for lateral mentions — snapshots would have been offered as cross-references, which also violates the rule that snapshots are never referenced from living documents; **`/daily-dashboard`** scans all vault-root subdirectories for `YYMMDD-*.md` on the target date — snapshots would have surfaced as meetings. Both now carry an explicit never-scanned list.

### Changed
- **Boundary documented against the two skills a handoff is most easily confused with.** `/outbox` gains a short section stating the distinction: an outbox item is addressed to a *person* and has a send event, an expected reply and a resolution; a snapshot is addressed to a *future work session*, is never sent, and resolves only when a human opens it. `/tasks` gains the matching rule: a snapshot is context, not intent — it never generates a task, and if its subject should become work the user decides that and the task states the subject in its own words rather than linking the snapshot.

## [1.35.0] - 2026-08-28

### Added
- **`handoff` skill (`/handoff`) — frozen, self-contained context snapshots (CR-033).** A new artefact class for a bounded subject that belongs to *different* work than the conversation that produced it. Previously such material had three bad homes: buried in a meeting summary the next session will not find, copied into a living document that then carries content it does not own, or dropped into `.ephemeral/` where it is allowed to die (CR-024). `/handoff` writes it to `<vault>/.handoff/` as a self-contained document — no wikilinks, no relative paths, readable by someone with no vault access. **The defining property is non-delivery:** an outbox item is sent, a task is executed, a handoff is neither. Nothing in the suite picks it up — no parse, index, summarise, sweep or lint; no task generated, no dashboard entry, never auto-archived. A human opens it and starts new work from it. Isolation is the point: the receiving session gets exactly one subject with no adjacent threads bleeding in. Six contract rules (frozen, self-contained, bounded, not indexed, read on explicit request only, not archived), numbered sections closing with what was still open at capture time, and — where the source was confidential — an explicit boundary block at the top stating what may be shared onward, what may not, and whether the source may be named, so **the constraint travels with the content**. Subcommands: `list`, `read <name>`, `help`. Registered in `ecosystem.yaml` `vault_conventions` with an explicit skip instruction for every other skill. See `docs/proposals/CR-033-handoff-snapshots.md`.

## [1.34.0] - 2026-08-28

### Added
- **External-counterpart preparation (CR-032).** `/preparation` produces a walk-in card plus deep dives (CR-005) — right for internal meetings, insufficient when the counterpart is external. An external preparation asserts claims about a person the author has not verified (mandate, tenure, who they need sign-off from), and being confidently wrong about that is expensive in the room. Six mechanisms now apply **only** to external counterparts (contact folders classified `professional`/`confidential`, `_customers/`, `_partners/`, any first contact): an inline **`[UNVERIFIED]` marker** carrying the CR-015/CR-016 convention into preparation; **source-conflict resolution** that states the conflict, reasons about which value is implausible, and issues an explicit instruction about what may be said in the room; **reliability grading** against comparable prior preparations in the same folder; a per-counterpart **sensitive-ground** negative list (distinct from "if they push back" — that is a response, this is a prohibition); a **branched opening** that may instruct the reader to abandon the prepared agenda when the premise is invalidated; and a **what-they-are-measured-on** line. Additive and scoped — internal preparation is unchanged, no new sections, no second file. Behavioural-signal inference (reading calendar or mail activity as buying intent) is explicitly out of scope. See `docs/proposals/CR-032-external-counterpart-preparation.md`.

## [1.33.3] - 2026-07-27

### Added
- **Triage external-mirror contract (CR-017).** `/inbox triage` gains a documented, optional hook for mirroring the triage doc's *today/tomorrow* items to an external actions surface. Two directions, both human-gated: **push** (preview → one-way additive, deduped, never invents dates) and **reconcile** (read the surface back → *propose* `[x]` on matching triage lines, human approves before any write). The triage doc stays the system of record — no auto-merge, no hidden IDs. Documentation only: this repo ships the contract (gated + secret-free + triage-path read from the registered `file:`), never provider code — the actual integration is a local, per-vault script with its credential and target IDs outside the repo. Absent local config the mirror does not exist. See `docs/proposals/CR-017-triage-external-mirror.md`.

## [1.33.2] - 2026-07-27

### Added
- **`/analytics pipeline` — the outcome layer (CR-031).** The document counts were never the full picture: a meeting's outcomes live in structured files the skill refused to touch. Live use surfaced the gap ("is that actually the full picture?") — answering it required four sources outside the scan: insight entries (`date:`/`type:` in `_insights.yaml`), tasks created (`created:` in `_tasks.yaml` v2), dated CHANGELOG bullets (which carry the original meeting date, making them the best longitudinal outcome proxy), and outbox packages. The new subcommand traces the whole chain **input → meeting docs → outcomes** as a grouped table with quarters as columns, derived ratios (insights/tasks/changelog entries per meeting), and per-day averages including **active-day density** (active days / calendar days — in practice the strongest adoption signal). Reports are two-part by contract: Part 1 Overview (headline totals + numbered interpreted findings + mandatory measurement notes), Part 2 Deep dive (the tables). The "metadata only" principle is refined to **metadata and structured fields**: field-level regex scans only, prose never read — entry contents remain the visualisation app's domain.

### Changed
- **Overview gains active-day density** — active days / calendar days for the current quarter plus files per active day; the gap between files/day and files/active-day shows whether growth comes from busier days or fewer idle days.
- **Classification fixes:** `sammanfattning`/`summary` added to the meeting keyword list (descriptive summary filenames were falling to uncategorized), and dual-mode `agenda`/`facilitator` docs (CR-018) get their own class instead of falling through.

## [1.33.1] - 2026-07-10

### Added
- **Guard modes + rollout to sibling repos (CR-030).** The pre-push hook gains `git config guard.mode secrets-only`: keys/tokens/private-key blocks only, no denylist requirement, no allowlist — the right regime for private repos whose legitimate content includes infra details (internal IPs, credential-idiom documentation) that full mode would false-positive on, which would train `--no-verify` habits (guard theater). A cross-repo audit found zero keys ever committed anywhere; public repos verified clean; private repos now carry secrets-only, public ones full. Any repo installs the shared hook via an absolute `core.hooksPath` pointing at this repo's `scripts/githooks`.

## [1.33.0] - 2026-07-10

### Added
- **Invented-examples allowlist + scheduled repo privacy watch (CR-029).** The inversion that makes "never reveal names in examples" mechanically watchable: real names can never be fully enumerated, but allowed FAKE ones can. New `scripts/privacy-scan.sh` (three layers: built-in secret patterns, private denylist, and **allowlist enforcement** — every name-like token in the repo (contact slugs, dated send-slugs, Name-Name filename pairs, `display_name` values) must fully match `scripts/githooks/allowed-examples.txt`, a public list containing only invented names). The pre-push hook now blocks unknown name-like tokens in outgoing lines even when no denylist knows them; `/ops sweep` check 8 runs the scan weekly over the whole tree via `workflows.sweep.privacy_scan.command`. Baseline run adjudicated every existing token (all confirmed invented) and genericized two remaining real-name example lines the history audit had classed as benign. Adding an allowlist line is a conscious act: confirm invented, never borrowed.

## [1.32.0] - 2026-07-10

### Changed
- **Evolution artifacts are local-only (CR-028).** `/insights propose` and `propose apply` now write to `workflows.knowledge_extraction.evolution.proposals_path` (new config, default `<vault>/.skill-evolution/proposals/`, vault-relative) instead of `docs/proposals/` in this repo — generated proposals derive from vault data and never belonged in public territory. `/insights status` reads the same path. The repo's `docs/proposals/` remains only the generic CR index.
- **Example hygiene:** a history audit (all 43 commits, every added line) found zero secrets ever committed, but a handful of real-looking example slugs in old skill docs; all genericized at HEAD to invented names. The gap they demonstrate — real identifiers a denylist has never heard of pass every regex — is addressed by the mandatory review step below. History rewrite deliberately declined (low sensitivity, high disruption).

### Added
- **Semantic release review (CR-028)** — mandatory RELEASING.md step between commit and push: read the outgoing added lines against the data-classification table and answer three questions (does anything identify a real person/org/deal; does any example look copied rather than invented; does any incident description reveal its source rather than its class). Any yes → rewrite generically + extend the private denylist. The pattern guard is the mechanical floor; this is the judgment layer above it.
- **RELEASING.md: server-side backstop + fresh-clone posture documented** — GitHub secret scanning/push protection as the always-on floor for clones without the local guard; per-clone guard installation called out as a pre-first-push requirement, now also reminded by `/update-skills install` (step 4b) for repos shipping `scripts/githooks/pre-push`.

## [1.31.0] - 2026-07-10

### Added
- **Knowledge synthesis: `/insights synthesize` + the wiki layer (CR-027).** The insights corpus was write-heavy and read-poor: atomic YAML entries accumulated (1,267 across a production vault) but nothing rendered them *readable*. Inspired by the personal-knowledge-OS pattern (capture → LLM-compiled wiki → auto-maintained index the LLM reads instead of RAG), the new subcommand clusters insights **semantically and vault-wide** (deliberately unlike compile Pass 2's mechanical per-folder matching — the first real compile run confirmed token-overlap yields zero promotions on prose summaries) and writes topic-named living articles to `<wiki_path>/<slug>.md`: `sources:`/`updated:`/`related:` frontmatter, synthesized prose with tensions and open questions, Obsidian wikilinks, verbatim quotes with attribution. `<vault>/.knowledge/INDEX.md` is the auto-maintained master index — sessions answering knowledge questions read INDEX first, then only the relevant articles; no retrieval infrastructure. Idempotent refresh from new insights; `<!-- human-edited -->` articles are never auto-updated (flag once, respect the answer); vocabulary is canonicalized at synthesis (known ASR-legacy terms written correctly — source entries untouched); topics matching a registered vertical LINK to it instead of duplicating. New config block `workflows.knowledge_synthesis` (enabled / article_threshold / wiki_path); `vault_conventions` entries for `.knowledge/wiki/` and `.knowledge/INDEX.md`. Shipped as an explicit experiment: the follow-up knowledge-lint CR is gated on the wiki proving useful in practice.

## [1.30.0] - 2026-07-08

### Added
- **Release process + privacy push-guardrails (CR-026).** The vault this suite operates on is live production data while this repo is public — until now the boundary was held by discipline (an ad-hoc leak-scan grep before push), which is a rule without enforcement. Three layers now: (1) **write generic by construction** stays the primary rule; (2) **`scripts/githooks/pre-push`** is the fail-closed backstop — scans every added line in the outgoing range against built-in secret patterns (API-key prefixes, private-key blocks, internal IP literals, credential idioms) plus a **private denylist** of real identifiers read from `git config guard.denylist` (the list lives outside the repo, next to the private CR archive; missing list = push blocked); (3) **`docs/RELEASING.md`** codifies the process — data classification, the per-CR flow (private spec updated *in the same session*), when to push (per release commit, same day), and when to update the webpage/Marvin (on every `core_skills_version` change, nagged by the alignment check / sweep check 8). Install per clone: `git config core.hooksPath scripts/githooks` + `git config guard.denylist <path>`. Verified with pass, fail-closed, and injected-leak tests. `git push --no-verify` remains the documented conscious override.

## [1.29.0] - 2026-07-08

### Added
- **Structure conformance as `/ops sweep` check 9 (CR-025).** CR-010 declared the single-inbox/outbox rule and `/ops status` got a health step for it — which failed in practice for the two familiar reasons: no scheduled reader, and exact-name matching while reality drifts through *variants*. A live vault was found carrying an active stray org-level `_outbox/` (invisible to `/outbox list`, so the central pending list lied), a dead `.inbox` scaffold, and an `_outbox-archive` variant — two of the three invisible to the exact-match check. Sweep check 9 now scans with a **fuzzy matcher** (`_inbox`/`_outbox`/`.inbox`/`.outbox`/`*inbox*`/`*outbox*`/localized `inkorg*`/`utkorg*`, case-insensitive), flags everything except the vault-root pair including empty scaffolds, and offers fixes routed through the normal `/inbox`/`/outbox` flows (never auto-merged). New `workflows.sweep.structure_exemptions` config records deliberate exceptions once — exempt paths report as a one-line note, not a finding. The `/ops status` vault-health step is upgraded to the same matcher + exemption list.

## [1.28.0] - 2026-07-08

### Added
- **File-drop lifecycle: `_inbox/.files/` (CR-024).** `_inbox` is a door, not a residence — and until now the door only accepted text and audio. `.files/` generalizes the `.audio/` pairing pattern to any **input file with a vault destiny** (a PDF to summarize, a CSV that becomes project data, media that will accompany content): drop the file, `/inbox` registers a paired stub with a type-based classification guess, processing runs the right skill with the file as input, and the source file **moves with its output** — to the target folder's `.attachments/` or to `_inbox/.archive/.files/`. Orphan file drops surface in `/inbox status` like orphan audio. Size guard: >~25 MB files are flagged and offered process-in-place + reference-stub archiving instead of moving blobs through synced folders. New `vault_conventions` entries for `_inbox/.files/` and `.ephemeral/`; `contract_version` stays 2.
- **`.ephemeral/` contract (CR-024).** The counterpart boundary, now stated in ops-base: `.ephemeral/` is the one never-delete exception — disposable working material with **no vault destiny**, never input to vault content, never referenced from vault files, aged out by sweep check 6 after 14 days. The routing rule becomes a one-second conscious choice: *vault destiny → `_inbox/.files/`; no destiny → `.ephemeral/`.* Anything in `.ephemeral/` that turns out to matter exits through `_inbox/.files/` like any other input.

## [1.27.0] - 2026-07-08

### Added
- **Contract alignment as `/ops sweep` check 8 (CR-023).** `ecosystem.yaml` (CR-010) made the suite's contract explicit and `check-ecosystem-alignment.sh` made drift detectable — but the script only ran when a human remembered it, and external components sat six releases behind while it reported `[DRIFT]` to nobody. Sweep now runs the configured alignment command (`workflows.sweep.alignment_check.command`, new optional config block) read-only and reports each `[DRIFT]` component with expected-vs-actual version plus a pointer to the update runbook (now documented in the script header). `[SKIP]` verdicts (unreachable mount, missing checkout) are reported as *unverified*, not clean — an unreachable component is itself a finding and has previously hidden drift. Absent config → check skipped silently (maintainer tooling, not consumer-vault behavior). No auto-fix: cross-repo version references and live deploys stay human-confirmed. The alignment command remains the single source of truth for the component list; sweep is the scheduled reader that guarantees its output is seen.

## [1.26.1] - 2026-07-07

### Changed
- **`<!-- secret-ok -->` opt-out for the triage no-secrets rule (CR-022 amendment).** The owner may deliberately keep a credential inline in the triage doc; a line ending in `<!-- secret-ok -->` records that decision, and `/inbox triage refresh` + `/ops sweep` skip it instead of re-flagging every run (mirrors the `<!-- no-normalize -->` convention). Flag once, respect the answer. Surfaced immediately by live usage: the rule as shipped would have nagged on credentials the owner had explicitly chosen to keep.

## [1.26.0] - 2026-07-07

### Added
- **Triage working-surface contract (CR-022).** `docs/schemas/inbox.md` gains a "Working documents & the triage surface" section: a working doc lives in `_inbox/`, registered with `type: working_doc` / `status: keep` / tag `do-not-process`, exempt from the capture lifecycle; the **triage doc** (at most one per vault) is the canonical case — a rolling human sorting surface with a defined section vocabulary (INKORG/INBOX, PRIO/NOW, DENNA VECKA/THIS WEEK, SENARE/LATER, UPPFÖLJNINGAR/FOLLOW-UPS, BESLUT/DECISIONS), bracket-tagged checkbox bullets (`[Möte · X]`), a week anchor, a KLART done-archive, a graduation rule (one item = one home: a bullet that becomes real folder work MOVES with a link, never forks), and a no-secrets rule. Design principle stated in every touched skill: **skills adapt to the triage doc; the triage doc never adapts to skills** — it stays markdown, human-ordered, never auto-processed. Motivated by live usage where a hand-rolled triage file organically became the personal system of record while the structured root task file rotted.
- **`/inbox triage [refresh|status]` (CR-022).** Mechanical upkeep only, explicitly invoked: `refresh` updates the week-anchor date/week tokens (standing context preserved verbatim), moves `[x]` bullets to `_inbox/.archive/YYMMDD-triage-klart.md`, reports INKORG items unsorted >7 days, and flags plaintext-credential lines (report, never auto-remove). Never reorders, rewords, or re-buckets — sorting is the human's thinking step. `/inbox process all` now explicitly skips working documents.
- **Preps read the triage doc (CR-022).** `/preparation` (new Step 2.4) and `/ops prepare` (Step P1) scan the triage doc for open bullets whose bracket-tag second segment resolves to the meeting's contact/participants, pull them into agenda/open-actions, and stamp each pulled bullet `→ i prep YYMMDD` — the only write allowed, one-line suffix. Closes the previously by-hand collection loop.
- **Triage as task-import target (CR-022).** `/transcript` Step 4 and `/ops` Step 9 task import offer "append to triage INKORG (with source link)" for personal/ad-hoc action items with no natural org/project folder — matching observed behavior instead of feeding per-folder ledgers that go stale. One item = one home.
- **`/daily-dashboard` Triage section (CR-022, read-only).** Links the doc, inlines open PRIO items, shows DENNA VECKA bucket counts and INKORG count. Same read-only principle as Rolling Plans; applies in both generic and org mode. Omitted entirely when no triage doc is registered.
- **`/ops sweep` seventh check: triage hygiene (CR-022).** INKORG unsorted >7 days, unarchived `[x]` items, stale week anchor, plaintext-credential lines; offered fix is `/inbox triage refresh`.

## [1.25.0] - 2026-07-07

### Added
- **Filename slug policy (CR-021).** ops-base General Naming Rules is now an explicit slug contract: keep å/ä/ö in filenames (never transliterate, never digit-substitute, never mix policies within one filename), `YYMMDD-` prefix always (ISO only via explicit folder CLAUDE.md), mandatory role keyword (`samtal`/`förberedelse`/...) so file role stays machine-readable, names Capitalized / other tokens lowercase. `/transcript`, `/preparation`, and `/ops` now run the CR-007 driftword check against the *slug* before saving -- filenames were the one surface CR-007 never covered. New `/ops normalize --filenames` opt-in backfill renames drifted files and rewrites inbound references (CHANGELOG, README, supersede stamps, wikilinks); dry-run first. Existing files are never renamed implicitly.

## [1.24.0] - 2026-07-07

### Added
- **`/ops sweep` -- closure/staleness audit (CR-019).** Skills append reliably but never reconcile; audits keep refinding the same closure-debt classes. New read-only subcommand detects all six in one pass: (1) index lag (README vs newest file/CHANGELOG head), (2) ledger rot (stale `_tasks.yaml` with open tasks; `_insights.yaml` never/stalely compiled via the CR-020 `last_compiled` stamp), (3) migration corpses (live-looking artifacts superseded by a move), (4) outbox aging (sent-but-unarchived, manifest-less, >30d pending), (5) sync duplicates (`* 2.*` with base present -- report only, never auto-delete), (6) unrouted residue (`unsorted/`, stale `.ephemeral/`, root paste files). Report-only; every fix is offered, none applied automatically. Suitable for a weekly scheduled run delivering into `_inbox/` triage.
- **Retirement Convention in ops-base (CR-019).** Any relocation of a living artifact MUST leave a tombstone at the old path (`> **Flyttad (YYMMDD):** se [new-path]`), log the move in CHANGELOG, and update stale pointers the skill created. Prevents the migration-corpse class at move time; `/ops sweep` catches violations after the fact.
- **`/outbox archive --all-sent` (CR-019).** Batch mode over the single-folder archive flow: collect all `skickad` items, confirm the selection up front, run the standard steps per folder (per-folder judgement calls still asked individually), one summary report. This is the fix `/ops sweep` offers for outbox aging.

## [1.23.0] - 2026-07-07

### Added
- **Template contracts + shape lint (CR-018).** Recurring meeting series erode format by *silent template forking* -- one deviating file re-seeds the whole series, and every later file is internally consistent, which is why per-file review never catches it. New `workflows.meeting_templates` registry (org or folder config) declares per-series shape contracts (`match` glob, `headings`, `action_table`); a `default` contract (CR-006 canonical order + strings table headers) always applies. `/ops` and `/transcript` verify three things as the last pre-save step: H2 heading sequence, action-table header row, and the empty-Beslut marker (previously mandated but never checked). `mode: warn` (default) saves + reports the diff + logs an `edge_case`; `strict` asks first. Deliberate format changes are made by editing the contract -- an accidental fork becomes an explicit, reviewable decision.
- **`/ops lint <folder>` (CR-018).** Read-only contract check across existing files, grouped by series and first-deviating date ("this series forked at YYMMDD"), with the two resolutions spelled out: amend the contract (accept) or fix the files.

## [1.22.0] - 2026-07-07

### Added
- **People roster (CR-017).** New optional `people:` block in ops-config (org and folder-local): `canonical` + `aliases` + `role` for recurring persons who are neither in `team[]` nor have a `_contacts/` folder -- exactly the long tail ASR garbles most. Name resolution in `/transcript` and `/ops` now checks the roster first; the CR-016 known-entity set includes it.
- **Committed-spelling consistency check (CR-017).** CR-016 verifies names against *configured* entities but has no memory of what the pipeline previously committed -- so an ASR variant of an established name sails through as a plausible new name, and one person ends up spelled three ways across consecutive documents of the same series. New pre-save check in `/transcript` (and `/ops`, including before CHANGELOG/README writes -- changelogs are how misspellings propagate): scan the target folder's ~10 most recent files + CHANGELOG for near-miss variants (edit distance ≤2, initial-letter swaps) of draft names; use the established spelling when it resolves via a roster, flag both forms (`"X" -- tidigare skrivet "Y" (YYMMDD) -- samma person?`) when it doesn't, never silently introduce a third variant. The same mechanism covers *contextually anomalous domain terms* (a real-word ASR mishearing invisible to both spellcheck and entity matching). Recurring flags for one name = the signal to add it to the roster. Logs `edge_case` on flag, `correction` on user fix.
- **`/ops normalize --names` (CR-017).** Opt-in backfill applying the roster (aliases → canonical) across a folder's files and CHANGELOG, each substitution confirmed.

## [1.21.0] - 2026-07-07

### Changed
- **Insights privacy rule formally retired (CR-020).** The 2026-04-07 audit retired the "never include personal/company names in `summary`/`rationale`/`tags`" rule, but the skill text still mandated it -- leaving it neither enforced nor removed while ~10% of a real corpus "violated" it. The rule is now replaced everywhere (`/transcript` Step 3.5, `/insights`, `/ops` Step 5.5) by a *reusability preference*: names allowed; prefer name-free `summary`/`tags` when the insight generalizes; names in `rationale` always fine (quote attribution lives there by design); classification-aware rendering stays with the visualisation app (CR-009).
- **`quote` formally canonized as an insight type (CR-020)** in the `/insights` quick-reference and lifecycle rules (it was already in `/transcript` Step 3.5; it is exempt from rule-promotion). `/insights reprocess` now creates new files as `version: 2`, not `version: 1`.

### Added
- **Write-time vocabulary guard (CR-020).** Before any `_insights.yaml` write (all writers): `type` must be canonical (known past drift -- `decision-pattern`, `principle`, `outcome`, `design` -- maps to nearest canonical), `confidence` limited to `hypothesis|rule` (a re-confirmation bumps `confirmation_count`, it does not rename confidence to `high`/`confirmed`), dates YYMMDD never ISO, integer ids with `next_id` maintained, max 5 tags. Fix silently when unambiguous, ask when not.
- **`/insights normalize [path] [--apply]` (CR-020).** One-shot schema migration for drifted files (dry-run by default): ISO dates → YYMMDD, string ids → integers (old id kept as `legacy_id`), missing/non-canonical types inferred/mapped (tagged `type-inferred` when ambiguous), non-canonical confidence remapped, legacy field shapes (`added:`, string `source:`) restructured, `superseded_by`-vs-`status` inconsistencies fixed, missing `version`/`next_id`/`last_updated` added, tags capped at 5. Structure and vocabulary only -- entry text stays untouched (content remediation remains `/ops normalize`).
- **Compile freshness stamp (CR-020).** `/insights compile` now writes top-level `last_compiled: YYMMDD` into every file it scans (additive; older readers ignore it), making "compile never ran / is stale" detectable by `/insights status` and `/ops sweep`. Insights corpora are write-heavy by design; the stamp keeps the synthesis half of the loop honest.

### Rationale
- All five 2026-07-07 CRs (017-021) come from a comprehensive private audit of ~4 months of heavy skill usage across a production vault (~250 skill-produced files/month). Recurring result: capture-side conventions (CR-006/007/015/016) held at near-100% in new output, while the failure modes moved to name canonicalisation across documents, silent template forking in recurring series, schema drift from pre-CR writers, and closure loops that never ran. CR specs with vault-specific evidence are tracked privately outside this repo (see docs/proposals/README.md).

## [1.20.1] - 2026-06-27

### Added
- **`/transcript` Step 2.5: silent raw-transcript archive.** The skill now always saves the verbatim raw input to a central `.transcripts/` folder in the vault root (sibling to `_inbox`/`_outbox`), as plain readable markdown named `YYMMDD-...-raw.md` (mirrors the summary stem). The raw file carries frontmatter linking back to the summary and every file the run created (`summary:`, `created_files:`); the summary gets a discreet `raw:` back-link. Multiple recordings merged into one summary are stored in the same raw file with separators. A **read-back lock** governs the folder: files in `.transcripts/` are never read back, quoted, re-summarized, or fed into `_insights.yaml`/summaries unless the user explicitly asks for the raw material. The CHANGELOG never links the raw file. Step 0.5's insights-walk now skips `.transcripts/` alongside `.archive/`/`clones/`. Purely additive doc behaviour — no schema change.

## [1.20.0] - 2026-06-05

### Added
- **Proper-noun verification (CR-016).** New "Proper-noun verification" section in `skills/transcript/SKILL.md`. Name Resolution corrects the *spelling* of names it can match; CR-016 covers the opposite failure -- a proper noun the transcriber garbled into a *plausible* token that matches nothing and reads fine. The skill now: (1) builds a known-entity set from `team[]`, `_contacts/*/_meta.yaml` (`display_name`/`aliases`/`company`), `terminology[].term`, and the filename; (2) resolves each person/company name to canonical spelling if matched, else marks it `Name?` or collects it into a `> ⚠ Namn att verifiera:` note instead of committing it as fact; (3) states the failure-mode principle -- invisible plausible substitutions cost more downstream than obvious garble, so scrutiny goes to proper nouns and semantic swaps; (4) logs an `edge_case` when flagging and a `correction` on user fix. No-op when every name resolves.
- **Step 4.5 `edge_case` example extended (CR-016):** "unresolved proper noun flagged for verification" added to the example list.
- **Preparation ASR-vocabulary hint (CR-016).** New one-line `{strings.preparation.recording_names}` hint in the `/preparation` walk-in card, reusing the entities the Step 2.5 cross-context scan already gathers -- suggests putting key proper nouns in the calendar event title so the transcriber's ASR has the vocabulary. New `preparation.recording_names` strings key in both language blocks of `skills/ops-config/base.yaml`.

### Rationale
- Surfaced from an independent field comparison of two Swedish transcription tools across four real meetings. Its thesis matches the skill's: intelligence lives downstream, so transcript word-fidelity is the axis that matters because errors propagate. The comparison validated CR-015 (merged-readable-paragraph output is the undiarized case the skill already fails safe on) and surfaced proper nouns as the one place tools fail and the skill lagged. CR-016 extends CR-015's fail-safe philosophy from owners to all proper nouns. Tool-specific branching and two-transcript reconciliation were deliberately left out (see `docs/proposals/CR-016-proper-noun-verification.md`). Prompt-only and additive; no contract/schema change.

## [1.19.0] - 2026-06-05

### Added
- **Undiarized-transcript owner safety (CR-015).** New "Speaker attribution & undiarized transcripts" section in `skills/transcript/SKILL.md`. Name Resolution fixes spelling but not *who said what*; many sources (Deep Thought paste, raw recorder export) arrive as a single unlabeled stream where action-item ownership can only be inferred. The skill now: (1) detects diarized vs undiarized input before assigning owners; (2) on undiarized input treats every owner as a hypothesis and fails safe -- writes `?` / `Name?` instead of a confident guess from a first-person cue; (3) runs a final owner self-check on the `Nästa steg` table before save; (4) logs undiarized input as an `edge_case` and user owner-corrections as `correction` (Step 4.5) so `/insights compile` can cluster the pattern.
- **Action Item Table rule extended (CR-015):** an owner cell holds a bare name only when an identifiable speaker explicitly takes the action; otherwise `?`. Consistent with the binary `?` rule already in CR-006.
- **Step 4.5 `edge_case` example extended (CR-015):** "transcript lacks speaker labels (owners inferred)" added to the example list.

### Rationale
- Surfaced from real use: a Deep Thought transcript with no speaker labels produced two confident-but-wrong action-item owners that the operator had to correct, while a Fathom recap of the same meeting (which has audio diarization) got them right. The gap was not format -- the owner/prio/deadline table already exists -- but that the skill committed to inferred owners with no confidence signal. CR-015 makes the skill fail safe instead. The durable root fix (diarized input) is noted in-skill but is an input-pipeline choice, not a skill change. Prompt-only and additive; diarized transcripts are unaffected.

## [1.18.0] - 2026-06-04

### Added
- **Rolling plans -- participant-triggered per-axis living docs (CR-014).** New optional `workflows.rolling_plans` config block: a list of living, shareable per-axis planning documents (`path`, `axis`, `participants`, optional `language`/`status`/`trigger`). Rolling plans are the **participant-keyed** counterpart to `verticals` (topic-keyed): a vertical is topic-longitudinal, a rolling plan is relationship/axis-longitudinal ("what's on now / next / later, and who owns what" for the workstream a 1-on-1 partner owns).
- **`/ops` Step 9 -- "Update Rolling Plans" post-processing.** After a meeting whose participants intersect a plan's `participants` (resolved via the standard name-resolution algorithm), /ops offers a yes/no/select update -- move completed rows into the just-written summary, add new NOW items in the owner column, reflect decisions. Missing target files are offered a scaffold from the new template instead of erroring. Enforces the golden rule **one item = one owner = one doc** and keeps each plan's "Sister documents" cross-link block consistent.
- **`/daily-dashboard` -- read-only "Rolling plans" surface.** In org mode, when `workflows.rolling_plans` is configured, the dashboard links each plan (with its `axis`) and optionally pulls the plan's NOW block. Read-only: the dashboard never maintains rolling plans (that is `/ops`).
- **Rolling-plan template** `skills/ops-config/templates/rolling-plan.md` -- generic, placeholder-driven scaffold used by the /ops scaffold path.
- **`vault_conventions` entry (CR-014):** `<folder>/rolling-plan-<facilitator>-<partner>.md` registered in `ecosystem.yaml` per_folder (writers `/ops`, user; readers `/ops`, `/daily-dashboard`, user).

### Documentation
- `skills/ops-config/schema.md` -- new "Rolling Plans (CR-014)" section (schema + field table + example).
- `skills/ops/SKILL.md` -- `workflows.rolling_plans` added to "What Config Controls"; `/ops status` now reports registered rolling plans (count + axes).

### Rationale
- Surfaced from real use: recurring 1-on-1s accumulate per-relationship, cross-meeting state that meeting summaries (point-in-time), verticals (topic), and `_tasks.yaml` (flat ledger) don't capture. Operators were hand-maintaining `rolling-plan-<facilitator>-<partner>.md` files and they drifted (same item in two plans, summaries updating while plans went stale). Reusing the verticals mechanism with a participant trigger makes the update a prompted, governed step instead of a manual habit. Fully config-driven and additive: an org with no `rolling_plans` sees no change.

## [1.17.1] - 2026-05-25

### Added
- **`/ops` Step 9 -- post-meeting priorities artifact (opt-in).** New subsection "Generate Post-Meeting Priorities Artifact" in the Post-Processing step. Produces a slim `YYMMDD-priorities-post-<meeting-type>.md` file alongside the comprehensive meeting summary, capturing the facilitator's working list (the team's actual day-to-day artifact) separately from the archive (the comprehensive summary). This makes post-meeting outputs symmetric with the pre-meeting dual mode (`agenda` + `facilitator`): pre-meeting has a two-layer pair, post-meeting now also has a two-layer pair.
- **`workflows.post_processing.priorities_artifact.enabled`** config key (default `false`, opt-in per org or project). When true, /ops generates the slim priorities artifact after the comprehensive summary is written. Source priority: (1) facilitator's post-meeting message verbatim if present, (2) top items from the action-items table if not, (3) skip if neither yields a clear priority list -- producing a slim doc that just restates the action-items table adds no value.

### Documentation
- **Symmetric layering documented.** ops/SKILL.md now describes both the pre-meeting two-layer artifact (single vs dual `preparation_mode`) and the post-meeting two-layer artifact (comprehensive summary + optional priorities) as symmetric patterns. Critical rules: bidirectional cross-references, anti-bloat (>1 page = trim), slim artifact is the working list (not a second summary), comprehensive stays comprehensive.
- **What Config Controls** table updated to reflect that `workflows.post_processing` now covers task import, dashboard refresh, AND the optional priorities artifact.

### Rationale
- Distinction surfaced from real use: comprehensive standup summaries are correct as archive material (searchable, traceable, complete) but too dense to be the team's working list. Facilitators were already producing a slim priority list (email / Teams message) as the de-facto working layer. The skill now formalizes this layering so the working list is captured as its own artifact, not buried inside the archive.

## [1.17.0] - 2026-05-10

### Added
- **CR-013: hypothesis → rule lifecycle for `_insights.yaml`.** New optional `confidence` field on insights (`hypothesis` | `rule`, default `hypothesis`), plus `confirmation_count`, `confirmations[]`, and `contradicted_by[]` for source-traceable promotion and demotion. `/insights compile` now runs three passes: (1) existing `skill_pattern` compilation, (2) hypothesis-to-rule promotion when ≥3 semantically similar hypotheses cluster in one folder, (3) rule-to-hypothesis demotion when a `correction` contradicts a rule. `/ops` and `/transcript` gain a Step 0.5 that walks the CWD's `_insights.yaml` chain, filters to `confidence: rule`, and injects up to 20 rules as a working-context preamble before the main step. `/insights status` extended with a "Confidence Lifecycle" section. Schema bumped: `schemas.insights: 1 → 2` in `ecosystem.yaml`. Bump is additive — schema v1 readers (e.g., current `core-skills-visualisation` build) ignore unknown fields.
- **`workflows.knowledge_extraction.evolution.demote_on_contradiction`** (default `true`): controls whether `/insights compile` runs the demotion pass.

## [1.16.7] - 2026-05-06

### Fixed
- **`md2pdf` Homebrew library discovery in non-interactive shells:** Added `_bootstrap_homebrew_paths()` that runs before `weasyprint` and `markdown` are imported. It prepends `/opt/homebrew/bin` (and `/usr/local/bin`) to `PATH` and `/opt/homebrew/lib` (and `/usr/local/lib`) to `DYLD_FALLBACK_LIBRARY_PATH` when those directories exist on the system. Two failure modes this resolves: (1) `weasyprint` import crashing with `OSError: cannot load library 'libgobject-2.0-0'` because the native pango/glib stack lives in `/opt/homebrew/lib` and dyld can't find it, (2) `mmdc` running but its internal `node` lookup failing with `env: node: No such file or directory`. Both happen when md2pdf is invoked from SSH sessions, cron jobs, or any shell where `~/.zshrc` hasn't extended PATH. Bootstrap is idempotent and a no-op on systems without those Homebrew prefixes.
- **`md2pdf` mmdc binary discovery:** New `find_mmdc()` looks for `mmdc` on `PATH` first, then falls back to common Homebrew locations (`/opt/homebrew/bin/mmdc`, `/usr/local/bin/mmdc`), Linux package locations, npm-global, and the highest-versioned nvm-managed Node install. Fixes the case where the binary is installed but unreachable via `shutil.which`.

## [1.16.6] - 2026-05-06

### Added
- **`md2pdf` autolinking of bare URLs:** `pymdownx.magiclink` extension is now loaded when `pymdown-extensions` is available, so raw URLs in prose become real clickable `<a>` elements in the PDF (previously they rendered as plain text). Hard-coded `[text](url)` syntax is still respected. Also avoids smartypants mangling URL fragments (which previously turned `--` inside long URLs into em-dashes).

### Changed
- **`md2pdf` task-list indentation:** `ul.task-list` and `li.task-list-item` no longer override `padding-left: 0`; task lists inherit the same `padding-left: 20pt` as regular `ul`/`ol`, so checkbox items align with sibling bullet lists in the same document.
- **`md2pdf` task-list checkbox layout:** Switched from `text-indent: -1.4em` to `display: inline-block` on the checkbox so it stays inline with the task text on a single line (previous version pushed the text to the next line).
- **`md2pdf` link CSS:** `a` elements now have `overflow-wrap: anywhere` and `word-break: break-word`, allowing long URLs to wrap across lines while keeping the entire URL as one clickable anchor.

## [1.16.5] - 2026-05-06

### Added
- **`md2pdf` task-list rendering:** `pymdownx.tasklist` extension is now loaded when `pymdown-extensions` is installed, so `- [ ] item` / `- [x] item` render as proper checkboxes (with custom_checkbox styling) instead of a bullet followed by a literal `[ ]` glyph. CSS in `style.css` removes the list bullet on `ul.task-list`, indents items uniformly, draws a square checkbox with a checked-state ✓ glyph, and keeps spacing consistent with regular bullet lists. Falls back gracefully (literal `[ ]` text after bullet, same as before) if `pymdown-extensions` is not installed -- the build always succeeds. Documented under Dependencies with `pip install pymdown-extensions` added to the first-time setup.

## [1.16.4] - 2026-05-06

### Added
- **`md2pdf` markmap mindmap support:** New ` ```markmap ` fenced block translates to a Mermaid mindmap before rendering. Heading levels (`#`, `##`, `###`) and bullets (`-`/`*`) become indentation -- `#` is root (depth 0), `##` is depth 1, etc. Bullets inherit their parent heading's depth and add their own indent (each two spaces / tab = one extra level). Optional `depth=N` fence attribute (e.g. ` ```markmap depth=2 `) prunes nodes deeper than N -- use a small depth for executive summaries, omit (or use a higher value) for detailed maps. The Mermaid renderer is reused, so `mmdc` is now required for both `mermaid` and `markmap` blocks (still optional, with a plain code-listing fallback if `mmdc` is missing).
- **`md2pdf` lazy-list normalization:** New pre-processor inserts a blank line before a list that follows a paragraph without one, matching GitHub Flavored Markdown / Obsidian behavior. Python-markdown is strict CommonMark and requires the blank line; authors used to GFM/Obsidian style routinely hit this and got bullet items rendered as inline paragraph text. Fix is idempotent (already-separated lists unchanged) and skips fenced code blocks so bullets inside `pre`/`code` are preserved as-is. Applies to both `-`/`*` bullets and numbered lists.

### Changed
- **`md2pdf` mermaid/markmap fence regex hardened:** Anchored to start-of-line so inline backticks in prose (e.g. ` ```markmap` ` mentioned in a sentence) no longer trigger block extraction.
- **`md2pdf` SKILL.md:** Documents the new mindmap support, `depth=N` attribute, lazy-list normalization step, and adds explicit install commands (`pip install weasyprint markdown` + `npm install -g @mermaid-js/mermaid-cli`) under Dependencies with a note that `mmdc` is required when using `mermaid` or `markmap` blocks.

## [1.16.3] - 2026-05-06

### Added
- **`outbox` skill (`/outbox`):** Lifecycle management for outgoing material in `<vault>/_outbox/`. Subcommands: `list` (default, scans `_outbox/*` and classifies items as PENDING / RESOLUTION-READY / DRAFT / WITHOUT MANIFEST based on `_manifest.md` state), `archive <folder>` (moves a resolved outbox folder into the relevant `_contacts/<contact>/YYMMDD-<theme>/` -- stripping the contact-name prefix that becomes redundant inside the contact's own folder, updating manifest `Status:` to `arkiverad`, appending `## Tidslinje`, adding a CHANGELOG entry, rewriting `source:` paths in `_tasks.yaml`, and searching the vault for stray references to the old path), `status` (alias for `list`), `help`. Closes the lifecycle gap where outbox material was sent and replied to but never returned to the contact's own folder -- the search target six months later is the contact folder, not a central archive. Multi-contact fan-out (ambassador-style) is detected and asks the user for resolution strategy (duplicate to each, or keep central). Never auto-completes tasks -- archiving is a file operation, not a workflow decision. Manifest schema clarified: an item is "resolution-ready" when `Status: skickad ...` AND all `Svar förväntas på` items are checked AND `Utfall` is populated. Registered in `ecosystem.yaml` skills registry under `user_invocable` with `Utility` badge.

## [1.16.2] - 2026-05-04

### Changed
- **`/ops prepare` dual-mode clarified to two-layer model.** Earlier framing in 1.16.1 implied the facilitator file was a superset (full prep + extras) and the agenda file was a stripped-down subset. Operational use surfaced that this inverts the natural workflow: the team-facing document should be the full standup-style prep (status overview, blockers, action items, agenda) -- exactly what prior single-mode prep files in the same folder look like -- and the facilitator file is a *separate* private add-on layer that contains only the additional content that would change behaviour or expose sensitive context if shared. The agenda is now the primary prep; the facilitator file is the extra. Updated: `skills/ops/SKILL.md` -- Preparation modes section rewritten with explicit "agenda file contains" / "facilitator file contains" lists and a "if it fits both, keep in agenda" rule; Step P5 reordered so agenda is generated first by mirroring prior-day single-mode prep, then the facilitator layer is derived; cross-reference rule restated (facilitator → agenda only, never the other direction). No config or filename changes -- this is a documentation/behaviour clarification only.

## [1.16.1] - 2026-05-04

### Added
- **`/ops prepare` dual-mode for group meetings:** New `meeting_types[<type>].preparation_mode` config in `_ops.yaml` (top-level, sibling to `workflows`). Values: `single` (default, one `preparation`/`förberedelse` file) or `dual` (two files: `YYMMDD-facilitator-*.md` private + `YYMMDD-agenda-*.md` shareable). Use `dual` for group meetings where the facilitator needs private notes (deflection strategies, time-boxing, sensitive probes, policy reminders) that must NOT appear in the document shared with attendees. The agenda file does not advertise that a facilitator file exists. Updates: `skills/ops/SKILL.md` (Step P5 filename resolution, Step P6 lifecycle, supersede step accepts all four filename patterns), `skills/ops-config/schema.md` (new top-level `meeting_types` section). Single-mode default preserved -- only meeting types explicitly listed with `preparation_mode: dual` get the new behaviour. NOTE: dual-mode filenames are English-only for now (`facilitator`, `agenda`); Swedish localisation deferred.
- **Marvin filename pattern recognition for dual-mode (paired with above):** `parsers/activity.py` `TYPE_KEYWORDS` adds `facilitator` and `agenda` -> `preparation` bucket. `static/js/dashboard.js` and `static/js/documents.js` recognise dual-mode files in thread keying, participant extraction, and prep-dot rendering. Marvin must ship together with this core-skills release.

## [1.16.0] - 2026-04-29

### Added
- **`vault_conventions` block in `ecosystem.yaml` (CR-010):** Authoritative declaration of every file the suite produces or consumes in a user's vault. Each entry documents path pattern, purpose, schema link (when one exists), writers, readers, and lifecycle. Three sections: `vault_root` (7 entries -- `_inbox/`, `_inbox/.audio/`, `_outbox/`, `_config/`, `_analytics/`, `_tasks.yaml`, `_Dashboard.md`), `per_folder` (6 entries -- `_ops.yaml`, `_tasks.yaml`, `_insights.yaml`, `_meta.yaml`, `_summary.yaml`, `CHANGELOG.md`), and `rules` (5 cross-cutting rules covering vault root resolution, inbox/outbox singularity, config resolution order, naming conventions, audio/transcript pairing). Bumps `contract_version` 1 -> 2; additive change, contract_version=1 clients ignore the new block. Marvin, Trillian (vault-pulse), and future external skills should read this as the contract.
- **Formal `_inbox/` schema at `docs/schemas/inbox.md` (CR-012):** Canonical contract for `_inbox/<id>.md` frontmatter (id, created, classification, status, source, target_skill, target_folder), `_inbox/.audio/<id>.m4a` pairing-by-basename rule, and lifecycle states (`pending` -> `processing` -> `processed` -> archived). Identifier format upgraded to `YYMMDD-HHMMSS[-slug]` for second-level uniqueness across multiple producers (Trillian writes audio, Deep Thought writes transcript later). `_inbox.yaml` is now a derived index, rebuilt from frontmatter; frontmatter wins on disagreement. Schema bump for `_inbox.yaml`: v1 -> v2 (auto-rewritten lazily on first `/inbox` run). Hidden `.audio/` subfolder convention keeps audio out of Obsidian sync by default. Producers: `/inbox`, Trillian, Deep Thought, Marvin web UI. Cross-linked from `vault_conventions` block.
- **Vault health check in `/ops status`:** New step that surfaces drift from the `vault_conventions` contract -- stray nested `_inbox/` or `_outbox/` folders (violates `rules.single_inbox_outbox`), unparseable `_ops.yaml` files, ops-aligned folders missing their `_ops.yaml`, and residual legacy `*-ops-config` skill installs (CR-011 deprecation). Silent when clean (one-line `Vault health: OK`); expands into a numbered warning list otherwise. Implements the runtime side of the CR-010 contract -- the rule was already in `ecosystem.yaml`, this surfaces violations.

### Changed
- **`/ops` config resolution chain rewritten (CR-011):** Org configs now live in the vault folder they describe (`<vault>/<org>/_ops.yaml`) instead of dedicated skill repos. New chain: (1) project-level `.claude/ops-config.yaml`, (2) folder-local `_ops.yaml` walked up from CWD until vault root, (3) vault-wide `<vault>/_config/base.yaml`, (4) skill `base.yaml`. Vault root is detected by `_inbox/`, `_outbox/`, or `.obsidian/` markers, or `VAULT_ROOT` env override. Updated in `skills/ops/SKILL.md`, `skills/ops-base/SKILL.md`, `skills/ops-config/README.md`. Replaces the pre-v1.16.0 step "Org config skill: `~/.claude/skills/{org}-ops-config/{org}.yaml`".

### Deprecated
- **`*-ops-config` skill-based discovery (CR-011):** `~/.claude/skills/acme-ops-config/`, `bravo-ops-config/`, `delta-ops-config/` are deprecated. They remain as fallback (between vault-wide and skill defaults) with a one-time per-session deprecation warning. Removed entirely in v1.17.0.

### Migration
- **CR-011 -- migrate org configs to vault folders.** One-time per machine:
  1. `cp ~/repos/acme-skills/skills/acme-ops-config/acme.yaml <vault>/acme/_ops.yaml`
  2. `cp ~/repos/bravo-skills/skills/bravo-ops-config/bravo.yaml <vault>/bravo/_ops.yaml`
  3. `cp ~/.claude/skills/delta-ops-config/delta.yaml <vault>/delta/_ops.yaml`
  4. Verify each new file parses: `python3 -c "import yaml; yaml.safe_load(open('<vault>/acme/_ops.yaml'))"`
  5. `cd <vault>/acme && /ops status` -- confirm team, language, terminology match the originals
  6. Repeat step 5 in `<vault>/bravo/` and `<vault>/delta/`
  7. **Do not** delete the old `*-ops-config` skill files yet -- they still work as fallback until v1.17.0
  
  After migration, new orgs (e.g. `delta`, `echo`) get a config by dropping a `_ops.yaml` in their vault folder -- no skill repo, no symlink, no SKILL.md.

## [1.15.10] - 2026-04-16

### Fixed
- **`md2pdf` orphaned headings fix:** Headings (h2/h3/h4) no longer appear alone at the bottom of pages. New `wrap_heading_sections()` function wraps each heading + its following content (up to ~3000 chars) in a `<section class="heading-group">` with `break-inside: avoid`. CSS updated with `break-after: avoid`, adjacent sibling rules, and heading-group container styling. Weasyprint's limited support for `page-break-after: avoid` is now worked around at the HTML level.

## [1.15.9] - 2026-04-15

### Added
- **`ecosystem.yaml` shared contract:** Machine-readable single source of truth for type enums, skill metadata, schema versions, and contact classification. Referenced by core-skills-visualisation and landing page to prevent drift. Includes: insight types (content + evolution), contact classification levels, skills registry with badges and subcommands, output artifacts, visualisation feature list.
- **`scripts/check-ecosystem-alignment.sh`:** Version alignment checker that reads ecosystem.yaml and verifies visualiser CLAUDE.md and landing page i18n reference the same core-skills version. Run after version bumps to detect drift.

## [1.15.8] - 2026-04-15

### Added
- **Contact classification taxonomy (CR-009):** New `classification` field in `_meta.yaml` with four levels: `family`, `personal`, `professional` (default), `confidential`. New `private` convenience boolean for backward compatibility with `_tasks.yaml` filtering. Folder naming convention documented (`a1-*`/`a2*` = family). Privacy defaults in `base.yaml` auto-classify contacts by folder name pattern when `_meta.yaml` is absent.
- **`analytics` privacy filtering updated (CR-009):** `/analytics contacts` excludes `family` and `personal` contacts. Classification resolved from: `_meta.yaml` field > `private` field > folder name pattern > `professional` default.
- **`daily-dashboard` contact-level filtering (CR-009):** Generic mode shows all classifications. Org/shared mode excludes `family`, `personal`, and `confidential` contacts. Task-level `private` field continues to work independently.
- **`insights` classification awareness (CR-009):** Insights still extracted from all contacts regardless of classification. Visualisation app responsible for filtering. Privacy scrubbing rules unchanged.
- **`ops-config` schema v1.3 (CR-009):** New `privacy_defaults` config block in `base.yaml`. Contact-meta-schema bumped to v1.1 with `classification` and `private` fields.

## [1.15.7] - 2026-04-15

### Added
- **`analytics` skill:** Vault-level content analytics -- file creation trends, skill adoption, contact engagement, content distribution, and unprocessed backlog detection. Analyses file metadata (names, dates, paths), not file contents. Outputs dated snapshots to `_analytics/` folder in vault root with automatic archiving of older snapshots. Subcommands: `overview` (vault-wide metrics, growth trajectory, distributions), `skills` (per-skill adoption over time, structured vs unstructured ratio), `contacts` (engagement timelines, network growth, lifecycle patterns), `backlog` (unprocessed .txt files, missing _insights.yaml, stale inbox items), `help`. Uses path-first classification to avoid keyword miscount (~17% improvement over pure keyword matching). Privacy-aware via `_meta.yaml` `classification` field. Standalone skill -- no dependency on ops-base or ops-config.

## [1.15.6] - 2026-04-15

### Added
- **`md2pdf --outbox NAME` mode:** One-command outbox packaging. Creates `<vault>/_outbox/YYMMDD-NAME/`, PDFs every input markdown into that folder (or one combined PDF if `--combined` is also given), and generates a `_manifest.md` skeleton (status/kanal/kontakt/projekt + Innehåll table) plus a `YYMMDD-NAME-mejl.txt` email stub with subject + Bilagor listed and body left empty. NAME follows the contact convention (`förnamn-efternamn_organisation`). Vault root is auto-detected by walking up from cwd for `_outbox/` or `_contacts/` markers, with `$OBSIDIAN_VAULT` fallback and `--vault PATH` override. Optional `--subject TEXT` pre-fills the email Ämne line. Warns (non-fatal) if `_contacts/<NAME>/` is missing in the vault. Replaces the manual 4-step process of dated-folder creation, per-file PDF runs, hand-written manifest, and hand-written email stub.

### Added
- **`md2pdf` skill:** Markdown-to-PDF converter using weasyprint. Professional A4 styling with page numbers, tables, typography. Mermaid diagrams rendered as high-res PNG (SVG foreignObject not supported by weasyprint). Supports individual files, combined output, and custom CSS. Dependencies: weasyprint, markdown (Python), mmdc (npm, optional).

## [1.15.4] - 2026-04-07

### Added
- **`ops-config` swedish_chars sub-tree inheritance (CR-007):** New `language_inheritance` config block in `base.yaml`. By default, files written under `_projects/**`, `_contacts/**`, `_private/**`, or `_inbox/**` automatically inherit `swedish_chars: strict` from base regardless of whether the folder has its own CLAUDE.md. Catches sub-trees like `_projects/<client>/` that previously slipped through enforcement and accumulated character drift. Override per folder via CLAUDE.md.
- **`ops-config` swedish_substitutions.yaml:** New data file with the seed substitution list (verbs, prepositions, nouns, adjectives) loaded from MEMORY.md. Single source of truth for both `/ops normalize` and the `/insights` pre-write validator. Each entry has `from`, `to`, `category`, optional `ambiguous` flag for cases like `ar`/`är` and `bor`/`bör` where the ASCII form could be a different word.
- **`ops` `/ops normalize` subcommand (CR-007):** Lint pass that scans markdown and YAML files for known Swedish character drift and restores correct characters. Supports single files or recursive folder scans. Flags: `--dry-run` (preview diff), `--strict-no-ambiguous` (skip ambiguous substitutions). Skips code blocks, inline code, URLs, file paths, YAML keys, and lines marked `<!-- no-normalize -->`. Updates folder CHANGELOG.md when applying.
- **`insights` pre-write Swedish character validator (CR-007):** Before writing any `_insights.yaml` entry with Swedish text in `summary`/`rationale`/`context`, scan against the substitution map. Refuses to write on non-ambiguous violations; warns on ambiguous ones. The structural validation that the MEMORY.md reminder cannot provide.
- **`ops-base` Step 7 swedish_chars resolution order documented:** New explicit 4-step resolution rule (folder CLAUDE.md → venture config → inheritance glob → base default). Points to `swedish_substitutions.yaml` as the canonical substitution list and to `/ops normalize` for after-the-fact remediation.
- **`ops-config` schema v1.2:** Bumped from v1.1 to reflect addition of `language_inheritance` config block and the substitution data file.

## [1.15.3] - 2026-04-07

### Changed
- **`transcript` Structure rule reordered (CR-006):** New canonical section order is **Nästa steg → Beslut → Konklusion → Diskussion → Bakgrund**. Action items first (a reader scanning at 08:30 needs what they own first, not narrative). Konklusion is the wrap-up of the actions/decisions above, not a discussion summary. Bakgrund moves to the bottom (reference, not navigation).
- **`transcript` Beslut/Decisions section is now mandatory.** Always include the section, even if there were no formal decisions -- in that case write `*(Inga formella beslut -- diskussionen var orienterande.)*` or the English equivalent. Honest absence is searchable; silent omission is not.
- **`transcript` Action Item Table format standardised:** Required 5-column markdown table format with `#`, `Åtgärd/Action`, `Ägare/Owner`, `Prio/Priority`, `Deadline`. If owner or deadline is unknown, write `?` rather than omitting the column. The visualisation app and `/daily-dashboard` parse this table -- variants break them.
- **`transcript` canonical heading names locked.** Pick one Swedish + one English term per concept: Nästa steg/Next Steps, Beslut/Decisions, Konklusion/Outcome, Diskussion/Discussion, Bakgrund/Background, Blockers. Banished variants (will not be produced in new files): Sammanfattning, Executive Summary, Summary, Action Items, Åtgärdspunkter, Huvudpunkter, Key Discussion Points, Decisions Made.
- **`transcript` Konklusion length floor removed.** A short meeting can still have a 1-sentence outcome. Always include the section, however brief. The undocumented ~110-word floor is removed.
- **`ops-base` canonical heading order documented** with the same rules as `/transcript`. Applies to both Concise and Detailed Strategic two-tier summary formats.
- **`daily-dashboard` meeting status detection** now recognises canonical headings (Nästa steg, Beslut, Konklusion, Diskussion + English equivalents). Legacy headings (Sammanfattning, Executive Summary, Action Items, etc.) are kept in the detection list for read-only back-compat with pre-CR-006 files.

### Added
- **`transcript` Template variants by meeting length (CR-006):** Three modes -- Concise (<30 min), Standard (30-90 min, default), Extended (>90 min). Skill picks variant by estimating duration from transcript metadata. Override with `/transcript --concise` or `/transcript --extended`.
- **`ops-config` base.yaml strings:** New canonical heading keys under `transcript`: `decisions`, `outcome`, `discussion`, `background`, `blockers`, `no_decisions_marker`, `action_table_headers`. Both English and Swedish defaults.

### Migration
- **Existing files keep their headings.** This change applies to new files only. The daily-dashboard's section detection retains the legacy heading variants for back-compat reads. No bulk migration is performed.

## [1.15.2] - 2026-04-07

### Changed
- **`preparation` agenda-card-first format (CR-005):** Restructured prep document template around a 60-second walk-in card on top (agenda + open actions), with deep-dive content below the fold separated by a horizontal rule. Top-of-file is now self-sufficient -- a reader who only sees the walk-in card can lead the meeting.
- **`preparation` Agenda Tag System (CR-005):** Each agenda item must start with one of five tags: `[DECISION]`, `[DEMO]`, `[STATUS]`, `[QUESTION]`, `[FYI]` (Swedish: BESLUT/DEMO/STATUS/FRÅGA/FYI). Item text after the tag must be a question or deliverable, not a topic noun phrase. Tags resolve from `strings.agenda_tags` in org config.
- **`preparation` Step 2.5 cross-reference scan is now mandatory** with explained relevance. Each cross-reference link must include a one-sentence explanation of why it matters; bare links are forbidden. Skip the section entirely if no relevant lateral mentions found.
- **`preparation` walk-in card prioritisation rule:** Maximum 5 items in the walk-in card -- they must be the most critical, not the first 5 reported. Items 6+ go in an "Övriga punkter" section after the deep dives.
- **`preparation` single-document principle:** A prep file may not reference another prep file as required reading. If two prep streams converge, merge them.
- **`preparation` Background section moved to bottom** of the document. It is reference material, not navigation.

### Added
- **`preparation` Step 0 frozen-prep check (CR-005):** Before writing or modifying a prep file, refuse if the meeting date is in the past (with `--force` override). Prevents mid-meeting contamination of prep files. Live updates belong in the transcript file, not the prep file.
- **`ops` bidirectional supersede linkage (CR-005):** When `/ops` marks a prep file as superseded, it now also writes a `*Preparation: [filename](path)*` back-link into the meeting summary's metadata footer. Readers can navigate prep -> transcript or transcript -> prep.
- **`ops-config` base.yaml strings:** New keys `preparation.cross_references`, `preparation.their_actions`, `preparation.deep_dive_separator`, and the `agenda_tags` table (English + Swedish defaults).

## [1.15.1] - 2026-04-06

### Changed
- **`ops` prepare filename:** Include organization/project name in preparation filenames (`YYMMDD-preparation-[org/project]-[type].md`) to distinguish preparations created the same day for different orgs/projects. H1 heading also includes org/project prefix.

## [1.15.0] - 2026-04-04

### Added
- **Skill evolution loop (CR-004):** Three-step feedback loop — capture, compile, improve. Skills silently log execution feedback (`edge_case`, `correction`) to `_insights.yaml`. New `/insights compile` finds patterns. New `/insights propose` generates SKILL.md improvement diffs. Configurable `auto_apply` for fully automatic evolution. Inspired by Bosma's Promptware and Karpathy's LLM Knowledge Base patterns.
- **`ops-base` Step 9:** Execution feedback capture — silently logs edge cases and user corrections to `_insights.yaml` when `evolution.enabled` is true. Inherited by all ops-based skills.
- **`transcript` Step 4.5:** Execution feedback capture — same as ops-base Step 9, for standalone transcript processing.
- **`insights` subcommands:** `compile`, `compile since YYMMDD`, `propose`, `propose apply [file|all]`.
- **`ops-config` schema:** New `evolution` section under `workflows.knowledge_extraction` with `enabled`, `auto_apply`, `compile_threshold`, `propose_threshold`.
- **`ops-config` base.yaml:** New insight types `edge_case`, `correction`, `skill_pattern` added to default types list. Evolution config defaults added.
- **`docs/proposals/`:** Directory for skill improvement proposals generated by `/insights propose`.
- **`ops-config` schema v1.1:** Bumped from v1.0 to reflect addition of `evolution` config section and execution feedback types.

## [1.14.1] - 2026-04-04

### Changed
- **CR index:** Renumbered self-evolution loop CR-001→CR-004 for chronological consistency. Registered CR-003 (inbox) as implemented.

## [1.14.0] - 2026-03-24

### Added
- **`ops` Verticals support (Step 9.5):** After meeting processing, /ops now checks for configured vertical documents -- living documents that aggregate insights across multiple meetings on a single strategic topic. When topic keywords from the meeting match a vertical's trigger, the user is prompted to update it. Verticals are config-driven via `workflows.verticals` in org config.
- **`ops-config` schema:** Added `verticals` section under `workflows` with fields: `path`, `name`, `topics`, `trigger` (if_mentioned/always).

## [1.13.2] - 2026-03-15

### Changed
- **`transcript` Structure rule:** Added "Conclusion first, details second" requirement. Summaries must now lead with the actual outcome/decision, followed by next steps, then background sections (labeled with "Bakgrund:" prefix). Anti-pattern guidance added to avoid "Sammanfattning" that describes discussion rather than conclusion.
- **`transcript` Name Resolution:** Added explicit rule to never trust transcript spellings. Names must be resolved against filename, `_meta.yaml`, and org config before use throughout summary content.

## [1.13.1] - 2026-03-12

### Added
- **`ops` ATTACHMENTS AND MEDIA section:** Guidance for handling PDFs, presentations, and binary files referenced in meetings. Includes detection triggers, placement convention (`.attachments/`), naming format (`YYMMDD-description.ext`), linking format for meeting summaries, and workflow steps for asking user and suggesting moves.

## [1.13.0] - 2026-03-08

### Added
- **`inbox` skill:** Universal entry point for unstructured content (voice memos, quick notes, emails, raw text). Auto-classifies and routes to the appropriate downstream skill (`/transcript`, `/ops`, `/tasks`). Subcommands: `/inbox [content]`, `/inbox status`, `/inbox process [id]`, `/inbox help`. Stores items in `_inbox/` with `_inbox.yaml` index. Supports web UI via core-skills-visualisation.
- **README.md:** Added inbox skill to skill table, dependency tree, overview table, and choosing guide.

## [1.12.1] - 2026-03-04

### Fixed
- **`tasks/skill.md` anonymization:** Replaced real company names, personal names, and project identifiers with generic placeholders in all examples and documentation

## [1.12.0] - 2026-03-04

### Changed
- **Distributed `_tasks.yaml` system (v2):** Tasks are now tracked in per-folder `_tasks.yaml` files (like `_insights.yaml`) instead of a single central file. Replaces `task-priority-matrix.md` entirely.
  - `tasks/skill.md`: Rewritten for v2 schema -- per-folder discovery, `--all` aggregation, `context`/`scope` fields, local file creation
  - `ops/SKILL.md`: Step 5 `task_yaml` replaces `task_matrix`; Step 9 task import targets local `_tasks.yaml`; fallback creates v2 file
  - `daily-dashboard/SKILL.md`: Multi-file scanning for tasks; groups by context; updated org mode task discovery and priority tracker links
  - `transcript/SKILL.md`: Step 4 task import targets local folder `_tasks.yaml` (not vault root); creates v2 file if missing
  - `ops-base/SKILL.md`: Task management section updated for per-folder `_tasks.yaml` convention

## [1.11.2] - 2026-03-04

### Changed
- **Vault folder structure redesign:** Updated all skills to use new `_contacts/`, `_projects/`, `_private/` convention instead of `=*/` prefix pattern
  - `transcript/SKILL.md`: Contact folder discovery now checks `_contacts/` directory
  - `preparation/SKILL.md`: Folder matching uses `_contacts/firstname-lastname/` format
  - `daily-dashboard/SKILL.md`: Scan locations, contact name extraction (hyphen-separated), symlink paths updated
  - `insights/SKILL.md`: Scan paths and examples use `_contacts/` and `_projects/` prefixes
  - `tasks/skill.md`: Example vault path updated from `=privat/` to `_private/`
  - All skill README.md files updated to match
- `README.md`: Version to 1.11.2

## [1.11.1] - 2026-03-04

### Changed
- **Privacy enforcement in `_insights.yaml`:** Added explicit rules to `transcript` Step 3.5, `insights` Extraction Reference, and `ops` Step 5.5 -- NEVER include personal names or company names in `summary`, `rationale`, or `tags` fields. Includes bad/good examples.
- **Swedish character enforcement strengthened:** Added YAML-specific reminders to `transcript`, `insights`, and `ops` skills -- `_insights.yaml` fields are equally prone to missing å, ä, ö as markdown files.
- Anonymized bad-example snippets in `transcript` and `insights` skills (replaced real names with generic placeholders)
- `transcript/SKILL.md`: Removed specific user name reference from Step 4 task import description
- `README.md`: Version to 1.11.1

## [1.11.0] - 2026-03-04

### Added
- **`insights` skill:** Knowledge extraction manager for retroactive insight extraction
  - `reprocess [target]`: Extract insights from existing YYMMDD-*.md transcript files
    - Target: folder path, `all` (all CHANGELOG.md folders), `since YYMMDD` (date filter)
    - Same extraction logic as transcript Step 3.5 (types, threshold, dedup)
    - Progress reporting per folder, summary at end
  - `scan-claude-md`: Extract embedded knowledge from CLAUDE.md files in vault
    - Type mapping: decisions, preferences, learnings, patterns from structured sections
    - Re-extracts when CLAUDE.md is modified after last extraction
  - `status`: Show insights statistics (counts, top folders, reprocessing opportunities)
  - `help`: Usage guide with examples

### Changed
- `README.md`: Added insights skill to skills table, dependency diagram, comparison, workflows, interaction diagram, version to 1.11.0

## [1.10.0] - 2026-03-03

### Added
- **Knowledge Extraction (`_insights.yaml`):** Silent accumulation layer that captures durable insights from meetings and conversations
  - `transcript` Step 3.5: Scans summaries for decisions, preferences, learnings, opportunities, and patterns
  - `ops` Step 5.5: Same extraction with additional ops-specific sources (domain additions, agenda resolutions)
  - Per-folder `_insights.yaml` files alongside CHANGELOG.md
  - Deduplication by source file, configurable threshold, max 10 insights per meeting
  - Never surfaces in skill output -- visualization app is the only consumer
- **`ops-config` base.yaml:** `knowledge_extraction` workflow config (enabled by default)
- **`ops-config` base.yaml:** `strings.insights` and `strings_sv.insights` i18n blocks

## [1.9.0] - 2026-03-03

### Added
- `preparation`: Step 2.5 -- Cross-Context Scan. After gathering context from the contact's folder, scans recent `YYMMDD-*.md` files across all `=*/` folders (last 7 days) for mentions of the contact, company, or key topics. Adds a `{strings.preparation.cross_references}` section to the preparation document when relevant mentions are found. Skips when fewer than 3 contact folders or no matches.
- `README.md`: Daily Workflow Guide section -- consolidated overview of which skills to run before, during, and after meetings throughout a workday

## [1.8.3] - 2026-02-26

### Added
- **`ops` subcommand: `/ops help`** -- shows usage guide, skill correlation, config loading, and common patterns

### Changed
- Anonymized all documentation: replaced company names, personal names, infrastructure details, and GitHub URLs with generic placeholders
- `ops/SKILL.md`: Added `help` subcommand definition, argument-hint updated
- `README.md`: Updated /ops description, workflow comparison, skill selection table, version to 1.8.3
- `README.md`: Rewrote skill selection guide, added quick-start table, updated interaction/lifecycle diagrams to show /ops as primary path

## [1.8.2] - 2026-02-26

### Added
- **`ops` subcommand: `/ops status`** -- shows available org configs, active config for current directory, team, workflows, and base defaults
- **`ops` Step 9: Post-Processing** -- optional task import and dashboard refresh after meeting processing
  - `post_processing.task_import`: Extract action items from summary, match/import to `_tasks.yaml`
  - `post_processing.dashboard_refresh`: Regenerate org dashboard after all updates
- **`ops` usage guidance:** "WHEN TO USE /OPS vs /TRANSCRIPT" section in SKILL.md
- **`ops-config` schema:** `post_processing` section (task_import + dashboard_refresh)
- **`ops-config` base.yaml:** `post_processing` defaults (both disabled)

### Changed
- `ops/SKILL.md`: Added SUBCOMMANDS section (`/ops status`), argument-hint updated, added `post_processing` to config table, added Step 9, added usage guidance
- `ops-config/README.md`: Updated to reference `/ops` instead of removed domain skills
- `README.md`: Updated /ops description with status subcommand, workflow comparison, skill selection table, task flow diagram, config list, version to 1.8.2

## [1.8.1] - 2026-02-25

### Removed
- `engagement-ops` skill (moved to [bravo-skills](https://github.com/bravo-org/bravo-skills) -- consulting-specific, not core)

## [1.8.0] - 2026-02-25

### Added
- **`ops` skill:** Unified meeting and operations processing, config-driven for any organization
  - Replaces `project-ops` (core-skills), `bravo-ops` (bravo-skills), `management-ops` and `marketing-ops` (acme-skills)
  - Summary format driven by `summary_sections` config or TWO-TIER default
  - Configurable file updates (1-5 files), action propagation, agenda management
  - Domain additions applied from org config
  - Fallback to base.yaml when no org config exists
- **`ops-config` schema additions:**
  - `summary_sections`: Custom meeting summary structure (table/subsections/freeform)
  - `status_terminology`: Domain-specific work and resolution status terms
  - `issue_id_format`: Structured issue ID pattern
  - `workflows.agenda_management`: Post-meeting agenda updates (enabled, file, section)
- **`ops-config` base.yaml defaults:** Empty summary_sections, empty status_terminology, null issue_id_format, agenda_management disabled

### Removed
- `project-ops` skill (replaced by `/ops` with project-level config)

### Changed
- `ops-base`: Updated description and references to point to `/ops` instead of domain-specific skills
- `README.md`: Updated skills table, dependency diagram, comparison section, workflow diagrams for `/ops`

## [1.7.5] - 2026-02-24

### Removed
- `cr` skill (moved to [bravo-skills](https://github.com/bravo-org/bravo-skills))

## [1.7.4] - 2026-02-23

### Changed
- **`transcript` Step 3:** CHANGELOG update is now mandatory -- always creates or updates CHANGELOG.md in target folder. If no CHANGELOG exists, one is created automatically with entries for all existing files in the folder.

## [1.7.3] - 2026-02-21

### Added
- **`tasks` skill:** New personal task tracker with cross-project correlation
  - Central `_tasks.yaml` index at vault parent level
  - Source linking back to meetings/decisions
  - Automatic carry-forward of incomplete tasks
  - Privacy model (`private: true/false`) for shared vs personal tasks
  - Project tagging for cross-project views
  - Structured YAML format with history tracking
  - Commands: `show`, `add`, `done`, `import`, `weekly`, `archive`, `migrate`
- **`transcript` Step 4:** Task import integration
  - Offers to import action items to `_tasks.yaml` after saving transcript
  - Auto-detects project from file path
  - Links tasks back to source meeting
  - Respects existing task schema
- **`daily-dashboard` task integration:**
  - Reads active tasks from `_tasks.yaml`
  - Displays in "Teamfokus" section grouped by priority
  - Shows overdue, P0, P1, P2 with source links
  - Includes completed tasks from `_tasks-history.md`
  - Task counts in Quick Stats table

### Changed
- `README.md`: Added comprehensive skill interaction documentation with state diagrams
- `transcript/skill.md`: Added Step 4 (Task Import), updated meeting lifecycle diagram
- `daily-dashboard/skill.md`: Added Personal Task Integration section, updated templates and execution steps

### Architecture
- Tasks flow: `/transcript` extracts action items -> offers import -> `_tasks.yaml` -> `/daily-dashboard` displays
- Central task index enables cross-project visibility while respecting per-project filtering
- Privacy model separates personal tasks from shared team views

### Notes
- **Person+project folder pattern validated:** Merged contact+project folders using the pattern `=person-project/`. Transcript skill routes via CLAUDE.md routing table. No skill code changes required.

## [1.7.2] - 2026-02-19

### Changed
- `daily-dashboard`: Org mode now writes to `_Dashboard-{org}.md` (e.g. `_Dashboard-acme.md`) instead of `_Dashboard.md`. Generic mode keeps `_Dashboard.md`. Both coexist without collision.

## [1.7.1] - 2026-02-19

### Fixed
- `update-skills`: All git commands now use `git -C <repo-path>` instead of relying on shell working directory. Prevents operating on the wrong repository when processing multiple repos sequentially.
- `update-skills`: Added safety rule 9 -- explicit `-C` flag requirement for every git command

## [1.7.0] - 2026-02-19

### Added
- **String tables (i18n):** `ops-config` schema and `base.yaml` now include `strings` (English) and `strings_sv` (Swedish) blocks for configurable section headers, annotations, labels, and filename keywords
- **Lifecycle integration:** `/transcript` Step 1.5 links back to preparation files when one exists for the same contact + date
- **Standup discovery:** `/daily-dashboard` now categorizes `standup`/`daily-standup` files in a dedicated "Standup/Projekt" section
- **Dashboard deduplication:** When both preparation and transcript exist for same contact + date, only the transcript is shown (preparation suppressed)
- **README howto:** "How Skills Work Together" section documenting meeting lifecycle, file discovery, config-driven strings, and CHANGELOG conventions

### Changed
- `ops-config/schema.md`: Added `strings` section definition with resolution order documentation
- `ops-config/base.yaml`: Added `strings` and `strings_sv` default blocks
- `preparation/SKILL.md`: Template annotated with `{strings.*}` references, string resolution section added
- `transcript/SKILL.md`: String resolution section, Step 1.5 lifecycle link, metadata footer, lifecycle diagram
- `daily-dashboard/SKILL.md`: String resolution section, expanded 3-category file classification, deduplication logic, standup scanning in org mode
- `README.md`: Added "How Skills Work Together" section, version bump to 1.7.0

### Notes
- `bravo-ops` uses `YYYY-MM-DD` date format instead of `YYMMDD` -- not addressed in this release but noted for future alignment
- All changes are backwards-compatible: skills without config loaded fall back to current hardcoded strings

## [1.6.4] - 2026-02-19

### Added
- `preparation` skill for creating structured meeting preparation documents
  - Takes a contact name + optional date: `/preparation david tomorrow`
  - Reads previous transcripts, preparations, and CHANGELOG from the contact's `=*/` folder
  - Generates briefing with context, numbered discussion topics, open action items, and suggested agenda
  - Supports post-meeting updates with `[UTFALL]` annotations
  - Output follows `YYMMDD-förberedelse-*.md` naming convention, auto-discovered by `/daily-dashboard`

### Changed
- `daily-dashboard`: Rewritten to support two modes -- generic and org
  - Generic mode (default): scans current working directory for `YYMMDD-*.md` files in `=contact/` folders
  - Org mode: pass an org name (e.g. `/daily-dashboard acme`) to load org config and use project-specific discovery
  - New argument format: `[org] [today|tomorrow|YYMMDD]`
  - New symlink types: `_PREP-*` for preparations, `_TODAY-*` for meetings
  - Persistent symlinks (`_MGMT-*`, `_MKT-*`, etc.) only created in org mode
  - Swedish-language dashboard in generic mode
- `transcript`: Added cross-reference to `/preparation` skill and naming convention documentation

## [1.6.3] - 2026-02-17

### Changed
- `daily-dashboard`: Added casing convention (title case for status labels, e.g. "Completed" not "COMPLETED")
- `daily-dashboard`: Added "Tomorrow" section to template with daily standup placeholder
- `daily-dashboard`: Added completed meeting example to template

## [1.6.2] - 2026-02-17

### Added
- `daily-dashboard` skill for daily meeting and task dashboard generation
  - Creates mobile-friendly `_Dashboard.md` with meeting links and embeds
  - Creates desktop symlinks for quick access (`_TODAY-*`, `_MGMT-*`, `_MKT-*`, `_MOBILE-*`)
  - Auto-discovers meetings by date (YYMMDD format)
  - Extracts critical items from priority matrices
  - Standalone skill, no dependency on ops-base

## [1.6.1] - 2026-02-15

### Changed
- Moved origin to `your-username/core-claude-skills` (public)
- Deleted old `bravo-org/core-skills` GitHub repo
- Updated all documentation URLs across core-skills, acme-skills, and bravo-skills

## [1.6.0] - 2026-02-15

### Removed
- `management-ops` skill (moved to [acme-skills](https://github.com/acme-org/acme-claude-skills))
- `marketing-ops` skill (moved to [acme-skills](https://github.com/acme-org/acme-claude-skills))
- `bravo-ops` skill (moved to [bravo-skills](https://github.com/bravo-org/bravo-skills))
- `ops-config/acme.yaml` (moved to acme-skills as `acme-ops-config`)
- `ops-config/bravo.yaml` (moved to bravo-skills as `bravo-ops-config`)

### Changed
- core-skills is now purely generic: ops-base, ops-config (schema + base only), transcript, project-ops, cr, update-skills
- Updated update-skills sources table with acme-skills and bravo-skills repos
- Updated README with new skill table, dependency diagram, and related repos
- Updated ops-base config docs to reflect org configs as separate skills
- Version bump to 1.6.0

## [1.5.0] - 2026-02-15

### Changed
- Renamed repository from `bravo-skills` to `core-skills` to reflect its role as the generic foundation
- Replaced all relative cross-skill paths (`../ops-base/`, `../ops-config/`) with skill-name references (`~/.claude/skills/`) that resolve through symlinks regardless of repo location
- Updated config resolution pattern: org configs now live in their own skill directories (`{org}-ops-config/{org}.yaml`) instead of `ops-config/{org}.yaml`
- Updated update-skills sources table with new repo name and URLs
- Updated all documentation (README.md, README-local-setup.md) with new repo name
- Version bump to 1.5.0

## [1.4.0] - 2026-02-15

### Added
- `update-skills` skill for skill repo management
  - 4 operations: update (default), status, check, install
  - Multi-remote support with version safety (commit graph ancestor check before pull)
  - Repo discovery via self-discovery, symlink scanning, and sources table matching
  - Automatic symlink creation for new skills after pull
  - Symlink health auditing (broken, missing, orphaned detection)
  - Repo installation with automatic remote configuration
  - Standalone: no dependency on ops-base or ops-config
- Bootstrapping shortcut in README: clone + single symlink + `/update-skills update`

### Changed
- Made repo paths flexible: removed hardcoded `~/Projects/` from sources table and all documentation
  - Repos are now discovered dynamically via symlink resolution (self-discovery + symlink scanning)
  - `install` clones repos as siblings of `core-skills` (base directory detected from `update-skills` symlink target)
  - Bootstrapping instructions now work from any directory
- Updated README.md with update-skills in skills table, comparison section, dependency diagram, and installation instructions
- Simplified README installation section: replaced 9-symlink manual setup with 4-line quick start using `/update-skills` bootstrapping
- Removed Remotes section from public README (internal detail)
- Added `README-local-setup.md` for NAS-first setup on local network machines (clone from NAS, dual-remote config)
- Version bump to 1.4.0

## [1.3.0] - 2026-02-15

### Added
- `cr` skill for change request lifecycle management
  - 10 operations: create, status, promote, branch, list, next, show, deps, version, audit
  - Draft/Proposed templates with status lifecycle enforcement (Draft -> Proposed -> Planned -> Implemented -> Archived)
  - CR index management with automatic README.md updates
  - Git branch creation for Proposed CRs (kebab-case branches, snake_case filenames)
  - Integrity auditing with auto-fix (orphaned files, broken links, status mismatches)
  - Project-agnostic: CR directory path configurable via CLAUDE.md

### Changed
- Updated README.md with cr skill in skills table, comparison section, dependency diagram, and installation instructions
- Version bump to 1.3.0

## [1.2.1] - 2026-02-12

### Added
- Comprehensive skill comparison section in README
  - Overview table (organization, language, files updated, domain focus)
  - Shared features via ops-base
  - Detailed differences between each skill
  - Workflow comparison diagrams
  - Skill selection guide
  - Instructions for adding new organizations

## [1.2.0] - 2026-02-12

### Added
- `ops-config` configuration system for organization-agnostic skills
  - `schema.md`: YAML schema definition for org configs
  - `base.yaml`: Default fallback configuration
  - `acme.yaml`: Acme organization (English, full team, responsibility matrix)
  - `bravo.yaml`: Bravo organization (Swedish, action propagation enabled)
- Structured extraction format in `transcript` skill
  - YAML-based extraction output for domain skills
  - Enables consistent parsing across all ops skills

### Changed
- `ops-base`: Added configuration resolution logic and workflow orchestration
- `management-ops`: Now reads team/terminology from acme.yaml config
- `marketing-ops`: Now reads team/terminology from acme.yaml config
- `bravo-ops`: Now reads team/terminology from bravo.yaml config
- Updated README.md with config system documentation and architecture diagram

### Architecture
- Skills are now organization-agnostic via layered config system
- Config resolution: project-level > org-level > base defaults
- Transcript serves as universal extraction layer for domain skills

## [1.1.0] - 2026-02-12

### Added
- `bravo-ops` skill for Bravo business operations
  - Swedish-language output for all documentation
  - Integrates with Bravo styrning/ templates (mall-motesreflektion.md)
  - Decision propagation to BRAVO.md, actions to ALEX.md/HANK.md
  - Customer sentiment tracking, delivery status monitoring
  - Extends ops-base framework

### Changed
- Updated README.md with bravo-ops in skills table and dependency diagram

## [1.0.1] - 2026-02-12

### Added
- `project-ops` skill for development standup processing
  - 5-file update workflow (summary, task-priority-matrix, README, CHANGELOG, meetings index)
  - 8-section detailed meeting format
  - Development-specific sections (Completed, In Progress, Technical Updates, Issues, Decisions, Actions, Version Status, Status Summary)
  - Extends ops-base framework

### Changed
- Updated README.md with project-ops in skills table and dependency diagram

## [1.0.0] - 2026-02-11

### Added
- Initial release with 4 skills:
  - `ops-base` - Shared operational framework
  - `transcript` - Transcription processing
  - `management-ops` - Executive management documentation
  - `marketing-ops` - Marketing operations documentation
