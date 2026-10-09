"""CR-117: the card opens with what the agenda was built from, parsed from the sources
block so the two cannot disagree; the post carries the same line. Invented data."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr107_agenda_card import CARD, ITEMS  # noqa: E402
from test_cr101_agenda_draft import build  # noqa: E402

TR = "external_systems:\n  transcripts:\n    store: Recorder\n    match: [standup]\n"


class BuiltFrom(unittest.TestCase):
    def setUp(self):
        self.agenda, _ = build(CARD + TR, note_items=ITEMS)

    def test_note_is_first_and_names_the_note(self):
        self.assertIn("> **Built from**", self.agenda)
        self.assertLess(self.agenda.index("> **Built from**"), self.agenda.index("## Milestone"))
        self.assertIn("**Built from** (", self.agenda); self.assertIn("260922-daily-standup.md ·", self.agenda)

    def test_undeclared_and_unarchived_sources_are_named(self):
        line = next(l for l in self.agenda.splitlines() if l.startswith("> **Built from**"))
        self.assertIn("**Not used or stale:**", line)
        self.assertIn("chat", line[line.index("Not used"):])
        self.assertNotIn("Recorder", line)   # recordings feed the note, not the agenda

    def test_post_carries_it(self):
        self.assertIn("**Built from:** 260922-daily-standup.md", build.last_post)


if __name__ == "__main__":
    unittest.main()
