"""CR-156: the presence check matches names, not whole row labels, and reads declared leave.

Invented data. The check warns when a roster person is *not in the last three rounds*. It used
to compare the whole row label, exactly, so a person in the room every day was reported absent
because the note labelled their row `Robert (Bob)`. And it could not know leave.
"""

import datetime
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_agenda as ba  # noqa: E402

DAY = datetime.date(2026, 9, 24)
DAYS = ("260921", "260922", "260923")


def round_rows(*labels):
    rows = "".join(f"| {l} | web app | said something |\n" for l in labels)
    return "| | Track | Their minute |\n|---|---|---|\n" + rows


def findings(people, per_day_labels):
    d = Path(tempfile.mkdtemp())
    hist = []
    for day, labels in zip(DAYS, per_day_labels):
        f = d / f"{day}-daily-standup.md"
        f.write_text("# n\n\n## Round\n\n" + round_rows(*labels) + "\n## Carried forward\n\n- **x** · **Ann**\n",
                     encoding="utf-8")
        hist.append((day, f))
    cf = {"people": people, "_root": Path("."), "milestone": {"name": "x", "date": "2099-01-01"}}
    out = ba.config_checks(cf, hist, DAY, None)
    return [o for o in out if "not in the last three rounds" in o]


class LabelHasName(unittest.TestCase):
    def test_a_bracketed_alias_matches(self):
        self.assertTrue(ba.label_has_name("Robert (Bob)", ["Bob"]))
        self.assertTrue(ba.label_has_name("Robert (Bob)", ["Robert"]))

    def test_a_trailing_role_does_not_stop_a_match(self):
        self.assertTrue(ba.label_has_name("Bob - backend", ["Bob"]))

    def test_case_is_ignored(self):
        self.assertTrue(ba.label_has_name("ROBERT", ["robert"]))

    def test_a_name_that_is_only_part_of_a_longer_word_does_not_match(self):
        self.assertFalse(ba.label_has_name("Mohamed", ["Mo"]))
        self.assertFalse(ba.label_has_name("Samuel", ["Sam"]))

    def test_an_empty_name_matches_nothing(self):
        self.assertFalse(ba.label_has_name("Robert", ["", None]))


class AwayDays(unittest.TestCase):
    def test_a_bare_day(self):
        self.assertEqual(ba.away_days({"away": ["261021"]}), {datetime.date(2026, 10, 21)})

    def test_an_iso_day_and_a_range_with_a_reason(self):
        days = ba.away_days({"away": ["2026-10-21", "2026-10-26..2026-10-28 leave"]})
        self.assertEqual(days, {datetime.date(2026, 10, 21), datetime.date(2026, 10, 26),
                                datetime.date(2026, 10, 27), datetime.date(2026, 10, 28)})

    def test_a_mapping(self):
        days = ba.away_days({"away": [{"from": "261026", "to": "261027", "reason": "leave"}]})
        self.assertEqual(days, {datetime.date(2026, 10, 26), datetime.date(2026, 10, 27)})

    def test_a_bad_entry_is_skipped_and_the_rest_kept(self):
        self.assertEqual(ba.away_days({"away": ["nonsense", "261021"]}), {datetime.date(2026, 10, 21)})

    def test_none_declared_is_empty(self):
        self.assertEqual(ba.away_days({"name": "Ann"}), set())


class PresenceCheck(unittest.TestCase):
    PEOPLE = [{"name": "Ann"}, {"name": "Robert", "aliases": ["Bob"]}, {"name": "Dee"}]

    def test_a_person_named_by_a_bracketed_alias_in_every_round_is_present(self):
        out = findings(self.PEOPLE, [["Ann", "Robert (Bob)", "Dee"]] * 3)
        self.assertEqual(out, [])

    def test_a_person_in_one_round_under_any_spelling_is_present(self):
        out = findings(self.PEOPLE, [["Ann", "Dee"], ["Ann", "Dee"], ["Ann", "Bob", "Dee"]])
        self.assertEqual(out, [])

    def test_a_person_in_no_round_is_reported_with_the_basis(self):
        out = findings(self.PEOPLE, [["Ann", "Dee"]] * 3)
        self.assertEqual(len(out), 1)
        self.assertIn("not in the last three rounds: Robert (no row matching Robert, Bob)", out[0])
        self.assertIn("(absent, or no longer in this meeting?)", out[0])

    def test_a_name_inside_a_longer_word_is_not_presence(self):
        people = [{"name": "Mo"}, {"name": "Ann"}]
        out = findings(people, [["Mohamed", "Ann"]] * 3)
        self.assertEqual(len(out), 1)
        self.assertIn("Mo (no row matching Mo)", out[0])

    def test_a_person_away_on_a_round_day_is_not_reported(self):
        people = [{"name": "Ann"}, {"name": "Robert", "aliases": ["Bob"], "away": ["260922"]}]
        out = findings(people, [["Ann"]] * 3)
        self.assertEqual(out, [])

    def test_a_person_away_on_other_days_is_still_reported(self):
        people = [{"name": "Ann"}, {"name": "Robert", "aliases": ["Bob"], "away": ["261101..261105"]}]
        out = findings(people, [["Ann"]] * 3)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
