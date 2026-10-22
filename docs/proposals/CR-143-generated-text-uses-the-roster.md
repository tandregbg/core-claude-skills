# CR-143 — Generated text uses the roster's names and pronouns, and a lint checks it

| | |
|---|---|
| **Status** | **Implemented v1.92.5** (2026-10-22) |
| **Contract** | additive — a roster field (`pronouns`) and a lint over generated and staged text |
| **Date** | 2026-10-21 |
| **Area** | `ops` (`lint`, SKILL.md writing rules), `ops-config` (`people:` roster), `outbox` (staging) |
| **Related CRs** | CR-017 (ASR variants in the roster), CR-102 (manifests edited in place) |

## What happened

A team member's name is also a common female name when shortened, and the member is male. The roster carries
the full name, aliases, and a note. **The assistant wrote the short form and the wrong pronoun in two
separate drafts**, once in each of two sessions, after the roster and the assistant's own notes had both
said otherwise. The person had corrected this in a meeting weeks earlier. The same roster maps a spoken
first name to a different person (an alias), which the assistant handled correctly only because it read the
file that day.

**[E]** Two wrong-pronoun incidents in about ten days, both caught by the operator, none by a check. This is
the regression-test-is-the-operator failure CR-138 describes.

## Proposal

1. **A `pronouns:` field in the roster entry** (`he`, `she`, `they`) and a `canonical_short:` form the
   notes must use when the short name is ambiguous.
2. **A lint over generated and staged text** (agenda, post, recap, daily note, manifest bodies): a line that
   names a person and then uses a pronoun in a different form fails the check, and the ambiguous short form
   is reported with the canonical one.
3. **Unlisted people default to `they`**, never inferred from a name.
4. **The lint runs at staging**, so a draft with the problem never reaches the outbox.

## Not in scope

Rewriting sent material. A sent package is never edited.

## Acceptance

- A draft using the ambiguous short form or a wrong pronoun fails staging with the line shown.
- A roster entry without `pronouns` produces `they`-neutral text.
