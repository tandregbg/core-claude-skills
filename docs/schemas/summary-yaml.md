# `_summary.yaml` schema

A per-folder narrative summary file generated in the background by Marvin.
The schema is owned by core-skills (this document); Marvin is the only
producer.

**Producer**: Marvin (formerly `core-skills-visualisation`, renamed 2026-04-29) -- `scripts/generate_summaries.py`. See CR-008 in that repo's `docs/change-requests/`.

**Consumers**: read-only by any skill or tool. Examples:
- `/preparation` -- load summary as one-shot context for a contact briefing
- `/ops` -- supplemental context for a project meeting
- `/transcript` -- context lookup for who/what is being discussed
- Marvin's MCP `get_summary` tool

**Skills must never write `_summary.yaml`**. Marvin overwrites the file
on each scheduled run from the full folder content -- any skill-written changes
will be lost.

## Location

One file per folder, sibling to `CHANGELOG.md` and `_insights.yaml`. Examples:

```
vault/
  _contacts/david/_summary.yaml
  _projects/acme/_summary.yaml
  acme/_summary.yaml
  acme/meetings/management/_summary.yaml
```

A folder is eligible for a summary when it contains at least
`settings.summaries.min_files` (default 2) dated markdown files
(`YYMMDD-*.md`) anywhere in its tree.

## Generation

The producer regenerates each folder's summary from scratch -- no incremental
merging. A `content_hash` over `(filename, mtime, size)` triples is stored in
the file; on the next run, folders whose hash is unchanged are skipped.
Generation runs against the configured Ollama endpoint (local LLM only). If
generation fails for any reason, the existing `_summary.yaml` is left
untouched.

## Schema

```yaml
version: 1                      # int, required, currently 1
context: "david-ekberg"         # str, required: folder display name
context_type: "contact"         # str, required: contact | project | partner | meeting-series | folder
last_updated: 260407T0500       # str, required: YYMMDDTHHMM (UTC-naive local)
generated_by: "ollama:qwen3:30b"  # str, required: provider:model
language: "sv"                  # str, required: ISO 639-1 (auto-detected from source)

source:                         # required block
  folder: "_contacts/david-ekberg"  # str: rel path from vault root
  first_entry: 250912           # YYMMDD of oldest dated file (str or int)
  last_entry: 260405            # YYMMDD of newest dated file
  entry_count: 47               # int: total files included in source
  content_hash: "sha256:abc..." # str: hash of (filename, mtime, size) triples
  truncated: false              # bool: true if max_chars_per_folder cap was hit

summary: |                      # str, required: one paragraph (3-6 sentences)
  Plain prose in the source language. Describes who/what this folder is and
  the current state.

timeline:                       # list, required (may be empty)
  - date: 250912                # YYMMDD (str or int)
    event: "First meeting -- discussed X"   # str: one sentence
    source: "250912-mote-david.md"          # str, optional: source filename

evolution:                      # block, required
  what_changed: |               # str: one paragraph describing how this has evolved
    The conversation shifted from X to Y after Z.
  recurring_themes:             # list of short strings
    - "topic a"
    - "topic b"
  open_threads:                 # list of unresolved threads as short strings
    - "decision on pricing still pending"

generation:                     # block, optional, producer-internal
  duration_seconds: 12.4
  source_files_read: 47
  prompt_chars: 18342
```

### Field rules

- **All language is in the source language.** Producer auto-detects per folder
  (Swedish vs English). No translation.
- **`context` and `context_type`** must be present so consumers can categorise
  the summary without reading the folder path.
- **`source.content_hash`** is the cache key. Consumers should not rely on its
  format beyond "string that changes when the folder content changes".
- **`timeline`** items may be in any order; consumers should sort by `date`.
  Producer emits chronological (oldest first).
- **`evolution.what_changed`** is the most important consumer-facing field
  for "what has changed since I last looked at this folder".
- **No nested objects beyond what is shown above.** Keep the file flat enough
  to render in a single tooltip / panel.

## Reading the file

```python
import yaml

with open(folder + '/_summary.yaml') as f:
    data = yaml.safe_load(f)

if data and data.get('version') == 1:
    print(data['summary'])
    for t in data.get('timeline', []):
        print(t['date'], t['event'])
```

Skills should treat a missing or unparseable `_summary.yaml` as "no summary
available" and continue without it. The file is supplemental context, never a
required dependency.

## Versioning

`version: 1` is the initial release. Breaking schema changes will increment
the version; consumers should check `version` before parsing and skip files
with versions they don't understand.
