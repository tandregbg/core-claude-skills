# CR-070: `classification` — a third value, `management-only`

| Field | Value |
|-------|-------|
| **CR Number** | CR-070 |
| **Date** | 2026-09-22 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-22, v1.71.0** |
| **Implementation Date** | 2026-09-22 |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `ecosystem.yaml` (contract_version 23), `/outbox` manifest schema |
| **Related CRs** | **CR-066** (declares `classification`, two values), CR-059 (`recap_artifact`), CR-047 (`outbound_dispatch`, write boundary), CR-049 (identifier language), CR-053 (fields by identifier) |
| **Contract** | Written against contract_version 22 |
| **Depends On** | CR-066 |
| **Breaking Changes** | No (additive value; clients on 22 see an unrecognised value and tolerate it per CR-049) |
| **Renumbered** | **Was CR-068, contract_version 21, v1.69.0 when written.** All three were taken on main by the `.teamschats/` rename (CR-068) and the Status/Results Report standard (CR-069, contract 22) while this work sat uncommitted. Renumbered 2026-09-22 — the same collision CR-059 records, from the same cause: parallel sessions reserving numbers by using them |

---

## The question

**CR-066 settled the enum at two values the same day it was raised. Was two the right number, or only the number that happened to be in use?**

---

## Why it comes up

CR-066 declared `classification` by surveying 20 live manifests and taking the values it found: `team-wide-safe` (19) and `team-only` (1). A third, `internal`, turned out to be a synonym and was normalised away. The reasoning was explicit and good — *"take the values that are in use; do not invent a parallel set"* — because the alternative sketch (`open | team | management | named`) would have invalidated every live manifest.

**That method answers what to call the values. It does not answer how many there are.** A survey can only find values someone has already written, and it fixes the enum on the day it runs. Anything the field needs to express but nobody has yet had occasion to write is invisible to it.

### The 21st manifest, hours later (evidence, 2026-09-22)

A staged item was written the same day the enum was settled: a **post-meeting recap addressed to a single named recipient who had been in the room** — the confirmation variant, carrying individual judgements about three third parties who were not.

Neither declared value fits:

- **`team-wide-safe`** is plainly wrong; the item names individuals and assesses them.
- **`team-only`** is also wrong, and wrong in a way worth naming. It means *the working team minus interns and contractors* — still **a group, still a channel**. The item in question must not reach a channel at all. Choosing `team-only` would not have been an approximation; it would have recorded the wrong kind of audience.

The author wrote `management-only` — **a value outside the declared enum, in the 21st manifest, hours after a CR was decided specifically to stop that drift.** Not through carelessness: the recap standard the item was written against already defines three levels, `management-only` among them, and the author followed the document in front of them.

**That is the finding.** A schema that cannot express what its own source document mandates does not prevent drift; it relocates it. The author must either misrecord (pick `team-only`) or invent (write the third value). Both are worse than declaring the value.

## What the third value is, precisely

**Not a smaller team — a different kind of audience.** The first two values scale a group; the third leaves group distribution entirely.

| Value | Audience | Test |
|---|---|---|
| `team-wide-safe` | Anyone internal | Would it survive being forwarded anywhere inside the organisation? |
| `team-only` | The working team; not interns or contractors | Is the restriction about *employment status*? |
| `management-only` | **Named recipients** | Is there a list of people, rather than a group? |

**The ordering must be declared, not inferred.** CR-066's warn-on-widening rule compares a send against the declared value, which requires knowing that `team-wide-safe` > `team-only` > `management-only` in permissiveness. With two values the order was obvious enough to leave implicit. With three it is not, and a dispatcher guessing an order is a dispatcher deciding policy — which CR-047 says is not its to decide.

**The most dangerous widening is the one that was previously unrepresentable.** Forwarding a named-recipient note into a channel is the step that converts individual assessment into a group communication, and until now nothing in the manifest could object to it.

## Also closes a CR-066 loose end

CR-066's scope named *"`/outbox` skill manifest schema; dispatcher `rules.toml` field map"*, but the field landed only in `ecosystem.yaml`. The `/outbox` manifest schema block — the document an author actually reads while staging — never gained it. Anyone writing a manifest from that skill still sees five fields and no classification, which is how a sixth value gets invented next time.

Added here alongside the third value, with all three spelled out at the point of authoring.

## Implementation

1. **`ecosystem.yaml`** — contract_version 23: third value declared, permissiveness order stated explicitly, and the dispatcher's warn-on-widening described against a three-step ladder.
2. **`/outbox` SKILL.md** — `Klassificering` added to the manifest schema block with the three values and the test for each.
3. **No change to the warning itself** — it belongs to the dispatching surface, outside this repo (CR-066).

## Not proposed

- **A fourth value for external recipients.** Everything staged today is internal; an external-facing value would be invented rather than observed, which is the mistake CR-066 correctly refused. Raise it when something external is staged.
- **Refusal rather than warning.** CR-066 settled that and nothing here reopens it.
- **A default other than `team-wide-safe`.** An absent field still means the most permissive value. Making the strictest value the default would silently reclassify 19 live manifests.

## The lesson worth keeping

**Survey establishes spelling. Source documents establish range.** CR-066 asked the manifests what the values are called and got a correct answer; it did not ask the standards that govern what gets staged how many distinct audiences they distinguish. When a field is declared after the fact, both questions have to be asked — and the second one is the one that catches the value nobody has written yet.
