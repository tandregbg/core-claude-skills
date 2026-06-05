# CR-016: Proper-noun Verification + ASR-vocabulary Hint

| Field | Value |
|-------|-------|
| **CR Number** | CR-016 |
| **Date** | 2026-06-05 |
| **Author** | Alex + Claude Code |
| **Status** | Implemented (v1.20.0, 2026-06-05) |
| **Priority** | Medium |
| **Complexity** | Low |
| **Estimated Scope** | `transcript` + `preparation` (SKILL.md prompt guidance), `ops-config` (one strings key) |
| **Related CRs** | CR-015 (fail-safe owners on undiarized input); CR-007 (Swedish character inheritance); CR-005 (preparation agenda-card-first) |
| **Depends On** | None |
| **Breaking Changes** | No (additive; no-op when every proper noun resolves) |
| **Source** | Independent field comparison of two Swedish transcription tools across four real meetings |

---

## Executive Summary

A field comparison of two Swedish transcription tools reinforced the thesis `/transcript` is built on: the operator's intelligence lives **downstream in their own system**, so transcript **word-fidelity** is the only axis that matters -- word errors propagate into every summary and extraction built on the transcript; tool-side metadata is regenerated downstream and is redundant.

Most of the comparison **validates existing design** -- notably CR-015: the merged-readable-paragraph output some tools produce is exactly the undiarized case the skill already fails safe on. Three findings were not yet reflected:

1. **Proper nouns are unreliable across tools.** Company and personal names get garbled into *plausible* wrong forms that read fine and match nothing. Today the skill does spelling correction *only when a name matches a known entry* -- a plausible-but-unmatched garble sails through as fact.
2. **Failure-mode > failure-count.** Invisible plausible substitutions cost more than obvious garble (a low word-error-rate but smoothed-over transcript can be *less* trustworthy than a higher-error but verbatim one). This says *where* to spend scrutiny: proper nouns and semantic swaps.
3. **ASR keyword-boost.** Putting key proper nouns in the calendar event title gives the ASR vocabulary to grab.

CR-016 extends CR-015's fail-safe philosophy from *owners* to *all proper nouns*, states the failure-mode principle as scrutiny guidance, and has `/preparation` surface a names-for-the-recording hint. Prompt-only and additive.

## Problem

- Name Resolution (`skills/transcript/SKILL.md`) corrects the *spelling* of names it can **match** against `team[]`, `_contacts/*/_meta.yaml`, or the filename. It is silent on the opposite failure: a proper noun the transcriber garbled into a different plausible token that matches nothing.
- These are the *expensive* errors: they read cleanly, so they are not caught on sight, and they propagate into every downstream deliverable. Typical shape: a real surname rendered as a different real-looking surname, or a company name as a phonetic near-miss.
- The skill had no instruction to *prefer* flagging an unmatched proper noun over committing it as fact -- so the model committed plausible garble confidently.

## What was decided NOT to change (honesty check)

- **Tool-specific branching.** The diarized/undiarized binary (CR-015) already captures the real distinction; naming specific tools would couple the skill to a vendor list. Not added.
- **Two-transcript reconciliation / korskontroll.** The strongest workflow idea (run two independent tools; divergence marks what to verify) is real but a meatier feature -- the skill processes one transcript today. Deferred to a future CR.
- **Banished CR-006 headings.** Not reintroduced.
- **ASR itself / diarization.** Out of skill scope, as in CR-015. The keyword-boost hint is an upstream nudge, not an ASR change.

## Changes

1. **`skills/transcript/SKILL.md`** -- new section **"Proper-noun verification (critical, CR-016)"** after the CR-015 Speaker-attribution section: build a known-entity set from `team[]`, `_contacts/*/_meta.yaml` (`display_name`/`aliases`/`company`), `terminology[].term`, and the filename; for each person/company name, resolve to canonical spelling if matched, else mark `Name?` or collect into a `> ⚠ Namn att verifiera:` note; states the failure-mode principle (plausible substitutions cost more than obvious garble); logs an `edge_case` when flagging and `correction` on user fix. No-op when every name resolves.
2. **`skills/transcript/SKILL.md`** -- Step 4.5 `edge_case` example list extended with "unresolved proper noun flagged for verification (CR-016)".
3. **`skills/preparation/SKILL.md`** -- one-line `{strings.preparation.recording_names}` hint in the walk-in card, reusing the entities the Step 2.5 cross-context scan already gathers (contact `display_name`, company, top topic keywords). Stays within CR-005's agenda-card-first / frozen-at-meeting-time constraints.
4. **`skills/ops-config/base.yaml`** -- new `preparation.recording_names` strings key in both language blocks ("Names for the recording" / "Namn för inspelningen").

## Verification

- Re-reading the new rule against a garbled company or surname that matches no known entry: it is flagged `…?`, while a name present in `team[]` / `_contacts` resolves cleanly to canonical spelling -- it catches the invisible-plausible case without touching known names.
- `/insights compile` clusters repeated Step 4.5 entries (`edge_case` "unresolved proper noun", plus any user `correction`) into a `skill_pattern` targeting `transcript`.
- `grep` confirms no CR-006 banished headings were reintroduced.
- Version bumped 1.19.0 -> 1.20.0 in README and ecosystem.yaml. No `contract_version` change.
