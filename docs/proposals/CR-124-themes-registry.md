# CR-124 — A themes registry: what a series keeps coming back to, checked in three directions

| | |
|---|---|
| **Status** | **Proposed** (target **v1.90.0**, released together with CR-122 and CR-123) |
| **Contract** | additive, inside `contract_version` 42 (CR-123); a new optional per-project file `_themes.yaml`; an optional `themes` field in insights schema 3; one optional metadata line in the summary skeleton. Opt-in for **every** profile, not podcast-only |
| **Date** | 2026-10-13 |
| **Area** | `ecosystem.yaml` (`vault_conventions`), `transcript` (summary metadata, Step 3.5), `ops` (`process`, `check`), `insights` (`synthesize`) |
| **Related CRs** | CR-027 (`.knowledge/` and `INDEX.md`), CR-036 (singleton test), CR-123 (profile, schema 3, original date), CR-122 (the same report-only check pattern) |
| **Companions** | Marvin CR-025 (theme filter and theme page) |

## What happened

In the podcast archive behind CR-123, the most useful question turned out to be neither *what was said
in episode N* nor *which claims are confirmed*, but **what does this series keep coming back to, and how
has that changed**. A local themes registry answered it: a list of themes, each summary tagged with the
themes it covers, each insight with the themes it belongs to, a count per quarter and a synthesis page
per large theme.

It is not a podcast feature. A meeting series has the same shape: a topic deferred three meetings in a row
is a theme, and today nothing shows it.

Built locally, it needed repair scripts every time agents ran in sequence:

- new theme ids written into older insights without being added to the registry;
- themes added later (back-filled) missing from the older summaries' theme line;
- registry `insight_ids` and insight `themes` disagreeing in both directions.

All three are mechanically checkable.

## Decisions (taken 2026-10-13)

| Question | Decision |
|---|---|
| Ship now or later? | **In v1.90.0** with CR-122 and CR-123: one Marvin pass, one landing-page rebuild |
| Podcast-only? | **No.** Opt-in per project with `themes.enabled: true`, any profile |
| A second synthesis mechanism? | **No.** Theme pages are produced by `/insights synthesize`, written into `.knowledge/wiki/` like every other article; the registry feeds it and points at the page |

## Proposal

### 1. The registry (`<project>/_themes.yaml`)

```yaml
schema: 1
next_id: 14
themes:
  - id: T07
    name: Hiring before product-market fit
    description: When to hire the first people, and what founders regret
    aliases: [early hiring, first hires]
    status: active              # active | merged
    merged_into: null           # T## when merged
    first_seen: 2025-03-14      # original date (CR-123 section 6) where present
    last_seen: 2026-09-02
    units:
      - {source: "260103-episode-guest-topic.md", role: primary, note: "the guest's three hiring mistakes"}
    insight_ids: [12, 48, 233]
    related: [T03, T11]
    synthesis: .knowledge/wiki/themes/t07-hiring-before-product-market-fit.md
```

- Project-scoped, next to `_insights.yaml` and `_tasks.yaml`. Not a singleton: by the CR-036 test a second,
  folder-scoped registry does not defeat its purpose, because themes belong to a series.
- `units` is the profile's unit (meeting or episode); the key is generic for that reason.
- **Privacy:** no personal or company names in any theme field, the same rule as insights.

### 2. Tagging (`/transcript`, `/ops process`)

- Each summary carries one metadata line: `Themes: T07 (primary), T03, T11`. Two to six themes, at most two
  primary.
- Each new insight carries `themes: [T##]` (insights schema 3, optional).
- **Reuse before create.** A new theme is created only when no active theme or alias fits, and it should
  plausibly recur in three or more units. Guidance: 20 to 50 themes for about 70 units. Breadth is handled by
  phases in the synthesis page, not by splitting a broad theme.
- Every write that adds a theme to a summary or an insight updates the registry **in the same step**, by
  targeted edit (CR-122).

### 3. Consistency checks (`/ops check`, report only)

1. **Three-way:** registry `units[]` ↔ the summary's `Themes:` line ↔ the themes of insights from that
   summary. Each disagreement is one line, naming which side lacks what.
2. **Two-way:** insight `themes` ↔ registry `insight_ids`.
3. A theme id used anywhere and absent from the registry; a `merged` theme still used by a new write;
   a `synthesis` path that does not exist.

### 4. Time and synthesis (`/insights synthesize --themes <project>`)

- A generated count per theme per quarter, by **original** date, written as a table at the top of the
  theme page (never stored in the registry, which holds facts, not views).
- One page per theme with enough units (default 5): core messages, where voices disagree, phases over time,
  who raises it (by voice, CR-123, never by name), gaps, and a unit table. Written to
  `.knowledge/wiki/themes/` and listed in `.knowledge/INDEX.md`, so it is reached the way every other article is.
- Pages are drafts by nature. The page says what it was built from (units, insights, date of build).

## What this does not do

- No theme is created or merged by a check. Merges are a person's decision, recorded with `merged_into`.
- No change for a project without `themes.enabled`.
- It does not tag existing summaries by itself. A back-fill is an explicit `/ops process --themes-backfill`
  run that proposes tags per summary and writes after confirmation.

## Verification (tests under `tests/test_cr124_themes.py`)

1. An insight tagged `T09` with no registry entry → one finding.
2. A registry unit with no matching `Themes:` line in the summary → one finding naming the summary.
3. Registry `insight_ids` missing an insight that lists the theme → one finding; the reverse too.
4. A summary line with three primary themes → one finding.
5. Quarter counts use `Originally published` when present: a back-catalogue unit lands in its original quarter.
6. A project without `themes.enabled` → no theme checks run, output unchanged.
