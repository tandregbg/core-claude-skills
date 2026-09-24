# CR-077 — The orientation layer: render what the contract already knows

| | |
|---|---|
| **Status** | Proposed |
| **Contract** | additive (25 → 26) |
| **Date** | 2026-09-23 |
| **Area** | `ecosystem.yaml` (`vault_conventions`), landing page `/guide`, README, `/ops help` |
| **Related CRs** | **CR-078** (the ownership boundary this CR's scope section applies — see note below), CR-034 (prefix conventions), CR-036 (placement classes), CR-010 (vault conventions), CR-062 (working_loop rendered from the contract), CR-026 (privacy boundary) |

## What happened

Two onboardings on consecutive days. The installation worked — it builds the structure and it
builds it well. Then every question was about what the structure *is*:

- *"What is inbox and outbox?"*
- Claude started in the home directory and searched outside the vault.
- A speaker was corrected and the material was never reprocessed, so extraction and tagging
  stayed built on the wrong speaker — and nothing showed the error.
- Pasted material was not fenced, which is the whole defence against a pasted instruction being
  read as an instruction.

Each of these takes seconds to explain out loud, which is exactly why none of them was written
down. **The person who built the system never reads its documentation, so the gap is invisible
from the inside.**

## The finding, stated precisely

The `/guide` page exists and has eight sections. Measured against what the sessions exposed, it
mentions `_inbox` zero times, `_outbox` zero times, prompt injection zero times, and context
windows in passing.

**That is not a missing document. It is a document answering the second question.** The guide
teaches *the loop* — process a meeting, build a routine, track tasks. Every observed failure was
about *the substrate*: which folders are read, which are sealed, what is in the context window,
where a session starts.

A person cannot run the loop before they can read the room.

## Why this is a contract change and not a page rewrite

**The facts already exist in `ecosystem.yaml`.** `vault_conventions.vault_root` declares each
surface with its purpose, writers, readers and lifecycle. `rules.prefix_conventions` states the
dot-versus-underscore test in one line. `rules.single_inbox_outbox` is an invariant. Nothing about
these needs discovering — they need *rendering somewhere a new user looks*.

CR-062 settled the precedent: `working_loop` lives in the contract and both the README and the
landing page render it, **because a hand-written copy in each is two things to keep true.** The
README's release list went seventeen versions stale proving the point.

So writing an orientation page by hand would create a third copy of facts the contract already
owns, and it would drift the same way.

## Proposed

**1. `orientation:` in `ecosystem.yaml`** — an ordered list of the concepts a person needs before
the loop makes sense. Each entry: `id`, `question` (the user's own words), `answer` (two or three
sentences), and `sources` (the `vault_root` paths or `rules` ids it derives from).

The initial set, every one of them observed:

| id | The question as asked |
|---|---|
| `where_to_start` | Where do I start a session, and why does it matter? |
| `inbox_outbox` | What are inbox and outbox? |
| `dot_vs_underscore` | Why do some folders start with a dot? |
| `sealed_surfaces` | What is `.transcripts/`, and how do I get the raw text when I need it? |
| `context_window` | New window or resume — when do I want which? |
| `pasted_material` | How do I paste something safely? |
| `structure_grows` | Does the structure have to be right from the start? |
| `correcting_data` | How do I fix something that is wrong? |

**2. Render it everywhere the loop is already rendered.** `working_loop` has four renderers —
README, landing page, `/ops help` and Marvin — from one declaration. Orientation takes the same
path, and each surface renders it in its own idiom rather than restating it:

| Renderer | How orientation appears |
|---|---|
| Landing page `/guide` | A section ahead of the existing eight, in both languages |
| README | A short block with a link |
| **`/ops help`** | Before the loop — a person who types `help` is more likely to be lost in the substrate than in the sequence |
| Marvin | As the dispatching surface's own idiom decides |

**`/ops help` is the renderer most easily forgotten and the one that matters most**, for the reason
already written into that command: a help command is read precisely by people who cannot tell that
it is wrong. The same logic that forbids a hand-written loop there requires a rendered orientation
there.

**3. The answers carry the *why*, not only the *what*.** *"`.transcripts/` is sealed"* does not
survive contact with a user who wants the raw text. *"The summary is the truth; the raw material
is the audit trail behind it, and it is not read back into new documents — ask explicitly when you
need it"* does.

## The two answers this CR fixes rather than documents

**`structure_grows`.** A user stalled trying to phrase a dictation correctly *"so it works for the
structure."* Nothing anywhere says structure is discovered rather than declared up front. One
sentence removes a whole class of paralysis.

**`correcting_data`.** The principle is *fix it with an instruction, not by editing the file* —
say the thing that is wrong and let the skill update the YAML. A user who opens `_meta.yaml` by
hand has been failed by the documentation, not by the format.

## Scope / non-goals

- **Nothing product-specific.** Recording, speaker assignment, reprocessing and cloud access belong
  to the product that does them, not to core-skills. This CR is only the vault substrate. (See
  CR-078 for the boundary, which this CR's scope section already assumes.)
- **No README per folder.** A permanent explanatory file living inside `_inbox/` contradicts
  *"a door, not a home"* — the inbox would carry furniture that is never processed.
- **No new page.** `/guide` exists; orientation goes at the top of it. A second page competes with
  the first and one of them goes stale.
- **No renderer restates the block.** Each presents the declared entries in its own idiom — the
  rule `/ops help` already carries for `working_loop`. A renderer that paraphrases is a copy.
- Does not change any declared surface, writer, reader or lifecycle. Additive: a rendering of
  facts already in the contract.

## A note on order (added 2026-09-24)

CR-078 is filed as depending on this CR. In implementation the dependency runs the **other way**:
this CR's scope section already invokes CR-078's rule — *documentation belongs to the component
that owns the behaviour* — to decide which of the eight orientation answers belong here at all.

Write the eight answers before that boundary is settled and some of them will be written against
a rule that later excludes them. **Settle CR-078's rule first** (it is prose in `components:` plus
`RELEASING.md`), then write orientation against a decided boundary. The formal `depends_on` in
CR-078 is about the *renderer* existing; this note is about the *content* being decidable.

## Privacy note (CR-026)

Orientation copy is written from real onboarding sessions, which makes it exactly the place a
borrowed name slips into a public repo. **Every example name must be invented and added
consciously to `scripts/githooks/allowed-examples.txt`** — write the example first, allowlist it
second, never the reverse. No organisation, product or person from the source sessions appears in
the rendered text.
