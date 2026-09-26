# CR-099 — Backlog detection counts correct structure as debt

| | |
|---|---|
| **Status** | **Proposed 2026-09-26** |
| **Contract** | none. Changes detection filters and adds one convention (`_manifest.md` as a processed marker) |
| **Date** | 2026-09-26 |
| **Area** | `skills/analytics/SKILL.md` `backlog` steps 2, 3 and 5 |
| **Note** | Written as CR-097 and renumbered to 099: CR-097 was taken the same evening by *analytics snapshots live in `.analytics/`*, written in a parallel session |

## What was measured

`/analytics backlog` run against a mature vault, 2026-09-26:

| Step | Flags raised | True findings | False-positive rate |
|---|---|---|---|
| 3 — directories without `CHANGELOG.md` | **241** | **19** | **92 %** |
| 2 — `.txt` with YYMMDD prefix | 342 | ~7–13 | **~97 %** |
| 5 — `CHANGELOG` without `_insights.yaml` | 77 | not assessed | unknown |

Breakdown of the 241 in step 3:

| Cause | Count |
|---|---|
| `CHANGELOG.md` exists **in an ancestor directory** | **170** |
| Directory contains a `_manifest.md` (declared folder index) | 67 |
| Dot-prefixed somewhere in the path (`.audio`, `.linkedin`, …) | 9 |
| **Genuine** — no ancestor CHANGELOG, no manifest, not dotted | **19** |

The report is not slightly noisy. **It is wrong nine times out of ten**, and a reader who trusts
the headline number is told the vault has 241 structural gaps when it has 19.

## Why each filter is missing

### Step 3 — ancestor CHANGELOG (170 of 241)

A project keeps **one** `CHANGELOG.md` at project root and dates its files in subdirectories:

```
<org>/_projects/<project>/CHANGELOG.md        <- the index
<org>/_projects/<project>/meetings/*.md       <- 400 dated files, flagged
<org>/_projects/<project>/audits/*.md         <- 112 dated files, flagged
```

That is the documented structure, and the check flags both subdirectories for lacking something
their parent is supposed to hold. The two largest "findings" in the report are a correctly
structured project.

### Step 3 — declared folder index (67 of 241)

`_manifest.md` is this vault family's convention for *"this folder is a deliberate set, here is
what it contains"* — and the ecosystem's own naming rule names it as the exception to the
`YYMMDD-` prefix requirement. A directory that carries one has an owner who described it. The
check does not look.

### Step 2 — `.txt` + date prefix means nothing on its own

The rule is *"`.txt` files with a YYMMDD prefix are likely raw transcriptions that haven't been
processed"*. Extension plus date cannot distinguish:

- a raw transcript awaiting `/transcript` — **a real finding**
- raw material already processed, kept deliberately, whose summaries live one level up — **not a finding**

In the measured vault, one directory of 124 archived `.txt` files from 2022–2025 accounted for
**36 % of the step-2 total**. Its summaries exist, indexed in the parent's CHANGELOG. It was
flagged purely on filename shape.

### Step 5 — same ancestor blindness

77 folders have a `CHANGELOG.md` but no `_insights.yaml`. Insights accumulate per folder by
design, so many of those are correct — but the step applies no ancestor check and no
declared-intent check, so the number cannot be acted on either way.

## Proposed change

**In section:** `backlog`, step 2
**Action:** Replace the detection rule.

> 2. **Detect unprocessed transcriptions:**
>    - Find `.txt` files with YYMMDD prefix
>    - **Exclude** a file when any of these holds, and say which in the report:
>      - its directory contains a `_manifest.md` (the folder's intent is declared)
>      - a sibling `.md` file shares its date prefix (the summary exists)
>      - its directory name marks it as archived (`arkiv`, `archive`, `raw`, `källmaterial`)
>      - the newest file in the directory is older than 12 months (dormant, not queued)
>    - Report survivors as the queue, and report the exclusion counts separately so the
>      suppression is auditable rather than invisible

**In section:** `backlog`, step 3
**Action:** Replace the detection rule.

> 3. **Detect orphaned content:**
>    - Find directories with 2+ YYMMDD-prefixed files and no `CHANGELOG.md`
>    - **Exclude** when:
>      - any ancestor directory up to 4 levels holds a `CHANGELOG.md` — a project indexes at its
>        root, not per subdirectory
>      - the directory holds a `_manifest.md`
>      - any path component is dot-prefixed — those are raw-material surfaces by convention
>    - Report survivors, and print the exclusion counts by cause

**In section:** `backlog`, step 5
**Action:** Add the same ancestor and manifest exclusions, and require 2+ transcript files rather
than 1+ before a folder is reported.

**Also:** the summary table must print **flags raised** and **after exclusions** side by side. A
single number that has been silently filtered is as misleading as an unfiltered one.

## Why `_manifest.md` and not a new marker

A new field (`processed: true`, a `.nobacklog` file) would work and is worse: it invents a
convention only this subcommand reads, which is the kind of single-purpose marker that rots. The
vault family already has a way to say *"this folder is a deliberate set"* and already treats
`_manifest.md` as a structural exception. **Reuse beats invention**, and a folder worth excluding
is a folder worth describing anyway.

## What this does not fix

Excluding a directory because an ancestor holds a `CHANGELOG.md` assumes the ancestor's index
actually covers the subdirectory. It usually does, and verifying it would mean parsing the
CHANGELOG for links to each file — expensive, and a separate concern. **The 4-level ancestor walk
is a heuristic that trades a small number of misses for removing 170 false positives.** Stated
here so the tradeoff is visible rather than assumed.

## Verification

Re-run against the same vault. Step 3 should report ~19 directories rather than 241, with the
exclusion table accounting for the remaining 222. Then inspect five of the 19 by hand: if any is
also correct structure, the filters need one more case before the number can be trusted.

## Evidence

One mature vault, 4 002 dated files, 241 step-3 flags of which 19 survive the proposed filters.
Directory names withheld; the causes and counts are the finding.
