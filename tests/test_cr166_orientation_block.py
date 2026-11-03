"""CR-166: the orientation entry, and the check that keeps the block from drifting.

CR-077 put `orientation` in the contract under the rule *rendered, never restated*, and
then nothing enforced it: no script referenced `orientation`, so the README block could
drift from the declaration silently -- the exact failure the rule was written to prevent.
`render-loop.py` now renders and checks both README blocks, and resolves each entry's
`sources` against the contract.

The assertions compare the README against the renderer and the renderer against the
contract. None of them compares the renderer with itself.

    python3 -m unittest discover -s tests
"""
import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")
ENTRIES = DOC["orientation"]


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_loop", ROOT / "scripts" / "render-loop.py")
    mod = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["render-loop.py"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    return mod


RL = load_renderer()


def readme_block():
    m = re.search(re.escape(RL.O_START) + r"\n(.*?)" + re.escape(RL.O_END), README, re.S)
    assert m, "README has no orientation block"
    return m.group(1)


class TheEntry(unittest.TestCase):
    def test_the_entry_exists_and_is_asked_first(self):
        self.assertEqual(ENTRIES[0]["id"], "what_it_knows",
                         "the question a person asks before the others is not first")

    def test_the_question_is_in_the_form_a_person_asks_it(self):
        q = ENTRIES[0]["question"]
        self.assertTrue(q.endswith("?"), q)
        self.assertIn("know about me", q)

    def test_the_answer_names_four_things_and_keeps_its_last_sentence(self):
        a = " ".join(ENTRIES[0]["answer"].split())
        self.assertTrue(a.startswith("Four things"), a[:40])
        # The load-bearing sentence: CR-166 says it is the answer to the question
        # behind the question, and must not be cut for length.
        self.assertIn("None of it is a model of you", a)
        self.assertIn("open, correct and delete", a)

    def test_every_entry_still_carries_the_fields_a_renderer_relies_on(self):
        for e in ENTRIES:
            for field in ("id", "question", "answer"):
                self.assertIn(field, e, f"orientation entry {e.get('id', '?')}")


class SourcesResolve(unittest.TestCase):
    """The first verification row of the CR, made mechanical."""

    def test_no_entry_cites_a_declaration_that_does_not_exist(self):
        self.assertEqual(RL.check_sources(DOC), [])

    def test_the_new_entry_cites_the_four_parts_its_answer_names(self):
        self.assertEqual(ENTRIES[0]["sources"],
                         ["vault_conventions", "skills.company", "skills.insights", "components"])

    def test_the_resolver_is_not_vacuous(self):
        import copy
        bad = copy.deepcopy(DOC)
        bad["orientation"][0]["sources"] = ["vault_conventions.nope", "skills.not_a_skill"]
        self.assertEqual(len(RL.check_sources(bad)), 2)


class TheReadmeBlockIsTheDeclaration(unittest.TestCase):
    def test_the_committed_block_is_what_the_renderer_produces(self):
        self.assertEqual(readme_block().strip(),
                         RL.render_orientation(ENTRIES).strip(),
                         "run python3 scripts/render-loop.py --write")

    def test_one_row_per_entry_with_the_question_as_asked(self):
        block = readme_block()
        rows = [l for l in block.splitlines() if l.startswith("| ") and not l.startswith("|---")]
        self.assertEqual(len(rows), len(ENTRIES) + 1)      # + the empty header row
        for e in ENTRIES:
            self.assertIn(" ".join(e["question"].split()), block)

    def test_the_block_still_promises_it_is_generated(self):
        self.assertIn("do not edit here (CR-077)", readme_block())


class TheCheckRuns(unittest.TestCase):
    def test_render_loop_check_passes_on_the_committed_tree(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "render-loop.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("orientation", r.stdout)

    def test_a_hand_edited_block_fails_the_check(self):
        # The whole point of the CR's part 2: a hand edit is caught, not tolerated.
        # Run the renderer's own comparison against a mutated copy of the block.
        mutated = readme_block().replace("Four things", "Three things", 1)
        self.assertNotEqual(mutated.strip(), RL.render_orientation(ENTRIES).strip())

    def test_the_components_check_covers_the_orientation_block(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check-components.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
