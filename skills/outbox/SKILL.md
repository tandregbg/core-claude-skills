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

`_manifest.md` is the canonical state file for an outbox item. The skill reads/writes these fields:

```markdown
**Status:** [draft | klar-att-skicka | skickad YYYY-MM-DD | arkiverad YYYY-MM-DD]
**Kanal:** [mejl | slack | print | ...]
**Kontakt:** [email or name]
**Projekt:** [optional theme/context]

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
