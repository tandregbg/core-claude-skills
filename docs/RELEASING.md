# Releasing & Privacy Guardrails (CR-026)

This repo is **public**. The vault it operates on is **production data** — real
people, real organizations, real infrastructure. Development runs on that live
data by design (the skills improve by observing real usage), which makes the
boundary between the two non-negotiable. This document is the authoritative
release process; the pre-push guard enforces its privacy half mechanically.

## The prod/dev reality

- **The vault is production.** Everything in it is private by default.
- **This repo is the product.** Everything in it is public by default.
- **The membrane is one-way and narrow:** vault experience flows into the repo
  only through the CR pipeline, rewritten generically. Nothing else crosses.

## Data classification

| May be public (this repo) | Must never be public |
|---|---|
| Generic skill logic, schemas, config shapes | Real personal names (family, contacts, team) |
| Invented example names ("Bob", "Ravi", "David Ekberg") | Customer/venture/org names |
| Generic incident descriptions ("a stray org-level outbox") | Hostnames, internal IPs, ports-with-hosts, mount paths |
| Version numbers, CR numbers, generic titles | Credentials, keys, tokens — in any form |
| The alignment/update runbooks (host-agnostic wording) | Vault folder specifics and audit evidence |
| | Full CR specs (they cite vault evidence) |

**Private CR archive:** the full CR specs live in the operator's private vault,
not in this repo. `docs/proposals/README.md` carries generic title rows only.
`docs/audits/` and `docs/change-requests/` are gitignored (local working
material, never pushed).

## Per-CR release flow

1. **Implement generically** — vault specifics never enter skill text; examples
   use invented names; incident evidence is described by *class*, not instance.
2. **Update the private CR spec to Implemented (version, date) in the same
   working session** — never deferred; a deferred index is a drifted index
   (learned via CR-020).
3. **Bookkeeping in the same commit:** CHANGELOG entry, README what's-new (+
   any affected counts/tables), `ecosystem.yaml` `core_skills_version`, public
   proposals-index row moved to Implemented.
4. **Run `scripts/check-ecosystem-alignment.sh`** — the repo itself must be
   `[OK]` before commit.
5. **Commit** (one release = one commit; no unrelated work mixed in).
6. **Push** — the pre-push guard scans every added line (see below).

## When to push

- Per completed release commit, the same working day. Local-only release
  commits are drift waiting to happen.
- Never push a working tree state you haven't leak-reviewed; the guard is the
  backstop, not the reviewer.

## When to update the webpage and Marvin

- **Trigger:** any `core_skills_version` change. The alignment check — and
  `/ops sweep` check 8 on the maintainer machine — is the scheduled nag.
- **What:** landing page `whats_new` (both languages; the title carries the
  version the alignment script reads), footer version, `BUILD_VERSION`, restart
  exactly the landing app; Marvin's CLAUDE.md version reference + schema notes.
- **How:** the runbook lives in the header of
  `scripts/check-ecosystem-alignment.sh` (CR-023).

## The pre-push guard

Fail-closed hook at `scripts/githooks/pre-push`. Install per clone:

```bash
git config core.hooksPath scripts/githooks
git config guard.denylist /absolute/path/to/private/push-denylist.txt
```

- **Built-in patterns** (public): API-key prefixes, private-key blocks,
  internal IP literals, credential-passing idioms.
- **Private denylist** (in the vault, never in this repo): word-boundary
  regexes for every real identifier — names, orgs, hosts. Extend it whenever a
  new sensitive identifier enters the working vocabulary; it is maintained
  next to the private CR archive.
- **Fail-closed:** no denylist configured → no push.
- **Override:** `git push --no-verify` exists by design — a guard that cannot
  be consciously overridden gets uninstalled. Review the flagged lines first,
  then own the decision.

The guard scans **added lines of the outgoing range** only. It does not
absolve history (what was pushed before the guard existed is a separate
question) and it does not replace rule 1: write generic by construction.
