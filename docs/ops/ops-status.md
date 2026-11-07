# Ops status — core-skills: what is released, what is configured, what waits

**Last verified: 2026-11-07 (read back on this checkout: `README.md` **Version** 1.96.0 and the first `CHANGELOG.md` entry `[1.96.1]`, which is **another session's uncommitted release in progress** -- six files are modified or untracked in this shared checkout and none of them is mine. Marvin's tracking note for contracts 48, 49 and 50 was written and committed on 2026-11-07, on its working branch and on `main`; `main` is 2 ahead of its origin and cannot be pushed from here. **Not re-checked today:** the test suite, the alignment run and the live landing page -- the 2026-11-05 reading below stands for those, and this stamp changes only sections E and G)**

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
| core-skills release | **1.95.0** (2026-11-05), contract **49**. Since the 2026-11-03 board: **1.94.2** (another session, CR-172, the privacy scan's tree walk), **1.94.3** (CR-177 -- one malformed `_insights.yaml` parsed as a list and took the whole candidate scan down, found by running the first full compile), **1.94.4** (CR-175 -- the compile backlog as one number, computed once and read by three skills) and **1.95.0** (CR-152, contract 49 -- the ledger's source vocabulary declared, shape separated from channel; 85 task findings on one vault became 60, of which 2 are genuine). Tags `v1.93.0` through `v1.95.0` are annotated and on GitHub. Still open: CR-126 (build window opened 2026-10-27) and the placeholders CR-129 and CR-130 | None | The maintainer | 2026-11-05 | [CHANGELOG](../../CHANGELOG.md) |

| Ecosystem contract | `contract_version` **49**, served by this repo from 1.95.0 and by the live landing page since 2026-11-05. Bumps since the last board: 49 (CR-152, the task source vocabulary; `task_source_types` and `task_scopes` move out of a script into the contract, each gaining one value, plus two read-only alias maps and an open `source.channel`). CR-126, CR-160 and the rest now take **50** at implementation -- each says *the next free number*, which is why none of them had to be touched this time | None | The maintainer | 2026-11-05 | [`ecosystem.yaml`](../../ecosystem.yaml) |

| Landing page | **Serving v1.95.0 / contract 49** (built and deployed 2026-11-05 from a clean worktree at the committed 2.0.24; the working checkout still carries another session's 22 uncommitted files for 2.0.25 and none of them shipped). Gate before each deploy: 16 ok, 0 failing. **`npm run build` does not run `render-og-company.mjs`**, so every build without that step silently drops the company share card the live site has -- run it first, every time. `whats_new` no longer exists (Flask-only, dropped in 2.0.0), so a release needs no content edit here | None | The maintainer | 2026-11-05 | landing repo `scripts/deploy.sh` |

| Visualiser (Marvin) | `CLAUDE.md` tracks **v1.94.1, contract 48** -- three releases behind 1.95.0. The 2026-11-03 commit is on the working branch (`f315e80`) **and on `main` (`fd1dce6`), and `main` is still not pushed**: the remote is https with no credentials in a remote session, so it needs a push from a terminal on that machine. Its tracking note is written against Marvin's code, not the contract's prose: no parser work for 47 or 48, one hazard recorded (CR-170 lets `source.audio_path` point outside the vault). **Contract 49 is unassessed.** Marvin CR-025 remains implemented, committed and unreleased -- the running process still serves 0.9.12. **Worth a CR of its own:** this line drifts on every version bump and only one host's alignment run ever notices, which is CR-175's shape one component over | Push `main`, then release Marvin (see E) | The maintainer | 2026-11-05 | `scripts/check-ecosystem-alignment.sh` |

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
| CR-165: the loop ring still renders a count with no noun | **Verified open 2026-11-05.** `LoopRing.astro` draws `{a.manual} {t.you}` -- *3 du* / *3 you* -- and the centre reads *3 av dem gör du*. That was CR-165's whole argument: the page could only render a number because the contract offered no word. Since 1.93.0 it does (`terms.checkpoint`, checkpoint / kontrollpunkt). The page already **links to an essay named for the concept** from `/the-loop` and `/arbetsloopen` while not using the word for the thing | Read `terms` and label the manual steps; it is the landing repo's change and its own release | The maintainer | 2026-11-07 | landing repo `site/src/components/LoopRing.astro` |
| CR-167: does the company-profile page carry the contrast? | **Verified open 2026-11-05.** `company-profile.astro` and `sv/bolagsprofil.astro` say *source-backed* in the description and show `interview:<date>` in the sample, so the mechanics are there. What is missing is the claim CR-167 shipped in the skill: *source-backed, not self-described -- a profile written once from memory is a different object with the same filename.* CR-167 left this to the landing repo deliberately | A positioning decision, not a defect. CR-167 itself warns the sentence reads weaker if it leans on someone else being worse | The maintainer | 2026-11-07 | landing repo `site/src/pages/company-profile.astro` |

| Marvin: a release, and a push | CR-025 is implemented and committed and the running process still serves **0.9.12**; the `hanterad` status picker for CR-120 is still unwritten. Separately, `main` is **2 commits ahead of `origin/main`** and cannot be pushed from a remote session (https remote, no credentials there) -- the tracking note for contracts 48, 49 and 50 is in both of them. Contract 49 and 50 were checked against Marvin's code, not the contract's prose: **no parser work**, because Marvin reads no `source.type`, carries `scope` without ever comparing it, and reads neither `channel` nor `source.step` | Choose a version, release it, `pm2 restart marvin`; and `git push origin main` from a terminal on that machine | The maintainer | 2026-11-07 | Marvin `docs/contract-tracking.md` |

## F. Operator steps waiting in CRs

| Step | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Move the podcast archive that prompted CR-123 to the profile | The vault runs local conventions in its project `CLAUDE.md`; nothing migrated yet | Set `profile: podcast` (and `themes.enabled` if its registry is kept), then `/insights migrate --profile podcast` as a dry run, then `--apply`; then `/ops check` on the project | The maintainer | 2026-10-13 | [CR-123](../proposals/CR-123-podcast-profile-and-insights-schema-3.md) section 8 |
| Evidence for CR-122..CR-124 in the private CR archive | The figures from the source archive are deliberately absent from the public specs; not yet written to the private archive | Record them there (`docs/RELEASING.md`, private CR archive) | The maintainer | 2026-10-13 | `docs/RELEASING.md` |

## G. Known open issues

| Issue | State | Next step | Who | Since | Source |
|---|---|---|---|---|---|
| Two files claim CR-173 | `CR-173-the-status-field-carries-prose-because-that-is-where-people-look.md` is committed and is the row the index points at. `CR-173-venture-then-project-then-the-entries.md` is **untracked in the working checkout**, written by another session that was mid-release on 1.96.1. The index says **CR-179** is next free, so that session either read a stale index or did not check. Noted, not touched: it is that session's work | Renumber the untracked file before it is committed, or confirm which claim stands | The maintainer | 2026-11-07 | `docs/proposals/` |

---

## H. Push audit, 2026-10-20

Before the push of 53 local commits, every added line, filename and commit message of the range, and of each intermediate commit (history is public too), was scanned against the private denylist, an extended list of names and ventures, and fingerprints of a private template's question text. Findings: real contact and team names in two code comments, a docstring and three commit messages; organisation names in intermediate versions of one proposal. The guard did not catch these: it reads added lines, case-sensitively, and not commit messages or intermediate history. The unpushed commits were rewritten with invented names, the private denylist was extended, and five groups were pushed through the guard. Net tree change from the rewrite: three comment lines. Lesson: scan commit messages and intermediate commits before a push.
