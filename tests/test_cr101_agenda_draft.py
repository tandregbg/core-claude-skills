"""CR-101: a generated agenda is a draft.

Four gaps that each looked plausible and stacked into an agenda reported as done:
an empty round with no warning, chat counted but never read, pull requests archived
but unread, and closure evidence that took an early claim over a later contradiction.
All data here is invented.
"""

import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OPS = Path(__file__).resolve().parent.parent / "skills" / "ops"
sys.path.insert(0, str(OPS))
import build_agenda as ba  # noqa: E402

NOTE_DAY = "260922"
AFTER = datetime.date(2026, 9, 22)


def build(ops_yaml: str, *, chat_lines=None, repo=None, note_items="- **Android build:** Bob\n", date="260924"):
    """A venture with one project; returns (agenda text, stdout)."""
    vault = Path(tempfile.mkdtemp())
    venture = vault / "venture"
    meetings = venture / "proj" / "meetings"
    meetings.mkdir(parents=True)
    (venture / "proj" / "_ops.yaml").write_text(ops_yaml, encoding="utf-8")
    (meetings / f"{NOTE_DAY}-daily-standup.md").write_text(
        f"# Standup\n\n## Carried forward\n\n{note_items}", encoding="utf-8")
    if chat_lines is not None:
        chat = venture / ".teamschats" / "standup"
        chat.mkdir(parents=True)
        (chat / "_chat.json").write_text(json.dumps({"chat_id": "chat-1"}), encoding="utf-8")
        (chat / "standup-2026-09-23.md").write_text(
            "# Standup — 2026-09-23\n\n" + "".join(
                f"### {hm} — {who}\n\n{body}\n\n" for hm, who, body in chat_lines),
            encoding="utf-8")
    if repo is not None:
        rdir = venture / ".githubmeta" / "app"
        rdir.mkdir(parents=True)
        (rdir / "_repo.json").write_text(json.dumps({"repo": "acme/app", "reads": repo["reads"]}),
                                         encoding="utf-8")
        (rdir / "app-2026-09-24.json").write_text(json.dumps(
            {"day": "2026-09-24", "issues": repo.get("issues", []), "pulls": repo.get("pulls", [])}),
            encoding="utf-8")
    res = subprocess.run([sys.executable, str(OPS / "build_agenda.py"), "--dir", str(meetings),
                          "--date", date], check=True, capture_output=True, text=True)
    build.last_post = (meetings / f"{date}-teams-agenda-daily-standup.md").read_text(encoding="utf-8")
    build.last_meetings = str(meetings)
    return (meetings / f"{date}-agenda-daily-standup.md").read_text(encoding="utf-8"), res.stdout


CF = "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
CHATS = "external_systems:\n  chats:\n    - name: standup\n      id: chat-1\n"
REPOS = "external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"


class Round(unittest.TestCase):
    def test_no_roster_is_said_and_names_the_participants_key(self):
        agenda, out = build(CF + "meeting_types:\n  standup:\n    participants: [Ann, Bob]\n")
        self.assertIn("No roster: `people:` is not declared beside `carry_forward` in _ops.yaml", agenda)
        self.assertIn("meeting_types.<type>.participants`: Ann, Bob", agenda)
        self.assertIn("no roster", out)
        # the participants key is named, never used to fill rows
        self.assertNotIn("| **Ann** |", agenda)

    def test_no_participants_line_without_the_key(self):
        agenda, _ = build(CF)
        self.assertIn("No roster:", agenda)
        self.assertNotIn("Attendees found under", agenda)

    def test_a_roster_gets_no_warning(self):
        agenda, _ = build(CF + "people:\n  - name: Ann\n")
        self.assertNotIn("No roster:", agenda)
        self.assertIn("| **Ann** |", agenda)


class Digest(unittest.TestCase):
    def test_messages_leave_a_marked_slot_and_a_sources_line(self):
        agenda, out = build(CF + CHATS, chat_lines=[("10:00", "Bob", "build 764 distributed")])
        self.assertIn("## Since the last standup — not said in the room", agenda)
        self.assertIn("<!-- DIGEST: 1 messages since 260922 (standup 1). Not yet read. -->", agenda)
        self.assertIn("NOT FILLED", agenda)
        self.assertIn("digest slot", out)
        # facts are prepare's to write; the script never reproduces message text
        self.assertNotIn("build 764 distributed", agenda.split("## Since the last standup")[1].split("##")[0])

    def test_no_messages_no_slot(self):
        agenda, _ = build(CF + CHATS, chat_lines=[])
        self.assertNotIn("<!-- DIGEST:", agenda)


PULLS = [
    {"number": 12, "title": "Android build fix", "state": "MERGED", "createdAt": "2026-09-22T09:00:00Z",
     "updatedAt": "2026-09-23T12:00:00Z", "mergedAt": "2026-09-23T12:00:00Z", "author": {"login": "bob"}},
    {"number": 13, "title": "Settings page", "state": "OPEN", "createdAt": "2026-09-21T09:00:00Z",
     "updatedAt": "2026-09-23T08:00:00Z", "isDraft": False, "reviewDecision": "REVIEW_REQUIRED"},
    {"number": 9, "title": "Old", "state": "OPEN", "createdAt": "2026-09-01T09:00:00Z",
     "updatedAt": "2026-09-10T08:00:00Z"},
]


class Pulls(unittest.TestCase):
    def test_pulls_are_read_when_declared(self):
        agenda, _ = build(CF + REPOS, repo={"reads": ["docs", "pulls", "releases"], "pulls": PULLS})
        self.assertIn("pull request(s) moved since the last note", agenda)
        self.assertIn("*Merged (1)*", agenda)
        self.assertIn("acme/app #13 Settings page", agenda)
        self.assertIn("waiting", agenda)
        self.assertNotIn("#9 Old", agenda)          # not updated since the note
        self.assertNotIn("skipped", agenda)

    def test_skip_note_only_when_neither_is_declared(self):
        agenda, _ = build(CF + REPOS, repo={"reads": ["docs"], "pulls": PULLS})
        self.assertIn("neither issues nor pulls in declared reads", agenda)

    def test_teams_post_counts_merged_and_waiting(self):
        build(CF + REPOS, repo={"reads": ["pulls"], "pulls": PULLS})
        self.assertIn("**Repo since the last note:** 1 merged, 1 awaiting review (oldest", build.last_post)

    def test_pulls_since_classifies(self):
        rows = ba.pulls_since("acme/app", PULLS, AFTER, today=datetime.date(2026, 9, 24))
        by = {r["n"]: r for r in rows}
        self.assertEqual(by[12]["status"], "merged")
        self.assertEqual(by[13]["status"], "awaiting review")
        self.assertEqual(by[13]["age"], 3)
        self.assertNotIn(9, by)


class Evidence(unittest.TestCase):
    ITEM = [("Android build", "Bob")]

    def chat(self, *lines):
        return [{"name": "standup", "messages": [(l[:10], l) for l in lines]}]

    def test_a_newer_negative_cancels_an_older_claim(self):
        chat = self.chat("2026-09-23 10:00 — Bob — Android build is failing, I have fixed and raised a PR",
                         "2026-09-24 09:00 — Bob — Android build issue was not solved after my fix")
        closed, still = ba.probably_closed(self.ITEM, chat, [], [])
        self.assertEqual(closed, [])
        self.assertEqual(still, self.ITEM)

    def test_the_newest_positive_is_the_evidence_and_carries_its_time(self):
        chat = self.chat("2026-09-23 10:00 — Bob — Android build failing again",
                         "2026-09-24 09:00 — Bob — Android build fixed and distributed")
        closed, _ = ba.probably_closed(self.ITEM, chat, [], [])
        self.assertEqual(len(closed), 1)
        kind, ref, txt = closed[0][2]
        self.assertEqual(kind, "chat")
        self.assertIn("2026-09-24 09:00", ref)

    def test_a_merged_pull_request_outranks_chat(self):
        chat = self.chat("2026-09-24 09:00 — Bob — Android build still broken")
        repo = [{"kind": "pull", "repo": "acme/app", "n": 12, "title": "Android build fix",
                 "status": "merged", "when": "2026-09-23T12:00:00Z"}]
        closed, _ = ba.probably_closed(self.ITEM, chat, repo, [])
        self.assertEqual(len(closed), 1)
        self.assertIn("PR #12 merged", closed[0][2][1])

    def test_nothing_is_ever_dropped(self):
        chat = self.chat("2026-09-24 09:00 — Bob — Android build done")
        closed, still = ba.probably_closed(self.ITEM + [("Web copy", "Ann")], chat, [], [])
        self.assertEqual(len(closed) + len(still), 2)


if __name__ == "__main__":
    unittest.main()


class Orient(unittest.TestCase):
    """`/ops orient` reports a generated agenda whose digest is unread as a draft."""

    def brief(self, digest_filled: bool) -> str:
        # the brief's "next session" is the next weekday after the note: 260923
        build(CF + CHATS, chat_lines=[("10:00", "Bob", "build 764 distributed")], date="260923")
        meetings = Path(build.last_meetings)
        agenda = meetings / "260923-agenda-daily-standup.md"
        if digest_filled:
            text = agenda.read_text(encoding="utf-8")
            start = text.index("<!-- DIGEST:")
            end = text.index("-->", start) + 3
            agenda.write_text(text[:start] + "- Build 764 was distributed." + text[end:], encoding="utf-8")
        res = subprocess.run([sys.executable, str(OPS / "project_brief.py"), "--dir", str(meetings)],
                             check=True, capture_output=True, text=True)
        return res.stdout

    def test_unfilled_digest_is_a_draft(self):
        self.assertIn("digest not filled", self.brief(False))

    def test_filled_digest_is_an_agenda(self):
        out = self.brief(True)
        self.assertNotIn("digest not filled", out)
