# core-skills — project guidelines

Claude Code skills for operational documentation, transcript processing, task tracking and team
coordination, with a knowledge loop (insights corpus, standing rules, knowledge wiki). Start with
`README.md`; the shared contract every skill and companion tool reads is `ecosystem.yaml`. This
repo is **public** and the vault it runs on is production data: `docs/RELEASING.md` (CR-026) is
the release process and its privacy guardrails, enforced by the pre-push guard.

## CRs, releases, versions

- CRs are `CR-nnn` here (`CS-CR-nnn` seen from other repos). The public index is
  `docs/proposals/README.md` (generic title rows only); full specs stay in the private archive.
- Releases go in `CHANGELOG.md`, newest first; `README.md` **Version** and `ecosystem.yaml`
  `core_skills_version` match the first entry. Run `scripts/check-ecosystem-alignment.sh` before
  a release commit; one release is one commit.
- This repo's own ops board is `docs/ops/ops-status.md` (index `docs/ops/README.md`): what is
  released, what is configured, what waits. Start here for this product; a release updates it the
  same day.
- A checkout may be shared: commit only your own files; never stash, reset or discard
  someone else's work.

## Deep Thought

core-skills is a sibling product family, not a Deep Thought component, and nothing in it is a
Deep Thought dependency. It is the **other way to use Deep Thought's output**: a user who does
not want the platform's own processing (its extraction and insights) runs Claude Code with
core-skills on Deep Thought's content instead, read over the MCP tools, the Public API or the
meeting handover (`deep-thought-handover`, which runs `/transcript` on one Deep Thought transcript
in an isolated workspace). In Deep Thought's five steps that is step 3 *Asked* and step 4 *Kept*.

- The contract read is Deep Thought's: `docs/reference/public-api.md` and the MCP tools in the
  `deep-thought-server` repository. A change there that breaks a skill is a Deep Thought CR.
- Deep Thought's state and plan live in that repository too: `docs/ops/ops-status.md` (what runs
  now) and the Waves table in `docs/change-requests/README.md`; the ecosystem map, including this
  family's row, is `docs/architecture/ecosystem-components.md`.

## Never

- Commit real names, organisations, hosts, internal addresses or credentials (`docs/RELEASING.md`).
- Use emojis in code, docs or commit messages.
