# CR-164 — A conversation's type is named from one vocabulary, before the conversation, not improvised per file

| | |
|---|---|
| **Status** | **Proposed** (2026-11-02) |
| **Contract** | `ecosystem.yaml`: a new `conversation_types` list and an optional `Conversation type:` metadata line. Additive — a summary written today keeps its meaning and its shape |
| **Area** | `ecosystem.yaml` (`conversation_types`, `terms`), `ops-base` (summary metadata lines; the empty-`Beslut` marker in Template Contracts), `transcript` (Step 1), `ops` (the matching step), `preparation` (the agenda card), `analytics` |
| **Related CRs** | **CR-006** (the canonical order and the empty-decision marker this CR gives a vocabulary to), **CR-159** (declared the marker out of scope; this CR is the part it left), **CR-123** (the precedent: a profile whose types stopped carrying information got its own list), CR-124 (`Themes:`, the metadata slot this line joins) |

Marks: **[E]** observed in the corpus and measured · **[H]** not yet run.

---

## What happened

The empty-decision marker was measured across the whole live corpus on 2026-11-02, excluding
`.transcripts/`, `.archive/`, `.handoff/` and `.ephemeral/`:

| | |
|---|---|
| Files carrying `## Beslut` / `## Decisions` | **848** |
| …of those, in contact folders | **338** |
| Marker lines (the section opens with the `*(…)*` form) | **169** |
| …short and formulaic, at most 60 characters | **51** |
| …longer, carrying added prose | **118** |
| …**naming what kind of conversation it was**, in free text | **59** |

**[E]** The 59 are the finding. A sample of what the writers put inside the parentheses, with names
removed:

> *…the conversation was orienting.* · *…the conversation was social/orienting.* · *…the discussion
> was orienting and relationship-building.* · *…the afterwork was social and orienting.* · *…the
> conversation was a reflective check-in after the party.* · *…the conversation was probing.* ·
> *…an informal exchange of experience between two entrepreneurs.* · *Informal social lunch — no
> formal decisions.* · *…exploratory knowledge-sharing session.* · *…a reflective lunch conversation.*
> · *…it was a status walk.* · *…a catch-up.*

Fifty-nine summaries independently reached for the same idea — *this was not a conversation that
was going to decide anything* — and each one invented its own words for it. **[E]** The vocabulary
that recurs (*social*, *orienting*, *reflective*, *relationship-building*, *probing*, *informal*) is
a three-way distinction being rediscovered one file at a time, with no shared terms and nothing a
reader can query across.

The marker was right to exist: CR-006 made honest absence searchable, and the 169 prove the
section earns its place. What it has no field for is **which kind of conversation produced the
absence** — so the writer appends prose, or writes the bare formula and the information is lost.

## Why the contract has no expression for it

CR-159 gave the configuration language a way to say *this heading depends on content*
(`{name: Bakgrund, trigger: if_relevant}`) and then stated, in *Not in scope*: **"The action-table
and `Beslut`-marker checks."** It also fixed that `default` declares nothing optional. Both are
right, and together they leave exactly this case with nowhere to go: the marker is mandatory, its
text is free, and 59 files have used that freedom to record a classification the system does not
know it has.

CR-123 already ruled on the shape of this problem from the other side. The podcast profile got its
own `insight_types` because under the meeting list *"nearly everything became learning or pattern
and the type stopped carrying information."* The same test applied here gives the opposite answer
in one respect and the same answer in another: conversation type **is** carrying information — 59
writers thought it worth typing out — but it is **not an insight type**, and must not be added to
`insight_types`. It is a property of the unit, like `Themes:`, not a kind of thing extracted from it.

## Why a percentage is the wrong artifact

The idea that prompted this CR was a percentage split: score a transcript on the three types and
report *60 % practical, 30 % social, 10 % emotional*, the way speaker identification is reported
today.

Reject it, for three reasons:

1. **No decision hangs on it.** A distribution over a finished transcript is a chart. Nothing in the
   loop reads it, and nothing changes if the numbers move. The field proposed below is read by the
   marker, by the agenda card, and by `/analytics`; a percentage is read by nobody.
2. **It is a second classifier.** The upstream store already runs an L1 classification pass over
   every ingested source — content type, business context, classifications — on *all* sources, not
   only the ones a skill happens to process. A percentage computed in the skill would be a parallel
   classifier over the same text, with no join and no way to tell which one is authoritative when
   they disagree. See *Boundary* below.
3. **The value is forward-looking, and a transcript is backward-looking.** The literature's point is
   diagnostic in the present tense — *identify which conversation you are having* — and its named
   failure mode is answering a conversation that wants to be heard with a solution. That failure is
   avoidable at 08:20 and unfixable at 09:30. A measurement taken after the fact arrives after the
   only moment it could have helped.

## Proposal

**1. One vocabulary, declared once.** `ecosystem.yaml` gains:

```yaml
# --- Conversation types (CR-164) ---
# Named in the literature (practical / emotional / social), not invented here, so the
# three words mean the same thing in a card, a summary and an analytics view.
conversation_types:
  values:
    - practical     # what is this really about, what do we do
    - emotional     # how this feels; the speaker wants to be heard, not solved
    - social        # who we are to each other; relationship and standing
  default: practical
```

`terms` gains the Swedish and English surface words (`Konversationstyp` / `Conversation type`) so
the line is written in the target file's language like every other heading.

**2. `/preparation` states the expected type, and the mismatch.** The agenda card (CR-005) gains one
line: which of the three this conversation is expected to be, and — when the preparer's own purpose
is a different one — a single sentence naming that gap. Not a score, not a section: one line and one
warning, in the one artifact that exists before the conversation. **[H]**

**3. `/transcript` and `/ops` record the type as metadata, not as a measurement.** One line in the
slot CR-123 and CR-124 already established, directly under the H1 beside `Themes:` and
`Originally published:`:

```markdown
**Konversationstyp:** social
```

One value. Two only when the conversation demonstrably turned, written in order
(`practical → emotional`). No percentages, no confidence, no third value. Absent is valid and means
nothing was determined — the 948 dated contact documents already written stay correct as they are.

**4. The empty-decision marker reads the vocabulary instead of improvising.** The canonical marker
keeps its form and its mandatory heading; what changes is that its qualifying clause is drawn from
the declared vocabulary when a type is recorded:

| Recorded type | Marker form |
|---|---|
| `social` / `emotional` | *(Inga formella beslut — samtalet var socialt.)* — the absence is a property of the kind of conversation |
| `practical` | *(Inga formella beslut — diskussionen var orienterande.)* — unchanged, and still worth a reader's attention, because a practical conversation that decided nothing is a fact about the conversation |

A writer may still add a clause after the marker when something was agreed in passing; four markers
do that today and they are not the problem. **[E]**

**5. `/analytics` counts by type.** The one query a vocabulary unlocks and free text cannot: how a
contact's or a series' conversations distribute across the three over a year, and whether a series
that used to be social has become practical. Cheap, because the field is already written by step 3
— no new pass over any transcript.

## Boundary: no second classifier

Stated so it is not inferred, because the obvious next step is the wrong one.

- **The field is the writer's, not a classifier's.** It is set from the summary being written, by
  whoever writes it, in one line. No skill derives it by scoring text, now or later.
- **It is never joined to the upstream store's L1 classifications.** They answer a different
  question (what kind of *source* is this) on a different population (everything ingested). Two
  fields that look joinable and are not is worse than two fields that plainly are not.
- **`insight_types` is not extended.** Explicitly, with CR-123's reason: a type that applies to
  every insight in the file is a property of the file.

## What is not changed

- The canonical heading order, the five section names, the mandatory `Beslut` heading and the
  action-table contract. This CR adds a metadata line and a vocabulary for one clause.
- CR-159's optional-heading mechanism and `default` behaviour. Nothing here makes a heading
  optional; the marker stays required, which is why this is additive to CR-159 rather than a
  revision of it.
- Insights, their types, their lifecycle, and `confidence`.
- Every summary already written. The line is optional and absent on all of them.

## Verification

1. A summary written with `**Konversationstyp:** social` passes the CR-018 template-contract check
   unchanged — the line sits in the metadata block, not in the heading sequence.
2. A summary with no such line passes exactly as it does today, in a folder with a declared contract
   and in one without.
3. A value outside `conversation_types.values` is reported by `/ops check` as a hygiene finding
   (report only, in the CR-122 class), never silently accepted and never auto-corrected.
4. An agenda card for a contact whose expected type differs from the preparer's stated purpose shows
   the one-line gap; a card where they agree shows the type and no warning.
5. `/analytics` over a contact folder with mixed types returns counts per type that sum to the
   number of summaries carrying the line, and excludes those that do not — an absent line is never
   counted as `practical` by way of the default.
6. The 59 historical markers are untouched and still readable. This CR gives new files a vocabulary;
   it does not rewrite the corpus, and no migration is proposed.

## Not in scope

- **Percentages, scores, and any automatic derivation of the type.** Argued above.
- **Retrofitting the 59.** They are evidence, not a backlog. A later `/insights`-side pass could map
  them, but mapping free text to a vocabulary is a judgement per file and belongs to whoever reads
  the file, not to a migration.
- **A `conversation` profile.** The meeting profile covers contact conversations adequately — 338
  of them carry the canonical heading. Adding a profile would be a larger change than the evidence
  supports; if one is ever needed, this vocabulary is what it would declare.
- **The literature itself.** The three types and the interface argument are cited as the source of
  the vocabulary, not reproduced as method.

## Evidence

- Whole-corpus measurement, 2026-11-02: 848 files with the decision heading (338 in contact
  folders), 169 marker lines, 118 of them carrying added prose, **59 naming the kind of conversation
  in free text**, 4 recording something agreed in passing. 948 dated contact documents in total.
- The recurring vocabulary inside those 59: *social*, *orienting*, *reflective*,
  *relationship-building*, *probing*, *informal*, *status walk*, *catch-up* — eight ad-hoc words for
  a three-way distinction, none of them declared anywhere.
- CR-159's *Not in scope*, which named the marker and left it; and its fix that `default` declares
  nothing optional, which closes the other route.
- CR-123's rationale for the podcast `insight_types` list, applied here to reject an
  `insight_types` extension.

## How this was found

Raised by an external contact in a one-to-one call, as an observation about their own practice: they
had started asking which of the three conversations they were in, and noticed they habitually
answered a *heard* conversation with a *help* response. The first instinct in that call was to turn
it into a measurement — a percentage split per transcript, next to speaker identification.

The measurement above is what changed the proposal. The corpus had already answered the question
59 times in free text, which is evidence that the distinction is real **and** that the field belongs
where the writer is, not where a classifier would be. The percentage would have produced a number
nobody reads for a distinction the corpus was already making in words.
