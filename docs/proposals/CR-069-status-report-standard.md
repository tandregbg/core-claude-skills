# CR-069 — a generic Status/Results Report standard in `ops-base`

| | |
|---|---|
| **Status** | Proposed |
| **Contract** | 21 → 22 (**additive** — declares a standard, changes no existing one) |
| **Date** | 2026-09-22 |
| **Area** | `ops-base` (shared standards) |
| **Related CRs** | complements the TWO-TIER **summary** format (meeting-driven); this is its measurement-driven sibling |

## The problem

`ops-base` defines how to write up **a meeting** — the TWO-TIER summary (Concise / Standard /
Extended), canon section order (Next steps → Decisions → Outcome → Discussion → Background). That
format is *event-driven*: its input is a transcript, it looks backward at what was said.

There is a second, distinct kind of report that recurs across projects and has **no shared
standard**: a **status / results report** — measuring where something stands against data over
time. Its input is a data source plus a period, it looks forward, and its job is "is this working,
and what is the one thing slowing it." A daily product-metrics report, a campaign-performance
readout, a project-health check, an experiment result — all the same shape.

Today each such report is invented per project. That produces avoidable, repeated failure modes:
a single-day snapshot presented as if it were a trend; a partial-day figure misread as a stall;
internally inconsistent totals nobody cross-checks; numbers presented as fresh when the source is
stale or coarser than implied; a recommendation with no owner. These are not project-specific
mistakes — they are what any status report gets wrong without a standard.

The shape was recently rediscovered from scratch while building one such report, then found to
generalise unchanged across two different data domains. That is the signal that it belongs in
`ops-base` as a standard the way TWO-TIER already is — defined once, referenced by each skill that
produces a status report, not re-derived each time.

## The change

Add a **Status/Results Report** standard to `ops-base` (a sibling to the TWO-TIER *summary*
standard, not a replacement — they answer different questions). A skill produces a status report by
**referencing** this standard, exactly as meeting summaries reference TWO-TIER; the skill supplies
the domain (the data source, the metric names, the reconciliation rules), the standard supplies the
structure and the discipline.

The standard is business-agnostic — no product, org, or dataset names. Its required elements:

1. **Scorecard first.** Lead with 3–6 headline measures as a **trend** (movement over a period),
   never a point-in-time snapshot, plus one line naming the single biggest thing slowing progress.
   The reader gets the verdict before any detail.
2. **Trend anchoring / partial-period guard.** Compute deltas over complete periods; if the latest
   data point is a partial period (an early-in-the-day snapshot, an in-progress week), anchor the
   trend on the last *complete* period and label the partial one — a partial delta must not read as
   a stall or a spike.
3. **Reconciliation invariants.** The report declares the identities its own numbers must satisfy
   (a total equals the sum of its parts; two independently-computed figures of the same quantity
   agree) and states in the footer that they hold. A failing invariant blocks publication.
4. **Honest provenance and blind spots.** Stamp the data source and as-of timestamp; name explicitly
   what the data *cannot* show (a quantity there is no feed for). Never imply a metric that was not
   measured, or present a coarser/older series as current.
5. **Data-freshness gate (warn, do not fail silently).** Before writing, check each source against a
   declared freshness expectation and its own cadence; if a source is stale, or is a lower-cadence
   rollup than the report implies, WARN at the top of the report (or refuse to publish a stale one).
6. **Owner-ranked actions.** Close with what to do, ranked by impact, each with a named owner and the
   number that justifies it. A recommendation without an owner is not an action.

`ops-base` declares this as a named standard (parallel to the summary format), with a short contract
so a producing skill can be checked for the required elements the way summaries are checked for
canon section order. Business-specific report skills then cite it and add their domain rules.

## Why `ops-base`, not `/ops`

`/ops` processes *meetings* (input = transcript). A status report's input is a *data source*, not a
conversation — putting it inside `/ops` would conflate two report types and blur the skill. But the
*standard* belongs beside TWO-TIER in `ops-base`, which is exactly "shared standards across all
ops-skills." A status-report skill in any repo (business or personal) then references it, the same
way meeting summaries reference TWO-TIER — one source of truth for "how we measure status/results,"
reusable across every venture, without loading `/ops` with a format that is not a meeting summary.

## Scope / non-goals

- **Additive.** Declares a new standard; touches no existing format, section order, or contract. A
  skill that does not produce status reports is unaffected.
- Does **not** prescribe metrics, thresholds, or a data stack — those are the producing skill's
  domain. The standard is structure + discipline only.
- The concrete freshness thresholds, reconciliation identities, and metric names live in each
  producing skill, not here — this standard only *requires that they exist and are honoured*.
