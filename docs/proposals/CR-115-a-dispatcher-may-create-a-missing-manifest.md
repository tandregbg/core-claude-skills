# CR-115 — A dispatching surface may create a manifest where a folder has none

| | |
|---|---|
| **Status** | **Implemented** v1.89.4, 2026-10-08 (contract 41) |
| **Contract** | additive (40 → 41): a new, narrow writer permission on `_outbox/<item>/_manifest.md` |
| **Date** | 2026-10-08 |
| **Area** | `ecosystem.yaml` (`vault_conventions` `_manifest.md` writers, `outbound_dispatch.tools`, `components.dashboard`), `outbox` (manifest detection edge cases, `list`) |
| **Related CRs** | CR-032 (`Kanonisk källa` required), CR-047 (dispatcher writes status), CR-066/CR-070 (`Klassificering`), CR-102 (edit in place), CR-103 (declared status words); Marvin **CR-024** (the implementation) |

Marks: **[E]** observed · **[H]** not yet run.

## What happened

On 2026-10-08 two outbox folders had no `_manifest.md`. One was a plain-text mail reply, the other an API
note for a customer, with a reference file beside it. **[E]** The dashboard listed them as "no status, no
manifest" and could do nothing else:

- a send through it could not be recorded;
- Mark not sent refused, because there was no manifest to write to;
- `/outbox` will not close them: "refuse to archive without one. User must create manifest manually
  first."

The owner knew what had happened to each item and had nowhere to say it. Creating a manifest by hand means
remembering the labels, the declared status words and the required `Kanonisk källa`, which is exactly the
step that gets skipped.

## Findings

**"Never authors a manifest" protects existing manifests, not missing ones.** The rule exists so that a
dispatcher cannot become a second author of a file the skill wrote: rewriting the field block, the
`Klassificering`, the outcome. A folder with no manifest has no author to compete with. Without a
manifest, though, the one record the contract relies on (the status) cannot exist at all.

**Most fields can be derived, and the one that cannot should be asked for.** A mail body's `Till:` and
`Ämne:` give the channel, recipient and subject. The `<recipient>_<subject>` folder name gives the
recipient, and a sibling item for the same recipient carries the project and channel. Whether something
was sent outside the dispatcher cannot be seen, so the person must say it.

## Proposal

1. **Writer permission (`_outbox/<item>/_manifest.md` `writers`, `components.dashboard.writes`):** a
   dispatching surface may **create** a manifest for an outbox *folder* that has none, on explicit
   confirmation after showing the exact file. Conditions:
   - the create is exclusive: if a manifest exists by the time it writes, it stops and overwrites
     nothing (CR-102's read-before-write, applied to creation);
   - `Status` is one of the declared `status_forms` (CR-103), chosen by the person and never derived;
   - `Kanonisk källa` is written (CR-032), defaulting to `ingen (originalet bor här)`;
   - `Klassificering` may be written **at creation only**, as chosen by the person; empty means absent,
     which reads as `team-wide-safe`. After creation it is read-only to the dispatcher, as now;
   - the body has `## Innehåll` with one row per file and `## Tidslinje` with one line saying the
     dispatcher created it and when. **No** `Svar förväntas på` and **no** `Utfall`: those stay the
     skill's.
2. **Once created it is an ordinary manifest.** `manifest_edit_in_place` applies from the next write on.
   `/outbox` and `/ops` may add the sections they own, and the dispatcher keeps its usual four fields.
3. **`/outbox` edge cases:** "No manifest" becomes "flag in `list`; a dispatching surface can create one;
   refuse to archive without one". `list` may show a manifest whose timeline says a dispatcher created it,
   so a reviewer knows its `Svar förväntas på` was never written.
4. `outbound_dispatch.tools` `never:` becomes *"Edits an existing manifest beyond status, status-note,
   channel and contact; decides what a status means; or archives"*.

## Not in scope

- Loose top-level files. Moving one into a folder is a staging judgement and stays `/outbox`'s.
- Detecting sends the dispatcher did not make.

## Verification

- `ecosystem.yaml` validates; `contract_version` 41 with a changelog line.
- Marvin CR-024 implements the dispatcher side (tests: exclusive create, declared-status refusal, preview
  writes nothing). **[E]**
- `/outbox list` and `close` on a dispatcher-created manifest: it parses, it is listed by status, and
  `close` asks for `Utfall` as for any other item. **[H]**
