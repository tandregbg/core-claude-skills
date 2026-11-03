# CR-167 — A company profile says what it is not

| | |
|---|---|
| **Area** | `skills/company/SKILL.md` (the opening, beside *Open and optional*), `skills/company/references/contract.md` (the opening statement, **not** section 7) |
| **Priority** | Medium |
| **Status** | **Implemented v1.93.0** (2026-11-03) |
| **Contract** | None. Documentation only — no schema, no new field, no behaviour change |
| **Related CRs** | **CR-125** (the profile and its open contract — this states a property CR-125 built but never claimed), **CR-126** (`export deep-thought`) and **CR-130** (`export agent-core`) both touch `skills/company`, but only `export` and **contract.md section 7**; this CR deliberately stays out of that section so the three do not collide |

Marks: **[E]** observed in the repository · **[H]** not yet run.

---

## The problem

`/company` says what it **is**: structure, no questions, an optional template read from
`company.template:`, nine facets, a skeleton that works without a template **[E]**.

It never says what it is **not**, and the omission has become expensive now that
self-described context files are a product category in the open market. A reader who has met the
general idea — *describe your voice, your process, what you know, and where it is used, then save
the files* — will assume `/company` is the same kind of thing. The difference is large and is
nowhere stated:

| | A self-described profile | What `/company` builds **[E]** |
|---|---|---|
| Where the content comes from | What the author remembers and chooses to say, once | Sources, with `sources:` recorded per facet |
| What happens when it ages | Nothing; it is as true as the day it was written | `/company check` reports drift against the sources |
| What happens where material is missing | The assistant fills the gap or the author guesses | The gap is written as a gap and stays visible |
| How much there is | One pass | Levels, from a profile built only from what is already public up to the full platform |
| Who decides it is good enough | The author | A quality gate, external to the skill |

Every row on the right already works. **None of it is claimed**, so the skill is read as the
weaker thing it resembles.

This matters in two directions. Outward, the one durable property — *source-backed with provenance
and a drift check* — is the property nothing else in the category has, and it is invisible.
Inward, a person who does not know the profile is source-backed will hand-edit it, which is the
exact failure the orientation set already warns about (*"a correction made by hand is invisible to
everything that maintains the file"*) **[E]**.

## The change

**One paragraph in `SKILL.md`**, directly after *Open and optional*, stating the distinction in the
skill's own voice. Short, and with no comparison to any named product or method — the claim is about
what this skill does, and it reads as weaker, not stronger, if it leans on someone else being worse:

> **Source-backed, not self-described.** A facet file is built from sources and records them: every
> statement can be traced to where it came from, `check` reports when the sources have moved on, and
> a fact nobody has is written as a gap rather than filled in. A profile written once from memory is
> a different object with the same filename — it is as true as the day it was written and has no way
> to say so.

**One sentence in `references/contract.md`**, in the opening statement rather than any numbered
section, so that a reader of the contract meets the property before the file formats.

### Not in scope

- Any change to the facets, the levels, the gate or the template interface. The template is not part
  of this repository and this CR does not reach into it.
- Section 7 of `contract.md` (the export targets) — reserved for CR-126 and CR-130.
- Naming any external method, product or person. The repository is public; a comparison to a named
  competitor does not belong in it, in this skill or anywhere else.

## Verification

| Check | State |
|---|---|
| Every row of the table above is true of the shipped skill | **[E]** for sources, `check`, gaps and levels; **[H]** for the exact wording of each, which should be read back against `contract.md` before merge |
| The paragraph names no external product, method or person | **[E]** by construction; re-read at merge, and the pre-push guard is the backstop |
| `contract.md` section 7 is untouched | **[E]** by construction — the collision check that motivated the placement |
| No behaviour, schema or test changes | **[E]** by construction |

**One sentence was added at the merge [E].** Reading the skill back for row 1 showed that where a fact
exists only in what a person says, `/company` accepts it — and records it as a dated `interview:<date>`
source (intake step 4). A paragraph claiming only *built from sources* would have been read as refusing
that input. The shipped paragraph says it: *"Where the only source is a person, that is recorded too — an
owner's answer is a dated `interview:<date>` source, not an unmarked fact."* This is the same finding that
sent CR-168 back for a rewrite, met from the other side.

One open question for the merge **[H]**: whether the same paragraph belongs in the landing page's
company-profile route, which has its own hand-written copy. It probably does, but that is the landing
repository's change and its own release.
