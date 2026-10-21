# CR-137 — The link check sees half the files and forgives the rest

| | |
|---|---|
| **Status** | **Implemented** (2026-10-20, 1.92.1) |
| **Contract** | No contract change. `hygiene_check.py` behaviour only; one new optional key `workflows.sweep.links.scope` (**additive** — a vault that declares nothing gets the widened default) |
| **Date** | 2026-10-20 |
| **Area** | `ops` (`hygiene_check.py` `LINKED`, `check_links`; check 11 in `/ops check`, the folder check's `links` class) |
| **Related CRs** | CR-122 (check 11 — the hygiene run over the whole scope), CR-025 (structure conformance, the other fuzzy-matching check), CR-029 (privacy scan — the class this CR borrows a finding from) |

## What happened

Check 11 exists, runs, and names link targets first. On one vault it was reporting clean while
**163 relative links in a single folder tree were broken.** Run against that tree after the links
were repaired by hand it reported 7 — the same 7 it would have reported before.

The check is not missing. **It is scoped to about half the files and forgives the rest.**

## Two causes, both measured

### 1. `LINKED` excludes most living documents

```python
LINKED = re.compile(r"^(\d{6}-.*|README|CHANGELOG)\.md$")
```

Only dated files, `README.md` and `CHANGELOG.md` are link-checked. Measured on one vault's
one organisation's `ops/` tree, 2026-10-20:

| | Files |
|---|---|
| Markdown files in scope | 238 |
| Checked by `check_links` | 111 |
| **Never checked** | **127 (53%)** |

The excluded half is not incidental. It is every **standards document** (`_standards/` entirely —
`canonical-customer-model.md`, `terminology.md`, `work-tracking.md`), every **rolling plan**
(`rolling-plan-<A>-<B>.md`, the living per-axis docs the skill set itself defines), every
domain map (`DOMAINS.md`), and every manifest. **The pattern selects the files that are born with a
date and skips the ones that are maintained** — which is backwards: a dated file is written once,
and a living document accumulates links for months.

The pattern is not wrong about dated files. It is simply from a time when those were the only files
carrying links.

### 2. The ancestor fallback forgives a wrong link

```python
if path and not any((d / path).exists() for d in (p.parent, *p.parent.parents)):
```

A target is accepted if it resolves from the file's own directory **or from any ancestor**. A link
that is wrong relative to the file it sits in passes silently whenever the same relative path happens
to resolve higher up the tree.

Measured across the files the check *does* read, whole vault, 2026-10-20: **10,698 link targets
examined, 199 resolve only via an ancestor.** Those 199 are broken links the check reports as fine.

The fallback presumably exists to be forgiving about where a document "really" sits. The cost is that
the check cannot distinguish a correct link from one that is wrong by exactly the amount the tree is
deep — which is the single most common error, because it is what a moved file produces.

## What the gap cost on one vault

163 broken links in `ops/`, accumulated over months, with **three systematic roots** each of which a
weekly run would have caught on its first appearance:

| Root | Links | What happened |
|---|---|---|
| A CHANGELOG writing links as though it lived in the folder it documents | 24 | Bare filenames and `<Person>/` prefixes, no `../../` |
| A README that did not follow its sources into a `source/` subfolder | 10 | The files moved one level down |
| Two meeting subfolders renamed | 8 | Every reference still named the old folder |

The rest were wrong depth, absolute paths, and one retired project. **All 103 with a recoverable
target were repairable mechanically** once they were visible; the work was finding them.

## Proposal

**1. Widen the default scope to every `.md` file.** `LINKED` becomes the default of a new optional
`workflows.sweep.links.scope` (`all` | `dated` | a regex). A vault that declares nothing gets `all`.
`dated` preserves today's behaviour for anyone who wants it.

**2. Resolve relative to the file's own directory only.** Remove the ancestor fallback from the
pass/fail decision — but **do not turn 199 silent links into 199 hard findings on day one**. Report
them as their own class, `resolves only from an ancestor`, with the correct path as the offered fix.
It is a different defect from a dead target and deserves a different line.

**3. Split the finding into three classes**, because they need different people:

| Class | Meaning | Who acts |
|---|---|---|
| **moved** | Exactly one file of that name exists elsewhere | Mechanical. Offer the computed relative path |
| **ambiguous** | Several candidates | Human. List them, never choose — one bare `README.md` matched 311 files in one vault |
| **dead** | No file of that name anywhere | **A content finding, not a link finding.** The document claims a source that does not exist |

The third class is the one worth the whole CR. On the measured vault 18 targets were dead, 14 of
them in board material — including a board executive summary citing six research documents, none of
which exist. A broken link is an annoyance; **a dead target means a document rests on evidence
nobody can read.** Today both are printed as one undifferentiated line, so the second hides in the
first.

**4. Report the count per folder as a trend, not an absolute.** A vault adopting this starts with a
backlog, and a check that opens with 163 findings is one the operator learns to scroll past. Print
the number and whether it rose since the previous run; alarm on the rise. The existing scoreboard
line already has the shape for it.

**5. One new finding class: a link that crosses a privacy boundary.** Observed twice on the measured
vault, both pre-existing and both invisible: a shared ops CHANGELOG linking into `.notes/board-private/`,
and a board input document **shared with a named colleague** linking to two private one-on-one
conversations with a different board member. Both were broken, so repairing them mechanically would
have *restored a leak that happened to be inoperative.*

A link from a document outside a privacy-restricted path into one is a finding whatever its state,
and its offered fix is **removal of the link, not repair** — keep the reference as text. The paths
come from the same declarations `/ops check` already reads (`.notes/board-private/`, `.handoff/`,
`.transcripts/`); no new configuration.

> This is the one place where the repair tooling was actively dangerous. Everything else in this CR
> makes a silent check louder; item 5 stops an automated fix from undoing a privacy accident.

## What this does not change

- **Report-only stays report-only.** Every fix is offered, none applied. Item 5 strengthens that: the
  one class where the obvious mechanical fix is the wrong action.
- **`.archive/`, `.transcripts/`, `.handoff/` stay out of scope as sources.** A frozen document's
  links are part of what was frozen. A link *into* `.archive/` from a living document stays valid and
  should carry an `(archived)` note, which is a convention question, not a check.
- **No contract bump.** One optional key under an existing namespace.

## Verification

Run the widened check against a vault with known debt and confirm: the count matches an independent
scan; the three classes separate; the ancestor class is reported and not mixed into dead; the
privacy class fires on a constructed case. **The measured vault above is the fixture** — 163 found,
103 mechanically repairable, 18 dead, 3 ambiguous, 2 privacy-crossing.


---

## Implementation notes (2026-10-20)

`hygiene_check.py`: `LINKED_DATED` keeps the old pattern, `_links_scope()` resolves
`workflows.sweep.links.scope` (default `all`), `check_links` resolves from the file's own folder
only and classifies through a lazily-built vault basename index -- built **only when something is
already broken**, so a clean tree costs nothing.

### Two calibrations the measured vault forced, both away from the CR as written

**1. `.transcripts/` is not sealed.** The CR named `.handoff/` and `.transcripts/` together. Run
over one vault that fired **176 privacy findings, all of them summaries naming the raw file they
were built from** -- the vault's own provenance convention, written into every meeting summary by
the skill set itself. A check that is wrong 176 times out of 176 is worse than no check. `.handoff/`
stays sealed (written once, indexed nowhere, referenced from nothing); `.transcripts/` is out.

**2. A private link is advisory unless the document leaves.** The CR said the fix is removal. Applied
literally it fired 11 times inside `ops/board/` alone, on board planning notes referencing their
author's own board-private notes -- normal practice. The distinguishing feature of the two real cases
was not the target but **whether the source is shared**, which no generic rule can read from a path.

So: a per-link finding only when the source sits in `_outbox/` (staged to leave), and otherwise
**one advisory line per run** naming the count and the top files, with the question stated plainly:
*review whether any of these are shared.* Measured: 40 links across 24 living documents, including
one meeting summary with external participants.

> **Stated plainly, because it matters more than the feature:** as implemented this class **would not
> have caught either of the two cases that motivated it** -- a shared ops CHANGELOG and a board input
> document shared with a named colleague, both linking private one-on-ones. Both were found by hand.
> The advisory line puts all 24 candidates in front of a person every run, which is the honest reach
> of a mechanical check here. **Do not read a clean privacy line as proof there is no leak.**

### Measured after implementation, same vault

| Scope | Findings | moved | dead | ancestor | ambiguous | privacy |
|---|---|---|---|---|---|---|
| one `ops/` tree (after this session's repairs) | 24 | 0 | 21 | 2 | 1 | 0 |
| the organisation above it (untouched) | 690 | 257 | 143 | 217 | 64 | 1 advisory |

The 217 ancestor findings in the wider tree are the CR's second cause, now visible for the first
time. They are reported, not failed, exactly so that this number does not block adoption.
