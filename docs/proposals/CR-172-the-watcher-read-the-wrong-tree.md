# CR-172 — The watcher read the wrong tree, and called an empty read clean

| | |
|---|---|
| **Status** | **Implemented v1.94.2** (2026-11-03), contract unchanged (48) |
| **Contract** | none — a defect in `scripts/privacy-scan.sh` and the test that was missing |
| **Date** | 2026-11-03 |
| **Area** | `scripts/privacy-scan.sh`, `tests/test_cr172_privacy_scan_tree.py` |
| **Related CRs** | CR-029 (the privacy watcher), CR-043 (allow-lines), CR-026 (the release process) |

## What happened

`privacy-scan.sh --tree` built its file list with `git -C "$REPO" ls-files`, which prints
**repo-relative** paths, and piped them into `xargs -0 cat` running in **the caller's** directory.

The declared command in a vault config is
`bash ~/repos/core-skills/scripts/privacy-scan.sh --tree`, and `/ops check` runs it **from the vault
root**. So the watcher read the vault.

**[E] Measured 2026-11-03.** Run from a vault, it reported **six `[FINDING]` lines against the private
denylist** — two person names, a mail domain, a host prefix and two venture slugs. *(The patterns are
not reproduced here: a public document naming them is the leak the denylist exists to prevent. This CR
was itself caught by the gate on its first draft for doing exactly that — see the note at the end.)*
**Every one of the six was the vault's own `CLAUDE.md`**, which is private by design and is not in the
repository. Proof is positional: the line the scan flagged as number 19 is a structural table row in
the vault's file and `- A checkout may be shared: commit only your own files …` in the repository's.
Run from the repository the same command answered `[OK] privacy-scan clean (--tree)`.

**The second effect is the one that made it invisible.** A path existing **only** in the repository
made `cat` fail, and `2>/dev/null` ate the error, so the file was skipped **in silence**. Most of the
repository was never scanned.

**[E] And the worst case is not a wrong answer but a confident one.** Writing the regression test
produced it: run from a directory that shadows *nothing*, every `cat` fails, `INPUT` is empty, and the
script takes its own early exit —

```
[OK] privacy-scan: nothing to scan        # exit 0
```

**A clean bill of health on zero bytes read.** The `nothing to scan` branch exists for the legitimate
empty case and cannot tell it from a total read failure.

**Four months.** The script dates from 2026-07-10. The watcher's purpose, in its own header, is that a
leak *"is caught within a week, not at the next audit"* — and it had been answering a different
question for that whole period.

## Why the risk was bounded, and this is not a leak report

**The blocking gate was never affected.** `scripts/githooks/pre-push` pipes the pushed range's added
lines through `--stdin`, whose branch is `INPUT="$(cat)"` — **no path resolution, no working
directory**. It is armed (`core.hooksPath = scripts/githooks`, so the absent `.git/hooks/pre-push` is
correct) and the denylist resolves and is readable, 82 patterns.

So two independent layers agree: the gate ran on every push, and a correct full-tree scan today is
clean. **Nothing leaked.** What was lost is the *second* layer — the one that catches something
already in history: pushed with `--no-verify`, from a machine without the hooks path, or committed
before the hook existed. The gate sees added lines in a push; only the sweep sees the tree.

**The class is one instance, not a pattern.** `check-ecosystem-alignment.sh` resolves `SCRIPT_DIR`
from its own location and has no working-directory dependency; its results from the vault were valid.

## The fix

`cat` runs **in** the repository, and a tracked file that cannot be read is **reported rather than
swallowed** — because an unscanned file is not a clean one:

```bash
ERRFILE="$(mktemp)"
INPUT="$(cd "$REPO" && git ls-files -z -- … | xargs -0 cat 2>"$ERRFILE")"
UNREADABLE="$(cat "$ERRFILE")"
```

```
[FINDING] privacy-scan could not read N tracked file(s) -- those are UNSCANNED:
```

Keeping `2>/dev/null` and only fixing the directory would have left the silent half free to return
under any other cause — a permission, a broken link, a file deleted but still in the index.

## The test is the deliverable

A defect invisible for four months is a **missing test**, not a missing line. Five tests, each
building a throwaway git repository with the script inside it so `REPO` resolves to the fixture and
the real repository is never touched:

| Test | Asserts |
|---|---|
| `same_verdict_from_any_directory` | the answer does not depend on where it was started |
| `a_colliding_name_outside_the_repo_is_not_scanned` | the measured failure: a same-named file in the caller's tree is not read |
| `a_repo_only_file_is_read` | the silent half — a file with no counterpart **is** scanned |
| `an_unreadable_tracked_file_is_reported_not_skipped` | tracked, absent on disk → a finding, not silence |
| `stdin_mode_resolves_no_paths` | the gate never had this bug, and keeps not having it |

**[E] Validated against the defect, not only the fix: 4 of the 5 fail on the old script and all 5
pass on the new one.** The fifth passes on both, correctly — it is the one that documents why the
exposure was bounded, and a test that cannot fail against the old code would have been decoration.

## Acceptance

- `--tree` gives the same verdict from any working directory. ✅
- A file only the repository has is scanned. ✅
- A tracked file that cannot be read is named and fails the run. ✅
- `--stdin` is unchanged. ✅
- The tests fail against the pre-fix script. ✅

## The gate caught this CR, which is the strongest evidence in it

The first draft of this file reproduced the six denylist patterns verbatim, to show what had been
reported. Staged, it was **untracked** — and `--tree` reads `git ls-files`, so the clean run taken
after the fix never saw it. The pre-push gate did, on the added lines, because `--stdin` reads what is
being pushed rather than what is tracked.

**And the fixture needed the same discipline.** The planted string has to trip the scanner, so the
first version used an address from the measured vault — caught too. It is now a built-in *command*
pattern, assembled at runtime so the literal never appears in the file. No tracked file in the
repository contains a built-in pattern and the hook excludes nothing; a test is a poor reason to
become the first exception, because an exclusion for `tests/` is a hole somebody later puts a real
credential through.

Two conclusions worth keeping. **The two layers are not redundant** — one reads the tree, the other
reads the change, and this file existed in exactly the gap between them. And **the evidence in a
privacy finding is itself private**: a report that quotes what it found carries the finding into one
more file, which is the mistake CR-150 already recorded for per-person figures and which applies here
without having been written down.

## One thing left for the operator, not fixed here

**On the measured vault the denylist file lives under an `.archive/` path**, pointed to by
`git config guard.denylist` on both machines. The vault's own `stale_vs_junk` rule says `.archive/` is
for material that **was** current and is now outdated; a denylist is a live, fail-closed dependency
read on every push, and if it becomes unreadable the gate loses every pattern it holds. A placement
question, and the operator's — noted here because it was found in the same pass and nothing else would
record it. *(The path is deliberately not written out: this repository is public, and where a vault
keeps its denylist is a fact about that vault.)*
