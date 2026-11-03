"""CR-167: the company profile says what it is not.

`/company` said what it is -- structure, no questions, an optional template -- and never
that it is source-backed, so it read as the weaker thing it resembles: a profile written
once from memory. The claim is now stated in the skill and in the opening of its contract.

A claim in a skill file is worth only what the skill does, so these assertions check the
paragraph against the behaviour it describes: sources per facet, a drift check, a gap left
visible, and an owner's answer recorded as a dated source rather than an unmarked fact.

    python3 -m unittest discover -s tests
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills" / "company" / "SKILL.md").read_text(encoding="utf-8")
CONTRACT = (ROOT / "skills" / "company" / "references" / "contract.md").read_text(encoding="utf-8")


def flat(text):
    return " ".join(text.split())


class ThePlacement(unittest.TestCase):
    def test_the_paragraph_follows_open_and_optional(self):
        self.assertIn("**Open and optional.**", SKILL)
        self.assertIn("**Source-backed, not self-described (CR-167).**", SKILL)
        self.assertLess(SKILL.index("**Open and optional.**"),
                        SKILL.index("**Source-backed, not self-described (CR-167).**"))

    def test_it_comes_before_the_subcommands(self):
        self.assertLess(SKILL.index("**Source-backed, not self-described (CR-167).**"),
                        SKILL.index("## Subcommands"))

    def test_the_contract_states_it_in_the_opening_not_in_a_numbered_section(self):
        self.assertIn("source-backed, never self-described", CONTRACT)
        self.assertLess(CONTRACT.index("source-backed, never self-described"),
                        CONTRACT.index("## 1. Where"))

    def test_section_7_is_not_where_the_claim_went(self):
        # Reserved for CR-126 and CR-130; the placement was chosen so the three
        # proposals do not collide.
        start = CONTRACT.index("## 7.")
        nxt = CONTRACT.find("\n## ", start + 4)
        section7 = CONTRACT[start:nxt if nxt != -1 else len(CONTRACT)]
        self.assertNotIn("self-described", section7)


class TheClaimIsTrueOfTheSkill(unittest.TestCase):
    """Each clause of the paragraph, bound to the behaviour it claims."""

    def test_sources_are_recorded_per_facet(self):
        self.assertIn("sources.yaml", SKILL)
        self.assertIn("a fact without a source marker", SKILL.replace("**", ""))

    def test_check_reports_staleness_rather_than_assuming_it_away(self):
        self.assertIn("max_age_days", SKILL)
        self.assertIn("stale", SKILL)

    def test_a_missing_fact_stays_a_visible_gap(self):
        self.assertIn("_Not provided yet._", SKILL)

    def test_an_owners_answer_is_recorded_as_a_dated_source(self):
        # The clause added at the merge gate: where the only source is a person,
        # that is recorded too. The skill has to actually do this.
        self.assertIn("interview:<date>", SKILL)
        self.assertIn("dated `interview:<date>` source", flat(SKILL))

    def test_the_paragraph_makes_no_comparison_to_a_named_product(self):
        para = SKILL[SKILL.index("**Source-backed, not self-described (CR-167).**"):]
        para = para[:para.index("\n\n---")] if "\n\n---" in para else para[:1200]
        for word in ("Anthropic", "OpenAI", "ChatGPT", "Notion", "competitor"):
            self.assertNotIn(word, para)


if __name__ == "__main__":
    unittest.main()
