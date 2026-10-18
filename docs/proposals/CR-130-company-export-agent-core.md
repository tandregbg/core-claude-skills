# CR-130 — `/company export agent-core`: a compressed core of a profile for an agent with a character budget (placeholder)

| | |
|---|---|
| **Status** | **Placeholder 2026-10-18.** Scope and questions only; nothing is designed or decided. Taken up after the 2026-10-27 meeting and after CR-125 is released |
| **Contract** | Expected: additive (a new export target and an optional `company.agent_core:` block) |
| **Date** | 2026-10-18 |
| **Area** | `skills/company` (`export`), `skills/company/references/contract.md` (section 7), `ops-config` (`company.agent_core`), `docs/schemas/` |
| **Related CRs** | CR-125 (the profile and its contract), CR-126 (the export target for another platform), CR-129 (distributing skills to an organisation: Microsoft 365 Copilot as one target) |

## What this is about

Some assistants build an agent from a short instruction field and a document library the agent searches in fragments;
the instruction field can be only a few thousand characters. A company profile (all nine facets) is many times larger,
and the parts that shape every text the agent writes (tone, narrative voice, what the company never says) are the
parts that fragment search loses. A target is a **compressed core** that fits a stated character budget, plus the
**whole profile as files** for the agent's knowledge library.

## Proposal (to be designed)

- A new export target in `exports/agent-core/`: (1) `core.md`, the instruction text built from the facets in a fixed
  order (what the company is, how it speaks, the never-say list, a few examples) and cut to a configured character
  budget (`company.agent_core.max_chars`, no default shipped), with a note of what was left out; (2) the facet files
  as plain text for a knowledge library, with the source markers kept.
- The export is derived, regenerated, never edited. It contains answers only: no question wording from any attached
  question set (the leak check applies to the export too), no credentials, no staff names beyond roles.
- A check that the core fits the budget and that every statement in it traces to a facet.

## Open questions

1. Which facets and in which order go into the core, and what is the rule when the budget is too small?
2. How is a cut recorded so a reader can see what the agent does not know?
3. Is the budget a property of the target (a named platform) or a plain number in the configuration?
4. Which file format does a knowledge library index reliably, and does the export need a conversion step?
5. How does a person tell when the core is out of date after the profile changed (a hash in the export header)?
6. Where is the line between this export (for an agent that writes in the company's voice) and the skills themselves
   (CR-129)?

## Not in scope

- Building any agent. Choosing a platform. Any change to the profile contract before the questions above are answered.
