# CR-123 — A podcast profile, and insights schema 3: who said it, and consensus that is never a rule

| | |
|---|---|
| **Status** | **Proposed** (target **v1.90.0**, released together with CR-122 and CR-124) |
| **Contract** | additive, `contract_version` 41 → 42 (one bump for the release, shared with CR-124); `schemas.insights` 2 → 3; `schemas.ops_config` "1.4" → "1.5"; new `terms:` ids; `insight_types` gains a profile block. Meeting vaults behave exactly as before |
| **Date** | 2026-10-13 |
| **Area** | `ecosystem.yaml` (`schemas`, `terms`, `insight_types`), `ops-config` (`base.yaml` `profiles:`, schema 1.5), `transcript` (Step 3.5, summary skeleton), `ops` (`process`, index update), `insights` (compile Pass 2, `status`, new `migrate`), `promotion_candidates.py`, `tasks` (optional `kind`) |
| **Related CRs** | CR-013 (hypothesis/rule), CR-098 (distinct dates), CR-100 (`promotion_review`, shared candidate script), CR-105 (`content` is not a meeting), CR-089 (one term per concept, role keywords), CR-018 (template contracts), CR-122 (hygiene checks), CR-124 (themes) |
| **Companions** | Marvin CR-025 (readers); the core-skills landing page (What's new, both languages) |

## What happened

An archive of a recorded interview podcast (one host, a different guest nearly every episode, plus some
live and back-catalogue episodes) was processed in order through `/ops` + `/transcript` as one project,
with a shared insights corpus. Every skill assumed a meeting, and the mismatch showed in four places:

1. **The insight types collapsed.** A podcast produces claims, practices, tips and predictions. Under the
   meeting vocabulary nearly everything became `learning` or `pattern`; `decision` and `preference` were
   almost empty. The types stopped carrying information.
2. **Confirmation meant the wrong thing.** A point confirmed in three episodes reads as settled. But if the
   host raised it all three times, it is one person repeating themselves, and the host chooses the guests.
   Nothing recorded who said it.
3. **Promotion would have turned guests' claims into standing instructions.** `/transcript` Step 0.5 and
   `/ops` load `confidence: rule` as instructions for future sessions. A podcast's recurring claims are
   knowledge *about* the conversation, never instructions *to* the assistant.
4. **`Next steps` filled with announcements.** Most rows were a guest's own plans (a book, a course),
   listener calls to action, or the host's housekeeping. Only a handful became tasks. They are
   announcements, not commitments, and the action table's owner column did not fit them.

Two counting failures came out of the data as well:

- **Dates are not independent sources.** CR-098 counts `confirmation_count` from distinct dates. Back-catalogue
  episodes were re-published on one date, and live or bonus episodes share a date with the regular one.
  Counted by date, five episodes collapsed into one confirmation.
- **Confirmations grew the rationale.** Agents were told to extend `rationale` by one clause per
  confirmation. The most-confirmed insights ended with rationales of well over a thousand characters, and the
  rationale stopped being a rationale.

The vault got by with a project `CLAUDE.md` (which the skills treat as source of truth), a one-off
promotion script and a line-based migration. It works, but the generic skills do not know about it and
will drift back.

## Decisions (taken 2026-10-13)

| # | Question | Decision | Why |
|---|---|---|---|
| 1 | Name and home of the switch | A project-level **`profile:`** key; values `meeting` (default) and `podcast`. Not `content_type` | `content` is a declared term (CR-105): one-way material the vault *received*, with a sender and no participants. A podcast is the opposite: a recorded conversation with named voices, shaped like a series. Reusing the word would collide in `terms:` and in `check-terms.py` |
| 2 | One CR or several; release | Three CRs (CR-122 hygiene, CR-123 this, CR-124 themes), **all in v1.90.0** | They share one schema bump and one contract bump; splitting the release would mean two Marvin passes |
| 3 | Does `voice` generalise? | **Yes, as a generic field whose values each profile declares.** The meeting profile declares none, so meeting vaults write nothing | Avoids a schema 4 when meetings want "who raised it" later |
| 4 | `consensus` in `/insights status` | **Yes, its own count** beside hypothesis and rule | Otherwise consensus is invisible in every summary view |
| 5 | Follow-up vs task | **The profile sets the default** (podcast: tasks are the host's editorial backlog only; announcements stay in the summary). A project config may override. `/ops` does not enforce beyond CR-122's enum check | It is a judgement per project, and the default covers the observed case |

## Proposal

### 1. Profiles (`ops-config` schema 1.5, `base.yaml`)

A profile is a named bundle of defaults in `base.yaml`. A project selects one with one line and may
override any key of it:

```yaml
# project _ops.yaml
profile: podcast
```

```yaml
# base.yaml
profiles:
  meeting:                     # the default; every value equals today's behaviour
    unit: meeting              # a term id
    summary_folder: meetings/
    index_key: meetings_index
    follow_up: action_items    # Next Steps = action items with owners
    insight_types: content     # ecosystem.yaml insight_types.content
    promotable_types: [decision, preference, learning, pattern]
    promotes_to: rule
    count_by: date             # CR-098
    voices: []                 # no voice field written
  podcast:
    unit: episode
    summary_folder: episodes/
    index_key: episode_index   # accepted alias of meetings_index; same behaviour
    follow_up: announcements   # Follow-up: guest plans, next episode, host notes, listener calls to action
    insight_types: podcast     # ecosystem.yaml insight_types.podcast
    promotable_types: [claim, practice, tool_tip, prediction]
    promotes_to: consensus
    count_by: unit             # distinct summaries, not distinct dates
    voices: [host, guest, both]
    owner_voice: host          # the voice that chooses the others; never counts as independent
    consensus_threshold: 3
    task_kinds: [episode_idea, guest_lead, housekeeping, publication]
```

- Display words come from the existing `strings` / `strings_<lang>` mechanism, not new keys:
  `strings.recent_units` (*Recent meetings* / *Latest episodes*), `strings.follow_up` (*Follow-up* /
  *Uppföljning*). `next_steps` keeps its meaning for the meeting profile.
- A missing `profile:` resolves to `meeting`. An unknown profile name is a `/ops check` finding and
  resolves to `meeting`, never to a guess.
- `/ops orient` prints the resolved profile on its first line.

### 2. Terms (`ecosystem.yaml` `terms:`)

| id | en | sv | file | note |
|---|---|---|---|---|
| `profile` | profile | profil | — | the bundle of defaults a project selects; not a meeting type |
| `episode` | episode | avsnitt | `episode` | one published recording of a series the vault processes; the podcast profile's unit |
| `follow-up` | follow-up | uppföljning | — | announcements in a summary (plans, next episode, calls to action); not tasks |
| `consensus` | consensus | konsensus | — | an insight confirmed by enough independent voices; knowledge, never an instruction |

Episode summaries take the role keyword `episode` (`YYMMDD-episode-<description>.md`), **forward only**
per CR-089: existing files are not renamed.

### 3. Insight types (`ecosystem.yaml` `insight_types`)

```yaml
insight_types:
  content: [decision, preference, learning, opportunity, pattern, quote, metric]   # unchanged
  podcast: [claim, practice, tool_tip, prediction, opportunity, quote]
  evolution: [edge_case, correction, skill_pattern]                                # unchanged
```

The podcast list is declared here so it cannot silently diverge from what readers know. `tool_tip`
follows the existing underscore style (`edge_case`).

### 4. Insights schema 3 (additive)

```yaml
- id: 12
  type: claim
  voice: guest                 # profile `voices`; who raised it in the SOURCE summary
  confidence: hypothesis       # hypothesis | rule | consensus
  confirmation_count: 3        # distinct units (count_by: unit) or dates (count_by: date)
  independent_count: 3         # distinct units where a voice other than owner_voice raised it
  owner_count: 1               # distinct units where owner_voice raised it (voice owner|both)
  confirmations:
    - {source: "260103-episode-guest-topic.md", date: 260103, voice: guest, note: "same point, applied to hiring"}
  contradicted_by:
    - {source: "260410-episode-guest-topic.md", date: 260410, voice: guest}
  original_date: 251003        # optional; see section 6
```

Rules:

- **`consensus`** = `independent_count >= consensus_threshold`, `contradicted_by` empty, `type` in
  `promotable_types`, `status: active`. A point only the owner voice repeats can never reach it.
- **`consensus` is never loaded.** `/transcript` Step 0.5 and `/ops` keep loading `confidence: rule` only.
  The schema states it, and a test asserts it.
- **Old readers:** a reader that does not know `consensus` must treat it as `hypothesis`, never as `rule`.
  v2 readers ignore the new fields (as with CR-013).
- **Confirmations carry their own `note`** (one line). The writing rule changes for **every profile**:
  a confirmation never extends `rationale`.
- **Caveat, stated in the schema:** under the podcast profile the owner voice chooses the guests, so
  `consensus` means *recurring among guests*, not *generally accepted*.
- `voice` labels are assigned by a model from the summary and transcript. Where a confirmation is a
  paraphrase that cannot be placed, the writer uses `both`; owner voice is therefore likely undercounted.

### 5. Promotion (`insights` compile Pass 2, `promotion_candidates.py`)

The candidate script (CR-100: one implementation both compile and the dashboard read) gains three inputs
from the resolved profile and changes nothing when the profile is `meeting`:

- the candidate filter reads `promotable_types` instead of the `PROMOTABLE` constant;
- `count_by: unit` counts distinct `source` files; each group reports `distinct_units` beside
  `distinct_dates`, and `confirmation_count` is taken from the one the profile names;
- `promotes_to: consensus` applies the independence gate above and writes `confidence: consensus`.

`promotion_review` (CR-100) works unchanged: a person's approval or rejection of a group is recorded the
same way whatever the target.

### 6. Original date (summary skeleton, optional)

Re-published and back-catalogue material has two dates. The file name and `Published` keep the
processing or publication date per the project's naming rule; an optional metadata line
`Originally published: YYYY-MM-DD` carries the true date. Anything time-based (reading order,
confirmation order, theme counts per quarter in CR-124) uses the original date when present. The insight
copies it as `original_date`. It is an optional field of the CR-018 template contract for every profile.

### 7. Follow-up and tasks

- Under `follow_up: announcements` the summary section is **Follow-up** (`strings.follow_up`), a plain list
  without owners. `/ops process` creates **no task** from it.
- `_tasks.yaml` under the podcast profile is the host's **editorial backlog**: episode ideas, guest leads,
  housekeeping, publication steps. The tasks schema gains an optional `kind`; its legal values come from the
  profile's `task_kinds`, and CR-122's check validates it.

### 8. `/insights status` and `/insights migrate`

- `status` prints `consensus` as its own count, beside `hypothesis` and `rule`, when any exists.
- **`/insights migrate --profile podcast [--apply]`** moves an existing v2 corpus to the profile:
  type remap (judged per entry, from its wording, and shown as a table before anything is written), `voice`
  labelling, recount by unit, `rule` → `consensus` where the entry is a claim and not an instruction the
  user wrote. Dry run by default. Writes by targeted line edits that keep the file's formatting (CR-122).
  Never runs on a vault whose profile is `meeting`.

## What must stay compatible

- No behaviour change anywhere without `profile: podcast`.
- `contract_version` 42 documents every addition in one comment entry; `scripts/check-ecosystem-alignment.sh`
  stays green.
- Readers of `_insights.yaml` known today: `/transcript` Step 0.5, `/ops` rules-walk, `/insights` (compile,
  status, synthesize), `promotion_candidates.py`, Marvin (`parsers/insights.py`, `parsers/promotions.py`,
  `parsers/activity.py`, the hard-coded type list in `app.py`). Marvin already treats an unknown
  `confidence` as `hypothesis`, so it is safe on day one; what it cannot yet do is in Marvin CR-025.

## Release (v1.90.0, with CR-122 and CR-124)

1. Implement generically, with invented examples only (`docs/RELEASING.md`).
2. Private CR spec to Implemented with version and date, same session; evidence figures stay there.
3. `CHANGELOG.md` entry, `README.md` **Version**, `ecosystem.yaml` `core_skills_version: "1.90.0"`,
   `contract_version: 42` with its comment block, `schemas.insights: 3` and `schemas.ops_config: "1.5"`
   with theirs, `skills/ops-config/schema.md` to v1.5.
4. `docs/proposals/README.md` rows to Implemented; `docs/ops/ops-status.md` A and E rows.
5. `scripts/check-ecosystem-alignment.sh`, `scripts/check-terms.py`, `scripts/privacy-scan.sh`, the test suite.
6. **Companions, same day** (RELEASING "When to update the webpage and Marvin"):
   - **Marvin:** version reference and schema notes in its `CLAUDE.md`, a `docs/contract-tracking.md` entry
     for contract 42 and schema 3, and Marvin CR-025.
   - **Landing page:** rebuild from `ecosystem.yaml` (new terms and the podcast type list render from it),
     a *What's new* entry in both languages with generic wording only (*a podcast profile: episodes,
     follow-up instead of action items, guest-confirmed consensus that is never a rule; a themes registry*),
     footer version and `BUILD_VERSION`, deploy, and read back `/version.json`. Before the rebuild, check
     the landing source for pages that say *meeting* where the text now means *meeting or episode*.

## Verification (tests under `tests/test_cr123_profile.py`)

1. No `profile:` → resolved `meeting`; every resolved value equals v1.89.10 behaviour.
2. Five episodes with the same publication date, each confirming one claim from a guest voice:
   `count_by: unit` → 5, `count_by: date` → 1.
3. An insight confirmed three times by the owner voice only → never `consensus`.
4. `consensus` entries are not returned by the Step 0.5 rule loader.
5. A podcast-profile corpus: compile candidates include `claim`, exclude `quote`.
6. A v2 reader fixture given a `consensus` entry treats it as `hypothesis`.
7. `migrate` dry run prints the remap table and writes nothing; `--apply` leaves comments and `å/ä/ö` intact.
8. A Follow-up section produces no task.
