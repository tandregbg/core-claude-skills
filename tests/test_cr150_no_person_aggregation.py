"""CR-150: the generator never aggregates by person, and a lint keeps team-facing files clean.

Counts of work per person -- issues closed, pull requests, commits, lines -- belong in one
owner-only document and never in the files the team reads or that the person leading the
meeting reads aloud. The numbers mislead (lines reward volume, closures reward splitting
one job into three, and part of the code is written in agent sessions), and the person
leading is often one of the people counted.

What is tested is the REQUIREMENT, not the shape of the implementation: every generated
team-facing file is run through the detector (so a renderer that grows a leaderboard later
fails here), a hand-added table and a hand-added line each make the lint fail, an owner
column does not, and a source carrying figures produces one line and no copied figure.
Invented data.

    python3 -m unittest discover -s tests
"""

import datetime
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "skills" / "ops"
sys.path.insert(0, str(OPS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_agenda as ba  # noqa: E402
import build_movement as bm  # noqa: E402
import hygiene_check as hc  # noqa: E402
from test_cr101_agenda_draft import build  # noqa: E402

SKILL = (OPS / "SKILL.md").read_text(encoding="utf-8")
SCHEMA = (ROOT / "skills" / "ops-config" / "schema.md").read_text(encoding="utf-8")

MS = "milestone:\n  name: Beta\n  date: 2026-11-01\n  set_on: 2026-09-01\n"
PEOPLE = "people:\n  - name: Ann\n  - name: Bob\n  - name: Dee\n"
# The roster the detector resolves a count's SUBJECT against (CR-150). Passed at
# every direct call: without it the detector finds nothing by contract, so an
# assertion that the generator counted nobody would pass against any output at all.
ROSTER = {"ann", "bob", "dee"}
REPOS = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
         "      reads: [issues, pulls]\n")

# Two issues and two pull requests with authors and assignees on them: the appendix lists
# the author of each item, which is the one grouping away from a leaderboard CR-150 names.
REPO = {
    "reads": ["issues", "pulls"],
    "issues": [
        {"number": 12, "title": "Payment webhook retry", "state": "CLOSED",
         "createdAt": "2026-09-23T09:00:00Z", "updatedAt": "2026-09-24T09:00:00Z",
         "closedAt": "2026-09-24T09:00:00Z", "assignees": [{"login": "bob"}],
         "labels": [{"name": "area:api"}]},
        {"number": 13, "title": "Refund rounding", "state": "OPEN",
         "createdAt": "2026-09-23T09:00:00Z", "updatedAt": "2026-09-24T09:00:00Z",
         "assignees": [], "labels": [{"name": "area:api"}]},
    ],
    "pulls": [
        {"number": 7, "title": "Fix refunds", "state": "MERGED",
         "mergedAt": "2026-09-24T10:00:00Z", "createdAt": "2026-09-23T08:00:00Z",
         "updatedAt": "2026-09-24T10:00:00Z", "author": {"login": "bob"}},
        {"number": 8, "title": "Retry logic", "state": "OPEN",
         "createdAt": "2026-09-20T08:00:00Z", "updatedAt": "2026-09-24T10:00:00Z",
         "author": {"login": "dee"}},
    ],
}

ITEMS = ("- [blocker] **Payment webhook fails** — #12 · **Bob**\n"
         "- [dependency] **Backend answer on refunds** — TICK-9 · **Ann**\n"
         "- **Android build:** Dee\n")

# A leaderboard, in the two shapes somebody actually pastes in.
LEADER_TABLE = ("## Who closed what\n\n"
                "| Person | Issues closed | PRs merged |\n|---|--:|--:|\n"
                "| Bob | 14 | 3 |\n| Dee | 2 | 1 |\n")
LEADER_LINE = "- **Dee:** 14 issues closed this week\n"


def cfg(layout: str = "") -> str:
    return ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
            + (f"      layout: {layout}\n" if layout else "")
            + PEOPLE + MS + REPOS)


def vault(ops_yaml: str, files: dict[str, str] | None = None):
    """A venture with one project and whatever extra files a test needs.

    Returns (venture root, project root). Paths in `files` are relative to the project.
    """
    venture = Path(tempfile.mkdtemp()) / "venture"
    proj = venture / "proj"
    (proj / "meetings").mkdir(parents=True)
    (proj / "_ops.yaml").write_text(ops_yaml, encoding="utf-8")
    for rel, body in (files or {}).items():
        f = proj / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return venture, proj


class TheGeneratorEmitsNone(unittest.TestCase):
    """Proposal 1: no per-person total in any team-facing output, in any layout.

    Asserted over the files the generator actually wrote rather than over a renderer,
    because the requirement is about the output: the next section somebody adds is covered
    by this test without the test being changed.
    """

    def _files(self, layout: str):
        txt, _out = build(cfg(layout), repo=REPO, note_items=ITEMS,
                          chat_lines=[("09:12", "Ann", "Refunds need a decision")])
        md = Path(build.last_meetings)
        got = {p.name: p.read_text(encoding="utf-8") for p in sorted(md.glob("260924-*"))}
        self.assertTrue(got, "the generator wrote nothing")
        return got

    def test_the_list_layout_counts_nobody(self):
        for name, text in self._files("").items():
            self.assertEqual(ba.person_count_lines(text, ROSTER), [], name)

    def test_the_card_layout_and_its_details_file_count_nobody(self):
        got = self._files("card")
        self.assertIn("260924-agenda-details-daily-standup.md", got)
        for name, text in got.items():
            self.assertEqual(ba.person_count_lines(text, ROSTER), [], name)

    def test_the_compact_layout_and_its_facilitator_document_count_nobody(self):
        # CR-148's facilitator document is read by whoever leads, who is one of the people
        # a "who carries the most" list would count. It is named explicitly so this test
        # fails if the document stops being generated rather than passing vacuously.
        got = self._files("compact")
        self.assertIn("260924-agenda-facilitator-daily-standup.md", got)
        for name, text in got.items():
            self.assertEqual(ba.person_count_lines(text, ROSTER), [], name)

    def test_the_chat_post_counts_nobody(self):
        for layout in ("", "card", "compact"):
            self._files(layout)
            self.assertEqual(ba.person_count_lines(build.last_post, ROSTER), [], layout or "list")

    def test_the_appendix_still_names_the_author_of_each_item(self):
        """Proposal 1's other half: traceability is kept, only the GROUP BY is refused."""
        got = self._files("card")
        details = got["260924-agenda-details-daily-standup.md"]
        self.assertIn("#7", details)
        self.assertIn("bob", details)      # the author, beside the pull request it belongs to
        self.assertIn("dee", details)
        self.assertEqual(ba.person_count_lines(details, ROSTER), [])


class TheLintFlagsALeaderboard(unittest.TestCase):
    """Proposal 4: a team-facing file with a people-by-counts table, or a person-and-count
    line, is a finding that names the file and the line and repeats no figure."""

    def _lint(self, body: str, ops_yaml: str = cfg(), rel: str = "meetings/260924-agenda-daily-standup.md"):
        venture, proj = vault(ops_yaml, {rel: body})
        return hc.run(proj, only=("persons",))

    def test_a_hand_added_table_of_people_against_counts_is_a_finding(self):
        found = self._lint("# Agenda\n\n" + LEADER_TABLE)
        self.assertTrue(found)
        self.assertTrue(all(f["kind"] == "persons" for f in found))

    def test_the_finding_names_the_file_and_the_line(self):
        found = self._lint("# Agenda\n\n" + LEADER_TABLE)
        self.assertEqual(found[0]["file"], "meetings/260924-agenda-daily-standup.md")
        # The table's first body row: heading, blank, heading, blank, header, rule, row.
        self.assertEqual(found[0]["line"], 7)

    def test_the_finding_does_not_repeat_the_figure(self):
        """The point of the rule: a report quoting the number has copied it onward."""
        found = self._lint("# Agenda\n\n" + LEADER_TABLE + LEADER_LINE)
        self.assertTrue(found)
        for f in found:
            self.assertNotIn("14", f["message"])
            self.assertNotIn("3", f["message"].replace("CR-150", ""))

    def test_a_line_pairing_a_person_with_a_count_is_a_finding(self):
        found = self._lint("# Agenda\n\n" + LEADER_LINE)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["line"], 3)

    def test_the_count_is_flagged_written_either_way_round(self):
        for line in ("- **Bob:** 9 commits\n", "- 9 commits by Bob\n",
                     "- Dee — 7 pull requests merged\n", "- **Ann** 312 lines of code\n",
                     # The commonest spelling of all: a dash between the name and the
                     # figure, in both the em and the en form, with the emphasis outside
                     # the name rather than around the whole pair.
                     "- **Dee** — 14 issues closed\n", "- Bob – 7 PRs merged\n"):
            self.assertTrue(self._lint("# Agenda\n\n" + line), line)

    def test_a_leaderboard_line_is_not_silenced_by_naming_an_issue(self):
        """The guard is on the ORDER, not on the presence of an identifier.

        A rule that could be switched off by appending `on #12` to the line would not be
        a rule. What decides is which comes first: an item with an owner names the item,
        a count against a person names the person.
        """
        for line in ("- **Bob:** 3 commits on #12\n", "- Ann — 2 pull requests, see TICK-9\n",
                     "- 3 commits by Bob on #12\n"):
            self.assertTrue(self._lint("# Agenda\n\n" + line), line)

    def test_a_count_of_something_other_than_work_is_not_a_finding(self):
        # The unit list is closed on purpose: widening it is how a lint starts firing on
        # the round table and the facilitator's time boxes.
        for line in ("- **Bob:** 3 sessions carried\n", "| One-minute round (3 people) | 3 |\n",
                     "- **Ann** waiting 9 days\n"):
            self.assertEqual(self._lint("# Agenda\n\n" + line), [], line)


class AnOwnerIsNotAFinding(unittest.TestCase):
    """Proposal 5: a name beside an ITEM is accountability for a task, not a scoreboard.

    This is the boundary the whole rule stands on -- a lint that fires on every owner
    column is switched off within a week, and then nothing is checked at all.
    """

    def _lint(self, body: str):
        venture, proj = vault(cfg(), {"meetings/260924-agenda-daily-standup.md": body})
        return hc.run(proj, only=("persons",))

    def test_an_owner_column_is_not_a_finding(self):
        self.assertEqual(self._lint(
            "# Agenda\n\n| Item | Owner | Waiting | State |\n|---|---|---|---|\n"
            "| **Refunds** | Ann | 2 sessions · 9d | open |\n"
            "| **Payment webhook** | Bob | 1 session | **closed** |\n"), [])

    def test_an_assignee_beside_an_issue_is_not_a_finding(self):
        self.assertEqual(self._lint(
            "# Agenda\n\n- #12 Payment webhook retry — Bob\n"
            "- #13 Refund rounding — **no assignee**\n"
            "- acme/app #7 Fix refunds (bob)\n"), [])

    def test_an_item_that_names_both_an_owner_and_a_count_is_not_a_finding(self):
        """An identifier BEFORE the pair makes the line a statement about one item.

        This is the half of the boundary the order decides: the item is named first and
        the name and the figure that follow both belong to it, which is a detail line and
        not a comparison of people.
        """
        self.assertEqual(self._lint(
            "# Agenda\n\n- #12 Payment webhook retry — Bob 3 commits\n"
            "- TICK-9 Refunds — Ann 2 pull requests\n"
            "- acme/app #7 Fix refunds (bob) — 3 commits\n"), [])

    # The three lines above happen not to match the person-and-count shape at all, so they
    # would stay clean with no guard in the reader whatsoever -- they say nothing about the
    # leading-identifier rule. These do (defect pass): each one DOES pair a roster name
    # with a count, in both orders, and is clean only because an identifier comes first.
    # Deleting the guard turns every one of them into a finding.
    GUARDED = ("- #12 Payment webhook retry — **Bob:** 3 commits\n",
               "- TICK-9 Refunds — **Ann** 2 pull requests\n",
               "- acme/app #7 Fix refunds — **Dee** 14 issues closed\n",
               "- #12 Refunds · 3 commits by Bob\n",
               "- TICK-9 Refunds · 2 pull requests by Ann\n")

    def test_an_owned_item_carrying_a_count_is_clean_only_because_of_the_order(self):
        """The leading-identifier guard, on lines that reach it.

        Each line pairs a person ON THE ROSTER with a count of work, which is the shape
        the lint exists to catch -- and is still not a finding, because the line names the
        ITEM first: `#12 ... Bob: 3 commits` is three commits on that issue, attributed,
        not a comparison of people. This is the detail line the appendix writes.
        """
        for line in self.GUARDED:
            self.assertEqual(self._lint("# Agenda\n\n" + line), [], line)

    def test_the_same_pair_without_a_leading_identifier_is_a_finding(self):
        """The other side of the same boundary, one edit apart.

        Drop the item from the front of each line above and nothing else, and every one
        becomes a finding. Asserted as a PAIR with the test above so neither can pass for
        a reason other than the order: a reader that always fired would fail that one, a
        reader that never fired fails this one.
        """
        for line in self.GUARDED:
            bare = re.sub(r"^- (?:acme/app )?(?:#\d+|TICK-\d+)[^—·]*[—·] ?", "- ", line)
            self.assertNotEqual(bare, line, line)          # the edit actually happened
            found = self._lint("# Agenda\n\n" + bare)
            self.assertEqual(len(found), 1, f"{bare!r} from {line!r}")

    def test_an_identifier_after_the_pair_does_not_silence_it(self):
        """`m.start()` is the boundary, not "the line mentions an identifier".

        Kept beside the two tests above because it is the third possible reading of the
        same rule and the one that would make it useless: if an identifier ANYWHERE ruled
        a line out, appending `on #12` to a leaderboard would switch the lint off.
        """
        self.assertEqual(len(self._lint("# Agenda\n\n- **Bob:** 3 commits on #12\n")), 1)

    def test_a_round_table_of_people_against_what_they_owe_is_not_a_finding(self):
        """People in the rows and a NUMBER in a cell is still not a leaderboard.

        The round table carries a session count and a day count per person, because that
        is how long a line has been carried -- not how much anybody produced. What makes
        a column a count of WORK is its header naming a unit of work, and nothing else;
        without that requirement every table with a person and a number in it would fire.
        """
        self.assertEqual(self._lint(
            "# Agenda\n\n| Person | Track | Sessions | Due |\n|---|---|--:|---|\n"
            "| **Ann** | backend | 2 | *blocked:* refunds |\n"
            "| **Bob** | mobile | 1 | *decide:* release day |\n"), [])

    def test_an_area_table_with_a_closed_column_is_not_a_finding(self):
        # The appendix's own table. Its rows are AREAS, which is what makes a counted
        # column legitimate: nobody's name is in the first cell.
        self.assertEqual(self._lint(
            "# Agenda\n\n| Area | Opened | Closed | No assignee |\n|---|--:|--:|--:|\n"
            "| api | 3 | 2 | **1** |\n| **all** | **3** | **2** | **1**|\n"), [])

    def test_a_counted_column_over_rows_that_are_not_people_is_not_a_finding(self):
        """The rows are what make it a leaderboard, not the column.

        `Issues closed` per AREA is the appendix's own kind of table and is the thing a
        standup is for; the same column per PERSON is the thing CR-150 forbids. So the
        header alone must never be enough -- the first cell has to be a person.
        """
        self.assertEqual(self._lint(
            "# Agenda\n\n| Area | Issues closed | Commits |\n|---|--:|--:|\n"
            "| api | 14 | 61 |\n| mobile | 2 | 9 |\n"), [])

        # ... and the same table with PEOPLE in the first cell is a finding: one changed
        # cell either way, which is the difference the two halves of this assertion pin.
        self.assertEqual(len(self._lint(
            "# Agenda\n\n| Person | Issues closed | Commits |\n|---|--:|--:|\n"
            "| Bob | 14 | 61 |\n| Dee | 2 | 9 |\n")), 2)

    def test_an_item_naming_its_own_identifier_is_not_a_finding(self):
        # `TICK-9 (3 commits) — Ann` is a statement about the work, which is what every
        # line the generator writes is.
        self.assertEqual(self._lint("# Agenda\n\n- TICK-9 (3 commits) — Ann\n"), [])

    def test_a_table_inside_a_fence_is_an_example_not_a_file_s_content(self):
        self.assertEqual(self._lint("# How not to write it\n\n```\n" + LEADER_TABLE + "```\n"), [])


class TheSubjectIsADeclaredPerson(unittest.TestCase):
    """Proposal 5's boundary, where the whole difficulty is (defect pass).

    The subject of a count is resolved against the project's `people:` roster. A shape
    test cannot do this job: a team, an area and a grand total are all spelled the way a
    first name is spelled, so a lint that read the shape answered "work counted per
    person" for `Mobile: 7 PRs merged` and for `Total: 40 PRs merged`. Counts per area are
    what a standup is for, and a lint that fires on ordinary lines gets switched off --
    after which nothing at all is checked.
    """

    # The five lines a standup or weekly status writes, which the shape test flagged.
    TEAMS = ("Mobile: 7 PRs merged", "Backend: 12 issues closed", "Frontend: 3 commits",
             "Payments: 5 issues closed", "Total: 40 PRs merged")

    def _lint(self, body: str, ops_yaml: str | None = None):
        venture, proj = vault(ops_yaml if ops_yaml is not None else cfg(),
                              {"meetings/260924-agenda-daily-standup.md": body})
        return hc.run(proj, only=("persons",))

    def test_a_team_or_area_with_a_count_is_not_a_finding(self):
        for line in self.TEAMS:
            self.assertEqual(self._lint(f"# Agenda\n\n- {line}\n"), [], line)

    def test_a_grand_total_is_not_reported_as_a_count_per_person(self):
        """The clearest case that a shape test gets backwards: `Total` is nobody."""
        self.assertEqual(self._lint("# Agenda\n\n- Total: 40 PRs merged\n"), [])

    def test_the_whole_block_of_team_lines_is_clean_and_a_roster_line_in_it_fires(self):
        """Asserted together, because what matters is the DIFFERENCE between them.

        One file, the five area lines plus one count against a person on the roster: the
        lint must find exactly the one. A reader that flags by shape returns six, and a
        reader that flags nothing returns none -- both fail this one assertion.
        """
        body = "# Agenda\n\n" + "".join(f"- {l}\n" for l in self.TEAMS) + "- Bob: 14 issues closed\n"
        found = self._lint(body)
        self.assertEqual([(f["line"], f["message"].split(" against ")[1].split(".")[0])
                          for f in found], [(8, "Bob")])

    def test_an_area_count_on_the_line_does_not_hide_a_person_count_behind_it(self):
        """Every pair on the line is considered, not only the first one.

        A consequence of the gate: a subject can now be REJECTED for not being a person,
        so a reader that stopped at the first pair would read `Mobile: 7 PRs merged`,
        reject it, and never see the count against a person after it -- which would make
        prefixing any leaderboard line with an area the way to switch the lint off.
        """
        found = self._lint("# Agenda\n\n- Mobile: 7 PRs merged · Bob: 3 commits\n")
        self.assertEqual(len(found), 1)
        self.assertIn("against Bob", found[0]["message"])

    def test_a_table_of_teams_against_counts_is_not_a_finding(self):
        # The same boundary in the table shape: a counted column over rows that are teams.
        self.assertEqual(self._lint(
            "# Agenda\n\n| Team | Issues closed | PRs merged |\n|---|--:|--:|\n"
            "| Mobile | 14 | 3 |\n| Payments | 2 | 1 |\n| Total | 16 | 4 |\n"), [])

    def test_a_table_of_roster_people_against_counts_is_still_a_finding(self):
        # ... and the pair: the same table with roster names in the first cell fires once
        # per row, so neither half can pass by a reader that always or never fires.
        self.assertEqual(len(self._lint("# Agenda\n\n" + LEADER_TABLE)), 2)

    def test_a_name_shaped_subject_off_the_roster_is_not_a_finding(self):
        """A roster of two does not make the third name a person this project declared.

        The gate is the declaration, not "looks like a name": `Dee` is dropped from the
        roster here and the identical line goes clean, which is the one-edit difference
        between a declared person and any other capitalised word.
        """
        two = cfg().replace("  - name: Dee\n", "")
        self.assertEqual(self._lint("# Agenda\n\n" + LEADER_LINE, two), [])
        self.assertEqual(len(self._lint("# Agenda\n\n" + LEADER_LINE)), 1)

    def test_an_alias_of_a_roster_member_is_a_finding(self):
        """Aliases resolve, as they do for every other roster reader in the module.

        A config that declares `aliases: [Dee]` for `Deepa` has said they are the same
        person, so a leaderboard written the short way is the same leaderboard.
        """
        aliased = cfg().replace("  - name: Dee\n", "  - name: Deepa\n    aliases: [Dee]\n")
        self.assertEqual(len(self._lint("# Agenda\n\n" + LEADER_LINE, aliased)), 1)

    def test_a_first_name_of_a_roster_member_is_a_finding(self):
        """A roster entry `Ann Rivera` is `Ann` in the room, and that is how a hand-added
        leaderboard spells her -- a gate that only knew the full spelling would miss it."""
        full = cfg().replace("  - name: Ann\n", "  - name: Ann Rivera\n")
        self.assertEqual(len(self._lint("# Agenda\n\n- **Ann:** 9 commits\n", full)), 1)

    def test_a_project_with_no_roster_gets_no_findings(self):
        """Silence, not a fallback to the shape: a project with no `people:` is usually one
        that has not configured much, and the shape test would give it the false findings
        while a configured project got none. `--check` says the roster is missing instead.
        """
        none = cfg().replace(PEOPLE, "")
        self.assertEqual(self._lint("# Agenda\n\n" + LEADER_TABLE + LEADER_LINE, none), [])

    def test_the_detector_itself_finds_nothing_without_a_roster(self):
        """Asserted on the reader, not only through the lint.

        The lint stops before reading a file no roster governs, so a reader that quietly
        guessed when handed an empty roster would never show up there -- and the digest
        (proposal 2) and any later caller go through the reader. The contract is the
        reader's: no roster, no findings.
        """
        text = "# Agenda\n\n" + LEADER_TABLE + LEADER_LINE
        self.assertEqual(ba.person_count_lines(text, set()), [])
        self.assertEqual(ba.person_count_lines(text, None), [])
        self.assertEqual(ba.person_count_lines(text), [])
        # ... and the same text WITH a roster is two table rows plus the line, so the
        # three assertions above cannot be passing because the text is clean.
        self.assertEqual(len(ba.person_count_lines(text, ROSTER)), 3)

    def _checks(self, ops_yaml: str, with_history: bool = True):
        """`config_checks` for a project, with one past note so there is something to lint."""
        venture, proj = vault(ops_yaml)
        md = proj / "meetings"
        note = md / "260922-daily-standup.md"
        hist = []
        if with_history:
            note.write_text("# Standup\n\n## Carried forward\n\n" + ITEMS, encoding="utf-8")
            hist = [(datetime.date(2026, 9, 22), note)]
        return ba.config_checks(ba.config(md), hist, datetime.date(2026, 9, 24), None)

    def _said(self, ops_yaml: str, with_history: bool = True):
        return [s for s in self._checks(ops_yaml, with_history)
                if "people:" in s and "CR-150" in s]

    def test_the_check_says_so_when_no_roster_is_declared(self):
        self.assertEqual(len(self._said(cfg().replace(PEOPLE, ""))), 1)

    def test_the_check_is_silent_when_a_roster_is_declared(self):
        self.assertEqual(self._said(cfg()), [])

    def test_the_check_is_silent_before_the_series_has_any_history(self):
        """A series with no notes yet has nothing for the check to read, so a missing
        roster is not yet a gap -- and a project that has not held its first session
        should not be told about a check that has nothing to check."""
        self.assertEqual(self._said(cfg().replace(PEOPLE, ""), with_history=False), [])

    def test_the_nearest_roster_governs_a_file(self):
        """Nearest declaration wins, as everywhere else in this family.

        The venture declares one set of people and the project another; a file inside the
        project is read against the project's. Without that, a vault-wide run would resolve
        every file against whichever roster it happened to find first.
        """
        venture, proj = vault(cfg(), {"meetings/260924-agenda-daily-standup.md":
                                      "# Agenda\n\n- **Cai:** 14 issues closed\n"})
        (venture / "_ops.yaml").write_text("people:\n  - name: Cai\n", encoding="utf-8")
        # Scoped to the project: its own roster has no Cai, so the line is not a finding.
        self.assertEqual(hc.run(proj, only=("persons",)), [])
        # Scoped to the venture: the project's config is still the nearest one to the file.
        self.assertEqual(hc.run(venture, only=("persons",)), [])

    def test_a_venture_roster_governs_a_file_no_project_config_covers(self):
        """The other half: a file outside every project IS governed by the venture."""
        venture, proj = vault(cfg())
        (venture / "_ops.yaml").write_text("people:\n  - name: Cai\n", encoding="utf-8")
        (venture / "board").mkdir()
        (venture / "board" / "status.md").write_text(
            "# Status\n\n- **Cai:** 14 issues closed\n", encoding="utf-8")
        found = hc.run(venture, only=("persons",))
        self.assertEqual([(f["file"], f["line"]) for f in found], [("board/status.md", 3)])


class TheMetricsDocumentIsExempt(unittest.TestCase):
    """Proposal 3: `metrics_document:` is the owner-only path -- exempt from the lint,
    never linked from a team-facing file, never written to by the generator."""

    def test_the_declared_document_may_count_people(self):
        venture, proj = vault(cfg() + "metrics_document: status/metrics.md\n",
                              {"status/metrics.md": "# Metrics (owner only)\n\n" + LEADER_TABLE})
        self.assertEqual(hc.run(proj, only=("persons",)), [])

    def test_an_undeclared_document_of_the_same_name_is_not_exempt(self):
        # Exempt by DECLARATION, not by filename: a path nobody declared is a file the
        # team can open, whatever it is called.
        venture, proj = vault(cfg(), {"status/metrics.md": "# Metrics\n\n" + LEADER_TABLE})
        self.assertTrue(hc.run(proj, only=("persons",)))

    def test_the_config_reader_merges_the_key(self):
        venture, proj = vault(cfg() + "metrics_document: status/metrics.md\n",
                              {"status/metrics.md": "x\n"})
        cf = ba.config(proj / "meetings")
        self.assertEqual(cf["metrics_document"], "status/metrics.md")
        self.assertEqual(ba.metrics_path(cf).resolve(), (proj / "status" / "metrics.md").resolve())

    def test_a_declared_document_that_is_not_there_is_a_config_finding(self):
        """A stale declaration exempts nothing, so the figures have no declared home."""
        import datetime
        day = datetime.date(2026, 9, 24)
        venture, proj = vault(cfg() + "metrics_document: status/metrics.md\n")
        missing = [f for f in ba.config_checks(ba.config(proj / "meetings"), [], day, None)
                   if "metrics_document" in f]
        self.assertEqual(len(missing), 1)
        # ... and the finding is about ABSENCE, not about the declaration: the same config
        # with the file written is clean. Without this half, a check that fired always
        # would pass the assertion above.
        (proj / "status").mkdir(exist_ok=True)
        (proj / "status" / "metrics.md").write_text("# Metrics\n", encoding="utf-8")
        self.assertEqual([f for f in ba.config_checks(ba.config(proj / "meetings"), [], day, None)
                          if "metrics_document" in f], [])

    def test_a_project_declaring_nothing_gets_no_metrics_finding(self):
        import datetime
        venture, proj = vault(cfg())
        self.assertEqual([f for f in ba.config_checks(ba.config(proj / "meetings"), [],
                                                      datetime.date(2026, 9, 24), None)
                          if "metrics_document" in f], [])

    def test_the_generator_never_writes_to_it_and_never_links_it(self):
        venture, proj = vault(cfg("card") + "metrics_document: status/metrics.md\n",
                              {"status/metrics.md": "# Metrics (owner only)\n\n" + LEADER_TABLE})
        md = proj / "meetings"
        (md / "260922-daily-standup.md").write_text(
            "# Standup\n\n## Carried forward\n\n" + ITEMS, encoding="utf-8")
        before = (proj / "status" / "metrics.md").read_text(encoding="utf-8")
        subprocess.run([sys.executable, str(OPS / "build_agenda.py"), "--dir", str(md),
                        "--date", "260924"], check=True, capture_output=True, text=True)
        self.assertEqual((proj / "status" / "metrics.md").read_text(encoding="utf-8"), before)
        for p in md.glob("260924-*"):
            self.assertNotIn("metrics.md", p.read_text(encoding="utf-8"), p.name)


class ASourceCarryingFiguresIsNamedNotCopied(unittest.TestCase):
    """Proposal 2: one line, naming the source, and no figure from it."""

    def _build(self, report_body: str, layout: str = ""):
        venture, proj = vault(
            cfg(layout) + ("external_systems:\n  vault_reports:\n    - name: Team status\n"
                           "      dir: status\n      current: status.md\n"),
            {"status/status.md": report_body})
        md = proj / "meetings"
        (md / "260922-daily-standup.md").write_text(
            "# Standup\n\n## Carried forward\n\n" + ITEMS, encoding="utf-8")
        res = subprocess.run([sys.executable, str(OPS / "build_agenda.py"), "--dir", str(md),
                              "--date", "260924"], check=True, capture_output=True, text=True)
        written = {p.name: p.read_text(encoding="utf-8") for p in sorted(md.glob("260924-*"))}
        return written, res.stdout

    NOTE = "per-person figures present in the source, not copied"

    def test_the_note_is_one_line_naming_the_source(self):
        written, _out = self._build("# Status\n\n" + LEADER_TABLE)
        lines = [l for t in written.values() for l in t.splitlines() if self.NOTE in l]
        self.assertEqual(len(lines), 1)
        self.assertIn("Team status", lines[0])

    def test_no_figure_from_the_source_is_copied(self):
        written, _out = self._build("# Status\n\n" + LEADER_TABLE)
        for name, text in written.items():
            self.assertNotIn("| Bob | 14 |", text, name)
            self.assertNotIn("Issues closed", text, name)
            self.assertEqual(ba.person_count_lines(text, ROSTER), [], name)

    def test_a_source_with_no_per_person_figures_produces_no_note(self):
        written, _out = self._build(
            "# Status\n\n| Area | Opened | Closed |\n|---|--:|--:|\n| api | 3 | 2 |\n")
        self.assertEqual([l for t in written.values() for l in t.splitlines() if self.NOTE in l], [])

    def test_the_reader_is_the_same_one_the_lint_uses(self):
        # One reader for one rule (the CR-142 precedent): a lint and a generator that
        # disagreed about what a count against a name is would be worse than neither.
        venture, proj = vault(cfg() + ("external_systems:\n  vault_reports:\n    - name: Team status\n"
                                       "      dir: status\n      current: status.md\n"),
                              {"status/status.md": "# Status\n\n" + LEADER_TABLE})
        cf = ba.config(proj / "meetings")
        self.assertEqual(len(ba.source_person_counts(cf)), 1)
        self.assertIs(hc.build_agenda.person_count_lines, ba.person_count_lines)

    def test_the_declared_metrics_document_is_not_reported_as_a_source(self):
        venture, proj = vault(
            cfg() + "metrics_document: status/status.md\n"
            + ("external_systems:\n  vault_reports:\n    - name: Team status\n"
               "      dir: status\n      current: status.md\n"),
            {"status/status.md": "# Status\n\n" + LEADER_TABLE})
        cf = ba.config(proj / "meetings")
        self.assertEqual(ba.source_person_counts(cf), [])


class OneResolverForADeclaredReport(unittest.TestCase):
    """Which FILE a `vault_reports:` declaration names is one answer, not two.

    `build_movement` already owns that declaration -- it is what reports a report's age
    to `--check` -- so the digest reads the file that module resolves (defect pass). Two
    resolvers would eventually disagree, and then a report's age would be read off one
    file and its per-person figures off another. Asserted by making the two answer about
    the same declaration and requiring the same file, so a second resolver reintroduced
    here fails as soon as it differs.
    """

    DECL = ("external_systems:\n  vault_reports:\n    - name: Team status\n"
            "      dir: status\n      pattern: '^\\d{6}-status\\.md$'\n")
    CLEAN = "# Status\n\n| Area | Closed |\n|---|--:|\n| api | 2 |\n"

    def _cf(self, files):
        venture, proj = vault(cfg() + self.DECL, files)
        return ba.config(proj / "meetings"), proj

    def test_the_digest_reads_the_newest_of_a_dated_series(self):
        """The figures are in the OLD file only, so a resolver picking the newest finds
        none -- and the same resolver is the one `--check` dates the series by."""
        cf, _proj = self._cf({"status/260901-status.md": "# Status\n\n" + LEADER_TABLE,
                              "status/260923-status.md": self.CLEAN})
        self.assertEqual(ba.source_person_counts(cf), [])
        _l, states = bm.vault_reports(cf, datetime.date(2026, 9, 24))
        self.assertEqual([s[2] for s in states], ["260923-status.md"])

    def test_and_finds_them_when_the_newest_is_the_one_carrying_them(self):
        # The pair: the two files swapped, nothing else. One line of output either way,
        # which is what makes the test above a statement about WHICH file was read.
        cf, _proj = self._cf({"status/260901-status.md": self.CLEAN,
                              "status/260923-status.md": "# Status\n\n" + LEADER_TABLE})
        self.assertEqual(len(ba.source_person_counts(cf)), 1)

    def test_a_current_path_wins_over_the_dated_series_for_both_readers(self):
        """`current:` is the author's statement that this is the live file. The digest and
        `--check` have to agree about that too, or they are reading different reports."""
        cf, _proj = self._cf({"status/260923-status.md": "# Status\n\n" + LEADER_TABLE})
        (Path(cf["_root"]) / "status" / "live.md").write_text(self.CLEAN, encoding="utf-8")
        cf["ext"]["vault_reports"][0]["current"] = "live.md"
        self.assertEqual(ba.source_person_counts(cf), [])
        _l, states = bm.vault_reports(cf, datetime.date(2026, 9, 24))
        self.assertEqual([s[2] for s in states], ["live.md"])

    def test_a_directory_found_by_walking_up_is_read_by_both(self):
        """`dir:` resolves from the project root or above, which is how a project nested
        under a venture declares the venture's board folder."""
        venture, proj = vault(cfg() + self.DECL.replace("dir: status", "dir: board"))
        (venture / "board").mkdir()
        (venture / "board" / "260923-status.md").write_text("# Status\n\n" + LEADER_TABLE,
                                                            encoding="utf-8")
        cf = ba.config(proj / "meetings")
        self.assertEqual(len(ba.source_person_counts(cf)), 1)
        self.assertEqual(bm.vault_report_dir(cf, cf["ext"]["vault_reports"][0]),
                         (venture / "board").resolve())


class TheLintReadsConfigsOnce(unittest.TestCase):
    """The lint's config scan is one walk over the tree, with one copy of the config
    file pair and the dot-folder skip (defect pass).

    A second walk and a second literal pair were cost and drift risk: a config filename
    or a skip rule changed in one place and not the other is a declaration the lint
    silently cannot see. Asserted on what the scan ANSWERS -- both spellings of the
    config file are honoured, and a dot-folder is skipped -- not on how it is written.
    """

    def test_both_spellings_of_the_config_file_declare_a_roster(self):
        for rel in ("_ops.yaml", ".claude/ops-config.yaml"):
            venture = Path(tempfile.mkdtemp()) / "venture"
            proj = venture / "proj"
            (proj / "meetings").mkdir(parents=True)
            (proj / rel).parent.mkdir(parents=True, exist_ok=True)
            (proj / rel).write_text(cfg(), encoding="utf-8")
            (proj / "meetings" / "260924-agenda-daily-standup.md").write_text(
                "# Agenda\n\n" + LEADER_LINE, encoding="utf-8")
            self.assertEqual(len(hc.run(proj, only=("persons",))), 1, rel)

    def test_both_spellings_declare_the_exempt_document(self):
        for rel in ("_ops.yaml", ".claude/ops-config.yaml"):
            venture, proj = vault("", {"status/metrics.md": "# Metrics\n\n" + LEADER_TABLE})
            (proj / "_ops.yaml").unlink()
            (proj / rel).parent.mkdir(parents=True, exist_ok=True)
            (proj / rel).write_text(cfg() + "metrics_document: status/metrics.md\n",
                                    encoding="utf-8")
            self.assertEqual(hc.run(proj, only=("persons",)), [], rel)

    def test_a_leaderboard_inside_a_dot_folder_is_not_linted(self):
        """`walk()` owns the dot-folder skip and the scan inherits it: an archived file is
        not a file the team reads, and `.archive/` is this repo's archive convention.

        Asserted as a pair with the same file one folder over, so it cannot pass because
        the content is clean or because no roster was found.
        """
        venture, proj = vault(cfg(), {".archive/260101-agenda-daily-standup.md":
                                      "# Agenda\n\n" + LEADER_LINE})
        self.assertEqual(hc.run(proj, only=("persons",)), [])
        (proj / "meetings" / "260924-agenda-daily-standup.md").write_text(
            "# Agenda\n\n" + LEADER_LINE, encoding="utf-8")
        self.assertEqual(len(hc.run(proj, only=("persons",))), 1)

    def test_a_roster_declared_above_the_scanned_folder_is_read(self):
        """`config()` walks UP, so the scan has to as well.

        A project that declares its loop in its own config and its roster at the venture
        level is read against that roster by the agenda. A lint that only looked downward
        would call the same file clean when the project was scanned and a finding when the
        venture was -- two answers about one file, which is the worse of the two bugs.
        """
        venture, proj = vault("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n",
                              {"meetings/260924-agenda-daily-standup.md": "# Agenda\n\n" + LEADER_LINE})
        (venture / "_ops.yaml").write_text(PEOPLE, encoding="utf-8")
        for scope in (proj, venture):
            found = hc.run(scope, only=("persons",))
            self.assertEqual([f["line"] for f in found], [3], scope.name)

    def test_the_preferred_file_of_the_pair_wins_within_one_folder(self):
        """A folder declaring both files resolves to the one `config()` prefers.

        `CONFIG_FILES` is in that order, and the scan has to honour it: a project that
        declares a roster in `.claude/ops-config.yaml` and a stale one in `_ops.yaml`
        would otherwise be linted against whichever was read first. Pinned by making the
        two rosters disjoint, so the finding names which file was believed.
        """
        venture, proj = vault(cfg().replace(PEOPLE, "people:\n  - name: Cai\n"),
                              {"meetings/260924-agenda-daily-standup.md":
                               "# Agenda\n\n- **Dee:** 14 issues closed\n- **Cai:** 9 commits\n"})
        (proj / ".claude").mkdir()
        (proj / ".claude" / "ops-config.yaml").write_text(cfg(), encoding="utf-8")
        found = hc.run(proj, only=("persons",))
        # `.claude/ops-config.yaml` declares Ann/Bob/Dee, `_ops.yaml` declares Cai.
        self.assertEqual([f["line"] for f in found], [3])
        self.assertIn("against Dee", found[0]["message"])

    def test_a_file_of_the_right_name_in_the_wrong_place_is_not_a_config(self):
        # `ops-config.yaml` belongs in `.claude/`; loose in the project it is a document.
        venture, proj = vault(cfg().replace(PEOPLE, ""),
                              {"meetings/260924-agenda-daily-standup.md": "# Agenda\n\n" + LEADER_LINE,
                               "ops-config.yaml": cfg()})
        self.assertEqual(hc.run(proj, only=("persons",)), [])


class TheContractIsDocumented(unittest.TestCase):
    def test_persons_is_a_declared_check(self):
        self.assertIn("persons", hc.CHECKS)

    def test_the_skill_documents_the_check_and_the_boundary(self):
        self.assertIn("persons", SKILL)
        self.assertIn("CR-150", SKILL)

    def test_the_schema_documents_the_key(self):
        self.assertIn("metrics_document", SCHEMA)

    def test_the_schema_documents_the_roster_dependency(self):
        # Somebody declaring `metrics_document:` needs to know the check it exempts a path
        # from answers about declared people only, and about nothing without a roster.
        self.assertRegex(SCHEMA, r"needs a `people:` roster")

    def test_the_skill_documents_the_roster_gate(self):
        # The boundary a reader needs to know before switching the check on: it answers
        # about declared people only, and says nothing at all without a roster.
        self.assertIn("people:", SKILL)
        self.assertRegex(SKILL, r"no `people:` roster the\s+check finds nothing")


class TheBoundaryHasNoEscapeHatch(unittest.TestCase):
    """Spellings a leaderboard is actually written in, in both directions.

    The first implementation of this lint fired on every team total; the fix for
    that opened the opposite hole, and five real per-person counts went unreported
    -- `has`/`with` were unreachable legs of the pattern, a subject could not follow
    sentence punctuation, `re.I` let a two-word name swallow `has`, and a separator
    inside the emphasis (`**Bob:**`) was not matched. Each is one line here, so the
    boundary cannot drift back in either direction unnoticed.
    """

    FIRES = (
        "Bob: 14 issues closed",
        "Bob has 14 issues closed",
        "Bob with 6 merge requests",
        "Dee has 5 commits",
        "Total: 40 PRs merged, Bob: 14 issues closed",
        "Total: 40 PRs merged. Bob: 14 issues closed",
        "Total: 40 PRs merged; Bob: 14 issues closed",
        "- **Dee** -- 14 issues closed",
        "**Bob:** 14 issues",
        "Ann - 7 story points",
        "**Dee** 22 LOC",
    )

    # A team, an area or a grand total is not a person. A lint that reports these is
    # switched off by the first operator who reads one, and then reports nothing.
    STAYS_CLEAN = (
        "Mobile: 7 PRs merged",
        "Backend: 12 issues closed",
        "Frontend: 3 commits",
        "Payments: 5 issues closed",
        "Platform: 9 tickets closed",
        "Total: 40 PRs merged",
        "Mobile has 7 PRs merged",
        # A name beside an item is accountability, not a scoreboard (proposal 5).
        "| Webhook retry | Bob | open |",
        "- **Payment webhook fails** - #12 - **Ann**",
    )

    def test_a_count_against_a_declared_person_is_found(self):
        for line in self.FIRES:
            with self.subTest(line=line):
                self.assertTrue(ba.person_count_lines(line, ROSTER),
                                "a per-person count went unreported")

    def test_a_count_against_a_team_or_an_item_owner_is_not(self):
        for line in self.STAYS_CLEAN:
            with self.subTest(line=line):
                self.assertEqual(ba.person_count_lines(line, ROSTER), [],
                                 "an aggregate or an owner was reported as a person")

    def test_a_two_word_name_in_a_leaderboard_table_is_found(self):
        # The table branch, which carries the count columns from the header row.
        table = ("| Person | PRs |\n|---|---|\n"
                 "| Dee Okafor | 312 |\n| Bob | 14 |\n")
        hits = ba.person_count_lines(table, ROSTER | {"dee okafor"})
        self.assertEqual(len(hits), 2)
        self.assertNotIn("312", " ".join(t for _n, t in hits),
                         "the finding must not repeat the figure")
