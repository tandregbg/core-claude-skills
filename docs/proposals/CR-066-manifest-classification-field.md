# CR-066: `classification` — who may receive a staged item, as a manifest field

| Field | Value |
|-------|-------|
| **CR Number** | CR-066 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | Proposed — question, not a decision |
| **Priority** | Medium |
| **Complexity** | Low (schema), Medium (enforcement) |
| **Estimated Scope** | `/outbox` skill manifest schema; dispatcher `rules.toml` field map |
| **Related CRs** | CR-059 (`recap_artifact`), **CR-047** (`outbound_dispatch`, write boundary + known_gaps), **CR-049** (identifier language), **CR-053** (fields by identifier) |
| **Contract** | Written against contract_version 19 |
| **Owner of the decision** | The `/outbox` skill — it owns what a manifest means |
| **Breaking Changes** | No (additive, optional field) |

---

## The question

**Should the outbox manifest carry a field stating who may receive the item — and should a dispatcher enforce it?**

Raised from CR-059 (`recap_artifact`, implemented v1.50.0), which needs the concept and deliberately did not add it. The manifest schema belongs to `/outbox`; a consumer inventing a field would be the second-implementation problem the outbox/dispatcher split exists to prevent.

---

## Why it comes up

Outgoing material is not uniformly shareable. A recap written for a whole team, a summary for a management group, and a note for named recipients are different in one respect that nothing in the manifest records: **the size of the audience permitted to see it.**

Today that lives in prose — a line in the staged file saying *team-wide-safe* or *management-only*. Prose informs **the author and nobody else**. By the time an item reaches a picker and a send, the constraint is invisible.

**The asymmetry matters.** Sending a team-wide item to a narrow audience wastes it. Sending a restricted item to a broadcast channel cannot be undone.

---

## What already exists, and why it is not enough

`channel` and `contact` carry *where it goes*. They do not carry *where it may go*. **`outbound_dispatch` (CR-047) declares that a dispatching surface may write `channel` and `contact`** — correctly, that is what a picker is for — so an operator can widen the audience of an item never written for it, and nothing in the file objects.

**The write boundary makes the shape obvious:** a dispatching surface may write `status`, `status-note`, `channel` and `contact`, and nothing else. **`classification` would be authored by the skill and read-only to the dispatcher** — so it can inform a send without a dispatcher inventing policy, which is exactly the line CR-047 draws when it says a dispatcher "must not invent a status the skill does not recognise".

`replaces` shows the schema already models relationships between items rather than only their contents, so an audience constraint is not foreign to it.

---

## Sketch, for discussion

**Identifier `classification`; the label is data** (CR-049, CR-053) — a Swedish vault writes `Klassificering:`, the field is keyed `classification`, and the enum values are English like every other status key.

| Value | Meaning |
|---|---|
| `open` | Anyone internal. **The default when absent** |
| `team` | The working team; not interns or contractors |
| `management` | Management only |
| `named` | Only the addresses in `contact` / `recipients` |

**Absent means `open`** — every existing manifest stays valid and nothing changes for material already staged.

**A value a reader does not recognise should be tolerated rather than silently treated as the default** — the lesson CR-049 carried forward from `task_statuses`. Here that cuts the other way from absence: see open question 4.

---

## The real question: advisory or enforcing?

Three positions, and this CR does not pick one.

**A. Display only.** The picker shows the classification; the operator decides. Cheapest, no false confidence, and it does nothing on the day someone is moving fast.

**B. Warn on widening.** Sending `ledning` or `namngivna` to a channel matched as broadcast requires a confirmation. Catches the error that matters without preventing deliberate action.

**C. Refuse.** A restricted item cannot be sent to a broadcast channel at all; the classification must be changed in the manifest first — which is an edit to the file, by the skill that owns it, leaving a trace.

**B is the likely answer**, and CR-047's boundary is the reason it can be: a warning reads a field the skill authored and asks the operator to confirm. It does not decide what the value *means* — the skill did that when it wrote it. **C is where the boundary strains**: refusing is the dispatcher enforcing policy, which is the thing it is declared never to do.

**If the boundary should hold strictly, the honest answer is A** — the field exists, the surface shows it, and enforcement lives wherever policy lives.

---

## Open questions

1. **Does this belong in the manifest at all**, or is audience a property of the *channel* rather than the item? A channel known to be broadcast could carry the constraint instead — fewer fields, but then every new channel needs classifying.
2. **Who sets it?** The authoring skill from the meeting's own classification, or a human at staging time?
3. **Four values or two?** `öppen` / `begränsad` may be enough. Four invites debate about which bucket an item is in; two may be too coarse to act on.
4. **Does a wrong value fail safe, and does that conflict with tolerating unknown values?** An unparseable classification arguably should read as the *most* restrictive — the opposite both of how an absent field behaves and of the "tolerate what you do not recognise" rule CR-049 carried forward. Absent and unrecognised may need to differ here, which is unusual enough to state rather than assume.

5. **Or does it belong in `known_gaps` rather than the schema?** CR-047 records the archive-of-unsent-items gap that way — described, owned, unresolved — rather than adding a field ahead of the decision. This may be the same shape.

---

## Not proposed

- Encryption, access control, or anything resembling a security boundary. This is a routing guard against an easy mistake, not protection against a determined one.
- Retro-classifying existing staged material.
- Per-recipient rules. One item, one classification.
