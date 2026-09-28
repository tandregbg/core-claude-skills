# CR-104 — A project opens with a command and closes by hand

| | |
|---|---|
| **Status** | **Proposed** |
| **Contract** | additive — a `close` subcommand and an optional `lifecycle:` config block; no existing key changes |
| **Date** | 2026-09-28 |
| **Area** | `ops` (`project new`, `project close`), `ops-config` schema |
| **Related CRs** | CR-086 (project create and register), CR-061 (project brief), CR-019 (`check`, closure debt), CR-036 (placement classes) |

## What happened

An external practitioner described the project flow she wants for her firm's project managers,
unprompted and without knowing what the skills already do:

> record the client meeting, generate a brief, confirm the brief with the client, let it flow
> onward in the system, update it as the team changes, and evaluate when the project closes

Five of those six steps exist. `project new` creates and registers the folder (CR-086),
`project_brief.py` reads where a recurring project stands (CR-061), and the transcript and
task ledgers carry the middle. **The sixth does not exist as a code path.** A project is closed
by hand: someone remembers to write a tombstone, update the register rows that `project new`
wrote, and decide whether the task ledger's open rows are finished, moved or abandoned.

The asymmetry is the finding. Opening is a command precisely because doing it by hand meant
copying a folder shape by eye and updating three registers manually — and CR-086 documents a
parallel session having already written one of those rows. **Closing has the same shape and the
same failure mode, and nothing was built for it.** The registers a create wrote are exactly the
registers a close must unwind.

## Why this is the second instance, not the first

`skills/ops/SKILL.md` already names the gap and sets the bar for closing it:

> This is a README convention, not a declared lifecycle. There is one known instance of the shape,
> and a lifecycle declared on a single case is a guess. If a second appears wanting the same three
> parts (exit criterion, handover, tombstone), that earns its own CR.

The pre-phase block was that first instance. This request is the second, and it wants the same
three parts from a different direction: a client project that ends on delivery rather than on a
handover to a sibling track, with an **evaluation** as the thing that makes the ending worth
recording. Two instances with different shapes and the same three parts is the condition the
skill itself set.

## What goes wrong today

`/ops check` (CR-019) detects closure debt *after* it accumulates: migration corpses, folders
inactive past sixty days whose participant stream continues elsewhere, outbox items sent but
never archived. That is a sweeper, and it works. But it finds abandonment, not closure — it
cannot tell a project that ended properly from one that was dropped, because neither leaves a
record. The evidence is the same in both cases: activity stops.

A close that writes something is what makes the two distinguishable, and it is what lets the
sweeper stop reporting a finished project as debt.

## Proposal

### `project close <project> --reason <handover|delivered|abandoned> [--to <project>/<track>]`

Read-only by default, every write confirmed, in the manner of `check`.

1. **Report the open surface first.** Open rows in `_tasks.yaml` with owners and ages; outbox
   items not yet resolved; register rows naming this project; rolling-plan rows pointing at it.
   Nothing is written before this is shown — a project whose ledger still holds eleven open P1s
   is not closed, it is abandoned, and the report is what makes the operator say which.
2. **Offer the tombstone**, in the existing Retirement Convention shape, naming the reason and,
   for a handover, the receiving project and track.
3. **Unwind what `new` wrote.** The same declared `registry:` block, in reverse: the portfolio row
   moves to its closed section, the structure doc's tree entry goes. `mode: propose | write` is
   honoured exactly as on create.
4. **Ask for the evaluation, and only ask.** Where the config declares one, `project close` opens
   the evaluation document from its template with the project's own numbers already filled in
   (duration, meeting count, participants, tasks opened against closed). **It never writes the
   judgement** — what went well is human work, and a generated retrospective is worth nothing.

### Config

```yaml
lifecycle:
  close:
    evaluation:
      template: <path>          # omitted: no evaluation step
      destination: <path>
    tombstone: true             # default
```

Absent the block, `close` still reports and offers the tombstone and the register unwind. The
evaluation is the part that varies by organisation, so it is declared, never assumed.

## What this is not

- **Not an archiver.** Closing a project does not move its folder. The Archive Policy is unchanged.
- **Not automatic.** No sweeper closes a project. `check` may *report* a project that looks finished
  and suggest the command; the decision that something is done stays with a person.
- **Not a status field.** The tombstone and the register are the record. A `status: closed` key in
  a config would be a fourth register for a fact two registers already carry.

## Evidence

The practitioner's flow is recorded in a private vault conversation dated 2026-09-28. She was
not a user of these skills at the time; she described the flow she wanted before being told what
exists, which is what makes it usable as an independent instance rather than a feature request
shaped by the tool.
