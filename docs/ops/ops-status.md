# Ops status — core-skills: what is released, what is configured, what waits

**Last verified: 2026-10-12 13:30 (read back: `README.md` **Version**, `ecosystem.yaml` `core_skills_version` and
`contract_version`, the first `CHANGELOG.md` entry, `docs/proposals/README.md`, and
`scripts/check-ecosystem-alignment.sh`: 6 aligned, 0 drifted, visualiser skipped)**

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
| core-skills release | **1.89.10** (CR-119, validate the configuration first). `README.md` **Version**, `ecosystem.yaml` `core_skills_version` and the first `CHANGELOG.md` entry agree | Next release per `docs/RELEASING.md` | The maintainer | 2026-10-12 | [CHANGELOG](../../CHANGELOG.md) |
| Ecosystem contract | `contract_version` **41** (CR-115, v1.89.4); highest documented bump 41 | A contract change bumps it in the same release | The maintainer | 2026-10-08 | [`ecosystem.yaml`](../../ecosystem.yaml) |
| Landing page | Built from **v1.89.10**, contract 41 (its build 2.0.13), read back by the alignment check | Rebuild and deploy on every `core_skills_version` change (`docs/RELEASING.md`, "When to update the webpage") | The maintainer | 2026-10-12 | `scripts/check-ecosystem-alignment.sh` |
| Visualiser | Not checked: the alignment check reports `[SKIP]` (no checkout where it looks). A skip is unverified, not clean | Run the check where the visualiser checkout exists | The maintainer | 2026-10-12 | same |
| Unreleased work on main | CR-120 (handled is not sent) committed as **Proposed** with code and tests; no CHANGELOG entry, `[Unreleased]` empty | Release it (CHANGELOG, README, version bump, index row), or mark it as not yet released in the index | The maintainer | 2026-10-12 | [CR-120](../proposals/CR-120-handled-is-not-sent.md) |

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
| Open proposals: CR-080, CR-109, CR-110, CR-111, CR-112, CR-113 (rest), CR-120, CR-121 (the card fits the project; renumbered from CR-119) | Proposed | Decide order and implement per release flow | The maintainer | 2026-10-12 | [Proposals index](../proposals/README.md) "Proposed" |
| v1.90.0: CR-122 (hygiene checks), CR-123 (podcast profile, insights schema 3), CR-124 (themes registry) | Proposed 2026-10-13; decisions taken (profile key `profile:`, all three in one minor, `voice` generic, `consensus` counted in status, follow-up vs task set by profile). Contract 41 to 42 | Implement and release as one commit; same day: Marvin CR-025 and the landing page (What's new, both languages) | The maintainer | 2026-10-13 | [CR-123](../proposals/CR-123-podcast-profile-and-insights-schema-3.md) |

## F. Operator steps waiting in CRs

None today.

## G. Known open issues

| Issue | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Two proposals share the number CR-119 | `CR-119-validate-the-configuration-first.md` (Implemented v1.89.10) and `CR-119-the-card-fits-the-project-and-the-session.md` (Proposed, untracked) | Renumber the proposed one (CR-108 is the precedent) and fix its index row | The maintainer | 2026-10-12 | [Proposals index](../proposals/README.md) |
| The proposals index lags | CR-120 has a spec file but no index row; "Next available CR number" still says CR-120 | Add the row and bump the next number | The maintainer | 2026-10-12 | same |
