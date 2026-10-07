# CR-108 — The prepare template has no place for options or deferrals, and no update path

| | |
|---|---|
| **Status** | **Proposed** — renumbered from CR-105 (that number was released for another change). Its *pending decisions* gap is absorbed by CR-107's card (*Decisions needed today*) for wired projects; the deferrals half and the unwired template remain here |
| **Contract** | additive — two template sections, one P0 option, one sentence on linking, and a section order change (existing agendas stay readable; nothing parses agenda order); no config key changes |
| **Date** | 2026-10-06 |
| **Area** | `ops` (`prepare` P0, P3, P5) |
| **Related CRs** | CR-005 (agenda-card-first, for `/preparation`), CR-082 (one way to make an agenda), CR-086 (check for an existing preparation), CR-101 (generated agenda is a draft), CR-102 (manifests are edited, not regenerated) |

## What happened

A project without a wired loop (no `carry_forward`) had its daily agenda written by `/ops prepare`
in one session. A later session was asked whether the agenda followed the skill. It did not. The
P3 template's order was broken in three places:

- the **Key Updates** table was replaced by a prose block ("where the project stands")
- **Reported Updates** had moved below Blockers
- **four sections the template does not have** sat between Agenda and Blockers

The content was not wrong, and none of it was removed when the agenda was put back into template
order. **The finding is about where it went.** Each extra section exists because the template had
nowhere to put something a real meeting needed. Two of the four answer a need every
decision-taking series has. The other two were duplicates the template already covers.

| Section added by hand | What it held | Verdict |
|---|---|---|
| "The two decisions" | Each pending decision with options A/B, what the choice means, and what exactly has to be decided | **Template gap.** `Decisions → Pending` is a bullet list with no room for options |
| "Not today" | Open questions deliberately left off a short session, carried to a later one | **Template gap.** An unwired project has no place for an open item that is not on today's agenda |
| "Status to confirm" | One closed question per person | Duplicate of the *Today* column in Status Overview |
| A topic brief (a proposal for new tracker columns) | The material behind one agenda item | Already covered by *Relevant reference section*. Only the link from the agenda item was missing |
| Prose "where the project stands" | Catch-up for a facilitator who had been away | Duplicate of Key Updates, which has a Source column for exactly this |

**A fifth, process finding.** The agenda already existed when the second session started, and the
repository had moved since it was written: two tickets merged, one new pull request open. P0
(CR-086) offers three choices: *open it, regenerate it, or write anyway*. The case that actually
happened was a fourth: **update the existing agenda**, keeping its structure and adding what has
changed. Nothing in P0 or P5 says what an update must also touch. The agenda had a copy staged in
`_outbox/` and a manifest, and both had to be kept in step by hand.

## Why the gaps matter

**Deferrals are the carry-forward of an unwired project.** In a wired project, `## Carried forward`
and `build_agenda.py` keep an open item alive across sessions (CR-082, CR-084). An unwired project
has only the template, and the template's only carry-forward is in the *weekly/planning* variation
(P4). A daily agenda that leaves an item off for time reasons therefore drops it. Nothing records
that it was deferred rather than closed, and the next agenda, built from the summary, does not
know it exists. In this instance two open questions were about to disappear that way: a
data-model question with no owner, and a question whose answer in the previous session had
addressed a different point.

**Options are what make a pending decision decidable in the room.** A bullet saying
*"(a) the cadence"* puts the framing on the facilitator, live. The sessions that need options are
those where the decider was absent or the decision has already slipped once, which is when the
room has the least time to construct them.

## Proposal

### 1. Pending decisions carry options (P3)

`Decisions → Pending` stays a list, one line per decision. **Each decision that has more than one
real answer gets a block under `# Reference`**:

```markdown
## Decision: <what is being decided>

| Option | What it means |
|---|---|
| **A. <option>** | <consequence> |
| **B. <option>** | <consequence> |

**Recommendation:** <A or B, one line why>, or *none -- the room decides*
**Decides:** <name> · **Open since:** <date>
```

The matching agenda item says *"options under Reference"*. A decision with only one answer on the
table is a confirmation, not a decision, and goes in Status Overview's *Today* column instead.

### 2. A fixed section for what is deliberately not on the agenda (P3)

Between `## Decisions` and `# Reference`:

```markdown
## Carried, not on today's agenda

- **<item>** -- <one line of state> · **<owner>**
```

Same line shape as `## Carried forward` (owner read from the trailing bold, `UNOWNED` otherwise),
so `/ops orient` and a later wiring of the loop can read it without a second format. **Write the
section even when it is empty**: *"Nothing deferred."* An omitted section means the same as an
omitted `## Carried forward` (CR-082): nobody can tell it from a section someone forgot.

`/ops process` then closes the loop: an item in this section that the meeting did not address is
carried into the summary's *Next Steps* rather than dropped.

### 3. An agenda item links to its material (P3, one sentence)

> An agenda item whose discussion needs more than one line of background gets a section under
> `# Reference`, and the item says so. Material does not go between `## Agenda` and `## Blockers`.

The template already allows the section. This makes the placement explicit, because the inline
placement is what reordered the agenda.

### 4. P0 offers *update*, and an update syncs its copies (P0, P5)

When an existing preparation is found, P0 offers four choices, not three:

| Choice | When |
|---|---|
| Open it | Nothing has changed since it was written |
| **Update it** | The sources have moved (chat, repository, a processed meeting). Keep the structure, add what changed, and state the update in the footer (`Updated <date> with ...`) |
| Regenerate it | The structure is wrong or the meeting changed |
| Write anyway | Never the default; say why |

**An update is not finished until every copy matches.** Where the agenda has been staged
(`_outbox/<item>/`), P5 copies the updated source over the staged copy, verifies they are
identical, and edits the manifest line by line under CR-102: append one judgement line naming
what changed, and never touch `status`. A staged copy that differs from its source is the failure
`Kanonisk källa` exists to prevent, and nothing catches it today.

### 5. The agenda comes first (P3)

Today P3 opens with **Status Overview** and **Key Updates** and puts the Agenda third. The reader
opens the file and meets two tables of state before learning what the meeting is for and what
each piece of state is *for*. The person who flagged it put it plainly: the agenda should come
first, *so that you can see how everything fits together*.

**`/preparation` already made this change.** CR-005 measured prep files that opened with a recap:
*"2-minute walk-in usability"* scored 4/10, and it moved to agenda-card-first. `/ops prepare` never
followed, so the two doors to the same loop step (*prepare*) lead to opposite orders. The same
reasoning applies more strongly here, because a team agenda is shown on screen to people who did
not write it.

New P3 order:

1. **Agenda**: items as questions, each with owner and time-box, each linking to its Status row
   or Reference section
2. Status Overview
3. Key Updates
4. Reported Updates
5. Blockers
6. Decisions (Made / Pending)
7. Carried, not on today's agenda
8. `# Reference`

Everything below the Agenda is what the agenda points to. **The heading line keeps its one-line
meeting note** (time, length, what must be decided today) above the Agenda, so the first screen
says what the meeting is for.

`build_agenda.py` (wired projects) has its own order (sources block first, CR-084) and is out of
scope here. Whether the generated agenda should follow is a question for a later CR, once this
order has been used on the template path.

### 6. Template check before reporting (P5)

Before reporting the agenda as done, P5 compares the agenda's `##` headings with the P3 order in
(5): Agenda, Status Overview, Key Updates, Reported Updates, Blockers, Decisions,
Carried-not-today, then Reference. It reports any heading outside `# Reference` that the template does not name.
This is the same template-contract check the summaries already get (CR-018), applied to the
artifact that until now had none.

## What this does not do

- **It does not rewrite existing agendas.** They keep their order; only new ones follow (5).

- **It does not wire the loop.** An unwired project stays unwired. The deferral section is the
  smallest thing that stops an item disappearing, not a second carry-forward engine.
- **It does not add "Status to confirm".** That need is met by the *Today* column. Adding a
  section for it would create two places for one fact.
- **It does not change the generated agenda.** `build_agenda.py` already carries items forward. The
  options block (1) may be worth adding there later, but only after it has proved itself on the
  template path.

## Verification

1. An unwired project, an agenda with one pending two-option decision and two deferred items:
   P3 output has the Reference decision block and a populated *Carried, not on today's agenda*
   section. P5's heading check passes.
2. The same, nothing deferred: the section reads *"Nothing deferred."*, and is not omitted.
3. An existing agenda plus a source newer than it: P0 offers *update*. After the update the staged
   copy is byte-identical to the source, and the manifest has one appended line and an unchanged
   field block.
4. An agenda with a section between Status Overview and Blockers that the template does not
   name: P5 reports it before saying the agenda is done.
5. `/ops process` on a meeting that skipped a deferred item: the item appears in the summary's
   *Next Steps*.
6. A new P3 agenda: the first `##` heading is `## Agenda`, and every agenda item that needs
   background links to a heading below it.
