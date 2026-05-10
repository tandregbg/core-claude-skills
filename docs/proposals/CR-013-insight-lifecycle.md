# CR-013: Hypothesis → rule lifecycle for `_insights.yaml`

| Field | Value |
|-------|-------|
| **CR Number** | CR-013 |
| **Date** | 2026-05-10 |
| **Author** | Alex + Claude Code |
| **Status** | Proposed |
| **Priority** | Medium |
| **Complexity** | Low-Medium |
| **Estimated Scope** | `_insights.yaml` schema bump (additive), `/insights compile` extended, `/ops` and `/transcript` rule-loading prelude |
| **Related CRs** | CR-010 (vault_conventions), CR-011 (org-config move; folder-walking resolution) |
| **Depends On** | None |
| **Breaking Changes** | No (additive schema bump 1 → 2; v1 readers ignore new fields) |

---

## Executive Summary

The `insights` skill (CR-007 era, refined in CR-008/CR-009) accumulates per-folder `_insights.yaml` entries from transcripts and `CLAUDE.md` files, compiles execution feedback into `skill_pattern` entries, and proposes `SKILL.md` improvements. **What it does not do** is distinguish a one-off observation from a default-apply rule, and it does not feed insights back into Claude's context before tasks run. Today, every insight is `status: active` until manually superseded, and only the visualisation app reads them.

This CR adds a **two-state confidence lifecycle** (`hypothesis` → `rule`) on top of the existing schema:

1. New observations enter as `confidence: hypothesis`.
2. When `/insights compile` finds 3+ semantically similar hypotheses, the canonical entry is promoted to `confidence: rule`.
3. When a `correction` entry contradicts a rule, it is demoted back to `hypothesis`.
4. `/ops` and `/transcript` load applicable rules from the CWD's `_insights.yaml` chain (per CR-011 resolution) and inject them as a preamble into their working context — actively guiding output, not just accumulating it.

The schema change is additive: existing `_insights.yaml` files remain valid; the visualisation app on schema v1 keeps working.

**Current Problems:**

1. **No confidence layer.** A pattern observed once and a pattern observed twenty times look identical in `_insights.yaml`. Promotion to "always apply" is implicit and unenforced.
2. **No active loading.** Insights are written by `/transcript` Step 3.5, `/ops` Step 5.5, and `/insights *`, but never read back into Claude's context when a new task starts. The system accumulates knowledge but does not recall it.
3. **No demotion path.** When a `correction` arrives that contradicts an established pattern, the only signal is manual `status: superseded`. Patterns silently rot.

---

## Problem Analysis

### What `_insights.yaml` looks like today

Per `skills/insights/SKILL.md` and `skills/transcript/SKILL.md`, an entry is:

```yaml
- id: 17
  type: decision | preference | learning | opportunity | pattern | edge_case | correction | skill_pattern | quote
  date: YYMMDD
  summary: One sentence
  rationale: One sentence
  source:
    file: meetings/management/260420-summary.md
    section: Decisions
  tags: [k1, k2, k3]
  status: active | superseded | archived
  superseded_by: null | <id>
```

`compile_threshold: 3` already exists in `workflows.knowledge_extraction.evolution` (`skills/ops-config/base.yaml`) — but it gates **`skill_pattern` clustering of execution feedback**, not promotion of regular insights to rules.

### The three gaps

**(a) Confidence.** `status` covers archival lifecycle (active / superseded / archived) but not maturity. There's no field that says "this has been confirmed N times, treat as default."

**(b) Active loading.** `/ops` and `/transcript` write to `_insights.yaml` but do not read from it. The "knowledge accumulation engine" never closes the loop into "knowledge use."

**(c) Demotion.** The existing `correction` insight type captures contradictions but only as standalone entries. Nothing connects "I corrected X today" to "the rule that said X should now stop being a default."

### What this CR is not

- **Not a new file format.** No `knowledge.md` / `hypotheses.md` / `rules.md` triplets per folder. The article that inspired this CR uses three markdown files; we already have `_insights.yaml` and mirroring would create two systems to keep in sync.
- **Not a new `/knowledge/` tree.** No vault-wide `INDEX.md` or domain folder. Per-folder `_insights.yaml` plus the CR-011 walking resolution already gives us domain scoping for free.
- **Not a global pre-prompt hook.** Rule loading happens inside `/ops` and `/transcript` execution paths, not on every Claude prompt.

---

## Proposed Solution

### 1. Schema additions (additive, optional)

Bump `schemas.insights` in `ecosystem.yaml` from `1` to `2`. Add four optional fields per entry:

```yaml
- id: 17
  type: pattern
  confidence: hypothesis        # NEW: hypothesis | rule  (default: hypothesis if absent)
  confirmation_count: 1         # NEW: integer, defaults to 1
  confirmations:                # NEW: optional list of source-traceable confirmations
    - source: meetings/management/260420-summary.md
      date: 260420
  contradicted_by:              # NEW: optional, populated on demotion
    - source: meetings/management/260507-summary.md
      date: 260507
  ... existing fields unchanged
```

**Defaults and back-compat:**
- Entries without `confidence` are treated as `hypothesis`.
- Entries without `confirmation_count` are treated as `1`.
- Schema v1 readers (e.g., the current `core-skills-visualisation` build) ignore unknown fields and continue to work.

**Relationship to existing `status`:** `status` and `confidence` are orthogonal. `status` is the curation/archival lifecycle (active/superseded/archived); `confidence` is the maturity lifecycle (hypothesis/rule). A rule can be archived. A hypothesis can be superseded by a more specific hypothesis. Both fields coexist.

### 2. `/insights compile` extension — promotion + demotion passes

The current `compile` subcommand groups recurring `edge_case` and `correction` into `skill_pattern`. Extend it with two additional passes:

**Promotion pass (after the existing skill_pattern compilation):**
1. For each folder's `_insights.yaml`, group `confidence: hypothesis` entries by similarity (same `type`, fuzzy-matched `summary`, overlapping `tags`).
2. For each group with size ≥ `workflows.knowledge_extraction.evolution.compile_threshold` (default 3):
   - Pick the earliest entry as canonical.
   - Set `confidence: rule` on canonical.
   - Set `confirmation_count` to group size.
   - Append each non-canonical entry's `source` to `canonical.confirmations`.
   - Mark non-canonical entries as `status: superseded`, `superseded_by: <canonical-id>`.
3. Log promotions in the compile output.

**Demotion pass (after promotion):**
1. For each entry with `confidence: rule`, scan all newer `correction` entries in the same folder (and parent folders walking up via CR-011 resolution).
2. A correction "targets" a rule if its `summary` semantically contradicts the rule's `summary` and shares overlapping `tags`. (Heuristic: same primary tag, opposing keyword in summary — e.g., rule says "always X", correction says "do not X" or "X was wrong".)
3. For each rule with at least one targeting correction:
   - Set `confidence: hypothesis`.
   - Append the correction's `source` to `contradicted_by`.
   - Reduce `confirmation_count` by the number of contradictions (floor 1).
4. Log demotions in the compile output.

**Configurable knobs (in `workflows.knowledge_extraction.evolution`):**
- `compile_threshold: 3` — already exists, reused for promotion.
- `demote_on_contradiction: true` — NEW, default true.

### 3. Rule-loading prelude in `/ops` and `/transcript`

Both skills already determine "what folder are we in" via the CR-011 walking resolution. Add an early step that:

1. Walks up from CWD, collecting `_insights.yaml` files (max depth 6, skip `.archive/`).
2. Filters entries to `confidence: rule` AND `status: active`.
3. Compiles a short "Applicable rules" preamble (one line per rule: `[type] summary`).
4. Injects the preamble into the skill's working context before the main extraction/summarisation step.

The preamble is **scoped to the active folder chain** (CWD and parents), so a rule in `meetings/management/` doesn't pollute work in `meetings/marketing/`.

**Length cap:** maximum 20 rules in the preamble; if more, prefer the most recently confirmed (top-N by `confirmation_count` then `date`). This prevents context bloat in folders with many promoted rules.

### 4. `/insights status` extended output

Add three new sections to the existing status output:

```
Confidence Lifecycle
────────────────────
  Hypotheses:  142 (top 5 near promotion: ...)
  Rules:       18 (most recent promotion: 260505)
  Recent demotions: 2 (last 30 days)
```

Helps the user see the brain learning over time.

---

## Files to Modify

| File | Action | Changes |
|------|--------|---------|
| `ecosystem.yaml` | Modify | Bump `schemas.insights` from `1` to `2`; document additive fields |
| `skills/insights/SKILL.md` | Modify | Document `confidence` field, promotion/demotion passes in `compile`, extended `status` output |
| `skills/insights/README.md` | **CREATE** | Brief user-facing guide to the lifecycle (or merge into SKILL.md if no separate README exists) |
| `skills/ops/SKILL.md` | Modify | Add "Step 0.5: Load applicable rules" prelude |
| `skills/transcript/SKILL.md` | Modify | Add same prelude; extend `_insights.yaml format` doc with new fields |
| `skills/ops-config/base.yaml` | Modify | Add `demote_on_contradiction: true` under `evolution` |
| `skills/ops-config/schema.md` | Modify | Document `demote_on_contradiction` |
| `CHANGELOG.md` | Modify | Entry under next minor version (`### Added` section) |

**No code files change.** The insights/ops/transcript skills are documentation-driven (SKILL.md tells Claude what to do at runtime). The promotion, demotion, and rule-loading logic is added as instructions in SKILL.md, consistent with the rest of core-skills.

---

## Testing Plan

### Test Case 1: backward compatibility

- Open an existing `_insights.yaml` in the Acme vault.
- Run `/insights status`.
- Expect: no errors. All existing entries reported as hypotheses (default when `confidence` is absent).

### Test Case 2: promotion at threshold

- In a sandbox vault folder, create three `_insights.yaml` entries with `type: pattern`, similar summaries (e.g., "Bob prefers concise weekly summaries"), and distinct `source.file` values across three different dates.
- Run `/insights compile`.
- Expect: one canonical entry with `confidence: rule`, `confirmation_count: 3`, `confirmations` populated; the other two marked `status: superseded`, `superseded_by: <canonical-id>`.

### Test Case 3: demotion on contradiction

- Starting from the rule in Test 2, add a `correction` entry: `summary: "Bob asked for detailed weekly summaries this week"`, with a tag overlapping the rule.
- Run `/insights compile`.
- Expect: the rule's `confidence` flips to `hypothesis`, `contradicted_by` populated with the correction's source, `confirmation_count` reduced by 1.

### Test Case 4: active loading in `/ops`

- In a folder where Test 2's rule lives, run `/ops` on a meeting transcript.
- Expect: the generated summary reflects the rule (e.g., uses concise format) without an explicit per-meeting reminder.
- Verify rule preamble appears in the skill's working context (visible in trace output / dry-run mode).

### Test Case 5: schema v1 reader compatibility

- Confirm the current `core-skills-visualisation` app loads `_insights.yaml` files containing `confidence`, `confirmation_count`, `confirmations`, `contradicted_by` without crashing.
- Expect: unknown fields ignored; existing dashboards render normally.

### Test Case 6: status output

- Run `/insights status` on a vault with mixed hypotheses and rules.
- Expect: new "Confidence Lifecycle" section showing counts, top-5 hypotheses near promotion, most recent rule promotion date, recent demotions.

### Test Case 7: scoped rule loading

- Promote a rule in `meetings/management/_insights.yaml`.
- Run `/ops` from `meetings/marketing/`.
- Expect: the management rule does NOT appear in the marketing run's preamble (out of CWD chain).

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Similarity matching for promotion is too aggressive (false promotions) | Medium | Medium | Conservative heuristic: same `type` + summary fuzzy-match + tag overlap; require all three; threshold ≥3 |
| Similarity matching is too loose for demotion (false demotions) | Medium | Medium | Require explicit `correction` type AND tag overlap AND opposing-keyword check; user can audit via `status` output |
| Rule preamble bloats `/ops` context in folders with many rules | Low | Medium | Cap at 20 rules; prefer high-confirmation, recent rules |
| Visualisation app breaks on new fields | Low | Medium | Schema bump is additive; v1 readers ignore unknown fields per YAML default |
| User dislikes the new fields cluttering YAML | Medium | Low | Fields are optional; skill writes them only when populated; existing entries left alone |
| Promotion interacts badly with `/insights propose` (which already has its own threshold) | Low | Low | Different code paths: promotion targets `confidence` field on raw insights; `propose` targets `skill_pattern` SKILL.md improvements. Document the distinction. |

---

## Rollback

1. Revert `ecosystem.yaml` schema bump.
2. Revert SKILL.md changes in `insights`, `ops`, `transcript`, `ops-config`.
3. Existing `_insights.yaml` files retain the new fields harmlessly (ignored by old logic).
4. Optionally run a one-time scrub script to strip `confidence`, `confirmation_count`, `confirmations`, `contradicted_by` from all `_insights.yaml` files — but this is not required; the fields are inert without the skill logic.

Net rollback risk: low.

---

## Success Criteria

- All seven test cases pass.
- A 30-day soak in the Acme vault produces at least 5 promoted rules and at least 1 observed demotion (sanity check that the lifecycle is exercised, not just declared).
- `/ops` output in a rule-bearing folder visibly reflects an applied rule without a per-task reminder (qualitative check).
- The visualisation app continues to render `_insights.yaml` data without changes.

---

## Open Questions

1. **Should rules expire?** A rule promoted from observations dated 12 months ago may no longer apply. Initial answer: no time-based decay; demotion only on explicit contradiction. Revisit after 30-day soak.
2. **Cross-folder rule promotion?** A pattern observed in 1× management and 2× marketing — should it promote to a vault-wide rule? Initial answer: no; promotion is per-folder. Cross-folder unification is a future CR if needed.
3. **Should `/insights propose` consume rules?** A promoted rule could be the seed for a SKILL.md change. Initial answer: leave as-is; `propose` operates on `skill_pattern`, rules are domain-knowledge not skill-knowledge. Revisit if patterns emerge.

---

## Related

- **CR-007 (insights skill creation)** — original architecture this CR extends
- **CR-010 (vault_conventions)** — the additive schema-bump pattern this CR follows
- **CR-011 (org-config move; folder-walking)** — the resolution chain reused for rule loading
