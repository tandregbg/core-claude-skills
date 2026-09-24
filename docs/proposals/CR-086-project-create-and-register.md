# CR-086 — Creating a project, and registering it where it must be found

| | |
|---|---|
| **Status** | **Implemented 2026-09-24, v1.76.0** |
| **Contract** | additive — a `registry:` config block; no existing key changes |
| **Date** | 2026-09-24 |
| **Area** | `ops` (`project new`, `prepare`, `sweep`), `ops-config` schema |
| **Related CRs** | CR-036 (placement classes), CR-040 (external task ledger), CR-065 (`/ops projects`, read-only), CR-072 (declared series), CR-085 (the sibling CR from the same session) |

## What happened

Two coordination projects were created in one sitting. **No skill creates a project**, so all of it
was done by hand:

- The folder shape — README, config, task ledger, changelog, meetings — was copied **by eye** from the
  two most recent projects.
- **Three registers were updated by hand:** the organisation's project index, the folder tree in its
  instructions file, and a hand-written portfolio at the vault root.
- **A row graduated from a rolling plan into its own project.** It had to be annotated *moved — linked,
  not copied* in two plans, by hand, with nothing to say it was done.
- **A preparation was nearly written twice.** One for the same meeting, same day, same participants
  already existed from the day before. Only a manual search found it.

And the argument for doing this at all, from the same session: **a parallel session had already added
one of the register rows.** Two sessions editing one register is not a discipline problem — it is what
happens when a register has no code path.

## Proposal

### 1. `/ops project new <name>` — one way to create a project

Scaffolds the five artefacts in the organisation's projects tree, resolved from config: README with
roles, status and cadence; the ops config; a v2 task ledger; a changelog with its first entry; an
empty meetings folder.

**Team aliases are seeded from the organisation's declared roster, never re-typed.** A hand-copied
roster is where a misspelling enters and then resolves to nobody.

Options worth supporting:

- `--from-meeting <summary>` — the first changelog entry and the README's meetings row point at it.
- `--pre-phase-of <project>/<track> --exit "<criterion>"` — writes the pre-phase block into the README
  and a task-ledger note naming the **parent's** register as the source of open questions. A pre-phase
  that keeps its own register is a second register for one body of work (CR-040's shape, applied to a
  sibling project).
- **Check before create.** Refuse if the folder exists; glob for near-names and ask. A project created
  under a second spelling is invisible to everything that looks for the first.

### 2. Register after create — declared, never hardcoded

A `registry:` block, resolved through the normal config chain, naming the registers a new project must
appear in and how each may be written:

- **`mode: propose` is the default for a hand-written register.** Such a register carries *judgement* —
  a role, a sponsor, a mode of engagement — that the skill cannot know. It fills what it does know
  (name, status, owner, one-line purpose, link) and leaves the judgement columns marked for a person.
- `mode: write` for generated indexes, which carry no judgement.
- **Idempotent.** If a row already exists, verify the link and do nothing else. This is what makes two
  sessions harmless rather than merely unlikely.
- **Unconfigured means skip, silently.** A vault that does not declare registers is not misconfigured.

### 3. Graduation: a plan row becomes a project

`--graduates <plan>#<row>` annotates the row in place — *moved to X on DATE; linked, not copied, the
row stays as history* — in **every** plan that carries it, and seeds the new README from the row.

This is the existing golden rule made executable: one item, one owner, one document. A row copied
rather than linked becomes two rows that disagree within a week.

### 4. `/ops prepare` checks before it writes

Glob the target folder and its siblings for a preparation, agenda or facilitator file matching the
meeting **date and participants**. If one exists, report it and offer: open it, regenerate it from
current sources, or write anyway.

`build_agenda.py` already refuses to overwrite an agenda. The hand-prepared path has no equivalent,
which is the whole of the gap.

### 5. `/ops sweep` — one new finding

A project folder with an ops config but **no row in any configured register** is a finding, with the
proposed row as the fix. This catches projects created before this CR, and any created by hand after
it.

## Acceptance

- `/ops project new` produces the five artefacts; aliases come from the declared roster.
- Registers updated per config; a hand-written register goes through propose; **a second run is a
  no-op**.
- Graduation annotates every plan carrying the row.
- `/ops prepare` on a meeting that already has a preparation reports it instead of writing a second.
- `/ops sweep` flags an unregistered project.
- `working_loop` and `ecosystem.yaml` updated; `check-components.py` passes; release guard and
  semantic review pass.

## Decided 2026-09-24 — the four questions the draft left open

### 1. A separate verb: `/ops project new`

`/ops projects` (CR-065) stays read-only. **A read-only command that sometimes writes is harder to
trust than two commands**, and the read-only guarantee is the reason that one is safe to run without
thinking.

### 2. `registry:` is declared at both layers, merged by the config chain

Not either/or. A vault can hold a **cross-venture portfolio** at its root and a **per-organisation
index** inside each organisation, and both are registers a new project must appear in:

```yaml
# vault layer — the portfolio, declared once
registry:
  projects:
    - path: <vault-root portfolio>
      section: <table name>
      mode: propose

# organisation layer — that organisation's own index
registry:
  projects:
    - path: _projects/README.md
      section: "Active Projects"
      mode: propose
```

The chain merges them, so a project in an organisation that declares an index gets **two** rows, and
one in an organisation that declares none gets the portfolio row only. **An organisation without an
index is not misconfigured** — it has one register, which is a legitimate shape and the common one
early on.

### 3. The skill fills what it knows; judgement columns are left marked

A portfolio row typically carries: name, venture, type, **the owner's own role**, status, **sponsor or
mode**, and where it runs.

| The skill fills | Left for a person |
|---|---|
| Name, venture, type, status (`New <date>`) | **The owner's role**, sponsor/mode, where it runs |

The division is not about effort, it is about what can be known. **A role column can legitimately
contain a question** — an owner writing *"contributing?"* about their own involvement is recording an
open question, and a skill that filled that cell would turn a question into an assertion.

Marked, not blank: the proposed row shows the judgement columns as placeholders so an unfilled one is
visible rather than merely empty.

### 4. "Pre-phase of a track" stays a README convention

`--pre-phase-of <project>/<track> --exit "<criterion>"` writes the README block and the note that open
questions stay in the parent's register. **No declared lifecycle, no tombstone automation.**

There is one instance of this shape. **A lifecycle declared on a single case is a guess** — the three
parts (exit criterion, handover to a track, tombstone on close) are each real, but whether they recur
together often enough to earn contract fields is not yet known. If a second pre-phase appears and
wants the same three, that is its own CR with evidence behind it.
