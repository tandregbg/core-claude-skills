# CR-177 — One malformed file took the whole scan down

| | |
|---|---|
| **Status** | **Implemented v1.94.3** (2026-11-04) |
| **Contract** | none — one guard in one script |
| **Date** | 2026-11-04 |
| **Area** | `insights` (`promotion_candidates.py`), `tests/test_cr177_malformed_insights.py` |
| **Related CRs** | **CR-100** (this script is the arithmetic both compile and a review surface read), CR-096 (orphan entries — the other way an `_insights.yaml` goes wrong), CR-020 (`migrate`, the tool for a drifted file), CR-145 (a failed source is named in the output, never silently dropped), CR-175 (the compile backlog this run was measuring) |

Marks: **[E]** observed · **[H]** not yet run.

---

## What happened

**[E] 2026-11-04, running compile Pass 2 over a 133-ledger vault for the first time:**

```
AttributeError: 'list' object has no attribute 'get'
  promotion_candidates.py:336  everything = [e for e in (doc.get("insights") or []) ...]
```

**One file**, in one folder of one venture, parses as a YAML **list** rather than a mapping — a
hand-written corpus with its own schema (`topic:` and `insight:` instead of `type:` and `summary:`,
ISO dates, no `insights:` key, entries at the top level). It is a legitimate thing to find in a
vault that has been accumulating for a year, and `migrate` exists for exactly that drift.

**The script already handles the harder case.** A file that does not parse at all is caught and
recorded:

```python
except (OSError, yaml.YAMLError) as error:
    report["unreadable"].append({"file": str(f), "error": type(error).__name__})
    continue
```

A second file in the same vault is genuinely unparseable (`ScannerError`) and was handled
correctly. **The list-shaped file parses fine and then fails on the next line** — outside the
`except`, so it propagated.

### The cost is the whole pass, not the one folder

This script is, by CR-100's design, the single arithmetic for promotion — compile reads it and a
review surface reads it, so that they cannot drift apart. That makes it a **chokepoint**: one
malformed file in one folder stopped the candidate scan for all 133, and the first compile run over
a 3,389-entry backlog could not start.

**The shape is the one the suite keeps finding, inverted.** CR-145's rule is that a source that
cannot be read is *named in the output* rather than silently dropped. Here the source was neither
named nor dropped — it took the reader with it. A crash is not a report.

## The change

One guard, in the same place and the same shape as the existing one:

```python
if not isinstance(doc, dict):
    report["unreadable"].append({"file": str(f),
                                 "error": f"not a mapping ({type(doc).__name__})"})
    continue
```

A file that parses but is not a mapping has the **same outcome** as one that does not parse — this
scan cannot use it — so it belongs in the same list, with a reason precise enough to act on.
`unreadable` is already printed by `--text` and carried in the JSON, so both readers see it.

## As implemented

**[E]** The run that found it then completed: **130 folders scanned, 76 candidate groups, 2 files
reported unreadable** — the list-shaped one and the `ScannerError` one, each named with its reason.

**What this CR deliberately does not do:**

- **It does not repair either file.** They are vault data, one of them a corpus in a foreign schema
  that a person needs to look at. `/insights migrate` is the tool, and it is a judgement call
  whether that file should be migrated or left as what it is.
- **It does not make the other readers tolerant.** `compile`, `status` and `synthesize` each walk
  the corpus too, and whether they have the same hole is **[H]** — worth a pass, and not something
  to assert from one fix.

## Acceptance

- A vault containing a list-shaped `_insights.yaml` scans to completion.
- That file appears in `unreadable` with a reason naming the type found.
- A genuinely unparseable file keeps its existing handling.
- A test builds both shapes and asserts the scan completes and reports both. **[E]** 6 new tests.
