# CR-076: `external_systems` is resolved from the wrong folder, and the miss is silent

| Field | Value |
|-------|-------|
| **CR Number** | CR-076 |
| **Date** | 2026-09-22 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-24, v1.73.0** |
| **Priority** | **High** -- it silently empties the one block that carries what the room did not say |
| **Complexity** | Low |
| **Estimated Scope** | `skills/ops/build_agenda.py` (`config`, `external`, `from_chat`, the run summary). `project_brief.py` imports `config` and is fixed by the same change |
| **Related CRs** | CR-054 (`external_systems`), CR-058 (pre-meeting retrieval), CR-071 (multi-chat retrieval), CR-067 (same silent-misclassification shape), CR-011 (config chain), CR-072 (series declaration) |
| **Contract** | No change. contract_version 24 unaffected -- the schema is right, the reader is not |
| **Breaking Changes** | No |

---

## Executive Summary

`config()` finds `carry_forward` by walking **up** from the meetings folder, nearest wins. It then
anchors `external_systems` to **that same folder**:

```python
src = d.get("external_systems") or {}
...
cf["ext"] = src or external(root)          # root = where carry_forward was found
```

and `external(root)` reads **only** `root`'s own config.

**The two declarations do not have to live in the same file, and in the shape CR-072 just made
first-class they systematically do not.** A recurring series declares its chats in its own
`_ops.yaml`, beside the series itself. `carry_forward` is declared once at the org layer, because it
describes the loop for the venture rather than for one folder. So `carry_forward` resolves **up** to
the org config, `ext` is anchored **there**, and the declaration sitting one level **down** -- nearer
to the meetings folder, in the file whose whole subject is that series -- is never read.

**The resolution order is inverted relative to the documented chain.** CR-011 says nearest wins,
walking up from the target. This walks up from a folder that is already further from the target than
the file it should have read.

## Observed

Verified by instrumenting the resolution on a live series whose `_ops.yaml` declares one chat:

```
carry_forward root : <venture>/
note_suffix        : <series>-*
ext                : {}
declared chats     : None
```

The archive was checked independently and **the declared chat is there**, readable, with snapshots
from three of the previous fourteen days including one written the day before the session.

The generated agenda carries no *"Since the last standup -- not said in the room"* block at all.

## Why this is worse than an empty block

**The run reports `0 chat`.** That number is `len(chat)` -- the count of *declared and resolved* chat
records, not of messages -- so it is literally accurate and reads as *nothing was said*. A project
that declares no chats prints the same `0`.

`from_chat` returns early on an empty declaration:

```python
chats = cf.get("ext", {}).get("chats") or []
if not chats:
    return []
```

so no `problem` record is produced either. **The three states are indistinguishable in the output:**
nothing declared, a declaration the reader failed to find, and a declared chat with genuinely no
traffic. Only the third is a fact about the work.

CR-071 established the principle this violates: *a diagnostic counted as traffic is worse than no
count at all*, and a declared chat that cannot be resolved **prints as a problem**. That rule is
implemented for a chat that is declared-but-absent-from-the-archive. It does not fire when the
declaration itself was never located -- which is the earlier and more complete failure.

**And it is the block that exists precisely to carry what the transcript cannot.** CR-058's whole
argument is that a meeting record holds only what was said out loud in the room; decisions posted to
the chat reach no transcript and often never come up. Emptying that block silently returns the agenda
to the state CR-058 was written to fix, while looking like it succeeded.

## Proposed change

**1. Resolve `external_systems` on its own chain, from the target.**

`ext` must not be a by-product of where `carry_forward` was found. Walk up from the **meetings
folder** -- the same start `config()` uses -- and take the nearest `external_systems`, independently
of which layer declared the loop. Two declarations, two chains, one shared rule: nearest wins.

This is additive for every existing config. A project that declares both in one file resolves
identically, because that file is also the nearest on both chains.

**2. `from_chat` reports an unlocated declaration, rather than returning silence.**

An empty `chats` list is a legitimate state and must stay quiet -- a project with no chat declared
should not be nagged. But the summary line must stop asserting a count over a source it never found.
Print what is true:

```
no chats declared -- nothing to retrieve
```

instead of `0 chat`, when the resolved `external_systems` is empty. Distinguish, in one word, the
three states the output currently collapses.

**3. Same for `repos:`.** `from_repo` reads `cf["ext"]["repos"]` through the identical anchor and has
the identical defect. It is not separately observed only because the series in question declares no
repositories.

## Test

The regression that would have caught this: a fixture with `carry_forward` in a parent config and
`external_systems` in a child, asserting that `config(child/"meetings")["ext"]["chats"]` is non-empty.
No current fixture separates the two files, which is why a defect this central survived three CRs
that each touched the retrieval path.

## What this does not change

The schema is correct and `contract_version` does not move. `external_systems` has always been
declared as resolved by the normal config chain; this makes the reader do what the contract already
says. No vault file changes shape, and no existing declaration has to be rewritten or moved.

---

## Outcome (2026-09-24, v1.73.0)

`external()` now walks up from the folder it is given, nearest declaration wins — the same
chain every other key uses. `project_brief.py` imports `config` and is fixed by the same change.

**And the miss is no longer silent:** when nothing in the chain declares `external_systems.chats`,
the run says so, distinguishing *undeclared* from *declared but quiet*. Both rendered as an empty
section before, which is how this went unnoticed.

**Honest scope note.** Checked against the live vault after the fix: **no folder there was
actually affected.** The two folders declaring `carry_forward` without `external_systems`
(an org root and a marketing project) have no declaration anywhere above them either, so they
resolved to nothing before and after. The bug was real and the reasoning holds — a project
declaring the loop in its own config and its chats one level up would have lost the block
entirely — but this repo should not claim a recovered failure it cannot point at. The change is
correct and, here, latent.
