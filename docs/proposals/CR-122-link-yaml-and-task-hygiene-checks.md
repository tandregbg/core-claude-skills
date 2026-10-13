# CR-122 — Link, YAML and task hygiene: three mechanical checks in `/ops check`

| | |
|---|---|
| **Status** | **Implemented 2026-10-13, v1.90.0** (with the other two of CR-122, CR-123, CR-124) |
| **Contract** | additive — three report-only findings in `/ops check`; one writing rule for agents that edit YAML; no key changes |
| **Date** | 2026-10-13 |
| **Area** | `ops` (`check`), `ops-base` (agent briefs that edit YAML), `transcript` (link targets in summaries), `tasks` (schema enums, read only) |
| **Related CRs** | CR-048 (task_statuses enum), CR-096 (append before `next_id`), CR-123 (podcast profile, where all three surfaced), CR-124 (themes; its consistency checks follow the same pattern) |

## What happened

A long archive of recorded episodes was run through `/ops` + `/transcript` strictly in order, one agent
per document. The output was good. Three kinds of damage accumulated anyway, each needing a repair
script, and **each was mechanically checkable** before anyone looked:

1. **Parentheses in file names broke Markdown links.** A summary named
   `260103-episode-guest-topic (live).md` was linked as `[...](260103-episode-guest-topic (live).md)`.
   The link renders as text plus a dangling `.md)`; the reader sees nothing wrong until a click fails.
2. **An agent re-dumped a whole YAML file.** Asked to add one entry, it loaded the file, appended, and
   wrote the entire structure back with `yaml.dump` defaults: key order changed, comments vanished,
   `å/ä/ö` became `\xE5` escapes, long strings were folded. The data was intact; the diff was the whole
   file, and the comments were the part a person had written.
3. **`_tasks.yaml` drifted off the schema.** Entries used `title` instead of `task`, a `status: archived`
   no reader declares, `scope: editorial` and `source.type: analysis`. CR-048 declared the status enum so
   that drift would be checkable; nothing checks it.

## Proposal

### 1. Link targets are percent-encoded (`/transcript`, `/ops process`, `/ops check`)

- **Writing rule:** a Markdown link target containing `(`, `)` or a space is written with `%28`, `%29`,
  `%20`. The link text stays as the person reads it.
- **Check:** `/ops check` reports every relative link target in `YYMMDD-*.md`, `README.md` and
  `CHANGELOG.md` under the checked folder that contains a raw `(` or `)` after the opening `](`, or that
  does not resolve to an existing file. One line per link: file, line, target. Report only.

### 2. YAML is edited, never re-dumped (`ops-base`, every skill brief that edits YAML)

- **Writing rule:** an agent adds or changes entries in an existing YAML file by a **targeted edit** (the
  line-based insertion `/transcript` Step 3.5 already uses, CR-096). Loading and writing back the whole
  file is not allowed for `_insights.yaml`, `_tasks.yaml`, `_ops.yaml` or any registry file.
- **Where a full write is unavoidable** (a migration, CR-123), it uses
  `safe_dump(allow_unicode=True, sort_keys=False, width=1000)` and then **verifies**: no `\x`/`\u`
  escapes for characters that were literal before, the same count of `å/ä/ö`, and comments preserved or
  the loss reported.
- **Check:** `/ops check` reports a YAML file under the folder that contains `\xNN` or `\uNNNN` escapes
  of letters (a re-dump signature). Report only.

### 3. `_tasks.yaml` is checked against its declared enums (`/ops check`)

Read `ecosystem.yaml` `task_statuses` and the tasks skill schema, and report per entry:

- a missing `task` field (and a present `title`, which is the usual cause);
- a `status` outside `task_statuses.active` + `finished`;
- a `source.type` outside `meeting | decision | manual | imported`;
- a `scope` outside `root | org | project | personal`;
- an optional `kind` outside the values a profile declares (CR-123), when the active profile declares any.

Report only: the check never rewrites a ledger, because the right fix (rename the field, map the
status, or cancel the task) is a judgement.

## As implemented (v1.90.0)

- `skills/ops/hygiene_check.py` (kinds `links`, `yaml`, `tasks`, `profile`, `themes`), run by `/ops check`.
- A link target is resolved from the file's folder **and every folder above it**: a vault may write
  links from its root, and those are not broken.
- Task findings are **one line per file, field and value**, with the first task ids. A ledger with one
  habit (eighty tasks with the same undeclared source type) gives one line.
- `content` (CR-105) and `correspondence` (CR-080) are accepted as `source.type`: the contract declared
  them as terms after the tasks schema was written. Other undeclared source types are reported; whether
  to declare them is a separate decision.

## What this does not do

- It does not rename existing files. A file name with parentheses may stay; only its link targets are
  encoded.
- It does not add a YAML library requirement to skills that do not write YAML.
- It does not change the tasks schema. CR-123 adds the optional `kind`; this CR only checks what is
  declared.

## Verification (tests under `tests/test_cr122_hygiene.py`)

1. A summary with a raw-parenthesis link target → one finding with file and line; the encoded form → none.
2. A YAML file containing `\xE5` → one finding; the same file with a literal `å` → none.
3. A `_tasks.yaml` with `title:`, `status: archived`, `scope: editorial` → three findings, one per field;
   a valid ledger → none.
4. `/ops check` output on a vault with no findings is unchanged from v1.89.10.
