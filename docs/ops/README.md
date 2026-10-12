# Ops — the living operational state

One question, one place: **what is the state now, and what waits for whom?**

| File | What it answers |
|---|---|
| **[ops-status.md](ops-status.md)** | The living board in seven sections: A. production versions / releases, B. feature switches / configuration, C. external accounts and verifications, D. secrets and backups (names and places only), E. decisions waiting for the maintainer, F. operator steps waiting in CRs, G. known open issues |

## Where the plan stands

The CRs are in the [proposals index](../proposals/README.md) (*Proposed*, *Implemented*, *Archived*); releases in
[CHANGELOG.md](../../CHANGELOG.md). `ops-status.md` holds what is released now and every open item with its next
step. core-skills is a sibling of Deep Thought, not a component of it; Deep Thought's own state and plan live in its
repository (`CLAUDE.md`, "Deep Thought").

## How it differs from its neighbours

| Place | Kind | Lifetime |
|---|---|---|
| `docs/ops/` (this) | **State**: what is true now, and the next step for each open item | Edited in place; never dated by filename |
| [`docs/RELEASING.md`](../RELEASING.md) | **Procedure**: how to release, the privacy guardrails | Edited in place |
| [`docs/proposals/`](../proposals/README.md) | **Why and how** a change is made | One per change |
| [`CHANGELOG.md`](../../CHANGELOG.md) | **History**: what each release did | Appended |

`ops-status.md` links out instead of repeating. When a row is closed, delete it (the CHANGELOG or the proposal
already holds the history).

## The rule

**Every release, configuration change or new open item updates `ops-status.md` the same day**: the version rows in
section A after a release, section B when the guard or the contract changes, section G when an issue is found or
fixed. Then re-stamp its "Last verified" line.

Read-only checks that refresh it:

- `head -3 README.md` and the first `## [x.y.z]` in `CHANGELOG.md`: the release;
- `grep -n 'core_skills_version\|contract_version' ecosystem.yaml`: version and contract;
- `scripts/check-ecosystem-alignment.sh`: README, contract, landing page and visualiser in step (`[SKIP]` = unverified);
- `scripts/privacy-scan.sh --tree`: the whole tree against the privacy patterns.
