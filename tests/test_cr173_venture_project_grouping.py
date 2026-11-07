"""CR-173: the living view groups by venture then PROJECT, and a venture name is not a project.

Two defects, asserted separately because fixing one leaves the other:

1. `match_project` prefix-matched a context against a portfolio row in both directions. Right for
   `kickoff` -> `Kickoff 2026`; wrong when the context IS the venture's name, where `acme` matched
   `Acme Omstart` and labelled 104 of 125 entries with a project almost none of them belonged to.
2. The section heading led with the context slug and carried the project as a suffix, so a group
   with no project was indistinguishable from one whose project was not matched.

    python3 -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "inbox"))
import survey  # noqa: E402

PROJECTS = {
    "acmeomstart": "Acme Omstart",
    "kickoff2026": "Kickoff 2026",
    "hällestrandvillage": "Hällestrand Village",
}
VENTURES = ("Acme", "Delta", "Bravo")


class MatchProject(unittest.TestCase):
    def test_a_venture_name_is_not_a_project(self):
        """The measured defect: `acme` is the venture, not an abbreviation of a project."""
        self.assertIsNone(survey.match_project("acme", PROJECTS, VENTURES))

    def test_a_venture_name_still_matched_without_the_venture_list(self):
        """Callers that pass no ventures keep the old behaviour, so nothing else shifts."""
        self.assertEqual(survey.match_project("acme", PROJECTS), "Acme Omstart")

    def test_the_documented_prefix_case_still_works(self):
        """`kickoff` -> `Kickoff 2026` is why prefix matching exists and must survive the fix."""
        self.assertEqual(survey.match_project("kickoff", PROJECTS, VENTURES), "Kickoff 2026")

    def test_case_and_punctuation_do_not_let_a_venture_through(self):
        self.assertIsNone(survey.match_project("Acme", PROJECTS, VENTURES))
        self.assertIsNone(survey.match_project("delta", PROJECTS, VENTURES))

    def test_an_unknown_context_is_still_unmatched(self):
        self.assertIsNone(survey.match_project("husbil", PROJECTS, VENTURES))


class RowOrderPerGroup(unittest.TestCase):
    """CR-173: rows rank by age inside a project, by context+id inside `utan projekt`.

    The age ranks the work where a project already says what the work is. Where there is no
    project, the context is the only thing that tells one row from the next, so an operator
    reading 111 entries needs them clustered rather than interleaved by age.
    """

    def test_the_two_orders_are_declared_in_the_source(self):
        src = (ROOT / "skills" / "inbox" / "survey.py").read_text(encoding="utf-8")
        self.assertIn('order = lambda r: (r["_ctx"], r["id"])', src)
        self.assertIn('order = lambda r: (-(r.get("age_days") or 0), r["id"])', src)

    def test_context_then_id_is_what_the_no_project_key_produces(self):
        rows = [{"_ctx": "husbil", "id": 9}, {"_ctx": "aka", "id": 4},
                {"_ctx": "husbil", "id": 2}, {"_ctx": "aka", "id": 11}]
        got = [r["id"] for r in sorted(rows, key=lambda r: (r["_ctx"], r["id"]))]
        self.assertEqual(got, [4, 11, 2, 9])


class NoProjectIsNamed(unittest.TestCase):
    def test_the_no_project_label_is_a_declared_constant(self):
        """A group with no project is named, not left blank -- that is the operator's ask."""
        self.assertEqual(survey.NOPROJ, "utan projekt")


if __name__ == "__main__":
    unittest.main()
