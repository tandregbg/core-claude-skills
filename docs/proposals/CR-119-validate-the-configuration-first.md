# CR-119 — Validate the configuration first: a decision that changes a project's shape is not done until the config says so

| | |
|---|---|
| **Status** | **Implemented 2026-10-12** |
| **Contract** | additive — no new keys; a `config` line in the sources block, a review slot, an `orient` state |
| **Date** | 2026-10-12 |
| **Area** | `ops` (`config_checks()` in `build_agenda.py`, `build_movement.py` missing labels, `project_brief.py`, `prepare`) |
| **Related CRs** | CR-089 (`/ops status` validates config against the schema, on request), CR-101 (the digest slot), CR-107, CR-114, CR-116, CR-118 |

## What happened

In one week of a running series, decisions changed the project's shape and the config lagged each time: a report
series folded into another (the old source then showed as stale every morning), a milestone date was confirmed (the
card still said *date not set*), and two people joined the meeting without being on the roster. Each was caught only
because the operator remembered it before generating. A reader in the room then asked why a number looked wrong.
**[E]** `/ops status` validates config against the schema, but only on request and never against the project's
decisions.

## Change

1. **Machine checks, every generation** (`config_checks()`), printed as `config` lines in the sources block and, in
   card layout, as **Config: N finding(s)** on the card: milestone date passed or undecided past its decide-by; card
   without a milestone; declared label missing in the repo; declared report not found or ≥3 days old; roster name
   absent from the last three rounds; unknown kind in the last note; definitions terms without a status. The script
   never edits the config.
2. **A judgement step in `prepare`, before generating:** read the decisions since the last agenda, ask of each
   whether it changes the config, propose the edit out loud, make it, regenerate.
3. **A review slot** (`<!-- CONFIG-REVIEW: … -->`) that prepare replaces with *Config reviewed against <decisions>*;
   `/ops orient` reports *generated, config review not stated* while it remains.

## Verified

On a live project the first run found the roster drift that had been carried for days: three roster names absent
from the last three rounds, two of them newly invited.

## Tests

`tests/test_cr119_config_checks.py`.
