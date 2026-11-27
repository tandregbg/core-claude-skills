"""CR-183: a preparation asks what the user must have thought through, not only what to report.

    python3 -m unittest discover -s tests
"""
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "preparation" / "SKILL.md"


class PreparationAsksWhatTheUserMustDecide(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_the_step_exists_between_step_3_and_step_4(self):
        i3 = self.text.index("### Step 3.5")
        self.assertIn("(CR-183)", self.text[i3:i3 + 120])
        self.assertLess(self.text.index("### Step 3"), i3)
        self.assertLess(i3, self.text.index("### Step 4"))

    def test_the_position_comes_before_the_material(self):
        step = self.text[self.text.index("### Step 3.5"):self.text.index("### Step 4")]
        self.assertIn("**before** what was delivered", step)
        self.assertIn("Distinguish pitching from opening a door", step)
        self.assertIn("previous preparations for the same contact", step)


if __name__ == "__main__":
    unittest.main()
