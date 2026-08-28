# CR-033: Handoff snapshots — frozen, self-contained context transfer

| Field | Value |
|-------|-------|
| **CR Number** | CR-033 |
| **Date** | 2026-08-28 |
| **Status** | Implemented |
| **Related CRs** | CR-024 (`.ephemeral/` scratch); CR-019 (living-artefact moves need tombstones); CR-012 (inbox schema) |
| **Skills touched** | new skill `handoff`; `ecosystem.yaml` (`vault_conventions`) |
| **Breaking Changes** | No — new artefact class, opt-in |

## Summary

A conversation frequently produces a *bounded subject* that belongs to a different
piece of work than the one being done: a topic raised in a meeting that a colleague
should hear about, a positioning question that belongs to a company document, a
commitment whose execution is a separate task entirely.

Today that material has three bad homes. It stays buried in a meeting summary where
the next session will not find it; it is copied into a living document that then
carries content it does not own; or it lands in `.ephemeral/` and dies.

This CR adds a fourth: a **handoff snapshot** — a frozen, self-contained document
capturing one bounded subject, written once, indexed nowhere, and **acted on only
by a human**.

## The defining property: non-delivery

An outbox item is *sent*. A task is *executed*. A handoff snapshot is **neither**.
It is written, and then it waits.

Nothing in the suite picks it up. No skill parses, indexes, summarises, sweeps or
lints it. It does not appear in a dashboard, does not generate a task, and is never
auto-archived. The only way it moves is that a person opens it and starts a new
piece of work from it.

This is deliberate, and it is the entire point. The value of a handoff is that the
receiving session gets **exactly one subject with no surrounding context** — no
vault links to chase, no adjacent threads bleeding in, no risk of the new session
inheriting the old one's assumptions. Isolation is the feature; automation would
destroy it.

## Why not the existing homes

| Home | Why it fails |
|---|---|
| `_outbox/` | Outgoing material addressed to a *person*, with a send event and an expected reply. A handoff addresses a *future work session* and is never sent. |
| `_tasks.yaml` | A task is a line of intent. A handoff is the context a task would need — too large for a task, and it does not want a status field. |
| `.ephemeral/` | Explicitly allowed to die (CR-024). A handoff must survive until acted on. |
| The living document | Puts one subject's context inside a document that owns a different subject. The next session reads the whole file to find the part it needs. |

## Contract

1. **Frozen.** Written once. Not updated as the world changes; it records what was
   true when captured. If the situation moves materially, write a new snapshot —
   do not edit the old one.
2. **Self-contained.** No links into the vault, no wikilinks, no relative paths. A
   reader with no vault access must be able to act on it. This is what makes it
   portable into a fresh session, another machine, or another person's hands.
3. **Bounded.** One subject. A conversation that yields three separable subjects
   yields three snapshots, not one long document.
4. **Not indexed.** No CHANGELOG entry, no README index, no `_insights.yaml`, no
   task generated. Skills must never parse, index, update, summarise, sweep or lint
   the contents.
5. **Read on explicit request only.** A session opens a snapshot because the user
   asked for it by name — never as part of a scan.
6. **Not archived.** Already frozen; archiving is a no-op. They accumulate, and that
   is acceptable: they are small and they are the cheapest possible record of a
   decision's context.

## Confidentiality boundary

A snapshot is often the right place to record *what may and may not be repeated*,
because it is written at the moment the source is still clear. Where the content
came from a confidential conversation, the snapshot carries an explicit boundary
block at the top: what may be shared onward, what may not, and whether the source
may be named. The receiving session then has the constraint in front of it rather
than having to infer it.

This is the one respect in which a handoff outperforms every other home: the
constraint travels with the content.

## Non-goals

- **No automation.** Nothing schedules, chases, or reminds. If a handoff needs a
  deadline, the deadline belongs in a task that references the subject; the snapshot
  itself stays inert.
- **No dashboards.** Surfacing handoffs in a daily view would re-couple them to the
  flow they were extracted from.
- **Not a knowledge layer.** `.knowledge/` (CR-027) synthesises across the corpus and
  is maintained. Handoffs are point-in-time and are not.
- **Not a replacement for a summary.** The meeting summary remains the record of the
  meeting. A snapshot is an extract for a different purpose.
