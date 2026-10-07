# CR-106 — A preparation must read the task register, and `/ops prepare` needs the card too

| | |
|---|---|
| **Status** | **Implemented 2026-10-07** |
| **Contract** | additive — one new step in `/preparation`, one inherited rule in `/ops prepare` |
| **Date** | 2026-10-07 |
| **Area** | `skills/preparation/SKILL.md` (new Step 2.6), `skills/ops/SKILL.md` (`prepare`) |
| **Related CRs** | **CR-005** (agenda-card-first, the rule `/ops` never inherited), **CR-022** (the triage doc Step 2.4 reads) |

## What happened

A preparation was written for a lunch with the CEO, five days before a board update. It carried six
questions, all of them real, all of them about that board update.

The person it was written for read it and asked: *"is this really ALL the points I have open with
him right now?"*

It was not. A direct query against `_inbox/_tasks.yaml` returned **43 open rows naming him**, of
which **15 genuinely required him** — his answer, his decision, or a sentence that could only be
said to his face. Nine of those fifteen were absent from the prep. Three were trivial and overdue:

- *tell him you work less Thursday to Sunday* — overdue by a week, and the lunch was on a Wednesday
- *ask for the two WEEKLY STATS images missing from the report* — a question never asked
- *where is first-touch UTM stored?* — access already granted, the question simply never put

Each takes under a minute at the table. Each had been waiting for weeks because nothing put them in
front of the person at the moment he was in the room.

## Why the prep missed them

**`/preparation` never reads the task register.** The string `_tasks.yaml` appears **zero times** in
its SKILL.md.

Step 2.4 reads the *triage document* (CR-022). That was correct when the triage doc was the source
of truth — but it stopped being that on 2026-09-07, when the register became the truth and the
triage doc became a **generated view** of it. A generated view is filtered: it carries what has a
date or a P0/P1, and leaves the rest in YAML. So a prep reading the view sees a subset of a subset,
and silently.

The second half is `/ops prepare`, which wrote this particular file. It has **no card rule at all** —
zero occurrences of `walk-in`, `60-second` or `agenda-card`. CR-005 gave `/preparation` a card: at
most five items, self-sufficient, everything else below a rule. `/ops` never inherited it, so the
same document type has two shapes depending on which skill happens to run.

The result in this instance: **27 lines of metadata, source links and a rationale** before the card
the reader actually needed. The author's own note in the file said the card existed *"so it can be
read from a phone"* — and then placed it where a phone reader would never reach it.

## Proposal

### 1. `/preparation` Step 2.6 — read the register, not only the view

After the cross-context scan, query the vault's task register for every open row naming the contact,
and split the result:

| Bucket | What goes in the prep |
|---|---|
| **Requires them** — their answer, their decision, or something only sayable to their face | Candidates for the card |
| **Mentions them** — context, or an action that is entirely yours | Listed under open actions, not in the card |

**Short and overdue beats important and new.** An item that takes under a minute and has been
waiting weeks belongs in front of the person *now*; a substantial question needs a slot of its own.
Where the card is full, those go in a separate two-to-three-line block — *"while you are both here"* —
which is not an agenda item and does not consume one of the five.

**State the remainder.** When more rows require the person than fit, the prep says so with a count
and points at the full list. The failure this CR fixes is not that nine items were left out — a card
of 24 items is useless. It is that **nothing in the document said they existed.**

### 2. `/ops prepare` inherits the card

The CR-005 card is the shape for any preparation, not only contact ones: **top of file, at most five
items, self-sufficient, everything else below a horizontal rule.**

- **Metadata, source links and rationale go BELOW the rule.** A reader opening the file sees the card
  first, or the card has failed at its one job.
- **Dual mode** may declare its own card for the facilitator layer — a facilitator needs time-boxing
  and deflection cues where a 1-on-1 needs questions. The exception is declared, not assumed.

## What this is not

- **Not a change to the triage scan.** Step 2.4 stays; the triage doc still collects items between
  meetings. This adds the register underneath it.
- **Not automatic inclusion.** Reading every open row does not mean printing every open row. The
  split and the five-item cap are the point.
- **Not a new source of truth.** The register already is one. The prep simply never asked it.

## Evidence

- 43 open rows naming the person; 15 requiring them; 9 absent from the prep (2026-10-07)
- `grep -c "_tasks.yaml" skills/preparation/SKILL.md` → **0**
- `grep -c "walk-in\|60-second\|agenda-card" skills/ops/SKILL.md` → **0**
- The prep in question: 27 lines before the card, in a file whose own note said the card was for
  reading on a phone
