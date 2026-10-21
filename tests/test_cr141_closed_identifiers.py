"""CR-141: the *probably closed* matcher matches on explicit identifiers, or says nothing.

The old matcher compared word sets -- two shared 4+-letter words between the carried
line and an evidence string made a hit -- and the evidence string always carries the
repository name and the ticket prefix, so unrelated work paired up. Here: only an
explicit `#id` or ticket key matches, a line with no identifier is never marked and is
listed as unchecked instead, every marker states its basis, and a state change is not
a close. Invented data.

    python3 -m unittest discover -s tests
"""

import datetime
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
REPO_DECL = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
             "      reads: [issues, pulls]\n")
JIRA_DECL = "external_systems:\n  jira:\n    - project: TICK\n"


def chat(*lines):
    return [{"name": "standup", "messages": [(l[:10], l) for l in lines]}]


class Identifiers(unittest.TestCase):
    """The extraction CR-147 will reuse to act on a close."""

    def test_hash_numbers(self):
        self.assertEqual(ba.identifiers("Payment webhook fails — #12"), {"#12"})
        self.assertEqual(ba.identifiers("#4 and #1207"), {"#4", "#1207"})

    def test_ticket_keys_keep_their_prefix(self):
        self.assertEqual(ba.identifiers("Backend answer on refunds — TICK-9"), {"TICK-9"})
        self.assertEqual(ba.identifiers("BRAVO-1234 is the one"), {"BRAVO-1234"})

    def test_a_colour_and_a_date_are_not_identifiers(self):
        self.assertEqual(ba.identifiers("brand colour #fff on the re-run of 2026-09-24"), set())

    def test_prose_with_no_identifier_yields_nothing(self):
        self.assertEqual(ba.identifiers("Update the readme"), set())
        self.assertEqual(ba.identifiers(""), set())

    def test_a_ticket_range_expands_to_every_key_in_it(self):
        self.assertEqual(ba.identifiers("TICK-9..12"), {"TICK-9", "TICK-10", "TICK-11", "TICK-12"})
        self.assertEqual(ba.identifiers("TICK-9-11"), {"TICK-9", "TICK-10", "TICK-11"})
        self.assertEqual(ba.identifiers("TICK-9–10"), {"TICK-9", "TICK-10"})
        self.assertEqual(ba.identifiers("TICK-9..TICK-10"), {"TICK-9", "TICK-10"})

    def test_a_spaced_dash_is_prose_and_invents_no_keys(self):
        # the range feature reintroduced the over-matching this CR removes: with a
        # spaced dash allowed, a roadmap line yielded five keys and a standards line
        # nine, none of them written anywhere. Only the literal keys survive.
        self.assertEqual(ba.identifiers("Q3-2026 - Q3-2030 roadmap"), {"Q3-2026", "Q3-2030"})
        self.assertEqual(ba.identifiers("ISO-8601 - ISO-8609 encoding"), {"ISO-8601", "ISO-8609"})
        # the em dash is this file's own separator, on nearly every carried line
        self.assertEqual(ba.identifiers("Payments release — TICK-9 — **Bob**"), {"TICK-9"})
        self.assertEqual(ba.identifiers("TICK-9, TICK-12 — **Ann**"), {"TICK-9", "TICK-12"})

    def test_a_written_range_still_expands(self):
        self.assertEqual(ba.identifiers("TICK-9..12 shipped"),
                         {"TICK-9", "TICK-10", "TICK-11", "TICK-12"})
        self.assertEqual(ba.identifiers("TICK-9–11 shipped"), {"TICK-9", "TICK-10", "TICK-11"})

    def test_an_absurd_range_is_not_expanded(self):
        # a typo would otherwise match every ticket on the board, which is the old
        # everything-matches failure in a new costume; only what is written survives
        self.assertEqual(ba.identifiers("TICK-9..99999"), {"TICK-9"})

    def test_closing_keywords_name_the_issue_they_close(self):
        self.assertEqual(ba.closing_refs("fix the retry, Re #12"), {"#12"})
        self.assertEqual(ba.closing_refs("Fixes #12 and closes #13"), {"#12", "#13"})
        self.assertEqual(ba.closing_refs("touches #12 in passing"), set())
        self.assertIn("#12", ba.identifiers("Fixes #12"))


class OnlyAnIdentifierMatches(unittest.TestCase):
    ITEM = [("Payments release", "#12 · **Bob**")]

    def test_a_shared_word_is_not_a_match(self):
        # the measured failure: a checkout fix paired with a carried payments line
        repo = [{"kind": "pull", "repo": "acme/app", "n": 7, "title": "checkout release fix",
                 "status": "merged", "when": "2026-09-23 10:00"}]
        closed, still = ba.probably_closed(self.ITEM, [], repo, [])
        self.assertEqual(closed, [])
        self.assertEqual(still, self.ITEM)

    def test_a_pull_request_naming_the_issue_matches(self):
        repo = [{"kind": "pull", "repo": "acme/app", "n": 7, "title": "retry path, Re #12",
                 "status": "merged", "when": "2026-09-23 10:00"}]
        closed, still = ba.probably_closed(self.ITEM, [], repo, [])
        self.assertEqual(len(closed), 1)
        self.assertEqual(still, [])

    def test_a_closed_issue_with_the_same_number_matches(self):
        repo = [{"kind": "issue", "repo": "acme/app", "n": 12, "title": "Payments release",
                 "state": "closed", "when": "2026-10-16 11:02"}]
        closed, _ = ba.probably_closed(self.ITEM, [], repo, [])
        self.assertEqual(len(closed), 1)

    def test_an_issue_with_a_different_number_does_not(self):
        repo = [{"kind": "issue", "repo": "acme/app", "n": 99, "title": "Payments release",
                 "state": "closed", "when": "2026-10-16 11:02"}]
        closed, _ = ba.probably_closed(self.ITEM, [], repo, [])
        self.assertEqual(closed, [])

    def test_a_ticket_key_matches_and_a_sibling_key_does_not(self):
        item = [("Backend answer on refunds", "TICK-9 · **Ann**")]
        closed, _ = ba.probably_closed(item, [], [], [{"n": "TICK-9", "title": "Refunds", "state": "done"}])
        self.assertEqual(len(closed), 1)
        closed, _ = ba.probably_closed(item, [], [], [{"n": "TICK-8", "title": "Refunds", "state": "done"}])
        self.assertEqual(closed, [])

    def test_a_chat_done_word_without_an_id_matches_nothing(self):
        closed, still = ba.probably_closed(self.ITEM, chat("2026-09-24 09:00 — Bob — payments release shipped"),
                                           [], [])
        self.assertEqual(closed, [])
        self.assertEqual(still, self.ITEM)

    def test_a_chat_line_naming_the_id_matches(self):
        closed, _ = ba.probably_closed(self.ITEM, chat("2026-09-24 09:00 — Bob — #12 shipped"), [], [])
        self.assertEqual(len(closed), 1)

    def test_a_release_matches_only_what_its_notes_name(self):
        rel = [{"kind": "release", "repo": "acme/app", "n": "v2.1", "title": "payments and checkout",
                "when": "2026-09-23 10:00"}]
        closed, _ = ba.probably_closed(self.ITEM, [], rel, [])
        self.assertEqual(closed, [])
        rel[0]["title"] = "ships #12"
        closed, _ = ba.probably_closed(self.ITEM, [], rel, [])
        self.assertEqual(len(closed), 1)


class EveryMarkerStatesItsBasis(unittest.TestCase):
    def test_a_closed_issue_says_which_issue_and_when(self):
        item = [("Payments release", "#12 · **Bob**")]
        repo = [{"kind": "issue", "repo": "acme/app", "n": 12, "title": "Payments release",
                 "state": "closed", "when": "2026-10-16 11:02"}]
        _l, _r, (kind, ref, _txt) = ba.probably_closed(item, [], repo, [])[0][0]
        self.assertEqual(kind, "repo")
        self.assertIn("issue #12 closed", ref)
        self.assertIn("2026-10-16 11:02", ref)

    def test_a_pull_request_names_the_issue_it_closes(self):
        item = [("Payments release", "#12 · **Bob**")]
        repo = [{"kind": "pull", "repo": "acme/app", "n": 7, "title": "retry path, Re #12",
                 "status": "merged", "when": "2026-09-23 10:00"}]
        closed, _ = ba.probably_closed(item, [], repo, [])
        self.assertIn("PR #7 (Re #12) merged", closed[0][2][1])

    def test_a_ticket_marker_names_the_key_and_its_state(self):
        item = [("Backend answer on refunds", "TICK-9 · **Ann**")]
        closed, _ = ba.probably_closed(item, [], [], [{"n": "TICK-9", "title": "Refunds", "state": "done"}])
        self.assertIn("ticket TICK-9 done", closed[0][2][1])


class NoIdentifierIsSaidOutLoud(unittest.TestCase):
    ITEMS = [("Payments release", "#12 · **Bob**"), ("Update the readme", "docs/README.md · **Bob**")]

    def test_without_identifier_lists_only_the_unidentifiable_line(self):
        self.assertEqual(ba.without_identifier(self.ITEMS), [self.ITEMS[1]])

    def test_an_unidentifiable_line_stays_carried_and_is_never_marked(self):
        repo = [{"kind": "issue", "repo": "acme/app", "n": 12, "title": "readme update",
                 "state": "closed", "when": "2026-10-16 11:02"}]
        closed, still = ba.probably_closed(self.ITEMS, [], repo, [])
        self.assertEqual([l for l, _r, _h in closed], ["Payments release"])
        self.assertEqual(still, [self.ITEMS[1]])

    def test_the_unchecked_list_reaches_the_details_file(self):
        items = ("- [blocker] **Payment webhook fails** — #12 · **Bob**\n"
                 "- **Update the readme** — docs/README.md · **Bob**\n")
        repo = {"reads": ["issues", "pulls"], "pulls": [
            {"number": 7, "title": "retry path, Re #12", "state": "MERGED",
             "mergedAt": "2026-09-23T10:00:00Z", "createdAt": "2026-09-23T09:00:00Z",
             "author": {"login": "bob"}}]}
        agenda, _ = build(CARD + REPO_DECL, note_items=items, repo=repo)
        details = (Path(build.last_meetings)
                   / "260924-agenda-details-daily-standup.md").read_text(encoding="utf-8")
        self.assertIn("Items with no identifier, cannot be checked (1)", details)
        self.assertIn("Update the readme", details)
        # the card itself never carries the unchecked list
        self.assertNotIn("cannot be checked", agenda)


class AStateChangeIsNotAClose(unittest.TestCase):
    ITEM = [("Payment webhook fails", "TICK-9 · **Bob**")]

    def test_a_fixed_ticket_is_not_probably_closed(self):
        closed, still = ba.probably_closed(self.ITEM, [], [],
                                           [{"n": "TICK-9", "title": "Webhook", "state": "fixed"}])
        self.assertEqual(closed, [])
        self.assertEqual(still, self.ITEM)

    def test_a_fixed_ticket_is_reported_as_waiting_for_a_test(self):
        rows = ba.state_changed(self.ITEM, [{"n": "TICK-9", "title": "Webhook", "state": "fixed"}])
        self.assertEqual(rows, [("Payment webhook fails", "TICK-9 · **Bob**", "fixed, waiting for a test")])

    def test_a_done_ticket_is_a_close_not_a_state_change(self):
        self.assertEqual(ba.state_changed(self.ITEM, [{"n": "TICK-9", "state": "done"}]), [])

    def test_a_state_change_on_another_key_says_nothing(self):
        self.assertEqual(ba.state_changed(self.ITEM, [{"n": "TICK-8", "state": "in review"}]), [])

    def test_a_line_with_no_identifier_gets_no_state_row(self):
        self.assertEqual(ba.state_changed([("Update the readme", "**Bob**")],
                                          [{"n": "TICK-9", "state": "fixed"}]), [])


class AClosingReferenceInAPullRequestBody(unittest.TestCase):
    """CR-141: the closing-reference path, from the archived payload onward.

    The ids a merged PR says it closes are read in `pulls_since`, where the
    archived record is; the row it emits is a fixed shape, so a reference living
    only in the description had no way through it. These go through the producer
    with a payload shaped like the archive's, never a dict hand-made to carry the
    field the matcher happens to read.
    """

    AFTER = datetime.date(2026, 9, 23)
    TODAY = datetime.date(2026, 9, 24)
    ITEM = [("Payment webhook fails", "#12 · **Bob**")]

    def pr(self, **extra):
        pr = {"number": 7, "title": "Retry path for the payment webhook", "state": "MERGED",
              "isDraft": False, "reviewDecision": "APPROVED", "author": {"login": "bob"},
              "createdAt": "2026-09-22T09:00:00Z", "updatedAt": "2026-09-23T10:00:00Z",
              "mergedAt": "2026-09-23T10:00:00Z"}
        pr.update(extra)
        return ba.pulls_since("acme/app", [pr], self.AFTER, self.TODAY)

    def test_fixes_in_the_body_matches_the_carried_issue(self):
        body = "Rework the retry so a 5xx is retried three times.\n\nFixes #12\n"
        rows = self.pr(body=body)
        self.assertEqual(rows[0]["closes"], ["#12"])     # read by the producer
        closed, still = ba.probably_closed(self.ITEM, [], rows, [])
        self.assertEqual(len(closed), 1)
        self.assertEqual(still, [])
        self.assertIn("PR #7 (Re #12) merged", closed[0][2][1])

    def test_the_graphql_field_name_is_read_too(self):
        rows = self.pr(bodyText="Closes #12 once review is in.")
        self.assertEqual(rows[0]["closes"], ["#12"])
        self.assertEqual(len(ba.probably_closed(self.ITEM, [], rows, [])[0]), 1)

    def test_a_body_that_only_mentions_the_issue_closes_nothing(self):
        rows = self.pr(body="Groundwork for #12; the fix itself comes later.")
        self.assertEqual(rows[0]["closes"], [])
        self.assertEqual(ba.probably_closed(self.ITEM, [], rows, [])[0], [])

    def test_an_archive_with_no_description_still_matches_on_the_title(self):
        rows = self.pr(title="retry path, Fixes #12")
        self.assertEqual(rows[0]["closes"], ["#12"])
        self.assertEqual(len(ba.probably_closed(self.ITEM, [], rows, [])[0]), 1)

    def test_a_release_matches_what_its_notes_name(self):
        # the same dead path on the release branch: the ids live in the NOTES, which
        # never reached the matcher either, so `from_repo` reads them now
        rel = [{"kind": "release", "repo": "acme/app", "n": "v2.1", "title": "September",
                "when": "2026-09-23 10:00", "names": ["#12"]}]
        self.assertEqual(len(ba.probably_closed(self.ITEM, [], rel, [])[0]), 1)
        rel[0]["names"] = ["#99"]
        self.assertEqual(ba.probably_closed(self.ITEM, [], rel, [])[0], [])


class OneLineGetsOneVerdict(unittest.TestCase):
    """CR-141: *probably closed* and *waiting for a test* cannot both be true."""

    ITEM = [("Webhook", "TICK-9, TICK-10 — **Bob**")]
    JIRA = [{"n": "TICK-9", "state": "done"}, {"n": "TICK-10", "state": "in review"}]

    def test_waiting_for_a_test_wins_over_a_close_on_the_same_line(self):
        closed, _ = ba.probably_closed(self.ITEM, [], [], self.JIRA)
        fixed = ba.state_changed(self.ITEM, self.JIRA)
        self.assertEqual(len(closed), 1)            # both fire on the raw lines
        self.assertEqual(len(fixed), 1)
        # reconciled: proposal 4's precedence, so the item stays carried
        self.assertEqual(ba.reconcile_closed(closed, fixed), [])

    def test_a_close_with_no_state_change_is_untouched(self):
        jira = [{"n": "TICK-9", "state": "done"}, {"n": "TICK-10", "state": "done"}]
        closed, _ = ba.probably_closed(self.ITEM, [], [], jira)
        self.assertEqual(len(ba.reconcile_closed(closed, ba.state_changed(self.ITEM, jira))), 1)

    def test_the_generated_agenda_never_reports_one_item_in_both_sections(self):
        # end to end, through the ticket archive: the line names two keys, one done
        # and one in review. Before reconciling, the details file carried it under
        # both headings and the carried list had lost it to the close.
        items = "- [blocker] **Webhook** — TICK-9, TICK-10 · **Bob**\n"
        agenda, _ = build(CARD + JIRA_DECL, note_items=items,
                          jira=[{"key": "TICK-9", "summary": "Webhook", "status": "Done",
                                 "updated": "2026-09-24T09:00:00.000+0000"},
                                {"key": "TICK-10", "summary": "Webhook retry", "status": "In Review",
                                 "updated": "2026-09-24T09:00:00.000+0000"}])
        details = (Path(build.last_meetings)
                   / "260924-agenda-details-daily-standup.md").read_text(encoding="utf-8")
        self.assertIn("## Fixed, waiting for a test", details)
        self.assertNotIn("## Probably closed", details)
        self.assertIn("Webhook", agenda)        # and it is still on the card


class ChatEvidenceStatesItsBasis(unittest.TestCase):
    """CR-141, proposal 3: verifiable in one click, chat included."""

    ITEM = [("Payments release", "#12 · **Bob**")]

    def test_the_basis_names_the_identifier_it_matched_on(self):
        closed, _ = ba.probably_closed(self.ITEM, chat("2026-09-24 09:00 — Bob — #12 shipped"), [], [])
        _l, _r, (kind, ref, _txt) = closed[0]
        self.assertEqual(kind, "chat")
        self.assertIn("#12", ref)
        self.assertIn("2026-09-24 09:00", ref)

    def test_the_id_survives_the_quote_being_cut(self):
        late = ("2026-09-24 09:00 — Bob — we finally got the long awaited retry path merged "
                "this morning after a second review, which closes #12")
        closed, _ = ba.probably_closed(self.ITEM, chat(late), [], [])
        _l, _r, (_k, ref, txt) = closed[0]
        self.assertIn("#12", ref)
        self.assertIn("#12", txt)            # the quote agrees with the basis
        self.assertLessEqual(len(txt), 80)   # and is still cut to table width

    def test_a_short_quote_is_printed_whole(self):
        self.assertEqual(ba.quote_for("#12 shipped", {"#12"}), "#12 shipped")

    def test_an_early_id_is_cut_from_the_front_as_before(self):
        t = "#12 shipped " + "and then a great deal of further detail nobody needs " * 3
        self.assertTrue(ba.quote_for(t, {"#12"}).startswith("#12 shipped"))


class NothingIsEverDropped(unittest.TestCase):
    def test_every_carried_line_is_in_one_of_the_two_lists(self):
        items = [("Payments release", "#12 · **Bob**"), ("Update the readme", "**Bob**"),
                 ("Backend answer on refunds", "TICK-9 · **Ann**")]
        repo = [{"kind": "issue", "repo": "acme/app", "n": 12, "title": "Payments",
                 "state": "closed", "when": "2026-10-16 11:02"}]
        closed, still = ba.probably_closed(items, [], repo, [])
        self.assertEqual(len(closed) + len(still), 3)


if __name__ == "__main__":
    unittest.main()
