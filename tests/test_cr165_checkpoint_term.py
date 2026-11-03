"""CR-165: the checkpoint has a name, and the name is in the contract.

The suite's load-bearing idea -- the place where a person decides, because generating
the obvious answer would be confidently wrong in a way the reader could not check --
was declared three times as `manual: true` with a reason and named nowhere, so the
landing page could render only a count and `check-terms.py` had nothing to be
consistent with.

Two of the three phrases the CR proposed to ban are banned. The third, `sign-off`, is
NOT, and that is a finding rather than an omission: it occurs five times in skill prose
in its ordinary meaning (a third party's approval of a document), and the `terms` rule
says a word with a legitimate second meaning is explained in `note` instead of being
banned. These assertions hold that decision in place -- the first one that bans
`sign-off` will fail here and in `check-terms.py` on the same run.

    python3 -m unittest discover -s tests
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
TERMS = {t["id"]: t for t in DOC["terms"]}


def prose_lines(path):
    """Lines outside fenced code with inline code removed -- what check-terms.py reads."""
    fenced = False
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield i, re.sub(r"`[^`]*`", "", line)


class TheEntry(unittest.TestCase):
    def test_the_term_is_declared_in_both_languages(self):
        self.assertIn("checkpoint", TERMS)
        self.assertEqual(TERMS["checkpoint"]["en"], "checkpoint")
        self.assertEqual(TERMS["checkpoint"]["sv"], "kontrollpunkt")

    def test_the_note_names_what_declares_it(self):
        note = TERMS["checkpoint"]["note"]
        self.assertIn("manual: true", note)
        self.assertIn("working_loop", note)

    def test_the_claim_the_avoided_phrases_exist_to_protect(self):
        # Not decoration: the entry is worth its place because the two phrases
        # describe the opposite arrangement -- a gate the finished work passes
        # through, and a person placed inside a machine process.
        note = TERMS["checkpoint"]["note"]
        self.assertIn("IS the work", note)
        self.assertIn("serves the person", note)


class TheWorkingLoopStillDeclaresThem(unittest.TestCase):
    """The term names something; if the something goes away the term is a fiction."""

    def test_every_manual_step_carries_its_reason(self):
        manual = [s for s in DOC["working_loop"] if s.get("manual")]
        self.assertEqual([s["id"] for s in manual], ["facilitate", "recap", "record"])
        for s in manual:
            self.assertTrue(s.get("why_manual"), f"{s['id']} is manual with no reason")


class TheAvoidList(unittest.TestCase):
    def test_the_two_mechanical_phrases_are_banned(self):
        self.assertEqual(sorted(TERMS["checkpoint"]["avoid"]),
                         ["approval step", "human in the loop"])

    def test_sign_off_is_deliberately_not_banned_and_the_note_says_why(self):
        self.assertNotIn("sign-off", TERMS["checkpoint"]["avoid"])
        self.assertIn("sign-off", TERMS["checkpoint"]["note"])

    def test_banning_sign_off_would_break_the_check_on_legitimate_prose(self):
        # The reason, checked against the files rather than asserted: the word is
        # in use in its other meaning. If these uses are ever rewritten, the
        # exclusion can be revisited -- this test is where that conversation starts.
        rx = re.compile(r"(?<![\w-])sign-off(?![\w-])", re.I)
        hits = [f"{p.relative_to(ROOT)}:{n}"
                for p in sorted((ROOT / "skills").rglob("*.md"))
                for n, line in prose_lines(p) if rx.search(line)]
        self.assertGreaterEqual(len(hits), 1,
                                "no legitimate use left: `sign-off` could now be avoided")

    def test_neither_banned_phrase_occurs_in_skill_prose(self):
        for phrase in TERMS["checkpoint"]["avoid"]:
            rx = re.compile(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", re.I)
            for p in sorted((ROOT / "skills").rglob("*.md")):
                for n, line in prose_lines(p):
                    self.assertIsNone(rx.search(line),
                                      f"{p.relative_to(ROOT)}:{n} uses '{phrase}'")


class TheCheckAcceptsIt(unittest.TestCase):
    def test_check_terms_passes_with_the_entry_present(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check-terms.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
