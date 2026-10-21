"""CR-147: a carried line is re-read from its source before the card is built.

CR-141 made the match reliable and SUGGESTS a close; this ACTS, and only on a certain
one -- an issue in a closed state, a merged pull request that names the id, a done
ticket. A label change never closes. A line nobody can read anything about is not
asserted as live. A source that could not be read removes nothing. Invented data.

    python3 -m unittest discover -s tests
"""

import datetime
import json
import sys
import unittest
from pathlib import Path

OPS = Path(__file__).resolve().parent.parent / "skills" / "ops"
sys.path.insert(0, str(OPS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_agenda as ba  # noqa: E402
from test_cr101_agenda_draft import build  # noqa: E402

CARD = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n      layout: card\n"
        "people:\n  - name: Ann\n  - name: Bob\n")
# The LIST layout: carry-forward on, no `layout: card`. CR-147 is additive, so this
# must behave as it did before the CR except where the CR says otherwise.
LIST = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
        "people:\n  - name: Ann\n  - name: Bob\n")
REPO_DECL = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
             "      reads: [issues, pulls]\n")
JIRA_DECL = "external_systems:\n  jira:\n    - project: TICK\n"
# One `external_systems:` key, both sources under it: two top-level keys of the same
# name would silently leave only the second.
BOTH_DECL = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
             "      reads: [issues, pulls]\n  jira:\n    - project: TICK\n")

# One carried line per kind, each naming its own identifier.
ITEMS = ("- [blocker] **Payment webhook fails** — #12 · **Bob**\n"
         "- [dependency] **Backend answer on refunds** — TICK-9 · **Ann**\n")

CLOSED_ISSUE = {"number": 12, "title": "Payment webhook retry", "state": "CLOSED",
                "createdAt": "2026-09-01T09:00:00Z", "updatedAt": "2026-10-16T11:02:00Z",
                "closedAt": "2026-10-16T11:02:00Z", "assignees": [{"login": "bob"}]}
OPEN_ISSUE = dict(CLOSED_ISSUE, state="OPEN", closedAt=None)
MERGED_PR = {"number": 7, "title": "retry the webhook, Fixes #12", "state": "MERGED",
             "createdAt": "2026-09-23T09:00:00Z", "updatedAt": "2026-09-23T10:00:00Z",
             "mergedAt": "2026-09-23T10:00:00Z", "author": {"login": "bob"}}


def details():
    return (Path(build.last_meetings) / "260924-agenda-details-daily-standup.md").read_text(encoding="utf-8")


class CertainClose(unittest.TestCase):
    """Proposal 5: only a state read off the work's own source closes a line."""

    def test_a_closed_issue_is_a_certain_close(self):
        hits = ba.certainly_closed([("[blocker] **Pay**", "#12 · **Bob**")],
                                   [{"kind": "issue", "repo": "acme/app", "n": 12, "state": "closed",
                                     "title": "t", "when": "2026-10-16T11:02:00Z"}], [])
        self.assertEqual(len(hits), 1)
        # The verdict carries the ids whose OWN source closed them, so the header
        # can name those and only those.
        kind, basis, when, shut = hits[0][2]
        self.assertEqual(kind, "repo")
        self.assertIn("issue #12 closed", basis)
        self.assertEqual(when, "2026-10-16 11:02")
        self.assertEqual(shut, {"#12"})

    def test_only_the_closed_id_is_reported_as_closed(self):
        # A line naming a closed id and an open one closes, but the open id must
        # not be announced as closed: it is the one misstatement this CR must not
        # make, and the header reads the verdict's own id set.
        hits = ba.certainly_closed(
            [("[blocker] **Pay**", "#12, #30 · **Bob**")],
            [{"kind": "issue", "repo": "acme/app", "n": 12, "state": "closed",
              "title": "t", "when": "2026-10-16T11:02:00Z"},
             {"kind": "issue", "repo": "acme/app", "n": 30, "state": "open",
              "title": "u", "when": "2026-10-16T12:00:00Z"}], [])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][2][3], {"#12"})

    def test_an_open_issue_is_not_a_close(self):
        self.assertEqual(ba.certainly_closed(
            [("[blocker] **Pay**", "#12")],
            [{"kind": "issue", "repo": "acme/app", "n": 12, "state": "open", "title": "t",
              "when": "2026-10-16T11:02:00Z"}], []), [])

    def test_a_merged_pr_closes_only_what_it_names(self):
        row = {"kind": "pull", "repo": "acme/app", "n": 7, "status": "merged",
               "title": "retry", "closes": ["#12"], "when": "2026-09-23T10:00:00Z"}
        self.assertEqual(len(ba.certainly_closed([("**Pay**", "#12")], [row], [])), 1)
        # the PR's own number is NOT a close of a line about the PR
        self.assertEqual(ba.certainly_closed([("**The retry change**", "#7")], [row], []), [])

    def test_a_merged_pr_naming_nothing_closes_nothing(self):
        row = {"kind": "pull", "repo": "acme/app", "n": 7, "status": "merged",
               "title": "retry the webhook", "closes": [], "when": "2026-09-23T10:00:00Z"}
        self.assertEqual(ba.certainly_closed([("**Pay**", "#12")], [row], []), [])

    def test_an_unmerged_pr_is_not_a_close(self):
        row = {"kind": "pull", "repo": "acme/app", "n": 7, "status": "awaiting review",
               "title": "Fixes #12", "closes": ["#12"], "when": "2026-09-23T10:00:00Z"}
        self.assertEqual(ba.certainly_closed([("**Pay**", "#12")], [row], []), [])

    def test_a_done_ticket_is_a_certain_close(self):
        hits = ba.certainly_closed([("**Refunds**", "TICK-9 · **Ann**")], [],
                                   [{"board": "TICK", "n": "TICK-9", "state": "done", "title": "t"}])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][2][0], "tickets")
        self.assertIn("ticket TICK-9 done", hits[0][2][1])

    def test_a_label_change_is_never_a_close(self):
        # the heart of proposal 5: every state CR-141 calls built-but-not-accepted
        for st in ba.FIXED_STATES:
            with self.subTest(state=st):
                self.assertEqual(ba.certainly_closed(
                    [("**Refunds**", "TICK-9")], [],
                    [{"board": "TICK", "n": "TICK-9", "state": st, "title": "t"}]), [])

    def test_a_release_does_not_close_a_line(self):
        # a release names what it shipped; shipped is not the issue's state
        self.assertEqual(ba.certainly_closed(
            [("**Pay**", "#12")],
            [{"kind": "release", "repo": "acme/app", "n": "v2", "title": "v2",
              "names": ["#12"], "when": "2026-09-23T10:00:00Z"}], []), [])

    def test_a_chat_word_does_not_close_a_line(self):
        # `certainly_closed` reads sources, never talk -- chat is not even an argument
        self.assertEqual(ba.certainly_closed([("**Pay**", "#12")], [], []), [])

    def test_a_line_with_no_identifier_is_not_closed_by_anything(self):
        self.assertEqual(ba.certainly_closed(
            [("**Update the readme**", "docs/README.md")],
            [{"kind": "issue", "repo": "acme/app", "n": 12, "state": "closed", "title": "t",
              "when": "2026-10-16T11:02:00Z"}], []), [])

    def test_the_newest_state_wins_over_an_older_one(self):
        # an issue closed then reopened inside the same window must not be dropped
        rows = [{"kind": "issue", "repo": "acme/app", "n": 12, "state": "closed", "title": "t",
                 "when": "2026-10-14T09:00:00Z"},
                {"kind": "issue", "repo": "acme/app", "n": 12, "state": "open", "title": "t",
                 "when": "2026-10-16T09:00:00Z"}]
        self.assertEqual(ba.certainly_closed([("**Pay**", "#12")], rows, []), [])


class StateChangeTakesPrecedence(unittest.TestCase):
    """Proposal 5 integrated with CR-141 rather than re-decided."""

    def test_a_line_naming_a_done_key_and_a_fixed_key_is_not_dropped(self):
        items = [("[dependency] **Refunds**", "TICK-9, TICK-10 · **Ann**")]
        jira = [{"board": "TICK", "n": "TICK-9", "state": "done", "title": "t"},
                {"board": "TICK", "n": "TICK-10", "state": "in review", "title": "t"}]
        certain = ba.certainly_closed(items, [], jira)
        self.assertEqual(len(certain), 1)          # the done key does match
        fixed = ba.state_changed(items, jira)
        self.assertEqual(fixed[0][2], "fixed, waiting for a test")
        # ... and reconcile_closed is what stops the drop
        self.assertEqual(ba.reconcile_closed(certain, fixed), [])

    def test_the_card_keeps_a_line_whose_other_key_is_only_fixed(self):
        jira = [{"key": "TICK-9", "status": "Done", "summary": "refunds", "updated": "2026-09-24T10:00:00Z"},
                {"key": "TICK-10", "status": "In review", "summary": "refunds ui",
                 "updated": "2026-09-24T10:00:00Z"}]
        agenda, _ = build(CARD + JIRA_DECL,
                          note_items="- [dependency] **Backend answer on refunds** — TICK-9, TICK-10 · **Ann**\n",
                          jira=jira)
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertIn("**Backend answer on refunds**", deps)
        self.assertNotIn("Closed in the data since the last meeting:", agenda)


class OffTheCard(unittest.TestCase):
    """`off_card_keys` is the one predicate the card's sections, each person's minute
    and the chat post all read. Each of its terms has to carry its own weight."""

    def test_a_probable_close_the_card_holds_stays_on_it(self):
        # CR-107's rule, unchanged: a probable close is evidence, and the line stays
        # in its section, marked.
        self.assertEqual(ba.off_card_keys(set(), set(), {"pay"}, {"pay"}), set())

    def test_a_probable_close_the_card_does_not_hold_comes_off(self):
        self.assertEqual(ba.off_card_keys(set(), set(), {"pay"}, set()), {"pay"})

    def test_a_line_awaiting_its_owners_word_comes_off(self):
        self.assertEqual(ba.off_card_keys(set(), {"wait"}, set(), set()), {"wait"})

    def test_a_certain_close_comes_off_even_when_no_probable_close_matched(self):
        # The term that is NOT a shortcut through `closed_keys`: the two matchers
        # normalise a ticket state differently, so a board that writes *Done* is a
        # certain close and not a probable one. Without this term the line would stay
        # on the card while the header announced it closed.
        items = [("[dependency] **Refunds**", "TICK-9 · **Ann**")]
        jira = [{"board": "TICK", "n": "TICK-9", "state": "Done", "title": "t"}]
        certain = ba.certainly_closed(items, [], jira)
        probable, _still = ba.probably_closed(items, [], [], jira)
        self.assertEqual(len(certain), 1)
        self.assertEqual(probable, [])                 # capitalised: no probable close
        certain_keys = {ba.key(l) for l, _r, _h in certain}
        self.assertEqual(ba.off_card_keys(certain_keys, set(), set(), set()), certain_keys)


class TheLineLeavesTheCard(unittest.TestCase):
    """Proposals 1 and 2: it leaves, and it leaves a trace."""

    def setUp(self):
        repo = {"reads": ["issues", "pulls"], "issues": [CLOSED_ISSUE]}
        jira = [{"key": "TICK-9", "status": "Done", "summary": "refunds",
                 "updated": "2026-09-24T10:00:00Z"}]
        self.agenda, _ = build(CARD + BOTH_DECL, note_items=ITEMS,
                               repo=repo, jira=jira)
        self.details = details()

    def test_neither_line_is_on_the_card(self):
        blockers = self.agenda[self.agenda.index("## Release blockers"):self.agenda.index("## Dependencies")]
        deps = self.agenda[self.agenda.index("## Dependencies"):self.agenda.index("## Decisions")]
        self.assertIn("*None carried as `[blocker]`.*", blockers)
        self.assertIn("*None carried as `[dependency]`.*", deps)

    def test_the_card_header_names_the_ids(self):
        head = self.agenda.split("## Milestone")[0]
        self.assertIn("**Closed in the data since the last meeting:**", head)
        self.assertIn("#12", head)
        self.assertIn("TICK-9", head)

    def test_the_details_file_lists_each_with_its_basis_and_time(self):
        d = self.details
        self.assertIn("## Closed in the data since the last meeting (2)", d)
        self.assertIn("issue #12 closed", d)
        self.assertIn("2026-10-16 11:02", d)        # the close time, not today's
        self.assertIn("ticket TICK-9 done", d)

    def test_a_dropped_line_is_not_also_offered_for_confirmation(self):
        # it is gone with its basis, not a question for the room
        confirm = self.details.split("## Probably closed")[1:] or [""]
        self.assertNotIn("Payment webhook fails", confirm[0])

    def test_no_dropped_line_reaches_a_persons_minute_or_the_post(self):
        rnd = self.agenda[self.agenda.index("## One-minute round"):]
        self.assertNotIn("Payment webhook fails", rnd)
        self.assertNotIn("Backend answer on refunds", build.last_post)

    def test_an_open_issue_leaves_the_line_exactly_where_it_was(self):
        agenda, _ = build(CARD + REPO_DECL, note_items=ITEMS,
                          repo={"reads": ["issues", "pulls"], "issues": [OPEN_ISSUE]})
        blockers = agenda[agenda.index("## Release blockers"):agenda.index("## Dependencies")]
        self.assertIn("**Payment webhook fails**", blockers)
        self.assertNotIn("Closed in the data since the last meeting:", agenda)


class CannotBeChecked(unittest.TestCase):
    """Proposal 3: a line nobody can read anything about is not asserted as live."""

    def test_a_line_with_no_identifier_is_unconfirmed(self):
        rows = ba.unconfirmed([("[dependency] **Waiting on the other team**", "· **Ann**")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "no identifier, nothing to read")

    def test_an_owner_confirmation_takes_a_line_out_of_the_state(self):
        self.assertEqual(ba.unconfirmed(
            [("[dependency] **Waiting on the other team**",
              "*confirmed: Ann says still waiting* · **Ann**")]), [])

    def test_a_line_with_an_identifier_is_not_in_the_state(self):
        self.assertEqual(ba.unconfirmed([("[dependency] **Refunds**", "TICK-9 · **Ann**")]), [])

    def test_an_extra_marker_puts_a_line_in_the_same_state(self):
        # the hook CR-142 uses: its own marker, the same routing and ageing
        import re
        rows = ba.unconfirmed([("[dependency] **Refunds**", "TICK-9 *inferred: the owner* · **Ann**")],
                              extra_markers=(re.compile(r"\*inferred\b", re.I),))
        self.assertEqual([r[2] for r in rows], ["unconfirmed inference"])

    def test_two_sessions_is_the_ageing_threshold(self):
        self.assertEqual(ba.CONFIRM_SESSIONS, 2)
        self.assertFalse(ba.ages_out(1))
        self.assertFalse(ba.ages_out(2))
        self.assertTrue(ba.ages_out(3))

    def test_a_first_session_line_stays_on_the_card(self):
        # proposal 4: the room raised it last night, and the data may not unmake that
        agenda, _ = build(CARD, note_items="- [dependency] **Waiting on the other team** — · **Ann**\n")
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertIn("**Waiting on the other team**", deps)

    def test_a_second_session_line_goes_to_the_details_not_the_card(self):
        note = "- [dependency] **Waiting on the other team** — · **Ann**\n"
        agenda, _ = build(CARD, note_items=note, notes={"260921": note})
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertNotIn("**Waiting on the other team**", deps)
        d = details()
        # CR-141's section is the one place this is said; CR-147 adds the card column
        self.assertIn("Items with no identifier, cannot be checked (1)", d)
        self.assertIn("the agenda does not assert a line it cannot read", d)
        self.assertIn("awaiting its owner's word", d)

    def test_a_confirmed_second_session_line_is_back_on_the_card(self):
        note = ("- [dependency] **Waiting on the other team** — "
                "*confirmed: Ann said so in her minute* · **Ann**\n")
        agenda, _ = build(CARD, note_items=note, notes={"260921": note})
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertIn("**Waiting on the other team**", deps)

    def test_an_unconfirmed_line_ages_out_and_is_marked_as_such(self):
        note = "- [dependency] **Waiting on the other team** — · **Ann**\n"
        agenda, _ = build(CARD, note_items=note,
                          notes={"260918": note, "260919": note, "260921": note})
        d = details()
        # Ageing out means off the CARD, which is the only list it was ever on. It
        # keeps its row in this table, because a line dropped from the one list that
        # names it would be dropped silently -- the thing this agenda's rule forbids.
        self.assertIn("**aged out** — unconfirmed, off the card", d)
        self.assertNotIn("off the list", d)
        self.assertIn("Waiting on the other team", d)
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertNotIn("Waiting on the other team", deps)

    def test_the_prose_does_not_claim_the_row_leaves_this_table(self):
        # The prose said "comes off this list too" while the row below it was printed
        # in that very list. It now says what actually happens.
        note = "- [dependency] **Waiting on the other team** — · **Ann**\n"
        build(CARD, note_items=note, notes={"260921": note})
        d = details()
        self.assertIn("it keeps its place in this table", d)
        self.assertNotIn("comes off this list too", d)

    def test_the_first_session_exception_is_stated_where_the_rule_is(self):
        # The acceptance text says a line stays on the card only on its owner's word;
        # the implementation asserts a FIRST session anyway (proposal 4: the room
        # raised it last night). The prose must say so, or the two disagree.
        note = "- [dependency] **Waiting on the other team** — · **Ann**\n"
        build(CARD, note_items=note, notes={"260921": note})
        d = details()
        self.assertIn("Its FIRST session is the one exception", d)
        self.assertIn("the room is its confirmation", d)

    def test_the_list_layout_keeps_every_line_as_before(self):
        note = "- [dependency] **Waiting on the other team** — · **Ann**\n"
        agenda, _ = build(LIST, note_items=note, notes={"260919": note, "260921": note})
        self.assertIn("Waiting on the other team", agenda)


class TheListLayoutIsUntouched(unittest.TestCase):
    """CR-147's own additive contract: a project that has not moved to the card sees
    nothing of this CR that would make its page say something false.

    The card is what asserts a short list as today's live work. The list layout's
    carried-forward table is the full list by definition, so proposal 3 does not
    apply to it -- and anything the card's machinery prints must therefore either
    mean something there or not be printed at all.
    """

    NOTE = ("- [dependency] **Waiting on the other team** — nobody confirmed anything"
            " · **Ann**\n")

    def test_the_close_line_links_to_a_file_the_layout_writes(self):
        # The list layout writes no companion details file: the basis table is a
        # section of the agenda itself. A header link to that unwritten file is dead.
        agenda, _ = build(LIST + REPO_DECL,
                          note_items="- [blocker] **Payment webhook fails** — #12 · **Bob**\n",
                          repo={"reads": ["issues", "pulls"], "issues": [CLOSED_ISSUE]})
        head = agenda.split("---")[0]
        self.assertIn("**Closed in the data since the last meeting:** #12", head)
        self.assertNotIn("agenda-details", head)
        # the basis is still one page away, in this page
        self.assertIn("Basis and time below", head)
        self.assertIn("## Closed in the data since the last meeting (1)", agenda)
        self.assertIn("issue #12 closed", agenda)
        self.assertFalse((Path(build.last_meetings)
                          / "260924-agenda-details-daily-standup.md").exists())

    def test_the_card_close_line_still_links_to_the_details_file(self):
        agenda, _ = build(CARD + REPO_DECL,
                          note_items="- [blocker] **Payment webhook fails** — #12 · **Bob**\n",
                          repo={"reads": ["issues", "pulls"], "issues": [CLOSED_ISSUE]})
        head = agenda.split("## Milestone")[0]
        self.assertIn("Basis and time: [260924-agenda-details-daily-standup.md]", head)
        self.assertTrue((Path(build.last_meetings)
                         / "260924-agenda-details-daily-standup.md").exists())

    def test_no_on_the_card_column_where_there_is_no_card(self):
        # The column was printed unconditionally while `pending` was gated on the card,
        # so every row fell to the final branch: a line nobody confirmed, in its third
        # session, was printed as "yes -- confirmed". A false statement about the
        # operator's own data.
        agenda, _ = build(LIST, note_items=self.NOTE,
                          notes={"260919": self.NOTE, "260921": self.NOTE})
        table = agenda[agenda.index("## Items with no identifier"):]
        self.assertIn("| Item | Owner | Sessions |", table)
        self.assertNotIn("On the card", table)
        self.assertNotIn("confirmed", table.split("## ")[1])
        # the line itself is untouched: still carried, with its session count
        self.assertIn("| Waiting on the other team | Ann | 3 |", table)

    def test_the_card_column_says_why_each_line_is_there(self):
        # The second session on the card: nobody confirmed it, so it is off the card
        # and the cell says so -- never "confirmed".
        build(CARD, note_items=self.NOTE, notes={"260921": self.NOTE})
        d = details()
        table = d[d.index("## Items with no identifier"):]
        self.assertIn("| Item | Owner | On the card | Sessions |", table)
        self.assertIn("no — awaiting its owner's word", table)
        self.assertNotIn("yes — confirmed", table)

    def test_a_first_session_card_line_says_the_room_raised_it(self):
        build(CARD, note_items=self.NOTE)
        d = details()
        table = d[d.index("## Items with no identifier"):]
        self.assertIn("yes — first session, raised in the room", table)
        self.assertNotIn("confirmed by its owner", table)

    def test_a_confirmed_card_line_says_its_owner_confirmed_it(self):
        note = ("- [dependency] **Waiting on the other team** — "
                "*confirmed: Ann said so in her minute* · **Ann**\n")
        build(CARD, note_items=note, notes={"260921": note})
        d = details()
        table = d[d.index("## Items with no identifier"):]
        self.assertIn("yes — confirmed by its owner", table)


class NothingIsOpenedByTheData(unittest.TestCase):
    """Proposal 4: the data can close a dependency, never open one."""

    def test_a_closed_issue_nobody_carried_adds_no_line(self):
        repo = {"reads": ["issues", "pulls"],
                "issues": [dict(CLOSED_ISSUE, number=99, title="something else")]}
        agenda, _ = build(CARD + REPO_DECL,
                          note_items="- [dependency] **Backend answer on refunds** — TICK-9 · **Ann**\n",
                          repo=repo)
        deps = agenda[agenda.index("## Dependencies"):agenda.index("## Decisions")]
        self.assertIn("**Backend answer on refunds**", deps)
        self.assertNotIn("#99", deps)
        self.assertNotIn("something else", deps)


class AFailedSourceRemovesNothing(unittest.TestCase):
    """Proposal 6, reusing CR-088's record and CR-140's reporting."""

    # `readable_sources` reads the config to learn which sources the project
    # DECLARES, the same gate `failed_fetches` applies: only a declared source can
    # be an unread one.
    DECLARED = {"ext": {"repos": [{"url": "https://github.com/acme/app"}],
                        "jira": [{"project": "TICK"}]}}

    def test_a_recorded_failure_blocks_that_source(self):
        bad = ba.readable_sources(self.DECLARED,
                                  {".githubmeta": {"result": "auth"}, ".jirameta": None},
                                  {"repo": [], "tickets": []}, datetime.date(2026, 10, 21))
        self.assertIn("repo", bad)
        self.assertIn("fetch failed", bad["repo"])
        self.assertNotIn("tickets", bad)            # not recorded is not failed

    def test_a_producer_note_blocks_that_source(self):
        bad = ba.readable_sources(self.DECLARED, {".githubmeta": None, ".jirameta": None},
                                  {"repo": [{"note": "acme/app: no snapshot in the archive"}],
                                   "tickets": []}, datetime.date(2026, 10, 21))
        self.assertIn("no snapshot", bad["repo"])

    def test_an_undeclared_source_is_not_an_unread_one(self):
        # A `_fetch.json` left behind by a config that no longer declares the board
        # produces no verdicts, so it holds nothing back -- but the header names every
        # blocked source, and naming one the project does not use says a source failed
        # when none did.
        recs = {".githubmeta": {"result": "auth"}, ".jirameta": {"result": "auth"}}
        rows = {"repo": [], "tickets": [{"note": "tick: no snapshot in the archive"}]}
        only_repo = {"ext": {"repos": [{"url": "https://github.com/acme/app"}]}}
        bad = ba.readable_sources(only_repo, recs, rows, datetime.date(2026, 10, 21))
        self.assertIn("repo", bad)
        self.assertNotIn("tickets", bad)
        # ... and with neither declared, nothing is blocked at all
        self.assertEqual(ba.readable_sources({}, recs, rows, datetime.date(2026, 10, 21)), {})

    def test_drop_closed_holds_a_verdict_from_a_blocked_source(self):
        hit = ("**Pay**", "#12", ("repo", "acme/app issue #12 closed", "2026-10-16 11:02"))
        acted, held = ba.drop_closed([hit], {"repo": "fetch failed 09:00: expired login"})
        self.assertEqual(acted, [])
        self.assertEqual(held, [hit])
        acted, held = ba.drop_closed([hit], {})
        self.assertEqual((acted, held), ([hit], []))

    def test_a_failed_fetch_keeps_the_line_and_names_the_source(self):
        repo = {"reads": ["issues", "pulls"], "issues": [CLOSED_ISSUE]}
        agenda, _ = build(CARD + REPO_DECL, note_items=ITEMS, repo=repo,
                          fetch={".githubmeta": {"result": "auth", "last_attempt": "2026-09-24T08:00:00",
                                                 "last_success": "2026-09-20T08:00:00"}})
        blockers = agenda[agenda.index("## Release blockers"):agenda.index("## Dependencies")]
        self.assertIn("**Payment webhook fails**", blockers)
        self.assertNotIn("Closed in the data since the last meeting:", agenda)
        head = agenda.split("## Milestone")[0]
        self.assertIn("nothing was removed on its word", head)
        self.assertIn("Payment webhook fails", head)


if __name__ == "__main__":
    unittest.main()
