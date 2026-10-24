# Ops status — core-skills: what is released, what is configured, what waits

**Last verified: 2026-10-24 (read back: tags v1.92.0 to v1.92.9 on GitHub; Marvin's version reference 1.92.9 (alignment on the MacBook 7 aligned); `README.md` **Version** and `ecosystem.yaml` `core_skills_version` 1.92.9, `contract_version` 46, the first `CHANGELOG.md` entry `[1.92.9]` with no `[Unreleased]` section; the test suite on a clean checkout of `origin/main`: 975 tests OK; `scripts/check-ecosystem-alignment.sh`: 6 aligned, 0 drifted on the Mac Studio and 1 drifted on the MacBook (Marvin's version reference); Mac Studio and MacBook both level with `origin/main` at 935abc2; the live landing page reports build 2.0.24 from 1.92.9)**

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
| core-skills release | **1.92.9** (2026-10-22), contract 46 unchanged since CR-135. Since 1.92.0 (2026-10-20): 1.92.1 CR-137 (the link check), 1.92.2 Wave 1 CR-138 to CR-141 (the morning run), 1.92.3 Wave 2 CR-147 and CR-142, 1.92.4 Wave 3 CR-149, CR-121, CR-148 and CR-150, 1.92.5 Wave 4 CR-143, CR-145 and CR-151, 1.92.6 CR-155, 1.92.7 CR-156, 1.92.8 CR-157, 1.92.9 CR-154. All pushed to `origin/main`. **Git tags `v1.92.0` to `v1.92.9` all exist on GitHub** (annotated; 1.92.1 to 1.92.9 created 2026-10-24, each at the commit where the version first appears on main: 332cec7, 255dafa, ebfa6be, d364a44, 38dbfd0, c96968b, 10c12e4, d3e4633, 935abc2). Still open: CR-126 (build after 2026-10-27) and the placeholders CR-129 and CR-130 | None | The maintainer | 2026-10-24 | [CHANGELOG](../../CHANGELOG.md) |
| Ecosystem contract | `contract_version` **46**, served (live landing page, Mac Studio and MacBook). Documented bumps 43 (CR-125, `/company`), 44 (CR-127, ledger and milestone dates), 45 (CR-128, adopted raw transcript) and 46 (CR-135, ledger attributes `verksamhet`, `projekt`, `objekttyp`); no bump in 1.92.1 to 1.92.9. Schemas: insights 3, ops_config 1.6. The growth of the company-profile contract after the first bump is recorded as an amendment paragraph in the 43 comment block of `ecosystem.yaml`. CR-126 takes the next free number (47) when built | None | The maintainer | 2026-10-24 | [`ecosystem.yaml`](../../ecosystem.yaml) |
| Landing page | **2.0.24 live** (built 2026-10-22 from **v1.92.9**, contract **46**; `/mcp` still answers 401 without a token). The company profile has a front-page section and a "bring your own method" section, both languages. Alignment check: [OK]. The landing repo (private on GitHub) has uncommitted work on 2.0.25 in progress from another thread. Gateway settings checked 2026-10-20 and needed no change | None | The maintainer | 2026-10-24 | landing repo `CHANGELOG.md` |
| Visualiser (Marvin) | `CLAUDE.md` tracks **v1.92.9**, contract 46 (pushed to Marvin's `main` as 68941d2 on 2026-10-24; the MacBook's working branch `feature/CR-026-mail-section` carries the same change as 87a9bfd). The alignment check on the MacBook is [OK]: 7 aligned, 0 drifted. No Marvin work was recorded for 1.92.1 to 1.92.9 (`docs/contract-tracking.md`; not checked against Marvin's parsers beyond the changelog). Marvin CR-025 (reads profiles, consensus, voice, themes) is committed and pushed but **not released**: the running process still serves 0.9.12. The MacBook's git cannot fetch or pull from GitHub in a remote session (https remote, no credentials), so its core-skills checkout trails `origin/main` by docs-only commits until pulled there. On the Mac Studio the check reports `[SKIP]` by design: Marvin has no clone there and runs only on the MacBook | Release Marvin (see E) | The maintainer | 2026-10-24 | `scripts/check-ecosystem-alignment.sh` |
| Hosts | Mac Studio `~/repos/core-skills` and the MacBook are both **level with** `origin/main` (935abc2); local baseline tag `baseline-2026-10-18`. The Mac Studio working copy holds **other threads' uncommitted work** (`survey.py`, `build_agenda.py`, `docs/proposals/README.md`, two new CR files and a test): with it the suite shows 1 failure (`test_cr138_survey_contract`, the migration sheet gains a column the test forbids); a clean checkout passes 975. The skills in `~/.claude/skills/` are symlinks into each checkout (the `company` skill is linked on both). The system Python 3.9 on the MacBook cannot run the suite: use `/opt/homebrew/bin/python3` | None | The maintainer | 2026-10-24 | `git status -sb` on each host |

## B. Feature switches / configuration

| Item | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Pre-push guard | Fail-closed hook `scripts/githooks/pre-push`, installed per clone (`core.hooksPath`, `guard.denylist`); mode `full` for this public repo | Install on every fresh clone before its first push | The maintainer | — | [RELEASING](../RELEASING.md) "The pre-push guard" |
| Invented-examples allowlist | `scripts/githooks/allowed-examples.txt` (public, invented names only) | Adding a line is a conscious act: confirm the name is invented | The maintainer | — | same, CR-029 |
| Shared contract | `ecosystem.yaml`: skills, components, working loop, orientation; 14 skills, README table 14 rows | Keep README and `ecosystem.yaml` in step (alignment check) | The maintainer | 2026-10-12 | [`ecosystem.yaml`](../../ecosystem.yaml) |

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
| Open proposals on `origin/main`: Proposed CR-109, CR-110, CR-111, CR-112, CR-113 (rest), CR-126 (build after 2026-10-27; its Status line still says "not pushed"), CR-136, CR-152; Draft CR-144 and CR-146; placeholders CR-129 and CR-130. Implemented since the last verification: CR-080 (email half), CR-121 (1.92.4) | Proposed | Decide order and implement per release flow | The maintainer | 2026-10-24 | [Proposals index](../proposals/README.md) "Proposed" |
| Marvin release for 1.90.0 | Marvin CR-025 implemented, pushed, unreleased (`[Unreleased]` in its CHANGELOG); the `hanterad` status picker for CR-120 is still unwritten | Choose Marvin's version, release it, then `pm2 restart marvin` on the MacBook | The maintainer | 2026-10-13 | Marvin `docs/change-requests/` |
| Task source types outside the schema | The CR-122 check on one large venture of a real vault reported undeclared `source.type` values (`email`, `chat`, `analysis`, `reference` and others) across several ledgers. The tasks schema lists meeting, decision, manual, imported; `content` and `correspondence` are accepted as declared terms | Declare the recurring ones in the tasks schema, or map them in the ledgers | The maintainer | 2026-10-13 | [CR-122](../proposals/CR-122-link-yaml-and-task-hygiene-checks.md) "As implemented" |

## F. Operator steps waiting in CRs

| Step | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Move the podcast archive that prompted CR-123 to the profile | The vault runs local conventions in its project `CLAUDE.md`; nothing migrated yet | Set `profile: podcast` (and `themes.enabled` if its registry is kept), then `/insights migrate --profile podcast` as a dry run, then `--apply`; then `/ops check` on the project | The maintainer | 2026-10-13 | [CR-123](../proposals/CR-123-podcast-profile-and-insights-schema-3.md) section 8 |
| Evidence for CR-122..CR-124 in the private CR archive | The figures from the source archive are deliberately absent from the public specs; not yet written to the private archive | Record them there (`docs/RELEASING.md`, private CR archive) | The maintainer | 2026-10-13 | `docs/RELEASING.md` |

## G. Known open issues

None today.

---

## H. Push audit, 2026-10-20

Before the push of 53 local commits, every added line, filename and commit message of the range, and of each intermediate commit (history is public too), was scanned against the private denylist, an extended list of names and ventures, and fingerprints of a private template's question text. Findings: real contact and team names in two code comments, a docstring and three commit messages; organisation names in intermediate versions of one proposal. The guard did not catch these: it reads added lines, case-sensitively, and not commit messages or intermediate history. The unpushed commits were rewritten with invented names, the private denylist was extended, and five groups were pushed through the guard. Net tree change from the rewrite: three comment lines. Lesson: scan commit messages and intermediate commits before a push.
