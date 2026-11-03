# CR-166 — An orientation entry: what the vault ends up knowing about you

| | |
|---|---|
| **Area** | `ecosystem.yaml` (`orientation`), the `README.md` orientation block, the landing page `orientation` route (renders the contract, no edit needed), `scripts/` (a staleness check the block does not have) |
| **Priority** | Medium |
| **Status** | **Implemented v1.93.0** (2026-11-03) |
| **Contract** | `orientation` gains one entry. Additive; no `contract_version` bump — CR-077 established the list and adding to it is the intended use |
| **Related CRs** | **CR-077** (the orientation layer and its rule: *rendered, never restated*), **CR-062** (`working_loop`, rendered the same way and with the staleness check this one lacks), CR-125 (`/company`, one of the four things the answer names), CR-013 and CR-027 (`/insights` and the knowledge wiki, two more) |

Marks: **[E]** observed in the repository · **[H]** not yet run.

---

## The problem

CR-077 exists because *"two onboardings produced the same questions, and none of them were about the
loop: they were about the substrate"* **[E]**. The eight entries it added answer where to start, what
the prefixes mean, what is sealed, how to paste safely.

**One question of that same class is missing, and it is the one a person asks before any of the
others:** *what will this know about me when it has been running for a while?*

The suite answers it in four parts, and a newcomer can see none of them as a set **[E]**:

| What it ends up holding | Where it is produced | Where it lives |
|---|---|---|
| How the business sounds and what it may claim | `/company` | `<org>/_company/` |
| How the work is actually done | the skills and the folder's `CLAUDE.md` | the skill definitions and the config chain |
| What has been learned, and what is still a hypothesis | `/transcript`, `/ops`, `/insights` | `_insights.yaml`, `.knowledge/` |
| What reads what, and where the boundaries are | the config chain | `ecosystem.yaml`, `_ops.yaml`, `_config/base.yaml` |

Every one of these is documented. None of them is introduced alongside the others, so the README and
the landing page both lead with the **mechanism** (the loop) and never state the **result**. A person
deciding whether to adopt this is asking about the result.

**This is not a gap in the architecture.** All four exist and have for releases. It is a gap in
orientation, which is exactly what the `orientation` list was created to hold.

### A second finding, found while verifying this one

The README carries `<!-- orientation:start -->` with the promise *"Generated from `orientation` in
`ecosystem.yaml` — do not edit here (CR-077)"* **[E]**. The working-loop block makes the same promise
and `scripts/render-loop.py` enforces it with a staleness check that fails the build **[E]**.

**Nothing enforces the orientation block.** No script in `scripts/` references `orientation`, and
`scripts/check-ecosystem-alignment.sh` does not cover it **[E]**. The block can drift from the
declaration silently — which is precisely the failure CR-077's own rule was written to prevent, and
the failure the README describes elsewhere as how *"the 'what's new' list ended up seventeen releases
stale"*.

Adding an entry to a list whose rendering is unchecked is how the first copy is made.

## The change

**1. One `orientation` entry**, in the established shape (`id`, `question`, `answer`, `sources`),
with the question in the form a person actually asks it:

```yaml
- id: what_it_knows
  question: "What will this know about me once it has been running a while?"
  answer: >-
    Four things, each produced by a different part and each readable on its own.
    How the business sounds and what it may claim, kept with the source of every statement
    and checked for drift. How the work is done, which is the skills themselves and the
    folder's own config. What has been learned, separated into what is confirmed and what
    is still a hypothesis. And the declaration of what reads what, and where the boundaries
    are. None of it is a model of you: it is files you can open, correct and delete.
  sources: [vault_conventions, skills.company, skills.insights, components]
```

**The last sentence is the load-bearing one** and should not be cut for length. The question it
answers is the one behind the question asked.

**2. A staleness check for the orientation block**, modelled on `render-loop.py`: render the entries
from the declaration, compare against what is between the markers, fail on mismatch, and `--write`
to fix. Either extend `render-loop.py` to handle both blocks or add a sibling; the former is
preferable, because two scripts doing the same job is the same defect one layer up.

### Not in scope

- Naming the four as a numbered set, a diagram, or a brand. They are four answers to one question,
  not a model.
- A new page on the landing site. It renders `orientation` already; this entry appears there with no
  work in that repository.
- Reorganising `README.md`'s "Why it is shaped this way" layers (0–4). Those describe the machinery
  and are correct; this entry describes the result. See CR-168 for the one claim that section is
  missing.

## Verification

| Check | State |
|---|---|
| The entry's `sources` resolve to real declarations | **[E]** — and the check now enforces it for every entry: `render-loop.py` resolves a dotted path through the contract (a list of mappings keyed by `id`, `name` or `path`, so `skills.company` resolves). All eight pre-existing entries resolve unchanged; a bogus path is reported |
| The README orientation block, re-rendered, contains the new entry | **[E]** — and the renderer reproduces the eight existing rows **byte for byte**: the whole README diff is the one added row, which is the evidence that the generated block and the hand-maintained one were the same text |
| The new check fails on a hand-edited block and passes after `--write` | **[E]** — tried both ways, and through `check-components.py`, which the alignment check runs |
| The landing page `orientation` route shows the entry after a rebuild against the local contract | **[H]** — the landing build reads `ecosystem.yaml` locally, so this can be confirmed before any push |
| No proposed CR touches `orientation` | **[E]** verified 2026-11-03 across `docs/proposals/CR-12*` to `CR-16*` |

The check in part 2 is worth more than the entry in part 1. The entry is one answer; the check is the
reason every later answer stays true.
