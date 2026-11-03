# CR-165 — The checkpoint has a name

| | |
|---|---|
| **Area** | `ecosystem.yaml` (`terms`), `scripts/check-terms.py` (coverage follows from the entry), the prose in `ops-base`, `ops`, `transcript`, `outbox` and `company` where the idea is currently spelled out ad hoc |
| **Priority** | Medium |
| **Status** | Proposed (2026-11-03) |
| **Contract** | `terms` gains one entry. Additive; **no `contract_version` bump** — a `terms` row is a vocabulary addition, not a shape change (CR-164's precedent, which adds to the same list without naming a bump) |
| **Related CRs** | **CR-089** (one term per concept — the rule this uses), **CR-062** (`working_loop`, where `manual` and `why_manual` live), **CR-164** (also adds to `terms`; the two entries do not collide, but whichever lands second rebases its position in the list) |

Marks: **[E]** observed in the repository · **[H]** not yet run.

---

## The problem

The suite has a load-bearing idea with no name: **the place where a person must decide, because
generating the obvious answer would be confidently wrong in a way the reader could not check.**

It is declared three times in `working_loop`, as `manual: true` with a reason **[E]**:

| step | `why_manual` |
|---|---|
| facilitate | The agenda carries facts; which question to ask is judgement, not generation |
| recap | Whether a session warrants a recap is a judgement about the audience, not about the material |
| record | That click is where the posted message gets read as it actually landed |

The same principle is enforced in at least five other places, each in its own words **[E]**: the
sealed surfaces (`.transcripts/` read-seal, `.handoff/` total seal), `/ops` that observes and never
acts, the `?` / `Name?` owner safety of CR-015, the `[gap]` a profile writes instead of guessing
(CR-125), and the `[fyll i]`-style refusal to invent that several skills carry in prose.

Three consequences follow from it having no term:

1. **The landing page can only render a count.** `LoopRing.astro` draws `3 you` — a number with no
   noun, because the contract offers none **[E]**.
2. **`check-terms.py` cannot keep the prose consistent**, because there is nothing to be consistent
   with. The phrases that compete for the idea are not tracked.
3. **A reader meeting the idea in one place cannot tell it is the same idea elsewhere.** The gap
   marker, the seal and the manual step read as three unrelated design decisions.

## The change

One entry in `terms`:

```yaml
- {id: checkpoint, en: checkpoint, sv: kontrollpunkt,
   note: "the place where a person decides because generated confidence would not be checkable;
          declared by `manual: true` in working_loop, and the same principle behind every seal,
          every gap marker and every refusal to infer an owner",
   avoid: ["approval step", "sign-off", "human in the loop"]}
```

**The three avoided phrases are the reason the entry earns its place**, not decoration:

- *approval step* and *sign-off* describe a gate the finished work passes through. The claim here is
  the opposite — the checkpoint **is** the work, not a stage after it.
- *human in the loop* places the person inside a machine process as one of its components. The
  suite's arrangement is the other way round: the process serves the person who owns the outcome.

**This CR coins nothing.** The word is already in published prose — the insight *The checkpoint is
the job*, which the landing page's loop page links with the note *"Why the three manual steps stay
manual"* **[E]**. The entry moves a word already in use into the contract so every surface renders
the same one.

### Not in scope

- Renaming `manual` or `why_manual`. The field names are fine; they lacked a noun, not a shape.
- Any new page, section or layer.
- Changing which steps are manual.

## Verification

| Check | State |
|---|---|
| `scripts/check-terms.py` passes with the entry present | **[H]** |
| The three `avoid` phrases are flagged where they occur in skill prose | **[H]** — run before merge; the result decides whether this is vocabulary hygiene or a real drift |
| No collision with CR-164's `terms` additions (`Konversationstyp` / `Conversation type`) | **[E]** verified 2026-11-03 against the CR-164 file |
| `contract_version` unchanged | **[E]** by construction |

A count worth taking before merge **[H]**: how many places in `skills/**/*.md` state the principle
in their own words. If the answer is the five already identified, this is hygiene. If it is
substantially more, the next CR is consolidation, not vocabulary.
