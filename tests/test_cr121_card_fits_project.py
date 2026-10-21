"""CR-121: the card fits the project and the session. Invented data.

The second project wired to the card layout moves improvements one at a time from a
request sheet to staging to production, and nothing in it is a release. Its first card
opened with a lead asking the room to confirm the release blockers and a *Release
blockers* section reading *None carried*, and the session was that project's first demo
day -- the thing the card itself named -- with no place for what the meeting was for.

These tests assert the two configurable readings and the one blank that must never be
filled by a guess: `release_blockers: false` drops the section and the word release from
the lead while keeping carried `[blocker]` lines, a milestone `kind: demo` puts a Demo
section under the milestone on its own date and nowhere else, and *Shown by* is empty
where nothing in the data says who raised the item.
"""

import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr101_agenda_draft import build  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_agenda as ba  # noqa: E402

DAY = datetime.date(2026, 9, 24)      # the day `build` generates for
CARD = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n      layout: card\n"
        "people:\n  - name: Ann\n  - name: Bob\n")
NO_REL = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n      layout: card\n"
          "      card:\n        release_blockers: false\n"
          "people:\n  - name: Ann\n  - name: Bob\n")
MS = "milestone:\n  name: Staging step\n  date: 2026-10-01\n  set_on: 2026-09-01\n"
DEMO = ("milestone:\n  name: First demo day\n  date: 2026-09-24\n  set_on: 2026-09-01\n"
        "  kind: demo\n")
ITEMS = ("- [blocker] **Payment webhook fails** — #12 · **Bob**\n"
         "- [dependency] **Backend answer on refunds** — TICK-9 · **Ann**\n"
         "- [decision] **Canary shape** — plan section 4 · **Ann, Bob**\n")

# A repo declaring the labels CR-114 reads, and an archived movement record for it.
# Both halves are needed to reach the repo blocker table and the demo rows at all:
# before the archive existed they needed a live `gh` and no test could see them.
LABELS = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
          "      labels:\n        priority: [blocker, critical]\n"
          "        gap: [blocker, critical]\n"
          "        awaiting_test: 'status: Fixed'\n"
          "        area_prefix: 'area:'\n")


def issue(n, title, labels, who=()):
    return {"number": n, "title": title, "state": "OPEN",
            "createdAt": "2026-09-01T09:00:00Z", "closedAt": None,
            "labels": [{"name": x} for x in labels],
            "assignees": [{"login": w} for w in who],
            "url": f"https://github.com/acme/app/issues/{n}"}


# #41 is an open gap item; #42 is fixed and waiting for a test. The distinction is the
# whole of CR-114's grouping and of CR-121's "on staging or done".
MOVEMENT = {
    "repo": "acme/app",
    "issues": [issue(41, "Refund webhook retries forever", ["blocker", "area:payments"],
                     who=["bob"]),
               issue(42, "Locale crash on launch",
                     ["blocker", "status: Fixed", "area:app"], who=["ann"])],
    "labels": [{"name": n, "description": ""} for n in
               ("blocker", "critical", "status: Fixed", "area:payments", "area:app")],
    "events": [["labeled", "2026-09-01T09:05:00Z", 41, "blocker"],
               ["labeled", "2026-09-01T09:05:00Z", 42, "blocker"],
               ["labeled", "2026-09-10T09:05:00Z", 42, "status: Fixed"]],
}


class ReleaseBlockersOff(unittest.TestCase):
    """Proposal 1. The project ships no release, so it is not asked about one."""

    def setUp(self):
        self.agenda, _ = build(NO_REL + MS, note_items=ITEMS)

    def test_no_release_blockers_heading(self):
        self.assertNotIn("## Release blockers", self.agenda)
        self.assertIn("## Blockers", self.agenda)

    def test_the_lead_line_does_not_mention_release(self):
        lead = [l for l in self.agenda.split("\n") if l.startswith("*Raise") or l.startswith("*Confirm")]
        self.assertEqual(lead, ["*Raise what you wait on, then one minute each. Five to ten"
                                " minutes when nothing blocks; statistics are read offline.*"])
        self.assertNotIn("release", lead[0])

    def test_carried_blocker_lines_still_appear(self):
        """The key drops the *release* framing, not the blockers themselves."""
        after = self.agenda[self.agenda.index("## Blockers"):]
        self.assertIn("**Payment webhook fails**", after.split("## Dependencies")[0])

    def test_the_lead_in_the_section_drops_the_word_too(self):
        self.assertIn("**What is stuck, who owns it, the plan.**", self.agenda)
        self.assertNotIn("**What blocks the release, who owns it, the plan.**", self.agenda)


class ReleaseBlockersOnByDefault(unittest.TestCase):
    """The default is unchanged: a project that ships releases keeps CR-114."""

    def test_no_key_keeps_the_release_wording(self):
        agenda, _ = build(CARD + MS, note_items=ITEMS)
        self.assertIn("## Release blockers", agenda)
        self.assertIn("**What blocks the release, who owns it, the plan.**", agenda)
        self.assertIn("*Confirm the release blockers and their plan", agenda)

    def test_release_blockers_true_is_the_same_as_absent(self):
        on = CARD.replace("      layout: card\n",
                          "      layout: card\n      card:\n        release_blockers: true\n")
        a_on, _ = build(on + MS, note_items=ITEMS)
        a_off, _ = build(CARD + MS, note_items=ITEMS)
        self.assertEqual(a_on.replace("Built from", ""), a_off.replace("Built from", ""))


class DemoDay(unittest.TestCase):
    """Proposal 2. On the milestone's own date, and only then."""

    def setUp(self):
        self.agenda, _ = build(CARD + DEMO, note_items=ITEMS)

    def test_the_demo_section_is_directly_under_the_milestone(self):
        heads = [l for l in self.agenda.split("\n") if l.startswith("## ")]
        self.assertEqual(heads[:2], ["## Milestone", "## Demo"])

    def test_the_lead_line_is_the_demo_one(self):
        self.assertIn("*Demo day: the people who raised the ideas show them;", self.agenda)
        self.assertNotIn("*Confirm the release blockers", self.agenda)

    def test_rows_come_from_the_carried_lines(self):
        demo = self.agenda[self.agenda.index("## Demo"):self.agenda.index("## Release blockers")]
        self.assertIn("**Payment webhook fails**", demo)
        self.assertIn("carried as `[blocker]`", demo)

    def test_shown_by_is_read_where_the_line_names_an_owner(self):
        demo = self.agenda[self.agenda.index("## Demo"):self.agenda.index("## Release blockers")]
        self.assertIn("| **Payment webhook fails** | Bob | carried as `[blocker]` |", demo)

    def test_shown_by_is_blank_and_never_guessed_when_unowned(self):
        """The failure CR-121 names explicitly: a plausible name against work nobody
        offered to present. An unowned line must show an EMPTY cell."""
        agenda, _ = build(CARD + DEMO,
                          note_items="- [blocker] **Nobody raised this one** — #44\n")
        demo = agenda[agenda.index("## Demo"):]
        row = [l for l in demo.split("\n") if "Nobody raised this one" in l][0]
        self.assertEqual(row, "| **Nobody raised this one** |  | carried as `[blocker]` |")
        self.assertNotIn("UNOWNED", row)

    def test_the_post_carries_the_demo_list(self):
        self.assertIn("**Demo today:** Payment webhook fails (Bob)", build.last_post)

    def test_no_demo_section_the_day_after(self):
        agenda, _ = build(CARD + DEMO, note_items=ITEMS, date="260925")
        self.assertNotIn("## Demo", agenda)
        self.assertIn("*Confirm the release blockers", agenda)

    def test_after_the_date_the_card_asks_for_the_record(self):
        agenda, _ = build(CARD + DEMO, note_items=ITEMS, date="260925")
        self.assertIn("*Demo held (2026-09-24)? Record it and set the next milestone.*", agenda)

    def test_a_kind_other_than_demo_changes_nothing(self):
        agenda, _ = build(CARD + DEMO.replace("kind: demo", "kind: release"), note_items=ITEMS)
        self.assertNotIn("## Demo", agenda)
        self.assertIn("*Confirm the release blockers", agenda)


class DemoRowsFromTheRepo(unittest.TestCase):
    """Proposal 2, the repo half: "rows name tickets on staging or done".

    Reachable only since the movement archive existed (CR-121/CR-148): before that the
    repo rows needed a live `gh`, the branch had no coverage, and it rendered every
    open gap-label issue as a demo row reading **open**.
    """

    def setUp(self):
        self.agenda, _ = build(CARD + DEMO + LABELS, note_items=ITEMS, movement=MOVEMENT)
        self.demo = self.agenda[self.agenda.index("## Demo"):
                                self.agenda.index("## Release blockers")]

    def test_the_fixed_and_waiting_issue_is_a_demo_row(self):
        row = [l for l in self.demo.split("\n") if "Locale crash on launch" in l]
        self.assertEqual(len(row), 1, self.demo)
        self.assertEqual(
            row[0],
            "| [#42](https://github.com/acme/app/issues/42) Locale crash on launch"
            " |  | fixed, waiting for a test |")

    def test_an_open_issue_is_not_a_demo_row(self):
        """An open blocker is not something to show at a demo. It was rendered as a row
        reading **open**, which put the release-blocker table inside the Demo section.
        """
        self.assertNotIn("Refund webhook retries forever", self.demo)
        self.assertNotIn("**open**", self.demo)

    def test_the_open_issue_is_still_on_the_card_under_release_blockers(self):
        """Nothing is lost by the filter: the open one is where CR-114 puts it."""
        rb = self.agenda[self.agenda.index("## Release blockers"):]
        self.assertIn("Refund webhook retries forever", rb)
        self.assertIn("**open**", rb)

    def test_shown_by_is_blank_for_a_repo_row(self):
        """The repo knows an assignee, not a raiser. "This person fixed it" is not the
        same statement as "this person will show it", so the cell stays empty."""
        row = [l for l in self.demo.split("\n") if "Locale crash on launch" in l][0]
        self.assertEqual([c.strip() for c in row.strip("|").split("|")][1], "")
        self.assertNotIn("ann", row)

    def test_the_post_carries_the_same_filtered_list(self):
        line = build.last_post.split("**Demo today:**")[1].split("\n")[0]
        self.assertIn("#42 Locale crash on launch", line)
        self.assertNotIn("Refund webhook retries forever", line)

    def test_the_compact_post_carries_the_repo_rows_too(self):
        """The compact post is the ONLY post a compact project has, so it must not
        carry less than the card's post does on the same day -- under the same filter.
        """
        compact = CARD.replace("      layout: card\n", "      layout: compact\n")
        build(compact + DEMO + LABELS, note_items=ITEMS, movement=MOVEMENT)
        line = [l for l in build.last_post.split("\n") if l.startswith("Demo today:")][0]
        self.assertIn("#42 Locale crash on launch", line)
        self.assertIn("Payment webhook fails", line)
        self.assertNotIn("Refund webhook retries forever", line)
        self.assertEqual([c for c in "*_`|[]" if c in build.last_post], [])


class SectionPlan(unittest.TestCase):
    """The plan is the only place a key decides a section's presence or its order."""

    def test_the_default_plan_is_the_cards_order(self):
        self.assertEqual(ba.section_plan({"layout": "card"}, DAY)["agenda"],
                         ["milestone", "movement", "release_blockers", "dependencies",
                          "decisions", "confirm", "stuck", "round", "close"])

    def test_the_key_swaps_the_id_and_nothing_else(self):
        plan = ba.section_plan({"layout": "card", "card": {"release_blockers": False}}, DAY)
        self.assertEqual(plan["agenda"],
                         ["milestone", "movement", "blockers", "dependencies",
                          "decisions", "confirm", "stuck", "round", "close"])

    def test_demo_is_inserted_after_the_milestone_in_both_outputs(self):
        cf = {"layout": "card", "milestone": {"name": "D", "date": "2026-09-24", "kind": "demo"}}
        plan = ba.section_plan(cf, DAY)
        for out in ("agenda", "post"):
            self.assertEqual(plan[out][:2], ["milestone", "demo"], out)

    def test_demo_on_reads_the_date(self):
        cf = {"milestone": {"name": "D", "date": "2026-09-24", "kind": "demo"}}
        self.assertIsNotNone(ba.demo_on(cf, DAY))
        self.assertIsNone(ba.demo_on(cf, DAY + datetime.timedelta(days=1)))


class Lint(unittest.TestCase):
    """Proposal 3, report only. Both readings are legitimate; which is right is the
    team's to say, so the check names the contradiction and stops. Asserted through a
    generated card, because reaching the reader is half of what "report" means."""

    DEMO_MS = ("milestone:\n  name: First demo day\n  date: 2026-10-01\n"
               "  set_on: 2026-09-01\n  kind: demo\n")

    def test_a_card_with_no_labels_and_a_non_release_kind_is_suggested_the_key(self):
        agenda, _ = build(CARD + self.DEMO_MS, note_items=ITEMS)
        self.assertIn("consider `card: {release_blockers: false}`", agenda)

    def test_a_release_kind_is_not_suggested_anything(self):
        agenda, _ = build(CARD + self.DEMO_MS.replace("kind: demo", "kind: release"),
                          note_items=ITEMS)
        self.assertNotIn("release_blockers: false", agenda)

    def test_a_milestone_with_no_kind_is_not_suggested_anything(self):
        """Silence about the kind is not a statement that nothing is released."""
        agenda, _ = build(CARD + MS, note_items=ITEMS)
        self.assertNotIn("release_blockers: false", agenda)

    def test_the_key_set_explicitly_is_not_second_guessed(self):
        on = CARD.replace("      layout: card\n",
                          "      layout: card\n      card:\n        release_blockers: true\n")
        agenda, _ = build(on + self.DEMO_MS, note_items=ITEMS)
        self.assertNotIn("consider `card:", agenda)

    def test_false_against_a_repo_declaring_a_gap_label_is_a_contradiction(self):
        found = ba.config_checks({"layout": "card", "card": {"release_blockers": False},
                                  "milestone": {"name": "S", "date": "2026-10-01",
                                                "set_on": "2026-09-01"},
                                  "people": [], "_root": str(Path(ba.__file__).parent)},
                                 [], DAY, {"top": "gap"})
        self.assertTrue(any("one of the two is wrong" in f for f in found), found)

    def test_the_repo_table_is_not_suppressed_by_the_key(self):
        """CR-121 proposal 1 says check FLAGS the contradiction and stops there.
        Suppressing the repo's own data on a config key would hide repo data, which is
        the wrong direction -- so the table and its heading are rendered either way.

        Asserted by GENERATING both cards and comparing the table, not by reading the
        source: the previous version of this test matched one spelling of one line.
        """
        with_key, _ = build(NO_REL + MS + LABELS, note_items=ITEMS, movement=MOVEMENT)
        without, _ = build(CARD + MS + LABELS, note_items=ITEMS, movement=MOVEMENT)
        for agenda, label in ((with_key, "release_blockers: false"), (without, "default")):
            self.assertIn("## Release blockers", agenda, label)
            self.assertIn("From the repo's `blocker` label", agenda, label)
            self.assertIn("Refund webhook retries forever", agenda, label)
            self.assertIn("Locale crash on launch", agenda, label)
        # and the key changed nothing at all in that table
        cut = lambda a: a[a.index("## Release blockers"):a.index("## Dependencies")]
        self.assertEqual(cut(with_key), cut(without))

    def test_the_contradiction_reaches_the_card_as_a_finding(self):
        """The other half of proposal 1: `release_blockers: false` against a repo that
        declares a gap label is reported, in the generated card where it is read."""
        agenda, _ = build(NO_REL + MS + LABELS, note_items=ITEMS, movement=MOVEMENT)
        self.assertIn("one of the two is wrong", agenda)


if __name__ == "__main__":
    unittest.main()
