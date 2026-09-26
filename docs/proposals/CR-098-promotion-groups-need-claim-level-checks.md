# CR-098 — Promotion groups need claim-level checks, not more tag arithmetic

| | |
|---|---|
| **Status** | **Proposed 2026-09-26** |
| **Contract** | none. Adds two checks to `insights` Pass 2; no schema change |
| **Date** | 2026-09-26 |
| **Area** | `skills/insights/SKILL.md` Pass 2, steps 2–4 |
| **Follows** | CR-094 (implemented v1.82.0), which made promotion possible at all |

## Context

CR-094 replaced an unreachable ≥60 % token-overlap gate with: same `type`, two shared tags (or a
shared primary tag), plus a judgement that two entries make the same claim. Promotion went from 0
candidate groups to **55** on one mature vault.

Its own verification step 2 was left open: *inspect the first promotions.* This CR is that
inspection, done on the ten largest groups before anything was written.

## What the inspection found

| Verdict on the ten largest groups | Count |
|---|---|
| Would promote as-is | **1** |
| Would promote with a lower `confirmation_count` | 1 |
| Contains a real cluster but needs splitting first | 1 |
| Reject — shared topic, no shared claim | 6 |
| Reject — group contains a contradiction | 1 |

**Roughly one group in ten is a rule.** The tag gate is doing what it can; the remaining errors
are not tag-shaped.

### Three failure modes

**(a) A primary tag is a topic, not a claim.** `seo`, `payments`, `cs-dev`,
`leverantörsrelation` name subject areas. A six-entry `seo` group held two unrelated things: four
entries about **measurement discipline at low volume** (*"weekly movement is noise; judge whether
the position holds"*) and two about **navigation and search intent**. Same topic, different
claims, one group.

**(b) Contradictions group tightly.** A four-entry `architecture` group held a decision and its
own reversal — *"enforce in the backend, not app-side"* (260306) and *"enforcement reversed from
backend to app-side"* (260311). They share **three** tags, because a reversal is about exactly the
same thing as the decision it reverses. Step 4 makes the **earliest** entry canonical, so the
promoted rule would be **the decision that was later revoked.**

**(c) Same-session entries count as independent confirmations.** A five-entry `estimation` group
had four entries dated 260610 and one 260611. `confirmation_count: 5` implies five observations;
it was one analysis session and a follow-up.

## What was measured about the obvious fixes

Both candidate tightenings were tested against all 55 groups before proposing:

| Criterion | Groups | Entries |
|---|---|---|
| CR-094 as implemented | 55 | 183 |
| Require 2 shared tags **always** (drop the primary-tag shortcut) | 21 | 66 |
| Require ≥2 distinct dates | 49 | 165 |
| Both | 20 | 63 |

**Neither fixes the three failure modes, and the tag rule makes one worse:**

| Pair | Shared tags | Outcome | Should be |
|---|---|---|---|
| decision + its reversal | 3 | **passes** | rejected |
| navigation + search-intent | 2 | **passes** | separate groups |
| two measurement-discipline entries | **1** | **fails** | same group |

The tightening **removes a genuine cluster and keeps both bad ones.** A reversal shares more
vocabulary with its decision than two paraphrases of one principle share with each other — which
is the same lesson CR-094 already learned about token overlap, reappearing one level up.

The date rule is nearly inert: 55 → 49, and it passes the same-session group it was meant to
catch (four entries on 260610 plus one on 260611 satisfies "≥2 distinct dates").

**Conclusion: tag and date arithmetic cannot separate these cases.** The checks must operate on
the claim.

## Proposed change

**In section:** Pass 2, step 2
**Action:** Add after the semantic-agreement bullet.

> - **A shared tag that names a topic is not evidence of a shared claim.** When the tags two
>   entries share are subject areas (`seo`, `payments`, `architecture`, a supplier name) rather
>   than properties of the claim, the tag overlap carries no weight — decide on the summaries
>   alone. A group that survives only on topic tags is not a group.
> - **Split before promoting.** When a candidate group turns out to hold two or more distinct
>   claims, split it and apply the threshold to each part. A six-entry group that is really
>   four-plus-two yields one promotion, not one rule with two claims in it.

**In section:** Pass 2, new step between 3 and 4
**Action:** Add.

> 3b. **Contradiction check.** Before promoting, read the group for entries that reverse or
>     negate each other — a decision and its later reversal, a pattern and an entry saying it no
>     longer holds. Such a group must **not** be promoted on the earliest entry, because the
>     earliest is the superseded one. Either:
>     - mark the superseded entry `status: superseded`, `superseded_by: <later id>` and re-apply
>       the threshold to what remains, or
>     - skip the group and report it as `needs review: contradiction`.
>
>     A reversal shares more vocabulary with what it reverses than two paraphrases of one
>     principle share with each other, so no similarity measure will catch this. It has to be read.

**In section:** Pass 2, step 4
**Action:** Modify the `confirmation_count` rule.

> - Set `canonical.confirmation_count` to the number of **distinct dates** in the group, not the
>   number of entries. Entries written from one session are one observation however many were
>   extracted. Keep every entry in `confirmations[]` — the provenance is not lost, only the count
>   is honest.

**Also:** report skipped groups with their reason (`topic-only tags`, `contradiction`,
`single session`) rather than silently dropping them. A promotion pass that reports only successes
cannot be audited.

## Why not lower the threshold instead

Raising or lowering `compile_threshold` changes how many groups qualify, not whether a group holds
one claim. The measured problem is composition, not size. A three-entry group with one claim is a
better rule than a six-entry group with two.

## Verification

Re-run the inspection on the ten largest groups after the change. The target is not "more
promotions" — it is that **every promoted group holds exactly one claim, and no promoted canonical
entry has been superseded by a later entry in its own group.** If a contradiction still reaches
promotion, step 3b is not being applied.

The honest expectation from this vault is **single digits** of promotions, not 55. That is the
right order of magnitude for four months of accumulation: most observations are observations.

## Evidence

One mature vault, 2 585 entries. 55 candidate groups under CR-094; ten largest inspected by hand;
one promotable as-is. Both proposed arithmetic tightenings measured across all 55 and shown to
remove a genuine cluster while keeping a contradiction. Folder and person names withheld.
