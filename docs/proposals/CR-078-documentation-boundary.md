# CR-078 — Where a piece of documentation belongs

| | |
|---|---|
| **Status** | Proposed |
| **Contract** | additive (26 → 27), depends on CR-077 |
| **Date** | 2026-09-23 |
| **Area** | `ecosystem.yaml` (`components`), `docs/RELEASING.md` |
| **Related CRs** | CR-050 (`components:` — reads, writes, depends_on), CR-077 (orientation layer), CR-026 (public/private membrane) |

## The question this settles

An onboarding session produced a list of things a new user needs explained. Some are about the
vault; some are about the tool that records audio and assigns speakers; some are about the
terminal. The working document that captured them left *where each belongs* open, and offered
three candidates — this repo, the product's own help pages, or a README the installer drops into
the new vault.

Left open, the answer becomes *whichever was convenient*, and the same fact ends up written twice
in places that drift apart. This repo already learned that lesson from a release list that went
seventeen versions stale.

## The rule

**Documentation belongs to the component that owns the behaviour it describes.**

`components:` (CR-050) already declares each part by its role, its reads and writes, and its
direction of dependency. That declaration answers the routing question with no judgement required:

| If the fact is about | It belongs to | Because |
|---|---|---|
| A declared vault surface, prefix, placement or rule | **This repo**, via `orientation:` (CR-077) | The contract owns the surface |
| A step in the working loop | **This repo**, via `working_loop` (CR-062) | Already rendered from the contract |
| What a capture product does — recording, speakers, reprocessing, its cloud access | **That product's own help** | The behaviour is not in this contract, and this repo cannot keep it true |
| Operating system and terminal basics | **Neither** — link outward | Owning it means maintaining it forever |

**The test, for anything new:** *if this behaviour changed tomorrow, which repo's commit would
change it?* That repo documents it. If the answer is "a repo that is not this one", this repo
links and does not explain.

## Why the boundary needs saying out loud

The tempting move is to write one complete getting-started page covering everything a new user
meets, because that is what the user experiences — one continuous confusion. But a single page
spanning three components can only be maintained by the person who happens to notice all three
changing, which is one person, which is the failure this CR exists to prevent.

**The user's experience being continuous does not make the ownership continuous.** The page can
*read* as one journey while each section is owned where its behaviour lives.

## A consequence worth stating

**A documentation gap is sometimes a product defect wearing a disguise.**

Observed: after correcting a speaker, the user must remember to trigger reprocessing, or every
downstream extraction stays built on the wrong speaker — silently. That can be documented. It can
also be fixed, and if it is fixed the documentation disappears entirely.

Proposed as a standing question in the release process: **before writing documentation for a
workaround, ask whether the workaround should exist.** Documentation that describes a defect
preserves it.

## Proposed

1. **`documentation_owner` on each entry in `components:`** — one of `this_repo`, `external`, or
   `none` (link only). Additive; no existing field changes.
2. **A short section in `docs/RELEASING.md`** stating the rule and the test above, so routing is
   decided when a doc is written rather than after it drifts.
3. **The defect question** added to the same section: documentation for a workaround requires a
   note on whether the workaround is being fixed.

## Scope / non-goals

- Does not move, rewrite or delete any existing documentation. It governs what is written next.
- Does not make this repo responsible for any external product's content, and does not import that
  content. The boundary is the point.
- Does not create a docs directory structure. Where a fact renders is already answered by CR-077
  and CR-062.

## Privacy note (CR-026)

Routing rules are generic by construction. The worked examples in this CR name behaviour classes
— *a capture product*, *a cloud reader* — never a product, customer or person.
