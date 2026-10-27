# CR-162 — The task audit is grouped by venture, and the state travels with the row

| | |
|---|---|
| **Area** | `inbox` (`survey.py` `render_living`, the `--table --markdown` dispatch, SKILL.md `/inbox survey`) |
| **Priority** | Medium |
| **Status** | Proposed (2026-10-26) |
| **Supersedes** | The `--table --markdown` contract introduced by CR-138 |

---

## The problem

`--table --markdown` and `--migration` covered the same open entries in two
groupings — one by state, one by venture — and the operator read both to answer
one question. That is duplication, not two views.

The state grouping also put the operator's primary attribute last. An entry's
venture is what decides whether it is even his to act on; its state is a
property of its date field. Sections by state scattered one venture's entries
across five headings and asked the reader to reassemble them.

## The change

One view. `render_living()` replaces `render_table()` on the
`--table --markdown` path:

- **Sections are ventures**, `## <Verksamhet> — N poster`, with unmapped
  contexts gathered under `## Utan post i kartan`.
- **Sub-sections are contexts**, `### \`<kontext>\` — N · projekt **<Projekt>**`,
  naming the PORTFÖLJEN project when the context maps to one.
- **The state travels with the row** in a `Läge` cell — `förfallen`,
  `prio utan datum`, `ingen ålder`, `odaterad`, `framåt YYMMDD` — instead of
  deciding the sections.

The row grows from six cells to eight:

```
| # | Verksamhet | Projekt | Läge | Uppgift | Förslag | | Godta |
```

The signal column's header cell stays empty, as before. `Godta` stays empty for
the generator to leave and the operator to fill.

**A forward-dated entry now carries a `Godta` cell.** Under the old contract
`DATERADE FRAMÅT` was a separate flat section with a three-cell row and nothing
to decide. It is no longer a section, so the exception has nothing to attach to,
and the entry is decidable like any other — its date can be wrong.

## What is not changed

- **Coverage.** Every open entry still appears exactly once, and the header
  still carries the ledger's own open count. A subset under this filename
  remains a regression.
- `propose_for()`, the buckets, the `✓`/`?` signal and the `Godta` legend.
- The other four views (`--markdown` alone, `--table` as JSON, `--undated`,
  `--migration`). `--migration` keeps its own purpose: it maps context *values*
  to ventures and carries no `Godta` column, and its decisions belong in
  `_config/verksamhet-karta.yaml`, not in the audit.

## Two things this CR must also do

**1. `render_table()` is now dead code.** It is defined and never called — the
non-markdown `--table` branch prints `json.dumps(states)` directly. Leaving it
is worse than removing it: it is a complete, readable implementation of the
contract this CR supersedes, and the next reader cannot tell which one is live.
**Remove it with this change.**

**2. SKILL.md is the contract and currently describes the superseded view.**
CR-138 exists precisely because the format lived only in code, and any surface
that lost the code "met the requirement by building something plausible
instead". Shipping `render_living` without rewriting `#### The shape of
--table --markdown` reproduces that defect with the documentation pointing at
the wrong shape — which is worse than no documentation, because it reads as
authoritative.

## How this was found

The implementation sat uncommitted in one machine's working tree for at least
five days, in use, generating the vault's live task view. The other machine —
the one the runbook names as the only place core-skills is updated — had a clean
checkout at the same commit and would have produced the superseded format under
the same filename, with no warning.

Nothing detected this. It surfaced while staging that machine's uncommitted work
for transfer. **The drift was caught by an operator, not by any check** — the
same sentence CR-138 already wrote about this file.
