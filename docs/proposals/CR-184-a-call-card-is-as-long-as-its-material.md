# CR-184 — `_callcards/`: a card is as long as its material, not fifteen bullets

| | |
|---|---|
| **Status** | **Proposed** (2026-11-28) |
| **Contract** | The `_callcards/` schema line in `ecosystem.yaml` (a comment today); no new key. Whether it is a `contract_version` bump is the release's call -- a renderer that keeps a cap reads the same paths as before |
| **Date** | 2026-11-28 |
| **Area** | `ecosystem.yaml` (`vault_conventions` path `_callcards/`, its `schema` line); CR-180's text where it states the cap |
| **Related CRs** | **CR-180** (`_callcards/`), CR-182 (reading surfaces, `walk_skip`), CR-183 (a preparation asks what must be decided) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E]** CR-180 declares the card's shape as *"five fixed headings: situation, do_say, do_not_say, ask,
open; at most 15 bullets per person"*. The vault-side renderer implemented the cap as 3 / 3 / 2 points
for the three written sections plus a short, date-windowed "open" list, and told the model "fewer is
better".

**[E]** The user, reading the cards on a phone, called them *"very, very low quality"*, and then said
what was wrong with the shape: *"still just 2-3 bullets -- even if [a colleague] should have many more,
and also 'all' tasks connected? It must align to the content itself, not the generic LLM bias."*

**[E]** Measured on the card for a close colleague, the day it was said:

- the material inside a 21-day window held **13 dated conversations** that concern the person -- daily
  meetings in which they spoke, a one-to-one, two project meetings -- and the card carried **3** points;
- the person was the owner of **about 200 open tasks** across five task ledgers, **a third overdue**,
  and the user owned **over 100** more that name them; the card's "open" section said *"(none dated)"*,
  because it read one folder's ledger within -14..+30 days.

**[E]** A fixed small number does not make a card short; it makes the model choose, and a model
choosing a few lines out of a week of material picks the general ones -- *"keep the conversation
structured"*, *"focus on the positives"* -- because a general line is true of every week. The cap was
meant as a guard against padding. It produced the padding it was meant to prevent.

## What replaced it, in the renderer, and what held

**[E]** The renderer was changed the same day (vault-side, outside this repository) and re-rendered all
cards:

1. **Every bullet in situation, do_say and ask ends with the date of the material it rests on**,
   `(YYMMDD)`, and the script **drops every bullet whose date is not in the material**. Filler has no
   date to give, so it goes, whatever the length. This -- not a count -- is the guard against padding.
2. **The count follows the material.** situation: one point per thing that happened or was decided,
   as many as the material holds, up to 10; do_say up to 6; ask up to 5 -- each also bounded by the
   number of dated sources, so thin material gives a short card.
3. **open lists every open task connected to the person** -- all they own, all the user owns that name
   them, and others' that name them as a count plus the newest few -- ordered for a conversation:
   recently overdue first, then upcoming, then undated, then long overdue (most-overdue-first had put
   eight-month-old items at the top).

**[E]** After: the same colleague's card carried 10 situation points, 5 do_say, 5 ask, all dated within
the window, and every task connected to them. Across 23 cards, every remaining point carries a date
that exists in its material.

**[E]** The cost is length: that card's "open" section is long, because the relationship is. That is
information -- a third of someone's tasks overdue is something to raise in the next conversation -- and
a reader who wants less can read the first group.

## The proposal

Replace the cap in the declared shape with the two rules that actually bound a card:

```yaml
    - path: "_callcards/"
      ...
      schema: null  # five fixed headings: situation, do_say, do_not_say, ask, open. Every point in
                    # situation, do_say and ask ends with the date (YYMMDD) of the material it rests
                    # on, and a point whose date is not in the material is dropped. The number of
                    # points follows the material; a renderer may cap a section, never the card.
                    # open lists the open tasks connected to the person, not only the folder's own.
```

and in CR-180's text, where it says *"at most 15 bullets per person"*, point here.

What it does **not** change:

- **do_not_say** stays as CR-180 has it: copied from the strategy document, never inferred, and empty
  when there is none. It is the one section where a missing point is safer than a guessed one.
- The card remains **per person and rolling**, written only by the renderer, never read by a skill
  (`walk_skip`, CR-182).
- No cap is *forbidden*: a renderer may still bound a section (10 / 6 / 5 above). What the contract stops
  saying is that the person, as a whole, fits in a fixed number.

## Why not keep a number and raise it

**[H]** Any fixed total has the same failure at a different size: a quiet relationship is padded up to
it, a busy one is cut down to it, and the model decides what is cut. The date rule decides it instead --
mechanically, and checkably by the reader, who can open the dated source.

## Not in this CR

- How a renderer finds the person's material across the vault, rather than in one folder. That is the
  renderer's business; the contract says what a card is, not how it is assembled.
- Naming a card after the contact when the conversations live in a non-contact folder (a one-to-one
  series under a venture). Observed the same day; a separate proposal if wanted.

## Verification

When implemented: the `_callcards/` schema line reads as above; `scripts/check-terms.py` and the
contract tests pass; CR-180's text points here. **[H]**
