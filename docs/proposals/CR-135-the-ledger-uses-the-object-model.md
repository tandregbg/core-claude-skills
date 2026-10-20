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
| `verksamhet:` | **optional** — one of the eight from `_INDEX-verksamheter.md`, or absent | declared enum; an undeclared value is a finding, **an absent one is not** |
| `projekt:` | optional | **must match a row in `_INDEX-projekt.md`** — an entry naming a project the portfolio does not have is a finding, in either direction |
| `objekttyp:` | only when the entry is **not** an Uppgift | the seven from `_INDEX-objektmodell.md`; makes järnregel 2 executable |

**`verksamhet:` is optional, and that is a finding of the review rather than a concession.**
The first draft of this CR made it required, on the assumption that everything belongs to some
business. It does not. `_INDEX-verksamheter.md` binds the attribute to *whose business a thing is*,
and a follow-up, a watch or a loose contact is nobody's: on the measured vault **20 of 199 entries**
are defined by their activity type and correctly carry no venture. Requiring the field would have
forced twenty entries into a venture they do not have, and the register would read as decided where
it is simply not applicable.

So three states, not two, and they must stay distinguishable: **a venture**, **deliberately none**
(the activity type is the primary attribute), and **undecided**. Collapsing the last two is what made
the first worksheet unreadable — it reported twenty correctly-classified entries as open questions.

**[E] And the ventures already answer "bound to me, not to a business".** The decision test's step 7
reads *"bygger du det annars för egen räkning, utan att det är en produkt som säljs? → Fria projekt"*.
Seven entries covering the operator's own tooling were sitting as undecided until the test was read;
they are Fria projekt, which is explicitly **not** Personligt (*"livet, inte affären"*).

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

## What the first pass of the worksheet exposed

**[E] The thing the operator works on most had no portfolio row.** `core-skills` itself -- five CRs
in one day, a contract version, a landing page, an undecided release number -- was absent from
`_INDEX-projekt.md`, together with the vault tooling and the assistant configuration. So
`projekt: core-skills` could not have validated against the register in either direction. A row was
added on 2026-10-20, typed `löpande` because the object model's test is decisive: it has no finish
line.

**[E] Prefix matching, not equality.** A ledger context reads `goa` where the portfolio row is
`Goa 2026`. Equality matched **2 of 50** context values; prefix matching took it to **8 of 50**. The
remaining 42 are categories that exist only in the ledger -- which is the measure of how far the two
registers had drifted apart.

## Not in scope

The KPI layer. `_INDEX-objektmodell.md` already notes that the register holds zero KPIs while
Dashbox visualises them, and proposes its own `_INDEX-kpi.md`. That gap is real but separate.
