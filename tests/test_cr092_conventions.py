"""CR-092: the contract's conventions are `conventions`, and their middle level is `standard`.

    python3 -m unittest discover -s tests

`rule` belongs to the insight lifecycle (CR-089). The component check refuses the old key
and the old level in this repo's contract; these tests pin that, and the counts the landing
page renders from it.
"""
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class Conventions(unittest.TestCase):
    def setUp(self):
        self.doc = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))

    def test_key_is_conventions(self):
        vc = self.doc["vault_conventions"]
        self.assertIn("conventions", vc)
        self.assertNotIn("rules", vc)

    def test_levels(self):
        levels = {c["level"] for c in self.doc["vault_conventions"]["conventions"]}
        self.assertEqual(levels - {"invariant", "standard", "guideline"}, set())
        self.assertIn("standard", levels)

    def test_standard_is_a_term(self):
        self.assertIn("standard", {t["id"] for t in self.doc["terms"]})

    def test_component_check_passes(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check-components.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
