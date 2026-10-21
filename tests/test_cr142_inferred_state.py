"""CR-142: an inference is a tracked state, and an item is closed only from its own source.

`*inferred: <what>*` is part of the carried-line contract; an unconfirmed inference is the
same state as CR-147's *cannot be checked*, so it comes off the card and ages out on the
same schedule, and after two sessions the agenda asks for it under *Confirm or drop*,
owner first. `/ops check` reports a decision whose note still carries the marker. The
close-out rule -- open the source before writing an item closed -- is a SKILL.md rule and
is checked as documented contract. Invented data.

    python3 -m unittest discover -s tests
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "skills" / "ops"
sys.path.insert(0, str(OPS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_agenda as ba  # noqa: E402
import hygiene_check as hc  # noqa: E402
from test_cr101_agenda_draft import build  # noqa: E402

SKILL = (OPS / "SKILL.md").read_text(encoding="utf-8")

CARD = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n      layout: card\n"
        "people:\n  - name: Ann\n  - name: Bob\n")
LIST = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
        "people:\n  - name: Ann\n  - name: Bob\n")

REPO_DECL = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
             "      reads: [issues, pulls]\n")

# One carried line per owner, each naming an identifier AND carrying an inference: the
# case CR-147's *cannot be checked* table cannot hold, because these lines can be read.
INFERRED_ITEMS = ("- [blocker] **Payment webhook fails** — #12 *inferred: the release day* · **Bob**\n"
                  "- [dependency] **Backend answer on refunds** — TICK-9 *inferred: the owner* · **Ann**\n")

# The other, commoner shape: a guess that names NOTHING to read. An owner, a release day
# and which items belong together are exactly the phrases a garbled recording produces,
# and none of them comes with an id.
NO_ID_ITEM = ("- [dependency] **Backend answer on refunds** — asked in the room"
              " *inferred: the owner* · **Ann**\n")

CLOSED_ISSUE = {"number": 12, "title": "Payment webhook retry", "state": "CLOSED",
                "createdAt": "2026-09-01T09:00:00Z", "updatedAt": "2026-10-16T11:02:00Z",
                "closedAt": "2026-10-16T11:02:00Z", "assignees": [{"login": "bob"}]}


def details():
    return (Path(build.last_meetings) / "260924-agenda-details-daily-standup.md").read_text(encoding="utf-8")


class TheMarkerIsRead(unittest.TestCase):
    """Proposal 1: the marker is the contract, in all three places it is written."""

    def test_the_marker_puts_a_carried_line_in_the_unconfirmed_state(self):
        rows = ba.unconfirmed([("[dependency] **Refunds**", "TICK-9 *inferred: the owner* · **Ann**")])
        self.assertEqual([r[2] for r in rows], ["unconfirmed inference"])

    def test_the_marker_is_registered_so_no_caller_has_to_pass_it(self):
        # CR-147 left `CONFIRM_MARKERS` as the hook; the point of registering is that a
        # caller with no `extra_markers` already sees the state.
        self.assertTrue(any(p.search("*inferred: the owner*") for p in ba.CONFIRM_MARKERS))

    def test_a_line_with_an_identifier_and_no_marker_is_not_in_the_state(self):
        self.assertEqual(ba.unconfirmed([("[dependency] **Refunds**", "TICK-9 · **Ann**")]), [])

    def test_inferred_reads_a_carried_line_a_decision_note_and_prose(self):
        self.assertTrue(ba.inferred("TICK-9 *inferred: the release day* · **Ann**"))
        self.assertTrue(ba.inferred("- Release moves to Thursday *inferred: the release day*"))
        self.assertTrue(ba.inferred("Inferred: which items belonged together"))
        self.assertFalse(ba.inferred("TICK-9 · **Ann**"))

    def test_the_marker_is_case_insensitive_in_prose(self):
        self.assertTrue(ba.inferred("inferred: the owner"))

    def test_a_confirmation_retires_the_marker(self):
        # Proposal 5 from the reader's side: once the confirming source is on the line the
        # text is no longer an open inference, even before the next summary rewrites it.
        self.assertFalse(ba.inferred("*inferred: the owner* *confirmed: TICK-9 assignee*"))
        self.assertEqual(ba.unconfirmed(
            [("[dependency] **Refunds**",
              "TICK-9 *inferred: the owner* *confirmed: Ann said so* · **Ann**")]), [])


class AnUnconfirmedInferenceAges(unittest.TestCase):
    """Proposal 2: two sessions, then *Confirm or drop*, owner first."""

    def test_nothing_is_listed_before_the_threshold(self):
        items = [("[dependency] **Refunds**", "TICK-9 *inferred: the owner* · **Ann**")]
        self.assertEqual(ba.confirm_or_drop(items, {ba.key(items[0][0]): 2}), [])

    def test_a_line_past_the_threshold_is_listed_with_its_session_count(self):
        items = [("[dependency] **Refunds**", "TICK-9 *inferred: the owner* · **Ann**")]
        rows = ba.confirm_or_drop(items, {ba.key(items[0][0]): 3})
        self.assertEqual([(r[0], r[2]) for r in rows], [("[dependency] **Refunds**", 3)])

    def test_the_threshold_is_the_one_cr147_set(self):
        # The CR's words are "after two sessions"; the mechanism is CR-147's, not a second one.
        items = [("**Refunds**", "TICK-9 *inferred: x* · **Ann**")]
        self.assertEqual(ba.CONFIRM_SESSIONS, 2)
        for n, listed in ((1, False), (2, False), (3, True)):
            with self.subTest(sessions=n):
                self.assertEqual(bool(ba.confirm_or_drop(items, {ba.key(items[0][0]): n})), listed)

    def test_a_confirmed_line_is_never_listed(self):
        items = [("**Refunds**", "TICK-9 *inferred: the owner* *confirmed: TICK-9 assignee* · **Ann**")]
        self.assertEqual(ba.confirm_or_drop(items, {ba.key(items[0][0]): 9}), [])

    def test_a_line_with_no_marker_is_never_listed(self):
        # the other unconfirmed state (CR-147's, no identifier) is not this section's business
        items = [("**Waiting on the other team**", "· **Ann**")]
        self.assertEqual(ba.confirm_or_drop(items, {ba.key(items[0][0]): 9}), [])

    def test_the_order_is_by_owner_not_by_item(self):
        items = [("**Zebra crossing**", "#1 *inferred: a* · **Ann**"),
                 ("**Apples**", "#2 *inferred: b* · **Bob**"),
                 ("**Mangoes**", "#3 *inferred: c* · **Ann**")]
        rows = ba.confirm_or_drop(items, {ba.key(l): 5 for l, _r in items})
        self.assertEqual([ba.owner_of(l, r) for l, r, _n in rows], ["Ann", "Ann", "Bob"])
        # within one owner, by the item -- so a person reads their own rows in one block
        self.assertEqual([ba.item_of(l, r) for l, r, _n in rows][:2],
                         ["**Mangoes**", "**Zebra crossing**"])

    def test_an_unowned_line_sorts_last(self):
        # The owner is **Vee** and not Bob, and that is what makes this bind (defect
        # pass): sorted on the owner's name alone "unowned" already falls after "bob",
        # so a fixture with Bob asserted nothing about the UNOWNED-last rule. "Vee"
        # sorts AFTER "UNOWNED" alphabetically, so only the rule itself puts the
        # nameless line last.
        items = [("**No name here**", "#1 *inferred: a*"),
                 ("**Apples**", "#2 *inferred: b* · **Vee**")]
        rows = ba.confirm_or_drop(items, {ba.key(l): 5 for l, _r in items})
        self.assertEqual([ba.owner_of(l, r) for l, r, _n in rows], ["Vee", "UNOWNED"])


class TheAgendaAsksForIt(unittest.TestCase):
    """Proposal 2 end to end: the card asks, and nothing leaves without a trace."""

    def test_the_card_lists_an_aged_inference_under_confirm_or_drop(self):
        agenda, _ = build(CARD, note_items=INFERRED_ITEMS,
                          notes={"260918": INFERRED_ITEMS, "260919": INFERRED_ITEMS,
                                 "260921": INFERRED_ITEMS})
        self.assertIn("## Confirm or drop (2)", agenda)
        # what was inferred, so the room asks about the guess and not about the item
        self.assertIn("the release day", agenda)
        self.assertIn("the owner", agenda)

    def test_the_card_section_is_owner_first(self):
        # Bob's item sorts BEFORE Ann's alphabetically, so a section ordered by item and
        # one ordered by owner cannot both pass this.
        note = ("- [blocker] **Android build** — #12 *inferred: the release day* · **Bob**\n"
                "- [dependency] **Refund flow** — TICK-9 *inferred: the owner* · **Ann**\n")
        agenda, _ = build(CARD, note_items=note,
                          notes={"260918": note, "260919": note, "260921": note})
        block = agenda.split("## Confirm or drop")[1].split("\n## ")[0]
        rows = [l for l in block.splitlines()
                if l.startswith("| ") and "---" not in l and "| Item |" not in l]
        self.assertEqual(len(rows), 2)
        self.assertIn("| Refund flow | Ann |", rows[0])
        self.assertIn("| Android build | Bob |", rows[1])

    def test_an_inference_comes_off_the_card_from_its_second_session(self):
        agenda, _ = build(CARD, note_items=INFERRED_ITEMS, notes={"260921": INFERRED_ITEMS})
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertNotIn("**Backend answer on refunds**", deps)

    def test_a_first_session_inference_is_still_on_the_card(self):
        # the room raised it last night; this pass may not unmake what the room created
        agenda, _ = build(CARD, note_items=INFERRED_ITEMS)
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertIn("**Backend answer on refunds**", deps)

    def test_a_line_off_the_card_but_not_yet_aged_leaves_a_trace(self):
        # the hole this CR must not leave: the line names an id, so CR-147's
        # *cannot be checked* table never held it.
        #
        # The fixture is NOT `INFERRED_ITEMS`, and that is the point of the last
        # assertion (defect pass): in that pair Ann's item also sorts first by item, so
        # an ordering assertion written against it passed under either sort and asserted
        # nothing. Here Bob's *Android build* sorts BEFORE Ann's *Refund flow* by item
        # and AFTER it by owner, so the two orderings cannot both satisfy this.
        note = ("- [blocker] **Android build** — #12 *inferred: the release day* · **Bob**\n"
                "- [dependency] **Refund flow** — TICK-9 *inferred: the owner* · **Ann**\n")
        build(CARD, note_items=note, notes={"260921": note})
        d = details()
        trace = d.split("## Unconfirmed inferences, off the card (2)")[1]
        self.assertIn("| Refund flow | Ann | 2 |", trace)
        self.assertIn("| Android build | Bob | 2 |", trace)
        # owner first here too, as on the card -- Ann's row before Bob's, although
        # Bob's item is the one that sorts first alphabetically
        self.assertLess(trace.index("| Refund flow | Ann |"),
                        trace.index("| Android build | Bob |"))

    def test_a_confirmed_inference_stays_on_the_card(self):
        note = ("- [dependency] **Backend answer on refunds** — TICK-9 *inferred: the owner*"
                " *confirmed: Ann named the owner in her minute* · **Ann**\n")
        agenda, _ = build(CARD, note_items=note, notes={"260921": note})
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertIn("**Backend answer on refunds**", deps)
        self.assertNotIn("## Confirm or drop", agenda)

    def test_a_line_with_no_marker_is_untouched(self):
        plain = "- [dependency] **Backend answer on refunds** — TICK-9 · **Ann**\n"
        agenda, _ = build(CARD, note_items=plain,
                          notes={"260918": plain, "260919": plain, "260921": plain})
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertIn("**Backend answer on refunds**", deps)
        self.assertNotIn("## Confirm or drop", agenda)

    def test_the_list_layout_keeps_every_line_and_still_asks(self):
        # additive: the list layout's carried table is the full list by definition
        agenda, _ = build(LIST, note_items=INFERRED_ITEMS,
                          notes={"260918": INFERRED_ITEMS, "260919": INFERRED_ITEMS,
                                 "260921": INFERRED_ITEMS})
        self.assertIn("## Carried forward", agenda)
        self.assertIn("Backend answer on refunds", agenda.split("## Confirm or drop")[0])
        self.assertIn("## Confirm or drop (2)", agenda)


class AnInferenceNamingNothingIsStillAsked(unittest.TestCase):
    """Acceptance bullet 1, for the commonest shape of inference there is.

    Proposal 2 is that *a line with the marker reappears on the agenda until confirmed or
    dropped*. Most inferences name no identifier -- an owner, a release day, which items
    belong together are exactly the phrases a garbled recording produces -- so the state
    has to be decided by the MARKER and not by whether the line can be read. Routing those
    lines into CR-147's *cannot be checked* table instead meant the agenda stopped asking
    about the guess after two sessions rather than asking harder.
    """

    def test_the_marker_decides_the_state_not_the_identifier(self):
        rows = ba.unconfirmed([("[dependency] **Refunds**", "asked in the room *inferred: the owner*")])
        self.assertEqual([r[2] for r in rows], ["unconfirmed inference"])

    def test_it_reaches_confirm_or_drop_with_no_identifier_on_the_line(self):
        items = [("[dependency] **Refunds**", "asked in the room *inferred: the owner* · **Ann**")]
        rows = ba.confirm_or_drop(items, {ba.key(items[0][0]): 3})
        self.assertEqual([(r[0], r[2]) for r in rows], [("[dependency] **Refunds**", 3)])

    def test_the_card_asks_about_it_and_names_the_guess(self):
        # the whole CR, end to end, on a line with nothing to read: six sittings and the
        # question is still on the card
        notes = {f"26091{d}": NO_ID_ITEM for d in (4, 5, 6, 7, 8)}
        agenda, _ = build(CARD, note_items=NO_ID_ITEM, notes=notes)
        self.assertIn("## Confirm or drop (1)", agenda)
        block = agenda.split("## Confirm or drop")[1].split("\n## ")[0]
        self.assertIn("| Backend answer on refunds | Ann | the owner |", block)

    def test_the_threshold_still_holds_for_a_line_with_no_identifier(self):
        # it is asked ABOUT, not asked about early: CR-147's schedule is unchanged
        agenda, _ = build(CARD, note_items=NO_ID_ITEM, notes={"260921": NO_ID_ITEM})
        self.assertNotIn("## Confirm or drop", agenda)

    def test_a_line_with_no_marker_and_no_identifier_keeps_cr147s_reason(self):
        # the half of the routing that must NOT change: CR-147's own case is untouched
        rows = ba.unconfirmed([("[dependency] **Waiting on the other team**", "· **Ann**")])
        self.assertEqual([r[2] for r in rows], ["no identifier, nothing to read"])

    def test_the_list_layout_asks_too_and_still_keeps_the_line(self):
        # additive, on the layout the CR must not disturb: the section adds a question
        # and removes nothing, so the carried-forward table still holds the line
        notes = {f"26091{d}": NO_ID_ITEM for d in (4, 5, 6, 7, 8)}
        agenda, _ = build(LIST, note_items=NO_ID_ITEM, notes=notes)
        self.assertIn("## Confirm or drop (1)", agenda)
        self.assertIn("Backend answer on refunds", agenda.split("## Confirm or drop")[0])

    def test_it_is_listed_once_not_twice_while_it_waits(self):
        # CR-147's rule is one section per line. A no-identifier inference is in both
        # states at once, and the *cannot be checked* table is the one that names it --
        # with its own card column, so nothing about it is silent.
        build(CARD, note_items=NO_ID_ITEM, notes={"260921": NO_ID_ITEM})
        d = details()
        self.assertIn("cannot be checked (1)", d)
        self.assertIn("no — awaiting its owner's word", d)
        self.assertNotIn("## Unconfirmed inferences, off the card", d)


class AClosedLineIsNotAlsoAskedAbout(unittest.TestCase):
    """CR-147's rule, applied to this CR's section: one statement per item.

    A line whose own source says closed is announced under *Closed in the data since the
    last meeting* and is gone. Asking the room to confirm its guess on the same page is
    two statements about one item, and the one that reads as an open question is wrong.
    """

    def setUp(self):
        self.note = ("- [blocker] **Payment webhook fails** — #12 *inferred: the release day*"
                     " · **Bob**\n")
        self.repo = {"reads": ["issues", "pulls"], "issues": [CLOSED_ISSUE]}

    def agenda_for(self, notes):
        agenda, _ = build(CARD + REPO_DECL, note_items=self.note, notes=notes, repo=self.repo)
        return agenda

    def test_an_aged_line_the_data_closed_is_announced_closed_and_not_asked(self):
        agenda = self.agenda_for({"260918": self.note, "260919": self.note, "260921": self.note})
        self.assertIn("Closed in the data since the last meeting:", agenda)
        self.assertIn("#12", agenda.split("## Milestone")[0])
        self.assertNotIn("## Confirm or drop", agenda)

    def test_it_is_not_pushed_into_the_off_card_trace_instead(self):
        # filtering it out of one section must not move the double statement to the other
        self.agenda_for({"260918": self.note, "260919": self.note, "260921": self.note})
        d = details()
        self.assertIn("## Closed in the data since the last meeting (1)", d)
        self.assertNotIn("## Unconfirmed inferences, off the card", d)

    def test_a_line_not_yet_aged_and_closed_in_the_data_is_also_stated_once(self):
        self.agenda_for({"260921": self.note})
        d = details()
        self.assertIn("## Closed in the data since the last meeting (1)", d)
        self.assertNotIn("## Unconfirmed inferences, off the card", d)

    def test_an_open_source_leaves_the_question_exactly_where_it_was(self):
        # the control: the filter keys on the CLOSE, not on the repo being declared
        agenda, _ = build(CARD + REPO_DECL, note_items=self.note,
                          notes={"260918": self.note, "260919": self.note, "260921": self.note},
                          repo={"reads": ["issues", "pulls"],
                                "issues": [dict(CLOSED_ISSUE, state="OPEN", closedAt=None)]})
        self.assertIn("## Confirm or drop (1)", agenda)
        self.assertNotIn("Closed in the data since the last meeting:", agenda)


class TheCheckReportsADecision(unittest.TestCase):
    """Proposal 2's second half: `/ops check` reports a decision whose note carries it."""

    def write(self, body: str):
        d = Path(self.tmp.name)
        (d / "260924-daily-standup.md").write_text(body, encoding="utf-8")
        return d

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_an_unconfirmed_inference_in_a_decision_is_a_finding(self):
        d = self.write("# Standup\n\n## Decisions\n\n"
                       "- Release moves to Thursday *inferred: the release day*\n")
        found = hc.check_inferred(d)
        self.assertEqual([(f["kind"], f["line"]) for f in found], [("inferred", 5)])
        self.assertIn("the release day", found[0]["message"])

    def test_a_confirmed_inference_is_not_a_finding(self):
        d = self.write("# Standup\n\n## Decisions\n\n"
                       "- Bob owns the retry *inferred: the owner* *confirmed: TICK-9 assignee*\n")
        self.assertEqual(hc.check_inferred(d), [])

    def test_a_decision_with_no_marker_is_not_a_finding(self):
        d = self.write("# Standup\n\n## Decisions\n\n- Release moves to Thursday\n")
        self.assertEqual(hc.check_inferred(d), [])

    def test_the_marker_outside_a_decisions_section_is_not_this_finding(self):
        # the carried line's own marker is the agenda's business, not the register's
        d = self.write("# Standup\n\n## Carried forward\n\n"
                       "- [dependency] **Refunds** — TICK-9 *inferred: the owner* · **Ann**\n")
        self.assertEqual(hc.check_inferred(d), [])

    def test_a_heading_after_the_decisions_section_ends_it(self):
        d = self.write("# Standup\n\n## Decisions\n\n- Settled\n\n## Next Steps\n\n"
                       "- Something *inferred: not a decision*\n")
        self.assertEqual(hc.check_inferred(d), [])

    def test_the_swedish_heading_is_read_too(self):
        d = self.write("# Standup\n\n## Beslut\n\n- Släpp flyttas till torsdag *inferred: dagen*\n")
        self.assertEqual(len(hc.check_inferred(d)), 1)

    def test_a_decision_register_heading_is_read(self):
        d = self.write("# Register\n\n### Decision register\n\n"
                       "| 2026-10-19 | Thursday *inferred: the release day* | Ann |\n")
        self.assertEqual(len(hc.check_inferred(d)), 1)

    def test_the_check_is_declared_and_runs_from_the_command_line(self):
        self.assertIn("inferred", hc.CHECKS)
        d = self.write("# Standup\n\n## Decisions\n\n- Thursday *inferred: the release day*\n")
        self.assertEqual(len(hc.run(d, only=("inferred",))), 1)

    def test_the_other_checks_are_unchanged_by_the_new_one(self):
        # additive: a folder with no marker gives the same findings it gave before
        d = self.write("# Standup\n\n## Decisions\n\n- Release moves to Thursday\n")
        self.assertEqual(hc.run(d), hc.run(d, only=tuple(c for c in hc.CHECKS if c != "inferred")))

    def test_a_hash_comment_in_a_fence_does_not_end_the_decisions_section(self):
        # defect pass: `HEADING` matches a `# ...` comment line, so a fenced code sample
        # inside a decisions section closed it and the REAL inference below the fence was
        # missed entirely -- the one thing this check exists to catch.
        d = self.write("# Standup\n\n## Decisions\n\n"
                       "- Settled\n\n```sh\n# set the release day\nbuild --day thu\n```\n\n"
                       "- Release moves to Thursday *inferred: the release day*\n")
        found = hc.check_inferred(d)
        self.assertEqual([(f["kind"], f["line"]) for f in found], [("inferred", 12)])

    def test_an_illustrative_marker_inside_a_fence_is_not_a_finding(self):
        # the other half: a document explaining the convention is not a decision register
        d = self.write("# Standup\n\n## Decisions\n\n"
                       "- Settled\n\n```md\n- Thursday *inferred: the release day*\n```\n")
        self.assertEqual(hc.check_inferred(d), [])

    def test_a_fence_opened_in_a_decisions_section_does_not_leak_past_a_heading(self):
        # a fence closes where it closes; the section boundary is still the heading's
        d = self.write("# Standup\n\n## Decisions\n\n```md\n*inferred: a*\n```\n\n"
                       "## Next Steps\n\n- Something *inferred: not a decision*\n")
        self.assertEqual(hc.check_inferred(d), [])


class OneReaderForTheMarker(unittest.TestCase):
    """Defect pass: the pattern and the words it names have ONE definition.

    The module comment on the import already states the principle for the marker itself;
    `*inferred: <what>*` was nevertheless read by `INFERRED_WHAT` here and by an identical
    inline regex in the agenda, which is exactly how the check and the *Confirm or drop*
    column could come to quote different words off one line.
    """

    def test_the_check_follows_the_agendas_definition_not_a_copy(self):
        # `assertIs` would NOT bind this: `re.compile` caches by pattern string, so a
        # second `re.compile` of the same text hands back the very same object and the
        # identity assertion passes against a duplicated definition. What binds it is
        # redefining the agenda's reader and requiring the check's finding to follow --
        # which it can only do if it has no copy of its own.
        line = "- Thursday *inferred: the release day*"
        d = Path(self.tmp.name)
        (d / "260924-daily-standup.md").write_text(f"# S\n\n## Decisions\n\n{line}\n",
                                                   encoding="utf-8")
        before = hc.check_inferred(d)[0]["message"]
        self.assertIn("the release day", before)
        original = ba.inferred_what
        ba.inferred_what = lambda text, default="not stated": "REDEFINED-BY-THE-AGENDA"
        self.addCleanup(lambda: setattr(ba, "inferred_what", original))
        self.assertIn("REDEFINED-BY-THE-AGENDA", hc.check_inferred(d)[0]["message"])

    def test_the_agenda_exports_one_reader_for_the_words(self):
        self.assertEqual(ba.inferred_what("TICK-9 *inferred: the release day* · **Ann**"),
                         "the release day")

    def test_a_marker_naming_nothing_reads_as_not_stated(self):
        self.assertEqual(ba.inferred_what("TICK-9 *inferred* · **Ann**"), "not stated")

    def test_the_card_and_the_finding_quote_the_same_words(self):
        # one line, both readers: the column and the finding message must agree
        line = "- Release moves to Thursday *inferred: which items belonged together*"
        d = Path(self.tmp.name)
        (d / "260924-daily-standup.md").write_text(f"# S\n\n## Decisions\n\n{line}\n",
                                                   encoding="utf-8")
        self.assertIn(ba.inferred_what(line), hc.check_inferred(d)[0]["message"])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)


class TheDocumentedRules(unittest.TestCase):
    """Proposals 1, 3 and 4 are rules a person follows; the contract is the skill."""

    def test_the_marker_is_documented_in_all_three_places_it_is_written(self):
        block = SKILL.split("What was inferred is marked as inferred (CR-142)")[1][:2000]
        self.assertIn("*inferred: <what>*", block)
        self.assertIn("in a decision's note", block)
        self.assertIn("`Inferred:`", block)

    def test_the_close_out_step_opens_the_source_and_names_it(self):
        # proposal 3, in the post-meeting steps -- the same day, where a close is written
        loop = SKILL.split("### After the meeting, the same day")[1].split("### What each step must not do")[0]
        self.assertIn("Close from the source (CR-142)", loop)
        self.assertIn("open its source and read the state", loop)
        self.assertIn("Say which source was read", loop)
        self.assertIn("not a source", loop)        # "said in the room" is a reason to look

    def test_an_unreadable_source_does_not_close_the_item(self):
        loop = SKILL.split("Close from the source (CR-142)")[1][:1200]
        self.assertIn("not closed", loop)

    def test_a_paraphrase_quotes_the_title_and_a_rewording_needs_the_owner(self):
        block = SKILL.split("A carried line's text does not replace its source's title (CR-142)")[1][:1200]
        self.assertIn("quote the title once", block)
        self.assertIn("needs the owner's word", block)

    def test_a_confirmed_inference_loses_its_marker_with_the_source(self):
        block = SKILL.split("A confirmed inference loses its marker in the next summary")[1][:800]
        self.assertIn("*confirmed:", block)

    def test_the_ageing_and_the_section_are_documented(self):
        block = SKILL.split("An unconfirmed inference ages, exactly as a line nothing can be read about does (CR-142)")[1][:1800]
        self.assertIn("Confirm or drop", block)
        self.assertIn("owner\n  first", block.replace("**", ""))

    def test_the_check_is_documented_under_the_check_subcommand(self):
        block = SKILL.split("### `check <folder>`")[1].split("### `check` --")[0]
        self.assertIn("an unconfirmed inference in a decision", block)
        self.assertIn("inferred", block)
        self.assertIn("Report only", block)

    def test_the_marker_and_not_the_identifier_decides_the_state(self):
        # defect pass: the one rule a reader of this section would otherwise get wrong,
        # because the paragraph it sits under is written from CR-147's side
        block = SKILL.split("An unconfirmed inference ages, exactly as a line nothing"
                            " can be read about does (CR-142)")[1][:2600]
        self.assertIn("The marker decides the state, not the identifier",
                      block.replace("**", ""))
        self.assertIn("whether or not it names one", block)

    def test_a_line_the_data_closed_is_documented_as_not_also_asked(self):
        block = SKILL.split("An unconfirmed inference ages, exactly as a line nothing"
                            " can be read about does (CR-142)")[1][:2600]
        self.assertIn("A line the data closed is not also asked about",
                      block.replace("**", ""))
        self.assertIn("Closed in the data since the last meeting", block)

    def test_the_fence_rule_is_documented_for_the_check(self):
        block = SKILL.split("`inferred` (CR-142): an unconfirmed inference in a decision")[1][:1600]
        self.assertIn("fenced block is skipped", block.replace("**", ""))


class NothingElseMoved(unittest.TestCase):
    """Additive: a project that never writes the marker sees the agenda it saw before."""

    def test_an_agenda_with_no_marker_has_no_new_section(self):
        plain = "- [dependency] **Backend answer on refunds** — TICK-9 · **Ann**\n"
        agenda, _ = build(CARD, note_items=plain, notes={"260921": plain})
        self.assertNotIn("Confirm or drop", agenda)
        self.assertNotIn("Unconfirmed inferences", agenda + details())

    def test_unconfirmed_still_answers_cr147s_own_case(self):
        rows = ba.unconfirmed([("[dependency] **Waiting on the other team**", "· **Ann**")])
        self.assertEqual([r[2] for r in rows], ["no identifier, nothing to read"])

    def test_an_extra_marker_can_still_be_passed_in(self):
        rows = ba.unconfirmed([("**Refunds**", "TICK-9 *guessed: the owner* · **Ann**")],
                              extra_markers=(re.compile(r"\*guessed\b", re.I),))
        self.assertEqual([r[2] for r in rows], ["unconfirmed inference"])


if __name__ == "__main__":
    unittest.main()
