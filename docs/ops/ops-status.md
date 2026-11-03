# Ops status — core-skills: what is released, what is configured, what waits

**Last verified: 2026-11-03 (read back on this checkout: `README.md` **Version** and `ecosystem.yaml` `core_skills_version` **1.94.1**, `contract_version` **48**, the first `CHANGELOG.md` entry `[1.94.1]` with no `[Unreleased]` section; the test suite: **1085 tests, 0 failures**; `scripts/check-ecosystem-alignment.sh`: **5 aligned, 1 drifted** (the landing page, which still serves 1.92.9 / contract 46 against 1.94.1), the visualiser `[SKIP]` on this host by design. **Not re-checked:** the git tags, the other host, Marvin's own parsers and the live landing build -- the 2026-10-24 reading below each row remains the last word on those)**

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
| core-skills release | **1.94.1** (2026-11-03), contract **48** -- published for the first time by this release, having sat on `main` since 2026-10-25 with no CHANGELOG entry, which is why this is a minor. Ships CR-165 (the `checkpoint` term), CR-166 (the orientation entry **and** the staleness check the block never had), CR-167 (`/company` says it is source-backed), plus CR-162 and CR-163, which were committed before it. **CR-168 was rewritten instead of merged**: its own merge gate required the claim be read back against the code, and two input paths build a durable layer from what a person said (`/company intake`, `/insights scan-claude-md`) -- see E. Previous: 1.92.0 to 1.92.9 (2026-10-20 to 2026-10-22), tags `v1.92.0` to `v1.92.9` on GitHub. **1.93.1** followed the same day: CR-138's contract tests re-derived against CR-162's output, and six stale claims in the `/inbox survey` section corrected, so the suite is green again at 1036 tests. **1.94.0** closed the day: CR-169 (the two drop zones and their ageing), CR-170 (audio has an exit, with the `mdat` verification shipped as code) and CR-171 (a vault's file names are data, with the check that keeps them out of the suite) -- contract 48, one bump for three additive changes, 1085 tests. **1.94.1** followed within the hour: the first vault to adopt CR-170 declared its audio destination in its own config, which the contract had never said was the place to declare it -- the resolution (contract default, vault config wins) and the config schema for `vault_conventions:` and `view_files:` are now written down. Tags `v1.93.0` (at 3effbc7) and `v1.93.1` (at 5df6593) are annotated and on GitHub** (created 2026-11-03, each at the commit where the version first appears on main, per the convention used for `v1.92.*`). Still open: CR-126 (build window opened 2026-10-27) and the placeholders CR-129 and CR-130 | The landing page and Marvin, both of which the version change left behind | The maintainer | 2026-11-03 | [CHANGELOG](../../CHANGELOG.md) |

| Ecosystem contract | `contract_version` **48**, served by this repo from 1.94.0; the live landing page still serves 46. Documented bumps 43 (CR-125, `/company`), 44 (CR-127, ledger and milestone dates), 45 (CR-128, adopted raw transcript), 46 (CR-135, ledger attributes) 47 (2026-10-25, `external_systems.linkedin` -- definitional only, nothing here reads it) and **48** (2026-11-03, CR-169/CR-170/CR-171: the third drop zone and `stale_after_days`, the audio exit with `audio_archive` and the three pointer fields, the grandfather clause as a test and `view_files`). Schemas: insights 3, ops_config 1.6. CR-165 and CR-166 add to `terms` and `orientation` without a bump: a vocabulary or list addition is not a shape change. **The numbering is settled, and settled again**: 48 went to this release, so CR-126, CR-152 **and CR-160** now all say *the next free number at implementation* and name 49 as today's hint. CR-160 had been correct at 1.93.0 and was wrong a fortnight later, which is the argument for the wording rather than for the number. Whichever of the three lands first takes 49 | None | The maintainer | 2026-11-03 | [`ecosystem.yaml`](../../ecosystem.yaml) |

| Landing page | **2.0.24 live** (built 2026-10-22 from **v1.92.9**, contract **46**; `/mcp` still answers 401 without a token). The company profile has a front-page section and a "bring your own method" section, both languages. Alignment check: [OK]. The landing repo (private on GitHub) has uncommitted work on 2.0.25 in progress from another thread. Gateway settings checked 2026-10-20 and needed no change. **Drifted as of 1.93.0**: the alignment check reports it one release and one contract behind | Rebuild and deploy from v1.93.0 / contract 47; the new `orientation` entry appears with no edit in that repo, and CR-167's paragraph probably belongs in its hand-written company-profile copy (its own release) | The maintainer | 2026-11-03 | landing repo `CHANGELOG.md` |
| Visualiser (Marvin) | `CLAUDE.md` tracks **v1.92.9**, contract 46 (pushed to Marvin's `main` as 68941d2 on 2026-10-24; the MacBook's working branch `feature/CR-026-mail-section` carries the same change as 87a9bfd). The alignment check on the MacBook is [OK]: 7 aligned, 0 drifted. No Marvin work was recorded for 1.92.1 to 1.92.9 (`docs/contract-tracking.md`; not checked against Marvin's parsers beyond the changelog). Marvin CR-025 (reads profiles, consensus, voice, themes) is committed and pushed but **not released**: the running process still serves 0.9.12. Checked from the MacBook on 2026-11-03 at 1.93.1: its alignment run reports **2 drifted** -- Marvin's `CLAUDE.md` at v1.92.9 against v1.93.1, and the landing page. On the Mac Studio the check reports `[SKIP]` by design: Marvin has no clone there and runs only on the MacBook. **Now also one release behind**: its version reference reads 1.92.9 against 1.93.0 | Release Marvin (see E), then move its version reference to 1.93.0 | The maintainer | 2026-11-03 | `scripts/check-ecosystem-alignment.sh` |
| Hosts | **Mac Studio** `~/repos/core-skills` is **level with `origin/main`** (5df6593), clean, and is where 1.93.0 and 1.93.1 were made. All **14 declared skills are symlinked** into it: `correspondence` was missing until 2026-11-03 and is now linked, so `/correspondence` had shipped for releases without being available on this machine. `md2pdf` points at the personal skill repo, which is correct since 1.79.0; the untracked `skills/md2pdf/` folder left in this checkout is a pre-1.79.0 leftover that no symlink reads. **The MacBook** `~/repos/core-skills` is also **level with `origin/main`** and clean, fast-forwarded from `3470aa6` (it was 8 behind), with the same 14 skills linked -- `correspondence` was missing there too and is now linked. Its suite: **1036 tests OK, 1 skipped** (`pdftotext not installed`, so the `/company extract` PDF path is untested and unusable there until poppler is installed). Reached over the private mesh network; **its login name differs from the Mac Studio's**, which is what made an earlier attempt from this host look like an access refusal rather than a wrong user. **Correction to the 2026-10-24 reading:** its remote is SSH (`git@github.com:...`), not https, and `git fetch` works non-interactively from a remote session -- the note that it could not fetch or pull was wrong. Local baseline tag `baseline-2026-10-18`. The skills in `~/.claude/skills/` are symlinks into each checkout. The system Python 3.9 on the MacBook cannot run the suite: use `/opt/homebrew/bin/python3` Install poppler on the MacBook if `/company extract` is wanted there | The maintainer | 2026-11-03 | `git status -sb` on each host |

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
