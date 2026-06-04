# CR-014: Rolling Plans — Participant-Triggered Per-Axis Living Planning Docs

| Field | Value |
|-------|-------|
| **CR Number** | CR-014 |
| **Date** | 2026-06-04 |
| **Author** | Alex + Claude Code |
| **Status** | Implemented (v1.18.0, 2026-06-04) |
| **Priority** | Medium |
| **Complexity** | Medium |
| **Estimated Scope** | `ops-config` (schema + template), `ops` (post-processing + status), `daily-dashboard` (read-only surface), `ecosystem.yaml` (vault_conventions) |
| **Related CRs** | Builds on the `workflows.verticals` mechanism; CR-010 (vault_conventions); CR-011 (name resolution / config chain) |
| **Depends On** | None |
| **Breaking Changes** | No (additive; absent config = no behaviour change) |
| **Source** | Field use in a production vault — four hand-maintained `rolling-plan-<facilitator>-<partner>.md` docs created and kept in sync manually during 1-on-1 processing |

---

## Executive Summary

Teams running recurring 1-on-1s accumulate **per-relationship, cross-meeting state** that no current artifact captures: a meeting summary is point-in-time, a vertical is topic-longitudinal, and `_tasks.yaml` is a flat private ledger. What's missing is a **relationship/axis-longitudinal** doc — one shareable view per 1-on-1 partner of "what's on now / next / later, and who owns what" for the orthogonal workstream that partner owns.

This CR adds a generic, config-driven `workflows.rolling_plans` capability to `/ops`, mirroring `verticals` but with a **participant trigger**, plus a read-only surface in `/daily-dashboard`. It is the participant-keyed counterpart to verticals (topic-keyed).

## Problem

Hand-maintained rolling plans have two failure modes:

1. **Drift.** The same item gets copied into two rolling plans with diverging status, or a summary updates while the plan goes stale. (Observed: an LCP metric, a UX-item count, and a "decide tomorrow vs already-deferred" status all drifted between a rolling plan and the summary feeding it.)
2. **No trigger.** Nothing reminds you to update partner X's plan after a 1-on-1 with X — it depends on the operator remembering.

Structurally this is the gap `verticals` already solved for topics, keyed on **participant** instead of **topic**.

## Solution

### Part 1 — Config schema (`ops-config/schema.md`)

```yaml
workflows:
  rolling_plans:
    - path: string               # rolling-plan doc, relative to venture root  (required)
      axis: string               # one-line workstream description             (required)
      participants: [string]     # trigger set; resolved via team[]/_contacts  (required)
      language: enum             # english/swedish/input/per_claude_md (default: org language)
      status: enum               # active (default) | placeholder | archived
      trigger: enum              # on_participant_match (default, only value)
```

`participants` resolves with the **same name-resolution algorithm** `/ops` already uses. A plan fires when the processed meeting's resolved participant set intersects `participants`.

### Part 2 — `/ops` post-processing step (Step 9)

New "Update Rolling Plans" subsection after "Check Verticals": match by participant, suggest update (yes/no/select), and on confirm move completed rows into the just-written summary, add new NOW items in the owner column, reflect decisions (never re-introduce stale wording), keep configured language. Golden rule: **one item = one owner = one doc** — rows belonging to another axis are linked, not copied. Missing target file → offer scaffold from the template; never error.

### Part 3 — Cross-link integrity

Each plan carries a "Sister documents (other axes)" block generated from the other configured plans' `axis` strings; `/ops` keeps it consistent.

### Part 4 — `/ops status`

Reports registered rolling plans per org (count + axes), alongside verticals.

### Part 5 — `/daily-dashboard` (read-only)

Org-mode "Rolling plans" section links each plan and optionally pulls its NOW block. Reads, never maintains.

### Part 6 — Template

`skills/ops-config/templates/rolling-plan.md` — generic, placeholder-driven; used by the scaffold path.

## Generic-by-construction (no hardcoding)

No person/org/path/axis/language values appear in any skill file — all of it is config data. The only new vocabulary in skill code is the schema keys (`rolling_plans`, `axis`, `participants`, `status`, `trigger: on_participant_match`) and the generic template. An org defining no `rolling_plans` sees **zero** behaviour change.

## Out of scope

- Auto-deciding row ownership / auto-moving items between axes (operator confirms; skill assists).
- Two-way sync with `_tasks.yaml` (cross-reference only; different altitude).
- Non-participant triggers (topic/schedule) — a later CR if needed.
- `ops-base/SKILL.md` was intentionally **not** touched: it does not document `verticals` either, so rolling plans follow the same precedent (documented in `ops/SKILL.md` + `ops-config/schema.md`).

## Backward compatibility / migration

Purely additive. Existing vaults are unaffected until they add `workflows.rolling_plans`. Vaults already hand-maintaining rolling plans migrate by registering existing files in their `_ops.yaml` — no file moves; the participant trigger then keeps them current.

## Implementation (v1.18.0)

- `skills/ops-config/schema.md` — "Rolling Plans (CR-014)" section.
- `skills/ops-config/templates/rolling-plan.md` — new template.
- `skills/ops/SKILL.md` — Step 9 "Update Rolling Plans"; config table row; `/ops status` reporting.
- `skills/daily-dashboard/SKILL.md` — read-only "Rolling Plans (Org Mode)" section.
- `ecosystem.yaml` — `core_skills_version` 1.17.1 → 1.18.0; `vault_conventions.per_folder` entry for `rolling-plan-<facilitator>-<partner>.md`.
- `CHANGELOG.md` — `[1.18.0]` entry.

## Acceptance criteria

- [x] With `rolling_plans` configured, processing a 1-on-1 with a matching participant offers a yes/no/select update.
- [x] Declining leaves the plan untouched; confirming updates NOW/NEXT/LATER and moves completed rows into the summary.
- [x] Missing target file offers a scaffold from the template instead of erroring.
- [x] Sister-documents block stays consistent across registered plans.
- [x] `/ops status` lists registered rolling plans.
- [x] `daily-dashboard` surfaces (links) registered plans when present, never writes to them.
- [x] No org/person/path/axis string appears in any skill file; an org with no config sees no change.

---

*Generic counterpart to `verticals`: verticals are topic-keyed, rolling plans are participant/axis-keyed. Same lifecycle, same update-after-meeting UX.*
