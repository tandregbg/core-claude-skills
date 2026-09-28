# CR-101 — A generated agenda is a draft: read what it counted, pull requests, and closure evidence that can be contradicted

| | |
|---|---|
| **Status** | **Proposed** 2026-09-28 |
| **Contract** | additive — one optional `reads:` value honoured, one new agenda block, no key renamed |
| **Date** | 2026-09-28 |
| **Area** | `ops` (`build_agenda.py`, `prepare` Step P0, Pre-Meeting Retrieval), `ops-config/schema.md` |
| **Related CRs** | CR-055 (repo archive), CR-058 (*since the last standup*), CR-071 (read every chat), CR-076 (say when nothing was declared), CR-082 (one way to make an agenda), CR-084 (sources block, probably-closed) |

## What happened

A wired project, twice-weekly standup. `/ops prepare` ran `build_agenda.py`, which printed:

```
19 chat message(s) since 260924 — read them for the facilitator sheet; they are not printed into the agenda
260924-daily-standup.md -> 260928-agenda-<project>-standup.md  (11 carried, 1 at 3+ sessions; 3 chat, 1 repo)
```

The agenda was reported as done. The owner opened it and asked why the proper agenda had not been
made. Four gaps, each plausible on its own, stacked into an agenda that looked complete and was
missing most of what the room needed:

| # | Gap | What the agenda showed | What the sources held |
|---|---|---|---|
| 1 | No `people:` roster in the file carrying `carry_forward` | `## Round` heading, zero rows, no warning | Attendees declared under `meeting_types.<type>.participants`, a key the generator does not read |
| 2 | Chat content deliberately not printed | Message counts only | Three merged PRs, a distributed build, five open asks with no owner, a dependency waiting four days on another team |
| 3 | Repo reader handles `issues` only | `issues not in declared reads — skipped` | The repo declares `reads: [docs, pulls, releases]`; the archive holds **200 pulls**. Work lives in PRs, not issues |
| 4 | Probably-closed matches a done-word anywhere in a message | Build item listed as probably closed | The matched message was *"Android build is failing … I have fixed and raised a PR"*; the next day: *"Issue was not solved after my fix."* |

And a fifth, in the process rather than the script: nothing in `prepare` says the counted messages
must be read before the agenda is reported. The script said *read them*; the run did not, and the
instruction has no owner.

## Findings that shape the proposal

**1. The documentation and the script disagree about the chat block, and neither is what the room
needs.** Pre-Meeting Retrieval says `build_agenda.py` *writes a "Since the last standup — not said in
the room" block into the agenda*. The script's own comment says the archive is *deliberately NOT
printed*, because raw message lines in a team-facing document are noise and quoting colleagues back
at the room reads as surveillance. The script's reasoning is right about **quotes** and wrong about
**facts**: *build 764 was distributed*, *the endpoint the switch depends on has no owner*, *Web has
not confirmed the paths* are not surveillance, they are the agenda. The distinction is a digest of
facts versus a reproduction of messages — and a digest is a judgement a stdlib script cannot make.

**2. An empty round is a configuration miss that renders as a finished section.** CR-076 already
established the rule: *say when nothing was declared, as distinct from declared-but-empty.* The round
breaks it. `if people:` skips the table and leaves the heading, so a project with no roster and a
project whose roster is all `adjacent` look identical, and both look done.

**3. The data for pull requests is already archived and unread.** `.githubmeta/<repo>/*.json` carries
`pulls` beside `issues`; the reader returns early on `"issues" not in reads`. On a repository that
tracks work in a separate ticket system, that early return makes the repo appendix permanently empty.

**4. Done-words are evidence of a claim, not of a state.** *"fixed"* in *"I have fixed and raised a
PR"* claims an attempt. The matcher takes the first message with two shared words and a done-word, so
it will prefer early claims over later contradictions — the opposite of what evidence ordering should
do.

## Proposal

### 1. The round says when it has no roster

When `people` resolves empty, write the table header and one line in its place:

```
No roster: `people:` is not declared beside `carry_forward` in <file>. The round has no rows.
Attendees found under `meeting_types.<type>.participants`: A, B, C — declare them as `people:`.
```

The second line only when `meeting_types.*.participants` exists; **never populate the round from
it** — that key describes a schedule, not a round order, and inferring one from the other is how an
`adjacent` person gets a permanent empty row. Print the same message to stdout. `/ops check <folder>`
check 2c reports it.

### 2. The agenda carries a digest slot; `prepare` fills it

`build_agenda.py` writes, when any declared chat has messages since the last note:

```markdown
## Since the last standup — not said in the room

<!-- DIGEST: 19 messages since 260924 (standup chat 18, UI/UX 1). Not yet read. -->
```

The marker is what makes an unread digest visible: an agenda whose file still contains
`<!-- DIGEST: … Not yet read. -->` is a draft, and `/ops orient` reports it as such in block 1
(*"next agenda: generated, digest not filled"*).

`prepare` Step P0 gains a required step after generation: **read the counted messages and replace
the marker with a digest** — facts, not quotes:

| In the digest | Not in the digest |
|---|---|
| What landed (PR, build, release), with its reference | Message text reproduced |
| Asks with **who is waiting on whom**, owner or `no owner named` | Who said what, beyond naming the requester of an ask |
| Dependencies on another team, with how long they have waited | Anything personal, or off-topic, in a work chat |
| Corrections to *Probably closed* evidence | |

Round rows may be extended from the digest (*"test build 764"*), and the sources block gets one line:
`digest filled by prepare <date>` — so a hand-completed agenda says so, and the "never hand-edited"
rule (THE DAILY LOOP, *What each step must not do*) is amended to: *the generated sections are not
hand-edited; the digest slot is filled by `prepare`, once.*

**`prepare` does not report the agenda as done while the marker remains.** This is the process gap:
a generator that counts and a caller that does not read are two halves that each assume the other.

The Pre-Meeting Retrieval text is corrected to describe this split, so the documentation and the
script agree.

### 3. Pull requests, when `pulls` is declared

Where `reads:` contains `pulls`, the repo reader returns PRs updated since the last note: opened,
merged, closed unmerged, and **open and awaiting review** with age. The appendix groups them that way;
the chat post gets one line (*"Repo since the last note: 3 merged, 2 awaiting review (oldest 3 days)"*).
Merged PRs join the probably-closed evidence. `issues` keeps its current behaviour; the skip note is
printed only when **neither** `issues` nor `pulls` is declared.

### 4. Closure evidence can be contradicted

- Evidence per item is the **newest** matching message, not the first.
- A matching message containing a negative (`failing`, `failed`, `not solved`, `broken`, `reverted`,
  `still`) is counter-evidence; a newer negative cancels an older positive.
- Precedence: a merged PR or published release that matches outranks a chat message.
- The evidence cell shows the message's date and time, so the room can see which message was used.

The rule stays as CR-084 wrote it: nothing is ever dropped, the room confirms.

## Out of scope

- Summarising chats in the script. The digest is judgement; it stays with `prepare`.
- Reading a ticket system that is not declared. `tickets NOT DECLARED` remains the honest output.
- Inferring `people:` from attendance. Check 2c already reports mismatches; the roster remains the
  project's to change.

## Verification

On the project that surfaced this, regenerate the 260928 agenda from the 260924 note:

1. With the roster removed: the round prints the no-roster line naming the participants key.
2. The agenda contains the digest marker; `/ops orient` reports *digest not filled*.
3. The repo appendix lists the PRs merged and awaiting review since 260924.
4. The build item's evidence is the newest matching message; with the 25 Sep contradiction present it
   is not listed as probably closed on a chat claim alone.
