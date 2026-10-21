"""CR-149: milestones as a list, each with a date, a source and a state. Invented data.

The card ran toward one date while the project it served had several that mattered. The
dates that existed lived in a plan document whose own header called every one of them an
unconfirmed proposal, so a reader meeting a bare date could not tell a commitment from a
proposal -- which is what `state:` is for. These tests assert that reading, the sort, the
days left on the next date, the four findings, and that a project declaring only the old
single `milestone:` is untouched.
"""

import datetime
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr101_agenda_draft import build  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_agenda as ba  # noqa: E402

DAY = datetime.date(2026, 9, 24)
BASE = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n      layout: card\n"
        "people:\n  - name: Ann\n  - name: Bob\n")
ITEMS = "- [blocker] **Payment webhook fails** — #12 · **Bob**\n"

# Five entries, deliberately declared out of date order: the card sorts them, the config
# does not have to. 260924 is the generated agenda's day in `build`.
FIVE = ("milestones:\n"
        "  - name: Rollout step two\n    date: 2026-11-18\n    state: target\n    set_on: 2026-09-01\n"
        "  - name: Backend release lands\n    date: 2026-10-28\n    state: confirmed\n"
        "    source: DEC-12\n    set_on: 2026-09-01\n"
        "  - name: Go/no-go\n    date: 2026-11-04\n    state: proposed\n"
        "    source: plan section 4\n    set_on: 2026-09-02\n"
        "  - name: Rollout step one\n    date: 2026-11-11\n    state: target\n    set_on: 2026-09-02\n"
        "  - name: Pilot closed\n    date: 2026-09-10\n    state: done\n"
        "    source: Dee\n    set_on: 2026-08-01\n")


def checks(yaml_entries, day=DAY, layout="card"):
    """config_checks over a `milestones:` list given as the parsed structure."""
    cf = {"milestones": yaml_entries, "layout": layout, "_root": Path(tempfile.gettempdir())}
    return ba.config_checks(cf, [], day, None)


class Shape(unittest.TestCase):
    def test_a_lone_milestone_reads_as_a_list_of_one(self):
        # The additivity requirement: three readers went through `milestones()`, and a
        # config that declares only the CR-107 block must still have a milestone to read.
        got = ba.milestones({"milestone": {"name": "Beta", "date": "2026-11-01"}})
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["name"], "Beta")
        self.assertEqual(got[0]["_date"], datetime.date(2026, 11, 1))

    def test_no_milestone_at_all_is_an_empty_list(self):
        self.assertEqual(ba.milestones({}), [])

    def test_a_single_mapping_under_the_plural_key_reads_as_one_entry(self):
        # A config that writes one entry as a mapping rather than a one-item list is the
        # same statement, and a renderer handed a bare dict would iterate its keys.
        got = ba.milestones({"milestones": {"name": "Beta", "date": "2026-11-01"}})
        self.assertEqual([e["name"] for e in got], ["Beta"])

    def test_entries_sort_by_date_and_undated_last(self):
        got = ba.milestones({"milestones": [
            {"name": "Later", "date": "2026-12-01"},
            {"name": "Undated"},
            {"name": "Earlier", "date": "2026-10-01"}]})
        self.assertEqual([e["name"] for e in got], ["Earlier", "Later", "Undated"])

    def test_the_list_and_a_lone_milestone_both_survive(self):
        # A project adding `milestones:` beside an existing `milestone:` loses neither.
        got = ba.milestones({"milestones": [{"name": "New", "date": "2026-12-01"}],
                             "milestone": {"name": "Old", "date": "2026-10-01"}})
        self.assertEqual([e["name"] for e in got], ["Old", "New"])

    def test_a_lone_milestone_already_in_the_list_is_not_duplicated(self):
        got = ba.milestones({"milestones": [{"name": "Beta", "date": "2026-12-01"}],
                             "milestone": {"name": "Beta", "date": "2026-12-01"}})
        self.assertEqual(len(got), 1)

    def test_an_absent_state_reads_as_proposed(self):
        # Silence must not read as a commitment: that is the whole point of the column.
        # A `source:` is declared so the demotion of an unsourced `confirmed` cannot be
        # what produces the answer -- only the default itself can.
        self.assertEqual(ba.milestones({"milestones": [
            {"name": "X", "date": "2026-12-01", "source": "DEC-12"}]})[0]["_state"], "proposed")

    def test_an_unknown_state_reads_as_proposed(self):
        self.assertEqual(ba.milestones({"milestones": [
            {"name": "X", "date": "2026-12-01", "state": "nearly", "source": "DEC-12"}]})[0]["_state"],
            "proposed")

    def test_a_stray_scalar_in_the_list_is_skipped_not_crashed_on(self):
        # A list item written as a bare string instead of a mapping -- an easy config slip.
        # Best effort everywhere else in this generator: the readable entries still render.
        got = ba.milestones({"milestones": ["Go/no-go", {"name": "Beta", "date": "2026-11-01"}]})
        self.assertEqual([e["name"] for e in got], ["Beta"])

    def test_a_malformed_date_does_not_stop_the_list(self):
        got = ba.milestones({"milestones": [{"name": "X", "date": "next Tuesday"}]})
        self.assertEqual(len(got), 1)
        self.assertIsNone(got[0]["_date"])


class ConfirmedNeedsASource(unittest.TestCase):
    def test_confirmed_without_a_source_is_shown_as_proposed(self):
        got = ba.milestones({"milestones": [
            {"name": "X", "date": "2026-12-01", "state": "confirmed"}]})
        self.assertEqual(got[0]["_state"], "proposed")

    def test_confirmed_with_a_source_stays_confirmed(self):
        for src in ("DEC-12", "plan section 4", "Dee"):
            got = ba.milestones({"milestones": [
                {"name": "X", "date": "2026-12-01", "state": "confirmed", "source": src}]})
            self.assertEqual(got[0]["_state"], "confirmed", src)

    def test_a_blank_source_does_not_count_as_one(self):
        got = ba.milestones({"milestones": [
            {"name": "X", "date": "2026-12-01", "state": "confirmed", "source": "   "}]})
        self.assertEqual(got[0]["_state"], "proposed")

    def test_the_validation_says_why_it_was_demoted(self):
        out = checks([{"name": "X", "date": "2026-12-01", "state": "confirmed", "set_on": "2026-09-01"}])
        self.assertTrue(any("marked `confirmed` with no `source`" in o for o in out), out)
        self.assertTrue(any("shown as `proposed`" in o for o in out), out)


class Findings(unittest.TestCase):
    def test_a_proposed_date_that_passed(self):
        out = checks([{"name": "X", "date": "2026-09-01", "state": "proposed",
                       "source": "plan section 4", "set_on": "2026-08-01"}])
        self.assertTrue(any("was proposed and has passed without being confirmed or moved" in o
                            for o in out), out)

    def test_an_entry_with_no_set_on(self):
        out = checks([{"name": "X", "date": "2026-12-01", "state": "target"}])
        self.assertTrue(any("no `set_on`" in o for o in out), out)

    def test_two_entries_on_the_same_date(self):
        out = checks([{"name": "Go/no-go", "date": "2026-12-01", "state": "target", "set_on": "2026-09-01"},
                      {"name": "Step one", "date": "2026-12-01", "state": "target", "set_on": "2026-09-01"}])
        same = [o for o in out if "same date" in o]
        self.assertEqual(len(same), 1, out)
        self.assertIn("2026-12-01", same[0])
        self.assertIn("Go/no-go", same[0])
        self.assertIn("Step one", same[0])

    def test_a_done_date_in_the_future(self):
        out = checks([{"name": "X", "date": "2026-12-01", "state": "done",
                       "source": "Dee", "set_on": "2026-09-01"}])
        self.assertTrue(any("marked `done` with a date in the future" in o for o in out), out)

    def test_a_done_date_in_the_past_is_not_a_slip(self):
        # The normal case for a finished milestone, and the reverse of the finding above.
        out = checks([{"name": "X", "date": "2026-09-01", "state": "done",
                       "source": "Dee", "set_on": "2026-08-01"}])
        self.assertEqual(out, [])

    def test_a_clean_list_of_five_is_clean(self):
        out = checks([{"name": "Backend release lands", "date": "2026-10-28", "state": "confirmed",
                       "source": "DEC-12", "set_on": "2026-09-01"},
                      {"name": "Go/no-go", "date": "2026-11-04", "state": "proposed",
                       "source": "plan section 4", "set_on": "2026-09-02"},
                      {"name": "Rollout step one", "date": "2026-11-11", "state": "target",
                       "set_on": "2026-09-02"},
                      {"name": "Rollout step two", "date": "2026-11-18", "state": "target",
                       "set_on": "2026-09-02"},
                      {"name": "Pilot closed", "date": "2026-09-10", "state": "done",
                       "source": "Dee", "set_on": "2026-08-01"}])
        self.assertEqual(out, [])

    def test_a_list_removes_the_card_without_a_milestone_finding(self):
        out = checks([{"name": "X", "date": "2026-12-01", "state": "target", "set_on": "2026-09-01"}])
        self.assertFalse(any("card layout without a milestone" in o for o in out), out)

    def test_each_finding_names_its_entry_where_there_is_more_than_one(self):
        out = checks([{"name": "Go/no-go", "date": "2026-12-01", "state": "target"},
                      {"name": "Step one", "date": "2026-12-08", "state": "target", "set_on": "2026-09-01"}])
        self.assertTrue(any("(Go/no-go)" in o and "no `set_on`" in o for o in out), out)


class NextDate(unittest.TestCase):
    def test_the_next_date_after_today_is_the_earliest_future_one(self):
        ms = ba.milestones({"milestones": [{"name": "Past", "date": "2026-09-01"},
                                           {"name": "Soon", "date": "2026-10-01"},
                                           {"name": "Later", "date": "2026-11-01"}]})
        self.assertEqual(ba.next_milestone(ms, DAY)["name"], "Soon")

    def test_today_itself_is_not_the_next_date(self):
        ms = ba.milestones({"milestones": [{"name": "Today", "date": "2026-09-24"}]})
        self.assertIsNone(ba.next_milestone(ms, DAY))

    def test_no_future_date_is_none(self):
        ms = ba.milestones({"milestones": [{"name": "Past", "date": "2026-09-01"}]})
        self.assertIsNone(ba.next_milestone(ms, DAY))

    def test_the_timeline_is_dates_only_in_order_and_skips_the_undated(self):
        ms = ba.milestones({"milestones": [{"name": "B", "date": "2026-11-01"},
                                           {"name": "Undated"},
                                           {"name": "A", "date": "2026-10-01"}]})
        self.assertEqual(ba.timeline_line(ms), "2026-10-01 -> 2026-11-01")


class CardAndPost(unittest.TestCase):
    def setUp(self):
        self.agenda, _ = build(BASE + FIVE, note_items=ITEMS)
        self.post = build.last_post
        self.block = self.agenda[self.agenda.index("## Milestone"):self.agenda.index("## Release blockers")]

    def test_five_entries_show_five_dated_lines_with_a_state_each(self):
        rows = [l for l in self.block.splitlines() if l.startswith("| **")]
        self.assertEqual(len(rows), 5, self.block)
        for row in rows:
            self.assertTrue(any(f"| {s} |" in row for s in ba.MILESTONE_STATES), row)

    def test_the_card_table_is_sorted_by_date(self):
        rows = [l for l in self.block.splitlines() if l.startswith("| **")]
        self.assertEqual([r.split("|")[1].strip().strip("*") for r in rows],
                         ["Pilot closed", "Backend release lands", "Go/no-go",
                          "Rollout step one", "Rollout step two"])

    def test_the_next_date_after_today_carries_the_days_left(self):
        # 2026-09-24 to 2026-10-28 is 34 days; only that row is marked.
        self.assertIn("| **2026-10-28** · **34 days** |", self.block)
        self.assertEqual(self.block.count("days**"), 1, self.block)

    def test_the_post_is_a_short_list_not_a_table(self):
        block = self.post[self.post.index("**Milestones:**"):]
        self.assertIn("- Backend release lands — 2026-10-28 · confirmed · **34 days** · DEC-12", block)
        self.assertIn("- Go/no-go — 2026-11-04 · proposed", block)
        self.assertNotIn("|---|", block)

    def test_the_dates_only_timeline_is_under_the_list(self):
        self.assertIn("*Sequence: 2026-09-10 -> 2026-10-28 -> 2026-11-04 -> 2026-11-11 -> 2026-11-18*",
                      self.block)

    def test_the_post_carries_the_timeline_too(self):
        self.assertIn("Sequence: 2026-09-10 -> 2026-10-28 -> 2026-11-04 -> 2026-11-11 -> 2026-11-18",
                      self.post.splitlines())

    def test_an_undated_entry_says_so_on_both_surfaces(self):
        # An entry still waiting for a date belongs in the list -- that it has none is the
        # thing to ask about -- and must not render as a blank cell.
        entries = FIVE + "  - name: Second region\n    state: proposed\n    set_on: 2026-09-02\n    decide_by: 2026-12-01\n"
        agenda, _ = build(BASE + entries, note_items=ITEMS)
        block = agenda[agenda.index("## Milestone"):agenda.index("## Release blockers")]
        self.assertIn("| **Second region** | *date not set*; decide by 2026-12-01 | proposed | 2026-09-02 | — |",
                      block.splitlines())
        self.assertIn("- Second region — date not set, decide by 2026-12-01 · proposed",
                      build.last_post.splitlines())

    def test_the_heading_is_plural_for_a_list(self):
        self.assertIn("## Milestones", self.agenda)

    def test_exit_criteria_are_kept_and_say_which_entry_they_belong_to(self):
        # CR-127's `criteria:` survives the move to a list. With more than one entry an
        # unlabelled "Exit criteria:" line could not be attached to a milestone.
        agenda, _ = build(BASE + FIVE.replace("  - name: Go/no-go\n",
                                              "  - name: Go/no-go\n    criteria: plan section 4\n"),
                          note_items=ITEMS)
        self.assertIn("Exit criteria — Go/no-go: plan section 4", agenda.splitlines())


class SingleMilestoneUnchanged(unittest.TestCase):
    # The acceptance bullet and the additivity rule: a project that does not opt in -- one
    # `milestone:` with no `state:` -- renders exactly as it did before CR-149.
    SINGLE = ("milestone:\n  name: Canary to five per cent\n  date: 2026-11-10\n"
              "  set_on: 2026-09-01\n  criteria: plan section 4\n")

    def setUp(self):
        self.agenda, _ = build(BASE + self.SINGLE, note_items=ITEMS)

    def test_the_single_line_form_is_kept(self):
        # Asserted as the WHOLE line, not a substring: a state silently appended to a
        # milestone that declared none is exactly the regression this guards, and it would
        # pass an `assertIn`.
        lines = self.agenda.splitlines()
        self.assertIn("**Canary to five per cent** — 2026-11-10 · **47 days**", lines)
        self.assertIn("Exit criteria: plan section 4", lines)

    def test_no_table_and_no_plural_heading(self):
        block = self.agenda[self.agenda.index("## Milestone"):self.agenda.index("## Release blockers")]
        self.assertNotIn("| Milestone | Date |", block)
        self.assertNotIn("## Milestones", block)
        self.assertNotIn("Sequence:", block)

    def test_no_state_is_appended_where_none_was_declared(self):
        self.assertIn("**Milestone:** Canary to five per cent — 2026-11-10", build.last_post)
        self.assertNotIn("proposed", build.last_post)

    def test_a_declared_state_on_a_single_milestone_is_shown(self):
        agenda, _ = build(BASE + self.SINGLE + "  state: confirmed\n  source: DEC-12\n",
                          note_items=ITEMS)
        self.assertIn("· *confirmed*", agenda)
        self.assertIn("— 2026-11-10 · confirmed", build.last_post)


class NothingDeclaredDisappears(unittest.TestCase):
    """The defect pass: four ways a DECLARED milestone went missing or was misreported.

    The CR exists so a reader can tell a commitment from a proposal. A commitment that is
    not on the card at all, or is on it described as something the config does not say,
    defeats that more completely than any wrong state ever could.
    """

    def test_an_undated_lone_milestone_survives_an_undated_list_entry(self):
        # Both dateless is `None == None` on the duplicate check, which read as the same
        # milestone and dropped the declared `milestone:` block from every surface. The
        # suppression now needs a date to compare.
        got = ba.milestones({"milestones": [{"name": "Second region"}],
                             "milestone": {"name": "Canary", "decide_by": "2026-12-01"}})
        self.assertEqual(sorted(e.get("name") for e in got), ["Canary", "Second region"])

    def test_an_undated_lone_milestone_survives_an_undated_list_on_the_card(self):
        # The card is where the loss was visible: the lone block had a name and a
        # decide-by and neither appeared.
        agenda, _ = build(BASE + "milestones:\n  - name: Second region\n    set_on: 2026-09-02\n"
                          + "milestone:\n  name: Canary\n  decide_by: 2026-12-01\n", note_items=ITEMS)
        block = agenda[agenda.index("## Milestone"):agenda.index("## Release blockers")]
        self.assertIn("Canary", block)
        self.assertIn("Second region", block)
        self.assertIn("Canary", build.last_post)

    def test_a_lone_milestone_is_still_suppressed_when_the_dates_match(self):
        # The fix must not turn the duplicate back on: a dated lone block whose date the
        # list already holds is one milestone, not two.
        got = ba.milestones({"milestones": [{"name": "Beta", "date": "2026-12-01"}],
                             "milestone": {"name": "Beta", "date": "2026-12-01"}})
        self.assertEqual(len(got), 1)

    def test_an_unparseable_date_is_a_finding(self):
        # `as_date` returns None for it, so every surface said "date not set" -- a false
        # statement about a config that declared a date. The validation now names it.
        out = checks([{"name": "X", "date": "next Tuesday", "state": "target", "set_on": "2026-09-01"}])
        self.assertTrue(any("not a date the generator can read" in o and "next Tuesday" in o
                            for o in out), out)

    def test_an_unparseable_date_is_never_called_unset(self):
        out = checks([{"name": "X", "date": "next Tuesday", "state": "target", "set_on": "2026-09-01"}])
        self.assertFalse(any("has no date" in o or "date not set" in o for o in out), out)

    def test_an_unparseable_date_renders_as_written_on_both_surfaces(self):
        entries = FIVE + "  - name: Second region\n    date: next Tuesday\n    set_on: 2026-09-02\n"
        agenda, _ = build(BASE + entries, note_items=ITEMS)
        block = agenda[agenda.index("## Milestone"):agenda.index("## Release blockers")]
        self.assertIn("| **Second region** | **next Tuesday** (unreadable date) | proposed | 2026-09-02 | \u2014 |",
                      block.splitlines())
        self.assertNotIn("date not set", block)
        self.assertIn("- Second region \u2014 next Tuesday (unreadable date) \u00b7 proposed",
                      build.last_post.splitlines())

    def test_a_single_unparseable_date_renders_as_written_and_does_not_crash(self):
        # The single-milestone renderer parsed the date itself and raised on this value.
        agenda, _ = build(BASE + "milestone:\n  name: Canary\n  date: next Tuesday\n  set_on: 2026-09-01\n",
                          note_items=ITEMS)
        self.assertIn("**Canary** \u2014 **next Tuesday** (not a date the generator can read)",
                      agenda.splitlines())
        self.assertNotIn("date not set", agenda)

    def test_a_non_mapping_list_item_is_a_finding(self):
        # `- Go/no-go` instead of `- name: Go/no-go`. It is dropped from the card, the post
        # and the timeline, so without a finding the milestone vanishes in silence.
        out = checks(["Go/no-go", {"name": "Beta", "date": "2026-11-01", "state": "target",
                                   "set_on": "2026-09-01"}])
        self.assertTrue(any("Go/no-go" in o and "is not a mapping" in o for o in out), out)

    def test_every_non_mapping_list_item_is_reported(self):
        out = checks(["Go/no-go", "Rollout step one",
                      {"name": "Beta", "date": "2026-11-01", "state": "target", "set_on": "2026-09-01"}])
        bad = [o for o in out if "is not a mapping" in o]
        self.assertEqual(len(bad), 2, out)

    def test_a_non_mapping_item_is_a_finding_on_the_generated_card(self):
        agenda, _ = build(BASE + "milestones:\n  - Go/no-go\n  - name: Beta\n    date: 2026-11-01\n"
                          "    set_on: 2026-09-01\n    state: target\n", note_items=ITEMS)
        self.assertIn("is not a mapping", agenda)

    def test_a_well_formed_list_reports_no_mapping_finding(self):
        out = checks([{"name": "Beta", "date": "2026-11-01", "state": "target", "set_on": "2026-09-01"}])
        self.assertFalse(any("is not a mapping" in o for o in out), out)

    def test_the_card_and_the_validation_agree_about_one_declared_date(self):
        # Defect 4: the single-milestone renderer kept its own `strptime` while `as_date`'s
        # docstring promised one reader, so that the date the card runs toward and the date
        # the validation complains about cannot disagree. The observable promise is that
        # agreement, asserted over values that read differently to the two parsers: the
        # renderer raised on the unreadable one and would not have raised on a `date:` key
        # written with surrounding whitespace.
        for value, readable in ((" 2026-11-10 ", False), ("2026-11-10", True),
                                ("next Tuesday", False), ("2026-13-01", False)):
            cf = {"milestone": {"name": "Canary", "date": value, "set_on": "2026-09-01"},
                  "layout": "card", "_root": Path(tempfile.gettempdir())}
            resolved = ba.milestones(cf)[0]["_date"] is not None
            self.assertEqual(resolved, readable, value)
            findings = ba.config_checks(cf, [], DAY, None)
            unreadable = any("not a date the generator can read" in f for f in findings)
            # The validation says unreadable for exactly the values the card cannot place.
            self.assertEqual(unreadable, not readable, (value, findings))
            agenda, _ = build(BASE + f"milestone:\n  name: Canary\n  date: \"{value}\"\n"
                              "  set_on: 2026-09-01\n", note_items=ITEMS)
            # And the card's own line matches that verdict rather than its own parse.
            self.assertEqual("**47 days**" in agenda, readable, value)
            self.assertEqual("not a date the generator can read" in agenda, not readable, value)


class FindingsThatOnlyCR119Caught(unittest.TestCase):
    """Defect 5: two mutations of CR-149's own code that this file passed green.

    Both were caught only by `tests/test_cr119_config_checks.py`, which exists to assert
    CR-119's behaviour and happens to cover these. A CR's own file has to fail when the
    CR's own code is broken, so the two readings are asserted here too.
    """

    def test_a_passed_date_with_no_declared_state_keeps_the_CR_107_wording(self):
        # The wording split: the sharper "was proposed and has passed" sentence belongs to
        # an entry that DECLARED itself a proposal. An entry that declares no state has
        # said nothing about being one, and the card has quoted the plain sentence since
        # CR-119. Collapsing the condition to always-sharper passed this whole file.
        out = checks([{"name": "X", "date": "2026-09-01", "set_on": "2026-08-01"}])
        self.assertIn("milestone date 2026-09-01 has passed: move it, or declare "
                      "the next milestone", out)
        self.assertFalse(any("was proposed and has passed" in o for o in out), out)

    def test_a_card_with_no_milestone_at_all_is_still_a_finding(self):
        # The finding moved to `not ms_all` when the list arrived, and nothing in this file
        # asserted it: deleting it passed. A card with nothing to run toward is the state
        # CR-107 added the milestone for.
        out = checks([])
        self.assertIn("card layout without a milestone: the card has nothing to run toward", out)

    def test_a_list_layout_with_no_milestone_is_not_that_finding(self):
        # The finding is the card's: a list-layout agenda has never run toward a date.
        out = checks([], layout="list")
        self.assertFalse(any("card layout without a milestone" in o for o in out), out)


class AsDate(unittest.TestCase):
    def test_a_string_a_date_and_a_non_date(self):
        self.assertEqual(ba.as_date("2026-10-01"), datetime.date(2026, 10, 1))
        self.assertEqual(ba.as_date(datetime.date(2026, 10, 1)), datetime.date(2026, 10, 1))
        for bad in (None, "", "soon", 7, "2026-13-01"):
            self.assertIsNone(ba.as_date(bad), bad)


if __name__ == "__main__":
    unittest.main()
