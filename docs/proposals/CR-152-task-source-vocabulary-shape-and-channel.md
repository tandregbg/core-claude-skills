# CR-152 — The ledger's source vocabulary: declare it, and separate shape from channel

| | |
|---|---|
| **Status** | **Implemented v1.95.0** (2026-11-05), contract 49 |
| **Contract** | `contract_version` to the next free number -- 48 → **49** as of 1.94.0 (47 went to `external_systems.linkedin`, 48 to CR-169/170/171) (**additive**): two enums move into `ecosystem.yaml`, `scope` gains one value, the task schema gains one optional field, and an alias map is declared. Every existing ledger stays readable and nothing is rewritten |
| **Date** | 2026-10-21 |
| **Area** | `ecosystem.yaml` (`task_source_types`, `task_scopes`, `task_source_aliases`), `tasks` (v2 schema + writers), `ops` (`hygiene_check.py`, `check`) |
| **Related CRs** | **CR-048** (the status enum was moved into the contract for exactly this reason), CR-080 (`correspondence` as a source type), CR-105 (`content`: incoming material is not a meeting), CR-122 (the enum check that surfaced this), CR-127 (`closed:`, and the precedent for reading a legacy field without migrating), CR-135 (the object-model fields beside these), CR-120 (a check that cries wolf is one an operator learns to ignore) |

## What happened

`/ops check` reports every `source.type` outside its enum. Run across one vault it reports **281
rows over 26 ledgers in 22 distinct words** — a wall nobody can act on, which under CR-120's own rule
is a check that has stopped working. The wall is not the defect. It is the symptom.

Measured, 2026-10-21, 93 ledgers and 2,047 task rows:

| Declared | Rows | | Undeclared | Rows |
|---|---|---|---|---|
| `meeting` | 1,893 | | `email` | 92 |
| `imported` | 288 | | `chat` | 58 |
| `manual` | 37 | | `analysis` | 25 |
| `correspondence` | **6** | | `reference` | 15 |
| `content` | 3 | | `mail` | 13 |
| `decision` | 1 | | `async` | 10 |
| | | | `document` 9 · `note` 8 · `external` 4 · `file` 3 · `agreement` 3 · `sms` 2 | 29 |
| | | | ten more words, one or two rows each | 12 |

**`email` plus `mail` is 105 rows. The declared word for the same material, `correspondence`, has 6.**
A declared word that loses to an undeclared one by 105 to 6 is not a discipline problem. It is a
vocabulary that does not fit what people actually record.

### Two diagnoses, and both are mechanical

**1. The enum classifies by shape; the writers classify by channel.** `meeting`, `decision`,
`manual`, `imported`, `content`, `correspondence` are *kinds of thing* — one-way material, a two-way
thread, a decision, something imported. But a person filing a task knows the **channel** it arrived
through before they know its shape, so they write `email`, `chat`, `sms`, `voice-memo`. Those are not
wrong answers to the question; they are right answers to a different question, and the field only asks
one.

**2. This enum was never declared in the contract.** `SOURCE_TYPES` and `SCOPES` are tuples inside
`hygiene_check.py`. The status enum used to be the same, and CR-048 moved it into `ecosystem.yaml` with
a rationale that reads as a prediction of this CR:

> Declared here because it was not, and three other dialects grew in its absence.

Three dialects grew in the status field's absence. **Twenty-two grew in the neighbouring field, which
was left where it was.**

### And `scope` has a real hole

`scope` is declared `root | org | project | personal`. Found in the wild: **`contact` (6 ledgers)**,
`management` (2), `domain` (1). The six are task ledgers inside contact folders — a shape the vault has
had since the beginning, with **no correct value to write**. That is not drift; that is a missing word.

## Whole-vault evidence, 2026-11-04

The figures above were taken on **one large venture**. The vault-wide audit of 2026-11-04 ran the
same check over every ledger and the shape held, wider than it looked:

**[E] 20 distinct undeclared `source.type` values across the vault**, against an enum of six
(`meeting`, `decision`, `manual`, `imported`, plus the declared `content` and `correspondence`):

| Value | Ledgers |
|---|---|
| `email` | **14** |
| `reference` | 6 |
| `analysis` | 4 |
| `document` | 3 |
| `mail`, `note`, `outbox`, `async` | 2 each |
| `agreement`, `audit`, `chat`, `conversation`, `cr`, `external`, `file`, `leverans`, `message`, `observation`, `preparation`, `sms` | 1 each |

**Three readings the distribution supports, which a single venture could not:**

1. **`email` is not an edge case.** Fourteen ledgers is the whole long tail put together, and
   `mail` is the same value spelled differently in two more — which is what the alias map in the
   proposal is for.
2. **The tail is not noise either.** `agreement`, `cr`, `leverans` and `audit` each name a real
   origin a task can have; they are vocabulary the vault grew because the enum had no word. An
   enum that forces eighteen of these into `manual` loses exactly the thing `source.type` exists
   to record.
3. **One-ledger values are where the channel key earns its place.** A value used once is a local
   convention, and the proposal's split — a small contract enum plus a free `channel` — is what
   keeps the contract short without flattening the long tail into `manual`.

Also found, same run: **`status: waiting` on 4 tasks** in one customer ledger (against the CR-048
enum) and **`scope: management`** in one project ledger (against `root|org|project|personal`). Both
are the same failure in the two other enums this CR does not touch; whether they join it or stay
reported is a decision for implementation.

## Proposal

### 1. Both enums move into `ecosystem.yaml`, and the checker reads them

```yaml
task_source_types:                 # the SHAPE of the thing the task came from
  - meeting
  - decision
  - manual
  - imported
  - content                        # one-way material (CR-105)
  - correspondence                 # a two-way thread (CR-080)
task_scopes:
  - root
  - org
  - project
  - personal
  - contact                        # NEW: a ledger in a contact folder
```

No new shapes are invented here. The point of the move is that the vocabulary becomes a contract a
reader can check against and a writer can look up — which is the whole of CR-048, applied to the field
it was not applied to.

### 2. The channel gets its own optional field

```yaml
    source:
      type: correspondence         # the shape -- from the declared enum
      channel: email               # NEW, optional: how it arrived
      file: "meetings/261019-summary.md"
```

`channel` is free text with a declared starter set (`email`, `chat`, `sms`, `teams`, `voice-memo`,
`file`, `call`) and no checker finding of its own. **It is deliberately not an enum**: channels are
whatever the world does next, and the half of this problem that comes from a closed list should not be
reproduced in the new field. The shape stays closed; the channel stays open.

### 3. The legacy words are read through a declared alias map, and never rewritten

```yaml
task_source_aliases:               # legacy word -> {type, channel}; read, never written
  email:        {type: correspondence, channel: email}
  mail:         {type: correspondence, channel: email}
  chat:         {type: correspondence, channel: chat}
  teams-chat:   {type: correspondence, channel: chat}
  message:      {type: correspondence, channel: chat}
  sms:          {type: correspondence, channel: sms}
  voice-memo:   {type: manual,         channel: voice-memo}
  document:     {type: content}
  file:         {type: content,        channel: file}
  note:         {type: manual}
  reference:    {type: content}
  written_input: {type: content}
  domain_sheet: {type: content,        channel: file}
  external:     {type: imported}
  outbox:       {type: manual}
  cr:           {type: decision}
  agreement:    {type: decision}
  conversation: {type: meeting}
  preparation:  {type: meeting}
  personal_ledger: {type: imported}
```

**No migration.** CR-127 settled the precedent one field over: a legacy spelling is read and never
written, because a backfilled guess is worse than a gap and a mass rewrite of 281 rows is the re-dump
CR-122 forbade. New writes use the canonical pair; the old rows stay readable and stop being reported.

### 4. The check gets quieter and sharper

| Today | After |
|---|---|
| 281 findings, one per row, 22 words | A finding **only** for a word that is neither canonical nor aliased |
| An aliased word looks identical to a typo | Aliased words counted **once per ledger** as an advisory line, never per row |
| `scope: contact` is a finding | A declared value |

A finding that survives this is a genuinely new word, which is the thing worth a person's attention —
either it earns a row in the alias map or it is a typo, and both are one-line answers.

## Open questions

1. **`analysis` (25 rows) and `async` (10) may be shapes the vocabulary genuinely lacks**, not channels
   and not aliases. `analysis` is a task the owner raised from their own reading of data — close to
   `manual` but with a provenance `manual` does not carry. `async` is a written pre-meeting update,
   which is neither the meeting nor a thread. Both are left **out of the alias map above** on purpose:
   mapping a shape to the nearest word is how the nearest word loses its meaning. Proposed as candidate
   enum values, to be decided with the numbers in front of whoever decides.
2. **`management` and `domain` as scopes** (3 rows) look like a different axis again — a domain is not a
   scope of ownership. Probably aliases to `org`, but worth one look at the two ledgers before deciding.

## What this is not

- **Not a migration.** Not one of the 2,047 rows is rewritten by this CR.
- **Not a per-vault extension.** A vault that may add its own source types is a vault where the
  twenty-third word appears next month. The enum is the contract's; the **channel** is where local
  reality goes.
- **Not a channel taxonomy for anything else.** `source.channel` on a task row says how that task's
  source arrived. The outbox's `channel:` field is a different thing in a different artefact and is not
  touched.

## Files touched

| File | Change |
|---|---|
| `ecosystem.yaml` | `task_source_types`, `task_scopes` (+ `contact`), `task_source_aliases`, `contract_version` → the next free number |
| `skills/tasks/SKILL.md` | `source.channel` in the v2 schema; the writing rule; the alias map named as read-only |
| `skills/ops/hygiene_check.py` | Read both enums and the alias map from the contract; per-ledger advisory instead of per-row findings |
| `skills/ops/SKILL.md` | The `tasks` check's description, under `check <folder>` and the vault sweep |
| `CHANGELOG.md` · `docs/proposals/README.md` | Release entry and the index row moved on implementation (CR-020) |

## As implemented (v1.95.0), including both open questions

**Open question 1 is settled by looking at the rows.** `analysis` **is** a shape the vocabulary
lacked and is now declared: 22 rows over four ledgers, and read together they are one thing -- work
the owner raised from their own reading of their own material (company books, a dataset, a draft,
an SEO audit). `manual` does not carry that provenance and `content` is material someone else sent.

**`async` is not**, and is deliberately in neither list. Row by row it is a written pre-meeting
update, a self-raised infrastructure task and three items lifted from a spreadsheet: it is defined
by what it is *not* -- it did not come from a meeting. Mapping it to the nearest word is how the
nearest word loses its meaning, so it stays a finding. Two ledgers, two advisory-sized questions
for a person, which is the right outcome rather than a residue.

**Open question 2, likewise.** `domain` is a meetings folder and `management` two per-person 1-on-1
folders, all three inside an organisation and none of them a project, a person or a contact. Both
are aliased to `org` through a new `task_scope_aliases` -- the same read-never-write mechanism as
the source aliases, which the CR declared for one field and not the other.

**Three aliases beyond the proposed map**, each a word the whole-vault scan found: `observation` and
`audit` resolve to `analysis` (they are the same shape), `leverans` to `decision`.

### Measured effect on the vault that produced the CR

| | Before | After |
|---|---|---|
| `tasks` findings | 85 | **60** |
| of which per-ledger legacy advisories | 0 | 27 |
| genuine `source.type` findings | 20 distinct words, per row | **2** (both `async`) |
| `scope` findings | 3 hard | 3 advisory, 0 hard |

**Two CR-122 tests were re-derived rather than loosened.** One asserted the old per-row wording for
`email`; it now asserts the advisory and still asserts the thing it was written for -- one line for
eight rows. The other counted four findings on a fixture whose fourth was `analysis`, which is a
declared word now, so it asserts three and that `analysis` produces nothing. 18 new tests.
