# CR-144 — A *sent* status carries its proof, and a session never overwrites it

| | |
|---|---|
| **Status** | **Draft** (2026-10-21) — the dispatching surface's behaviour has to be confirmed first |
| **Contract** | additive — the status note becomes required alongside a dispatcher-written *sent*; no new status form |
| **Date** | 2026-10-21 |
| **Area** | `outbox` (SKILL.md, `resolved.py`), `ecosystem.yaml` (`status_forms`, manifest writers) |
| **Related CRs** | CR-014 (the dispatching surface, in its own repo), CR-102 (manifests edited in place), CR-103 (declared words), CR-120, CR-131 |

## What happened

*Logical names are used throughout (`sent`, `withdrawn`, the status note, the outcome section). A Swedish vault writes them as `skickad`, `avskriven`, `Statusnot` and `Utfall`; see the question at the end on the written words.*

The contract lets a dispatching surface write a manifest's `Status`, the status note, channel and contact, because
*whether something was sent is an observation*. Earlier recaps carried both: `sent` and a the status note
naming the channel, the time and a message id. **On one day a manifest read `sent` with no the status note
and no matching message in the chat archive**, while the operator had said they would not send it. The
assistant overwrote the status to `withdrawn` after reading the file. What wrote `sent` could not be
established from the machine: no scheduled job, hook or script in the vault, the home directory or the
skills wrote the word.

**[E]** One false `sent` in about ten sends. A false `sent` is worse than none: it removes the item
from the outbox's open list, and the chat archive has nothing to contradict it.

## Questions to settle before this is Proposed

1. Which surface writes `sent`, on which trigger (a click, a draft saved, a copy to the clipboard)?
2. Does it always write a the status note with a message id, and is that the evidence a reader can check?
3. Can it mark `sent` for a file it has not posted?

## Written words are data (question)

The contract declares the identifiers in English and the written words as data (`identifier_language`, CR-049, CR-103), but `status_forms` today lists only Swedish written words, except for *draft*. A vault that wants English manifests cannot write `sent 2026-10-21` without the check calling it undeclared. **Proposal: every status form lists its English and its Swedish written word, a reader accepts both, and a vault setting chooses which the staging step writes.** This changes the written form of nothing that exists.

## Proposal (provisional)

1. **`sent` without a the status note carrying a channel and a time is reported by `check` as unproven.**
2. **A session that finds an unproven `sent` reads the chat archive for the message**; if none exists it
   reports this to the operator and changes nothing without their word.
3. **The dispatching surface writes the status note in the same edit as `sent`**, or neither.
4. **When an operator says an item will not be sent, the skill offers `withdrawn`** (CR-131: no reason
   required) and never a free-text word.

## Acceptance

- `check` lists manifests with `sent` and no proof.
- A session never writes `sent`; it records the operator's word in the outcome section.
