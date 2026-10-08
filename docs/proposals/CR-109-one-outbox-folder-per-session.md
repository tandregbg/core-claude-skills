# CR-109 — One outbox folder per session part (agenda, recap); the recap speaks the card's language; an opt-in layout says so

| | |
|---|---|
| **Status** | **Proposed** 2026-10-08 |
| **Contract** | additive for the recap and the prepare notice; **amends CR-102's "a new version is a new item"** for items that belong to one meeting session |
| **Date** | 2026-10-08 |
| **Area** | `ops` (Step 9 recap staging, `prepare` P0), `outbox` (manifest for a folder with mixed sent and unsent parts), `ops-config/schema.md` (`recap_artifact.sections` vocabulary) |
| **Related CRs** | CR-056 (a send folder is named for the session, not the artifact), CR-059 (recap on request), CR-086 (check for an existing preparation), CR-102 (a settled manifest is not written into), CR-103 (status words), CR-107 (the agenda is the card) |

Marks: **[E]** observed in a running series · **[H]** not yet run.

## What happened

A twice-weekly project standup, over one week:

1. **One session ended up in two and three folders.** The agenda was staged and sent the day before.
   The next morning new daily reports arrived; following CR-102 the update was staged as a new item,
   `<date>b-<recipient>_<subject>/`. Earlier in the week a recap had gone the same way, beside the
   session's agenda folder. The owner: *"I don't want to have multiple folders — only one folder for
   today's standup"*, and then *"align to ONE set of files"*, and then *"all content should be in the
   outbox"*. **[E]**
2. **The folder then held two versions of the same document** — the deep-dive as sent the day before,
   and the refreshed one — and two Teams posts, one sent and one not. Nothing said which was current. **[E]**
3. **The recap had no place for the milestone.** CR-107 made the agenda run toward a declared
   `milestone:`; the recap standard the venture uses predates it, and the project's `sections` preset
   still opened with a block about meeting times from an earlier cadence change. **[E]**
4. **The new agenda layout was not applied, and nothing said why.** CR-107 is opt-in
   (`layout: card`). The project had not opted in, so a run after the release generated the old layout;
   the next morning `prepare` found the existing agenda and appended to it rather than offering to
   regenerate (CR-086). The owner had asked for "the updated skills" and got the old shape without a word
   about it. **[E]**

## Findings

**CR-102 is right about manifests and wrong about folders for a session.** Its invariant — read before
writing, change only the lines you mean to change, never regenerate a manifest — prevented a lost send
record twice this week and should stay. What does not hold is the corollary that a new version must be a
new item. CR-056 already says a send folder is **named for the session, not the artifact**; a session's
agenda, its pre-meeting update and its recap are one send history, and splitting them across siblings
makes the folder listing answer *"what went to this meeting?"* wrongly.

**"Settled" is about the field block, not the folder.** A folder with one part sent and one part unsent
is still in flight. The manifest needs a way to say *which* part went, and the status needs to reflect the
part still waiting.

**An opt-in layout that is not opted into is indistinguishable from the old skill.** Nothing in the agenda,
the sources block or `prepare`'s output said that a newer layout existed and this project was not using it.

## Proposal

### 1. One folder per session (amends CR-102)

> **Revised 2026-10-08, same day:** the owner then asked for the **recap in a folder of its own**. So:
> **two folders per session** -- `YYMMDD-<who>_<what>/` for the agenda and its pre-meeting updates, and
> `YYMMDD-<who>_<what>-recap/` for the recap. Everything below applies to each folder; what it rules out
> is still the `YYMMDDb-` sibling for a new version. CR-056's "named for the session, not the artifact"
> holds for the agenda folder; the `-recap` suffix is the one deliberate exception, because the recap is a
> separate send with its own status.

For an item that belongs to a **meeting session** — agenda, pre-meeting update, recap — every later part is
added to the session's existing folder. A new sibling (`…b-…`) is created only when the owner asks for one.

- **A replaced file keeps its sent copy, never overwritten:** move the sent version to
  `_outbox/.archive/<folder>-sent-<YYMMDD>/` under its original name, then place the current version in the
  folder. The folder holds **one set of current files**; the archive holds what actually went out.
- **The manifest is still edited line by line** (CR-102 unchanged): add rows, mark them, append to
  `## Tidslinje`.
- Items that are not a session — a one-off mail, a deck sent as a deck — keep CR-102's new-item rule.

### 2. A manifest for a folder with mixed parts (outbox)

- `status` reflects the **least advanced unsent part**: `klar-att-skicka` while anything in the folder is
  unsent, even if earlier parts went out.
- `status-note` records what already went, with time (*"agenda sent <date> <time>; update staged, not yet
  sent"*).
- Each row in `## Innehåll` says **sent** (with date) or **not yet sent**.
- `/outbox list` shows such a folder as pending, and `close` refuses while any row is marked not yet sent.

### 3. The recap can carry the milestone (ops + schema)

- Add `milestone` to the documented `recap_artifact.sections` vocabulary: one block, *name — date — days
  left — what moved toward it this session*, read from the project's `milestone:` (CR-107).
- **The skill still states no counts** (CR-059): the venture's recap standard decides whether the block
  leads and how long it is. The skill only makes the milestone available to the recap, so a recap and the
  card agenda describe the same target.
- **Source boundary unchanged:** the milestone's name and date are configuration, not session content, but
  *what moved toward it* must come from the session (recap standard §2b).

### 4. Say which layout is in effect (prepare P0)

When `prepare` runs in a wired project, print the layout in use and, when the project runs `list` while
`card` is available, one line: *"this project runs layout: list; card (CR-107) is available — set
`carry_forward.layout: card` and a `milestone:`."* When an agenda for the date already exists and was
generated in a different layout from the one now configured, **offer to regenerate** rather than append.

## Out of scope

- Changing the venture's recap standard. It lives in the vault; this CR only gives it a `milestone`
  section to use.
- Retiring CR-102's manifest invariant. It stays exactly as written.

## Verification

1. Stage an agenda, mark it sent, then add a pre-meeting update: one folder, the sent agenda copy under
   `_outbox/.archive/<folder>-sent-<date>/`, `status: klar-att-skicka`, `status-note` naming what went.
2. Add a recap to the same folder after the meeting: still one folder; `close` refuses until the recap row
   is marked sent or written off.
3. A project with `milestone:` and `sections: [milestone, …]`: the staged recap opens with the milestone
   block; a project without `milestone:` silently skips that section.
4. `prepare` in a `list`-layout project prints the one-line notice; with an existing agenda generated in
   `list` and `card` now configured, it offers to regenerate.
