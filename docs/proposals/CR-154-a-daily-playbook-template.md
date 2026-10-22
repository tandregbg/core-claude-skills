# CR-154 — A daily-meeting playbook template: the generic page every project's team can start from

| | |
|---|---|
| **Status** | **Proposed** (2026-10-22) |
| **Contract** | additive — a template file and one pointer in the `ops` skill; no behaviour change |
| **Date** | 2026-10-22 |
| **Area** | `ops` (SKILL.md step 9, a new `templates/daily-playbook.md`), `ops-config` (a `playbook:` pointer, optional) |
| **Related CRs** | CR-148 (the compact card layout), CR-147 (carried lines re-read), CR-140 (a pre-flight check), CR-107 (the card) |

## What happened

A project's team page about its daily meeting ("how the daily works") was written in the first week and never revised.
By the fifth week it described a bug sheet and a registry that no longer existed, a recap posted every day that is now
written on request, a three-sentence round that had become four lines, and nothing about attendance, who verifies the
dates, or what to do after the meeting. The operator rewrote it from scratch on a single morning, in one page of
checklists, from the decisions the project had accumulated (about thirty).

Reading the result, almost all of it is not about the project at all: the four parts of the meeting, what to say in your
minute, what a participant must do to attend, what goes wrong when someone is absent silently, the rules about assignees
and failed fixes, the roles. What belongs to the project is a handful of names, a few decision numbers and the label
words. A convention that lives in one project's folder is not a convention.

## Proposal

1. **A template, `skills/ops/templates/daily-playbook.md`**, one page, in checklists, with the project's own parts as
   placeholders. The body is in the appendix below.
2. **The `ops` skill points to it** from step 9 (the agenda): a project that runs a daily series is offered the template
   once, at set-up (`/ops new` for a series), and fills it from its own config (`people:` roles, labels, time, tracker).
3. **The placeholders are read from the config where possible**: the leader and the verifier from `people:`; the labels
   from `labels:`; the time from the series' schedule. What cannot be read is left as a visible blank, not guessed.
4. **The page says what it is built on**: the words come from the organisation's standards page; the meeting shape is
   whichever layout the project declares (`card` or `compact`, CR-148). A line at the top says when a described shape is
   a trial the tooling does not yet produce.
5. **A staleness check** (CR-140's pre-flight can carry it): the playbook's last-edited date against the project's
   decision register. More than N new decisions since the page was edited produces a one-line note.

## Appendix — the template body

```markdown
# How the daily works — playbook

**For everyone in the daily.** One page. {{status line: suggestion / agreed, date}}. The calendar invite is the truth for the time.

## 1. The meeting: {{minutes}} minutes, four parts
| Part | Minutes | What happens |
| Milestones | 2 | The leader reads the dated list. The verifier ({{verifier}}) asks whether any date is unrealistic. |
| Blockers | 5 | Everything labelled `{{blocker_label}}`. To fix first; fixed, waiting for a test under its own heading. |
| The round | {{n}} | One minute each. |
| Close | 3 | Read back the decisions and who owns each, then what carries to tomorrow with a name on each. |
There is no separate section for dependencies or decisions: they come out of the milestones and your minute.

## 2. Attendance — {{required / expected}}
- Everyone named in the invite attends every working day. {{who is not in it, and where they meet}}
- Can't attend? Say so before {{time}} in {{channel}}: that you are out, what you are blocked on or owe, and who can speak for it.
- Your items do not wait for you. Late is fine. Planned leave: tell the channel a day ahead.
- The leader follows up a missed day with a question, not a verdict.

## 3. Your minute
1. What moved. 2. What you are stuck on, and who holds the other end (you raise a dependency; if you did not, you were
not dependent). 3. What you owe. 4. What you need decided. "Nothing" is a real answer.

## 4. Before and after
Before: read the post; open your assigned blockers and criticals; know whether you depend on someone.
After: every issue and pull request has an assignee; a failed fix returns to its assignee with the fixed label removed;
a test leaves a note; the label is the truth.

## 5. Roles
| Role | Who | Does |  (leader, verifier, status author, testers, repository triage)

## 6. Where things go
| What | Where |  (bugs and work, backend work, decisions, recaps, security findings)
```

## Acceptance

- A new project series offered the template at set-up produces a page with its leader, verifier and labels filled and
  every unknown left as a visible blank.
- A playbook not edited while the decision register has grown by more than N entries is reported once, not repeatedly.

## Not in scope

The content of any organisation's rules. The template carries structure and the generic rules above; an organisation's
own words and decisions are the project's to add.
