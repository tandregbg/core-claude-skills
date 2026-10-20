"""CR-119: before every agenda, the config is checked against the project -- by script for
what a script can see, by prepare for what needs judgement. Invented data."""

import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr101_agenda_draft import build  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_agenda as ba  # noqa: E402

BASE = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n      layout: card\n"
        "people:\n  - name: Ann\n  - name: Bob\n")
ROUND = "\n## Round\n\n| | Track | Focus |\n|---|---|---|\n| **Ann** | app | x |\n\n"


class Checks(unittest.TestCase):
    def test_passed_milestone_is_a_finding(self):
        agenda, _ = build(BASE + "milestone:\n  name: Beta\n  date: 2026-09-01\n",
                          note_items="- **Thing** — #1 · **Ann**\n")
        self.assertIn("**Config:", agenda)
        self.assertIn("milestone date 2026-09-01 has passed", agenda)

    def test_card_without_milestone_is_a_finding(self):
        agenda, _ = build(BASE, note_items="- **Thing** — #1 · **Ann**\n")
        self.assertIn("card layout without a milestone", agenda)

    def test_unknown_kind_is_a_finding(self):
        agenda, _ = build(BASE + "milestone:\n  name: Beta\n  date: 2027-01-01\n  set_on: 2026-09-01\n",
                          note_items="- [urgent] **Thing** — #1 · **Ann**\n")
        self.assertIn("unknown kind(s) in the last note: [urgent]", agenda)

    def test_clean_config_says_passed_and_leaves_the_review_slot(self):
        agenda, _ = build(BASE + "milestone:\n  name: Beta\n  date: 2027-01-01\n  set_on: 2026-09-01\n",
                          note_items="- **Thing** — #1 · **Ann**\n")
        details = (Path(build.last_meetings) / "260924-agenda-details-daily-standup.md").read_text(encoding="utf-8")
        self.assertNotIn("**Config:", agenda)
        self.assertIn("config    checks passed", details)
        self.assertIn(ba.CONFIG_MARKER, details)


class Roster(unittest.TestCase):
    def test_roster_name_absent_from_recent_rounds(self):
        cf = {"people": [{"name": "Ann"}, {"name": "Bob"}], "_root": Path("."), "milestone": {"name": "x", "date": "2099-01-01"}}
        import tempfile
        d = Path(tempfile.mkdtemp())
        hist = []
        for i, day in enumerate(("260921", "260922", "260923")):
            f = d / f"{day}-daily-standup.md"
            f.write_text("# n\n" + ROUND + "## Carried forward\n\n- **x** · **Ann**\n", encoding="utf-8")
            hist.append((day, f))
        out = ba.config_checks(cf, hist, datetime.date(2026, 9, 24), None)
        self.assertTrue(any("not in the last three rounds: Bob" in o for o in out))


if __name__ == "__main__":
    unittest.main()
