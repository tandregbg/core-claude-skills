"""CR-169: three drop zones, and both of the ageing ones declare their threshold.

The contract declared one drop zone and the vaults used two. `.archive/` against
`.ephemeral/` is stale against junk; `.files/` against `.ephemeral/` is destined
against undestined, decided at the drop -- and that second distinction was in no
contract, only in one vault's own CLAUDE.md. Deciding at the drop is what makes the
14-day sweep safe: anything allowed to die was declared homeless on arrival.

Both zones had failed in opposite directions on the measured vault, which is what an
uncounted rule does: `.files/` had no ageing rule at all, so nothing in it could ever
be late, while 33 of 44 `.ephemeral/` entries were past the sweep.

    python3 -m unittest discover -s tests
"""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
VC = DOC["vault_conventions"]
CONVENTIONS = {c["id"]: c for c in VC["conventions"]}
ROOTS = {e["path"]: e for e in VC["vault_root"] if isinstance(e, dict) and "path" in e}
OPS = (ROOT / "skills" / "ops" / "SKILL.md").read_text(encoding="utf-8")
INBOX = (ROOT / "skills" / "inbox" / "SKILL.md").read_text(encoding="utf-8")


def flat(text):
    return " ".join(text.split())


class TheConventionNamesThreeDestinations(unittest.TestCase):
    def test_all_three_destinations_are_named(self):
        rule = CONVENTIONS["stale_vs_junk"]["rule"]
        for destination in (".archive/", ".files/", ".ephemeral/"):
            self.assertIn(destination, rule)

    def test_each_destination_carries_the_question_that_routes_to_it(self):
        rule = flat(CONVENTIONS["stale_vs_junk"]["rule"])
        self.assertIn("was it current and is now outdated", rule.lower())
        self.assertIn("has not reached yet", rule)
        self.assertIn("no vault destination", rule)

    def test_the_decision_is_taken_at_the_drop(self):
        # The load-bearing sentence: it is the reason the sweep is safe.
        rule = flat(CONVENTIONS["stale_vs_junk"]["rule"])
        self.assertIn("AT THE DROP", rule)
        self.assertIn("gravity", rule)

    def test_the_level_is_unchanged(self):
        self.assertEqual(CONVENTIONS["stale_vs_junk"]["level"], "standard")


class BothAgeingZonesDeclareTheirThreshold(unittest.TestCase):
    def test_each_zone_declares_stale_after_days(self):
        for path in ("_inbox/.files/", ".ephemeral/"):
            self.assertIn("stale_after_days", ROOTS[path],
                          f"{path} has no declared ageing threshold")
            self.assertEqual(ROOTS[path]["stale_after_days"], 14)

    def test_the_two_thresholds_match_so_they_cannot_drift(self):
        self.assertEqual(ROOTS["_inbox/.files/"]["stale_after_days"],
                         ROOTS[".ephemeral/"]["stale_after_days"])

    def test_the_threshold_is_a_number_a_reader_can_use(self):
        for path in ("_inbox/.files/", ".ephemeral/"):
            self.assertIsInstance(ROOTS[path]["stale_after_days"], int)

    def test_the_files_entry_says_an_undestined_file_does_not_belong(self):
        life = flat(ROOTS["_inbox/.files/"]["lifecycle"])
        self.assertIn("IT AGES", life)
        self.assertIn("no vault destination does not belong here", life.lower())


class TheCheckReportsBothWithDifferentMeanings(unittest.TestCase):
    def test_the_two_meanings_are_distinct_in_the_check(self):
        self.assertIn("a sweep that has not run", flat(OPS))
        self.assertIn("a promise nobody kept", flat(OPS))

    def test_the_mis_filed_drop_is_reportable(self):
        self.assertIn("mis-filed at the drop", flat(OPS))

    def test_the_check_offers_and_never_executes(self):
        # CR-103: report-only. The defect measured was an unreported backlog, not an
        # unexecuted deletion, so a sweep is not the fix.
        self.assertIn("Offer, never execute", OPS)

    def test_the_drop_zone_question_is_asked_where_files_are_classified(self):
        self.assertIn("Ask the drop-zone question first (CR-169)", INBOX)
        self.assertIn("not later by gravity", flat(INBOX))


class TheRetiredCommandIsGone(unittest.TestCase):
    """The contract's own prose named a command retired three releases earlier."""

    def test_the_ephemeral_entry_no_longer_says_ops_sweep(self):
        life = ROOTS[".ephemeral/"]["lifecycle"]
        self.assertIn("/ops check", life)
        self.assertNotIn("/ops sweep flags", life)

    def test_no_convention_or_root_entry_calls_a_retired_command(self):
        # check-terms.py watches skills/ and the README; the contract was unwatched.
        retired = ("/ops sweep", "/ops lint", "/ops brief", "/ops projects",
                   "/outbox archive", "/inbox process", "/tasks show")
        blob = yaml.safe_dump(VC, allow_unicode=True)
        for cmd in retired:
            for line in blob.splitlines():
                if cmd in line and not any(w in line for w in
                                           ("was ", "until", "renamed", "retired", "removed")):
                    self.fail(f"vault_conventions still calls {cmd}: {line.strip()[:120]}")


if __name__ == "__main__":
    unittest.main()
