# CR-186 — `_meta.yaml` `aliases_within`: an alias that holds only under a path

| | |
|---|---|
| **Status** | **Proposed** (2026-11-28) |
| **Contract** | One optional key in a contact's `_meta.yaml`; contact-meta schema v1.2 (with CR-185) or v1.3. Additive: a reader that ignores it reads what it read before |
| **Date** | 2026-11-28 |
| **Area** | `skills/ops-config/contact-meta-schema.md` (`aliases_within`, Resolution Algorithm), readers that resolve participant names (`/transcript`, `/preparation`) |
| **Related CRs** | CR-009 (contact metadata), CR-185 (a folder says which contact it is about), CR-180 (`_callcards/`) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E]** In one venture's material a bare first name means one person. Measured over three weeks of that
venture's dated files: the bare name **1,694 times in 215 files**, the same person with surname **6
times**, nobody else of that first name with a surname **at all**. People in a team write the first name.

**[E]** Elsewhere in the vault the same first name is several other people -- a friend, a board contact.
Two of the contacts already list the bare first name as an alias.

**[E]** That leaves contact metadata two options today, and both are wrong:

- **A global alias** (`aliases: ["Erik"]` on `_contacts/erik-sandberg`): every bare "Erik" in the vault
  becomes him -- including the friend's.
- **No alias**: the bare name is shared, so a reader that counts or resolves by alias rightly attributes
  it to nobody -- and the person who is named sixteen hundred times in three weeks is invisible. A tool
  that gathered where a person occurs found **zero** mentions for him.

**[E]** The fix used vault-side, with a mention index and a preparation tool reading it: the contact's
`_meta.yaml` says the alias holds under one path.

```yaml
# _contacts/erik-sandberg/_meta.yaml
display_name: "Erik Sandberg"
aliases:
  - "Sandberg"
aliases_within:
  "acme/":
    - "Erik"
```

**[E]** After: the person went from 0 to over 25,000 mentions, nearly all under the venture; excerpts
around his name were found in every one of his files instead of a fifth of them; the other contacts with
that first name gained nothing from the venture and kept what they had elsewhere.

## The proposal

Add an optional key to the contact metadata schema:

```yaml
aliases_within:                  # Optional (v1.2/1.3): aliases that hold only under a path
  "<path prefix>/":              # vault-relative folder, trailing slash
    - "<name>"
```

**Meaning:** in a file whose vault-relative path starts with the prefix, a match of the name is this
contact. Outside the prefix the name means what it meant before -- typically shared, and so nobody's.

**Rules** -- each was needed in the vault-side implementation:

1. **A scoped alias wins over a shared name inside its scope.** That is the point of it.
2. **The longest matching prefix wins** (`acme/meetings/` over `acme/`).
3. **Two contacts claiming the same name under the same prefix is a tie, and the name is nobody's** --
   never the first one found.
4. **A fuller name still matches as itself first.** Inside `acme/`, the other Erik written with his
   surname is still `_contacts/erik-lindgren`, not the scoped "Erik"; readers try longer names first.
5. **Resolving a typed query is unchanged.** "Erik" typed by a user stays ambiguous -- the scope belongs
   to files, not to questions. A query with the surname, or the folder name, resolves as before.

**In the Resolution Algorithm** (contact-meta-schema), the priority list gains one step before alias
match: *if the name being resolved comes from a file, a scoped alias whose prefix the file is under*.
`/transcript` resolving a participant in a transcript filed under the venture gets the scoped contact;
`/preparation` gathering a person's material across the vault counts the scoped mentions. **[H]** for
both skills: only the vault-side tools implement it today.

## What it does not do

- It does not rename, move or rewrite anything already written.
- It does not touch `aliases`: a global alias keeps meaning everywhere.
- It does not infer a scope. The scope is declared by the user in the contact's metadata, where it can
  be read and corrected.

## Not in this CR

CR-185 (`contact:` on a folder outside `_contacts/`) solves the neighbouring problem -- which contact a
*folder* is about. This one is about which contact a *name* means; the two were found the same day and
are independent.

## Verification

When implemented: `contact-meta-schema.md` documents `aliases_within` with the five rules and the
example; the Resolution Algorithm lists the scoped step; a test fixture with two contacts sharing a first
name, one scoped to a venture, shows the venture's bare mentions resolve to the scoped contact, the rest
stay shared, a fuller name wins, and a same-prefix tie resolves to nobody. **[H]**
