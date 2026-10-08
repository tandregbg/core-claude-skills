"""CR-114: a blocker is a release blocker; people waiting on people are dependencies;
each area has one current status at a stable path; the meeting is short when nothing blocks.
All data here is invented."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr107_agenda_card import CARD, ITEMS  # noqa: E402
from test_cr101_agenda_draft import build  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_movement  # noqa: E402


class Card(unittest.TestCase):
    def setUp(self):
        self.agenda, _ = build(CARD, note_items=ITEMS)

    def test_short_meeting_lead_line(self):
        self.assertIn("Five to ten minutes when nothing blocks", self.agenda)
        self.assertLess(self.agenda.index("Five to ten minutes"), self.agenda.index("## Milestone"))

    def test_without_labels_carried_blockers_are_the_release_blockers(self):
        sec = self.agenda[self.agenda.index("## Release blockers"):self.agenda.index("## Dependencies")]
        self.assertIn("Payment webhook fails", sec)

    def test_dependency_means_a_person_waiting(self):
        self.assertIn("A person waiting on another person", self.agenda)


class Movement(unittest.TestCase):
    def test_no_labels_declared_returns_four_values(self):
        head, note, rep, extra = build_movement.run({"ext": {"repos": [{"url": "x"}]}, "_root": "."})
        self.assertIsNone(head)
        self.assertEqual(extra, {})


if __name__ == "__main__":
    unittest.main()
