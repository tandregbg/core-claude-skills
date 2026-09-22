# CR-071: A project has more than one chat — retrieval reads one of them

| Field | Value |
|-------|-------|
| **CR Number** | CR-071 |
| **Date** | 2026-09-22 |
| **Author** | User + Claude Code |
| **Status** | **Implemented** in v1.71.2 (2026-09-22), after the in-flight `from_chat` rewrite landed in v1.71.1 |
| **Priority** | Medium-High |
| **Complexity** | Low |
| **Estimated Scope** | `skills/ops/build_agenda.py` (`from_chat`) and the `/ops` SKILL.md retrieval section. **`project_brief.py` is already correct** — see change 4 |
| **Related CRs** | CR-054 (`external_systems`), CR-047 (chat archive), CR-058 (pre-meeting retrieval), CR-067 (same silent-failure shape) |
| **Contract** | Written against contract_version 23 |
| **Breaking Changes** | No |

---

## Executive Summary

**The schema already holds a list. The reader takes one item from it.**

```python
# build_agenda.py
chats = cf.get("ext", {}).get("chats") or []
c = next((x for x in chats if x.get("default")), chats[0])
```

Every other declared chat is dropped — no warning, no "skipped", nothing in the output. The agenda's *"Since the last standup — not said in the room"* block is then **complete-looking and partial**, which is the property that makes it expensive: a reader has no way to tell that a second conversation exists.

**This is the same failure shape as CR-067** (a disabled block read as enabled) and as the archive-directory rename being fixed in the same function right now, whose comment states the principle exactly: *"a retrieval block that goes quiet after a rename looks exactly like a chat with no traffic."* A retrieval step that silently reads a subset is indistinguishable from one that read everything and found little.

**Observed:** a project running its work across two chats, with one declared. The second is invisible to the agenda, to the facilitator sheet built from it, and to `/ops brief`'s archive-freshness block.

---

## The design error underneath

**`default:` is a *send* concept, reused for *reading*.**

CR-054 introduced `external_systems.chats` because a recap's destination was being chosen by recognising a name out of seventy live chats. Marking one entry `default: true` answers *"where does this project post?"* — and that question has exactly one answer.

**Reading has no default.** If a project's work happens across two chats, the pre-meeting question is *"what was said anywhere that bears on this session?"* — and the answer is all of them. There is no sense in which one chat is the default thing to have read.

So one field carries two meanings, and the retrieval side inherited a constraint that only the dispatch side needs.

---

## Proposed changes

### 1. `from_chat` reads every declared chat

Iterate `chats`, resolve each by platform id against the archive as now, merge the results **chronologically** rather than concatenating per chat — a meeting's context is a timeline, not a set of transcripts.

`default:` keeps its meaning for dispatch and **stops meaning anything for retrieval**.

### 2. Label the source when more than one chat is declared

With one chat, an unlabelled line is unambiguous and the label is noise. With two, an unlabelled merged list silently implies a single conversation, and a reader cannot tell a decision in the standup chat from one in a side channel.

**Label only when it disambiguates** — the same rule the round-table applies to owners.

### 3. A declared chat missing from the archive is reported per chat

Today the missing case returns `["declared chat not in the archive: <name>"]` **as the function's entire output**. With two chats that behaviour is wrong twice over: one missing chat would either replace the other's real content or vanish into it.

Each declared chat resolves independently; a miss becomes one line beside the others' content, not instead of it. **A skipped source that announces itself is honest; a silent one looks like an empty result** — `/ops` already states this rule for the repo `reads:` scope, and it should hold here.

### 4. `/ops brief` needs no change — and shows the intended shape

Checked: `project_brief.py` already iterates (`for c in ext.get("chats") or []`) and reports newest snapshot **per declared chat**. It is correct today, and it is the reference for what `from_chat` should do — two readers of the same declaration disagreeing about whether it is a list is the actual defect.

---

## Adjacent finding: the archiver fetches meeting threads only

Declaring a real project's chats surfaced a second gap, independent of the reader bug.

Teams carries two kinds of thread, and the id shows which:

| Form | Kind |
|------|------|
| `19:meeting_<base64>@thread.v2` | chat attached to a recurring meeting |
| `19:<hex>@thread.v2` | standing group chat, no meeting behind it |

A venture archive checked on 2026-09-22 held **35 chats, all of them meeting threads, and no group
chat at all**. The project's UI/UX discussion is a standing group chat, so no amount of fixing
`from_chat` would surface it: **there is nothing archived to read.**

This matters because the two gaps compound in the same direction. A collapsed reader drops a chat it
was told about; an archiver that fetches one kind of thread drops a chat nobody can tell it about.
Both end in a retrieval block that looks complete.

**Out of scope for this CR** -- the archiver is a separate component (CR-047) and the cause is not
yet confirmed to be a filter rather than, say, permissions. Filed here so the next person reading
`declared chat not in the archive` against a correct id does not go looking in `from_chat`.

### Resolved, 2026-09-22 (teams-chat-cli 0.4.4)

**A filter, not permissions.** The chat was reachable the whole time: read live, it returned its
topic and its messages on the first try. The sweep called `list_chats(all_types=args.all_types)`
with that flag defaulting to false, which kept `chatType == "meeting"` client-side. `--all-types`
had always existed, so nothing was ever unfetchable -- the archive was empty because no run had
asked for it.

Worth recording because the evidence pointed the other way: 35 of 35 archived chats being meeting
threads reads as an inability to fetch group chats, and it was a default.

A sweep now takes **meeting threads and named group chats** (`ARCHIVED_BY_DEFAULT`). One-on-ones
stay out -- private correspondence, and dozens landing in a vault is not a sweep's decision -- as do
unnamed group chats, which have nothing to name a folder. Thirteen named group chats came into scope
on the live tenant.

The UI/UX chat now holds 44 days of history back to June. Verified after: this project's brief
resolves all three declared chats, and `from_chat` reads **150 messages with zero retrieval
failures** where it previously read 12 of 218.

---

## Not proposed

- **Discovering chats.** A tool may read what is declared and must never append a chat it happened to see. CR-054's hand-written property is the point: *"a tool may read it but must never append what it happened to use — that would turn an accident into a declaration."*
- **Changing `default:`.** It stays, and stays meaningful for dispatch.
- **A per-chat `reads:` scope.** The repo declaration has one because a repository exposes several separable surfaces; a chat is one stream.

---

## Verification

1. A project declaring two chats produces a retrieval block containing messages from **both**, in date order.
2. With two or more declared, each line names its source; with one, no label appears.
3. A declared chat absent from the archive produces **one line saying so**, alongside the other chat's content rather than replacing it.
4. A project declaring one chat behaves exactly as today.
5. `/ops brief` is unchanged and still reports freshness per declared chat (regression check only).

---

## Why this is not implemented yet

`from_chat` is being rewritten in the working tree as this is filed — archive-directory naming and how chat content reaches the agenda. **Landing a second change to the same function from a different session is how two correct fixes produce one broken one.** The CR is filed now so the finding is not lost; implementation waits for that work to land.
