# CR-091 — The alignment check reads a version that survives a stack change

> **Superseded by CR-089 (v1.79.0, 2026-09-26).** The alignment check now reads the live site's `/version.json`. Renumbered from CR-088, which was taken by the archive fetch record (v1.78.0).

| | |
|---|---|
| **Status** | **Proposed 2026-09-24** |
| **Contract** | none — script behaviour only, no schema change |
| **Date** | 2026-09-24 |
| **Area** | `scripts/check-ecosystem-alignment.sh`, `/ops sweep` check 8 |
| **Related CRs** | CR-023 (alignment check wired into sweep), CR-044/CR-045 (a field nothing read back), CR-078 (`documentation_owner`) |

## What happens

`check-ecosystem-alignment.sh` reads the landing page's build version by grepping a Python file,
and gates the whole check on that file existing:

```bash
LANDING_MOUNT="${LANDING_MOUNT:-$HOME/workspace/remotes/tomas/core-skills-landingpage}"
if [ -f "$LANDING_MOUNT/app.py" ]; then
    LANDING_BUILD=$(grep 'BUILD_VERSION' "$LANDING_MOUNT/app.py" | ...)
    ...
else
    echo "[SKIP] landing page mount not available at $LANDING_MOUNT"
fi
```

The landing page is being rebuilt on a static generator. **There will be no `app.py`.** When it
goes, the check falls into the `else` branch and prints `[SKIP]`, and this script's own header
states what that means:

> A `[SKIP]` (e.g. unreachable mount) means UNVERIFIED, not clean.

So `/ops sweep` check 8 would stop verifying the landing page, and the output line would go on
looking harmless. Nothing fails. Nothing is reported. The component simply leaves the check.

## Why this is the same defect as CR-044

CR-044 corrected a field that sat at `2` for five days and four releases because **nothing read the
value back**. The fix was not to be more careful; it was to make the comparison mechanical.

This is that defect one level out. The check reads a version *through a file path*, so the path is
load-bearing without being declared anywhere. A component may change how it is built — that is its
own business, per `documentation_owner: external` — but it may not silently drop out of the
alignment check by doing so.

## Proposal

**1. Read the version from a surface, not from a source file.**

The landing page already serves `/version`, described in its own source as *"a verification surface:
what the page believes, and where it got it"*:

```json
{"build": "1.11.0", "core_skills_version": "1.77.0", "source": "contract"}
```

That surface survives any stack change, because it is what the component publishes rather than how
it is written. Read it over HTTP when a URL is configured, and fall back to the local build
metadata (`package.json` `version`, or `BUILD_VERSION` in `app.py`) when it is not.

**2. A missing version is a DRIFT, not a SKIP.**

`[SKIP]` should mean *the component was not reachable*. It should not mean *the component was
reachable and its version could not be found*. Those are different facts and only one of them is
acceptable to leave unresolved.

**3. Name the reason in the output.**

`[SKIP] landing page: mount not available at <path>` and `[DRIFT] landing page: reachable, no
version found` are two different lines. Today both produce the first.

## What this does not change

No contract change. No new field. `documentation_owner` stays `this_repo` for the landing page —
this is about how the check reads a component, not about who documents it.

## Evidence

Found 2026-09-24 while planning the landing page's 2.0.0 rebuild, before `app.py` was removed
rather than after. The same session found that the check reports **`4 aligned, 0 drifted`** against
a landing page tree with six real content gaps — three skills declared in the contract and present
on no page of the site, in either language, and a what's-new panel thirty-nine minor releases
stale.

That is not this CR's subject, but it is the same shape and worth recording next to it: **the check
compares version strings, and the version is parameterised, so it cannot detect content drift by
construction.** A second check comparing rendered content against the contract is the subject of a
separate proposal.

## Open question

Whether the fallback should exist at all. A check that only reads `/version` is simpler and fails
honestly when the site is down — but it then requires the network, and this repo's other guarantee
is that the offline path works with no credential and no connectivity. The fallback preserves that
at the cost of two code paths.
