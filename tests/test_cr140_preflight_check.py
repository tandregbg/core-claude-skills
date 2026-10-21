"""CR-140: `build_agenda.py --check` is a pre-flight -- one table of source states,
non-zero on any stale or missing source, and fast enough for a scheduler.

The full build takes about three minutes, so a check that needs the build to find a
missing source finds it three minutes late. Each state is built as a small vault and
run through the real script, because a pre-flight that reports READY over a broken
source is worse than no pre-flight. Invented data.

    python3 -m unittest discover -s tests
"""

import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

OPS = Path(__file__).resolve().parents[1] / "skills" / "ops"
sys.path.insert(0, str(OPS))
import build_agenda as ba  # noqa: E402
import build_movement as bm  # noqa: E402

NOTE_DAY = "260922"
NOTE_DATE = datetime.date(2026, 9, 22)
CF = "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"


def iso(day: datetime.date, hm: str = "06:30") -> str:
    return f"{day.isoformat()}T{hm}:00+02:00"


def vault(ops_yaml: str, notes: dict[str, str] | None = None):
    """A venture with one project; returns (venture, meetings folder)."""
    venture = Path(tempfile.mkdtemp()) / "venture"
    meetings = venture / "proj" / "meetings"
    meetings.mkdir(parents=True)
    (venture / "proj" / "_ops.yaml").write_text(ops_yaml, encoding="utf-8")
    if notes is None:
        notes = {NOTE_DAY: "- **Payment retry** — #12 · **Bob**\n"}
    for d, items in notes.items():
        (meetings / f"{d}-daily-standup.md").write_text(
            f"# Standup\n\n## Carried forward\n\n{items}" if items is not None else "# Standup\n",
            encoding="utf-8")
    return venture, meetings


def check(meetings: Path):
    return subprocess.run([sys.executable, str(OPS / "build_agenda.py"),
                           "--dir", str(meetings), "--check"],
                          capture_output=True, text=True)


def rows(meetings: Path, today: datetime.date | None = None, reports=None):
    """check_rows against the same config chain the script resolves."""
    cf = ba.config(meetings.resolve())
    pat = ba.note_pattern(cf["note_suffix"])
    hist = sorted((m.group(1), p) for p in meetings.glob("*.md")
                  if (m := pat.match(p.name)) and not any(c in p.name for c in ba.COMPANION))
    return ba.check_rows(cf, meetings, hist, today or NOTE_DATE, reports=reports)


def state_of(table, source):
    return next((r[1] for r in table if r[0] == source), None)


class TheTable(unittest.TestCase):
    def test_a_good_fetch_and_a_written_note_are_ready_and_exit_zero(self):
        venture, md = vault(CF + "external_systems:\n  chats:\n    - id: c1\n      name: Team\n")
        (venture / ".teamschats").mkdir()
        (venture / ".teamschats" / "_fetch.json").write_text(json.dumps(
            {"result": "ok", "last_success": iso(NOTE_DATE), "last_attempt": iso(NOTE_DATE)}),
            encoding="utf-8")
        t = rows(md)
        self.assertEqual(state_of(t, "chat fetch"), ba.READY)
        self.assertEqual(state_of(t, "previous note"), ba.READY)
        res = check(md)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("source(s) ready", res.stdout)

    def test_a_failed_fetch_is_failed_not_stale(self):
        venture, md = vault(CF + "external_systems:\n  chats:\n    - id: c1\n      name: Team\n")
        (venture / ".teamschats").mkdir()
        (venture / ".teamschats" / "_fetch.json").write_text(json.dumps(
            {"result": "auth_required", "last_attempt": iso(NOTE_DATE),
             "last_success": iso(NOTE_DATE - datetime.timedelta(days=2))}), encoding="utf-8")
        t = rows(md)
        self.assertEqual(state_of(t, "chat fetch"), ba.FAILED)
        self.assertIn("login required", next(r[3] for r in t if r[0] == "chat fetch"))
        self.assertEqual(check(md).returncode, 1)

    def test_a_fetch_that_last_worked_before_the_note_is_stale(self):
        venture, md = vault(CF + "external_systems:\n  repos:\n    - url: github.com/acme/app\n")
        (venture / ".githubmeta").mkdir()
        (venture / ".githubmeta" / "_fetch.json").write_text(json.dumps(
            {"result": "ok", "last_success": iso(NOTE_DATE - datetime.timedelta(days=1)),
             "last_attempt": iso(NOTE_DATE - datetime.timedelta(days=1))}), encoding="utf-8")
        self.assertEqual(state_of(rows(md), "repository fetch"), ba.STALE)
        self.assertEqual(check(md).returncode, 1)

    def test_no_fetch_record_at_all_is_missing(self):
        _venture, md = vault(CF + "external_systems:\n  jira:\n    - project: ABC\n")
        t = rows(md)
        self.assertEqual(state_of(t, "ticket fetch"), ba.MISSING)
        self.assertEqual(check(md).returncode, 1)

    def test_an_undeclared_source_gets_no_row(self):
        _venture, md = vault(CF)
        names = [r[0] for r in rows(md)]
        self.assertNotIn("chat fetch", names)
        self.assertNotIn("repository fetch", names)
        self.assertNotIn("ticket fetch", names)

    def test_a_note_with_no_carry_forward_section_is_a_missing_close_out(self):
        _venture, md = vault(CF, {NOTE_DAY: None})
        t = rows(md)
        self.assertEqual(state_of(t, "previous note"), ba.MISSING)
        self.assertIn("close-out not written", next(r[3] for r in t if r[0] == "previous note"))
        self.assertEqual(check(md).returncode, 1)

    def test_no_note_at_all_is_a_row_not_a_refusal(self):
        """A check whose own preconditions refuse it cannot be what a scheduler runs."""
        _venture, md = vault(CF, {})
        res = check(md)
        self.assertEqual(res.returncode, 1)
        self.assertIn("previous note", res.stdout)
        self.assertIn("missing", res.stdout)

    def test_the_recording_source_is_checked_or_not_checked_and_neither_fails(self):
        _venture, md = vault(CF + "external_systems:\n  transcripts:\n    store: a store\n")
        t = rows(md)
        self.assertEqual(state_of(t, "recording source"), ba.UNCHECKED)
        self.assertEqual(check(md).returncode, 0)   # not a failure, so not an exit code

    def test_the_table_has_a_source_a_state_and_a_time_column(self):
        venture, md = vault(CF + "external_systems:\n  chats:\n    - id: c1\n      name: Team\n")
        (venture / ".teamschats").mkdir()
        (venture / ".teamschats" / "_fetch.json").write_text(json.dumps(
            {"result": "ok", "last_success": iso(datetime.date.today(), "07:15"),
             "last_attempt": iso(datetime.date.today(), "07:15")}), encoding="utf-8")
        out = check(md).stdout
        self.assertIn("Source", out)
        self.assertIn("State", out)
        self.assertIn("Time", out)
        self.assertIn("07:15", out)


class Reports(unittest.TestCase):
    """Report rows, with the states injected so no network is touched."""

    def test_a_three_day_old_report_is_stale(self):
        _venture, md = vault(CF)
        t = rows(md, reports=[("Status report", "Bob", "docs/260919-status.md", 3)])
        self.assertEqual(state_of(t, "report: Status report"), ba.STALE)
        self.assertEqual(next(r[2] for r in t if r[0] == "report: Status report"), "3d old")

    def test_a_report_updated_today_is_ready(self):
        _venture, md = vault(CF)
        t = rows(md, reports=[("Status report", None, "docs/status.md", 0)])
        self.assertEqual(state_of(t, "report: Status report"), ba.READY)
        self.assertEqual(next(r[2] for r in t if r[0] == "report: Status report"), "today")

    def test_a_report_that_was_not_found_is_missing(self):
        _venture, md = vault(CF)
        t = rows(md, reports=[("Board status", None, None, None)])
        self.assertEqual(state_of(t, "report: Board status"), ba.MISSING)

    def test_a_report_whose_date_could_not_be_read_is_missing_not_fresh(self):
        _venture, md = vault(CF)
        t = rows(md, reports=[("Board status", None, "status.md", None)])
        self.assertEqual(state_of(t, "report: Board status"), ba.MISSING)

    def test_a_declared_report_series_needs_no_repository_history(self):
        """One status call per report, never `load()`: the check must stay in seconds."""
        _venture, md = vault(CF + "external_systems:\n  repos:\n    - url: github.com/acme/app\n"
                                  "      reports:\n        - name: Status report\n"
                                  "          current: docs/status.md\n")
        cf = ba.config(md.resolve())
        calls = []
        orig = bm._gh
        bm._gh = lambda args: (calls.append(args), "2026-09-22T08:00:00Z\n")[1]
        try:
            states, problems = bm.report_states(cf, NOTE_DATE)
        finally:
            bm._gh = orig
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "api")
        self.assertNotIn("issue", " ".join(calls[0]))
        self.assertEqual(problems, [])
        self.assertEqual(states[0][0], "Status report")
        self.assertEqual(states[0][3], 0)

    def test_an_unreadable_report_is_failed_never_guessed_at_as_missing(self):
        _venture, md = vault(CF + "external_systems:\n  repos:\n    - url: github.com/acme/app\n"
                                  "      reports:\n        - name: Status report\n"
                                  "          current: docs/status.md\n")
        cf = ba.config(md.resolve())
        orig = bm._gh

        def boom(_args):
            raise RuntimeError("gh api: not authenticated")
        bm._gh = boom
        try:
            states, problems = bm.report_states(cf, NOTE_DATE)
        finally:
            bm._gh = orig
        self.assertEqual(states, [])
        self.assertEqual(len(problems), 1)
        t = ba.check_rows(cf, md, [(NOTE_DAY, md / f"{NOTE_DAY}-daily-standup.md")],
                          NOTE_DATE, reports=states)
        self.assertNotIn("report: Status report", [r[0] for r in t])


class RenamedDirectory(unittest.TestCase):
    """A renamed folder reads as config stale, not source missing."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.proj = self.root / "org" / "proj"
        self.proj.mkdir(parents=True)
        self.reports = self.root / "org" / "board" / "status-reports-2026"
        self.reports.mkdir(parents=True)
        (self.reports / "260925-board-status.md").write_text("x", encoding="utf-8")

    def test_the_sibling_sharing_a_word_is_suggested(self):
        self.assertEqual(bm.renamed_to(self.proj, "../board/status-reports"),
                         "../board/status-reports-2026")

    def test_a_declared_directory_that_exists_is_not_second_guessed(self):
        self.assertIsNone(bm.renamed_to(self.proj, "../board/status-reports-2026"))

    def test_a_sibling_sharing_nothing_is_not_suggested(self):
        (self.root / "org" / "board" / "minutes").mkdir()
        self.assertIsNone(bm.renamed_to(self.proj, "../board/agendas"))

    def test_a_missing_parent_gives_no_suggestion(self):
        self.assertIsNone(bm.renamed_to(self.proj, "../nowhere/status-reports"))

    def test_the_vault_report_line_says_config_stale_and_names_the_path(self):
        cf = {"_root": self.proj, "ext": {"vault_reports": [
            {"name": "Board status", "dir": "../board/status-reports",
             "pattern": r"^\d{6}-board-status\.md$"}]}}
        lines, states = bm.vault_reports(cf, datetime.date(2026, 9, 26))
        self.assertIn("NOT FOUND", lines[0])
        self.assertIn("config stale?", lines[0])
        self.assertIn("../board/status-reports-2026", lines[0])
        self.assertIsNone(states[0][2])   # still missing: the suggestion decides nothing

    def test_the_check_table_carries_the_same_suggestion(self):
        _venture, md = vault(CF + "external_systems:\n  vault_reports:\n    - name: Board status\n"
                                  "      dir: ../board/status-reports\n"
                                  "      pattern: '^\\d{6}-board-status\\.md$'\n")
        reports = md.parent.parent / "board" / "status-reports-2026"
        reports.mkdir(parents=True)
        (reports / "260925-board-status.md").write_text("x", encoding="utf-8")
        res = check(md)
        self.assertEqual(res.returncode, 1)
        line = next(l for l in res.stdout.splitlines() if "Board status" in l)
        self.assertIn("missing", line)
        self.assertIn("config stale?", line)
        self.assertIn("../board/status-reports-2026", line)


class FailedFetchInTheHeader(unittest.TestCase):
    """CR-140 proposal 4: on a NORMAL build too, not only in the fetch's own file."""

    def build(self, record) -> str:
        venture, md = vault(CF + "external_systems:\n  jira:\n    - project: ABC\n")
        board = venture / ".jirameta" / "abc"
        board.mkdir(parents=True)
        (board / "_project.json").write_text(json.dumps({"project": "ABC"}), encoding="utf-8")
        (board / "abc-2026-09-20.json").write_text(
            json.dumps({"day": "2026-09-20", "issues": []}), encoding="utf-8")
        if record is not None:
            (venture / ".jirameta" / "_fetch.json").write_text(json.dumps(record), encoding="utf-8")
        subprocess.run([sys.executable, str(OPS / "build_agenda.py"), "--dir", str(md),
                        "--date", "260923"], check=True, capture_output=True, text=True)
        return (md / "260923-agenda-daily-standup.md").read_text(encoding="utf-8")

    def test_the_header_names_the_failed_fetch(self):
        a = self.build({"result": "auth_required", "last_attempt": iso(datetime.date(2026, 9, 23)),
                        "last_success": iso(datetime.date(2026, 9, 20))})
        head = a[:a.index("---")]
        self.assertIn("Fetch failed", head)
        self.assertIn("tickets", head)
        self.assertIn("login required", head)
        self.assertIn("last good data", head)

    def test_a_working_fetch_adds_no_warning(self):
        a = self.build({"result": "ok", "last_success": iso(datetime.date(2026, 9, 23)),
                        "last_attempt": iso(datetime.date(2026, 9, 23))})
        self.assertNotIn("Fetch failed", a)

    def test_a_missing_record_is_not_a_failed_fetch(self):
        """Not recorded and failed are different states; only one goes in the header."""
        self.assertNotIn("Fetch failed", self.build(None))


class DatedReportFilenames(unittest.TestCase):
    """CR-140 fix: both dated spellings, because the house convention is YYMMDD.

    `report_states()` first copied `build()`'s 4-digit-year regex, so every report
    named by the house convention yielded age None -- and `--check` cannot tell
    fresh from stale without an age. That is the one question it exists to answer.
    """

    def test_both_spellings_are_read(self):
        self.assertEqual(bm.filename_date("261021-status.md"), datetime.date(2026, 10, 21))
        self.assertEqual(bm.filename_date("2026-10-21-status-report.md"),
                         datetime.date(2026, 10, 21))

    def test_a_letter_suffixed_house_name_is_read(self):
        """The documented vault_reports pattern allows `261021a-board-status.md`."""
        self.assertEqual(bm.filename_date("261021a-board-status.md"),
                         datetime.date(2026, 10, 21))

    def test_an_undated_or_impossible_name_stays_undated(self):
        self.assertIsNone(bm.filename_date("status.md"))
        self.assertIsNone(bm.filename_date("261332-status.md"))   # month 13: not a date
        self.assertIsNone(bm.filename_date(""))

    def test_a_six_digit_series_in_a_repo_gets_an_age(self):
        """The defect itself: today's report read as undated, so never as fresh."""
        cf = {"_root": Path(tempfile.mkdtemp()),
              "ext": {"repos": [{"url": "github.com/acme/app", "reports": [
                  {"name": "Weekly status", "dir": "docs/status",
                   "pattern": r"^\d{6}-status\.md$"}]}]}}
        orig = bm._gh
        bm._gh = lambda _args: json.dumps(["261019-status.md", "261021-status.md"])
        try:
            states, problems = bm.report_states(cf, datetime.date(2026, 10, 21))
        finally:
            bm._gh = orig
        self.assertEqual(problems, [])
        self.assertEqual(states[0][2], "docs/status/261021-status.md")
        self.assertEqual(states[0][3], 0)

    def test_the_check_table_calls_that_report_ready_not_missing(self):
        _venture, md = vault(CF)
        t = rows(md, today=datetime.date(2026, 10, 21),
                 reports=[("Weekly status", None, "docs/status/261021-status.md", 0)])
        self.assertEqual(state_of(t, "report: Weekly status"), ba.READY)

    def test_a_six_digit_vault_series_gets_an_age_too(self):
        root = Path(tempfile.mkdtemp())
        d = root / "board" / "status"
        d.mkdir(parents=True)
        (d / "261019-status.md").write_text("x", encoding="utf-8")
        cf = {"_root": root, "ext": {"vault_reports": [
            {"name": "Board status", "dir": "board/status",
             "pattern": r"^\d{6}-status\.md$"}]}}
        _lines, states = bm.vault_reports(cf, datetime.date(2026, 10, 21))
        self.assertEqual(states[0][3], 2)


class OneZoneForOneReport(unittest.TestCase):
    """CR-140 fix: the pre-flight reads a commit date in the zone `build()` uses.

    Reading it in the machine's zone instead let the two disagree about the same
    report across the stale boundary -- the disagreement this function exists to
    prevent.
    """

    def states(self, tz, when):
        cf = {"_root": Path(tempfile.mkdtemp()),
              "movement": ({"tz": tz} if tz else {}),
              "ext": {"repos": [{"url": "github.com/acme/app", "reports": [
                  {"name": "Status report", "current": "docs/status.md"}]}]}}
        orig = bm._gh
        bm._gh = lambda _args: when
        try:
            return bm.report_states(cf, datetime.date(2026, 10, 21))[0]
        finally:
            bm._gh = orig

    def test_the_declared_zone_decides_the_day(self):
        """22:30 UTC on the 20th is the 21st in Stockholm and the 20th in UTC."""
        when = "2026-10-20T22:30:00Z\n"
        self.assertEqual(self.states("Europe/Stockholm", when)[0][3], 0)
        self.assertEqual(self.states("UTC", when)[0][3], 1)

    def test_the_zone_matches_what_build_reads(self):
        """Same declaration, same key: `carry_forward.movement.tz`."""
        mv = {"tz": "Pacific/Kiritimati"}
        when = "2026-10-21T00:30:00Z\n"
        age_check = self.states(mv["tz"], when)[0][3]
        tz = ZoneInfo(mv["tz"])
        age_build = (datetime.date(2026, 10, 21) - bm._ts(when.strip()).astimezone(tz).date()).days
        self.assertEqual(age_check, age_build)


class CurrentAndPatternTogether(unittest.TestCase):
    """CR-140 fix: a report declaring both is ONE report, reported as `build()` does."""

    def test_both_declared_gives_the_current_state_once(self):
        cf = {"_root": Path(tempfile.mkdtemp()), "movement": {"tz": "UTC"},
              "ext": {"repos": [{"url": "github.com/acme/app", "reports": [
                  {"name": "Status report", "current": "docs/status.md",
                   "dir": "docs/status", "pattern": r"^\d{6}-status\.md$"}]}]}}
        calls = []
        orig = bm._gh
        bm._gh = lambda args: (calls.append(args), "2026-10-21T08:00:00Z\n")[1]
        try:
            states, problems = bm.report_states(cf, datetime.date(2026, 10, 21))
        finally:
            bm._gh = orig
        self.assertEqual(problems, [])
        self.assertEqual(len(states), 1, states)       # one declaration, one row
        self.assertEqual(states[0][2], "docs/status.md")
        self.assertEqual(states[0][3], 0)
        self.assertEqual(len(calls), 1)                # and still one call per report

    def test_the_state_is_the_one_build_would_report(self):
        """`build()` appends the series state only when there is no `current:` path."""
        src = (OPS / "build_movement.py").read_text(encoding="utf-8")
        self.assertIn('if not r.get("current"):', src)


class RecordingArchiveIsResolved(unittest.TestCase):
    """CR-140 fix: "checked" means the archive was found, not merely declared."""

    def test_a_declared_archive_that_exists_is_checked(self):
        venture, md = vault(CF + "external_systems:\n  transcripts:\n"
                                 "    store: a store\n    archive: .records\n")
        (venture / ".records").mkdir()
        t = rows(md)
        self.assertEqual(state_of(t, "recording source"), "checked")
        self.assertEqual(check(md).returncode, 0)

    def test_a_declared_archive_that_is_not_there_is_missing(self):
        _venture, md = vault(CF + "external_systems:\n  transcripts:\n"
                                  "    store: a store\n    archive: .recrods\n")
        t = rows(md)
        self.assertEqual(state_of(t, "recording source"), ba.MISSING)
        self.assertIn("not found", next(r[3] for r in t if r[0] == "recording source"))
        self.assertEqual(check(md).returncode, 1)

    def test_no_archive_declared_is_still_not_checked_and_still_not_a_failure(self):
        _venture, md = vault(CF + "external_systems:\n  transcripts:\n    store: a store\n")
        self.assertEqual(state_of(rows(md), "recording source"), ba.UNCHECKED)
        self.assertEqual(check(md).returncode, 0)


class RenameSuggestionEdges(unittest.TestCase):
    """CR-140 fixes to `renamed_to()`: the year suffix, and the nearest-parent decoy."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.proj = self.root / "org" / "proj"
        self.proj.mkdir(parents=True)

    def test_a_year_appended_with_no_separator_is_suggested(self):
        """`reports` -> `reports2026`: the commonest form this rename takes."""
        (self.root / "org" / "board").mkdir()
        (self.root / "org" / "board" / "reports2026").mkdir()
        self.assertEqual(bm.renamed_to(self.proj, "../board/reports"),
                         "../board/reports2026")

    def test_a_shared_year_alone_suggests_nothing(self):
        """Two folders both carrying 2026 are not the same series renamed."""
        (self.root / "org" / "board").mkdir()
        (self.root / "org" / "board" / "minutes2026").mkdir()
        self.assertIsNone(bm.renamed_to(self.proj, "../board/agendas2026"))

    def test_the_declared_directory_in_a_higher_parent_beats_a_nearer_decoy(self):
        """A suggestion is read as an answer, so it must not point away from the
        folder that was there all along."""
        (self.proj / "board").mkdir()                       # nearer parent
        (self.proj / "board" / "status-decoy").mkdir()
        (self.root / "org" / "board").mkdir()               # higher parent
        (self.root / "org" / "board" / "status-reports").mkdir()
        self.assertIsNone(bm.renamed_to(self.proj, "board/status-reports"))

    def test_a_rename_in_a_higher_parent_is_still_suggested(self):
        (self.root / "org" / "board").mkdir()
        (self.root / "org" / "board" / "status-reports-2026").mkdir()
        self.assertEqual(bm.renamed_to(self.proj, "board/status-reports"),
                         "board/status-reports-2026")


class Documented(unittest.TestCase):
    def test_skill_documents_check_and_the_background_run(self):
        t = (OPS / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("--check", t)
        self.assertIn("exits non-zero", t)
        self.assertIn("background", t)


if __name__ == "__main__":
    unittest.main()
