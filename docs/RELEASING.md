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
6. **Semantic release review (CR-028, mandatory).** The pattern guard cannot judge meaning — a new customer name or a describable private situation passes every regex. Before pushing, read `git diff origin/main..HEAD` (added lines) against the classification table above and answer three questions: *Does any added line name or identify a real person, organization, or deal not on the invented-examples list? Does any example look copied from real data rather than invented? Does any incident description reveal the situation it came from rather than its class?* Any "yes" → rewrite generically and add the identifier to the private denylist so the mechanical guard knows it next time. Record the verdict in the push decision. (Live proof of why this step exists: a history audit found three real contact slugs in old example blocks that the denylist had never heard of.)
7. **Push** — the pre-push guard scans every added line (see below).

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
- **Invented-examples allowlist (CR-029)** — the inversion that makes "never
  reveal" watchable: real names can't all be enumerated, but allowed FAKE ones
  can. Every name-like token (contact slugs, dated send-slugs, Name-Name
  filename pairs, `display_name` values) must fully match
  `scripts/githooks/allowed-examples.txt` (public — it contains only invented
  names). The pre-push guard blocks unknown tokens; `scripts/privacy-scan.sh
  --tree` watches the whole tree on the weekly sweep. Adding an allowlist
  line is a conscious act: confirm the name is invented, never borrowed.
- **Fail-closed:** no denylist configured → no push (full mode).
- **Guard modes (CR-030):** `git config guard.mode secrets-only` gives other
  repos a lighter regime — keys/tokens/private-key blocks only — for PRIVATE
  repos whose legitimate content includes infra details the full patterns
  would false-positive on. All GitHub-remoted repos on a dev machine should
  carry at least secrets-only; public repos carry full. Install by pointing
  `core.hooksPath` at this repo's `scripts/githooks`.
- **Override:** `git push --no-verify` exists by design — a guard that cannot
  be consciously overridden gets uninstalled. Review the flagged lines first,
  then own the decision.

The guard scans **added lines of the outgoing range** only. It does not
replace rule 1 (write generic by construction) or the semantic review
(step 6) — it is the mechanical floor, not the ceiling.

## Development-evolution material is local-only (CR-028)

Everything the evolution loop produces from vault data stays in the vault:
CR specs (private archive), audits (gitignored + private archive), the
denylist (vault), and **generated skill proposals** — `/insights propose`
writes to `workflows.knowledge_extraction.evolution.proposals_path`
(vault-relative; default `.skill-evolution/proposals/`), never into this
repo. The repo receives only the *implemented, genericized* result of
evolution, through the flow above.

## Server-side backstop + history

- **GitHub secret scanning + push protection** are enabled on the repo —
  they catch known secret formats even from a clone where the local guard
  was never installed. They do NOT know the private denylist (and must
  not); local guard + semantic review remain the identifier defense.
- **History was audited once** (2026-07-10): every added line of every
  commit scanned against the denylist + patterns. Zero secrets ever
  committed; a handful of real-name example slugs found and genericized at
  HEAD (history rewrite deliberately declined — low sensitivity, high
  disruption; decision recorded in the private CR archive).
- **Fresh clones:** the local guard activates per clone (two `git config`
  lines above). Until then, only the server-side scanning applies —
  install the guard before your first push.
