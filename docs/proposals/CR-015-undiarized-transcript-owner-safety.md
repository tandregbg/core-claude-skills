# CR-015: Undiarized-Transcript Owner Safety

| Field | Value |
|-------|-------|
| **CR Number** | CR-015 |
| **Date** | 2026-06-05 |
| **Author** | Alex + Claude Code |
| **Status** | Implemented (v1.19.0, 2026-06-05) |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `transcript` (SKILL.md prompt guidance only) |
| **Related CRs** | CR-006 (Action Item Table + banished exec-summary headings); CR-013 (insight lifecycle / Step 4.5 feedback loop) |
| **Depends On** | None |
| **Breaking Changes** | No (additive; diarized transcripts unaffected) |
| **Source** | Field use: a Deep Thought transcript with no speaker labels yielded two confident-but-wrong action-item owners that the operator corrected; a Fathom recap of the same meeting (audio diarization) got them right |

---

## Executive Summary

`/transcript` resolves the *spelling* of participant names but has no guidance for *who said what* when a transcript arrives as a single unlabeled stream (Deep Thought paste, raw recorder export). On such input, action-item ownership can only be **inferred**, yet the skill committed inferred owners as confident bare names with no confidence signal. This produced wrong owners in production.

CR-015 makes the skill **fail safe** on undiarized input: detect the condition, treat each owner as a hypothesis, prefer `?` / `Name?` over a confident guess, run a final owner self-check before save, and log the condition (`edge_case`) and any user owner-correction (`correction`) so the evolution loop can see the pattern. Prompt-only and additive.

## Problem

- Name Resolution corrects spelling, not attribution. Participant detection assumes extractable speaker labels.
- Undiarized sources (one narrative blob) carry no turn markers, so first-person cues ("jag ska skicka…") prove an action exists but not who owns it.
- The Action Item Table's binary rule (name, else `?`) gave no instruction to *prefer* `?` when ownership is merely inferred — so the model guessed confidently and was wrong.

## What was decided NOT to change (honesty check)

- **Action-item format** — already mandated by CR-006 (owner/prio/deadline table). No change.
- **Executive-summary / "Key takeaways" headings** — deliberately banished by CR-006. Not reintroduced.
- **Diarization itself** — cannot be reproduced from a text paste; out of skill scope. Noted as the durable root fix (feed a speaker-labeled transcript) but implemented as guidance, not code.

## Changes (all in `skills/transcript/SKILL.md`)

1. New section **"Speaker attribution & undiarized transcripts (critical, CR-015)"** after Name Resolution: detect diarized vs undiarized; on undiarized input treat owners as hypotheses, fail safe with `?` / `Name?`, raise confidence only on explicit assignment; final owner self-check on the `Nästa steg` table before save; capture `edge_case`/`correction`; note the diarized-input root fix.
2. **Action Item Table** rule extended: bare name only when an identifiable speaker explicitly takes the action; otherwise `?`.
3. **Step 4.5 `edge_case`** example list extended with "transcript lacks speaker labels (owners inferred)".

## Verification

- Re-reading the new rule against the originating unlabeled transcript would produce `Carol?` / `?` instead of confident-wrong `Alex` — i.e. it fails safe.
- `/insights compile` clusters the three Step 4.5 entries logged for that run (2 `correction`, 1 `edge_case`, `skill: transcript`) into a `skill_pattern` targeting `transcript`, demonstrating the loop would itself surface this change.
- `grep` confirms no banished headings were reintroduced.
