# CR-171 — A vault's file names are data to the suite

| | |
|---|---|
| **Status** | **Implemented v1.94.0** (2026-11-03), contract 48 |
| **Contract** | additive — the grandfather clause gains its test; the leaked literals move to settings |
| **Date** | 2026-11-03 |
| **Area** | `ecosystem.yaml` (`system_file_language`, `identifier_language`, `vault_conventions`), `inbox` (`survey.py`, SKILL.md), `tests/test_cr138_survey_contract.py` |
| **Related CRs** | CR-049 (`identifier_language`), CR-035 (the working-document view), CR-022, CR-089, CR-138, CR-162 |

## What happened

`system_file_language` says system and structure files carry English names, and then grandfathers five
Swedish ones **by enumeration**:

> *"Applies going FORWARD — the derived registers with Swedish names (`_INDEX-agare.md`,
> `_INDEX-koppling.md`, `_INDEX-maskiner.md`, `_INDEX-objektmodell.md`, `_INDEX-verksamheter.md`) are
> read by scripts and renaming them costs more than the consistency gains."*

**The reason is a test — *is it read by scripts, and does renaming cost more than it gains?* — but the
rule records the answer as a list.** A list goes stale; the test would not have.

**[E] On one vault, four structure files meet the same test and are not on the list:**
`_INDEX-projekt.md`, `MINA-SPÅR.md`, `daglig-triage.md` (CR-022) and `_uppgifter.md` (CR-035, CR-162).
A reader comparing the vault against the contract finds four violations that are not violations.

## The sharper half: the names leaked into the suite

`identifier_language` (CR-049) is explicit that a person-facing word is data:

> *"Display text ... stays in the vault's working language and lives in a settings or vocabulary file,
> **so changing it is a settings change rather than a code change**."*

And the CHANGELOG names the failure it was written against: *"the mistake `identifier_language` was
written to prevent: a tool hardcoding the label."*

**[E] Both Swedish view names are hardcoded in the suite:**

| Literal | Where | What it is |
|---|---|---|
| `"daglig-triage.md"` | `skills/inbox/survey.py:153` | a skip-list entry in code |
| `"daglig-triage.md"` | `tests/test_cr138_survey_contract.py:226` | asserted as contract text |
| `"_inbox/_uppgifter.md"` | `tests/test_cr138_survey_contract.py:218` | asserted as contract text |

A vault that works in English cannot rename either file without editing the suite and breaking two
tests. **That is precisely the coupling CR-049 forbids**, and it arrived after CR-049 shipped — which
is the argument for a check rather than another prose rule.

**[E] The cost is asymmetric and worth recording**, because it is what the grandfather test is
measuring: `survey.py` renders to stdout and never writes a filename, so `_uppgifter.md` costs two test
strings and one SKILL.md line; `daglig-triage.md` additionally appears in a vault-side generator
outside this repository. Same rule, two different prices — which an enumeration cannot express and a
test can.

## Proposal

1. **`system_file_language` states the test and keeps the list as examples**, not as the boundary: a
   structure file whose name is read by a script and whose rename costs more than the consistency
   gains stays as it is, **and the vault declares it** rather than the contract enumerating it.

2. **Vault-local file names that the suite must know are declared in settings**
   (`vault_conventions.view_files` or the existing vault config), and the suite reads them from there.
   The three literals above become lookups. No file is renamed.

3. **A check for the leak, not for the names.** A grep-level test that the suite contains no
   vault-local display filename as a literal — the same shape as `check-terms.py`. It is the part
   worth more than the entry: CR-049 is a rule with no enforcement, and two literals entered after it.

## What this is not

**Not a renaming.** Nothing in any vault is renamed. `identifier_language` already settles the
direction — *where an identifier and its label were historically the same string, the label keeps the
existing spelling* — and this CR does not reopen it.

**Not a question about Swedish.** The same defect appears in any working language the moment a
display name is used as a key. Swedish is where it is visible because that is the measured vault.

## Acceptance

- `system_file_language` reads as a test with examples, and names where a vault declares its own.
- `survey.py` and the CR-138 tests take the view filenames from settings.
- A check fails when a vault-local display filename appears as a literal in the suite.

## As implemented (v1.94.0)

**The check is part of `check-terms.py`, not a new script.** That file already carries the rule that
two scripts doing the same job is the same defect one layer up, and the alignment check already runs
it — so the new check reports on every release with no wiring.

**It found both leaks the CR named, at the lines the CR named**, and one the CR did not: the first
implementation kept the two names as a `DEFAULT_VIEW_FILES` dict in `survey.py`, which is the same
literal one indirection further away. The names now exist in exactly one place in this repository —
`skills/ops-config/base.yaml` — and `survey.py` spells neither. A key that resolves to nothing is
simply absent, and its file is treated as ordinary content; no name is hardcoded as a fallback.

**The test that matters plants the leak.** It appends the triage name to a skill file, requires the
check to fail and name it, removes it, and requires the check to go clean again — because a check
that cannot be made to fail is not evidence that the tree is clean.

14 new tests.
