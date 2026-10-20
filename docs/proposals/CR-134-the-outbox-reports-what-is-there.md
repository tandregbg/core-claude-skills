# CR-134 — The outbox reports what is there, not what can be acted on

| | |
|---|---|
| **Status** | **Proposed** (2026-10-20); the measures and `--survey` are implemented in this commit |
| **Contract** | additive — one new report, one new finding class (motionless), measures exposed; no new fields or status forms |
| **Date** | 2026-10-20 |
| **Area** | `outbox` (`resolved.py` measures + `--survey`, SKILL.md `list`), `ops` (`check`), audit practice |
| **Related CRs** | CR-019 (`close --all-sent`), CR-032 (`Kanonisk källa`), CR-047 (absence is not evidence), CR-103 (declared status), CR-120 (aging of staged items), CR-133 (a sent item ages out) |

## What happened

A full manual pass over one vault's outbox on 2026-10-20 took it from 166 items to 92. Afterwards the
operator opened the folder and immediately found items that **had never appeared in any audit by name** —
a customer reply closed 34 days earlier, two deliveries to a partner closed 52 and 51 days earlier, and
eleven items from a single high-tempo track.

Nothing was broken. Every one of those items was correctly formed. The gap is what gets *asked*.

## Four causes, each measurable

**[E] The tool reports what it can act on.** `/outbox list` is specified to walk `_outbox/*` **excluding
`.archive/`** — 44 folders invisible by specification, 22 of them finished work filed in a shared archive
under the outbox rather than with the recipient, the oldest from 16 April. And `close --all-sent` *skips*
items that fail the gate: on this vault it would have reported "76 skipped" and closed one. A skip is
silence with a reason attached, and nobody reads it as a finding.

**[E] Every check is field-shaped; none is flow-shaped.** Missing `Kanonisk källa`, undeclared status word,
empty `Utfall`, absent manifest — all ask *is this item well formed?* None asks *has this item moved?*
CR-120 added aging for **staged** material only. So two deliveries sat perfectly formed and completely
motionless for 51 and 52 days and tripped nothing.

**[E] The measures lived in prose and were re-invented per reader.** "How many withdrawn items have no
outcome?" was answered **17, 16 and 20** on one day. Two of the three counted an empty `## Utfall` heading
as an outcome. A fourth probe and this tool's own `section()` both counted a body consisting of `---` as an
outcome, and disagreed with a fifth probe about the same item — one calling it resolved, the other waiting.

**[E] The audit was a hand-written document with the numbers baked in.** Four audit files were produced in
one day; each was stale within hours, and the only thing that made any of them usable was measuring again.
Meanwhile the same vault already runs the right pattern elsewhere: the task ledger is the truth and the
daily view is rendered from it.

## Proposal

**1. A report of the whole population.** `resolved.py --survey` walks the queue **and** `.archive/`, and
emits every item with its age, status, reply state, outcome, source field and whether it is closable —
including the items it cannot act on. `/outbox list` adopts the same scope. *A count is not a report:* it
was as the number 47 that those sent items stayed invisible.

**2. Motionless is a finding, in every state.** One threshold (30 days, CR-120's), applied to sent, draft
and ready alike. An item that is well formed and still must light up. This generalises CR-133 from `sent`
to the whole lifecycle; one uniform rule replaces a growing set of special cases.

**3. The measures are code.** `item_date`, `age_days`, `has_outcome`, `open_replies`, `is_closable`,
`survey` — one definition each, read by this tool, by `/ops check`, and by anything that reports. Two of
them encode a distinction prose kept losing: `open_replies` returns **None** when no reply was ever
expected and **0** when every expectation was met, and `is_closable` lets a written outcome outrank
unticked boxes (CR-133).

**4. The audit is generated; only the decisions are written.** `--survey --markdown` emits the situation
half. The audit file keeps the `→` rows and nothing else. A situation section written by hand is a
measurement with no owner, and it rots between the writing and the reading.

**[E] On the measured vault the survey immediately reported** 27 items closable with no decision needed,
19 motionless past the threshold, 24 without `Kanonisk källa`, 22 with undeclared status words and 4
without a manifest — across both the queue and the archive, in one listing, for the first time.

## Why this is not another check

The three CRs before it (131, 132, 133) each close a hole. This one closes the reason the holes were not
seen: **the skills describe form and valid transitions correctly, and nothing owned the question of
motion.** Form can be verified one item at a time. Motion can only be seen across the whole population,
which is the one view the tooling did not have.

## Not in scope

Watching for replies, and acting automatically. Every finding here is report-and-offer. Deciding that a
thread is over stays the operator's call.
