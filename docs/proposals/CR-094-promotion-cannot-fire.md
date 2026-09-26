# CR-094 — The promotion criterion cannot fire, so the rule layer is empty

| | |
|---|---|
| **Status** | **Proposed 2026-09-26** |
| **Contract** | none. `_insights.yaml` schema is unchanged; only the clustering criterion in `insights/SKILL.md` Pass 2 changes |
| **Date** | 2026-09-26 |
| **Area** | `skills/insights/SKILL.md` Pass 2 (hypothesis → rule promotion), line ~319 |
| **Supersedes** | nothing. Fixes an implementation detail introduced after CR-013 |

## What was measured

A `/insights compile` run against a mature vault, 2026-09-26:

| | |
|---|---|
| Insight entries, total | **2 585** |
| Active hypotheses in promotable types | **1 892** |
| Pairs sharing both `type` and ≥1 tag | **1 404** |
| Groups reaching the promotion threshold | **0** |
| Entries with `confidence: rule` | **5** (0.2 %) |

The token-overlap distribution across those 1 404 candidate pairs:

| Overlap | Pairs |
|---|---|
| 0.50 | 1 |
| 0.40–0.49 | 3 |
| 0.30–0.39 | 24 |
| 0.20–0.29 | 195 |
| 0.10–0.19 | 552 |
| 0.00–0.09 | 629 |

**The highest overlap in the entire corpus is 0.50, against a required 0.60.** Promotion is
not rare in this vault — it is unreachable.

## Why

`SKILL.md` Pass 2 step 2 requires, for two entries to group:

> Fuzzy summary match (case-insensitive, ignore stop words; require **≥60% token overlap**)

**CR-013 did not specify 60 %.** It said *"group `confidence: hypothesis` entries by similarity
(same `type`, fuzzy-matched `summary`, overlapping `tags`)"*. The numeric threshold was added
in implementation, and it encodes an assumption that turns out to be false for this corpus:
that two insights describing the same thing will share most of their words.

They do not, because **insight summaries are written by a language model**. Each one is phrased
freshly even when the underlying observation recurs. Two entries can be the same insight and
share almost no vocabulary:

- *"Den som byggt en AI-analys kan inte själv bedöma om svaren är bra"*
- *"Whoever builds a feature also chooses the account it works on"*

Same structural claim — the builder cannot validate their own work. Token overlap: near zero.

Verbatim near-duplicates are exactly what a well-behaved extraction step is designed **not** to
produce, so the criterion selects against the corpus it is meant to read.

## Why it matters beyond tidiness

CR-013's stated purpose was gap **(b)**: *"`/ops` and `/transcript` write to `_insights.yaml` but
do not read from it. The knowledge accumulation engine never closes the loop into knowledge use."*

The loop is closed by the rules-walk — `/transcript` Step 0.5 and `/ops` load entries where
`confidence: rule` AND `status: active`, capped at 20, as standing instructions. With 5 rules in
2 585 entries, **that preamble is effectively empty in every run.** Four months of accumulation
influence no behaviour.

The skill's own documented example output (`SKILL.md` line ~252) reads `Rules: 18` — the
documentation presents a working rule layer that the implementation cannot produce.

## Proposed change

**In section:** Pass 2, step 2 (`hypothesis → rule promotion`)
**Action:** Replace the similarity test.

> 2. **Group by similarity within the folder:**
>    - Same `type`
>    - **At least two shared tags**, or one shared tag when it is the primary tag (first in
>      `tags[]`) of both entries
>    - **Semantic agreement on the claim**, judged rather than counted: two summaries group when
>      they assert the same thing about the same kind of subject, even with no shared vocabulary.
>      Paraphrase is the norm, not the exception — the corpus is model-written.
>    - Token overlap is **not** a gate. It may be used as a tie-breaker when choosing which of
>      several candidate groups an entry joins.
>
>    Conservative bias is retained through the tag requirement and the threshold: prefer false
>    negatives over false promotions. A promoted rule becomes a standing instruction, so the cost
>    of a wrong promotion is higher than the cost of a missed one.

**Also correct** the example output at line ~252 so it cannot be read as a description of
current behaviour, and **state the measured baseline** so the next run can tell improvement from
noise.

## Alternatives considered

**Lower the number to 0.30.** Rejected: it would admit the 24 pairs at 0.30–0.39 but still miss
every genuinely-recurring insight that happens to be phrased differently. It tunes the wrong
mechanism — the problem is that token overlap does not measure what promotion needs.

**Manual promotion only.** Rejected as the primary fix: it makes the rule layer a function of
whoever remembers to curate it. Worth adding as a *supplement* — an explicit
`/insights promote <file>#<id>` for the case where a human recognises a rule before three
confirmations exist.

**Leave it.** Rejected: an unreachable criterion is worse than no criterion, because the skill
reports `Promoted 0 rules` as a normal result and nothing signals that the mechanism is dead.

## Verification

After the change, a compile run on the same corpus must:
1. Promote a non-zero number of rules, and
2. Have each promotion inspected once — is the canonical entry actually a standing instruction,
   and do its confirmations genuinely assert the same claim?

If (2) shows loose grouping, tighten the tag requirement before loosening anything else.

## Evidence

Observed in one mature vault, 112 `_insights.yaml` files. The measurement is reproducible from
the corpus: cluster active promotable hypotheses by `type` + shared tag, compute token overlap
per pair, and read off the distribution maximum.
