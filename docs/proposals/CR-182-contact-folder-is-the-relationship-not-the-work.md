# CR-182 — A contact folder holds the relationship, not the work; `_outbox/` holds what leaves

| | |
|---|---|
| **Status** | **Implemented v1.98.0, contract 52** (2026-11-27), including the addendum (`_toread/`) |
| **Contract** | No schema change required. Two routing rules in `ops-base`, one sharpening of `outbox`, one optional config key (`vault_conventions.binary_archive`) extending CR-170 from audio to all heavy binaries |
| **Date** | 2026-11-27 |
| **Area** | `skills/ops-base/SKILL.md` (routing), `skills/outbox/SKILL.md` (scope), `skills/ops-config/schema.md` (`vault_conventions.binary_archive`) |
| **Related CRs** | CR-010/CR-025 (one inbox, one outbox), CR-032 (canonical source), CR-120 (`hanterad`, destination), CR-170 (audio archive outside the vault) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E]** One piece of the user's own work — a talk, prepared over two weeks for an event run by one
external contact — was produced inside that contact's folder because the first meetings about it were
with that contact. The folder ended up holding the correspondence *and* the work: reasoning notes,
the speaker's script, a deck build (renderer, template, image bank, 23 rendered versions), a
reflection on the delivery and an improvement review.

**[E]** When a reusable second version was requested, there was no obvious home for it, so it was
placed in a different venture folder. The talk had two homes.

**[E]** Prospects met at the event (three people) were recorded in the organiser's folder. Two of
them got contact folders holding only metadata and a changelog line pointing back to the organiser's
folder; the next time either of them replied, nothing about them would have been found where they are.

**[E]** `_outbox/` was used for three different things in the same week: sends (a PDF, an email),
publications (two social posts already drafted in an external content workspace, so the same text
existed in three places), and "put all the material in an outbox" as storage.

**[E]** Counted afterwards: 14 kinds of material, 5 placed by a written rule, 9 by memory, an
in-the-moment correction, or the assistant's own choice. The user's words: *"I see no logic in what
ends up where."*

**[E]** Heavy binaries were moved off the vault under a rule whose destinations existed only as prose
in the vault's CLAUDE.md; the first destination chosen (the employer's folder, because the talk was
given in the employer's name) was wrong for material that is the user's own work, and had to be moved
again.

## The proposal

### 1. Contact folder = the relationship (ops-base routing)

> **Does it concern the relationship with this person?**

- **Belongs:** correspondence, meetings and their summaries, what the person gave you, commitments
  between you, **what you know about them as a prospect**.
- **Does not belong:** your own work, even when it was made *for* that person. The work lives in the
  venture's project folder (`<venture>/_projects/YYMMDD-<slug>/`), with each occasion it is used for
  as a subfolder (`YYMMDD-<occasion>/`) and a reusable version beside them. The contact folder gets a
  pointer and a changelog line.
- **Prospects live with the person.** Information about a prospect is written to the prospect's own
  contact folder, never only in the folder of the person who introduced them.
- **Decide at creation, not afterwards.** When a meeting starts work that will outlive the meeting,
  the skill proposes the project folder at that point. Moving later costs a link rewrite across every
  document in both folders.

### 2. `_outbox/` = what leaves the vault (outbox scope)

> **Is it going to leave the vault?**

- Sends (email, attachment, print) — as today, with `Kanonisk källa` pointing at the work.
- **Not storage.** "Put the material in an outbox" is answered with the project folder.
- **Not publications drafted elsewhere.** When a vault declares an external content workspace where
  posts are drafted and, once published, archived canonically, the outbox does not stage a third
  copy. The vault records the publication as a changelog line in the folder the post is about.

### 3. Binary destinations are configuration (extends CR-170)

```yaml
vault_conventions:
  binary_archive:            # optional; destination per venture
    personal: "//host/share/personal/"
    <venture>: "//host/share/<venture folder>/"
```

The destination follows **whose work the material is**, not whose name it was presented under. The
prose rule in a vault's CLAUDE.md stays; the key lets a skill pick the destination without guessing.

## What this does not change

- The single `_inbox` / `_outbox` rule (CR-010/CR-025).
- `hanterad` (CR-120) for material that was worked from in `_outbox/` — whether a reading surface
  belongs in `_outbox/` at all is a separate, open question and not settled here.

## Verification **[H]**

- `/ops check`: report a contact folder holding a deck build or more than N files whose role keyword
  is not a meeting/correspondence role, as a candidate for a project folder (report, never move).
- `/outbox list`: report an item whose `Kanonisk källa` is an external content workspace and whose
  status is published, as closable.

## Addendum 2026-11-27 — a reading surface (decided the same day)

**[E]** Material written *for the user to read* (a review, a reflection, a decision basis) landed in its
home folder and was opened once on the desktop. Afterwards nothing answered *"what is waiting for me to
read?"*, and nothing was reachable on a phone or tablet. `_outbox/` was used for it, which this CR rules
out; `.handoff/` was considered and rejected: it is locked for a different session, and **a dot-folder is
invisible in the mobile note app and the mobile file browser**.

### 4. `_<read>/` — one root reading surface

- An **underscore** root folder (the name is the vault's; this vault uses `_toread/`), so it is visible
  and can be pinned on mobile — the same reason CR-180 gives for `_callcards/`.
- Holds **reading copies**, each opening with a line pointing at its source; the source stays in its
  home and wins on conflict. An `_index.md` lists what is waiting.
- **Locked for skills** like `_callcards/` (CR-180): never read, parsed, indexed, summarised or swept.
  Its skip path belongs in the same declared skip list CR-180 introduces.
- Written in the same step as the material it copies, when the material is meant for the user to go
  through. Read → the copy moves to `.archive/`, and anything the user wrote in it is carried back to
  the source.
