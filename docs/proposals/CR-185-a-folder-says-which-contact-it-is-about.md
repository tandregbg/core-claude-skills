# CR-185 — `_meta.yaml` `contact:`: a folder that is not the contact folder says which contact it is about

| | |
|---|---|
| **Status** | **Proposed** (2026-11-28) |
| **Contract** | One optional key in `<folder>/_meta.yaml` for folders outside `_contacts/`; contact-meta schema v1.1 -> v1.2. Additive: a reader that ignores it reads what it read before |
| **Date** | 2026-11-28 |
| **Area** | `skills/ops-config/contact-meta-schema.md`, `ecosystem.yaml` (`<folder>/_meta.yaml` entry), CR-180's naming rule for `_callcards/` |
| **Related CRs** | **CR-180** (`_callcards/`: a card is named after the contact folder), CR-182 (a contact folder holds the relationship, not the work), CR-184 (a card is as long as its material), CR-009 (contact metadata) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E]** CR-182 says a contact folder holds the relationship and the work lives where it belongs. A
recurring one-to-one with a manager is such work: its series lives under the venture, for example
`acme/meetings/management/Erik/`, not under `_contacts/`. Nothing in the vault says that this folder is
*about* the contact `_contacts/erik-sandberg/`.

**[E]** Three things went wrong from that one missing link, on the same day:

1. **The card had the wrong name.** CR-180 names a card after the contact folder. The vault-side renderer,
   building a card from the meetings folder, could only name it after that folder -- `erik.md`, a first
   name -- while every other surface knows the person as `erik-sandberg`. A dashboard's person list, which
   matches cards to contacts by name, showed no card for him.
2. **The person could not be found.** The renderer looks the person up by the folder's name to gather
   their material across the vault. A first name is ambiguous in any vault with two people of that name,
   so the lookup returned nothing and the card was built from the meetings folder alone -- the one card of
   twenty-three without the person's wider material.
3. **A conversation was read as standing policy.** Hunting for the person's "strategy" document in that
   folder, the renderer matched a dated conversation whose title contained the word (a same-day suffix,
   `YYMMDDb-`, slipped past its date check) and fed it in as the strategy. A link would have pointed at the
   contact folder, where a strategy document actually lives.

**[E]** The renderer was fixed vault-side with exactly this key: the meetings folder's `_meta.yaml` says
`contact: erik-sandberg`; the card is now `erik-sandberg.md`, the person is looked up by that name, and the card
is built from their material across the vault. The dashboard's person list shows its card.

## The proposal

A folder **outside** `_contacts/` may declare, in its own `_meta.yaml`, the contact it is about:

```yaml
# acme/meetings/management/Erik/_meta.yaml
version: 1
display_name: "Erik Sandberg"       # optional: how the folder is shown
contact: erik-sandberg              # the contact folder's name under _contacts/
classification: professional
```

- **`contact`** -- optional, a contact folder name (the identifier, never the display name, per
  `identifier_language`). It means: *the conversations in this folder are with this person.*
- Readers that need the person behind such a folder use it before the folder's own name:
  - **`_callcards/`** (CR-180): a card is named after `contact` when the folder declares one -- which is
    what CR-180 already says ("named as the contact folder"); this gives a non-contact folder a way to
    say which one that is.
  - **Person lookup** (any reader resolving who a folder is about): `contact` first, then `display_name`,
    then the folder name.
  - **`/preparation`** (Step 2, gather context): for a meeting in such a folder, the contact folder's
    `_meta.yaml`, strategy and CHANGELOG are the relationship's context; the folder's own dated files
    are the conversations. **[H]**
- A `contact` that names no existing folder under `_contacts/` is reported by `/ops check`, never
  guessed at. **[H]**
- Inside `_contacts/` the key is meaningless (the folder *is* the contact) and ignored.

## What it does not do

- It does **not** move material. CR-182's routing stands: the one-to-one series stays under the venture,
  the contact folder holds the relationship.
- It does **not** make the folder a second contact folder. Classification, aliases and relationship stay
  in `_contacts/<name>/_meta.yaml`; the linking folder carries only what it needs to be read.
- One folder, one contact. A folder about several people (a team meeting) declares none.

## Not in this CR

**[E]** The same day showed a second gap in contact metadata: in one venture's material a bare first name
means one person -- over 1,600 bare mentions against 6 with the surname in three weeks -- while elsewhere
in the vault it is several people, so a global alias would be wrong and an absent one leaves the person
invisible. The fix used vault-side was an alias that holds only under a path
(`aliases_within: {"acme/": ["Erik"]}` in the contact's `_meta.yaml`). It belongs in the same schema,
but it is a separate decision and a separate proposal if wanted.

## Verification

When implemented: `contact-meta-schema.md` documents `contact` (v1.2) with an example; the
`<folder>/_meta.yaml` entry in `ecosystem.yaml` names it; CR-180's naming line points here; `/ops check`
reports a `contact` that names no folder. **[H]**
