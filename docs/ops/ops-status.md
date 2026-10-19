# Ops status — core-skills: what is released, what is configured, what waits

**Last verified: 2026-10-19 (read back: `README.md` **Version**, `ecosystem.yaml` `core_skills_version` 1.91.0 and `contract_version` 43, the first `CHANGELOG.md` entry, `docs/proposals/README.md` (next CR number 131), the test suite (215 tests, OK) and `scripts/check-ecosystem-alignment.sh`: 5 aligned, 1 drifted (the landing page, expected until it is deployed), visualiser skipped on the Mac Studio by design; `git log origin/main..HEAD`: 34 commits, none pushed)**

This is core-skills' own board: what is released, what is configured, what waits and on whom, for this product
only. core-skills is a sibling product family, not a Deep Thought component; Deep Thought's cross-product board and
its plan are in that repository (see `CLAUDE.md`). Rows link out; the CHANGELOG, the proposals index or
`docs/RELEASING.md` holds the detail. When a row is closed, delete it.

**The rule:** a release updates this board the same day, in the release commit or the one right after it: the
version rows in A, and any row the release closes or opens. Then re-stamp the "Last verified" line.

---

## A. Production versions / releases

| Item | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| core-skills release | **1.91.0** (CR-125 `/company`), committed on the Mac Studio only: **not pushed, not on the MacBook**. Last pushed release: 1.90.0. Since the first 1.91.0 commit the skill has grown a lot under the same number: `extract`, `coverage.yaml` and classification rules `company-coverage/3.2`, source provenance, `check --strict`, `--leak-from`, `--items-from`, config read from `_ops.yaml`, a packageable layout (`${CLAUDE_SKILL_DIR}`, schemas beside the skill). The CHANGELOG [1.91.0] entry carries it all. Placeholder and proposed CRs: CR-126 to CR-128 (other threads), **CR-129** (organisation distribution through a plugin) and **CR-130** (`export agent-core`). 34 commits ahead of `origin/main` | Decide whether the work ships as 1.91.0 or as a higher number, then push on the maintainer's word (see the contract row), then pull on the MacBook | The maintainer | 2026-10-14 | [CHANGELOG](../../CHANGELOG.md) |
| Ecosystem contract | `contract_version` **43** (CR-125, v1.91.0); highest documented bump 43. Schemas: insights 3, ops_config 1.6. **Open decision:** the company-profile contract (`skills/company/references/contract.md`, sections 1 to 9, new schemas `company-coverage` and the extended `company-sources` and `company-brands`, the `company.level_map` and `company.level_order` config keys) has grown well beyond what 43 described when it was bumped. It is additive, but a contract change bumps it in the same release, so **decide the number (44?) before the push**. CR-126 also plans 43 to 44 | Decide, bump `ecosystem.yaml` (and its comment block) in the release commit | The maintainer | 2026-10-19 | [`ecosystem.yaml`](../../ecosystem.yaml) |
| Landing page | Built from **v1.91.0**, contract 43 (build **2.0.17**, committed on the Mac Studio, 4 commits ahead, **not deployed**; the live site is 2.0.15 with the `/mcp` proxy). The company-profile page exists in both languages with the neutral level names. **It lags the contract:** it still says "the eleven rules" and does not describe `extract`, `coverage.yaml`, the classification rules or contract sections 8 and 9, so a 2.0.18 is needed before it is deployed. The alignment check reports it as drifted until then. Deploying it before core-skills is pushed would point readers at a skill that is not yet public | Write 2.0.18, push core-skills, then `scripts/deploy.sh --deploy` (`docs/RELEASING.md`, "When to update the website") | The maintainer | 2026-10-14 | landing repo `CHANGELOG.md` |
| Visualiser (Marvin) | `CLAUDE.md` tracks **v1.90.0**, contract 42 ([OK] in the alignment check on the MacBook). Marvin CR-025 (reads profiles, consensus, voice, themes) is committed and pushed but **not released**: the running process still serves 0.9.12. On the Mac Studio the check reports `[SKIP]` by design: Marvin has no clone there and runs only on the MacBook | Release Marvin (see E) | The maintainer | 2026-10-13 | `scripts/check-ecosystem-alignment.sh` |
| Hosts | Mac Studio `~/repos/core-skills` is **34 commits ahead** of `origin/main` (1.91.0 plus later work, unpushed; local baseline tag `baseline-2026-10-18`). MacBook is at `origin/main` (1.90.0) and does not have the new skill. The skills in `~/.claude/skills/` are symlinks into each checkout (the `company` skill is **not** linked on the Mac Studio). On the Studio, run the tests with `/opt/homebrew/bin/python3` | Push, then pull on the MacBook | The maintainer | 2026-10-19 | `git status -sb` on each host |

## B. Feature switches / configuration

| Item | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Pre-push guard | Fail-closed hook `scripts/githooks/pre-push`, installed per clone (`core.hooksPath`, `guard.denylist`); mode `full` for this public repo | Install on every fresh clone before its first push | The maintainer | — | [RELEASING](../RELEASING.md) "The pre-push guard" |
| Invented-examples allowlist | `scripts/githooks/allowed-examples.txt` (public, invented names only) | Adding a line is a conscious act: confirm the name is invented | The maintainer | — | same, CR-029 |
| Shared contract | `ecosystem.yaml`: skills, components, working loop, orientation; 13 skills, README table 13 rows | Keep README and `ecosystem.yaml` in step (alignment check) | The maintainer | 2026-10-12 | [`ecosystem.yaml`](../../ecosystem.yaml) |

## C. External accounts and verifications

| Item | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| GitHub secret scanning + push protection | Enabled on the repository (server-side backstop; does not know the private denylist) | — | — | — | [RELEASING](../RELEASING.md) "Server-side backstop" |

## D. Secrets and backups

Names and places only, never values.

| Item | Where | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Private push denylist | Outside this repository, in the maintainer's private store; its path is set per clone in `git config guard.denylist`. Never published | Extend it whenever a new sensitive identifier enters the working vocabulary | The maintainer | — | [RELEASING](../RELEASING.md) |
| Credentials in the repository | None. History audited once (2026-07-10): zero secrets ever committed | — | — | 2026-07-10 | same, "Server-side backstop + history" |

## E. Decisions waiting for the maintainer

| Decision | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Open proposals: CR-080, CR-109, CR-110, CR-111, CR-112, CR-113 (rest), CR-121 (the card fits the project; renumbered from CR-119) | Proposed | Decide order and implement per release flow | The maintainer | 2026-10-12 | [Proposals index](../proposals/README.md) "Proposed" |
| Marvin release for 1.90.0 | Marvin CR-025 implemented, pushed, unreleased (`[Unreleased]` in its CHANGELOG); the `hanterad` status picker for CR-120 is still unwritten | Choose Marvin's version, release it, then `pm2 restart marvin` on the MacBook | The maintainer | 2026-10-13 | Marvin `docs/change-requests/` |
| Task source types outside the schema | The CR-122 check on one large venture of a real vault reported undeclared `source.type` values (`email`, `chat`, `analysis`, `reference` and others) across several ledgers. The tasks schema lists meeting, decision, manual, imported; `content` and `correspondence` are accepted as declared terms | Declare the recurring ones in the tasks schema, or map them in the ledgers | The maintainer | 2026-10-13 | [CR-122](../proposals/CR-122-link-yaml-and-task-hygiene-checks.md) "As implemented" |

## F. Operator steps waiting in CRs

| Step | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Move the podcast archive that prompted CR-123 to the profile | The vault runs local conventions in its project `CLAUDE.md`; nothing migrated yet | Set `profile: podcast` (and `themes.enabled` if its registry is kept), then `/insights migrate --profile podcast` as a dry run, then `--apply`; then `/ops check` on the project | The maintainer | 2026-10-13 | [CR-123](../proposals/CR-123-podcast-profile-and-insights-schema-3.md) section 8 |
| Evidence for CR-122..CR-124 in the private CR archive | The figures from the source archive are deliberately absent from the public specs; not yet written to the private archive | Record them there (`docs/RELEASING.md`, private CR archive) | The maintainer | 2026-10-13 | `docs/RELEASING.md` |

## G. Known open issues

None today.
