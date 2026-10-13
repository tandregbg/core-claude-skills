# CR-120 — Handled is not sent: the outbox needs an exit for material that is worked from, not dispatched

| | |
|---|---|
| **Status** | **Implemented v1.90.0** (proposed and committed 2026-10-12, released 2026-10-13; the dashboard side is not written yet) |
| **Contract** | additive — one new status form (`hanterad`), one new optional field (`Destination`) |
| **Date** | 2026-10-12 |
| **Area** | `outbox` (`resolved.py`, SKILL.md), `ecosystem.yaml` (`status_forms`), `ops` (`check` outbox aging) |
| **Related CRs** | CR-047 (`avskriven` — resolved without being sent), CR-103 (status words are declared, not invented), CR-032 (`Kanonisk källa`), CR-102 (manifests edited in place), CR-115 (a dispatcher may create a missing manifest) |

## What happened

`_outbox/` is documented as the single outbox: *"allt utgående material staged här."* In practice it had
become something wider — **the one queue an external surface reads to find what needs working on.** A
dispatching surface (CR-014 in that surface's own repo, implemented 2026-09-22) already polls
`_outbox/<item>/_manifest.md` and already knows the five declared status forms.

**[E]** Measured on one vault, 2026-10-12: of 114 items, **four were material that is never sent** — two
weekend checklists for the operator's own children, a documentation inventory, a CR triage. Six more
carried the status note *"eget läsexemplar"* or *"Inget skickas"*, including two of the operator's own
meeting preparations. None of them can be closed, because `close` requires `skickad` or `avskriven`:

- `skickad` is false. Nothing was sent.
- `avskriven` means *resolved without being sent* and requires an outcome saying **why it was not sent**
  (CR-047). A preparation that was read and used in the meeting was not *declined*; it was **used up**.
  Filing it as withdrawn records a decision that was never taken.

So they sit in the queue indefinitely, looking unfinished while being done — the exact failure CR-047 was
written to fix, in a case CR-047 does not cover. **[E]** 55 items were unhandled, 9 of them older than 30
days, the oldest 119 days.

A second, smaller gap falls out of the same hole. `close` must guess where a closed item belongs. **[E]**
On a batch of 47 closures the destination was guessed 47 times and one had to be referred to the operator,
because no folder existed for it. Nothing in the manifest says where the material goes home.

## Change

### 1. A sixth status form: `hanterad YYYY-MM-DD`

```markdown
**Status:** hanterad 2026-10-12
**Statusnot:** läst inför passet; agendan användes
```

| | `avskriven` (CR-047) | `hanterad` (this CR) |
|---|---|---|
| Means | Resolved **without** being sent | Worked from; **sending was never the point** |
| `## Utfall` | Required — must say *why not sent* | Optional — there is no decision to record |
| Typical | A recap the meeting made unnecessary | A preparation, a checklist, an inventory |

**The distinction is whether a send was ever on the table.** Withdrawn is the record of a decision not to
send; handled is the record of material that had no send to decide about. Collapsing them would make the
withdrawn list — which an operator reads to see what they chose against — unreadable.

Written by **the party that handled it**, which is the person, not a tool. A dispatching surface may write
it for the same reason it may write `skickad` and `avskriven`: whether material was worked from is an
observation, not a judgement (CR-047). It must not write the `Utfall`.

Archivable on the same terms as `skickad`. `list` shows these under **HANDLED, NOT SENT**.

### 2. An optional `Destination` field

```markdown
**Destination:** acme/meetings/management/Dana/
```

Where the material goes when it is closed. **Optional, and never inferred** — absent, `close` asks as it
does today. Written by whoever stages the item, who knows the answer; `close` then files mechanically
instead of guessing, and a dispatching surface can offer a *file it back* action against a declared target
rather than proposing a path of its own.

Distinct from `Kanonisk källa`, and the pair is the point: the source says **where the original lives**,
the destination says **where this folder goes**. For an item whose original lives here (`ingen (originalet
bor här)`) they are not the same answer.

### 3. Aging covers the staging statuses

`/ops check` check 4 ages items *pending* for >30 days. It does not age `draft`, `utkast` or
`klar-att-skicka`, which is where material actually accumulates — **[E]** 45 of the 55 unhandled items.
Extend the same threshold to the three staging forms. Report only.

### 4. The drift check compares content, not bytes

Where a manifest names a `Kanonisk källa` inside the vault, compare the staged copy with its source and
report a difference. **Normalise relative links before comparing.**

**[E]** This is the finding that shaped the check. A byte comparison over one vault reported 6 differing
copies; reading them, **5 were link rewrites only** — the staged copy correctly points relatively from
`_outbox/`, the source from its own folder — and exactly **1 was real drift** (a source that had since
gained ticket ids the staged copy lacked). A check with a 5-in-6 false-positive rate is one an operator
learns to ignore, so the normalisation is not a refinement: without it the check is worse than absent.

A `Kanonisk källa` that resolves to nothing in the vault is **skipped and reported as unverifiable**, not
as broken — **[E]** 16 of 114 pointed at paths in other repositories, which is legitimate.

## Why not simply widen `_outbox`

Considered and rejected: redefining the folder as *"the work queue"* and dropping the send framing. The
manifest's `Kanal`, `Kontakt` and `Klassificering` fields all describe dispatch, and `Klassificering`
exists to gate **who may receive** an item (CR-066/CR-070). Material that is never sent has no audience to
gate, so widening the folder's definition would leave three fields meaningless for a growing share of its
contents. One status form costs less and keeps the send contract intact for everything that is sent.

## Verified

Not yet — proposed. On the measuring vault the change would close 4 items that cannot be closed today, give
10 more a status that matches what they are, and bring 45 items under aging.

## Tests

`tests/test_cr120_handled_status.py` — the status form parses and canonicalises; `hanterad` is archivable
without an `Utfall` while `avskriven` is not; `Destination` is read when present and absent-safe; the drift
check normalises relative links before comparing (the 5-of-6 case above) and reports an unresolvable source
as unverifiable.
