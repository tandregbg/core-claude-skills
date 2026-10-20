# CR-135 — The task ledger uses the object model that already governs it

| | |
|---|---|
| **Status** | **Proposed** (2026-10-20) |
| **Contract** | additive — two declared fields on the task schema, one existing field narrowed to free text; no migration required to read |
| **Date** | 2026-10-20 |
| **Area** | `tasks` (v2 schema + writers), `ops` (`check`), `inbox` (`survey.py`), the vault's own `_INDEX-objektmodell.md` as the norm source |
| **Related CRs** | CR-132 (declared vocabulary written at staging, not reported after), CR-127 (`closed:` on a finished task), CR-134 (whole-population reporting) |

## What happened

The task ledger's `context:` field is a single free-text slot. Measured on one vault, 2026-10-20,
over **199 open entries**:

| | |
|---|---|
| distinct values | **126** |
| of those, singletons | **111** |
| compounds glued with `·` | **109** |

**The field groups almost nothing**, because it is carrying at least six orthogonal axes at once:

| Axis | Examples | Entries |
|---|---|---|
| venture | four of the declared ventures | 79 |
| activity type | uppföljning, rutin, väntar, kontakt, samtal, möte, idé | 32 |
| project | four project names, one of them this repository | 27 |
| function | ekonomi, infrastruktur, struktur, content, dev | 27 |
| life domain | familj, privat, hem, hälsa, socialt | 19 |
| **an event with a date** | `styrelsen 17/9` | 8 |

The second element after `·` is not an attribute at all but a subject line, and it sometimes carries
a deadline in prose: *"referral-mätning — DEADLINE ~24/9"* — a date living in a category field while
`due` is empty.

Near-duplicates follow from having no declared set: `infra`/`infrastruktur`, `privat`/`personligt`,
`uppföljning`/`uppföljningspunkter`, `struktur`/`obsidian/struktur`, `kontakt`/`kontakter`, and
one venture spelled both plainly and with a trailing question mark. One value is literally `att kategorisera` — an entry whose category is that it
has none.

## The vocabulary is already declared, one directory up

This is the part that makes the CR small. The vault root carries both halves:

- **`_INDEX-objektmodell.md`** — *"Den enda definitionen. Gäller HELA vaulten."* Seven object types
  (Idé, Projekt, Löpande ansvar, Uppgift, KPI, Länk, Note/logg), a decision test, and
  **järnregel 1: every thing is exactly ONE object type.**
- **`_INDEX-verksamheter.md`** — eight numbered ventures, and the attribute names to use:
  `Verksamhet:` (*"vems affär — en av de åtta"*), `Kund:`, `Kör:`.

So nothing needs inventing. The ledger simply does not read the model that governs it.

**[E] And järnregel 1 is being broken inside the ledger.** Of the 50 distinct first-elements,
**ten are not categories but other object types**: `rutin` and `väntar` are Löpande ansvar, `idé` is
an Idé, `reflektion` is a Note, and `uppföljning`/`samtal`/`möte`/`kontakt`/`kolla` are activity
types. They sit as Uppgift while being labelled something else. Järnregel 2 says such an entry is
*re-marked and moved, never deleted* — which is exactly what cannot happen while the label lives in
a free-text field no writer validates.

**[E] The drift reaches the portfolio too.** `_INDEX-projekt.md`'s own `Typ` column held nine labels
for seven declared types, two of them differing only by bold (`löpande` / `**löpande**`), and four
that are not object types at all: `kundprojekt` (5), `arkiv` (2), `program` (1), `plattform` (1).
`Verksamhet` carried `Personligt` **and** `Personligt (infra)`. Both were corrected on 2026-10-20 —
and one of the undeclared values, `partnerprojekt`, had been introduced **that same morning** by an
assistant editing the register without reading the model first. A vocabulary that lives only in prose
is one each writer re-invents.

## Proposal

**Three fields instead of one**, named as the vault already names them:

| Field | Values | Validation |
|---|---|---|
| `verksamhet:` | the eight from `_INDEX-verksamheter.md` | declared enum; anything else is a finding |
| `projekt:` | optional | **must match a row in `_INDEX-projekt.md`** — an entry naming a project the portfolio does not have is a finding, in either direction |
| `objekttyp:` | only when the entry is **not** an Uppgift | the seven from `_INDEX-objektmodell.md`; makes järnregel 2 executable |

`context:` narrows to the subject line, or is dropped.

**Written at staging, validated there** (CR-132's rule, same reason): the author knows the venture
when the entry is created; nobody knows it at clean-up time.

`/ops check` reports, never rewrites (CR-103): an undeclared venture, a `projekt:` with no portfolio
row, a portfolio row with no entries, and an `objekttyp:` other than Uppgift still filed as a task.

## Why this is worth the schema change

The gain is not tidiness. It is that the questions become askable at all. *What is waiting on a given
1-on-1 axis? Which personal purchases have no date? Which projects in one venture have ledger entries
but no row in the portfolio?* None of them can be asked today, because the answer sits in a free-text
string with 126 variants — and that is also why **112 entries with neither date nor age** could not be
triaged in bulk: `verksamhet: <personal>` + an activity type and no date is obviously reference, while
`verksamhet: <a business>` + a project and no date is a gap. Same two entries, opposite verdicts, and the
field cannot tell them apart.

## Migration

Generated, not hand-written: a map from each of the 126 values to a proposed `verksamhet` and, where
the first element matches a portfolio row, a `projekt`. On the measured vault **12 values have no
obvious venture** and need the operator, and **ten carry the object-type remark** above. The map is
the operator's worksheet; the migration is a batch they confirm, not an inference.

## Not in scope

The KPI layer. `_INDEX-objektmodell.md` already notes that the register holds zero KPIs while
Dashbox visualises them, and proposes its own `_INDEX-kpi.md`. That gap is real but separate.
