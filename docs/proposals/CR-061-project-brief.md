# CR-061: `/ops brief` — where a recurring project actually stands, before work resumes

| Field | Value |
|-------|-------|
| **CR Number** | CR-061 |
| **Date** | 2026-09-21 |
| **Author** | User + Claude Code |
| **Status** | **Implemented 2026-09-21** |
| **Priority** | Medium |
| **Complexity** | Low — reads files that already exist, adds no schema |
| **Estimated Scope** | `skills/ops/SKILL.md` new subcommand, new `skills/ops/project_brief.py` |
| **Related CRs** | CR-057 (carry-forward), CR-058 (retrieval), CR-054 (`external_systems`), CR-038 (`.status/current.md`), CR-019 (`/ops sweep`) |
| **Contract** | None. Consumes what CR-054, CR-057 and the manifest schema already declare |
| **Breaking Changes** | No. Read-only, writes nothing |

---

## Executive Summary

**A session opening a project cold has no way to ask where it stands.**

`/ops status` reports which *config* would load. `/ops sweep` audits closure debt across a vault. `/bod`
does exactly this job but for a **software** project — app log, running version, health check, open
CRs — none of which a coordination project has. `.status/current.md` (CR-038) is the right idea with the
wrong scope: one contact or one person, and no project has ever had one.

So orientation means opening the changelog, the newest note, the open questions, and inferring the rest.
Four files and a reconstruction, performed identically at the start of every session, with the parts
that were never written down simply lost.

`/ops brief` reports it in one read-only pass. **Everything it needs is already machine-readable** — the
gap was that nothing read it together.

## Motivation

### The reconstruction is not free, and it is not reliable

The four-file walk recovers what was written down. It does not recover **position in the loop**: whether
the next agenda exists, whether the carry-forward chain is intact, how stale the archives are, or what
is staged and unsent. Those are facts about the *machinery*, and the machinery is what a returning
session most needs and least remembers.

### Observed

On 2026-09-21 a session resumed work on a project and spent its first minutes rebuilding context from
the changelog and the newest note. It then **worked from a stale checkout of a dependency for over an
hour**, because nothing in the orientation surfaced that a declaration it depended on had landed. The
information existed; no step asked for it.

The same session later found a recap that had been written on a Friday and never sent. It had sat
unnoticed for three days because a file in a meetings folder carries no status — **the only thing that
would have shown it was an orientation step nobody ran.**

### Why not extend `/ops status`

`/ops status` answers *"what configuration applies here"*. That is a question about the vault's wiring
and it is correctly vault-wide. This is a question about one folder's **current state**, and merging
them would produce a command whose output is half irrelevant whichever question you had.

## What it reports

Six blocks. Each reads files that exist; none is inferred.

1. **Loop position** — newest note, newest agenda, whether an agenda exists for the next session. The
   common failure is not a missing note but a **missing next agenda**, which nothing else surfaces.
2. **Chain integrity** — whether the newest note ends with `## Carried forward`. This is the one failure
   in the loop that announces nothing: without the section the next agenda generates zero carried items
   and **looks perfectly correct**.
3. **What is carrying, and what is escalating** — each item with its session count, age and owner, with
   `UNOWNED` shown as the finding it is. An item nobody is named against is the one that falls through
   an agenda that lists it.
4. **Archive freshness** — newest snapshot in each declared chat and repository archive, compared to the
   last note. **A stale archive is worse than none**: retrieval still produces a block, and it reads as
   current.
5. **Staged and unsent** — `_outbox/` folders whose manifest names this project and whose status is not
   `skickad` or `arkiverad`, with their age. This is where the unsent Friday recap would have appeared.
6. **Record movement** — the changelog's most recent entry, answering *"when did anyone last write this
   project down"* rather than *"when was a file touched"*.

## What it does not do

- **Writes nothing.** No status file, no cache, no generated view. It is a report, and re-running it is
  the only way to refresh it — deliberately, because a generated orientation file is a thing that can
  itself go stale and then lie.
- **Fetches nothing.** Archive freshness is read from what an archiver already wrote. If an archive is
  stale, the honest output is to say so, not to refresh it as a side effect of asking a question.
- **Judges nothing.** It reports that four items are unowned; it does not decide who should own them.
- **No new configuration.** It reads `carry_forward` for the filename shapes and `external_systems` for
  the archives. A project with neither still gets blocks 1, 5 and 6.

## Design notes

**It is `/bod` for a coordination project**, and the parallel is deliberate. `/bod` reads operational
state before work begins and never builds; this reads project state before a session resumes and never
writes. Both exist because the expensive mistake is not doing the wrong work — it is doing the right
work against a picture that was true yesterday.

**Six blocks, not a dashboard.** Every one answers a question a returning session actually asks. The
temptation is to add counts — decisions, insights, questions — and those belong in the registers, which
a person opens when they want them. A brief that lists everything is read as carefully as a status dump.

## Verification

1. A project with `carry_forward` enabled reports its loop position, chain state and carrying items.
2. A project whose newest note lacks the section reports the chain as broken.
3. A project with `external_systems` reports archive freshness against the last note.
4. A staged item whose status is not sent appears with its age.
5. A folder with no `post_processing` block still reports blocks 1, 5 and 6 rather than failing.
