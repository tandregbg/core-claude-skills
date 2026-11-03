# Ops status — core-skills: what is released, what is configured, what waits

**Last verified: 2026-11-03 (read back on this checkout: `README.md` **Version** and `ecosystem.yaml` `core_skills_version` **1.93.1**, `contract_version` **47**, the first `CHANGELOG.md` entry `[1.93.1]` with no `[Unreleased]` section; the test suite: **1036 tests, 0 failures** (987 with 9 errors before 1.93.1 re-derived CR-138's contract tests); `scripts/check-ecosystem-alignment.sh`: **5 aligned, 1 drifted** (the landing page, which still serves 1.92.9 / contract 46 against 1.93.1), the visualiser `[SKIP]` on this host by design. **Not re-checked:** the git tags, the other host, Marvin's own parsers and the live landing build -- the 2026-10-24 reading below each row remains the last word on those)**

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
| core-skills release | **1.93.1** (2026-11-03), contract **47** -- published for the first time by this release, having sat on `main` since 2026-10-25 with no CHANGELOG entry, which is why this is a minor. Ships CR-165 (the `checkpoint` term), CR-166 (the orientation entry **and** the staleness check the block never had), CR-167 (`/company` says it is source-backed), plus CR-162 and CR-163, which were committed before it. **CR-168 was rewritten instead of merged**: its own merge gate required the claim be read back against the code, and two input paths build a durable layer from what a person said (`/company intake`, `/insights scan-claude-md`) -- see E. Previous: 1.92.0 to 1.92.9 (2026-10-20 to 2026-10-22), tags `v1.92.0` to `v1.92.9` on GitHub. **1.93.1** followed the same day: CR-138's contract tests re-derived against CR-162's output, and six stale claims in the `/inbox survey` section corrected, so the suite is green again at 1036 tests. 1.93.0 is pushed; **neither version is tagged yet**. Still open: CR-126 (build window opened 2026-10-27) and the placeholders CR-129 and CR-130 | Tag `v1.93.0` and `v1.93.1`, then the landing page and Marvin (version changed) | The maintainer | 2026-11-03 | [CHANGELOG](../../CHANGELOG.md) |

| Ecosystem contract | `contract_version` **47**, served by this repo from 1.93.0; the live landing page still serves 46. Documented bumps 43 (CR-125, `/company`), 44 (CR-127, ledger and milestone dates), 45 (CR-128, adopted raw transcript), 46 (CR-135, ledger attributes) and 47 (2026-10-25, `external_systems.linkedin` -- definitional only, nothing here reads it). Schemas: insights 3, ops_config 1.6. CR-165 and CR-166 add to `terms` and `orientation` without a bump: a vocabulary or list addition is not a shape change. **The numbering is settled** (the 2026-11-03 addendum, now closed): CR-126 and CR-152 say *the next free number at implementation* and name 48 as today's value instead of carrying a constant that rots; CR-160 needed no change, its own numbering note already explains why its bump is 47 to 48. Whichever of the three lands first takes 48 | None | The maintainer | 2026-11-03 | [`ecosystem.yaml`](../../ecosystem.yaml) |

| Landing page | **2.0.24 live** (built 2026-10-22 from **v1.92.9**, contract **46**; `/mcp` still answers 401 without a token). The company profile has a front-page section and a "bring your own method" section, both languages. Alignment check: [OK]. The landing repo (private on GitHub) has uncommitted work on 2.0.25 in progress from another thread. Gateway settings checked 2026-10-20 and needed no change. **Drifted as of 1.93.0**: the alignment check reports it one release and one contract behind | Rebuild and deploy from v1.93.0 / contract 47; the new `orientation` entry appears with no edit in that repo, and CR-167's paragraph probably belongs in its hand-written company-profile copy (its own release) | The maintainer | 2026-11-03 | landing repo `CHANGELOG.md` |
| Visualiser (Marvin) | `CLAUDE.md` tracks **v1.92.9**, contract 46 (pushed to Marvin's `main` as 68941d2 on 2026-10-24; the MacBook's working branch `feature/CR-026-mail-section` carries the same change as 87a9bfd). The alignment check on the MacBook is [OK]: 7 aligned, 0 drifted. No Marvin work was recorded for 1.92.1 to 1.92.9 (`docs/contract-tracking.md`; not checked against Marvin's parsers beyond the changelog). Marvin CR-025 (reads profiles, consensus, voice, themes) is committed and pushed but **not released**: the running process still serves 0.9.12. The MacBook's git cannot fetch or pull from GitHub in a remote session (https remote, no credentials), so its core-skills checkout trails `origin/main` by docs-only commits until pulled there. On the Mac Studio the check reports `[SKIP]` by design: Marvin has no clone there and runs only on the MacBook. **Now also one release behind**: its version reference reads 1.92.9 against 1.93.0 | Release Marvin (see E), then move its version reference to 1.93.0 | The maintainer | 2026-11-03 | `scripts/check-ecosystem-alignment.sh` |
| Hosts | The checkout this release was made in is **ahead of `origin/main` by 3 commits** (CR-165..168 proposed, the board addendum, and the 1.93.0 release commit) and holds no other thread's uncommitted work. The other host was not read in this session: its 2026-10-24 state above stands until someone checks it. Local baseline tag `baseline-2026-10-18`. The skills in `~/.claude/skills/` are symlinks into each checkout. The system Python 3.9 on the MacBook cannot run the suite: use `/opt/homebrew/bin/python3` | Push; then pull on the other host | The maintainer | 2026-11-03 | `git status -sb` on each host |

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
| Open proposals: Proposed CR-109, CR-110, CR-111, CR-112, CR-113 (rest), CR-126 (build window opened 2026-10-27; its Status line still says "not pushed"), CR-136, CR-152, CR-153, CR-158, CR-159, CR-160, CR-161, CR-164, **CR-168 (rewritten)**; Draft CR-144 and CR-146; placeholders CR-129 and CR-130. Implemented since the last verification: CR-162, CR-163 (both before this release), CR-165, CR-166, CR-167 (1.93.0) | Proposed | Decide order and implement per release flow | The maintainer | 2026-11-03 | [Proposals index](../proposals/README.md) "Proposed" |
| CR-168: one sentence in README layer 1 | **The claim was corrected, the sentence not yet written.** The CR asserted that the layers are built from the record of work and never from a description; its gate required that be read back against the code, and two paths build a durable layer from what a person said -- `/company intake` (an owner's interview answers, recorded as a dated `interview:<date>` source) and `/insights scan-claude-md` (a folder's `CLAUDE.md`, promotable to a loaded rule). Neither is a defect. The claim the suite keeps is *recorded, dated and attributable, never recall at the moment of writing* | Write the README sentence and the heading in a later release, reading the corrected claim cold | The maintainer | 2026-11-03 | [CR-168](../proposals/CR-168-built-from-the-record-not-from-memory.md) |

| Marvin release for 1.90.0 | Marvin CR-025 implemented, pushed, unreleased (`[Unreleased]` in its CHANGELOG); the `hanterad` status picker for CR-120 is still unwritten | Choose Marvin's version, release it, then `pm2 restart marvin` on the MacBook | The maintainer | 2026-10-13 | Marvin `docs/change-requests/` |
| Task source types outside the schema | The CR-122 check on one large venture of a real vault reported undeclared `source.type` values (`email`, `chat`, `analysis`, `reference` and others) across several ledgers. The tasks schema lists meeting, decision, manual, imported; `content` and `correspondence` are accepted as declared terms | Declare the recurring ones in the tasks schema, or map them in the ledgers | The maintainer | 2026-10-13 | [CR-122](../proposals/CR-122-link-yaml-and-task-hygiene-checks.md) "As implemented" |

## F. Operator steps waiting in CRs

| Step | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Move the podcast archive that prompted CR-123 to the profile | The vault runs local conventions in its project `CLAUDE.md`; nothing migrated yet | Set `profile: podcast` (and `themes.enabled` if its registry is kept), then `/insights migrate --profile podcast` as a dry run, then `--apply`; then `/ops check` on the project | The maintainer | 2026-10-13 | [CR-123](../proposals/CR-123-podcast-profile-and-insights-schema-3.md) section 8 |
| Evidence for CR-122..CR-124 in the private CR archive | The figures from the source archive are deliberately absent from the public specs; not yet written to the private archive | Record them there (`docs/RELEASING.md`, private CR archive) | The maintainer | 2026-10-13 | `docs/RELEASING.md` |

## G. Known open issues

None today. CR-138's nine erroring contract tests, opened by CR-162 and recorded here this
morning, were re-derived in 1.93.1 the same day; the CHANGELOG holds what the re-derivation found.

---

## H. Push audit, 2026-10-20

Before the push of 53 local commits, every added line, filename and commit message of the range, and of each intermediate commit (history is public too), was scanned against the private denylist, an extended list of names and ventures, and fingerprints of a private template's question text. Findings: real contact and team names in two code comments, a docstring and three commit messages; organisation names in intermediate versions of one proposal. The guard did not catch these: it reads added lines, case-sensitively, and not commit messages or intermediate history. The unpushed commits were rewritten with invented names, the private denylist was extended, and five groups were pushed through the guard. Net tree change from the rewrite: three comment lines. Lesson: scan commit messages and intermediate commits before a push.
