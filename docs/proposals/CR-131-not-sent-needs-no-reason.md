# CR-131 — A *not sent* outcome needs no documented reason

| | |
|---|---|
| **Status** | **Proposed** (2026-10-20) |
| **Contract** | narrowing of one requirement — `avskriven` keeps requiring `## Utfall`, but the outcome `Skickades inte` is sufficient on its own |
| **Date** | 2026-10-20 |
| **Area** | `outbox` (SKILL.md `avskriven` section, `resolved.py` plan text), `ops` (`check` outbox findings) |
| **Related CRs** | CR-047 (`avskriven` — resolved without being sent), CR-120 (`hanterad`), CR-103 (status words are declared, not invented) |

## What happened

CR-047 requires `## Utfall` on a withdrawn item to say **why** it was not sent: *"'Not sent, because X' is
an outcome, and an item filed without one is indistinguishable later from an item that was abandoned."*

**[E]** Measured on one vault, 2026-10-20: of 37 withdrawn items, **16 had no outcome at all** and could
therefore not be closed. The oldest was from 2026-06-15. Going through them with the operator produced the
same answer sixteen times over: *it was not sent, and there is nothing more to say.* Three had a reason in
their status note (taken verbally at the meeting; draft overtaken; the meeting happened without a send).
**Thirteen had no reason anywhere, and none was recoverable** — the decision not to send had been made
weeks earlier, in passing, and was never a decision with a motive.

The requirement therefore did not produce reasons. It produced **sixteen items that could not be filed**,
which is the accumulation CR-047 exists to prevent, caused by CR-047 itself.

## The distinction that matters

The requirement is sound for the case it was written for: an item that was *declined* carries information
in why. But *"never got sent"* is not a decision with a motive — it is the absence of one. Demanding a
reason for an absence invents a record.

Compare CR-120, which drew the same line for `hanterad`: no decision was taken, so no outcome is required.
`Skickades inte` is the same shape of fact.

## Proposal

**`## Utfall` stays required for `avskriven`.** What changes is what satisfies it:

- `Skickades inte.` is a **complete** outcome. No reason is required, and `close` writes it without
  prompting when the status note is empty.
- When a status note *does* say why, `close` keeps writing `Skickades inte: <note>` as it does today —
  a reason that exists is never discarded.
- A superseded draft is unaffected: CR-103's `Ersatt av <item>` is still the outcome.

The three states stay distinguishable in the archive, which was CR-047's actual goal:

| Written | Means |
|---|---|
| `Skickades inte: <reason>` | declined, and the reason was known |
| `Skickades inte.` | never sent; no decision with a motive was taken |
| *(no `Utfall`)* | **not filed** — still an open item, exactly as CR-047 intended |

## Why not leave it as practice

The rule was settled with the operator on 2026-10-20 and applied to 16 items that day. It lives in an audit
file in one vault; `SKILL.md` still says the reason is required. The next person to read the convention —
or the next dispatching surface written against it — gets the old rule, and the sixteen items read as
having been filed in violation of it.

## Not in scope

Whether an item *should* be withdrawn. That is the operator's call, and CR-047's warning stands: absence is
never evidence that something was done.
