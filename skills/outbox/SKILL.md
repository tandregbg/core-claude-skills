---
name: outbox
description: Lifecycle management for outgoing material in `_outbox/`. List pending items, archive completed ones into the relevant contact/project folder, and keep manifest, CHANGELOG, and tasks in sync. Use when an outbox item has been sent, replied to, or otherwise resolved -- and the central `_outbox/` should be cleaned up.
user-invocable: true
argument-hint: [list | status | archive <folder-name> | help]
---

# Outbox Skill

Manages the lifecycle of outgoing material staged in `<vault>/_outbox/`. Each subfolder there represents one "send" event (mejl + attachment + preparation). Once sent and resolved, the material belongs in the relevant contact/project folder -- not as eternal residue in the central outbox.

## Vault Location

```
vault/_outbox/
  YYMMDD-<contact-or-project>_<context>/   <- staging while in flight
    _manifest.md                            <- canonical state file
    [files...]
```

**After archiving:**

```
vault/_contacts/<contact>/
  YYMMDD-<context>/                         <- archived inside contact folder
    _manifest.md                            <- updated with Status: arkiverad + Utfall
    [files...]
```

For project-scoped outbox items the destination is the project folder (`<vault>/<venture>/_projects/<project>/` or similar). The skill detects scope from the manifest or asks.

## Manifest schema

`_manifest.md` is the canonical state file for an outbox item. The skill reads/writes these fields.

**The labels below are Swedish because this vault is.** Each one is the written
form of a field whose name is English — `status`, `channel`, `contact`,
`project`, `source` — and a tool that reads manifests should key on the field
and keep the label in a vocabulary file, never as a literal in its code. That
way the same tool serves a vault in another language without a code change.
See `identifier_language` in `ecosystem.yaml`.

```markdown
**Status:** [draft | klar-att-skicka | skickad YYYY-MM-DD | avskriven YYYY-MM-DD | arkiverad YYYY-MM-DD]
**Statusnot:** [free text: what actually happened — channel, time, a link, a circumstance]
**Kanal:** [mejl | slack | print | ...]
**Kontakt:** [email or name]
**Projekt:** [optional theme/context]
**Klassificering:** [team-wide-safe | team-only | management-only]
**Kanonisk källa:** [path to the source doc each attachment is rendered from — or `ingen (originalet bor här)`]

## Innehåll
[file table]

## Skicka
[instructions]

## Svar förväntas på
- [ ] item 1
- [ ] item 2

## Utfall
[populated when resolved]
```

When all `Svar förväntas på` items are checked AND `Utfall` is populated, the item is **resolution-ready** -- ready to archive.

### `avskriven` -- resolved without being sent (CR-047)

Some items are resolved by a decision not to send them. A recap that the
meeting made unnecessary, a draft overtaken by events, questions that will be
asked in conversation instead. They were dealt with; they simply never became
a send event.

Before this status existed those items could never be archived, because
`archive` required a sent status -- so they accumulated in `_outbox/`
indefinitely, looking unfinished while actually being done.

```markdown
**Status:** avskriven 2026-09-21
**Statusnot:** Tas muntligt vid nästa samtal -- inget som behöver skickas
```

**Archivable on the same terms as `skickad`, with one addition: `## Utfall`
must say why.** "Not sent, because X" is an outcome, and an item filed without
one is indistinguishable later from an item that was abandoned.

`list` shows these under **RESOLVED, NOT SENT** rather than among the pending,
because a pending list that includes resolved items is a list nobody trusts.

A dispatching surface may set this status (contract `writers` on
`_manifest.md`), for the same reason it may set `skickad`: whether something
was sent is an observation. It must not write the `Utfall` -- what the outcome
*means* is the judgement this skill owns.

### `Klassificering` — who may receive it (CR-066, CR-070)

**Distinct from `Kanal` and `Kontakt`, which say where it is going.** This field says who may
*receive* it, and it is what lets a dispatching surface warn before a send widens the audience of
something never written for it.

| Value | Audience | The test |
|---|---|---|
| `team-wide-safe` | Anyone internal — **the default when absent** | Would it survive being forwarded anywhere inside the organisation? |
| `team-only` | The working team; not interns or contractors | Is the restriction about *employment status*? |
| `management-only` | **Named recipients** | Is there a list of people, rather than a group? |

**Listed most to least permissive, and the order is part of the schema.** The first two scale a
group; the third leaves group distribution altogether. Widening out of `management-only` into any
channel is the step that turns an individual assessment into a group communication — the one a
warning most needs to catch.

**Authored by the skill, read-only to a dispatcher.** A dispatching surface may write `Status`,
`Statusnot`, `Kanal` and `Kontakt`; it does not write this field. It warns and asks for confirmation
when a send would widen beyond the declared value, and does not refuse — refusing would be the
dispatcher deciding what a classification means, which is not its to decide (CR-047).

**Decide it before writing the body, not after.** An item written for everyone and reclassified at
the end is an item whose sentences were composed for the wrong reader.

### `Statusnot` — what happened, in words

`Status` is parsed; `Statusnot` is read by people. The status line answers *which
state is this in*, and a tool matches it with a pattern. The note answers *what
actually happened* and takes whatever detail makes the event reconstructable
later: the channel and time, a published URL, which of several recipients it
reached, or why a send was partial.

Documented here as of CR-053 because it grew in practice and was in use by 104
of the live vault's manifests while appearing nowhere in this schema. Examples
from those files:

```
**Statusnot:** skickad 2026-08-30 (mejl kl ~12:00)
**Statusnot:** PUBLISHED 2026-09-02 -- https://lnkd.in/p/d6WTTjb5
**Statusnot:** delvis skickat -- hela-teamet-utskicket gick via Teams 26/8 (mejlvägen blockerad)
```

Optional. An item with a plain `Status` and no note is complete.

### `Kanonisk källa` is REQUIRED (CR-032)

Every manifest must state where its material actually lives. Two valid answers:

- **A path** -- the attachment is a *rendering* (PDF out of a `.md`, export out of a dataset).
  The source is the original; the outbox copy is disposable. Example:
  `_contacts/<kontakt>/leverans/YYMMDD-onepager.md`
- **`ingen (originalet bor här)`** -- the material exists nowhere else. Typically the
  `mejl.txt` and the manifest itself. **This is not a defect**, it is a statement that the
  folder must be archived rather than deleted.

**Why it is required.** An audit on 2026-08-28 found 86 outbox items, of which only 3 of 71
manifests named a source. That made a routine question -- *"is this a copy or the original?"* --
unanswerable without opening every folder and grepping the vault. PDFs turned out to be
renderings, but the mejl-texts and manifests existed only in `_outbox/`, so a bulk clean-up
would have destroyed material. The field moves that determination to **creation time**, where
the author knows the answer, instead of to clean-up time, where nobody does.

**Enforcement:**
- `list` flags any manifest missing the field: `(saknar Kanonisk källa)`.
- `archive` **warns but does not abort** -- refusing would strand legacy folders. It asks the
  user to fill it in, and offers `ingen (originalet bor här)` as the default.
- When `/ops` (or anything else) stages new outbox material it must write the field. Leaving it
  blank is the same defect as leaving `Status:` blank.

## SUBCOMMANDS

### `list` (default if no args)

**Trigger:** `/outbox` or `/outbox list`

Walk `<vault>/_outbox/*` (excluding `.archive/`), parse each `_manifest.md`, and print a status table:

```
## Outbox status

PENDING (awaiting reply)
  260427-carol-jones_reflektion       skickad 260427      0/2 svar
  260427-dan-smith_reflektion     skickad 260427      0/1 svar

RESOLUTION-READY (archive candidates)
  260427-bob-lindgren_acme      skickad 260427      2/2 svar  Utfall: ja

DRAFT
  260506-someone_topic                 draft               -

WITHOUT MANIFEST (manual review needed)
  260418-bob-lindgren_acmecorp    -                   -

MISSING KANONISK KÄLLA (fill in — copy or original?)
  260503-someone_topic            skickad 260503      saknar Kanonisk källa
```

For each resolution-ready item, suggest: `/outbox archive <folder-name>`.

If a folder has no `_manifest.md`, flag for manual review -- don't auto-classify.

### `status`

Alias for `list`.

### `archive <folder-name>`

**Trigger:** `/outbox archive 260427-bob-lindgren_acme`

**Steps:**

1. **Validate:**
   - Folder exists in `<vault>/_outbox/<folder-name>/`
   - `_manifest.md` exists and parses
   - `Status:` is `skickad ...` (warn if `draft`, abort if missing)
   - All `Svar förväntas på` items checked (warn if any unchecked, ask user to confirm)
   - `Utfall` section populated (warn if empty)

2. **Determine destination:**
   - From manifest `Kontakt:` or folder-name prefix, identify contact/project
   - For contact: `<vault>/_contacts/<contact-slug>/`
   - For project: read manifest `Projekt:` or ask user
   - **Multiple contacts** (e.g. ambassador-style fan-out): ask user -- duplicate to each, or pick primary, or keep in a shared `_outbox/.archive/`. Default suggestion: duplicate to each contact folder.

3. **Determine new folder name:**
   - Default: strip contact-name prefix from outbox folder name
     - `260427-bob-lindgren_acme` -> `260427-acme` (or `260427-partnership` if user prefers theme over context)
   - Ask user to confirm or override

4. **Move folder:**
   - `mv <vault>/_outbox/<folder-name> <destination>/<new-folder-name>`
   - Files inside keep their original names (rename only on user request)

5. **Update `_manifest.md`** at new location:
   - `Status:` -> `arkiverad YYYY-MM-DD`
   - Add tidslinje row if not present
   - Ensure all reference paths (Detaljer:, Source:) point to new locations

6. **Update contact CHANGELOG.md:**
   - Add entry: `**YYMMDD: Ärendet arkiverat** - Outbox-material flyttat till <new-folder-name>/. [link]`

7. **Update `_tasks.yaml`** in contact folder:
   - For any task referencing the old `_outbox/...` path, rewrite the source path to point to new location
   - Don't auto-complete tasks -- that's a separate decision

8. **Update referencing documents:**
   - Search vault for links to old path: `grep -r "_outbox/<folder-name>" <vault>` (excluding `.archive/`)
   - Update each reference to the new path
   - Show diff before applying

9. **Report:**
   ```
   Archived: 260427-bob-lindgren_acme
     -> _contacts/bob-lindgren/260427-partnership/
   Updated:
     - _contacts/bob-lindgren/CHANGELOG.md (+1 entry)
     - _contacts/bob-lindgren/_tasks.yaml (1 source path)
     - _contacts/bob-lindgren/<samtal>.md (1 reference)
   ```

### `archive --all-sent` (CR-019)

**Trigger:** `/outbox archive --all-sent`

Batch mode over the single-folder `archive` flow, so a backlog of sent items can be closed in one sitting instead of item by item ( `/ops sweep` offers this command when it finds sent-but-unarchived items).

1. Run the `list` logic and collect every folder whose manifest `Status:` is `skickad ...`.
2. Present the candidate list up front (folder, destination guess, proposed new name) and let the user confirm all / select / abort.
3. For each confirmed folder, run the standard `archive <folder-name>` steps 1-9. Per-folder judgement calls (destination for multi-contact items, folder rename) are still asked individually -- batch mode batches the *selection*, not the decisions.
4. Final report: one summary table (archived → destination), plus the items skipped and why (unchecked "Svar förväntas på", empty Utfall, missing manifest).

### `help`

Print this skill's usage.

## Behaviour rules

- **Never delete files.** Only move. Original outbox folder is removed only after successful move (it should be empty).
- **Never auto-complete tasks.** Archiving is a file operation, not a workflow decision.
- **Always confirm folder rename** -- destination folder name is a judgement call (theme vs context vs date-only).
- **Preserve manifest history.** Append to `## Tidslinje` if it exists, never overwrite.
- **Swedish text** must use correct å, ä, ö (vault-wide rule). When generating manifest updates or CHANGELOG entries in Swedish, verify each common word: för, är, på, från, även, över, första.
- **Email .txt files are plain text** -- never reformat to markdown when touching them.

## Manifest detection edge cases

- **No manifest:** flag in `list`, refuse to archive without one. User must create manifest manually first.
- **Manifest with `Projekt:` set, no contact:** treat as project-scoped; archive to `<vault>/_projects/<projekt>/` or venture project folder.
- **Multiple contacts (ambassador case):** flag as fan-out; ask user for resolution strategy.
- **Old outbox layout (`260427-name_topic`)** vs new (`260427-topic`): support both for `list`; new naming is for archived destinations.

## Naming convention for staged folders

`YYMMDD-<recipient>_<subject>/` — the underscore splits **who** from **what**.

**The right side names the subject of the send, not the artifact inside it.** A staged item is a
*folder*: it holds a `_manifest.md` and one or more files, and `_manifest.md` already enumerates them.
Naming the folder after one of its files is a claim that stops being true the moment a second file
arrives — an attachment, a deck, a second cut for a different audience.

| Prefer | Not |
|--------|-----|
| `260921-team-a_standup` | `260921-team-a_standup-recap` |
| `260921-team-c_design-review` | `260921-team-c_design-review-recap` |
| `260916-team-e_topic-with-three-parts` | `260916-team-e_topic-with-three-parts-preread` |

**The exception is when the artifact type *is* the subject** — a board deck sent as a deck, a pre-read
sent as a pre-read, where the recipient asked for that thing and nothing else is coming. `_deck-v2` and
`_preread` are legitimate; `_recap` almost never is, because a recap is what the file is, not what the
send is about.

**The left side names the recipient, not the project.** `team-a_standup`, not
`team-a-v3_standup` — the project is visible from the content and from `_manifest.md`'s `Projekt:`
field, while who it goes to is the one thing a folder listing cannot otherwise tell you.

*(Introduced 2026-09-21 after three projects in one vault staged the same artifact under three
different shapes, and a fourth named its folder after a file it no longer contained.)*

## Naming convention for archived folders

When archiving into a contact's folder, the contact-name prefix is redundant. Strip it:

| Outbox name | Archived name (in contact folder) |
|-------------|-----------------------------------|
| `260427-bob-lindgren_acme` | `260427-acme` or `260427-partnership` |
| `260427-dan-smith_reflektion` | `260427-reflektion` |
| `260427-carol-jones_reflektion` | `260427-reflektion` |

The skill suggests a default but always asks before renaming. For ambassadörs-style (multi-contact) the original name may be retained when archiving to a shared location.

## Integration with other skills

- **`/ops`** -- when ops-skill creates outbox material (preparation, mejl), it stages to `_outbox/`. This skill handles the back end of that flow.
- **`/transcript`** -- transcripts of follow-up calls/replies that resolve an outbox item should reference the resolution doc, which `/outbox archive` then links to in the manifest's `Utfall` section.
- **`/inbox`** -- mirror skill for incoming material. Same lifecycle pattern.
- **`/tasks`** -- tasks generated from an outbox item live in the contact's `_tasks.yaml` and survive archiving (paths rewritten).

## Not to be confused with `/handoff` (CR-033)

An outbox item is **addressed to a person** and has a send event, an expected reply, and a resolution. A handoff snapshot is addressed to a **future work session**, is never sent, and is resolved only when a human opens it and starts new work.

If material is going to someone, it is outbox. If it is bounded context for different work, it is `/handoff`. This skill never reads or writes `.handoff/`.

## Out of scope

- Drafting outbox content -- that's `/ops` or manual.
- Sending email -- that's done outside the vault by the user.
- Categorisation/classification -- the manifest's `Projekt:` and folder-name prefix carry the signal.

---

*Created: 2026-05-06*
