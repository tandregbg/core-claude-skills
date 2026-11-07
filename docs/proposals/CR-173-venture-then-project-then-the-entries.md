# CR-173 — The living view groups by context and calls it a project

| | |
|---|---|
| **Status** | **Implemented v1.96.1** (2026-11-05), contract unchanged |
| **Contract** | none — a rendering change in `skills/inbox/survey.py` |
| **Date** | 2026-11-05 |
| **Area** | `skills/inbox/survey.py` (`render_living`, `match_project`) |
| **Related CRs** | CR-171 (a vault's file names are data), CR-097 (analytics) |

## What the operator asked for

> "Grupperingen just nu är på verksamhet och projekt. Kan vi inte få varje segment att visa
> verksamhet först, hur många poster, sen verksamhet, projekt och sen de sakerna i listan — så att
> Acme Omstart blir en lista, och sen kommer Acme Bravo, men så att det syns tydligt i
> rubriken."

And, pointing at a board section: *"här står det inget projekt på punkt 71, 72 och så vidare."*

## What it does today

Two levels: `## <venture>` then `### \`<context>\` — N · projekt **<Project>**`.

**The context is the organising key and the project is a suffix.** So a reader scanning for *the
mobile app* finds a heading that leads with a slug, and a group with no project looks the same as a
group whose project simply was not matched — nothing distinguishes *no project* from *unknown*.

## The second defect, found while measuring

`match_project` matches when either string is a prefix of the other. That is right for its
documented case — a context `kickoff` against a portfolio row `Kickoff 2026`. It is wrong when the context
**is the venture's own name**:

```
match_project("acme", …) -> "Acme Omstart"     # "acmeomstart".startswith("acme")
```

**[E] Measured on the operator's vault 2026-11-05: 104 of 125 Acme entries were labelled
`projekt Acme Omstart`** — the board items, the website work, the terminology
work, the weekly status. The label was false for most of them, and it was false *invisibly*, because a
suffix on a heading reads as decoration rather than as a claim.

A venture name is not a project abbreviation. The fix is one rule: **a context that equals a venture
name in the map never matches a project.**

## The change

Three levels — venture, then project, then the entries:

```
## Acme — 125 poster

### Acme · Kickoff 2026 — 12 poster
### Acme · Acme Kunskap — 1 post
### Acme · utan projekt — 112 poster
```

- **`utan projekt` is written out**, so an unmapped group is visibly a group with no project rather
  than a rendering gap.
- The per-row `Verksamhet` and `Projekt` columns go, and **`Kontext` takes their place**. Both now
  sit in the heading two levels up. This reverses the 261020 operator note that a row must be
  readable without its heading — taken knowingly: that note was written when the heading carried a
  slug, and the operator has now asked for the opposite emphasis.
- Contexts are listed in the group's intro line when there is more than one, so the slug is still
  findable.

## Acceptance

- A venture section lists project groups, each headed `<Venture> · <Project> — N poster`
- A group with no project is headed `<Venture> · utan projekt`
- `match_project` returns `None` for a context equal to a venture name
- `bravo` still matches `Kickoff 2026`

## Implemented

`match_project` takes the venture names and returns `None` for a context equal to one.
`render_living` groups `venture -> project -> entries`; the row is **seven cells**
(`# | Kontext | Läge | Uppgift | Förslag | | Godta`), and `utan projekt` sorts last in a venture
whatever its size.

**[E] On the operator's vault the false label moved 104 entries**: `Acme · Acme Omstart — 104`
became `Acme · utan projekt — 111`, with `Kickoff 2026 — 12` and `Acme Kunskap — 1` standing
as the real project groups.

**What the fix exposes, and does not solve.** 111 of 124 Acme entries have no project, because
the context field does not carry one — `acme · Omstart — PRIO` and `acme · styrelsen` both
reduce to `acme`. The old rendering hid that behind a label; this one states it. Giving those
entries a real project is a data question for the operator, not a rendering one.

`tests/test_cr173_venture_project_grouping.py` — 6 tests, including that `bravo -> Kickoff 2026` survives
and that a caller passing no ventures keeps the old behaviour. `test_cr138_survey_contract.py` was
updated with the contract: ten assertions moved from the eight-cell row to the seven-cell one, and
the ordering test now reads project groups. **Full suite: 1146 tests, OK.**
