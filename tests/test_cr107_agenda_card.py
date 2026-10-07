"""CR-107: the generated agenda opens with the card.

Milestone, blockers, dependencies and decisions lead; the full carried list, the
sources, the digest slot and the repo detail move to a details file. Carried lines
may declare their kind. All data here is invented.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr101_agenda_draft import build, CHATS  # noqa: E402

CARD = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n      layout: card\n"
        "milestone:\n  name: Canary to five per cent\n  decide_by: 2026-09-28\n"
        "people:\n  - name: Ann\n  - name: Bob\n")
ITEMS = ("- [blocker] **Payment webhook fails** — #12 · **Bob**\n"
         "- [dependency] **Backend answer on refunds** — TICK-9 · **Ann**\n"
         "- [decision] **Canary shape** — plan section 4 · **Ann, Bob**\n"
         "- **Update the readme** — docs/README.md · **Bob**\n")


class Card(unittest.TestCase):
    def setUp(self):
        self.agenda, self.out = build(CARD, note_items=ITEMS)
        self.md = Path(build.last_meetings)
        self.details = (self.md / "260924-agenda-details-daily-standup.md").read_text(encoding="utf-8")

    def test_card_order(self):
        a = self.agenda
        order = [a.index(h) for h in ("## Milestone", "## Blockers", "## Dependencies",
                                      "## Decisions needed today", "## One-minute round", "## Close")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("## Sources", a)

    def test_kinds_route_to_their_section(self):
        a = self.agenda
        self.assertIn("**Payment webhook fails**", a[a.index("## Blockers"):a.index("## Dependencies")])
        self.assertIn("**Backend answer on refunds**", a[a.index("## Dependencies"):a.index("## Decisions")])
        self.assertIn("**Canary shape**", a[a.index("## Decisions"):a.index("## One-minute")])

    def test_tasks_and_sources_go_to_details(self):
        self.assertNotIn("Update the readme", self.agenda)
        self.assertIn("Update the readme", self.details)
        self.assertIn("## Sources", self.details)
        self.assertIn("260924-agenda-details-daily-standup.md", self.agenda)

    def test_milestone_without_date_says_so(self):
        self.assertIn("**date not set**; decide by 2026-09-28", self.agenda)

    def test_post_is_the_card(self):
        p = build.last_post
        self.assertIn("**Blockers:** Payment webhook fails (Bob)", p)
        self.assertIn("**Decide today:** Canary shape (Ann, Bob)", p)
        self.assertNotIn("Update the readme", p)


class Digest(unittest.TestCase):
    def test_digest_slot_lives_in_details(self):
        agenda, _ = build(CARD + CHATS, note_items=ITEMS,
                          chat_lines=[("09:00", "Ann", "build 12 is out")])
        details = (Path(build.last_meetings) / "260924-agenda-details-daily-standup.md").read_text(encoding="utf-8")
        self.assertNotIn("<!-- DIGEST:", agenda)
        self.assertIn("<!-- DIGEST:", details)


class ListLayoutUnchanged(unittest.TestCase):
    def test_default_layout_keeps_sources_first_and_reads_kinds(self):
        agenda, _ = build("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n",
                          note_items=ITEMS)
        self.assertIn("## Sources", agenda)
        self.assertIn("Payment webhook fails", agenda)   # a kind prefix still parses as an item
        self.assertFalse((Path(build.last_meetings) / "260924-agenda-details-daily-standup.md").exists())


if __name__ == "__main__":
    unittest.main()
