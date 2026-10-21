# CR-147 — Carried lines are re-read from their source before the card is built

| | |
|---|---|
| **Status** | **Implemented v1.92.3** (2026-10-21) |
| **Contract** | additive — a pre-build pass over the carried lines; the card's contents change, the file formats do not |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`build_agenda.py`, the carried-forward and *Dependencies* sections, SKILL.md step 9) |
| **Related CRs** | CR-057 (the carry-forward agenda), CR-141 (the closed matcher matches on ids), CR-142 (an inference is a tracked state), CR-101 (a generated agenda is a draft: closure evidence), CR-088 (an archive says when it was last fetched, and whether that worked) |

## What happened

Carried lines are written from a meeting's transcript. The next morning's agenda lists them as they were written,
without asking the data whether they still hold. Two days after an issue was closed, a line about it was still on
the card, and the operator asked in the room why. A team member's reading was that the section "is based on
transcripts and not on the data, and keeps nagging week by week about things that have been discussed".

**[E]** Over two consecutive meetings, roughly half the dependency rows were removed on sight by the person
leading: about six of eleven in one, four of seven in the next. Each removal cost room time, and for most of them the
tracker already said *closed*, *merged* or *done*.

The agenda's own text states a rule worth keeping: *a machine that closes items silently is worse than one that
repeats them.* The answer is not silence. It is a close that shows its basis.

## Proposal

1. **Before the card is built, every carried line that carries an identifier (an issue, a pull request, a ticket key)
   is re-read from its source.** If the source says *closed* or *merged*, the line leaves the card.
2. **It leaves with a trace, not silently.** The card's header gets one line, *closed in the data since the last
   meeting: <ids>*, and the details file lists each with its basis and time.
3. **A line without an identifier is not asserted as live.** It goes to the details file under *cannot be checked*.
   It stays on the card only if its owner confirms it in their own minute, and it ages out after two sessions.
   (This is the same state as an unconfirmed inference, CR-142.)
4. **Creation stays in the room.** A dependency is, by definition, a person waiting on a person, raised aloud. The
   data can only close one; it cannot open one.
5. **The pass acts only on a certain close.** An issue in a closed state, or a pull request that names the id and is
   merged. A label change (for instance *fixed, waiting for a test*) never closes a line. CR-141 *suggests* a close
   when the evidence is weaker; this CR *acts* only on the certain case.
6. **If the source cannot be read** (a failed fetch, a permission), nothing is dropped. The line stays and the header
   names the failed source.

## Acceptance

- A carried line about an issue closed since the last meeting does not appear on the card, and appears in the header
  line and the details file with the close time.
- A carried line with no identifier appears under *cannot be checked*, not on the card.
- A failed fetch drops nothing and is named in the header.

## Not in scope

Deciding whether a closed issue was really done (the quality of a close). That is the QA process.
