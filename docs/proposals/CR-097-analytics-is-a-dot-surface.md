# CR-097 — Analytics snapshots live in `.analytics/`, not `_analytics/`

| | |
|---|---|
| **Status** | **Implemented 2026-09-26, v1.83.0** — contract 34 |
| **Contract** | **not additive** (33 → 34) — one declared path renamed; readers accept the old path for one release |
| **Date** | 2026-09-26 |
| **Area** | `vault_conventions` (`vault_root`, `output_artifacts`, the prefix convention's examples), `/analytics`. Outside this repo: the dashboard (it reads the snapshots) |
| **Related CRs** | CR-031 (`/analytics pipeline`, created the folder), CR-034 (the prefix answers read frequency), CR-089 (`_PLAN-*` removed from the same example list for the same reason) |

## What happened

CR-034 settled what a prefix means: **underscore = read in everyday work, dot = read rarely, on
demand, or never.** Who writes a surface is a separate property and never a reason for a prefix.

`_analytics/` fails that test:

- **Readers** (as declared): the dashboard and the user, on demand. No skill reads it.
- **Content**: dated snapshots — a vault overview, skill adoption, contact engagement, pipeline and
  backlog reports — written when someone runs `/analytics`, with older ones moved to `.archive/`.
  Archive material, not a working surface.

The folder predates the rule: it was created in 1.33 (CR-031), and CR-034 (1.36) listed it among the
underscore examples without applying the test to it. CR-089 found the same thing about `_PLAN-*` in
the same list.

**It also leaks into the everyday read path.** The snapshots are named `YYMMDD-*.md` — the pattern
the skills use to find notes when they walk folders. A walk skips dot folders by rule; it does not
skip underscore folders. `/analytics` itself carries an explicit exception so as not to count its own
output, which is the kind of special case a dot prefix makes unnecessary.

## Proposal

1. **The path is `.analytics/`.** `/analytics` writes there; its archive is `.analytics/.archive/`.
2. **`vault_conventions`**: the `vault_root` entry and `output_artifacts` name `.analytics/`, and the
   prefix convention's underscore examples drop `_analytics/`. It is a DORMANT dot surface
   (present, rarely read, safe to read on demand) — not blocked.
3. **One release of both.** A reader looks in `.analytics/` first and falls back to `_analytics/`.
   `/analytics` offers to move an existing `_analytics/` on its next run rather than writing to both.
4. **Readers that walk the vault never enter it** — by the existing dot rule, with no exception to
   maintain. A reader that wants the snapshots opens `.analytics/` by name.

## Outside this repo

| Where | What |
|---|---|
| The dashboard | Read `.analytics/` by name, fall back to `_analytics/` for one release |
| A vault | Move `_analytics/` → `.analytics/` once; update any hand-written index that lists it |

## What this does not do

- Change what `/analytics` measures or writes.
- Touch `_inbox/`, `_outbox/` or any other underscore surface — each is read routinely.
- Rename any snapshot.

## Acceptance

- `ecosystem.yaml`: contract 34; `.analytics/` declared; no `_analytics/` in `vault_conventions` or
  `output_artifacts`.
- `/analytics` documents `.analytics/` everywhere, with the one-release fallback and the move offer.
- The dashboard shows the snapshots from `.analytics/`, and still from `_analytics/` if not yet moved.
- The alignment check passes.

## Outcome (2026-09-26, v1.83.0)

Implemented as proposed: `/analytics` (paths, the move offer, the one-release fallback, the
path-classification row), `vault_conventions` (`.analytics/` declared DORMANT; removed from the
underscore examples and added to the dot examples), `output_artifacts`, README and the skills
comparison. The dashboard reads `.analytics/` and falls back to `_analytics/`.

**At implementation, another session was writing the snapshots** — the vault's `_analytics/` had
been written minutes earlier. The folder was moved only once it had been quiet, so the move could not
split a run between two paths.
