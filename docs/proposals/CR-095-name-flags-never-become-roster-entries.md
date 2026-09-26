# CR-095 — Name flags never become roster entries, so the same names are re-flagged forever

| | |
|---|---|
| **Status** | **Implemented 2026-09-26, v1.82.0** |
| **Contract** | none. Adds an output step; `people[]` schema is CR-017's and unchanged |
| **Date** | 2026-09-26 |
| **Area** | `skills/transcript/SKILL.md` (proper-noun verification, committed-spelling consistency), `skills/insights/SKILL.md` (compile output) |
| **Related** | CR-016 (proper-noun verification), CR-017 (`people[]` roster, committed-spelling consistency) |

## What was measured

A `/insights compile` run against a mature vault, 2026-09-26, clustering execution feedback by
tag family:

| Cluster | Entries | Folders | Date span |
|---|---|---|---|
| ASR / diarisation / attribution | **172** | 56 | 260605–260926 |
| **Proper-noun verification** | **98** | 40 | 260606–260924 |
| Owner inference (CR-015) | 42 | 21 | 260605–260923 |

Then the durable fix those 98 flags are supposed to produce:

```
$ grep -c "people:" <vault>/<org>/_ops.yaml
0
```

**98 flags over four months, and the roster does not exist.**

## Why this is a skill defect, not a user omission

`transcript/SKILL.md` already names the remedy, at the end of the committed-spelling section:

> Recurring flags for the same name are the signal to add it to the `people[]` roster — that is
> the durable fix, and once added this section goes quiet for that name.

The sentence is correct and it is addressed to nobody. The skill:

1. Detects the unresolved name,
2. Writes a `⚠ Namn att verifiera` note into the summary,
3. Logs an `edge_case`,
4. …and then **produces no artefact that anyone acts on.**

The note lands in a document that is read once, on the day it is written. The `edge_case` lands
in `_insights.yaml`, which no human opens. Nothing carries the same name across two runs, so
**every run re-flags the same people from scratch** — which is exactly what 98 entries across 40
folders looks like.

CR-017 built the near-miss detection that compares against *folder precedent*. It has no
mechanism to compare against *the last time this name was flagged anywhere else*, and no
mechanism to close the loop when it is.

## Proposed change

### 1. `insights/SKILL.md` — compile reports name candidates

**In section:** Pass 1 output
**Action:** Add.

> **Name-candidate roll-up.** While clustering execution feedback, collect entries tagged with
> the proper-noun family. Extract the flagged names from their `summary`/`detail`, count
> occurrences across folders, and report any name flagged **twice or more** as a roster
> candidate:
>
> ```
> Roster candidates (flagged 2+ times, not in any people[] roster):
>   "<name-a>"   4 flags   3 folders   → recurring person, no contact folder
>   "<name-b>"   3 flags   2 folders   → likely ASR variant of a domain term
>   "<name-c>"   2 flags   1 folder    → likely mishearing of a company name
> ```
>
> Names in the report come from vault data; the report is printed, never committed.
>
> The roll-up is a report, not a write. It never edits an org config — a roster entry is a claim
> about who someone is, and that claim needs a human.

### 2. `transcript/SKILL.md` — make the closing instruction actionable

**In section:** Committed-spelling consistency, final paragraph
**Action:** Replace the sentence *"Recurring flags for the same name are the signal…"* with:

> **Closing the loop is `/insights compile`'s job, not this skill's.** Log the `edge_case` and
> move on — compile's name-candidate roll-up (CR-095) is what surfaces a name flagged more than
> once, across folders, to someone who can decide whether it belongs in `people[]`. Do not
> attempt to write a roster entry from inside a transcript run: at that point only one occurrence
> is visible, and one occurrence is not evidence of a recurring person.

## Why not have `/transcript` write the roster directly

Three reasons, in order of weight:

1. **A roster entry is an identity claim.** *"<variant> is the canonical spelling of a person in
   <city>"* may be wrong in a way that then propagates silently into every future summary —
   which is the failure mode CR-016 exists to prevent. Automating it inverts the CR.
2. **One run sees one occurrence.** The recurrence that justifies the entry is only visible in
   aggregate, which is where compile already operates.
3. **Names are the one thing the pre-push guard protects.** Writing them into repo-adjacent
   config from an automated path is the wrong direction of travel.

## Verification

After the change, a compile run must list the roster candidates. The measurable outcome is on the
*next* compile after a human acts on the list: the proper-noun cluster should stop growing for
names that were added, while continuing to grow for genuinely new ones.

If the cluster keeps growing at the same rate for names already in a roster, the bug is in the
known-entity lookup, not in the reporting — and that is a different CR.

## Evidence

Observed in one mature vault: 98 proper-noun `edge_case` entries across 40 folders over four
months, with an empty `people[]` roster in the org config those folders resolve against. Names
withheld; the counts are the finding.

## Outcome (2026-09-26, v1.82.0)

Implemented as proposed: compile Pass 1 step 7 (the roll-up, report only, printed never written) with
an example in the documented output; the closing sentence in `transcript/SKILL.md` replaced.

**One addition found by running it against the measured vault:** the proper-noun family is logged in
the vault's working language. Its tags were mostly Swedish (`egennamn`, `namnverifiering`,
`namnupplösning`, `stavning`, `asr-variant`, `cr-016`), with `proper-noun` on only a handful. The
skill now names the tags in both languages; an English-only match would have found a fraction.

**Dry run at implementation:** 94 entries in the family; extracting quoted names gave 15 flagged twice
or more, in no roster. Names withheld here; the list was shown to the maintainer. It includes one
string that is the flag marker itself rather than a name, which the roll-up must skip, and at least
one known mis-transcription of the maintainer's own name — exactly the case the roster exists for.
