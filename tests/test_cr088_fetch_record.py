"""CR-088: an archive says when it was last fetched, and whether that worked.

    python3 -m unittest discover -s tests

The three states a snapshot date alone cannot tell apart -- nothing happened, not
fetched, fetch failed -- each built as a small vault and run through the real
scripts, because the sources block is where a wrong answer reads as a right one.
"""
import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OPS = Path(__file__).resolve().parents[1] / "skills" / "ops"
sys.path.insert(0, str(OPS))
import build_agenda as ba  # noqa: E402

NOTE_DAY = "260922"
NOTE_DATE = datetime.date(2026, 9, 22)


def iso(day: datetime.date, hm: str = "06:30") -> str:
    return f"{day.isoformat()}T{hm}:00+02:00"


class Helpers(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def write(self, payload) -> Path:
        (self.tmp / "_fetch.json").write_text(
            payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
        return self.tmp

    def test_missing_record_is_none_and_says_so(self):
        self.assertIsNone(ba.fetch_record(self.tmp))
        self.assertIsNone(ba.fetch_record(None))
        self.assertEqual(ba.fetch_status(None), "fetch not recorded")

    def test_unknown_result_reads_as_error(self):
        rec = ba.fetch_record(self.write({"result": "splendid"}))
        self.assertEqual(rec["result"], "error")
        self.assertIn("unknown result", rec["detail"])

    def test_unreadable_record_is_an_error_not_an_absence(self):
        rec = ba.fetch_record(self.write("{not json"))
        self.assertEqual(rec["result"], "error")
        self.assertTrue(ba.fetch_status(rec).startswith("fetch failed"))

    def test_auth_required_names_the_fix(self):
        rec = {"result": "auth_required", "last_attempt": iso(NOTE_DATE)}
        self.assertEqual(ba.fetch_status(rec, NOTE_DATE), "fetch failed 06:30: login required")

    def test_ok_shows_last_success(self):
        rec = {"result": "ok", "last_success": iso(NOTE_DATE, "07:00"), "last_attempt": iso(NOTE_DATE, "07:00")}
        self.assertEqual(ba.fetch_status(rec, NOTE_DATE), "fetched 07:00 ok")
        self.assertEqual(ba.fetch_status(rec, NOTE_DATE + datetime.timedelta(days=1)),
                         "fetched 260922 07:00 ok")

    def test_fetched_since_compares_days(self):
        rec = {"result": "ok", "last_success": iso(NOTE_DATE)}
        self.assertTrue(ba.fetched_since(rec, NOTE_DATE))
        self.assertFalse(ba.fetched_since(rec, NOTE_DATE + datetime.timedelta(days=1)))
        self.assertFalse(ba.fetched_since(None, NOTE_DATE))


class Agenda(unittest.TestCase):
    """End to end: a venture with a Jira archive whose newest snapshot predates the note."""

    def build(self, record) -> str:
        vault = Path(tempfile.mkdtemp())
        venture = vault / "venture"
        meetings = venture / "proj" / "meetings"
        meetings.mkdir(parents=True)
        (venture / "proj" / "_ops.yaml").write_text(
            "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
            "external_systems:\n  jira:\n    - project: ABC\n", encoding="utf-8")
        (meetings / f"{NOTE_DAY}-daily-standup.md").write_text(
            "# Standup\n\n## Carried forward\n\n- **Item:** someone\n", encoding="utf-8")
        board = venture / ".jirameta" / "abc"
        board.mkdir(parents=True)
        (board / "_project.json").write_text(json.dumps({"project": "ABC"}), encoding="utf-8")
        (board / "abc-2026-09-20.json").write_text(json.dumps({"day": "2026-09-20", "issues": []}),
                                                   encoding="utf-8")
        if record is not None:
            (venture / ".jirameta" / "_fetch.json").write_text(json.dumps(record), encoding="utf-8")
        subprocess.run([sys.executable, str(OPS / "build_agenda.py"), "--dir", str(meetings),
                        "--date", "260923"], check=True, capture_output=True, text=True)
        return (meetings / "260923-agenda-daily-standup.md").read_text(encoding="utf-8")

    def tickets_line(self, agenda: str) -> str:
        return next(l for l in agenda.splitlines() if l.lstrip().startswith("tickets"))

    def test_failed_fetch_gives_stale_its_reason(self):
        line = self.tickets_line(self.build({
            "source": "jira", "result": "auth_required",
            "last_attempt": iso(datetime.date(2026, 9, 23)),
            "last_success": iso(datetime.date(2026, 9, 20))}))
        self.assertIn("STALE — fetch failed", line)
        self.assertIn("login required", line)

    def test_fetched_after_the_note_is_current_not_stale(self):
        line = self.tickets_line(self.build({
            "source": "jira", "result": "ok",
            "last_attempt": iso(NOTE_DATE, "12:30"), "last_success": iso(NOTE_DATE, "12:30")}))
        self.assertNotIn("STALE", line)
        self.assertIn("read · 0 changed", line)
        self.assertIn("ok", line)

    def test_missing_record_is_printed_never_omitted(self):
        line = self.tickets_line(self.build(None))
        self.assertIn("STALE — fetch not recorded", line)


class Brief(unittest.TestCase):
    def test_a_failed_source_is_reported_first(self):
        vault = Path(tempfile.mkdtemp())
        venture = vault / "venture"
        meetings = venture / "proj" / "meetings"
        meetings.mkdir(parents=True)
        (venture / "proj" / "_ops.yaml").write_text(
            "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
            "external_systems:\n  jira:\n    - project: ABC\n", encoding="utf-8")
        (meetings / f"{NOTE_DAY}-daily-standup.md").write_text(
            "# Standup\n\n## Carried forward\n\n- **Item:** someone\n", encoding="utf-8")
        (venture / ".jirameta").mkdir()
        (venture / ".jirameta" / "_fetch.json").write_text(json.dumps(
            {"result": "auth_required", "last_attempt": iso(NOTE_DATE)}), encoding="utf-8")
        out = subprocess.run([sys.executable, str(OPS / "project_brief.py"), "--dir", str(meetings)],
                             check=True, capture_output=True, text=True).stdout
        lines = out.splitlines()
        self.assertEqual(lines[2].strip(), "Fetch problems")
        self.assertIn("login required", lines[3])
        self.assertIn("fetch tickets", out)


if __name__ == "__main__":
    unittest.main()
