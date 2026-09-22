# CR-066: `classification` — who may receive a staged item, as a manifest field

| Field | Value |
|-------|-------|
| **CR Number** | CR-066 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | Proposed — question, not a decision · **evidence added 2026-09-22** |
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

**The asymmetry matters.** Sending a team-wide item to a narrow audience wastes it. Sending a restricted item to a broadcast channel cannot be undone.

### It is not a proposal — it already grew (evidence, 2026-09-22)

The first draft of this CR said the constraint *"lives in prose, which informs the author and nobody else."* **That was wrong.** A survey of one live vault:

| | |
|---|--:|
| Manifests total | **170** |
| Carrying a `classification` field already | **20** |

With these values, as written:

| Value | Count |
|---|--:|
| `team-wide-safe` | **18** |
| `team-only` | 1 |
| `internal` | 1 |

**So the field exists and is in use. What it lacks is a declaration** — the dispatching surface reads it as an unrecognised extra and shows it read-only, which is the tolerant behaviour CR-049 asked for, working exactly as intended.

**This is the same shape as the status-note.** CR-053 declared that field because *"the field that carries what actually happened was undocumented while 104 of the live vault's manifests use it."* Identical pattern at smaller n: the vault grows a field in practice, the schema catches up. That precedent makes this a narrower question than the first draft posed — **not "should we add a concept" but "should the schema adopt one that is already there".**

**Two observations the data hands us:**

1. **The vocabulary has not converged.** `internal` and `team-wide-safe` are not obviously distinct, and one of the three values appears once. An undeclared field drifts because nothing tells an author what the options are — which is an argument for declaring it, not against.
2. **Adoption is skewed to one value.** 18 of 20 are the most open setting, so the field is currently carrying almost no restriction. Its value is in the two exceptions, and in the ones nobody wrote because there was no field to write.

---

## What already exists, and why it is not enough

`channel` and `contact` carry *where it goes*. They do not carry *where it may go*. **`outbound_dispatch` (CR-047) declares that a dispatching surface may write `channel` and `contact`** — correctly, that is what a picker is for — so an operator can widen the audience of an item never written for it, and nothing in the file objects.

**The write boundary makes the shape obvious:** a dispatching surface may write `status`, `status-note`, `channel` and `contact`, and nothing else. **`classification` would be authored by the skill and read-only to the dispatcher** — so it can inform a send without a dispatcher inventing policy, which is exactly the line CR-047 draws when it says a dispatcher "must not invent a status the skill does not recognise".

`replaces` shows the schema already models relationships between items rather than only their contents, so an audience constraint is not foreign to it.

---

## Sketch, for discussion

**Identifier `classification`; the label is data** (CR-049, CR-053) — a vault writes it under its own label, the field is keyed `classification`.

**Take the values that are in use; do not invent a parallel set.** The first draft sketched `open | team | management | named`, which would have invalidated all 20 live manifests — the second-implementation problem this CR argues against, committed inside the CR itself. CR-049 is explicit: *"the LABEL keeps the existing spelling. Renaming a key costs nothing; renaming a label changes a manifest a skill reads."*

| Value | In use | Meaning |
|---|--:|---|
| `team-wide-safe` | 18 | Anyone internal may read it |
| `team-only` | 1 | The working team; not interns or contractors |
| `internal` | 1 | **Unclear** — overlaps `team-wide-safe`; see open question 6 |

**Absent means the most open value** — every existing manifest stays valid and nothing changes for material already staged.

**A gap the data shows:** there is no observed value for *named recipients only*, the narrowest case and the one where a mis-send is least recoverable. Either it has not arisen, or people avoided the field for exactly the material that most needed it.

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
3. **How many values?** The data says three are in use and one of them is ambiguous. Declaring what exists is safe; adding a fourth for named-recipients-only is a judgement about material that has not been staged yet.
4. **Does a wrong value fail safe, and does that conflict with tolerating unknown values?** An unparseable classification arguably should read as the *most* restrictive — the opposite both of how an absent field behaves and of the "tolerate what you do not recognise" rule CR-049 carried forward. Absent and unrecognised may need to differ here, which is unusual enough to state rather than assume.

6. **Is `internal` the same as `team-wide-safe`?** Both appear once and twice respectively in the same vault with no stated difference. If they are the same, one is a typo the schema should not enshrine; if they differ, the difference has never been written down. **Answer this before declaring the enum, not after.**

7. **Does the 18-to-2 skew mean the field is working or unused?** A field almost always set to its most permissive value either reflects genuinely open material, or reflects an author reaching for the safe default. The two look identical in the data and imply opposite things about whether enforcement would help.

5. **Or does it belong in `known_gaps` rather than the schema?** CR-047 records the archive-of-unsent-items gap that way — described, owned, unresolved — rather than adding a field ahead of the decision. This may be the same shape.

---

## Not proposed

- Encryption, access control, or anything resembling a security boundary. This is a routing guard against an easy mistake, not protection against a determined one.
- Retro-classifying existing staged material.
- Per-recipient rules. One item, one classification.
