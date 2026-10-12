# CR-121 — The card fits the project and the session: no release blockers where nothing is released, a demo section on demo day

| | |
|---|---|
| **Status** | **Proposed** |
| **Contract** | additive — optional `carry_forward.card` keys and an optional milestone `kind`; default output unchanged |
| **Date** | 2026-10-09 |
| **Area** | `ops` (`build_agenda.py` card layout), `ops-config` schema |
| **Related CRs** | CR-107 (the agenda is the card), CR-114 (a blocker is a release blocker), CR-113 (the card keeps the round table) |

> **Renumbered 2026-10-12.** Drafted as CR-119 on one machine while a different CR-119 (*validate the
> configuration first*) was written and implemented on the other. Two proposals briefly carried the same
> number; this one moved to 121. Nothing in it changed.

## What happened

The second project wired to the card layout is an internal tooling project: improvements move one at a time from a request sheet to staging to production, and **nothing in it is a release**. Its first generated card opened with:

- an italic lead, *"Confirm the release blockers and their plan…"*
- a **Release blockers** section reading *None carried as `[blocker]`*

and the session was the project's **first demo day**, the milestone the card itself named, with **0 days** left. The card had no place for what the meeting was for: which items are shown, by whom, and in what state. The owner's reaction: *since this is the demo day, should we not focus on that instead? This project is not a release-blocker project, so that should be configured as not shown.*

Both were fixed by hand-editing the generated card, which the loop says must not happen. **Neither could be configured**: the section title and the lead line are literals in `build_agenda.py`.

## Two gaps

**1. Release blockers are assumed.** CR-114 defined a blocker as a release blocker, which is right for a product with releases. A project without releases still gets the section and the lead, and an empty section asks the room to confirm a list that cannot exist. An empty, irrelevant section on the card trains the room to skip sections, which is the failure the card exists to prevent.

**2. The session's purpose is not on the card.** The milestone says *demo day, 0 days*, and the card then runs the same blockers / dependencies / decisions / round as any other day. On a demo day the content *is* the list of things to show, and the pipeline already knows it: items on staging or done, each with the person who raised it (the demo convention: the raiser shows).

## Proposal

### 1. `carry_forward.card.release_blockers: false`

```yaml
workflows:
  post_processing:
    carry_forward:
      layout: card
      card:
        release_blockers: false   # default true; false drops the section and the lead line
```

With `false`: no *Release blockers* section, and the lead reads *"Raise what you wait on, then one minute each."* Carried `[blocker]` lines, if any, still appear, under **Blockers** without the word *release*. `/ops check` flags `release_blockers: false` together with repo `labels:` declaring a `gap`, since the two contradict each other.

### 2. A milestone kind: `demo`

```yaml
milestone:
  name: First demo day
  date: 2026-10-09
  kind: demo            # optional: demo | release | review; default none
```

**On the milestone's own date**, with `kind: demo`, the card places a **Demo** section directly under the milestone:

| Item | Shown by | State |
|---|---|---|

Rows come from carried lines and repo movement that name a ticket on staging or done since the last demo. *Shown by* is read from a carried line's owner or a declared `raised_by` source, and is **blank, not guessed**, when unknown: the room fills it, and the blank is visible. The lead line becomes *"Demo day: the people who raised the ideas show them; then what we wait on, and one minute each."* The Teams post carries the demo list in place of the blockers line.

Before the date the milestone line stays as it is. After it, the card says *demo held? record it and set the next milestone*.

### 3. Lint

`/ops check`: `layout: card` with `release_blockers` unset, no repo `labels:`, and a milestone with `kind:` other than `release` → suggest `release_blockers: false`. Report only.

## What this does not do

- It does not change the default card. A project that ships releases keeps CR-114 unchanged.
- It does not choose who demos. *Shown by* is read or left blank.
- It does not add a session-type system. One optional key on the milestone, because the milestone is already the thing the card runs toward.

## Verification

1. A card with `release_blockers: false`: no *Release blockers* heading, and no lead line mentioning release.
2. A milestone `kind: demo` dated today: the Demo section is directly under the milestone; rows name tickets on staging or done; *Shown by* blank where unknown.
3. The same milestone dated tomorrow: no Demo section.
4. `check` on a card project with no labels and no `release_blockers` key: one suggestion line.
