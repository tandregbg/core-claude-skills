# How the daily works — playbook

**For everyone in the daily.** One page. {{status: "Suggestion, <date>" or "Agreed <date>"}}. The calendar invite is the truth for the time.
{{trial note, if the meeting shape described below is a trial the tooling does not yet produce: say so in one line}}

## 1. The meeting: {{minutes}} minutes, four parts

| Part | Minutes | What happens |
|---|--:|---|
| **Milestones** | 2 | The leader reads the dated list. The **verifier** ({{verifier}}) asks whether any date is unrealistic. Anyone can raise a hand. |
| **Blockers** | 5 | Everything labelled `{{blocker label}}` in {{tracker}}. *To fix* first; *fixed, waiting for a test* under its own heading. Is this the list? Anything missing? |
| **The round** | {{minutes left}} | One minute each. See section 3. |
| **Close** | 3 | The leader reads back the decisions and who owns each one, then what carries to tomorrow, each with a name. |

There is no separate section for dependencies or decisions: they come out of the milestones and your minute.

## 2. Attendance — {{required / expected}}

- **Everyone named in the invite attends every working day.** {{who is not in the invite, and where they meet instead}}
- **Can't attend? Say so before {{time}} in {{channel}}:** that you are out, what you are blocked on or owe, and who can speak for it. A silent absence is the one thing we do not accept.
- **Your items do not wait for you.** The leader lists them as *absent*; the person who holds the other end speaks for them.
- **Late is fine; join and take your minute when asked.** Planned leave: tell the channel a day ahead.
- The leader follows up a missed day in a short message afterwards. It is a question, not a verdict.

## 3. Your minute

Four lines, in this order. If a line does not apply, skip it. "Nothing" is a real answer and costs ten seconds.

1. **What moved** since yesterday: what landed, not what you worked on.
2. **What you are stuck on, and who holds the other end.** *You* raise a dependency. If you did not raise it here, you were not dependent, and "I was waiting for this" afterwards is a failure.
3. **What you owe:** what is waiting on you.
4. **What you need decided.**

Do not read your status, and do not say what you will do anyway. Disagree in the room.

## 4. Before and after

**Before (two minutes):** read the post; open your assigned `{{blocker label}}` and `{{critical label}}` issues; know whether you depend on someone.

**After, every day:**

- Every issue and pull request has an **assignee**. Asking for a review means assigning the reviewer.
- **A fix that fails:** the tester removes the `{{fixed label}}` label and the issue goes back to its assignee.
- **A test leaves a note** on the issue: what was tried and what happened.
- {{where work that touches another team's system is filed, and who owns it}}
- **The label is the truth.** Nothing is a blocker unless it is labelled. If you think it is, label it and say so; if it stops being one, remove the label.

## 5. Roles

| Role | Who | Does |
|---|---|---|
| Leader | {{leader}} | Runs the agenda and the close |
| Milestone verifier | {{verifier}} | Checks the dates every day |
| Status author | {{status author}} | One current status, ready {{when}} |
| Testers | {{testers}} | Verify fixes; leave notes |
| Repository triage | {{per repository: who}} | {{any repository with no one named is listed here as "not named yet"}} |

## 6. Where things go

| What | Where |
|---|---|
| A bug or product work | {{tracker and repository}} |
| Work in another team's system | {{tracker, and how the two are linked}} |
| A decision | Said in the daily; the leader records it in {{the decision register}} |
| A recap | {{when it is written, and where the standard is}} |
| A security finding | {{where it is reported: not in the chat or the recap}} |

If the agenda or a note gets your work wrong, say so in the chat. The record is corrected, not defended.
