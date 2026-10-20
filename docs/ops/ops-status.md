# Ops status — core-skills: what is released, what is configured, what waits

**Last verified: 2026-10-20 (read back after the push: landing page 2.0.19 live and the alignment check 6 aligned; `origin/main` equals local `main`; `ecosystem.yaml` `contract_version` 45; the test suite (282 tests, OK); `scripts/privacy-scan.sh --tree` clean; the push audit in section H)**

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
| core-skills release | **1.91.0** (CR-125 `/company`), **pushed to `origin/main` on 2026-10-20 in five CR groups; not yet pulled on the MacBook**. Last tagged release: 1.90.0; no release number is chosen for the pushed work. Since the first 1.91.0 commit the skill has grown a lot under the same number: `extract`, `coverage.yaml` and classification rules `company-coverage/3.2`, source provenance, `check --strict`, `--leak-from`, `--items-from`, config read from `_ops.yaml`, a packageable layout (`${CLAUDE_SKILL_DIR}`, schemas beside the skill). The CHANGELOG [1.91.0] entry carries it all. **Unreleased, committed after the 1.91.0 entry:** CR-127 (`closed:` and milestone history), CR-128 (adopt a raw transcript archived at delivery), CR-131 to CR-133 and CR-134 (outbox). Still open: CR-126 (build after 2026-10-27), placeholders **CR-129** (organisation distribution through a plugin) and **CR-130** (`export agent-core`). level with `origin/main` | Decide whether the work is released as 1.91.0 or as a higher number (the `[Unreleased]` entries then move under it), then pull on the MacBook | The maintainer | 2026-10-14 | [CHANGELOG](../../CHANGELOG.md) |
| Ecosystem contract | `contract_version` **46** in the checkout; documented bumps 43 (CR-125, `/company`), 44 (CR-127, ledger and milestone dates), 45 (CR-128, adopted raw transcript, the last one served) and 46 (CR-135, ledger attributes `verksamhet`, `projekt`, `objekttyp`, committed 2026-10-20, not yet served: the landing page and Marvin still read 45). Schemas: insights 3, ops_config 1.6. **Proposal (45, unchanged for 43 to 45):** do not renumber those three. The growth of the company-profile contract after the first bump (coverage, provenance, strict checks, `level_map`, `level_order`) is additive and was never served as 43, so it is recorded as an amendment paragraph in the 43 comment block of `ecosystem.yaml` (done 2026-10-20) instead of a new number. CR-126 is rewritten to take the next free number (46) when built. **45 was pushed 2026-10-20; 46 is local** | None | The maintainer | 2026-10-19 | [`ecosystem.yaml`](../../ecosystem.yaml) |
| Landing page | **2.0.21 deployed 2026-10-20** (rebuilt against contract 46, no content change; 2.0.20 added the front-page company section) (the company profile has a section on the front page, and 'bring your own method' is the message on its page, both languages) (live: `/`, `/sv`, `/company-profile`, `/sv/bolagsprofil` 200; shows contract 46; `/mcp` still answers 401 without a token). Built from **v1.91.0**, contract 46. The company-profile page, in both languages, follows the contract: 18 rules, the three machine files, sources and citations, coverage, `extract`, the strict checks. Alignment check: 6 aligned, 0 drifted on the Mac Studio. The landing repo (private on GitHub) is pushed up to 2.0.20 (68607c4); 2.0.21 is committed locally. The four gateway steps from the deploy script were checked on 2026-10-20 and needed no change: the route already has `sitemap_enabled = False`, `robots_mode = 'proxy'` and `block_ai_crawlers` off; none of its 88 learned paths is a 404 (83 answer 200, 5 redirect); and the gate with `--live` is 17 ok, 0 failing, 3 skipped (`sitemap-truth`: all 60 advertised URLs answer 200) | None | The maintainer | 2026-10-20 | landing repo `CHANGELOG.md` |
| Visualiser (Marvin) | `CLAUDE.md` tracks **v1.91.0**, contract 46 (updated 2026-10-20 on the MacBook, branch `feature/CR-026-mail-section`, committed locally, not pushed; [OK] in the alignment check there: 7 aligned, 0 drifted); no parser work was needed for 1.91.0 (see its `docs/contract-tracking.md`). Marvin CR-025 (reads profiles, consensus, voice, themes) is committed and pushed but **not released**: the running process still serves 0.9.12. On the Mac Studio the check reports `[SKIP]` by design: Marvin has no clone there and runs only on the MacBook | Release Marvin (see E) | The maintainer | 2026-10-13 | `scripts/check-ecosystem-alignment.sh` |
| Hosts | Mac Studio `~/repos/core-skills` is **level with** `origin/main` (1.91.0 plus later work and the CR-127 to CR-134 batch, pushed 2026-10-20; local baseline tag `baseline-2026-10-18`). MacBook fast-forwarded to `origin/main` (1.91.0 plus later work, contract 45) on 2026-10-20; 282 tests OK there with `/opt/homebrew/bin/python3` (the system Python 3.9 cannot run the suite); the alignment check there is clean since Marvin's `CLAUDE.md` was updated (2026-10-20). The skills in `~/.claude/skills/` are symlinks into each checkout (the `company` skill was linked on the Mac Studio and the MacBook on 2026-10-20). On the Studio, run the tests with `/opt/homebrew/bin/python3` | None | The maintainer | 2026-10-19 | `git status -sb` on each host |

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
| Open proposals: CR-080, CR-109, CR-110, CR-111, CR-112, CR-113 (rest), CR-121 (the card fits the project; renumbered from CR-119), CR-126 (build after 2026-10-27) | Proposed | Decide order and implement per release flow | The maintainer | 2026-10-12 | [Proposals index](../proposals/README.md) "Proposed" |
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
