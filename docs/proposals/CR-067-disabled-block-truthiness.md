# CR-067: A disabled config block is truthy — two readers treat "off" as "on"

| Field | Value |
|-------|-------|
| **CR Number** | CR-067 |
| **Date** | 2026-09-22 |
| **Author** | User + Claude Code |
| **Status** | Implemented |
| **Implementation Date** | 2026-09-22 |
| **Priority** | High |
| **Complexity** | Low |
| **Estimated Scope** | `skills/ops/list_projects.py`, `skills/ops/build_agenda.py` |
| **Related CRs** | CR-057 (carry-forward), CR-065 (`/ops projects`), CR-011 (config chain) |
| **Breaking Changes** | No — fixes behaviour that was already wrong |

---

## Executive Summary

**Two readers test a config block for presence when they mean enabled.** A block written to turn something **off** is a non-empty dict, and a non-empty dict is truthy — so declaring `enabled: false` reads as *on*.

```python
# list_projects.py:72
if pp.get("carry_forward"):          # {"enabled": False} -> True
    return "wired", info

# build_agenda.py:76
if not cf:                           # {"enabled": False} -> not-falsy -> proceeds
    continue
```

**This is not a style point, because the config chain makes `false` the only way to say no.** A project inheriting an org layer that enables carry-forward cannot opt out by omitting the key — omission inherits. It must declare `enabled: false`. **The one correct way to disable the feature is the way that switches it on.**

Found when a project declared `carry_forward: {enabled: false}` specifically to avoid inheriting an org-level carry-forward pointed at a different meeting series. `/ops projects` then listed it as **LOOP WIRED**, advertising that `build_agenda.py` works there.

---

## Why the second one matters more

`list_projects.py` mislabels a row. **`build_agenda.py` acts.**

It accepts the block, then fills in defaults for everything the disabling project never specified — including `note_suffix`, which defaults to `daily-standup`. So it will build a standup agenda, from a note-naming convention the folder does not use, for a project that explicitly asked for no agenda at all.

**And the failure is quiet in the way carry-forward failures already are.** The skill documents this about the chain itself: a broken chain "does not error, does not warn, and produces a next agenda with zero carried items that looks perfectly correct". The same is true here, one level up — an agenda generated for a project that disabled agendas looks exactly like an agenda.

---

## The fix

Read the field, not the block. Both sites:

```python
# list_projects.py
if cf.get("enabled", True):
    return "wired", info

# build_agenda.py
if not cf.get("enabled", True):
    return {"enabled": False, "_root": root}
```

**Three states, not two.** No block at all means no loop. A block **without** `enabled` means one written before the flag existed — a working loop, and adding a field must not reclassify configurations that work today. Only an explicit `false` disables. Collapsing the first two is easy and wrong: normalising a missing block to `{}` makes the `enabled` default fire and reports every configured-but-loopless project as wired.

**A disabled declaration stops resolution; it does not fall through.** `build_agenda.py` resolves by walking up — *nearest declaration wins*. Skipping a disabled block and continuing the walk lets a further-away `enabled: true` override a nearer `enabled: false`, which is the opt-out failing in the single direction it exists for. The first version of this fix did exactly that: the project disabled carry-forward, the walk continued to the org layer, and it built against the org's note suffix. **Stopping is the fix; skipping is the same bug relocated.**

Anything that is not a mapping — `carry_forward: true`, or a stray string — is normalised before the test rather than crashing on `.get`.

---

## Verification

1. A project declaring `carry_forward: {enabled: false}` lists as **configured, no loop** — not wired.
2. The same project passed to `build_agenda.py` exits without building, **and does not inherit the org-level block** by continuing the walk.
3. A project declaring `carry_forward:` with other keys and no `enabled` still lists as wired and still builds — no existing configuration changes behaviour.
4. `carry_forward: true` is tolerated rather than raising.
5. A config with **no** `carry_forward` key lists as **configured, no loop** — absent must not inherit the absent-means-enabled default.

---

## The general shape

**Wherever a config chain permits inheritance, a child must be able to say no — and saying no must not read as yes.** Any `if config.get("feature")` guarding an optional block has this defect the moment an org layer enables the feature above it. The two sites here are the ones that exist today; the pattern is worth recognising in review.
