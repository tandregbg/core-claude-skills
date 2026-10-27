"""CR-158: the card's milestone table must not call a parsed date "unreadable". Invented data.

`s_milestone` printed `(unreadable date)` for every parsed date that `next_milestone` did not
return: the passed one, the one on the generated day, and every later one. The sequence line
under the table, which reads the same parsed dates, ordered them all correctly, so the card
contradicted its own config check. These tests pin the cell for each place a date can sit
relative to the generated day, on the card, in the post and in the compact post, and that a
date which truly does not parse is still named as such.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr101_agenda_draft import build  # noqa: E402
from test_cr149_milestone_list import BASE, ITEMS  # noqa: E402

# 260924 is the generated day in `build`. Declared out of order on purpose.
FOUR = ("milestones:\n"
        "  - name: Later one\n    date: 2026-11-06\n    state: target\n    set_on: 2026-09-01\n"
        "  - name: Next one\n    date: 2026-10-01\n    state: confirmed\n    source: DEC-1\n    set_on: 2026-09-01\n"
        "  - name: Today one\n    date: 2026-09-24\n    state: confirmed\n    source: DEC-2\n    set_on: 2026-09-01\n"
        "  - name: Past one\n    date: 2026-09-21\n    state: confirmed\n    source: DEC-3\n    set_on: 2026-09-01\n"
        "  - name: Past done\n    date: 2026-09-10\n    state: done\n    source: Dee\n    set_on: 2026-08-01\n")


def rows(block):
    return {l.split("|")[1].strip().strip("*"): l.split("|")[2].strip()
            for l in block.splitlines() if l.startswith("| **")}


class CardTable(unittest.TestCase):
    def setUp(self):
        self.agenda, _ = build(BASE + FOUR, note_items=ITEMS)
        self.block = self.agenda[self.agenda.index("## Milestone"):self.agenda.index("## Release blockers")]
        self.cells = rows(self.block)

    def test_no_parsed_date_is_called_unreadable(self):
        self.assertNotIn("unreadable", self.block, self.block)

    def test_the_next_date_after_today_keeps_its_days(self):
        self.assertEqual(self.cells["Next one"], "**2026-10-01** · **7 days**")

    def test_a_date_on_the_generated_day_says_today(self):
        self.assertEqual(self.cells["Today one"], "**2026-09-24** · **today**")

    def test_a_passed_date_not_marked_done_reads_as_overdue(self):
        self.assertEqual(self.cells["Past one"], "**2026-09-21** · 3 days ago, not marked done")

    def test_a_passed_date_marked_done_is_the_date_alone(self):
        self.assertEqual(self.cells["Past done"], "**2026-09-10**")

    def test_a_later_future_date_is_the_date_alone(self):
        self.assertEqual(self.cells["Later one"], "**2026-11-06**")

    def test_only_the_next_date_carries_a_bold_days_marker(self):
        # CR-149 asserts the same at five entries: the days-left marker is the next date's alone.
        self.assertEqual(self.block.count("days**"), 1, self.block)

    def test_the_sequence_line_is_unchanged(self):
        self.assertIn("*Sequence: 2026-09-10 -> 2026-09-21 -> 2026-09-24 -> 2026-10-01 -> 2026-11-06*",
                      self.block)


class PostAgrees(unittest.TestCase):
    def setUp(self):
        build(BASE + FOUR, note_items=ITEMS)
        post = build.last_post
        self.post = post[post.index("**Milestones:**"):]

    def test_the_list_marks_today_and_overdue_and_keeps_the_next_days(self):
        self.assertIn("- Today one — 2026-09-24 · confirmed · **today**", self.post)
        self.assertIn("- Past one — 2026-09-21 · confirmed · 3 days ago, not marked done", self.post)
        self.assertIn("- Next one — 2026-10-01 · confirmed · **7 days**", self.post)

    def test_done_and_later_dates_carry_no_marker(self):
        self.assertIn("- Past done — 2026-09-10 · done · Dee", self.post)
        self.assertIn("- Later one — 2026-11-06 · target", self.post)
        self.assertNotIn("Later one — 2026-11-06 · target ·", self.post)


class CompactPostAgrees(unittest.TestCase):
    def setUp(self):
        compact = BASE.replace("layout: card", "layout: compact")
        build(compact + FOUR, note_items=ITEMS)
        self.post = build.last_post

    def test_the_compact_post_marks_today_and_overdue(self):
        self.assertIn("- Today one: 2026-09-24, confirmed, today", self.post)
        self.assertIn("- Past one: 2026-09-21, confirmed, 3 days ago, not marked done", self.post)
        self.assertIn("- Next one: 2026-10-01, confirmed, 7 days", self.post)
        self.assertIn("- Later one: 2026-11-06, target\n", self.post + "\n")


class StillUnreadable(unittest.TestCase):
    def test_a_date_that_does_not_parse_is_still_named_as_written(self):
        entries = FOUR + "  - name: Second region\n    date: next Tuesday\n    set_on: 2026-09-02\n"
        agenda, _ = build(BASE + entries, note_items=ITEMS)
        block = agenda[agenda.index("## Milestone"):agenda.index("## Release blockers")]
        self.assertIn("| **Second region** | **next Tuesday** (unreadable date) | proposed | 2026-09-02 | — |",
                      block.splitlines())
        self.assertEqual(block.count("unreadable"), 1, block)


class SingleMilestoneUntouched(unittest.TestCase):
    def test_a_lone_milestone_renders_as_before(self):
        single = ("milestone:\n  name: Canary to five per cent\n  date: 2026-11-10\n"
                  "  set_on: 2026-09-01\n  criteria: plan section 4\n")
        agenda, _ = build(BASE + single, note_items=ITEMS)
        self.assertIn("**Canary to five per cent** — 2026-11-10 · **47 days**", agenda.splitlines())
        self.assertNotIn("| Milestone |", agenda)


if __name__ == "__main__":
    unittest.main()
