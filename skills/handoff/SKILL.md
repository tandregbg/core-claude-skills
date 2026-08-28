---
name: handoff
description: Capture a bounded subject from the current conversation as a frozen, self-contained snapshot in `.handoff/` — context a different work session can pick up cold. Written once, indexed nowhere, acted on only by a human. Use when a conversation surfaces something that belongs to a different piece of work.
user-invocable: true
argument-hint: <subject> [| list | read <name> | help]
---

# /handoff -- Frozen Context Snapshots (CR-033)

A conversation often surfaces a **bounded subject that belongs to different work**: a topic a colleague should hear about, a positioning question that belongs to a company document, a commitment whose execution is a separate job.

`/handoff` writes that subject to `<vault>/.handoff/` as a **frozen, self-contained snapshot** — everything the receiving session needs, and nothing else.

**The defining property: nothing picks it up.** No skill parses, indexes, summarises, sweeps or lints it. It generates no task, appears in no dashboard, and is never auto-archived. **A human opens it and starts new work from it.** That is the only way it moves.

Isolation is the feature. The receiving session gets exactly one subject with no surrounding context — no links to chase, no adjacent threads bleeding in, no inherited assumptions.

---

## When to use it

Write a snapshot when **all** of these hold:

- The subject is **bounded** — it can be stated without the rest of the conversation
- It belongs to **different work** than the session that produced it
- Someone will **act on it later**, in a separate session or a separate head
- It benefits from **arriving clean** — without the source conversation's context

### When NOT to use it

| Situation | Use instead |
|---|---|
| Material going out to a named person, with a send event | `_outbox/` + `/outbox` |
| A line of intent with an owner and a date | `_tasks.yaml` + `/tasks` |
| Working material with no destiny | `.ephemeral/` (allowed to die, CR-024) |
| A record of what a meeting covered | The meeting summary (`/transcript`, `/ops`) |
| Durable knowledge worth synthesising across sources | `.knowledge/` via `/insights synthesize` |

A snapshot that would need updating next week is the wrong artefact — that is a living document.

---

## Contract

Six rules. They are the skill.

1. **Frozen.** Written once. Never updated as the world changes; it records what was true when captured. If the situation moves materially, write a **new** snapshot — do not edit the old one.
2. **Self-contained.** No wikilinks, no relative paths, no references to vault files. A reader with no vault access must be able to act on it.
3. **Bounded.** One subject per snapshot. Three separable subjects yield three snapshots.
4. **Not indexed.** No CHANGELOG entry, no README index, no `_insights.yaml`, no task generated.
5. **Read on explicit request only.** Opened because the user asked for it by name — never as part of a scan.
6. **Not archived.** Already frozen; archiving is a no-op.

**For all other skills, `.handoff/` does not exist.** `/ops`, `/ops sweep`, `/ops lint`, `/ops normalize`, `/insights`, `/analytics` and `/daily-dashboard` must skip it the way they skip `.archive/` — regardless of urgency, sensitivity, or what the file says.

---

## Naming

```
.handoff/YYMMDD-handoff-<subject-slug>.md
```

Slug rules follow the vault's general naming contract: `YYMMDD-` prefix always, the `handoff` role keyword always, Swedish characters preserved (`förberedelse`, not `forberedelse`). The subject slug names **the subject**, not the source meeting — the receiving session searches by topic.

Good: `260828-handoff-medtech-transkribering-journalskrivning.md`
Bad: `260828-handoff-marc-motet.md` (names the source, not the subject)

---

## Document structure

```markdown
# Handoff snapshot: [subject]

**{strings.handoff.captured}:** YYYY-MM-DD · **{strings.handoff.source}:** [conversation, date, duration]
**{strings.handoff.scope}:** [what this covers -- and explicitly, what it does not]

> **{strings.handoff.frozen_marker}** Self-contained by design: no links into the vault,
> not indexed anywhere, not referenced by any living document. What is written here is what
> was true on the day -- it is not maintained and does not track later changes.

---

## 1. [First substantive section]

## 2. [Second]

## N. [What was still open / undecided at capture time]
```

**Numbered sections.** A receiving session refers to "section 4" without ambiguity.

**Close with what was open.** The most useful final section is what had *not* been decided when the snapshot was taken — it tells the receiving session where its work begins.

**Write for a cold reader.** Assume no knowledge of the source conversation, the people in it, or the vault. Spell out roles on first mention. Where a figure came from a specific claim, say so.

---

## Confidentiality boundary

Where the content came from a confidential conversation, the snapshot carries an explicit boundary block **at the top, before any content**:

```markdown
> ## {strings.handoff.confidentiality_header} -- READ BEFORE USE
>
> [Where this came from, in one sentence.]
>
> **May be shared onward:** [the general signal -- market state, category movement,
> a regulatory fact -- that the receiver should know regardless of source.]
>
> **May NOT be shared onward:** [the counterpart's own business -- terms, timing,
> commercial arrangements, and that they were the source.]
>
> **Naming:** [whether the source may be named, and what to do if the receiver wants
> to be connected.]
```

This is where the snapshot outperforms every other home: **the constraint travels with the content**, written while the source is still clear. A receiving session has the boundary in front of it instead of inferring it.

Anonymise inside the body too — write "a market-leading vendor" rather than the name when the name is the restricted part. A snapshot that needs a boundary block *and* leaks the identity in section 3 has failed.

---

## Subcommands

### `/handoff <subject>` (default)

Capture the named subject from the current conversation.

1. **Bound the subject.** Identify what belongs and — explicitly — what does not. State the boundary back to the user before writing.
2. **Check the confidentiality question.** Did any of this come from a confidential source? If yes, draft the boundary block and **ask the user to confirm it** before writing. Never guess where the line falls.
3. **Draft self-contained.** Strip every vault link. Expand every reference that assumed the source conversation.
4. **Write** to `.handoff/YYMMDD-handoff-<slug>.md`.
5. **Report the path and nothing else.** No CHANGELOG, no task, no index entry.

If the conversation yields several separable subjects, say so and offer one snapshot each — do not merge them.

### `/handoff list`

List snapshots: filename, capture date, subject line. **Filenames and headings only** — never open or summarise contents.

### `/handoff read <name>`

Open a named snapshot. This is the explicit request the read-lock requires. Partial name matching is fine; if ambiguous, list matches and ask.

### `/handoff help`

Show subcommands and the six contract rules.

---

## Behaviour rules

- **Never write a snapshot unasked.** Offering is fine ("this looks like it belongs to different work — snapshot it?"); writing without being asked is not.
- **Never update an existing snapshot.** Correcting a typo is acceptable. Adding new information is not — that is a new snapshot.
- **Never link a snapshot from a living document.** If a living document needs to point at the subject, it states the subject in its own words.
- **Never generate a task from a snapshot.** The user decides whether the subject becomes work. A snapshot that silently spawns a task has broken the non-delivery property.
- **Never read `.handoff/` during a scan.** Not for context gathering, not for cross-references (`/preparation` Step 2.5), not for insight extraction, not for sweeps.

---

## Out of scope

- **Automation.** Nothing schedules, chases or reminds. A deadline belongs in a task that names the subject; the snapshot stays inert.
- **Dashboards.** Surfacing handoffs in a daily view re-couples them to the flow they were extracted from.
- **Synthesis.** `.knowledge/` (CR-027) synthesises across the corpus and is maintained. Handoffs are point-in-time and are not.
- **Delivery.** A snapshot is never sent. If material is going to a person, that is `_outbox/`.

---

## String Resolution

Template strings marked `{strings.handoff.*}` resolve per the standard order: org config `strings` -> language-matched defaults -> hardcoded fallback.

| Key | English | Swedish |
|---|---|---|
| `strings.handoff.captured` | Captured | Fångad |
| `strings.handoff.source` | Source conversation | Källsamtal |
| `strings.handoff.scope` | Scope | Omfattning |
| `strings.handoff.frozen_marker` | **Frozen snapshot.** | **Fryst ögonblicksbild.** |
| `strings.handoff.confidentiality_header` | CONFIDENTIALITY BOUNDARY | SEKRETESSGRÄNS |

Swedish output follows the vault's `swedish_chars: strict` rule — å, ä and ö in every word that needs them, in headings, body and filename slug alike.
