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
3. **Then GitHub Copilot.** The same question for Copilot in the developer tools (repository or organisation
   instructions, agents, MCP).
4. **Then Microsoft 365 Copilot (a custom agent for people who work in Office 365).** A different product from
   step 3, with its own way of building a custom agent: what the agent is told (the instructions), what it may
   read (knowledge sources such as the organisation's own document libraries, where a company profile folder
   could live), what it may do (actions or tool connections, for example a read-only connection to a template
   service), who may use it (identity and licences) and how the organisation publishes it. The open questions
   below apply, plus: where the profile files live for such an agent, how an agent without a local runtime
   runs the checks (it cannot run `company_tool.py`), and what the organisation's tenant policies allow.

Each step starts with research and ends with a short note on what is possible, what is not, and what a user
loses compared with step 1. Step 1 is also the reference for a user of Claude who installs the skill alone (no
organisation): one installable unit and the same update path.

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

## What an existing, mature organisation plugin for Claude shows (input; checked against the vendor's documentation 2026-10-18 where noted)

The detailed reading is kept outside this repository. The lessons that apply to any distribution of skills:

1. **Check delivery, not existence.** Fields and hook output that are valid can still reach nobody. A delivery check that
   runs each mechanism for real (the skill loads, a hook speaks, nothing blocks by accident) is worth more than a linter.
2. **Ship no tool-server declaration inside the plugin.** A bundled declaration loads for everyone who enables the plugin.
   Offer the connection (a skill, or a hook that suggests it) and decide the scope in code. Never put a literal secret in a
   project file; keep the address and the credential in the user's own configuration, by reference.
3. **A hook must never block by accident.** End every command with `|| true`, decide through the structured decision output
   rather than exit codes, remember that only some events inject plain output into the model, never emit an empty
   context, and give every unprompted hook a budget and an off switch.
4. **Updating is two steps and every release needs a new version.** Refresh the marketplace, then update the plugin, then
   restart; the first alone is documented as not enough in practice. A rename silently breaks installs unless a rename map
   or a migration note exists.
5. **A guard against publishing sensitive content must be a tested check** that looks at the content and the destination,
   with "ask" as the default, not only at the account.
6. **A report-a-gap skill** that masks data, records provenance and deduplicates is a cheap feedback loop.

Items the reading could not confirm (to settle before a design): that a plugin's tool-server entries cannot be declined per
project; how an organisation-synced install behaves when the account changes; whether a refresh alone leaves a stale
version installed; limits on skill front matter.

Proposed staging (no files written yet): stage 0, verify the claims above against the vendor's documentation; stage 1, a
local marketplace with the open skill only; stage 2, a delivery check (the question set is absent, no credential in any
file, hooks never block, the skill loads); stage 3, a connect skill with the address and credential by reference; stage 4,
a private marketplace only if it has something to carry.

## Not in scope

- Building any of it before the research notes exist.
- Any change to how a skill behaves.
- Payment, accounts or keys (tracked elsewhere, outside this repository).
