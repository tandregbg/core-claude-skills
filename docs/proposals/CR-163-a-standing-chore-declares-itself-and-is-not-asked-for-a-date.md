# CR-163 — A standing chore declares itself, and the audit stops asking it for a date

| | |
|---|---|
| **Area** | `inbox` (`survey.py` `propose_for`, the row built for `--table`, SKILL.md `/inbox survey`), `tasks` (v2 schema) |
| **Priority** | Low |
| **Status** | Proposed (2026-10-27) |

---

## The problem

The task audit proposes **SÄTT DATUM** on every entry in the weekly maintenance
routine, on every run, with `?` — a guess. Those entries have no date *by
design*: they are standing chores run on a cadence, not work to be booked.

The generator cannot know that. `propose_for()` sees a line that opens with an
action and carries no date, which is exactly the shape of an entry that *should*
be dated. The proposal is right for everything else; it is wrong only for a
chore, and it is wrong every week, which is how a column of guesses stops being
read at all.

## The change

The entry **declares itself** with `recurring: true` in the ledger, and the
generator respects the declaration instead of guessing:

```python
if row.get("recurring") and state != "FÖRFALLNA":
    return ("LÅT STÅ", True, "återkommande rutin — deklarerad i registret")
```

**A declaration, not a heuristic on the context string.** Matching a prefix such
as `Rutin ·` was the obvious alternative and is rejected: in the vault that
prompted this, two of the four routine entries name the routine and two name the
thing they maintain. A prefix rule would have fixed half of them and added one
more guess to a file whose whole problem is that it guesses.

**An overdue chore is not silenced.** It falls through to the state logic and is
still proposed `NYTT DATUM`: a date that has passed is a real signal even on a
chore. The declaration removes a standing wrong answer; it does not hide the
entry.

`recurring` is optional and absent means `false`, so every existing ledger reads
unchanged.

## Verification

Unit, against `propose_for` directly:

| Case | Result |
|---|---|
| recurring, undated | `LÅT STÅ`, sure |
| recurring, `ODATERADE` | `LÅT STÅ`, sure |
| recurring, overdue 40 d | `NYTT DATUM` — falls through as intended |
| not recurring, P1 undated | `SÄTT DATUM` — unchanged |

End to end, four declared entries in a real ledger: three moved from
`SÄTT DATUM | ?` to `LÅT STÅ | ✓`; the fourth already read `LÅT STÅ` because it
carries a forward date, and was unchanged.
