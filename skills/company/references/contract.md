# The company profile contract (CR-125)

The open part of Company 360: where a company's profile lives, what its files are called, what they carry,
and the rules every file follows. This file is the whole contract. It contains **no questions and no method**:
what to ask, in which order, to what standard, belongs to an optional template the skill reads from
`company.template:` (see SKILL.md). Without a template the skill works with the plain skeleton below.

## 1. Where

One folder per organisation, at the top of that organisation's area:

```
<org>/_company/
  <facet>-<vertical>.md     one file per facet (names below); <vertical> is the organisation's folder name
  sources.yaml              where the facts live and what is off-limits       (schema: docs/schemas/company-sources.schema.json)
  brands.yaml               brand architecture and web domains                (schema: docs/schemas/company-brands.schema.json)
  coverage.yaml             only with a question set attached: every required item answered, na or open (section 9)
  layers/<department>.md    optional department layers (section 6)
  exports/<target>/         derived files for other systems; regenerated, never edited
  README.md                 sources read, conflicts, gaps, confidence, when to regenerate
  AUDIT-LOG.md              reviews: what was checked, by whom, what changed, next due
  .intake/                  dropped material that exists nowhere else
```

The folder name is fixed so tools find it; every file name carries the vertical so a copy that loses its folder
still says what it is. A profile file found **outside** `_company/` is a copy and is reported.

## 2. Facets

A facet is a subject the company must be able to state. The names and one-line purposes are the contract.

| Facet | Purpose |
|---|---|
| `essence` | The core: why the company exists, where it is heading, what it stands for |
| `company` | Who and what it is: owners, roles, numbers, siblings, current focus |
| `offering` | What is sold now: status, version, price, what is decided next |
| `positioning` | Where it stands: segments, value, differentiation, competitors, what it may claim |
| `messaging` | What it says: the message framework, the words to use and avoid |
| `gtm` | How it wins: audience, journey, qualification, channels, partners, pipeline |
| `strategy` | Where it goes: direction, bets decided or draft, open questions, horizon |
| `brand` | How it sounds and looks: voice, rules, vocabulary, visual rules, images |
| `public` | Only what outsiders can already see |

**Levels** say how much must be answered, not what is asked: `public` < `basic` < `standard` < `complete`. All nine facets exist at every level; the level is the depth the profile has reached.

| Level | Meaning |
|---|---|
| public | Only what outsiders can already see |
| basic | Facts stated with a source; conflicts and gaps listed (rules 3 and 4 hold at every level) |
| standard | Every conflict resolved by the owner or by a `binding` source; numbers dated and defined |
| complete | Every required item answered or explicitly open, and a person has reviewed it |

## 3. Frontmatter (every profile file)

```yaml
vertical: acme
facet: positioning            # one of the nine, or: readme
level: standard               # public | basic | standard | complete
status: draft                 # draft | synthesis-locked | draft-locked | final | stale
generated: 2026-01-05         # when the text was written
reviewed:                     # date and who; empty until a person has read it
language: en
sources: []                   # host:path, vault:path, url:..., interview:<date>
```

H1 is `# <Display name> -- <facet>`, facet always in English. A facet leaves `draft` only when every item
required at its level is answered, marked `na`, or listed as open with a reason.

Every profile file carries the keys above except `README.md` (`vertical`, `facet: readme`, `status`, `generated`,
`reviewed`, `language`) and `AUDIT-LOG.md` (none). The H1 display name is the same in every facet file, written as
the company writes it: check the company's own naming rule (spelling, diacritics, casing) before `init --display`.

## 4. Rules

1. **Never invent.** A fact without a source is not written. An open item reads `_Not provided yet._`
2. **Every fact carries its source** (`[s1]`, resolved in the file's Sources list). Numbers carry a date and a definition.
3. **Conflicts are written out**, never resolved silently: both values, both sources, which one the text uses and why.
4. **Gaps are information.** They are listed, not filled.
5. **Decisions are made, not found.** Anything that needs a decision is marked and goes to the owner.
   A file with status `draft-locked` or `final` must list its sources.
6. **A never-say list filters every file**, not only the brand file. It lives in `messaging-<vertical>.md`
   under the heading `## Never say`: words, claims and comparisons the company has ruled out, each with its
   source. With a template, the template's list is the starting point. Without one, derive it from the
   company's own written rules, mark it `derived` and leave it for the owner to confirm.
7. **Public means already public.** The `public` facet and level use only published sources.
8. **Methodology is not profile.** What the company teaches or delivers is linked, never summarised.
9. **Proof is reconciled** against engagement records before it is used as proof. Until then a superlative, a
   certification or an award may appear only as a published claim ("the company states ..."), with its source,
   never as a fact and never as the basis of `positioning`.
10. **Privacy.** No credentials, no private one-to-one content, no judgements of named people. Name a person
    by role (owner, sign-off, contact) unless the company names them on its own public pages.
11. **Status claims are dated.** "Active" with no recent evidence is a finding; a paused business is written as paused.
12. **A fact has one home.** Other facets link to it:

    | Fact | Home |
    |---|---|
    | Owners, legal entities, headcount, revenue, number of brands or products | `company` |
    | What is sold, versions, prices, lifecycle | `offering` |
    | Segments, differentiation, competitors, claims (as claims) | `positioning` |
    | Wording, message framework, the never-say list | `messaging` |
    | Domains, hosting, brand relations | `brands.yaml` (facets cite it) |
    | What outsiders can already see | `public`, only from published sources |
    | Anything that waits for a person | the owner's decision, marked as in rule 5 |
13. **Decisions are marked the same way everywhere:** a line `**Decision needed:** <the question> (<owner role>)`
    in the facet, and the same question listed under `## Decisions` in the README. `check --summary` counts them
    per facet, together with the `_Not provided yet._` lines.
14. **A source cited by an included source** that is itself excluded (an interview behind a register) is named in
    the cited source's `note`; the excluded one stays unread.
15. **Cite the page.** A statement drawn from a paged original reads `[s-id] (p. 12)` or `(pp. 12-14)`, with
    nothing but the id inside the brackets. `check --strict` rejects a page beyond the declared `pages`.
16. **A derived statement stricter than any original** ("never", "always", "only") is not a fact. Record it as a
    dated decision with its owner, or soften it to what the original says.
17. **A curated source's own working rules** (how a tool writes, what it forbids itself) are context. They never
    enter the never-say list or the voice rules unless the company adopts them in a decision.
18. **Reviewer notes and extraction losses.** Margin notes, "to update" remarks and anything the extraction could
    not carry (images, diagrams, colours drawn as graphics, tables) are listed in the README under
    `## Reviewer notes and extraction losses`, with the page, and the facets they touch name the gap.

## 5. Machine files

`sources.yaml` and `brands.yaml` follow the two schemas in `docs/schemas/`. `unknown` is a valid value wherever a
fact is not established; `null` and omission are not. A source has `id` (`s-...`, unique), `kind`
(`vault|host|repo|url|intake|interview`), `path`, `authority`, `feeds` (facet names, each one of the nine;
empty means context only) and an optional `note`. `exclude` lists off-limits paths with a reason and optional
exceptions. Paths in `exclude` are relative to the organisation folder (the parent of `_company/`),
a trailing `/` means a folder, `*` is a glob, and a path may be declared although it does not exist yet. A source
that is a captured copy of a web page is `kind: vault` (or `repo`) with `origin_url` and `as_of` set, so a public
fact can cite the capture and still be traced to the page.

**`authority`** says how much a source weighs when sources disagree:

| Value | Meaning |
|---|---|
| `binding` | The designated source of truth: a decision, a standard, a register. It wins a conflict |
| `current` | Maintained, and read as true for what it covers. Loses to a `binding` source |
| `public` | Published by the company itself. Evidence of what it says, not proof that it is so |
| `draft` | Thinking, undecided, dated, or known to contain an error. Never wins; use it to find questions |

A document that looks ratified but carries no sign-off is `current`, not `binding`. `binding` records a decision
by the company: name who made it in `decided_by` (a role). A tool's or a consultancy's own rules are not a
decision by the company, whatever they call themselves.

**Provenance of a source.** `curation` says what kind of thing the source is: `original` (the document itself),
`derived` (extracted or summarised from one) or `curated` (a tool's or team's own processed layer). A derived or
curated source names `derived_from` (a register id or a locator). `pages` gives the page count of a paged
original and bounds the `(p. N)` citations. When a derived or curated source disagrees with its original, the
original wins, whatever authority either carries; a derived or curated source is never `binding`.

**Source references** are one chain, not three systems. `sources.yaml` is the register and its `s-` ids are the
names. In a facet text a fact is marked with the register id (`[s-site]`) or with a local number (`[s1]`) whose
entry in the file's Sources list names the register id or a locator. The frontmatter `sources:` lists the register
ids the file draws on; a locator (`vault:`, `host:`, `url:`, `interview:<date>`) is allowed where no register
entry exists yet. A `vault:` path resolves against the vault root (the folder that holds the organisation folders); in a
stand-alone organisation folder with no vault around it, against the organisation folder. `check` does not test
that a path exists.
`/company check` reports a marker nobody defines and an `s-` id the register does not declare.

**Brand `kind` and `status`.** `kind` is `company`, `product`, `personal`, `sub-brand` or `system` (an internal
grouping label that has no consumer-facing name). `status` is `live`, `beta`, `pre-launch`, `paused`, `retired`,
`planned` (announced, not yet in the system), `legacy` (still published, being phased out) or `unknown`.
`source` is provenance only; a nuance belongs in a note in the facet that cites the brand.

**`brands.yaml` is complete or `unknown`.** Every field the schema lists as required is present; where a fact is
not established the value is `unknown` (for `languages`, the string `unknown` instead of a list). Quote language
codes: an unquoted `no`, `on`, `off`, `yes` is a YAML boolean, and `/company check` says so.

**Service accounts** are declared in `<org>/_ops.yaml` under `company.services` by reference, never by value:

```yaml
company:
  services:
    ranking: {account: acme, key_ref: "env:RANKING_API_KEY"}
```

One key per payer or account, never per profile. A key **value** in any profile, `sources.yaml`, `brands.yaml`
or repository is a defect (`/company check` reports it).

## 6. Department layers

A layer adds what one function needs and states which facets it may read:

```markdown
---
vertical: acme
layer: sales
reads: [positioning, messaging, gtm, offering, brand]
owner: <role>
---
```

An agent for a department loads its layer plus the facets in `reads`, nothing else.

## 7. Exports

`exports/<target>/` holds files derived for another system. They are regenerated from the profile and never
edited. The first target is an external search-visibility tracker: the subject, the buying category, named
competitors, buying situations and a context line per market. Search data, when it exists, beats the profile.

## 8. Structure the overview needs

`export overview` (a map of how facets, sources, conflicts, decisions and open items relate, with jumps between
them) is derived from the profile and nothing else. It works on any profile, but only draws the links the
profile states. A profile that wants the whole map follows these requirements; `company_tool.py check --strict`
reports every departure (off by default, so older profiles stay clean).

1. **Conflicts are a register.** In `README.md` under `## Conflicts`, one entry per conflict, written `C<n>`
   (`C1`, `C2`, ...), as a list item or a table row whose first cell is the id. Each entry names both sides as
   `[s-id]` markers (two markers; both may name the same source when it contradicts itself, on different
   pages) and the facet(s) it touches by name, for example `Touches: company, brand.`
2. **Every local marker names a register id.** A line that defines `[s3]` in a Sources list gives the `s-` id it
   stands for, not only a path or a title. A path alone cannot be linked to the register.
3. **Decisions use the one form** `**Decision needed:** <the question> (<owner role>)`, in the facet and again
   under `## Decisions` in the README. The owner role is what the overview groups by.
4. **`feeds` matches the text.** A facet that cites a source is listed in that source's `feeds`. A source that
   feeds a facet but is never cited there is fine (context); the reverse is a defect.
5. **Id prefixes are declared.** When the text uses prefixes of its own (`Q` for the open strategy questions the
   sources number, `D` for decisions in a source's register, `F` for audit findings), `sources.yaml` carries a
   `labels:` mapping saying what each prefix means. The overview shows the label; it never guesses one.
6. **Ids.** `C<n>` and the source ids are stable. A decision or an open item may carry its own short id; without
   one the overview derives it from the wording, and the derived id changes when the wording does.

The derived `graph.json` (`schema: company-graph/0.1`) holds nodes and edges for tools. It is regenerated with the
overview and never edited. The stakeholder variant of the overview shows sources only as numbered entries, with no
paths, no excluded material, no internal cross-references and no personal names; the contributor variant shows
register ids and notes but never a path to excluded material.

## 9. Coverage of an attached question set

A question set (template) numbers its items. The profile repository holds none, so the profile records its own side:
`coverage.yaml` lists **every required item** with the id the question set gave it, its facet, and one status. The
file carries `ruleset: company-coverage/1`, the version of the rules below, so two runs are only compared when
they used the same rules.

| Status | Needs | Meaning |
|---|---|---|
| `answered` | `where` | The profile states the whole answer, with a source |
| `partial` | `where`, `remainder` | Part of it is stated; `remainder` (`open`, `decision` or `workshop`) says what the missing part needs |
| `conflict` | `where` | Sources disagree on the answer itself and the profile records both |
| `na` | `reason` | The item does not apply to this company |
| `open` | `reason`, `close_with` | Nothing stated; a fact or a document exists that can be read or handed over. `close_with: us` = material we can read or fetch; `close_with: customer` = a fact only the company holds |
| `decision` | `reason` | Nothing stated; the company has to choose, and the options are visible in the sources or the profile |
| `workshop` | `reason` | Nothing stated; the answer has to be formed by people together (an interview or a facilitated session), and no document can hold it yet |

**How to classify (apply in order, stop at the first rule that fits).** The rules exist so that two readers, or
two runs, reach the same class.

1. **Judge the profile, never the sources.** An item is classed by what the profile text states. A fact that is
   in the originals but not in the profile is a gap, not an answer.
2. **`na`** only when the item does not apply to this kind of company (a sole trader has no board). Never because
   nothing was found.
3. **`answered`** needs all of: the answer is stated in the profile; it has a source marker; a number or status
   carries its date and definition; every part the item names is covered. Candidate wording, a recommendation, a
   quoted option, or a hint is not a stated answer. A statement the company has not made its own is `partial`
   (or `decision` when only the choice is missing).
4. **`conflict`** only when the sources disagree on the answer to this very item and the profile records both. A
   conflict on a neighbouring fact does not change the class of the item: name it in `where`. When an authority
   rule (section 5) settles the disagreement and the profile uses the winner, the item is `answered`, with the
   conflict noted.
5. **`partial`** when some part of the answer is stated. Name the part still missing in the facet and give its
   `remainder`. Do not move a partly stated item into a gap class.
6. **Nothing stated.** Choose by what closing it takes:
   - The company has to choose between visible options: `decision`.
   - People have to form the answer together (a core story, a distinctive claim, priorities, pillars):
     `workshop`.
   - A fact or a document exists that can be read, fetched or handed over without anyone deciding anything:
     `open`, with `close_with: us` when the material is public or supplied, `close_with: customer` when only the
     company has it (revenue, headcount, contracts).
7. **The item's answer role breaks a tie.** `doc`, `data`, `site`: `open`. `decision`: `decision`. `owner`: an
   existing fact the owner knows is `open` with `close_with: customer`; something still to be formed is `workshop`.
8. **When two adjacent classes both fit, take the less complete one** (`answered` before `partial`, `partial`
   before a gap class) and say why in `reason`. A looser reading is not allowed to raise a class.
9. **Changing a class between runs** is recorded as `profile` (the text changed) or `reading` (the same text read
   differently). A `reading` change with the same `ruleset` is a defect in the rules or in the reader; report it.

For a gap analysis that uses other names: `GAP-SOURCE` is `open` with `close_with: us`; a fact only the
company holds is `open` with `close_with: customer`; `GAP-DECISION` is `decision`; `GAP-WORKSHOP` is `workshop`.

Nothing is left out: an item missing from `coverage.yaml` is a silent omission, and the gaps nobody wrote down
are the ones that make a profile look finished when it is not. `check` validates the file. `check --items
<file.json>` takes the required ids from the question set (a list of ids, or of `{id, required}`) and reports every
one that `coverage.yaml` lacks. A facet that has left `draft` has no `partial` items.

**Levels of the profile and of the question set.** The profile's levels are `public`, `basic`, `standard`,
`complete`. A question set may name its own; map them in `company.level_map` (profile level to the set's level,
for example `{basic: <name>}`). The skill ships no default map, so it carries no name from any question set. The
agent uses the map to decide which items are required for the profile's level and passes those ids to `--items`.
