# CR-161 -- A vault item can say that it is one person's own, and no skill quotes it into a shared surface

| | |
|---|---|
| **Status** | **Proposed** (2026-10-26) |
| **Contract** | additive -- two optional front-matter keys on `_inbox/` items, one declared dormant sub-surface. No existing path is renamed, no writer loses a surface |
| **Date** | 2026-10-26 |
| **Area** | `ecosystem.yaml` (`vault_conventions`, contract bump), `ops` (`check`), `transcript`, `insights`, `outbox` (the three skills that could quote an item into something shared) |
| **Related CRs** | CR-160 (`.deepthought/` as an archive surface; **this CR depends on it for the surface itself**), CR-010 (vault conventions), CR-034 (`_` and `.` prefixes), CR-036 (placement and singletons), CR-038 (generated-view isolation); platform side: DT-CR-843 (the tree and the two layers), DT-CR-838 (the vault layout), DT-CR-740 part B (contract v1) |
| **Depends On** | CR-160. Platform contract v2 (DT-CR-843) must be published; until then the keys are optional and absent |

## Problem

The platform now writes items into a vault, and a vault may belong to one person (a Mac) or be one account's folder on the server. The platform separates what the account **shares** from what is one person's **own** (`layer: shared | member`, DT-CR-843). core-skills has no such concept. `/transcript`, `/insights` and `/outbox` read an item and may quote it into a summary, a knowledge note or an outgoing document. If an item is a person's private recording and the note is then placed in a folder the account shares, a private statement has crossed a boundary the platform worked to keep.

The same tools must also run **unchanged** in both homes: the server's per-account vault under `~/deep-thought-external-data/<user>/` and a person's local vault. Nothing may assume a host, a path or a user.

## Proposed Solution

1. **Two optional keys on an `_inbox/` item's front matter, declared in `ecosystem.yaml`:** `layer` (`shared` or `member`) and `owner` (a platform username). They sit beside the four keys the platform contract fixes (`source_id`, `tags`, `language`, `updated`), which are not renamed. **Absent means "not declared": no layer rule applies to the item** (today's behaviour). The platform writes `layer: member` only for material it knows to be one person's own; since the platform lets every member read every source in an account today (DT-CR-778), almost every item is `shared` and carries no key at all. Reading an absent key as `member` would block almost everything for no reason.
2. **The quoting rule, in the skills that write notes:** an item with an explicit `layer: member` is never quoted, summarised or named in anything written to a surface the vault declares shared (`_outbox/` items addressed to others, notes under a shared project folder, `.knowledge/`). It may feed the person's own private notes. An item with `layer: shared` may feed either. `check` reports a note that cites a `member` item and sits on a shared surface.
3. **`.deepthought/member/` is declared a dormant dot surface** (the same level as `.deepthought/` from CR-160): present, not read unattended, safe to read on request. It holds the person's own profile and ledgers written by the platform. No skill writes it.
4. **`_context.md` stays the platform's.** The shared account context is written by the client under `<root>/` exactly as in contract v1; the member profile is not written there. `CONTEXT.md` stays the human's and is never written.
5. **Host independence, as a check:** `ops check` fails a vault whose configuration names an absolute host path outside the vault root, and a skill must resolve the vault root by the existing upward walk only. The test fixture is two vaults, one laid out as the server's per-account folder and one as a person's local vault, and every skill gives the same results on both.

## Out of scope

Reading the platform (the contract is one-way). Deciding which layer a platform source belongs to (the platform decides; this CR only honours it). Changing how `/transcript` names notes (the vault's conventions win, as in contract v1 section 6). Any write to `.deepthought/`.

## Testing Plan

1. `ecosystem.yaml` validates with `layer` and `owner` declared; an item with `layer: other` is reported.
2. An item without `layer` is not restricted (no rule applies); an item with `layer: member` is refused a shared destination.
3. A note citing a `layer: member` item and placed on a shared surface is reported by `check`; the same note on a private surface is not.
4. `.deepthought/member/` is listed as a dormant surface, never walked by an unattended pass.
5. The same test vault, laid out as a server per-account folder and as a local vault, gives identical `check` and skill results.
6. `/outbox` refuses to attach a `member` item to a message addressed outside the vault's owner.

## Risk

| Risk | Mitigation |
|---|---|
| The rule is bypassed by a skill that does not know it | `check` reports the citation, not only the write; the three skills named above are the ones that quote |
| Over-blocking: a person cannot use their own recordings in their own notes | `member` items feed private surfaces freely; only shared destinations are refused |
| The platform adds a third layer later | the key is an enum with an `unknown -> member` default |

## Open questions

1. Which surfaces are "shared" in a vault? Recommendation: declared in `ecosystem.yaml` per vault (`shared_surfaces:`), default `_outbox/` and any folder the human marks; nothing implicit.
2. Does `owner` have to match the vault's user for a `member` item to be usable at all? Recommendation: yes on a server vault; ignore on a local vault with one user.
