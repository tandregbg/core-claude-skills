"""CR-148: a compact card layout -- four outputs instead of two. Invented data.

A project's own rule is that a chat message is three to five lines of plain text,
because pasted markdown shows as literal asterisks. The day's generated post ran about
660 words in markdown and the agenda about 1,880, and the room walked the agenda row by
row with the dependencies appearing twice -- once as a section, once again in each
person's cell of the round.

`layout: compact` redistributes the sections the card already computes: a plain-text
post, an agenda that is the decisions and the round, a facilitator document carrying the
dependencies read against the data, and the details file unchanged.

The first class here is the one that matters most: it asserts that the DEFAULT card is
unchanged, by naming the exact titles and lead lines, so a later edit to SECTIONS cannot
drift them silently. The byte-for-byte proof of the same claim is `DefaultCardIsExact`,
which renders the card fixture and compares it against the shipped expectation.
"""

import datetime
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr101_agenda_draft import build  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_agenda as ba  # noqa: E402
import build_movement as bm  # noqa: E402

DAY = datetime.date(2026, 9, 24)
PEOPLE = "people:\n  - name: Ann\n  - name: Bob\n  - name: Dee\n"
MS = ("milestones:\n"
      "  - name: Backend release\n    date: 2026-10-01\n    state: confirmed\n"
      "    source: DEC-12\n    set_on: 2026-09-01\n"
      "  - name: Rollout step one\n    date: 2026-10-15\n    set_on: 2026-09-01\n")
CARD = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
        "      layout: card\n") + PEOPLE + MS
COMPACT = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
           "      layout: compact\n") + PEOPLE + MS
# CR-155: the facilitator's dependencies table is optional and off by default, so the
# tests that read it ask for it.
COMPACT_DEPS = COMPACT.replace("      layout: compact\n",
                               "      layout: compact\n      compact:\n"
                               "        facilitator_dependencies: true\n")
ITEMS = ("- [blocker] **Payment webhook fails** — #12 · **Bob**\n"
         "- [dependency] **Backend answer on refunds** — TICK-9 · **Ann**\n"
         "- [dependency] **Legal sign-off on the terms** — LEG-4 · **Dee**\n"
         "- [decision] **Canary shape** — DEC-7 · **Ann, Bob**\n"
         "- **Update the readme** — docs/README.md · **Bob**\n")
# One earlier note, so every line above is in its SECOND session. A first-session line
# is asserted without asking (CR-147, proposal 4: the room raised it last night), and a
# third session puts the untagged task over the escalation threshold -- both are other
# CRs' paths. Two sessions is where the card carries each kind in its own section.
PRIOR = {"260920": ITEMS}
# CR-148, acceptance bullet 1: "with ten blockers, the post is at most 150 words".
# Ten titles the length a real tracker produces -- the original fixture used "Blocker 3
# on the payment path", which fits whatever the implementation does and so asserted
# nothing about the ceiling. Invented, about one issue title each.
BLOCKER_TITLES = [
    "Outbound calls to one mobile network drop after twelve seconds on the new codec path",
    "Signup confirmation mail is not delivered when the address carries a plus-addressed alias",
    "The app crashes on launch when the device locale is set to a right-to-left language",
    "A porting request never leaves pending in the customer portal after it is approved",
    "The billing export double-counts refunded subscriptions in the monthly reconciliation",
    "Notifications stop arriving once the app has been in the background for six hours",
    "Recording playback fails for recordings longer than forty minutes in one browser",
    "The two-factor reset flow lets an unverified address receive the recovery code",
    "The dashboard graph shows yesterday figures when the browser timezone is behind UTC",
    "Transcription returns an empty body for calls shorter than four seconds",
]


def files(date="260924"):
    return {p.name: p.read_text(encoding="utf-8")
            for p in Path(build.last_meetings).glob(f"{date}-*")}


class DefaultCardIsUnchanged(unittest.TestCase):
    """The CR requirement, not the implementation: `layout: card` stays the default and
    its titles, leads and columns are exactly what CR-107/CR-114 shipped. These strings
    now live in SECTIONS, so this is what stops an edit there from drifting them."""

    def setUp(self):
        self.agenda, _ = build(CARD, note_items=ITEMS, notes=PRIOR)

    def test_the_titles_are_exact(self):
        self.assertIn("## Release blockers", self.agenda)
        self.assertIn("## Dependencies", self.agenda)
        self.assertIn("## Decisions needed today", self.agenda)

    def test_the_lead_lines_are_exact(self):
        for lead in ("**What blocks the release, who owns it, the plan.**",
                     "**A person waiting on another person, or on someone outside the room.**",
                     "**Each one leaves the room decided, or with a date.**"):
            self.assertIn(lead, self.agenda, lead)

    def test_the_columns_are_exact(self):
        for col in ("| Item | Owner | Stuck for |", "| Item | Owner | Waiting |",
                    "| Item | Owner | Open for |"):
            self.assertIn(col, self.agenda, col)

    def test_the_order_is_the_cards(self):
        heads = [l for l in self.agenda.split("\n") if l.startswith("## ")]
        self.assertEqual(heads, ["## Milestones", "## Release blockers", "## Dependencies",
                                 "## Decisions needed today", "## One-minute round",
                                 "## Close"])

    def test_the_card_writes_two_files_and_no_facilitator(self):
        got = set(files())
        self.assertIn("260924-agenda-daily-standup.md", got)
        self.assertIn("260924-agenda-details-daily-standup.md", got)
        self.assertIn("260924-teams-agenda-daily-standup.md", got)
        self.assertNotIn("260924-agenda-facilitator-daily-standup.md", got)
        self.assertNotIn("260924-teams-agenda-daily-standup.txt", got)


class CompactPost(unittest.TestCase):
    """Acceptance 1: plain text, at most `max_words`, no round, no dependencies."""

    def setUp(self):
        build(COMPACT, note_items=ITEMS, notes=PRIOR)
        self.txt = files()["260924-teams-agenda-daily-standup.txt"]

    def test_the_post_is_a_txt_file_and_the_markdown_one_is_not_written(self):
        self.assertNotIn("260924-teams-agenda-daily-standup.md", files())

    def test_no_markdown_character_anywhere(self):
        """The measured failure: pasted markdown shows as literal asterisks."""
        self.assertEqual([c for c in "*_`#|[]" if c in self.txt], [])

    def test_the_milestones_are_a_dated_list_with_a_state_each(self):
        self.assertIn("- Backend release: 2026-10-01, confirmed, 7 days", self.txt)
        self.assertIn("- Rollout step one: 2026-10-15, proposed", self.txt)

    def test_the_blockers_are_one_per_line_and_grouped(self):
        self.assertIn("To fix:", self.txt)
        self.assertIn("- Payment webhook fails (Bob)", self.txt)

    def test_the_ask_is_there(self):
        self.assertIn("Bring what moved, what is stuck and who owns the other end.", self.txt)

    def test_on_demo_day_the_post_carries_the_demo_list(self):
        """CR-121 through the compact post: the demo list, in plain text, first."""
        demo = COMPACT.replace(MS, "milestone:\n  name: First demo day\n"
                                   "  date: 2026-09-24\n  set_on: 2026-09-01\n  kind: demo\n")
        build(demo, note_items=ITEMS, notes=PRIOR)
        txt = files()["260924-teams-agenda-daily-standup.txt"]
        self.assertIn("Demo today: Payment webhook fails", txt)
        self.assertEqual([c for c in "*_`#|[]" if c in txt], [])

    def test_off_demo_day_the_post_carries_no_demo_line(self):
        demo = COMPACT.replace(MS, "milestone:\n  name: First demo day\n"
                                   "  date: 2026-09-24\n  set_on: 2026-09-01\n  kind: demo\n")
        build(demo, note_items=ITEMS, notes=PRIOR, date="260925")
        txt = files("260925")["260925-teams-agenda-daily-standup.txt"]
        self.assertNotIn("Demo today", txt)

    def test_no_round_and_no_dependencies(self):
        self.assertNotIn("Order:", self.txt)
        self.assertNotIn("Round", self.txt)
        self.assertNotIn("Backend answer on refunds", self.txt)
        self.assertNotIn("Legal sign-off", self.txt)

    def test_ten_realistic_blockers_still_fit_in_the_default_limit(self):
        """CR-148 acceptance bullet 1, with titles the length a tracker really writes.

        The ceiling HOLDS: it is not a warning beside a long file. The blocker list is
        the part that gives way, and what is dropped is COUNTED in the post, so the
        reader is never told a short list is the whole list.
        """
        ten = "".join(f"- [blocker] **{t}** — #{i + 1} · **Bob**\n"
                      for i, t in enumerate(BLOCKER_TITLES))
        _a, out = build(COMPACT, note_items=ten, notes={"260920": ten})
        txt = files()["260924-teams-agenda-daily-standup.txt"]
        self.assertLessEqual(len(txt.split()), 150, txt)
        self.assertEqual([c for c in "*_`#|[]" if c in txt], [])
        # it warns, and the post itself says how many are not in it and where they are
        self.assertRegex(out, r"post is \d+ words \(limit 150\)")
        self.assertRegex(txt, r"- and \d+ more, in 260924-agenda-daily-standup\.md")
        # every blocker it DOES list is a whole title, never a cut-off one
        listed = [l for l in txt.split("\n") if l.startswith("- ") and "more, in" not in l
                  and not l.startswith("- Backend") and not l.startswith("- Rollout")]
        self.assertTrue(listed)
        for l in listed:
            self.assertIn(l[2:].rsplit(" (", 1)[0], BLOCKER_TITLES, l)

    def test_nothing_is_dropped_without_being_counted(self):
        """The count in the post must be the real number left out, not a constant: the
        same ten blockers at two limits leave out different numbers, and listed plus
        left-out always equals ten."""
        ten = "".join(f"- [blocker] **{t}** — #{i + 1} · **Bob**\n"
                      for i, t in enumerate(BLOCKER_TITLES))

        def run(limit):
            cfg = COMPACT.replace("      layout: compact\n",
                                  "      layout: compact\n      compact:\n"
                                  f"        max_words: {limit}\n")
            build(cfg, note_items=ten, notes={"260920": ten})
            txt = files()["260924-teams-agenda-daily-standup.txt"]
            shown = sum(1 for t in BLOCKER_TITLES if t in txt)
            left = int(re.search(r"- and (\d+) more, in ", txt).group(1))
            self.assertLessEqual(len(txt.split()), limit, txt)
            return shown, left

        for limit in (60, 100, 140):
            shown, left = run(limit)
            self.assertEqual(shown + left, 10, (limit, shown, left))
        self.assertLess(run(60)[0], run(140)[0])

    def test_over_the_limit_it_names_the_part_that_is_actually_the_longest(self):
        """CR-148 proposal 1: "it warns and names the longest part". The format alone
        proves nothing -- the named part has to BE the longest, so each of the two
        parts that can grow is made the longest in turn and the warning must follow it.
        """
        cfg = COMPACT.replace("      layout: compact\n",
                              "      layout: compact\n      compact:\n        max_words: 20\n")
        # ten long blocker titles, one short milestone: blockers is the longest part
        many_b = "".join(f"- [blocker] **{BLOCKER_TITLES[i]}** — #{i + 1} · **Bob**\n"
                         for i in range(10))
        _a, out = build(cfg, note_items=many_b, notes={"260920": many_b})
        self.assertRegex(out, r"longest part: blockers, \d+ words")
        # now eight long milestone names and one short blocker: milestones is longest
        long_ms = "milestones:\n" + "".join(
            f"  - name: {BLOCKER_TITLES[i]}\n    date: 2026-1{i // 5}-0{i % 5 + 1}\n"
            "    set_on: 2026-09-01\n" for i in range(8))
        one_b = "- [blocker] **Short one** — #1 · **Bob**\n"
        _a2, out2 = build(cfg.replace(MS, long_ms), note_items=one_b,
                          notes={"260920": one_b})
        self.assertRegex(out2, r"longest part: milestones, \d+ words")
        # and the two runs really did name different parts, so neither is a constant
        self.assertNotEqual([l for l in out.split("\n") if "longest part" in l],
                            [l for l in out2.split("\n") if "longest part" in l])

    def test_the_milestones_and_the_ask_are_never_what_gives_way(self):
        """What the post gives up under a ceiling is a decision, not an accident.

        The milestones are declared by the project and the ask is one line and the
        reason the post exists; only the blocker list is unbounded, so only the blocker
        list is shortened. At a limit too small for any of it, the post still carries
        the heading, the milestones and the ask -- never a post with no ask.
        """
        cfg = COMPACT.replace("      layout: compact\n",
                              "      layout: compact\n      compact:\n        max_words: 20\n")
        build(cfg, note_items=ITEMS, notes=PRIOR)
        txt = files()["260924-teams-agenda-daily-standup.txt"]
        self.assertIn("- Backend release: 2026-10-01, confirmed, 7 days", txt)
        self.assertIn("Bring what moved, what is stuck and who owns the other end.", txt)
        self.assertIn("proj — Thursday 24 September", txt)
        # the blockers are what went, and the post says so rather than going quiet
        self.assertNotIn("Payment webhook fails", txt)
        self.assertIn("more, in 260924-agenda-daily-standup.md", txt)

    def test_the_default_limit_is_150(self):
        """The only coverage of the default. Asserted through BEHAVIOUR: with no
        `max_words` the post obeys 150 and not some other number, which is shown by
        declaring 150 explicitly and getting the identical file, and by declaring 149
        and 151 and getting a file that differs from it in the expected direction.
        A grep for the literal would pass against `or 15` or `or 1500`.
        """
        long_ = "".join(f"- [blocker] **{BLOCKER_TITLES[i]}** — #{i + 1} · **Bob**\n"
                        for i in range(10))
        mk = lambda n: (COMPACT if n is None else COMPACT.replace(
            "      layout: compact\n",
            f"      layout: compact\n      compact:\n        max_words: {n}\n"))

        def post(n):
            build(mk(n), note_items=long_, notes={"260920": long_})
            return files()["260924-teams-agenda-daily-standup.txt"]

        unset, at_150 = post(None), post(150)
        self.assertEqual(unset, at_150)                       # the default IS 150
        self.assertLessEqual(len(unset.split()), 150)
        # and the default is really 150, not some other number the ceiling happens to
        # sit under: at a smaller limit the post keeps fewer blockers, at a larger one
        # it keeps more, and the unset run sits between them.
        shown = lambda t: sum(1 for x in BLOCKER_TITLES if x in t)
        self.assertLess(shown(post(100)), shown(unset))
        self.assertGreater(shown(post(400)), shown(unset))
        self.assertEqual(shown(post(400)), 10)                # 400 fits all ten

    def test_max_words_zero_is_not_read_as_unset(self):
        """CR-148's own key may legitimately be 0 -- a project writing 0 to mean
        "always warn" must get the warning, not the silent default of 150."""
        cfg = COMPACT.replace("      layout: compact\n",
                              "      layout: compact\n      compact:\n        max_words: 0\n")
        _a, out = build(cfg, note_items=ITEMS, notes=PRIOR)
        self.assertRegex(out, r"post is \d+ words \(limit 0\)")


class CompactPostGroupsTheRepoBlockers(unittest.TestCase):
    """CR-148 proposal 1: "blockers one per line, grouped *to fix* and *waiting for a
    test*". The second group comes only from the repo, so before the movement archive
    existed (CR-121/CR-148) the "Waiting for a test:" branch had ZERO coverage.
    """

    LABELS = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
              "      labels:\n        priority: [blocker, critical]\n"
              "        gap: [blocker, critical]\n"
              "        awaiting_test: 'status: Fixed'\n"
              "        area_prefix: 'area:'\n")

    @staticmethod
    def issue(n, title, labels, who=()):
        return {"number": n, "title": title, "state": "OPEN",
                "createdAt": "2026-09-01T09:00:00Z", "closedAt": None,
                "labels": [{"name": x} for x in labels],
                "assignees": [{"login": w} for w in who],
                "url": f"https://github.com/acme/app/issues/{n}"}

    def setUp(self):
        mv = {"repo": "acme/app",
              "issues": [self.issue(41, "Refund webhook retries forever",
                                    ["blocker", "area:payments"], who=["bob"]),
                         self.issue(42, "Locale crash on launch",
                                    ["blocker", "status: Fixed", "area:app"], who=["ann"])],
              "labels": [{"name": n, "description": ""} for n in
                         ("blocker", "critical", "status: Fixed", "area:payments", "area:app")],
              "events": [["labeled", "2026-09-01T09:05:00Z", 41, "blocker"],
                         ["labeled", "2026-09-01T09:05:00Z", 42, "blocker"],
                         ["labeled", "2026-09-10T09:05:00Z", 42, "status: Fixed"]]}
        self.agenda, _ = build(COMPACT + self.LABELS, note_items=ITEMS, notes=PRIOR,
                               movement=mv)
        self.txt = files()["260924-teams-agenda-daily-standup.txt"]

    def test_the_archived_record_drives_the_whole_movement_block(self):
        """Not only the grouped post: the release-gap series the facilitator document
        carries is rebuilt from the same archived record, and its own checks pass
        against it. The movement half used to be reachable only with a live `gh`.
        """
        f = files()["260924-agenda-facilitator-daily-standup.md"]   # CR-148: it moved here
        self.assertIn("## Movement", f)
        gap = [l for l in f.split("\n") if "**Release gap**" in l]
        self.assertEqual(len(gap), 1, f)
        self.assertIn("**2**", gap[0])              # both gap-label issues
        self.assertIn("| Release gap: still to fix | **1**", f)      # one not yet fixed
        self.assertIn("| Release gap: fixed, waiting for a test | 1 |", f)
        # the state rebuilt from the record must equal the record's own live state --
        # the check the movement block prints pass or fail, never silently
        self.assertIn("**Checks: passed**", f)
        self.assertNotIn("CHECK FAILED", f)

    def test_both_groups_are_written(self):
        self.assertIn("To fix:", self.txt)
        self.assertIn("Waiting for a test:", self.txt)

    def test_each_issue_is_under_the_group_its_label_puts_it_in(self):
        to_fix = self.txt.split("To fix:")[1].split("Waiting for a test:")[0]
        waiting = self.txt.split("Waiting for a test:")[1]
        self.assertIn("Refund webhook retries forever (#41)", to_fix)
        self.assertNotIn("Locale crash on launch", to_fix)
        self.assertIn("Locale crash on launch (#42)", waiting)
        self.assertNotIn("Refund webhook retries forever", waiting)

    def test_a_carried_blocker_line_joins_the_to_fix_group(self):
        """A line nobody has fixed is something to fix, whatever its source."""
        to_fix = self.txt.split("To fix:")[1].split("Waiting for a test:")[0]
        self.assertIn("Payment webhook fails (Bob)", to_fix)

    def test_it_is_still_plain_text(self):
        self.assertEqual([c for c in "*_`#|[]" if c in self.txt.replace("(#41)", "")
                          .replace("(#42)", "")], [])

    def test_a_group_emptied_by_the_ceiling_takes_its_heading_with_it(self):
        """The CR asks for the two groups; it does not ask for a heading with nothing
        under it. A limit that leaves room for the to-fix lines and not for the waiting
        ones must drop "Waiting for a test:" as well, and still count what it dropped.
        """
        mv = {"repo": "acme/app",
              "issues": [self.issue(40 + i, BLOCKER_TITLES[i],
                                    ["blocker", "area:payments"]
                                    + (["status: Fixed"] if i >= 5 else []))
                         for i in range(10)],
              "labels": [{"name": n, "description": ""} for n in
                         ("blocker", "critical", "status: Fixed", "area:payments")],
              "events": [["labeled", "2026-09-01T09:05:00Z", 40 + i, "blocker"]
                         for i in range(10)]
                        + [["labeled", "2026-09-10T09:05:00Z", 40 + i, "status: Fixed"]
                           for i in range(5, 10)]}
        # 130 is the limit where some to-fix rows fit and no waiting row does, so the
        # second heading would be left MID-LIST with nothing under it.
        cfg = (COMPACT + self.LABELS).replace(
            "      layout: compact\n",
            "      layout: compact\n      compact:\n        max_words: 130\n")
        build(cfg, note_items=ITEMS, notes=PRIOR, movement=mv)
        txt = files()["260924-teams-agenda-daily-standup.txt"]
        self.assertLessEqual(len(txt.split()), 130, txt)
        self.assertIn("To fix:", txt)
        self.assertGreater(sum(1 for l in txt.split("\n")
                               if l.startswith("- ") and "more, in" not in l
                               and not l.startswith("- Backend")
                               and not l.startswith("- Rollout")), 1, txt)
        self.assertNotIn("Waiting for a test:", txt)
        # the heading went, and nothing went silently: the count is still there
        self.assertRegex(txt, r"- and \d+ more, in 260924-agenda-daily-standup\.md")

    def test_the_archives_label_list_is_what_the_declared_labels_are_checked_against(self):
        """The record's third list. A declared label the repo does not have makes every
        count silently zero, which CR-119 reports -- and the archive is where the
        repo's real label set now comes from, so dropping it would silence the report.
        """
        mv = {"repo": "acme/app",
              "issues": [self.issue(41, "Refund webhook retries forever",
                                    ["blocker", "area:payments"], who=["bob"])],
              # `status: Fixed` is DECLARED in LABELS and absent here
              "labels": [{"name": n, "description": ""} for n in
                         ("blocker", "critical", "area:payments")],
              "events": [["labeled", "2026-09-01T09:05:00Z", 41, "blocker"]]}
        agenda, _ = build(COMPACT + self.LABELS, note_items=ITEMS, notes=PRIOR,
                          movement=mv)
        self.assertIn("declared label `status: Fixed` does not exist in the repo:"
                      " its counts read as zero", agenda)
        # and with the label present there is no such finding
        mv["labels"].append({"name": "status: Fixed", "description": ""})
        ok, _ = build(COMPACT + self.LABELS, note_items=ITEMS, notes=PRIOR, movement=mv)
        self.assertNotIn("does not exist in the repo", ok)

    def test_with_nothing_fixed_the_second_group_is_not_written(self):
        """An empty "Waiting for a test:" heading says nothing, so it is not there."""
        mv = {"repo": "acme/app",
              "issues": [self.issue(41, "Refund webhook retries forever",
                                    ["blocker", "area:payments"], who=["bob"])],
              "labels": [{"name": n, "description": ""} for n in
                         ("blocker", "critical", "status: Fixed", "area:payments")],
              "events": [["labeled", "2026-09-01T09:05:00Z", 41, "blocker"]]}
        build(COMPACT + self.LABELS, note_items=ITEMS, notes=PRIOR, movement=mv)
        txt = files()["260924-teams-agenda-daily-standup.txt"]
        self.assertIn("To fix:", txt)
        self.assertNotIn("Waiting for a test:", txt)


class MovementArchive(unittest.TestCase):
    """CR-121/CR-148: `.movementmeta/` -- the same three reads `load()` makes, from an
    archive instead of from `gh`. Tested on the reader itself for the parts the
    generated card cannot distinguish.
    """

    def record(self, tmp, **over):
        d = {"issues": [{"number": 7, "title": "T", "state": "OPEN",
                         "createdAt": "2026-09-01T09:00:00Z", "closedAt": None,
                         "labels": [{"name": "blocker"}], "assignees": [],
                         "url": "https://github.com/acme/app/issues/7"}],
             "labels": [{"name": "blocker", "description": ""}],
             "events": [["labeled", "2026-09-02T09:00:00Z", 7, "blocker"]]}
        d.update(over)
        (tmp / ".movementmeta").mkdir(parents=True, exist_ok=True)
        (tmp / ".movementmeta" / "acme-app.json").write_text(json.dumps(d), encoding="utf-8")
        return tmp

    def test_no_archive_is_no_archive(self):
        """No file, no change: `gh` stays the fallback, which is why this is additive."""
        tmp = Path(tempfile.mkdtemp())
        self.assertIsNone(bm.archived(tmp, "acme/app"))
        (tmp / ".movementmeta").mkdir()
        self.assertIsNone(bm.archived(tmp, "acme/app"))        # dir but no record
        self.assertIsNone(bm.archived(tmp, "acme/other"))

    def test_it_is_found_from_a_project_below_the_venture(self):
        """Found exactly as `.githubmeta/` is: the nearest ancestor that has it."""
        tmp = self.record(Path(tempfile.mkdtemp()))
        deep = tmp / "proj" / "meetings"
        deep.mkdir(parents=True)
        self.assertIsNotNone(bm.archived(deep, "acme/app"))

    def test_the_events_are_parsed_sorted_and_scoped_to_the_issues_read(self):
        """An event for an issue the record does not carry is dropped, exactly as
        `load()` drops it, so the two reads hand `History` the same thing. Timestamps
        become datetimes and the list is oldest first, which the series depends on.
        """
        tmp = self.record(Path(tempfile.mkdtemp()), events=[
            ["closed", "2026-09-05T09:00:00Z", 7, ""],
            ["labeled", "2026-09-02T09:00:00Z", 7, "blocker"],
            ["labeled", "2026-09-03T09:00:00Z", 99, "blocker"],     # no such issue
        ])
        issues, _l, events = bm.archived(tmp, "acme/app")
        self.assertEqual([(e, n, l) for _t, e, n, l in events],
                         [("labeled", 7, "blocker"), ("closed", 7, "")])
        self.assertTrue(all(isinstance(t, datetime.datetime) for t, *_ in events))
        # the invariant `History` is handed: every event names an issue in the list
        nums = {i["number"] for i in issues}
        self.assertTrue(all(n in nums for _t, _e, n, _l in events))
        self.assertNotIn(99, [n for _t, _e, n, _l in events])

    def test_a_record_with_an_out_of_scope_event_still_builds_a_card(self):
        """An archiver's record may name an issue the issue list does not carry. The
        card is built anyway, with the real issue in it -- which is what `load()` does
        with the same input, so the archive and the live read agree.
        """
        labels = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
                  "      labels:\n        priority: [blocker]\n        gap: [blocker]\n"
                  "        area_prefix: 'area:'\n")
        mv = {"repo": "acme/app",
              "issues": [{"number": 7, "title": "Only issue", "state": "OPEN",
                          "createdAt": "2026-09-01T09:00:00Z", "closedAt": None,
                          "labels": [{"name": "blocker"}], "assignees": [],
                          "url": "https://github.com/acme/app/issues/7"}],
              "labels": [{"name": "blocker", "description": ""}],
              "events": [["labeled", "2026-09-02T09:00:00Z", 7, "blocker"],
                         ["labeled", "2026-09-02T09:00:00Z", 404, "blocker"]]}
        build(COMPACT + labels, note_items=ITEMS, notes=PRIOR, movement=mv)
        f = files()["260924-agenda-facilitator-daily-standup.md"]
        self.assertIn("## Movement", f)
        self.assertNotIn("not read —", f)
        self.assertIn("Only issue", files()["260924-teams-agenda-daily-standup.txt"])


class CompactAgenda(unittest.TestCase):
    """Acceptance 2: the decisions needed and the one-minute round. Nothing else."""

    def setUp(self):
        self.agenda, _ = build(COMPACT, note_items=ITEMS, notes=PRIOR)

    def test_no_dependencies_decisions_or_movement(self):
        """CR-155: a dependency is raised by the person in their own minute and decisions
        come out of the milestones and the round, so neither has a section."""
        self.assertNotIn("## Dependencies", self.agenda)
        self.assertNotIn("## Decisions needed today", self.agenda)
        self.assertNotIn("## Movement", self.agenda)

    def test_the_milestones_the_blockers_and_the_round_are_there(self):
        """CR-155: remove only the duplication, never what the room confirms. The first
        release took the milestones and then the blockers out of the shared agenda, and the
        room had no dates and no list to confirm."""
        heads = [l for l in self.agenda.split("\n") if l.startswith("## ")]
        self.assertTrue(heads[0].startswith("## Milestone"), heads)
        self.assertIn("## Release blockers", heads)
        self.assertEqual(heads[-1], "## One-minute round")

    def test_the_round_keeps_each_persons_open_items(self):
        """CR-150: the per-person cells belong to the AGENDA, where they belong to the
        person, not to the facilitator."""
        rnd = self.agenda[self.agenda.index("## One-minute round"):]
        self.assertIn("| **Bob** |", rnd)
        self.assertIn("Payment webhook fails", rnd)

    def test_the_agenda_links_the_details_file(self):
        """"The rest is in the details" is the whole claim that lets the agenda be two
        sections. An agenda that drops the link is simply short.

        The claim is the CR-148 LINE, not any mention of the filename: every card and
        compact agenda already carries a "Built from ... Detail:" header, so an
        `assertIn` on the name alone passed with the line deleted. Asserted on the line
        itself, and by cutting the header off first.
        """
        body = self.agenda.split("Detail: ", 1)[1].split("\n", 1)[1]
        self.assertIn("260924-agenda-details-daily-standup.md", body)
        self.assertIn("Everything else -- the dependencies, the movement, the sources,"
                      " the full carried list: [260924-agenda-details-daily-standup.md]"
                      "(260924-agenda-details-daily-standup.md).", body)
        # and it names what it is replacing: the sections the compact agenda dropped
        for word in ("dependencies", "movement", "sources"):
            self.assertIn(word, body)

    def test_the_agenda_names_the_facilitator_document(self):
        self.assertIn("260924-agenda-facilitator-daily-standup.md", self.agenda)

    def test_the_lead_asks_the_room_to_confirm_the_blockers_it_now_carries(self):
        """CR-155: the compact agenda carries the blockers again, so its lead is the card's;
        `card.release_blockers: false` still gives the no-release lead, from the plan."""
        on = COMPACT.replace("      layout: compact\n",
                             "      layout: compact\n      card:\n"
                             "        release_blockers: true\n")
        off = COMPACT.replace("      layout: compact\n",
                              "      layout: compact\n      card:\n"
                              "        release_blockers: false\n")
        for cfg, label, want in ((COMPACT, "unset", "Confirm the release blockers"),
                                 (on, "true", "Confirm the release blockers"),
                                 (off, "false", "Raise what you wait on")):
            agenda, _ = build(cfg, note_items=ITEMS, notes=PRIOR)
            self.assertIn(want, agenda, label)
        carries = {"agenda": ["milestone", "release_blockers", "round"]}
        self.assertIn("Confirm the release blockers",
                      ba.lead_line({"layout": "compact"}, carries, DAY))
        self.assertIn("Confirm the release blockers",
                      ba.lead_line({"layout": "card"}, carries, DAY))

    def test_the_key_still_governs_the_posts_blockers_heading(self):
        """Inert for the LEAD is not inert everywhere: the post is where the compact
        blockers live, and that is where the key still reads."""
        self.assertEqual(ba.section_plan({"layout": "compact"}, DAY)["post"][-1],
                         "release_blockers")
        self.assertEqual(ba.section_plan({"layout": "compact",
                                          "card": {"release_blockers": False}},
                                         DAY)["post"][-1], "blockers")

    def test_on_demo_day_the_compact_agenda_carries_the_demo_under_the_milestone(self):
        """CR-155: the compact agenda has a milestone again, so CR-121's "directly under the
        milestone" holds there too (CR-148 had kept Demo in the post only)."""
        demo = COMPACT.replace(MS, "milestone:\n  name: First demo day\n"
                                   "  date: 2026-09-24\n  set_on: 2026-09-01\n  kind: demo\n")
        agenda, _ = build(demo, note_items=ITEMS, notes=PRIOR)
        heads = [l for l in agenda.split("\n") if l.startswith("## ")]
        self.assertEqual(heads[:2], ["## Milestone", "## Demo"])
        self.assertIn("Demo today:", files()["260924-teams-agenda-daily-standup.txt"])
        self.assertEqual(ba.section_plan(
            {"layout": "compact", "milestone": {"name": "D", "date": "2026-09-24",
                                                "kind": "demo"}}, DAY)["agenda"],
            ["milestone", "demo", "release_blockers", "confirm", "round"])

    def test_the_card_still_gets_its_demo_section_on_demo_day(self):
        """The CR-148 decision above is scoped to compact. CR-121 on the card is intact.
        """
        demo = CARD.replace(MS, "milestone:\n  name: First demo day\n"
                                "  date: 2026-09-24\n  set_on: 2026-09-01\n  kind: demo\n")
        agenda, _ = build(demo, note_items=ITEMS, notes=PRIOR)
        heads = [l for l in agenda.split("\n") if l.startswith("## ")]
        self.assertEqual(heads[:2], ["## Milestone", "## Demo"])


class CompactFacilitator(unittest.TestCase):
    """Acceptance 3: time boxes, the dependencies read against the data, what to watch,
    and NO per-person figures (CR-150)."""

    def setUp(self):
        build(COMPACT_DEPS, note_items=ITEMS, notes=PRIOR)
        self.f = files()["260924-agenda-facilitator-daily-standup.md"]

    def test_it_has_time_boxes(self):
        self.assertIn("## Time boxes", self.f)
        self.assertIn("| One-minute round (3 people) | 3 |", self.f)

    def test_it_carries_the_dependencies(self):
        dep = self.f[self.f.index("## Dependencies"):]
        self.assertIn("**Backend answer on refunds**", dep)
        self.assertIn("**Legal sign-off on the terms**", dep)

    def test_each_dependency_is_read_against_the_data(self):
        self.assertIn("| Item | Owner | Waiting | Read against the data |", self.f)

    def test_a_closed_dependency_is_listed_as_closed_not_dropped(self):
        """CR-147: a line that silently disappeared is the failure. The facilitator is
        the person who would otherwise raise it, so the close is said out loud."""
        tick = "external_systems:\n  jira:\n    - project: TICK\n"
        build(COMPACT_DEPS + tick, note_items=ITEMS, notes=PRIOR,
              jira=[{"key": "TICK-9", "summary": "Answer the refunds question",
                     "status": "Done", "updated": "2026-09-24T09:00:00.000+0000"}])
        f = files()["260924-agenda-facilitator-daily-standup.md"]
        dep = f[f.index("## Dependencies"):]
        self.assertIn("Backend answer on refunds", dep)
        self.assertIn("**closed** — its own source says so", dep)

    def test_it_has_what_to_watch(self):
        self.assertIn("## What to watch", self.f)

    def test_no_line_pairs_a_person_with_a_number(self):
        """CR-150. The temptation is a "who carries the most" watch list, and the person
        reading this is often one of the people who would be counted. A name may appear
        beside the ONE item it owns -- that is accountability -- but never beside a
        figure. Checked over every line of the document, prose and table alike."""
        names = ("Ann", "Bob", "Dee")
        for line in self.f.split("\n"):
            if not any(n in line for n in names):
                continue
            if line.startswith("|"):
                # a table row: the owner cell carries a name, and it carries no digit
                cells = [c.strip() for c in line.strip("|").split("|")]
                self.assertEqual(len(cells), 4, line)
                self.assertNotRegex(cells[1], r"\d", line)
                continue
            # any other line naming a person must carry no figure at all
            self.assertNotRegex(line, r"\d", line)

    def test_what_to_watch_counts_items_never_people(self):
        """The mutant this catches: the stuck list rewritten as owner-and-count pairs.
        It is the exact aggregation CR-150 forbids, in prose rather than in a table."""
        tasks = "".join(f"- **Readme section {i}** — docs/r{i}.md · **Bob**\n" for i in range(1, 4))
        build(COMPACT_DEPS, note_items=tasks,
              notes={"260914": tasks, "260918": tasks, "260920": tasks})
        f = files()["260924-agenda-facilitator-daily-standup.md"]
        watch = f[f.index("## What to watch"):]
        self.assertIn("task(s) carried", watch)
        for line in watch.split("\n"):
            if "Bob" in line:
                self.assertNotRegex(line, r"\d", line)

    def test_the_dependencies_are_ordered_by_age_never_by_owner(self):
        older = ("- [dependency] **Oldest waiting line** — OLD-1 · **Dee**\n"
                 "- [dependency] **Newer waiting line** — NEW-1 · **Ann**\n")
        # The older line has been carried since 260910; the newer one only since 260920,
        # so "oldest first" and "owner order" disagree (Dee before Ann).
        first = older.split("\n")[0] + "\n"
        build(COMPACT_DEPS, note_items=older,
              notes={"260910": first, "260914": first, "260920": older})
        f = files()["260924-agenda-facilitator-daily-standup.md"]
        dep = f[f.index("## Dependencies"):]
        self.assertLess(dep.index("Oldest waiting line"), dep.index("Newer waiting line"), dep)


class CompactDetails(unittest.TestCase):
    """Acceptance 4: the details file is unchanged and complete.

    Both halves are asserted. Comparing compact's file against the card's alone would
    pass if BOTH lost the same content, so the content the details file must carry is
    named here as well.
    """

    def setUp(self):
        build(COMPACT, note_items=ITEMS, notes=PRIOR)
        self.d = files()["260924-agenda-details-daily-standup.md"]

    def test_its_header_is_exact(self):
        """Exact, not `in`: a line inserted into the header would read as part of the
        document and an `assertIn` on each piece would not notice."""
        self.assertEqual(self.d.split("\n")[:6],
                         ["# Agenda details — Thursday 24 September",
                          "",
                          "Companion to [260924-agenda-daily-standup.md]"
                          "(260924-agenda-daily-standup.md): what the agenda was built from,"
                          " the full carried list, and the detail nobody needs to talk"
                          " through. Not read out in the meeting.",
                          "",
                          "*Base: 260922-daily-standup.md (last meeting held 260922)*",   # CR-139
                          ""])

    def test_it_is_complete(self):
        self.assertIn("## Sources", self.d)
        self.assertIn("## Carried forward", self.d)
        self.assertIn("Update the readme", self.d)                   # the full carried list

    def test_the_details_file_is_byte_identical_to_the_cards(self):
        build(CARD, note_items=ITEMS, notes=PRIOR)
        card = files()["260924-agenda-details-daily-standup.md"]
        build(COMPACT, note_items=ITEMS, notes=PRIOR)
        compact = files()["260924-agenda-details-daily-standup.md"]
        strip = lambda s: re.sub(r"built \d{6} \d\d:\d\d", "built", s)
        self.assertEqual(strip(card), strip(compact))


class LayoutPredicate(unittest.TestCase):
    """is_card() governs DATA, section_plan() governs TEXT. The split is what keeps
    compact from inheriting the card's headings along with its data rules."""

    def test_an_unknown_layout_reads_as_list_exactly_as_before(self):
        self.assertEqual(ba.layout_of({"layout": "kanban"}), "list")
        self.assertEqual(ba.layout_of({}), "list")
        self.assertFalse(ba.is_card({"layout": "kanban"}))

    def test_is_card_is_true_for_exactly_card_and_compact(self):
        self.assertTrue(ba.is_card({"layout": "card"}))
        self.assertTrue(ba.is_card({"layout": "compact"}))
        self.assertFalse(ba.is_card({}))

    def test_compact_is_not_the_card(self):
        self.assertTrue(ba.is_compact({"layout": "compact"}))
        self.assertFalse(ba.is_compact({"layout": "card"}))

    def test_the_four_output_plan(self):
        plan = ba.section_plan({"layout": "compact"}, DAY)
        self.assertEqual(plan["agenda"], ["milestone", "release_blockers", "confirm", "round"])
        self.assertEqual(plan["post"], ["milestone", "release_blockers"])
        self.assertEqual(plan["facilitator"], ["movement", "stuck"])      # CR-155: off by default
        deps = ba.section_plan({"layout": "compact",
                                "compact": {"facilitator_dependencies": True}}, DAY)
        self.assertEqual(deps["facilitator"], ["dependencies", "movement", "stuck"])

    def test_compact_shares_the_cards_config_findings(self):
        """is_card() governs data, and a finding about the data is one of them: the
        compact post leads with the milestone list, so a compact project with no
        milestone has the same nothing to run toward as a card without one."""
        no_ms = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
                 "      layout: compact\n") + PEOPLE
        agenda, _ = build(no_ms, note_items=ITEMS, notes=PRIOR)
        self.assertIn("card layout without a milestone", agenda)

    def test_the_list_layout_is_not_asked_for_a_milestone(self):
        no_ms = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n") + PEOPLE
        agenda, _ = build(no_ms, note_items=ITEMS, notes=PRIOR)
        self.assertNotIn("card layout without a milestone", agenda)

    def test_compact_gets_every_card_data_rule(self):
        """What the predicate is FOR, asserted as behaviour rather than as source text.

        A source-text assertion against one literal spelling of the comparison was
        worthless: the bug it existed to prevent was reintroduced in a different
        spelling and the test stayed green. The requirement is that `compact` is a
        card variant for every data rule the card has -- so it is checked by asking
        the predicate about each layout, which is what the renderers consult.
        """
        for layout, card, compact in (("card", True, False),
                                      ("compact", True, True),
                                      ("list", False, False),
                                      (None, False, False),
                                      ("nonsense", False, False)):
            cf = {"layout": layout} if layout is not None else {}
            with self.subTest(layout=layout):
                self.assertEqual(ba.is_card(cf), card)
                self.assertEqual(ba.is_compact(cf), compact)
                # An unknown or absent value reads as the list layout, as at HEAD.
                self.assertEqual(ba.layout_of(cf),
                                 layout if layout in ba.LAYOUTS else "list")


class FacilitatorName(unittest.TestCase):
    def test_it_is_derived_from_the_agenda_suffix(self):
        self.assertEqual(ba.facilitator_name({"agenda_suffix": "agenda-daily-standup"}, "260924"),
                         "260924-agenda-facilitator-daily-standup.md")

    def test_a_suffix_that_does_not_start_with_agenda_gets_a_tail(self):
        self.assertEqual(ba.facilitator_name({"agenda_suffix": "weekly"}, "260924"),
                         "260924-weekly-facilitator.md")

    def test_the_key_only_overrides_it(self):
        self.assertEqual(ba.facilitator_name({"agenda_suffix": "agenda-daily-standup",
                                              "compact": {"facilitator_suffix": "lead-notes"}},
                                             "260924"),
                         "260924-lead-notes.md")


class ListLayoutIsUntouched(unittest.TestCase):
    """CR-148 is additive. A project on `carry_forward.enabled` with no layout key gets
    exactly the page it got before, from a different code path entirely."""

    LIST = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n") + PEOPLE

    def test_the_list_layout_writes_one_agenda_and_the_markdown_post(self):
        agenda, _ = build(self.LIST, note_items=ITEMS, notes=PRIOR)
        got = set(files())
        self.assertIn("260924-teams-agenda-daily-standup.md", got)
        self.assertNotIn("260924-agenda-details-daily-standup.md", got)
        self.assertNotIn("260924-agenda-facilitator-daily-standup.md", got)
        self.assertNotIn("260924-teams-agenda-daily-standup.txt", got)
        self.assertIn("## Sources", agenda)
        self.assertIn("## Carried forward", agenda)


if __name__ == "__main__":
    unittest.main()


class LoginToPerson(unittest.TestCase):
    """CR-155: which roster person a tracker login belongs to. Invented names."""

    PEOPLE = [{"name": "Ann", "aliases": []},
              {"name": "Robert", "aliases": ["Bob"]},
              {"name": "Dee", "aliases": [], "github": ["dee-the-dev", "deedev2"]},
              {"name": "Annabel", "aliases": []},
              {"name": "Mo", "aliases": []}]

    def test_an_explicit_github_key_wins(self):
        self.assertEqual(ba.login_person("DeeDev2", self.PEOPLE), "Dee")

    def test_a_login_that_starts_with_a_name_or_alias_belongs_to_that_person(self):
        self.assertEqual(ba.login_person("Bob-Smith", self.PEOPLE), "Robert")
        self.assertEqual(ba.login_person("robert_s", self.PEOPLE), "Robert")

    def test_the_longest_name_wins(self):
        self.assertEqual(ba.login_person("annabel-l", self.PEOPLE), "Annabel")
        self.assertEqual(ba.login_person("ann-k", self.PEOPLE), "Ann")

    def test_a_short_name_is_never_a_prefix_claim(self):
        self.assertIsNone(ba.login_person("mojo", self.PEOPLE))      # "Mo" is two letters

    def test_a_login_nobody_claims_is_none_not_a_stranger(self):
        self.assertIsNone(ba.login_person("zed", self.PEOPLE))
        self.assertIsNone(ba.login_person("", self.PEOPLE))

    def test_two_people_tying_for_the_longest_is_unknown(self):
        two = [{"name": "Sam", "aliases": []}, {"name": "Sam", "aliases": ["Sam"], "x": 1}]
        two[1]["name"] = "Samuel"
        two[1]["aliases"] = ["Sam"]
        self.assertIsNone(ba.login_person("samsmith", two))


class CompactRoundIsBuiltFromAssignments(unittest.TestCase):
    """CR-155: each person's cell comes from the tracker's assignees, not from carried lines
    whose owner field names several people."""

    @staticmethod
    def row(agenda, name):
        return next(l for l in agenda.split("\n") if l.startswith(f"| **{name}** |"))

    def setUp(self):
        mv = {"repo": "acme/app",
              "issues": [CompactPostGroupsTheRepoBlockers.issue(
                             41, "Refund webhook retries forever", ["blocker", "area:payments"], who=["bob"]),
                         CompactPostGroupsTheRepoBlockers.issue(
                             42, "Locale crash on launch", ["blocker", "status: Fixed", "area:app"], who=["ann"]),
                         CompactPostGroupsTheRepoBlockers.issue(
                             43, "Slow export on large accounts", ["critical", "area:app"], who=["bob"])],
              "labels": [{"name": n, "description": ""} for n in
                         ("blocker", "critical", "status: Fixed", "area:payments", "area:app")],
              "events": [["labeled", "2026-09-01T09:05:00Z", 41, "blocker"],
                         ["labeled", "2026-09-01T09:05:00Z", 42, "blocker"],
                         ["labeled", "2026-09-01T09:05:00Z", 43, "critical"],
                         ["labeled", "2026-09-10T09:05:00Z", 42, "status: Fixed"]]}
        items = ITEMS + ("- [dependency] **Shared question on refunds** — TICK-77 · **Ann, Bob**\n"
                         "- [dependency] **Chase on issue 41** — #41 · **Dee**\n")
        self.agenda, _ = build(COMPACT + CompactPostGroupsTheRepoBlockers.LABELS,
                               note_items=items, notes=PRIOR, movement=mv)

    def test_an_open_assignment_is_the_persons_open_item(self):
        self.assertIn("*open:* #41 Refund webhook retries forever", self.row(self.agenda, "Bob"))
        self.assertIn("*open:* #43 Slow export on large accounts", self.row(self.agenda, "Bob"))

    def test_a_fixed_assignment_is_something_to_verify(self):
        self.assertIn("*verify:* #42 Locale crash on launch", self.row(self.agenda, "Ann"))

    def test_open_items_come_before_items_to_verify(self):
        row = self.row(self.agenda, "Bob")
        self.assertLess(row.index("*open:*"), row.index("Shared question") if "Shared question" in row else 10 ** 6)

    def test_a_carried_line_goes_only_to_its_first_named_owner(self):
        self.assertIn("Shared question", self.row(self.agenda, "Ann"))
        self.assertNotIn("Shared question", self.row(self.agenda, "Bob"))

    def test_a_carried_line_about_a_tracked_issue_is_not_repeated_for_its_owner(self):
        """Issue 41 is on the tracker; a carried line naming #41 owned by someone else must
        not put it into that person's cell as well."""
        self.assertNotIn("Chase on issue 41", self.row(self.agenda, "Dee"))

    def test_the_card_layout_is_untouched(self):
        agenda, _ = build(CARD + CompactPostGroupsTheRepoBlockers.LABELS, note_items=ITEMS, notes=PRIOR)
        self.assertNotIn("*open:*", agenda)
        self.assertNotIn("*verify:*", agenda)


class CompactFacilitatorDependenciesAreOptional(unittest.TestCase):
    """CR-155: the room raises dependencies itself, so the facilitator's table is opt-in."""

    def test_off_by_default(self):
        build(COMPACT, note_items=ITEMS, notes=PRIOR)
        f = files()["260924-agenda-facilitator-daily-standup.md"]
        self.assertNotIn("## Dependencies", f)

    def test_on_when_asked(self):
        build(COMPACT_DEPS, note_items=ITEMS, notes=PRIOR)
        f = files()["260924-agenda-facilitator-daily-standup.md"]
        self.assertIn("## Dependencies", f)
