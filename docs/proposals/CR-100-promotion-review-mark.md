# CR-100 — A person's promotion review, recorded in the entry and honoured by compile

| | |
|---|---|
| **Status** | **Implemented 2026-09-27, v1.85.0** — contract 35 |
| **Contract** | additive (34 → 35) — one optional field on `_insights.yaml` entries, one new writer, one optional config key |
| **Date** | 2026-09-27 |
| **Area** | `_insights.yaml` schema, `vault_conventions` (writers), `insights` compile Pass 2, new `skills/insights/promotion_candidates.py` |
| **Related CRs** | CR-013 (the lifecycle), CR-094 (grouping that can fire), CR-098 (claim-level checks, step 3b), CR-015 in the dashboard's own repo (the safe-write pattern). Pairs with the dashboard's review-surface CR, which renders what this declares |

## What happened

CR-098 made promotion honest and, in doing so, made it clear that promotion is a reading task. On
one mature vault the mechanical gates took 55 candidate groups to 39; **reading took 39 to 11.**
That reading currently happens in a terminal, against a one-off script that re-implements the
gates and dumps full summaries to a scratch file. It is not repeatable, and the decision leaves no
trace: a promoted rule carries a `confirmation_count` but nothing says who judged the group, when,
or which groups were looked at and turned down.

The dashboard is being given a review surface for this. It will show candidate groups with their
evidence and let a person approve, reject or split them. That surface needs somewhere to record
the decision, and compile needs to act on it. Neither exists.

## Two findings that shape the proposal

**1. Pass 2 is part arithmetic, part judgement, and only the arithmetic can be shared.** Steps 1–3
contain deterministic gates (type, shared tags or a shared primary tag, `status: active`,
threshold, `single session`) and judged ones (semantic agreement on the claim, whether a shared tag
names a topic or a property of the claim, splitting, step 3b). A second implementation of the
arithmetic in the dashboard is how the two would drift, and the judged parts cannot be implemented
in code at all. So the arithmetic moves into one script both use, and the judgement stays where it
is: with the model in compile, or with the person on the review surface.

It follows that a review surface and compile **cannot** be expected to report the same group
count. They agree on the *candidates* (the script's output); the *qualifying groups* differ exactly
by the judgement, which is the point.

**2. The line between observation and judgement is already drawn.** `outbound_dispatch` lets the
dashboard record what it did (a status note, a channel) and forbids it to write what an outcome
means. `confidence: rule` is the second kind: it turns entries into a standing instruction read by
every later `/transcript` and `/ops` run. A person's approval of a group is the first kind: *this
person, on this date, judged these entries to make one claim.* So the dashboard may write the
approval, and compile stays the only writer of `confidence`.

## Proposal

### 1. `skills/insights/promotion_candidates.py` — the arithmetic, once

A stdlib script (same shape as `skills/ops/build_agenda.py`) that reads one folder's
`_insights.yaml`, or a folder tree, and prints candidate groups as JSON:

- candidates: `confidence` hypothesis or absent, `status: active`, promotable `type` (step 1)
- grouping: same `type`, two shared tags or a shared primary tag (step 2's tag gate)
- threshold from `workflows.knowledge_extraction.evolution.compile_threshold` (default 3)
- `single session` marked, not dropped: every group reports its **distinct-date count**
- if the optional `insight_topic_tags` list is configured (see 4), each shared tag is marked
  `topic: true|false`; without it, nothing is marked and the judgement stays wholly with the reader
- each group carries a stable **group key**: the sorted entry ids plus a hash of their `date`,
  `summary` and `tags`, so a later change to any member produces a new key

It never judges agreement, never splits, never checks contradictions and never writes. Compile
Pass 2 uses it for steps 1–3's arithmetic; the dashboard calls it (or reads its JSON) instead of
re-implementing the gates.

### 2. `promotion_review` — one optional field, on the canonical entry

```yaml
promotion_review:
  decision: approved          # approved | rejected
  date: 260927
  by: dashboard               # which surface recorded it; a person's name is not required
  group: [12, 47, 83]         # the entry ids judged together, canonical first
  group_key: 3f9c…            # from promotion_candidates.py at review time
  reason: null                # required on rejected: topic-only tags | contradiction |
                              #   not a standing instruction | split | other: <text>
```

Declared in the `_insights.yaml` schema. **Additive:** a reader that ignores it behaves as today.
Written only on the canonical entry (the group's earliest by `date`), so one group has one record.

### 3. Writers

`_insights.yaml` `writers` gains the dashboard, **for `promotion_review` only**, recorded as a
field-scoped write the way `outbound_dispatch` scopes the manifest. `never:` states that it does
not write `confidence`, `confirmation_count`, `confirmations[]`, `status` or `superseded_by`, and
does not edit summaries or tags.

### 4. Optional config

```yaml
workflows:
  knowledge_extraction:
    evolution:
      promotion_review: optional      # optional | required   (default: optional)
      insight_topic_tags: []          # tags known to name subject areas, not claims
```

- `optional` (default, today's behaviour): compile judges groups itself, and honours any review it
  finds.
- `required`: compile promotes **only** approved groups and reports every unreviewed qualifying
  group as `awaiting review`. For vaults where the rule layer should change only by a person's
  decision.

### 5. Compile Pass 2 honours the mark

Between steps 3 and 3b:

- **Approved, and the group key still matches:** promote. Step 3b still runs: an approval does not
  bypass the contradiction check, because a reversal is exactly what a reviewer can miss. A group
  that fails 3b is reported `needs review: contradiction (approved <date>)` and not promoted.
- **Approved, key no longer matches** (an entry changed, was added or was superseded since): not
  promoted on the old approval. Reported as `review stale`.
- **Rejected, key matches:** skipped, reported with the recorded reason. Not re-offered.
- **Rejected, key no longer matches:** treated as unreviewed. The group changed, so the old
  rejection no longer describes it.
- **Split:** the reviewer approves a subset. That subset is a group of its own with its own key and
  canonical; the remainder is re-evaluated against the threshold.

Step 4 is unchanged: canonical, `confidence: rule`, `confirmation_count` by distinct dates,
`confirmations[]`, supersede the rest. The `promotion_review` block stays on the entry after
promotion as the record of who approved it.

## What this does not do

- Does not let the dashboard write `confidence`. One writer of that field is what keeps step 3b in
  the path of every promotion.
- Does not automate the judgement. Three measured attempts to replace it with a number are recorded
  in CR-094 and CR-098; this CR records the judgement instead of replacing it.
- Does not change demotion (Pass 3), which is driven by `correction` entries.

## Acceptance

- `promotion_candidates.py` run on the vault from CR-098 contains every group compile promoted in
  its CR-098 run among its candidates, marks single-session groups with a distinct-date count of 1,
  and its candidate count is recorded as the new baseline.
- A group approved on the dashboard is promoted by the next compile with `confirmation_count` equal
  to its distinct-date count; `promotion_review` is kept on the canonical.
- A group containing a decision and its later reversal, approved on the dashboard, is **refused**
  by compile as `needs review: contradiction`.
- A rejected group does not reappear until one of its entries changes; then it does.
- With `promotion_review: required`, an unreviewed qualifying group is reported `awaiting review`
  and not promoted.
- `check-components.py` passes with the field-scoped writer declared; contract_version 35.

## Outcome (2026-09-27, v1.85.0)

Implemented as proposed, with one addition and one decision made explicit.

- **`split_from` added to the block.** The proposal said both *a member added since the review makes
  it stale* and *a split subset is a group of its own*. From the recorded ids alone the two are
  indistinguishable: both leave a review over a subset of the current group. Treating the subset as
  still valid would let an entry added after the review -- possibly the very reversal step 3b exists
  for -- sit outside an approval that then promotes without it. So a subset review is valid only
  with `split_from` equal to the current group's key; otherwise it, and the group, are `stale`.
- **Grouping is connected components of the tag gate**, not greedy seeding. Tag overlap is not
  transitive; a seed keeps whichever pair it met first, so results would depend on file order and a
  pair could vanish unseen. Components err toward the superset and leave the split to the reader,
  which Pass 2 already requires. On the measured vault the largest component was 9 entries.
- **Topic marking only when configured.** With `insight_topic_tags` empty the script marks nothing;
  whether a tag names a topic stays a judgement.
- **Legacy confidence values** (`high`/`medium`/`low` from early extractions) read as hypotheses, as
  the dashboard already does. Unquoted ISO dates, which YAML parses as date objects, are normalised
  to YYMMDD -- found on the first real run.
- Measured on one mature vault, read-only: 111 folders scanned, 56 candidate groups, 6 of them
  single-session, largest 9, all unreviewed. The count sits next to CR-094's 55; the difference is
  the judgement compile applied then, which is the point.
- Tests: `tests/test_cr100_promotion_candidates.py`, 21 cases (gates, threshold, single session,
  topic marking, key stability and change, all review states, split and stale split, dot-folders,
  non-transitive overlap, ISO dates).

