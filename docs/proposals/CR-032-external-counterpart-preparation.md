# CR-032: External-counterpart preparation — verification and framing discipline

| Field | Value |
|-------|-------|
| **CR Number** | CR-032 |
| **Date** | 2026-08-28 |
| **Status** | Implemented |
| **Related CRs** | CR-005 (agenda-card-first template, tag system); CR-015/CR-016 (uncertainty markers in `/transcript`) |
| **Skills touched** | `preparation` (SKILL.md) |
| **Breaking Changes** | No — additive, and scoped to external counterparts only |

## Summary

`/preparation` produces a walk-in card plus deep dives (CR-005). That structure is
right for **internal** meetings, where the participants and facts are shared and
the risk of being wrong about someone is low. It is not sufficient when the
counterpart is **external** — a prospect, customer, partner, or competitor — where
the document asserts things about a person and an organisation that the author has
not verified, and where being confidently wrong is expensive in the room.

This CR adds six mechanisms that apply **only** to external-counterpart preparation.
Internal preparation (1-on-1s with colleagues, standups, team syncs) is unchanged.

## Motivation

Two independent observations converged.

First, `/transcript` already solved half of this problem. CR-015 and CR-016
established that an unverified owner or proper noun must be marked (`?`, `Name?`)
rather than asserted, because *a confident wrong attribution is worse than an
honest gap* — it propagates into every downstream document. Preparation files make
exactly the same class of claim (this person's mandate, their tenure, who they must
get sign-off from) and had no equivalent discipline.

Second, field observation of a mature external-meeting preparation agent in
production use — an independent implementation, unrelated to this repo — showed the
same design choice arrived at independently, plus four further mechanisms this
skill lacked. Convergent design across two systems is reasonable evidence that the
choice is structural rather than stylistic.

The gap this closes is not "more sections". It is the difference between a document
that reports what was found and a document that is **honest about what it does not
know, and tells the reader what to do about it.**

## What "external counterpart" means

A counterpart is external when the preparation asserts claims about a person or
organisation outside the author's own team. In practice: contact folders classified
`professional` or `confidential` in `_meta.yaml`, customer and partner folders, and
any first-contact meeting.

It is *not* external for colleagues, direct reports, internal 1-on-1s, standups, or
team meetings — there, shared context makes these mechanisms noise.

## The six mechanisms

1. **Verification marker.** Any claim about the counterpart the skill could not
   ground in a vault file or a source the user supplied is written inline as
   `[UNVERIFIED]`, optionally followed by an instruction to ask. This is the CR-015
   / CR-016 convention carried into preparation. Never silently omit an unverified
   claim, and never assert it.

2. **Source-conflict resolution.** When two sources disagree, do not silently pick
   one. State the conflict, reason about which figure is implausible given known
   context, and issue an explicit instruction about what may be said in the room.
   Then state the reduced claim that actually holds.

3. **Reliability grading.** When the available material is thinner than for
   comparable prior preparations, say so at the top of the speculative section and
   instruct the reader to present the content as expectations rather than findings.

4. **Sensitive ground.** A per-counterpart negative list: what not to say, and why.
   Distinct from the existing "if they push back" field, which is a response;
   this is a prohibition.

5. **Branched opening.** For a first contact or a meeting whose purpose is
   genuinely unknown, the opening is a qualifying question plus branches — including,
   where warranted, an explicit instruction to abandon the prepared material if the
   answer invalidates its premise.

6. **What they are measured on.** One line on the counterpart's own success metric,
   which is frequently not the same as their job description.

## Design constraints

- **Additive.** No existing section, tag, or template field changes.
- **Scoped.** Applies only to external counterparts; internal preparation is untouched.
- **No new file.** Everything lands inside the existing single preparation document
  (CR-005 single-document principle).
- **Honest gaps beat confident guesses** — the CR-015/CR-016 principle, restated for
  a second skill.

## Non-goals

- Not a CRM or enrichment layer. The skill reads the vault and what the user
  supplies; it does not acquire data about people.
- Not a sales playbook. Framing help is bounded to what a preparation document needs.
- No behavioural-signal inference (reading calendar or mail activity as intent).
  Deliberately excluded: it is available to implementers, and out of scope here.
