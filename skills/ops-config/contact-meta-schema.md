# Contact Metadata Schema v1.2

## Overview

This document defines the YAML schema for `_meta.yaml` files in contact folders (`_contacts/*/`). These files provide canonical name spelling and aliases for participant resolution in transcripts and filename generation.

**v1.2 (1.99.0, contract 53)** adds two keys: `aliases_within` on a contact (CR-186), and `contact:` on a folder **outside** `_contacts/` that is about one contact (CR-185). Both are read through one module, `skills/ops-base/contact_names.py`, so every reader applies the same rules.

---

## File Location

```
_contacts/
  david-ekberg/
    _meta.yaml          <- Contact metadata
    CHANGELOG.md
    _insights.yaml
    260313-samtal-*.md
```

---

## Schema

```yaml
version: 1                      # Required: Schema version
last_updated: YYMMDD            # Optional: Last modification date

# Identity (required)
display_name: string            # Required: Canonical name for filenames/display

# Matching (optional)
aliases: [string]               # Optional: Name variations for transcript matching
aliases_within:                 # Optional (v1.2, CR-186): aliases that hold only under a path
  "<path prefix>/": [string]    #   vault-relative folder, trailing slash

# Context (optional)
company: string                 # Optional: Company/organization affiliation
role: string                    # Optional: Role/title
relationship: enum              # Optional: Relationship type
language: enum                  # Optional: Preferred document language

# Privacy (optional, CR-009)
classification: enum            # Optional: Content classification level
private: boolean                # Optional: Convenience flag (true = family or personal)
```

---

## Properties

### display_name (required)

The canonical spelling of the contact's name. Used for:
- Filename generation: `260313-samtal-David-Ekberg-topic.md`
- Document headings: "Förberedelse: David Ekberg"
- Display in visualizer and dashboards

Must use correct Swedish characters where applicable (e.g., "André" not "Andre").

### aliases (optional)

Array of name variations that should match this contact during transcript processing:
- Nicknames: "Dave", "D"
- Partial names: "David E", "Ekberg"
- Spelling variants: "David Eckberg"
- Abbreviations: "DE"

Matching is case-insensitive with Swedish character folding ("Andre" matches "André").

### aliases_within (optional, v1.2, CR-186)

An alias that holds **only under a vault path**. Use it when a bare first name means one person inside
a venture and somebody else -- or several people -- elsewhere:

```yaml
# _contacts/erik-sandberg/_meta.yaml
display_name: "Erik Sandberg"
aliases: ["Sandberg"]
aliases_within:
  "acme/": ["Erik"]
```

In a file whose vault-relative path starts with `acme/`, "Erik" is this contact. Outside it the name
means what it meant before -- if two contacts list "Erik" as a global alias it is shared, and a shared
name is nobody's. A global alias would be wrong (every "Erik" in the vault becomes him); no alias leaves
him invisible in the material where he is named most.

Rules, for a name found **in a file**:

1. **A fuller name matches as itself first** -- readers try longer names before shorter, so the other
   Erik written with his surname is still the other Erik inside `acme/`.
2. **A scoped alias wins over the name's global meaning** inside its scope -- shared or not: declaring
   the scope says that inside the path the bare name is this contact.
3. **The longest matching prefix wins** (`acme/meetings/` over `acme/`).
4. **Two contacts claiming the same name under the same prefix is a tie, and the name is nobody's** --
   never the first one found, and not a third contact's global alias either.
5. **A typed query is unchanged.** "Erik" typed by a user stays ambiguous: the scope belongs to files,
   not to questions.

### contact (optional, v1.2, CR-185) -- on a folder OUTSIDE `_contacts/`

A folder that is about one contact but is not the contact folder -- a one-to-one series kept under a
venture, as CR-182 routes it -- names that contact by its folder name:

```yaml
# acme/meetings/management/Erik/_meta.yaml
version: 1
display_name: "Erik Sandberg"
contact: erik-sandberg
classification: professional
```

- It is the identifier (the contact folder's name), never the display name.
- A call card for the folder is named after it (`_callcards/erik-sandberg.md`, CR-180), and a reader
  looking for the person behind the folder asks for `contact`, then `display_name`, then the folder name.
- It moves nothing and makes the folder no second contact folder: classification, aliases and the
  relationship stay in `_contacts/<name>/_meta.yaml`. One folder, one contact; a team meeting has none.
- Inside `_contacts/` it is ignored -- that folder **is** the contact.
- A `contact` naming no folder under `_contacts/` is reported by `/ops check` (`contacts`), never guessed.

### relationship (optional)

Categorizes the contact relationship:

| Value | Description |
|-------|-------------|
| `client` | Customer or client |
| `partner` | Business partner |
| `colleague` | Internal colleague (external org) |
| `personal` | Personal contact |
| `vendor` | Supplier or vendor |

### language (optional)

Preferred language for documents related to this contact:

| Value | Behavior |
|-------|----------|
| `swedish` | Output in Swedish |
| `english` | Output in English |
| `input` | Match input language |

When not set, follows config or project settings.

### classification (optional, CR-009)

Content classification level. Controls how this contact's data appears in shared views, analytics, and dashboards.

| Value | Description | Sharing policy |
|-------|-------------|----------------|
| `family` | Immediate or extended family | Never in any shared output. Excluded from `/analytics contacts`, org dashboards, and shared task views. |
| `personal` | Personal (non-family) contacts | Never in org dashboards. Visible in personal views only. |
| `professional` | Professional contacts (default if unset) | Visible in all views including org dashboards and analytics. |
| `confidential` | Professional but sensitive | Visible in personal views. Excluded from shared dashboards unless explicitly opted in. |

When not set, defaults to `professional`.

### private (optional, CR-009)

Convenience boolean derived from `classification`. Primarily for backward compatibility with the `_tasks.yaml` `private` field and shared-view filtering.

| Value | Equivalent classification | Effect |
|-------|--------------------------|--------|
| `true` | `family` or `personal` | Excluded from shared views |
| `false` | `professional` | Included in shared views |

When both `classification` and `private` are set, `classification` takes precedence. When only `private` is set, it maps to: `true` -> `personal`, `false` -> `professional`. When only `classification` is set, `private` is inferred (`family`/`personal` -> `true`, `professional`/`confidential` -> `false`).

---

## Folder Naming Convention (CR-009)

Contact folders follow naming patterns that encode relationship context:

| Pattern | Category | Examples |
|---------|----------|---------|
| `a1-*` | Family (first household) | `a1-alice-bob` — children via first co-parent |
| `a2*` | Family (second household) | `a2` — children via second co-parent |
| `name_organization` | Professional (venture-linked) | `erik-lindgren_techco`, `sara-holm_acmeco` |
| `first-last` | Context-dependent | Could be personal or professional — check `_meta.yaml` |
| Single name | Context-dependent | Check `_meta.yaml` for classification |

The `a1`/`a2` prefix convention designates family contacts grouped by household. The number identifies the co-parent (a1 = first, a2 = second). Children and shared family topics are filed under these prefixes.

**Important:** Folder names are stable identifiers — never rename them. Use `_meta.yaml` `display_name` for human-readable presentation and `classification` for privacy policy.

---

## Privacy Defaults (CR-009)

When `_meta.yaml` is absent or has no `classification` field, skills should apply these defaults based on folder name patterns:

| Folder pattern | Default classification |
|----------------|----------------------|
| `_contacts/a1-*` | `family` |
| `_contacts/a2*` | `family` |
| `_private/**` | `personal` |
| All other `_contacts/*` | `professional` |

These defaults are encoded in `base.yaml` under `privacy_defaults` and can be overridden per contact via `_meta.yaml`.

---

## Resolution Algorithm

When resolving a participant name (from transcript or user input):

**Priority order:**
0. **For a name found in a file (v1.2, CR-186):** a contact's `aliases_within` whose prefix the file is
   under -- after any fuller name on the same line has been matched as itself
1. Contact folder `_meta.yaml` display_name/aliases
2. Config `team[]` with aliases
3. Folder name fallback (title-case, hyphen -> space)

**Matching logic:**
1. Exact match (case-insensitive)
2. Alias match (case-insensitive)
3. Partial match (first name only)
4. Swedish character folding ("Andre" matches "André")

```
Input: "dave"
  -> Check _contacts/*/_meta.yaml for display_name/alias match
  -> Found: _contacts/david-ekberg/_meta.yaml has alias "Dave"
  -> Return: "David Ekberg"
```

---

## Examples

### Minimal

```yaml
version: 1
display_name: "David Ekberg"
```

### With Aliases

```yaml
version: 1
last_updated: 260313

display_name: "David Ekberg"
aliases:
  - "Dave"
  - "David E"
  - "DE"
```

### Full Context

```yaml
version: 1
last_updated: 260313

display_name: "Erik Sandberg"
aliases:
  - "Erik"
  - "ES"
  - "Eransen"

company: "Bravo AB"
role: "Affärsutveckling"
relationship: partner
language: swedish
```

### External Client

```yaml
version: 1
last_updated: 260310

display_name: "Raj Patel"
aliases:
  - "Raj"
  - "RP"

company: "Acme Corp"
role: "Product Manager"
relationship: client
language: english
```

### Family Contact (CR-009)

```yaml
version: 1
last_updated: 260415

display_name: "Alice & Bob"
aliases:
  - "barnen"
  - "Alice"
  - "Bob"

relationship: personal
classification: family
private: true
language: swedish
```

### Personal Contact (CR-009)

```yaml
version: 1
last_updated: 260415

display_name: "Charlie"

relationship: personal
classification: personal
private: true
language: swedish
```

---

## Skill Integration

### /transcript

When processing a transcript:
1. Extract speaker names from transcript
2. For each speaker, run resolution algorithm
3. Use resolved `display_name` in filename: `260313-samtal-David-Ekberg-topic.md`
4. Use resolved names in summary content

### /preparation

When preparing for a meeting:
0. If the meeting's folder is outside `_contacts/` and its `_meta.yaml` names a `contact:` (CR-185),
   that contact folder is the relationship's context; the folder's own dated files are the conversations
1. Match user input against `_meta.yaml` files
2. Load contact context from matching folder
3. Use `display_name` in document heading
4. If no `_meta.yaml` exists, offer to create one

### /ops

When processing meeting content:
1. Match participant names against:
   - Config `team[]` (internal team)
   - `_contacts/*/_meta.yaml` (external contacts)
2. Use canonical names in attribution
3. `/ops check` (`contacts`, CR-185) reports a folder whose `contact:` names no contact folder

### /analytics (CR-009)

When generating contact engagement reports:
1. Read `_meta.yaml` for each contact folder
2. Resolve `classification` (explicit field > `private` field > folder name pattern > `professional` default)
3. Exclude `family` and `personal` contacts from `/analytics contacts` output
4. Include all contacts in aggregate counts (overview, skills) without attribution

### Shared views (CR-009)

Any tool that renders tasks or contact content for more than one reader:
1. Resolve contact `classification` via `_meta.yaml` or folder name pattern
2. In org mode / shared views: exclude `family`, `personal`, and `confidential` contacts
3. In personal mode: show all classifications
4. Task-level `private` field continues to work independently for backward compatibility

### /insights (CR-009)

When extracting insights from family/personal contacts:
1. Insights are still extracted (knowledge is valuable in personal context)
2. The `core-skills-visualisation` app respects `classification` when rendering
3. Privacy scrubbing rules (no names in summary/rationale/tags) apply regardless of classification

---

## Backwards Compatibility

Folders without `_meta.yaml` continue to work via folder-name fallback:

```
_contacts/david-ekberg/  (no _meta.yaml)
  -> folder name: "david-ekberg"
  -> transform: replace hyphens, title-case
  -> result: "David Ekberg"
```

Skills create `_meta.yaml` opportunistically when:
- User confirms a contact name during `/preparation`
- User routes a transcript to a contact folder
- User manually creates the file

---

## See Also

- [Configuration Schema](schema.md) - Main ops-config schema with team[] structure
- [ops-base SKILL.md](../ops-base/SKILL.md) - Shared naming conventions
