# CR-159 — A template contract cannot say a heading belongs only when there is content for it

| | |
|---|---|
| **Status** | **Proposed** (2026-10-26) |
| **Contract** | `workflows.meeting_templates`: a per-heading optional marker. Additive — a contract written today keeps its meaning |
| **Date** | 2026-10-26 |
| **Area** | `ops-base` (Template Contracts, CR-018), the pre-save check in `ops` and `transcript`, the template-contract check in `/ops check <folder>` |
| **Related CRs** | **CR-018** (template contracts: this is a gap in check 1), CR-006 (the canonical heading order, whose last section is the one at issue) |

Marks: **[E]** observed in a running series and measured · **[H]** not yet run.

## What happened

A partner folder's meeting series got its contract declared after `/ops check` reported three deviating files. Declaring it
surfaced a second finding the ad-hoc check had hidden: of **27 summaries** written since the series adopted the CR-006 order,
**16 carry the full five-heading canon, 5 carry exactly the first four and no fifth, and 6 have other shapes** (three of them
declared one-off contracts). **[E]**

The five without the trailing `## Bakgrund` are not drift. They are a lunch, a last-minute check before an event, an answer to
six written questions, an informal conversation, and a summary of a workshop — **meetings that had no background to give.** The
folder's owner, asked whether to complete them or change the contract, answered: *they have no background.* **[E]**

So both values of `headings` are wrong, and the difference was measured:

| `headings` declared as | Files that pass | Files reported |
|---|---|---|
| Five, with the trailing heading | 16 | **5** — the legitimate absences |
| Four, without it | 5 | **16** — every file that correctly has one |

Setting it to four inverts the finding and triples it. **[E]**

## Why

CR-018's check 1 is an equality: *the H2 heading sequence **equals** the contract's `headings` (order and canonical names)*. A
heading that belongs in a file **only when there is content for it** has no expression. Every route out fails:

- **A one-off contract per file.** Already used three times in this folder for genuinely singular shapes, and documented there
  as not scaling. Five more entries matching one historical file each describe nothing and can never match a new file.
- **Drop the heading from the contract.** Reports the 16 files that correctly carry it.
- **Keep it.** Reports the 5 legitimate absences on every run, for as long as the folder exists.
- **Compare prefixes instead of sequences.** This is what hid the drift in the first place: an ad-hoc four-heading check passed
  all 27 files, including the 5 that have no fifth heading at all, so nothing was reported and the series kept forking. **[E]**
  Loosening the comparison is not the fix — it is the original defect.

**The configuration language already has the idea, in a neighbouring key.** `domain_additions[].trigger: if_relevant` means
exactly *include this section when the meeting gives it something to say*. A heading contract cannot say it.

## Why it matters more than the wording

A check whose findings include known-good files stops being read, and then it stops working. CR-018's whole value is that a
finding means a file drifted — the mechanism exists because per-file review cannot catch silent template forking, and a reader
who has learned to skip five standing findings is back to per-file review. The permanent-finding route does not keep the
contract honest; it retires the check quietly.

## Proposal

1. **A heading may be declared optional**, in the idiom the config already uses for a section that depends on content:

   ```yaml
   workflows:
     meeting_templates:
       partner-series:
         match: "<partner>/meetings/*"
         headings: [Nästa steg, Beslut, Konklusion, Diskussion, {name: Bakgrund, trigger: if_relevant}]
         action_table: ["#", "Åtgärd", "Ägare", "Prio", "Deadline"]
   ```

   A bare string stays required, so every contract written before this CR keeps its exact meaning.

2. **Check 1 becomes:** the sequence of required headings must match in order and name; an optional heading may be absent, and
   **when present must sit in its declared position**. An optional heading in the wrong place is still a finding — the point is
   that the section is conditional, not that its position is free.

3. **Checks 2 and 3 are untouched.** The action-table header row and the empty-`Beslut` marker are unchanged.

4. **`default` declares nothing optional.** A project that silently stops writing a canonical section is still reported; making
   it optional is a declaration someone wrote down, which is what CR-018 asks for — *a deliberate format change is made by
   editing the contract*. The marker makes that edit expressible; it does not make it automatic.

5. **Report optional headings in `/ops status`** where it prints the resolved contract, so a reader can see which sections a
   series has been allowed to omit without opening the config.

## Verification

1. The folder above: the five summaries without the trailing heading pass; the 16 with it pass; the three declared one-off
   contracts are unaffected. Template-contract findings for the series go from 5 to 0 **without the contract losing the
   heading**.
2. A file that places the optional heading before `## Diskussion` is reported, with the expected position named.
3. A contract whose `headings` are all bare strings behaves byte for byte as before — the 11 pre-canon files in the same folder
   are still reported.
4. `default` with a canonical five-heading list still reports a file missing the fifth, in a folder that declared nothing
   optional.
5. The eleven pre-canon files stay reported: this CR does not give a way to silence history, only to describe a section that
   depends on content.

## Not in scope

- **Optional headings in the middle of a sequence.** The three one-off contracts in that folder are extra *topic* sections
  inserted after `Beslut`, each written once for one meeting. They are a different problem — an arbitrary extra section, not a
  declared conditional one — and declaring five of them would be the sprawl this CR avoids, not an instance of it.
- Whether CR-006's canonical order should keep the trailing section at all. It is canon in the vault that reported this, and 16
  of 27 files use it correctly.
- The action-table and `Beslut`-marker checks.

## Evidence

- A partner folder's 27 post-canon summaries, measured 2026-10-26: 16 with the full canonical sequence, 5 with the first four
  headings and no fifth, 6 other shapes. The 5 are short or informal meetings with no background to state.
- The same folder's three one-off contracts, declared two days earlier, with a note in the config that a fourth occurrence
  should produce a CR rather than a fourth entry. This is that CR, for a different and more common shape.
- The ad-hoc prefix-comparison check that passed all 27 files and reported none of the 5 — the measurement that showed
  loosening the comparison re-hides the drift CR-018 exists to catch.
