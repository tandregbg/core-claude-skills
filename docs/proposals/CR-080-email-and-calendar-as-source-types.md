# CR-080 — Email and calendar objects as source types

| | |
|---|---|
| **Status** | Proposed |
| **Contract** | additive (28 → 29, assuming CR-077/078/079 land first; renumber if they do not) |
| **Date** | 2026-09-24 |
| **Area** | a new `/correspondence` skill, `_inbox/` classification, `vault_conventions` |
| **Related CRs** | **CR-012** (inbox schema), **CR-015** (attribution safety), CR-024 (`_inbox/.files/`), CR-032 (`Kanonisk källa`), CR-036 (singleton placement), CR-075 (a fourth channel into one place), CR-079 (bulk import) |

## The problem

An email arrives — pasted into a session today, fetched over a protocol later. It carries
decisions, commitments and dates that belong in the vault. There is no skill that takes it.

What happens instead is that `/transcript` gets used, because it is the skill that turns
"something someone said" into a summary in the right folder. **That is the wrong instrument,
and it is wrong in a way that is easy to miss** because the output looks fine.

`/transcript` exists to solve a problem an email does not have: turning *speech* into *text*,
and recovering who said what from a stream that may not say. Its whole apparatus — undiarized
detection, owner downgrading to `?`, ASR near-miss spelling checks against folder precedent —
is machinery for **recovering structure that the source lost**.

An email lost nothing. It arrives with the sender in a header, the recipients enumerated, the
timestamp exact, the thread identified, and every name spelled the way its owner spells it. Run
it through the transcript route and the pipeline spends its effort second-guessing facts it was
handed, and — worse — **discards the structure it was given**, because the summary format has
nowhere to put a `Message-ID`, a cc list, or a thread's position in a chain.

A calendar object is the same shape with a different tense: it is *structured, and about the
future*.

## Not the inbox, despite the name

The obvious reading is that this belongs in `/inbox`, and it does not. **`/inbox` is the vault's
logical intake** — the door where anything unclassified waits to be routed. It is named for a
concept the mail world happens to share a word with, and that collision is the only reason the
idea suggests itself.

`/inbox` would still be the *route in*: a pasted email is an inbox item, classified and handed
to a downstream skill, exactly as a voice memo is. **What is missing is the downstream skill.**
`/inbox`'s classification table (SKILL.md step 2) maps signals to `transcript`, `ops`, `task`,
`note`, `idea`. Step 1 already detects `email` as a *content type*. There is no classification
row for it, so detection leads nowhere — the item is detected as email and then routed as
something else.

This CR proposes the missing target.

## What it is for: context, not a client

**The purpose is to build context in the structure that already exists** — a contact's folder,
a project's folder — from material that currently only builds context in a mail client, where
no skill can read it.

Stated as a non-goal because it is the failure this would fail as: **this is not a mail client
and not a calendar app.** It does not send, reply, file, flag, schedule, accept or decline. It
reads an object that already exists somewhere else and writes what the vault should know about
it. Every channel keeps its own behaviour; nothing here takes over any of them.

## The six things that need deciding

These are the decisions the skill cannot make silently, and the reason this is a CR rather than
a patch.

### 1. Object identity — what is the unit?

A transcript's unit is obvious: one recording, one meeting, one file. An email's is not.

A single message is usually too small to be worth a file. A thread is usually the right unit —
but a thread can run for months, cross topics, and split. Proposed: **the unit is the thread,
and the file is appended to as the thread continues**, which means an email file is a *living*
document where a transcript is a frozen one. That difference propagates: a frozen file is
written once and dated by its event, a living one needs a last-updated marker and a rule for
where new material goes (newest first, or appended in order — this CR proposes **newest first**,
so the current state is at the top where a reader lands).

The identity key is the thread's `References`/`In-Reply-To` chain, not the subject line, which
gets edited and reused.

### 2. Routing is per *ärende*, not per person

The meeting-routing table routes by participant, because a meeting is an event between people.
Correspondence is not: a thread with one person can be entirely about a project, and a project
thread can have six participants who each have their own contact folder.

**The subject of the thread decides the folder, not the sender.** A thread with a supplier about
a specific project belongs in the project; a thread with the same supplier about terms belongs
in their contact folder. This inverts the default the routing table sets, so it must be stated
rather than inherited — and the human-in-the-loop gate (below) is where it gets settled when the
answer is not obvious.

### 3. Participant roles — cc is not a participant

An email distinguishes `From`, `To` and `Cc`, and the distinction carries meaning a summary
format has no column for: a person on cc was *informed*, not *engaged*. Flatten them into one
participant list and the record claims six people were in a conversation two people had.

Proposed: roles are preserved in the file's frontmatter — `from`, `to`, `cc` as separate keys —
and **only `from`/`to` may own an action item**. A cc recipient owning a task is almost always
an attribution error, and this is the CR-015 rule applied to a source where the evidence is
actually available.

### 4. What the gate asks

Human-in-the-loop is the requirement, and an open-ended prompt is not a gate. `/inbox` already
has the right shape (step 4: "one question, then go"), so this inherits it with a specific
question:

> **Ny fil, eller uppdatering av `<befintlig fil>`?**

That is the one decision the skill genuinely cannot make — thread matching is a heuristic, and
a wrong merge silently corrupts two records at once, while a wrong split is visible and cheap to
fix. Proposed default: **when in doubt, propose the new file**, because the failure is recoverable.

Everything else — folder, filename, participant roles — is shown alongside as a proposal to
override, not asked as a second question.

### 5. Calendar has cases email does not

A calendar object is the same *shape* but not the same *thing*, and three cases have no email
equivalent:

| Case | The question it raises |
|---|---|
| **Recurring** | One object, many occurrences. Does the vault record the series, the occurrence, or both? Proposed: **the occurrence**, since that is what a meeting summary attaches to — the series is metadata on it. |
| **Moved or cancelled** | The object mutates after it is recorded. A cancelled meeting that already has a preparation file is a real state, not an error. |
| **RSVP** | Who accepted is *not* who attended, and recording the former as the latter is a fabricated participant list. |

These are the reason calendar is named in this CR but may reasonably ship after email: the email
half is well understood, the calendar half has open questions that deserve their own pass.

### 6. The raw form — open, and it must not be settled by the implementation

CR-079 established the principle for bulk import: raw transcripts land in `.transcripts/`
directly, **so the seal applies from the first minute** rather than being applied retroactively.

An email has a raw form too, and it is exactly the kind of thing that seal exists for: full
headers, `Message-ID`, the complete `References` chain, the original encoding — the audit trail
behind the record. But it is not a transcript, and `.transcripts/` is declared for transcripts.

This CR does not decide the question, and says so rather than letting the first implementation
decide it silently. Two defensible answers:

| Answer | What it costs |
|---|---|
| **The record carries the identity; the raw form is discarded.** Frontmatter keeps `message_id`, thread key and participant roles — enough to re-fetch or re-match — and the wire form is not kept | Nothing can be re-derived if the record is later found wrong. Re-fetching assumes the source still exists and is still reachable |
| **The raw form is kept behind a seal.** Either `.transcripts/` widens to *raw source material* generally, or correspondence gets its own sealed surface | A new surface is a contract change, and widening `.transcripts/` changes what a name means — the exact failure CR-068 was written about |

**This is a prerequisite, not a detail.** A raw email is materially more sensitive than a
transcript of a meeting the user attended: it carries other people's words verbatim, addressed
privately, with routing metadata attached — in an iCloud-synced vault. Deciding it by default,
in code, is how the wrong answer gets made permanent.

Related: this is the same question CR-075 raises about meeting recordings (*where is the line
between my working material and the organisation's material that happens to pass through me?*),
at lower cost per object and far higher volume. An email costs nothing to pull in; a recording
costs a deliberate act. That asymmetry is the reason to answer it before building, not after.

## What this composes with

- **`/outbox` is unchanged and is not replaced.** Outbox is *outgoing material the vault
  produced*. This is *incoming material the vault received*. A thread that the vault both sends
  into and receives from touches both, and they stay separate — the manifest's `Kanonisk källa`
  (CR-032) is where an outbox item points at the correspondence record, not a reason to merge them.
- **CR-079 (bulk import)** is the same material at a different volume. A mailbox export is a dump
  with no destination until read, which is exactly what `_inbox/.import/` was proposed for. This
  CR defines the per-object shape; CR-079 defines how a few thousand of them arrive.
- **CR-075's framing** — three archives are *three channels into one place* — is the frame this
  extends. Email and calendar are channels five and six.

## Scope / non-goals

- **Does not send, reply, schedule, or modify anything in a mail or calendar system.** Read-only
  toward the source, by construction.
- **Does not specify a protocol or a fetcher.** Paste is the input today; a fetcher is a separate
  component and a separate CR. This defines what the vault does with the object once it has it.
- **Does not replace `/transcript`.** A recorded meeting is still a transcript. The two meet only
  where a calendar object and a meeting summary describe the same event, and there the calendar
  object is context for the summary, not a competing record of it.
- **Does not change `/inbox`'s intake behaviour** — it adds a classification target so the
  `email` content type step 1 already detects has somewhere to go.
- **Does not introduce a new vault surface.** Correspondence lands in the contact and project
  folders that already exist. A source type is not a place.
- **Does not decide where the raw form goes** — named as open in decision 6, deliberately. A
  sealed surface for raw correspondence, if one is wanted, is a contract change and belongs in its
  own CR rather than being introduced as a side effect of this one.
