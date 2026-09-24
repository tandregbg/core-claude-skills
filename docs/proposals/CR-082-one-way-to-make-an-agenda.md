# CR-082 — One way to make an agenda

| | |
|---|---|
| **Status** | **Implemented 2026-09-24, v1.73.0** |
| **Contract** | none (skill text + one check) |
| **Date** | 2026-09-24 |
| **Area** | `ops` (`prepare`, THE DAILY LOOP, `build_agenda.py`), `ops-config` (`carry_forward.agenda_suffix`) |
| **Related CRs** | CR-021 (slug contract), CR-061 (`/ops brief`), CR-065 (`/ops projects`), CR-072 (declared series) |

## What happened

A user asked for the preparation for a recurring standup, in a project whose loop is wired
(`carry_forward.enabled`). The result was an agenda the user did not recognise, under filenames
that did not name the project.

Two causes, and only the first was the operator's:

1. **The subcommand was offered, accepted, and never run.** The files were written from the skill
   text already in context. No P1 gathering, no triage scan, no P5 naming.
2. **Running it would not have produced the right agenda either.** The skill describes three ways to
   make one, and they disagree.

## The three descriptions

| Where | Says |
|---|---|
| `prepare`, Step P3/P5 | The model writes the agenda from the Standup Preparation Template, named `YYMMDD-agenda-[org/project]-[type].md` |
| THE DAILY LOOP, step 2 | The agenda is **generated** by `build_agenda.py` and must not be hand-edited |
| `build_agenda.py` | The filename comes from `carry_forward.agenda_suffix` — which nothing checks against the naming rule in P5 |

**`prepare` never mentions `build_agenda.py`.** So a faithful run of `/ops prepare` in a wired
project produces a hand-written, template-shaped agenda beside a loop that expects a generated one:
no carried-forward block with session counts, no round from the roster, no *Since the last standup*
block from the archives. That block is the one that carries what the transcript cannot, and it is
the one that went missing.

And a config written before the P5 rule existed names every agenda without the project, so a file
that leaves its folder — staged in `_outbox/`, attached to a chat post — says nothing about where it
came from.

## Proposal

### 1. `prepare` branches on the loop

At the top of `prepare`, before P1:

- **`carry_forward.enabled`** → run `build_agenda.py` for the agenda and its chat post. P3's template
  is **not** used. In dual mode the facilitator file is still written by `prepare`, as a layer on top
  of the generated agenda — it reads the generated file and adds only facilitator content.
- **Not enabled** → P1–P5 as today.

State it once, in `prepare`, and have THE DAILY LOOP link to it rather than restate it.

### 2. Resolve the facilitator contradiction in the same place

`prepare` (dual mode) generates a facilitator file; THE DAILY LOOP step 3 says the sheet is *not*
generated and should not be. Both are defensible; both cannot be the rule. Proposed: **`prepare`
drafts it, the facilitator owns it** — a draft is judgement offered, not judgement made. Amend step 3
to say so, and drop "should not be" from the *Must not* table.

### 3. The project name is in every prepared filename

`agenda_suffix` must contain the project slug. `/ops lint` and `list_projects.py` flag a suffix that
does not, with the rename as the offered fix. Existing files are never renamed implicitly
(`/ops normalize --filenames` remains the only route).

### 4. Check before writing

Before `prepare` saves anything, it prints which path it took (generated / template) and the
filenames it will write. A hand-written agenda in a wired project then cannot happen silently — it is
the one outcome the run announces.

## What this does not change

- The template stays for unwired series and 1-on-1s, where it is the right tool.
- `build_agenda.py`'s output format.
- The recap rules.

## Acceptance

- `/ops prepare` in a wired project produces `YYMMDD-<agenda_suffix>.md` and
  `YYMMDD-teams-<agenda_suffix>.md` via `build_agenda.py`, and the facilitator draft, and nothing
  template-shaped.
- An `agenda_suffix` without the project slug is reported by `/ops lint`.
- `prepare` and THE DAILY LOOP no longer contradict each other on who generates what.
