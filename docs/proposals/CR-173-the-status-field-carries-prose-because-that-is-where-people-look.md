# CR-173 — The status field carries prose, because that is where people look

| | |
|---|---|
| **Status** | **Proposed** (2026-11-04) |
| **Contract** | additive — `status_forms` gains an optional note half; no new status word, no new file |
| **Date** | 2026-11-04 |
| **Area** | `outbox` (`resolved.py` `--validate` and the status reader, SKILL.md), `ops` (staging, `check` class 4), `ecosystem.yaml` (`status_forms`) |
| **Related CRs** | CR-053 (the manifest's fields are named by identifier), CR-102 (a manifest is edited, never regenerated), CR-103 (an undeclared status word is reported, never rewritten), CR-120 (`hanterad`), CR-131 (`Skickades inte.` is a complete outcome), CR-132 (the staging gate), CR-144 (a sent status carries its proof — **draft; this CR is the other half of the same field**) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E] Measured on one vault, 2026-11-04: 59 live outbox items, 9 carrying a status word the
contract does not declare.** They are not typos. Four of the nine are whole sentences, with
markdown, written into a field whose declared values are single words:

| What the field contained | What it is |
|---|---|
| *"the event was held 2026-10-23.`**` The deck was never shown — the demo slot was cancelled. One question left to ask (see *After the event*). The slides are still unvalidated."* | an **outcome**, which has its own section |
| *"REPLY RECEIVED 2026-10-30`**` — time booked Monday 2/11 at 14:45"* | an outcome **and** a next step |
| *"WAITING FOR THE SUPPLIER'S ANSWER`**` — goes out when they have been in touch about …"* | a **blocking condition**, which has no field at all |
| *"the links `**`SENT`**` 2026-10-28 08:58 · the reflection `**`klar-att-skicka`**`"* | **two states for one item**, because the item holds two things |

The remaining five are near-misses of a declared word -- `klar att skicka` with spaces for
`klar-att-skicka`, `utkast, ej skickat` for `utkast`, `klar-att-läsa` for nothing at all.

**The near-misses are a vocabulary problem and CR-103 already handles them**: report the word,
name the closest declared form, never rewrite. This CR is about the other four, which are a
**design** problem.

### The field is where people look, and the structure is elsewhere

A manifest already has `## Utfall` for the outcome and a body for everything else. Nobody is
confused about that. What they are doing is writing the thing they most need to see **in the place
they look first**, which is the status line — and a schema that loses to that every time is not
being disobeyed, it is being out-designed.

**[E]** Three of the four prose statuses carry information that has **no declared home at all**:

- *waiting on an external party before this can be sent* — not `draft` (it is finished), not
  `klar-att-skicka` (it is not), not `skickad`. The declared set has no word for *ready and held*.
- *one half sent, the other half still staged* — the item is one folder and two artefacts.
- *the event this was for has happened and the material was never used* — which is `avskriven`
  with a reason, and CR-131 says the reason is optional. So the author wrote the reason where it
  would be read.

### Why the gate did not catch it

**[E]** CR-132 made `Kanonisk källa` and a declared status word a precondition **at staging**, via
`resolved.py --validate`. All nine predate that gate or were written by a surface that does not call
it: **12 of the 59 live items also carry no `Kanonisk källa`**, which is the same gate's other half.
A gate at one door is a gate nobody passes through twice.

## Proposal

**1. The status line gets a declared note half.** One line, two parts, the separator already used
elsewhere in the manifest:

```
**Status:** klar-att-skicka · väntar på motpartens besked om tid och omfattning
```

The word before the separator is from `status_forms` and is what every reader parses. Everything
after it is **free text for a person**, declared as such, never parsed, never matched against an
enum. `resolved.py` reads the word and ignores the note; `check` reports the word and quotes the
note; no reader has to change to keep working, because a status with no note is what every manifest
has today.

**2. One new declared form: `hålls`** (*held*) — finished, approved and deliberately not sent yet,
waiting on something outside the item. It is the state three of the four prose statuses describe and
the only one the set genuinely lacks. **`hålls` ages like any other staging state** (CR-120's
30-day threshold) — a held item is exactly the kind that is held once and forgotten.

**3. `--validate` accepts the note and rejects the prose.** A status line whose **first token** is
not a declared form fails, as today; a declared form followed by `·` and text passes. The error
message names the note form, because the author who wrote a sentence was trying to record something
real and telling them only *"undeclared status"* sends them to invent a second word instead.

**4. `check` class 4 reports a status whose note is doing structural work.** A note containing a
date and a done-word (*sent*, *received*, *held*) is reporting an **outcome**, which belongs in
`## Utfall` where `close` can read it. Report it, name the section, rewrite nothing — CR-103's rule,
applied to the new half.

## What this is not

**Not a second enum.** The note is text and is never matched, sorted or counted. The moment anything
reads it, this CR has failed.

**Not a rewrite of existing manifests.** The nine are reported with the declared form and the note
split proposed; a person applies it, or does not. CR-102 still governs: a manifest past draft is
edited line by line, never regenerated.

**Not CR-144.** That CR is about a `skickad` status carrying its proof and never being overwritten.
This one is about the field's shape before anything is sent. They touch the same line and should be
read together, but neither depends on the other.

## Acceptance

- `status_forms` declares `hålls`, and the status line's grammar — one declared word, optional `·`,
  optional free text — is in the contract.
- `resolved.py --validate` passes a word-plus-note line and fails a line that opens with prose,
  naming the note form in the error.
- `check` reports a note that carries an outcome, names `## Utfall`, and rewrites nothing.
- A manifest with a bare declared word behaves exactly as it does today. **[H]** Re-run the measured
  vault: the nine should resolve into declared words plus notes, with no new word invented.
