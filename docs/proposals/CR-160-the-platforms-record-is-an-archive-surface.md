# CR-160 -- The platform's record is an archive surface, like any other external fetch

| | |
|---|---|
| **Status** | **Proposed 2026-10-21** |
| **Contract** | additive -- one new declared surface and its fetch record. No existing path is renamed, no writer loses a surface |
| **Date** | 2026-10-21 |
| **Area** | `ecosystem.yaml` (`vault_conventions.vault_root`, contract bump 47 -> 48), `ops` (`check`), `ops-config` schema |
| **Related CRs** | the handover CR (written 2026-10-13, never landed on this branch -- see *A numbering note* below), CR-010 (vault conventions), CR-034 (`_` and `.` prefixes), CR-036 (placement and singletons), CR-038 (generated-view isolation), CR-047 and CR-088 (the chat archive and its `_fetch.json`, the precedent this copies), CR-012 (the inbox schema), CR-071 (a missing record is reported, never omitted), CR-027 (`.knowledge/wiki/` is generated); Deep Thought DT-CR-838 (the writer), DT-CR-740 part B (the handover contract), DT-CR-675 (the note per source) |
| **Depends On** | Nothing. DT-CR-740 part B is deployed, which also unblocks the handover CR |

## Renumbered, and a numbering note

Filed on 2026-10-21 as CR-139 on a local branch. By the time it was pushed (2026-10-26) CR-139
through CR-157 had been taken upstream, so it is **CR-160**; the platform's documents that said
"CS-CR-139" mean this CR. The contract it bumps moved from 46 to 47 in the meantime (the
`external_systems.linkedin` entry), so the bump here is 47 to 48.

## A numbering note, before anything else

A CR titled *the vault follows the platform's handover* was written on 2026-10-13 and numbered
CR-121. **It is not on this branch.** It was committed to a second remote that then diverged: that
remote carries two commits this history never received, while this history went on to give CR-121
to an unrelated change and ran 77 commits further. So the handover CR exists, is referred to by
number from the platform's own documents, and that number means something else here.

This CR does not resolve that. It is noted so a reader who follows a CR-121 reference from the
platform side is not sent to the wrong document, and so the handover CR can be renumbered and
landed deliberately rather than by a merge nobody reviewed.

## What changed on the platform side

The handover CR was filed Proposed and **blocked**: it depended on the platform's handover endpoint
and contract, and neither existed. Both shipped on 2026-10-21. The contract is published, versioned
(`contract_version: 1`) and written to be implemented without reading the platform's code, and the
note-per-source route it leans on for write-back is live as well.

So the handover CR is buildable, and a second question arrives with it that it did not cover.

## Problem

The handover CR settled where a tag's **context** goes (`_context.md`, a declared generated file)
and that recording notes keep this family's own names. It said nothing about the platform's
**record** --
the structured output the platform already holds for every source it has processed: the
classification, the people with their roles and resolved identities, the organisations and projects
with their confidence and mention counts, the provenance of the extraction, the language decision,
which tags were applied by hand and which automatically, the quality verdict, and the originating
system's own metadata for a meeting (subject, organiser, start and end, participants, a link to the
recording).

That is not context and it is not a note. It is an archive of an external system's state, and this
family already has a shape for exactly that:

| Surface | Declared by | Fetch record |
|---|---|---|
| `<venture>/.teamschats/` | CR-047, CR-088 | `_fetch.json` |
| `<venture>/.githubmeta/` | declared | `_fetch.json` |
| `<venture>/.jirameta/` | declared | `_fetch.json` |

Three archivers, one pattern: a dot folder holding raw provider objects, a `_fetch.json` saying
when it was last fetched and whether that worked, and derived notes in the ordinary tree. Without a
fourth entry the platform's writer has two bad options -- invent an undeclared folder, which `check`
reports as a stray, or flatten the record into note front matter, which makes the note unreadable
and still loses the nested structure.

**It has already gone the first way.** A first writer, built before either contract was read,
produced `_index.md` (a name the platform's own contract reserves), plus `sources/`, `insights/`,
`manifest.json` and `sources.jsonl`, none of them declared here. Measured against one real account:
a source carries 153 top-level fields and that writer read about twenty; of the main extraction
block's 32 keys it rendered five; and the originating system's meeting metadata, the provenance,
the language decision, the applied-tag record, the link layer and the quality verdict appeared in
none of the files. The platform side has since been rewritten (DT-CR-838, server 2.37.261, 2026-10-24); this CR is the half that makes
the rewrite land on a declared surface instead of a second invention.

## Proposed Solution

1. **Declare `.deepthought/`** in `vault_conventions.vault_root`, worded from the `.teamschats/`
   entry because it is the same kind of thing:
   - **purpose**: the platform's own record for every source it has processed, as the platform
     holds it. A dot folder so a note tool ignores it; the derived notes belong in the normal tree.
   - **writers**: the platform's export client.
   - **readers**: user; any tool that wants the structure behind a note. Explicitly **not** read by
     the routine sweeps -- it is DORMANT in CR-034's sense (present, rarely read, safe to read on
     demand), not BLOCKED.
   - **lifecycle**: replaced per source on each run; a source removed upstream keeps its file and
     is reported, never deleted.
   - **placement**: SINGLETON at vault root. One platform account is one vault; two accounts are
     two vaults, which is the whole point of the isolation below.
2. **Declare `.deepthought/_fetch.json`** with the same field list CR-088 fixed for the other
   three (`source`, `last_attempt`, `last_success`, `result`, `detail`, `host`, `tool`), plus the
   two this fetch has that the others do not: the handover contract version the client wrote
   against, and the ETag it last saw. Same rule as CR-088's: `detail` is one line for a person and
   never a token, a signed URL or content.
3. **`check` knows both.** Neither is a stray; a missing `_fetch.json` reports as `fetch not
   recorded` (CR-071), never silently; an unknown `result` reads as an error.
4. **Write ownership stays where it is.** The platform's client writes `_inbox/` items, their
   paired audio, `.transcripts/`, `_context.md` and `.deepthought/`. It writes **nothing** under
   `_insights.yaml` or `.knowledge/`: those are `/insights`' and one is declared generated with
   hand-editing forbidden (CR-027), so a second writer there would lose work silently. The
   platform's own aggregates go inside `.deepthought/` and `/insights` may read them.
5. **The parent-directory invariant.** `vault_relative` finds the root by walking up until
   `_inbox/`, `_outbox/` or `.obsidian/` appears. A deployment that keeps several vaults side by
   side under one parent therefore depends on that parent holding none of those three names: the
   day it gains one, every vault below it merges into one and the singleton invariant is satisfied
   by the merge rather than broken by it. This is a property of the existing rule, not a new one,
   but it has never been written down as a deployment constraint and it is now load-bearing. State
   it in the `vault_relative` rule's text and have `check` report a vault whose parent carries a
   root marker.

### Out of scope

The platform side (DT-CR-838). Reading the archive back into the platform -- the handover is one
way and stays so. Any change to what `/insights` or `/transcript` produce. the handover CR's own scope,
which this does not touch.

## Files

`ecosystem.yaml` (two `vault_root` entries, the `vault_relative` rule's text, `contract_version`
47 -> 48), `skills/ops/SKILL.md` (`check`), `skills/ops-config/schema.md`, `tests/`,
`CHANGELOG.md` at release.

## Testing Plan

- A fixture vault with `.deepthought/` and a valid `_fetch.json`: `check` reports no stray and no
  finding.
- The same vault with the folder and no `_fetch.json`: `check` reports `fetch not recorded`.
- A `_fetch.json` whose `result` is a word the contract does not list: read as an error, reported.
- A `_fetch.json` carrying a token-shaped string in `detail`: the privacy test fails (the same
  assertion the other three archivers have).
- `.deepthought/` is not swept, indexed or quoted by `ops`, `insights`, `analytics`, `lint` or
  `normalize`, and is readable when a tool asks for it by name -- the DORMANT behaviour, asserted
  the way the other dot surfaces are, so a fifth surface inherits it without patching each skill.
- A fixture parent directory containing two vaults and no root marker: each vault resolves to
  itself. The same parent with an `_inbox/` added: `check` reports it, and the test asserts the
  message names the merge risk rather than printing a generic stray.
- The alignment script passes with the bumped contract version; a reader pinned to 47 ignores the
  new entries rather than failing.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A fifth dot surface and the sweeps are patched one by one again | Medium | Medium | CR-034's typed categories already exist; the test asserts the category, not the name |
| The archive is mistaken for the record and edited by hand | Low | Medium | Declared as a copy in its purpose line; a run replaces it and says so |
| Two vaults merge through a shared parent | Low | High | The invariant is written into the rule and `check` reports it |
| The platform's contract moves to v2 while a vault holds v1 files | Low | Low | The version is in `_fetch.json`; a client refuses a major it does not know |

## Open Questions

1. **Does the archive hold the platform's aggregates verbatim, or a reading of them?**
   Recommendation: verbatim, and let `/insights` decide what to make of it. A reading is a second
   opinion on a surface this family does not own.
2. **Should `check` warn when the archive is older than the newest `_inbox/` item from the same
   source?** Recommendation: yes, as a finding and not an error -- it is the same question
   `_fetch.json` answers for the other three, asked of the content rather than the fetch.
3. **Does `.deepthought/` deserve a generic name** (`.platform/`, with the source named inside)?
   Recommendation: no. The other three are named after their source for the same reason, and a
   vault that one day archives two platforms wants two folders, not one with a discriminator.
