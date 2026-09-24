# CR-081 — One messaging role, several implementations

| | |
|---|---|
| **Status** | Proposed — deliberately thin, reserves a shape rather than specifying a build |
| **Contract** | additive, `components:` note only — no new component, no new key |
| **Date** | 2026-09-24 |
| **Area** | `components: messaging client`, archive naming |
| **Related CRs** | **CR-068** (`.chats/` → `.teamschats/`: the provider names the folder), **CR-055** (`.githubmeta/`, the sibling pattern), CR-064 (a dispatching surface may write `external_systems.chats`), CR-080 (email and calendar as source types) |

## The problem, which is small and already half-solved

`components: messaging client` is declared generically — *"Talks to a chat platform"*, kind
*"library plus CLI"*. The role was written to be provider-neutral and is.

Its `writes:` is not: `<venture>/.teamschats/`. One role, one hardcoded archive path.

That was correct when there was one implementation, and CR-068 made it *more* correct by moving
the provider's name out of a falsely generic `.chats/` and into the path. But it leaves the
component declaring something it should not: **a role that names one provider's archive is a role
with one seat.**

When a second messaging channel arrives — iMessage, SMS, WhatsApp — there is no stated answer to
where its archive goes, so the answer gets invented at implementation time. CR-068 exists because
exactly that happened once already.

## The change

Three sentences, none of which require code today.

1. **`messaging client` is a role with many implementations, not one.** Its `writes:` lists an
   archive *pattern*, not a path: `<venture>/.<provider>chats/`. The existing `.teamschats/`
   is one instance of the pattern and does not move.

2. **A new channel names its provider in its folder**, per CR-068's rule — `.imessages/`,
   `.whatsapp/`. The rule already exists and was paid for; this states that it applies forward,
   so the next implementation does not re-litigate it.

3. **`external_systems.chats` stays generic.** CR-068 settled this explicitly: the config key
   names a *class* of system, the path names a *writer*. Recorded here because it is the exact
   thing a reader of point 2 is likely to change by mistake.

## The open question this does not answer

**Does a personal messaging channel sit per venture, or per person?**

`.teamschats/` sits under `<venture>/` because a Teams chat *is* organisational — it belongs to
the workplace whose tenant carries it. iMessage and SMS are not organised that way. A thread with
one person spans every context that person appears in, and a venture folder is the wrong container
for it — while a contact folder is the wrong container for a group chat.

This is left open on purpose. It is a structural decision with no reversible answer, the same
class as CR-080's routing question, and it should be settled by a real case rather than in
advance. **Stating it as open is the point** — an unstated assumption here would be inherited
silently by whatever is built first.

## Why file it now rather than with the implementation

Because the implementation belongs somewhere else. These clients live in `vault-tools`, and a
channel added there against an unstated shape is how `.chats/` got its name.

A placeholder costs one paragraph in `components:` and removes the chance that the next channel
invents a fourth naming convention. That is the entire value being claimed; nothing here makes
anything work that did not work before.

## Scope / non-goals

- **Proposes no implementation.** Not iMessage, not SMS, not WhatsApp. No scopes, no API, no
  fetcher, no schedule.
- **Moves nothing.** `.teamschats/` keeps its path, its writer and its readers.
- **Adds no component and no config key.** The role exists; this widens how it is described.
- **Does not decide the per-venture / per-person question.** Named above as open, deliberately.
