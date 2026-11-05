"""CR-178: `source.step` is an identifier, so the contract declares the values.

The field names WHERE A PROBLEM OCCURRED, not where the entry was written -- 273 of 362
measured entries name Step 1 of `/transcript`, which is parsing and speaker attribution,
and every one of them was written by Step 4.5. It was free text, and it accumulated 120
spellings of a handful of values.

The cost was not untidiness. `/insights compile` Pass 1 is specified to cluster execution
feedback by `skill` + `step`; with 120 values it cannot, so the 261105 run clustered on tag
families instead and the grouping the field exists for was never performed. **A field that
defeats its only reader is worse than an absent one, because it looks like it works.**

Third instance of one shape: CR-049 stated the rule, CR-152 fixed it in the task ledger's
`source.type`, this fixes it in the field next door.

    python3 -m unittest discover -s tests
"""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
STEPS = CONTRACT.get("feedback_steps") or {}


def skill_text(name):
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


class TheContractDeclaresThem(unittest.TestCase):
    def test_the_block_exists_for_the_skills_that_write_feedback(self):
        for skill in ("transcript", "ops"):
            self.assertIn(skill, STEPS, skill)
            self.assertTrue(STEPS[skill])

    def test_every_declared_id_is_a_real_heading_in_that_skill(self):
        # The list is worthless if it names a step the skill does not have.
        for skill in ("transcript", "ops"):
            text = skill_text(skill)
            headings = set(re.findall(r"^#+ Step ([0-9.]+):", text, re.M))
            for sid in STEPS[skill]:
                self.assertIn(str(sid), headings,
                              f"{skill} declares step {sid}, which has no heading")

    def test_the_step_that_writes_the_entry_is_declared_too(self):
        # 4.5 and 9 are where entries are WRITTEN; they are legal values, and the labels
        # say so, because an entry about the feedback step itself has to be expressible.
        self.assertIn("4.5", STEPS["transcript"])
        self.assertIn("9", STEPS["ops"])
        self.assertIn("WRITTEN", STEPS["transcript"]["4.5"])
        self.assertIn("WRITTEN", STEPS["ops"]["9"])

    def test_the_step_where_most_problems_occur_is_declared_with_what_it_does(self):
        self.assertIn("1", STEPS["transcript"])
        label = STEPS["transcript"]["1"].lower()
        self.assertIn("attribution", label)

    def test_ids_are_strings_so_5_5_is_not_a_float(self):
        # 5.4 and 5.5 as YAML floats would collide and reorder; quoting them is the point.
        for skill, steps in STEPS.items():
            for sid in steps:
                self.assertIsInstance(sid, str, f"{skill}:{sid!r}")


class TheIdIsRecoverableSoNothingNeedsRewriting(unittest.TestCase):
    """CR-127's precedent: a legacy spelling is read, never rewritten."""

    SPELLINGS = ["1", "Step 1", "Step 1 -- speaker attribution",
                 "Step 1 (proper-noun verification)", "step 1 / CR-016",
                 "1 (speaker attribution)", "4.5", "Step 5.5"]

    def test_every_observed_spelling_yields_its_id(self):
        for s in self.SPELLINGS:
            m = re.match(r"^(?:step\s*)?(\d+(?:\.\d+)?)", s, re.I)
            self.assertIsNotNone(m, s)
        ids = {re.match(r"^(?:step\s*)?(\d+(?:\.\d+)?)", s, re.I).group(1)
               for s in self.SPELLINGS}
        self.assertEqual(ids, {"1", "4.5", "5.5"})

    def test_a_recovered_id_resolves_against_the_declaration(self):
        for sid in ("1", "4.5"):
            self.assertIn(sid, STEPS["transcript"])
        self.assertIn("5.5", STEPS["ops"])


class TheSkillsSayIt(unittest.TestCase):
    def test_transcript_names_the_declaration_and_the_rule(self):
        t = skill_text("transcript")
        self.assertIn("feedback_steps", t)
        self.assertIn("where the problem occurred", t)
        self.assertIn("in `tags`", t)

    def test_transcript_no_longer_asks_for_a_description(self):
        t = skill_text("transcript")
        self.assertNotIn('step: "step number where it occurred"', t)

    def test_ops_names_it_too(self):
        t = skill_text("ops")
        self.assertIn("feedback_steps", t)
        self.assertIn("read and never rewritten", t)

    def test_both_say_the_id_alone(self):
        for skill in ("transcript", "ops"):
            self.assertIn("step id alone", skill_text(skill), skill)


if __name__ == "__main__":
    unittest.main()
