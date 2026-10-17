# CR-129 — Distributing skills to an organisation through a plugin (placeholder)

| | |
|---|---|
| **Status** | **Placeholder 2026-10-17.** Scope and questions only; nothing is designed or decided. Taken up after the 2026-10-27 meeting and after CR-125 is released |
| **Contract** | none yet. Expected: additive (a packaging step; the skills themselves do not change) |
| **Date** | 2026-10-17 |
| **Area** | packaging and distribution; `ecosystem.yaml` (a possible `distribution:` block), `scripts/` (a build step), `docs/` |
| **Related CRs** | CR-125 (`/company` and its optional private template, the first skill an organisation will want to roll out with its own configuration) |

## What this is about

An organisation that adopts the skills wants to give them to many people at once, with the same version, the same
configuration and one way to update, instead of every person copying folders by hand. The skills are plain
instruction files and small scripts; how they reach a person depends on the assistant that person uses.

## Steps (order is the owner's)

1. **Claude first.** Package the skills for an organisation to install the way that assistant supports plugins
   and shared skill sets: one installable unit, a version, a way to pin and update it, and a place for the
   organisation's own configuration (`ops-config`, `company:`) that is not part of the package.
2. **Then OpenAI / ChatGPT.** Find the closest supported way to give an organisation the same instructions and
   tools (custom assistants, shared instructions, tool or app integrations, or an MCP connection).
3. **Then GitHub Copilot.** The same question for Copilot (repository or organisation instructions, agents,
   MCP).

Each step starts with research and ends with a short note on what is possible, what is not, and what a user
loses compared with step 1.

## Open questions (to answer before a design)

1. What is the unit of distribution: the whole repository, a chosen subset of skills, or a profile per
   organisation (for example the `/company` skill with its checker and nothing else)?
2. Where does an organisation keep its own configuration so that an update of the package never overwrites it?
3. Which skills depend on files outside the package (a vault, a repository, a private template) and how does the
   package say so?
4. How is a version pinned, announced and rolled back? Who may publish to an organisation's feed?
5. What can an assistant other than Claude run? Scripts need a local runtime; some assistants only read text.
   Which skills degrade to instructions only, and is that acceptable?
6. Licensing and privacy: the repository is public, a private template and customer profiles are not. The package
   must never carry them, and the build must fail if it would (the same boundary rule as the release guard).
7. Does an organisation want a private feed (its own repository or registry) or the public one?
8. What does the landing page promise, and when? Nothing is promised for steps 2 and 3 until step 1 works.

## Not in scope

- Building any of it before the research notes exist.
- Any change to how a skill behaves.
- Payment, accounts or keys (tracked elsewhere, outside this repository).
