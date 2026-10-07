---
name: correspondence
description: Record a two-way thread with a person -- email, chat or message exchange -- as a living document that is appended to as the thread continues. Preserves sender and recipient roles per turn, never a participant list. One-way incoming material is `content` instead; a recording is a transcript.
user-invocable: true
argument-hint: <pasted thread, or path to a file containing it>
---

# /correspondence -- Two-way threads with a person

A thread where turns alternate and a decision may be reached in the exchange. The distinguishing
test is **not the channel but whether anyone replied** (CR-080).

**Standalone skill** -- works with any vault that has contact or project folders. Reads
`ops-config` for folder conventions and `strings.filename_keywords.correspondence`.

| Shape | What it is | Skill |
|---|---|---|
| **transcript** | A recording of an event the user was in | `/transcript` |
| **content** | One-way incoming material: a report, a newsletter, an automated digest (CR-105) | `/ops process` |
| **correspondence** | **A two-way thread with a person** | **this skill** |

---

## Subcommands

### `/correspondence <input>` (the default)

Record a thread. `<input>` is the pasted thread, or a path to a file containing it.

### `/correspondence help`

Show the shapes table, the three rules, and the routing rule.

---

## The three rules that make this shape different

These are not style preferences. Each one exists because flattening it loses information that
cannot be recovered.

### 1. No participant list, ever

A meeting has participants. A thread has a **sender and recipients, per turn**. Writing
`**Deltagare:** A, B, C` claims three people were in a conversation two people had.

Record turns with direction instead:

```markdown
**Turer:** B → A (6/10 10:42) · A → B, kopia C (6/10 15:22) · B → A (6/10 15:52)
```

### 2. cc is informed, not engaged -- and may not own an action

`From`, `To` and `Cc` carry meaning. A person on cc was *informed*. Keep the roles separate in
frontmatter, and **only `from` and `to` may own an action item**.

A cc recipient owning a task is almost always an attribution error. This is CR-015's attribution
rule applied to a source where the evidence is actually present.

### 3. The record keeps the identity; the raw form is not kept

**`.transcripts/` is for transcripts. A pasted mail is not one.** Writing one there is a finding,
not a convention (CR-080 decision 6, answered 2026-10-01).

| Keep | Discard |
|---|---|
| Sender, recipients with roles | Full headers |
| Timestamp per turn | Complete `References` chain |
| `message_id` and thread key where available | Original encoding |
| The substance: figures, decisions, commitments | Quoted history below the reply |

Three reasons, in order of weight: consent does not transfer (a mail is written *by* someone
else, *to* the user, with an expectation about where it goes); the re-derivation argument is
weaker than it looks (what matters is the figures and the decision, and both survive in the
record); and widening a seal changes what its name means (CR-068).

State it in the file so a reader is not left wondering:

```markdown
**Råmaterial:** behålls inte (CR-080). Avsändare, mottagare och datum står ovan.
```

---

## Execution steps

### Step 1: Identify the thread

The unit is **the thread, not the message**. A single message is usually too small to be worth a
file.

The identity key is the `References`/`In-Reply-To` chain where available, **not the subject
line**, which gets edited and reused. Working from a paste, reconstruct the chain from the quoted
history and the timestamps.

### Step 2: Find an existing file for this thread

Search the likely folders for a file whose thread key matches, or failing that, whose subject and
participants match. A living document is appended to; a new thread gets a new file.

### Step 3: Route by *ärende*, not by person

**The subject of the thread decides the folder, not the sender.** This inverts the default the
meeting-routing table sets, so it must be stated rather than inherited.

- A thread with a supplier about a specific project belongs in **the project**
- A thread with the same supplier about terms belongs in **their contact folder**

A thread with one person can be entirely about a project; a project thread can have six
participants who each have their own contact folder. Neither fact decides the folder.

### Step 4: The gate -- one question, then go

Human-in-the-loop is the requirement, and an open-ended prompt is not a gate. Ask exactly one
question:

> **Ny fil, eller uppdatering av `<befintlig fil>`?**

That is the one decision the skill genuinely cannot make. Thread matching is a heuristic, and a
**wrong merge silently corrupts two records at once, while a wrong split is visible and cheap to
fix**. Default when in doubt: **propose the new file**, because that failure is recoverable.

Everything else -- folder, filename, participant roles -- is shown alongside as a proposal to
override, not asked as a second question.

### Step 5: Write or append

**New material goes newest first**, so the current state is at the top where a reader lands.

A correspondence file is a **living** document where a transcript is a frozen one. That
difference propagates: a frozen file is written once and dated by its event; a living one needs a
last-updated marker.

### Step 6: Report

Name the file, the folder, and why that folder. If the thread was appended to an existing file,
say which turns were added.

---

## File format

Filename: `YYMMDD-{strings.filename_keywords.correspondence}-<person>-<ämne>.md`, where `YYMMDD`
is the date of the **first** turn. The file keeps that name as it grows.

```markdown
# Korrespondens: [one line on what the thread is about]

**Källa:** [channel and date; note if timestamps are missing from the source]
**Typ:** korrespondens (tvåvägs tråd, inte ett möte)
**Turer:** [sender → recipients (time)] · [sender → recipients (time)] · **[decision reached, or what is outstanding]**
**Senast uppdaterad:** YYMMDD
**Råmaterial:** behålls inte (CR-080). Avsändare, mottagare och datum står ovan.

---

## Sammanfattning

[What the exchange established. Two to four sentences. If a decision was reached *in* the
exchange, say so here -- that is the thing a thread can do that a one-way report cannot.]

## Nästa steg

| # | Åtgärd | Ägare | Prio | Deadline |
|---|--------|-------|------|----------|

[Only `from`/`to` participants may own a row. A cc recipient owning an action is an attribution
error -- see rule 2.]

## Turerna

### [YYMMDD HH:MM] [Sender] → [Recipients]

[What this turn said. Quote verbatim where the wording carries the meaning.]

## Bakgrund

[Prior context, and what the thread connects to elsewhere in the vault.]
```

---

## What this is not

- **Not a meeting.** No participant list, no facilitator, no agenda.
- **Not `content`.** One-way incoming material -- a report, a newsletter, an automated digest --
  has a sender but no exchange. That is CR-105's shape, handled by `/ops process`.
- **Not a transcript.** Nothing is recorded; nothing goes to `.transcripts/`.
- **Not an archive of mail.** The record carries the substance. The wire form is discarded by
  design, not by oversight.

## Scope

**Email, chat and message threads.** The **calendar half of CR-080 stays deferred** -- recurrence,
mutation after recording, and RSVP-as-attendance need their own pass.

---

## Related CRs

| CR | What it contributes |
|---|---|
| **CR-080** | This skill. Correspondence as a third shape; decision 6 answered 2026-10-01 |
| **CR-105** | `content` -- one-way incoming material, the shape this one deliberately excludes |
| **CR-015** | Attribution safety, applied here as the cc rule |
| **CR-012** | Inbox schema |
| **CR-068** | Why widening a seal changes what its name means |
