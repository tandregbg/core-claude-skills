"""CR-139: the agenda defaults to today, and a series can declare days it does not meet.

The default used to be "the next scheduled day after the newest note", which is only
right when the series meets every scheduled day and every meeting is written up the
same day. After a day nobody met it built for the skipped day. All data here is
invented.

    python3 -m unittest discover -s tests
"""

import datetime
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OPS = Path(__file__).resolve().parent.parent / "skills" / "ops"
sys.path.insert(0, str(OPS))
import build_agenda as ba  # noqa: E402

CF = "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
ROSTER = "people:\n  - name: Bob\n  - name: Ravi\n"
ITEMS = "- **Payment retry** — #12 · **Bob**\n"


def project(ops_yaml: str, notes: dict[str, str] | None = None):
    """A venture with one project and the notes named; returns the meetings folder."""
    venture = Path(tempfile.mkdtemp()) / "venture"
    meetings = venture / "proj" / "meetings"
    meetings.mkdir(parents=True)
    (venture / "proj" / "_ops.yaml").write_text(ops_yaml, encoding="utf-8")
    for d, items in (notes or {}).items():
        (meetings / f"{d}-daily-standup.md").write_text(
            f"# Standup\n\n## Carried forward\n\n{items}", encoding="utf-8")
    return meetings


def run(meetings: Path, *args):
    """The generator, exit code and output kept -- the refusals are the subject here."""
    return subprocess.run([sys.executable, str(OPS / "build_agenda.py"), "--dir", str(meetings), *args],
                          capture_output=True, text=True)


def ymd(d: datetime.date) -> str:
    return d.strftime("%y%m%d")


class TodayIsTheDefault(unittest.TestCase):
    def test_no_date_builds_for_today_not_the_day_after_the_note(self):
        today = datetime.date.today()
        note = ymd(today - datetime.timedelta(days=4))
        md = project(CF + ROSTER, {note: ITEMS})
        res = run(md)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((md / f"{ymd(today)}-agenda-daily-standup.md").exists())
        # the old default -- the next day after the note -- is not what was built
        self.assertFalse((md / f"{ymd(today - datetime.timedelta(days=3))}-agenda-daily-standup.md").exists())

    def test_default_target_is_today(self):
        d = datetime.date(2026, 10, 21)
        self.assertEqual(ba.default_target(d, [], None), "261021")

    def test_an_explicit_date_still_wins(self):
        today = datetime.date.today()
        note = ymd(today - datetime.timedelta(days=4))
        later = ymd(today + datetime.timedelta(days=2))
        md = project(CF + ROSTER, {note: ITEMS})
        self.assertEqual(run(md, "--date", later).returncode, 0)
        self.assertTrue((md / f"{later}-agenda-daily-standup.md").exists())


class TheCloseOutRunWantsTheNextSession(unittest.TestCase):
    """The loop has two runs with no `--date` and they want different dates.

    The morning run builds for today. The same-day close-out -- SKILL.md, *After the
    meeting, the same day*, step 5 writes today's summary and step 9 then runs this
    generator -- wants the NEXT session. A note for today is the signal that the
    close-out has happened, so it resolves rather than refuses: refusing it broke the
    documented sequence, which passes no `--date`.
    """

    def hist(self, *days):
        return [(d, Path(f"{d}-daily-standup.md")) for d in days]

    def test_a_note_for_today_moves_the_default_to_the_next_session(self):
        # 261021 is a Wednesday; with no cadence declared the next weekday is 261022
        self.assertEqual(ba.default_target(datetime.date(2026, 10, 21), self.hist("261021")), "261022")

    def test_the_declared_cadence_is_honoured_by_the_moved_default(self):
        got = ba.default_target(datetime.date(2026, 10, 21), self.hist("261021"), ["mon", "fri"])
        self.assertEqual(got, "261023")

    def test_a_note_for_a_day_that_is_not_today_leaves_the_default_alone(self):
        self.assertEqual(ba.default_target(datetime.date(2026, 10, 21), self.hist("261020")), "261021")

    def test_the_morning_run_with_no_note_for_today_builds_today(self):
        today = datetime.date.today()
        md = project(CF + ROSTER, {ymd(today - datetime.timedelta(days=1)): ITEMS})
        res = run(md)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((md / f"{ymd(today)}-agenda-daily-standup.md").exists())

    def test_the_close_out_run_right_after_todays_summary_builds_the_next_session(self):
        # the documented flow end to end: today's summary is written, the generator is
        # run with no --date, and the next session's agenda is what lands
        today = datetime.date.today()
        md = project(CF + ROSTER, {ymd(today - datetime.timedelta(days=1)): ITEMS,
                                   ymd(today): ITEMS})
        res = run(md)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        nxt = ba.next_session(ymd(today), None)
        self.assertTrue((md / f"{nxt}-agenda-daily-standup.md").exists())
        self.assertFalse((md / f"{ymd(today)}-agenda-daily-standup.md").exists())

    def test_the_close_out_run_is_built_from_todays_note(self):
        today = datetime.date.today()
        md = project(CF + ROSTER, {ymd(today - datetime.timedelta(days=1)): ITEMS,
                                   ymd(today): ITEMS})
        self.assertEqual(run(md).returncode, 0)
        nxt = ba.next_session(ymd(today), None)
        head = (md / f"{nxt}-agenda-daily-standup.md").read_text(encoding="utf-8").split("---")[0]
        self.assertIn(f"Base: {ymd(today)}-daily-standup.md", head)


class Refusals(unittest.TestCase):
    """A past date nobody typed, and a date that is not a date."""

    def hist(self, *days):
        return [(d, Path(f"{d}-daily-standup.md")) for d in days]

    def test_a_past_date_nobody_typed_is_refused_and_names_the_flag(self):
        now = datetime.date(2026, 10, 21)
        why = ba.refuse_target("261019", now, [], explicit=False)
        self.assertIn("earlier than today (261021)", why)
        self.assertIn("--date 261019", why)

    def test_an_explicit_past_date_is_the_caller_saying_they_mean_it(self):
        now = datetime.date(2026, 10, 21)
        self.assertIsNone(ba.refuse_target("261019", now, [], explicit=True))

    def test_an_explicit_date_with_a_note_is_honoured_as_the_contract_says(self):
        # the CR's contract is that an explicit --date behaves as before, and before
        # the CR this built: deleting the agenda and rebuilding is how one is corrected
        now = datetime.date(2026, 10, 21)
        self.assertIsNone(ba.refuse_target("261021", now, self.hist("261020", "261021"), explicit=True))
        self.assertIsNone(ba.refuse_target("261020", now, self.hist("261020"), explicit=True))

    def test_a_malformed_date_says_so(self):
        self.assertIn("not a YYMMDD date",
                      ba.refuse_target("2026-10-21", datetime.date(2026, 10, 21), [], explicit=True))

    def test_an_explicit_date_with_a_note_builds_end_to_end(self):
        today = datetime.date.today()
        md = project(CF + ROSTER, {ymd(today): ITEMS})
        res = run(md, "--date", ymd(today))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue((md / f"{ymd(today)}-agenda-daily-standup.md").exists())

    def test_the_existing_output_guard_is_a_different_case(self):
        today = datetime.date.today()
        md = project(CF + ROSTER, {ymd(today - datetime.timedelta(days=1)): ITEMS})
        self.assertEqual(run(md).returncode, 0)
        res = run(md)
        self.assertEqual(res.returncode, 1)
        out = res.stdout + res.stderr
        self.assertIn("exists -- delete it first", out)
        self.assertNotIn("already has a note", out)


class SkipDates(unittest.TestCase):
    def test_a_single_day_and_a_range_with_reasons(self):
        cf = {"skip_dates": [{"date": 261020, "reason": "holiday-in"},
                             {"from": 261224, "to": 261226, "reason": "leave"}]}
        self.assertEqual(ba.skip_dates(cf), [
            (datetime.date(2026, 10, 20), "holiday-in"),
            (datetime.date(2026, 12, 24), "leave"),
            (datetime.date(2026, 12, 25), "leave"),
            (datetime.date(2026, 12, 26), "leave")])

    def test_a_bare_date_is_accepted_and_has_no_reason(self):
        self.assertEqual(ba.skip_dates({"skip_dates": ["261020"]}),
                         [(datetime.date(2026, 10, 20), "no reason given")])

    def test_a_reversed_range_is_read_in_order(self):
        got = ba.skip_dates({"skip_dates": [{"from": 261022, "to": 261020, "reason": "leave"}]})
        self.assertEqual([d for d, _ in got],
                         [datetime.date(2026, 10, 20), datetime.date(2026, 10, 21),
                          datetime.date(2026, 10, 22)])

    def test_one_unparseable_entry_does_not_take_the_list_down(self):
        got = ba.skip_dates({"skip_dates": ["not-a-date", {"reason": "leave"},
                                            {"date": 261020, "reason": "holiday-in"}]})
        self.assertEqual(got, [(datetime.date(2026, 10, 20), "holiday-in")])

    def test_an_entry_giving_only_to_is_the_same_one_day_as_only_from(self):
        # the mirror of each other; dropping one silently restores the ageing on the
        # day the operator wrote a reason for
        only_to = ba.skip_dates({"skip_dates": [{"to": 261020, "reason": "leave"}]})
        only_from = ba.skip_dates({"skip_dates": [{"from": 261020, "reason": "leave"}]})
        self.assertEqual(only_to, [(datetime.date(2026, 10, 20), "leave")])
        self.assertEqual(only_to, only_from)

    def test_no_key_is_an_empty_list_not_an_error(self):
        self.assertEqual(ba.skip_dates({}), [])

    def test_one_day_written_without_the_dash_is_read_not_a_traceback(self):
        # `skip_dates: 261020` -- YAML reads it as an int, and iterating it raised
        for raw in (261020, "261020", {"date": 261020, "reason": "holiday-in"}):
            got = ba.skip_dates({"skip_dates": raw})
            self.assertEqual([d for d, _ in got], [datetime.date(2026, 10, 20)], raw)

    def test_a_shape_that_is_no_kind_of_date_list_is_empty_not_an_error(self):
        self.assertEqual(ba.skip_dates({"skip_dates": True}), [])

    def test_the_scalar_form_reaches_the_build(self):
        today = datetime.date.today()
        first = today - datetime.timedelta(days=10)
        md = project(CF + "      escalate_after_days: 8\n"
                     f"      skip_dates: {ymd(today - datetime.timedelta(days=3))}\n" + ROSTER,
                     {ymd(first): ITEMS, ymd(today - datetime.timedelta(days=1)): ITEMS})
        res = run(md)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("· 9d", (md / f"{ymd(today)}-agenda-daily-standup.md").read_text(encoding="utf-8"))

    def test_counted_over_a_half_open_interval(self):
        skips = ba.skip_dates({"skip_dates": [{"from": 261019, "to": 261021, "reason": "leave"}]})
        # the first day is a day the series DID meet; a skip on the target still counts
        self.assertEqual(ba.skipped_between(skips, datetime.date(2026, 10, 19),
                                            datetime.date(2026, 10, 21)), 2)
        self.assertEqual(ba.skipped_between(skips, datetime.date(2026, 10, 18),
                                            datetime.date(2026, 10, 22)), 3)


class NothingAgesOnADayNobodyMet(unittest.TestCase):
    def test_the_carried_age_skips_the_declared_days(self):
        today = datetime.date.today()
        first = today - datetime.timedelta(days=10)
        skipped = [today - datetime.timedelta(days=n) for n in (3, 4)]
        skip_yaml = "      skip_dates:\n" + "".join(
            f"        - date: {ymd(d)}\n          reason: holiday-in\n" for d in skipped)
        # 10 calendar days, two of them declared skipped: the item has carried 8
        notes = {ymd(first): ITEMS, ymd(today - datetime.timedelta(days=1)): ITEMS}
        md = project(CF + "      escalate_after_days: 8\n" + skip_yaml + ROSTER, notes)
        agenda = self.build(md)
        self.assertIn("· 8d", agenda)
        self.assertNotIn("· 10d", agenda)

    def test_without_skip_dates_the_age_is_the_calendar_gap(self):
        today = datetime.date.today()
        first = today - datetime.timedelta(days=10)
        notes = {ymd(first): ITEMS, ymd(today - datetime.timedelta(days=1)): ITEMS}
        md = project(CF + "      escalate_after_days: 8\n" + ROSTER, notes)
        self.assertIn("· 10d", self.build(md))

    def build(self, md: Path) -> str:
        res = run(md)
        self.assertEqual(res.returncode, 0, res.stderr)
        return (md / f"{ymd(datetime.date.today())}-agenda-daily-standup.md").read_text(encoding="utf-8")


class BaseHeader(unittest.TestCase):
    def test_the_line_names_the_note_and_the_last_meeting_held(self):
        line = ba.base_line("261019-daily-standup.md", "261019", [], datetime.date(2026, 10, 21))
        self.assertEqual(line, "Base: 261019-daily-standup.md (last meeting held 261019)")

    def test_skipped_days_in_the_window_are_listed_with_their_reason(self):
        skips = ba.skip_dates({"skip_dates": [{"date": 261020, "reason": "holiday-in"}]})
        line = ba.base_line("261019-daily-standup.md", "261019", skips, datetime.date(2026, 10, 21))
        self.assertIn("skipped: 261020 (holiday-in)", line)

    def test_a_skip_outside_the_window_is_not_listed(self):
        skips = ba.skip_dates({"skip_dates": [{"date": 260814, "reason": "leave"}]})
        line = ba.base_line("261019-daily-standup.md", "261019", skips, datetime.date(2026, 10, 21))
        self.assertNotIn("skipped", line)

    def test_the_agenda_carries_the_line_in_its_header(self):
        today = datetime.date.today()
        note = today - datetime.timedelta(days=2)
        md = project(CF + f"      skip_dates:\n        - date: {ymd(today - datetime.timedelta(days=1))}\n"
                     "          reason: holiday-in\n" + ROSTER, {ymd(note): ITEMS})
        res = run(md)
        self.assertEqual(res.returncode, 0, res.stderr)
        agenda = (md / f"{ymd(today)}-agenda-daily-standup.md").read_text(encoding="utf-8")
        head = agenda.split("---")[0]
        self.assertIn(f"Base: {ymd(note)}-daily-standup.md", head)
        self.assertIn(f"last meeting held {ymd(note)}", head)
        self.assertIn("holiday-in", head)


class MeetsIsAnAliasForScheduleDays(unittest.TestCase):
    """`meets:` and `schedule_days` answer the same question, so one list is resolved."""

    def resolve(self, body: str) -> list | None:
        md = project("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n" + body)
        return ba.config(md).get("schedule_days")

    def test_meets_fills_schedule_days(self):
        self.assertEqual(self.resolve("      meets: [mon, wed, fri]\n"), ["mon", "wed", "fri"])

    def test_an_existing_schedule_days_keeps_precedence(self):
        got = self.resolve("      schedule_days: [monday, thursday]\n      meets: [mon, wed, fri]\n")
        self.assertEqual(got, ["monday", "thursday"])

    def test_neither_key_resolves_to_the_meeting_type_schedule_as_before(self):
        md = project("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
                     "meeting_types:\n  standup:\n    schedule:\n      days: [tuesday]\n")
        self.assertEqual(ba.config(md).get("schedule_days"), ["tuesday"])

    def test_three_letter_and_full_names_both_resolve(self):
        self.assertEqual(ba.weekdays(["mon", "wed"]), {0, 2})
        self.assertEqual(ba.weekdays(["monday", "wednesday"]), {0, 2})
        self.assertEqual(ba.weekdays(["mon", "monday"]), {0})

    def test_an_unrecognised_entry_is_ignored_not_an_empty_schedule(self):
        self.assertEqual(ba.weekdays(["mon", "someday"]), {0})
        self.assertEqual(ba.weekdays([]), set())

    def test_next_session_reads_the_alias_spelling(self):
        # 261021 is a Wednesday; a Monday/Friday series next meets on the Friday
        self.assertEqual(ba.next_session("261021", ["mon", "fri"]), "261023")


if __name__ == "__main__":
    unittest.main()
