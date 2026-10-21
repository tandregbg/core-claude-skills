# CR-140 — A pre-flight check before the agenda: ready, stale or missing, per source

| | |
|---|---|
| **Status** | **Implemented v1.92.2** (2026-10-21) |
| **Contract** | additive — one flag (`--check`), no change to the agenda's shape; the background-run guidance is documentation |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`build_agenda.py`, SKILL.md step 9), `ops-config` (`reports`, `vault_reports`, `chats`) |
| **Related CRs** | CR-116 (vault reports), CR-117 (the *Built from* line), CR-119 (validate the config first), CR-088 (a fetch record says whether it worked), CR-139 (the default date) |

## What happened

Across seven mornings an assistant hand-wrote the same pre-flight in a scheduled prompt: are the chat and
repository fetches fresh and successful, is the status author's current report dated today, do today's
report files exist, does the previous note exist? Each morning the answer came from the assistant's own
shell commands. Three things went wrong that a command would have caught:

- **Two report folders were renamed and their files re-titled overnight.** The config still pointed at the
  old paths, so the generator would have called both reports missing. It was found by the assistant
  listing a folder, not by the tool.
- **The status report was three days old** on a Monday morning. The generator flagged it (*3d old*), but
  only after a three-minute build.
- **A fetch failed twice in one morning** (*none of 5 repositories could be read*). The agenda's repo-detail
  section silently used the last good data; only the fetch's own status file said so.

**[E]** The build takes about three minutes and exceeds the default foreground command limit, so a
check that needs the build to find a missing source finds it three minutes late.

## Proposal

1. **`build_agenda.py --check`** prints one table and exits non-zero on any *stale* or *missing* source:

   | Source | State | Time |
   |---|---|---|
   | chat fetch | ready / stale / **failed** | last success |
   | repository fetch | ready / stale / **failed** | last success |
   | each declared `reports:` entry | ready / **N days old** | commit date |
   | each `vault_reports:` entry | ready / **missing: directory not found** | newest file |
   | previous note | ready / **missing: close-out not written** | file |
   | recording source | checked / **not checked** | — |

2. **A missing report directory prints where a similarly named directory exists** (same parent, shared
   word), so a rename reads as *config stale*, not *source missing*.
3. **`--check` is fast** (no repository reads beyond one status call per declared report) and is what a
   scheduler runs. The full build is documented as long-running: SKILL.md says to run it in the background.
4. **A failed fetch is named in the agenda header**, in one line, not only in the fetch's own file.

## Acceptance

- A renamed report directory is reported as stale config with the new path suggested.
- A three-day-old status is reported by `--check` in seconds.
- A failed fetch appears in the agenda header.
