"""CR-154: the daily-playbook template, and a one-line check that the page has not gone stale.

Invented data. A team page about its daily meeting was written in week one and never revised; by
week five it described things that no longer existed. The template is the generic part; the check
compares the page's review date with the decisions recorded since.
"""

import datetime
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "ops"))
import build_agenda as ba  # noqa: E402

TEMPLATE = ROOT / "skills" / "ops" / "templates" / "daily-playbook.md"


class Template(unittest.TestCase):
    text = TEMPLATE.read_text(encoding="utf-8")

    def test_the_six_sections_are_there_in_order(self):
        heads = re.findall(r"^## (\d)\. ", self.text, re.M)
        self.assertEqual(heads, ["1", "2", "3", "4", "5", "6"])

    def test_the_four_parts_and_the_four_lines_of_a_minute(self):
        for w in ("Milestones", "Blockers", "The round", "Close"):
            self.assertIn(f"**{w}**", self.text)
        for w in ("What moved", "What you are stuck on", "What you owe", "What you need decided"):
            self.assertIn(w, self.text)

    def test_attendance_has_the_silent_absence_rule(self):
        self.assertIn("A silent absence is the one thing we do not accept.", self.text)

    def test_every_project_specific_part_is_a_visible_placeholder(self):
        ph = re.findall(r"\{\{[^}]+\}\}", self.text)
        self.assertGreaterEqual(len(ph), 15)
        for want in ("{{leader}}", "{{verifier}}", "{{blocker label}}", "{{channel}}"):
            self.assertIn(want, self.text)

    def test_no_real_names_and_no_project_numbers_in_a_generic_template(self):
        self.assertIsNone(re.search(r"\bD-\d+\b|#\d{3,}", self.text))


class Staleness(unittest.TestCase):
    def project(self, page, register):
        d = Path(tempfile.mkdtemp())
        (d / "how.md").write_text(page, encoding="utf-8")
        (d / "decisions.md").write_text(register, encoding="utf-8")
        return {"_root": d, "playbook": {"path": "how.md"}}

    @staticmethod
    def register(n, start="2026-10-10"):
        s = datetime.date.fromisoformat(start)
        rows = "".join(f"| D-{i} | {(s + datetime.timedelta(days=i)).isoformat()} | something | x | y |\n"
                       for i in range(1, n + 1))
        return "| # | Date | Decision | Who | Note |\n|---|---|---|---|---|\n" + rows

    def test_more_than_the_limit_since_the_review_is_one_line(self):
        cf = self.project("# Page\n\n**Reviewed:** 2026-10-09\n", self.register(10))
        out = ba.playbook_findings(cf)
        self.assertEqual(len(out), 1)
        self.assertIn("last reviewed 2026-10-09; 10 decision(s) recorded since", out[0])

    def test_at_or_under_the_limit_is_silent(self):
        cf = self.project("# Page\n\n**Reviewed:** 2026-10-09\n", self.register(8))
        self.assertEqual(ba.playbook_findings(cf), [])

    def test_decisions_before_the_review_do_not_count(self):
        cf = self.project("# Page\n\n**Reviewed:** 2026-12-01\n", self.register(20))
        self.assertEqual(ba.playbook_findings(cf), [])

    def test_the_limit_is_configurable(self):
        cf = self.project("# Page\n\n**Reviewed:** 2026-10-09\n", self.register(4))
        cf["playbook"]["stale_after"] = 3
        self.assertEqual(len(ba.playbook_findings(cf)), 1)

    def test_no_review_line_falls_back_to_the_file_date(self):
        cf = self.project("# Page without a review line\n", self.register(30, start="2000-01-01"))
        self.assertEqual(ba.playbook_findings(cf), [])      # file is new; every decision is older

    def test_a_missing_page_is_said_once(self):
        cf = self.project("x", self.register(1))
        cf["playbook"]["path"] = "nowhere.md"
        out = ba.playbook_findings(cf)
        self.assertEqual(len(out), 1)
        self.assertIn("declared but not found", out[0])

    def test_nothing_declared_is_silent(self):
        self.assertEqual(ba.playbook_findings({"_root": Path(".")}), [])


if __name__ == "__main__":
    unittest.main()
