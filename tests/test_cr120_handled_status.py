"""CR-120: `hanterad` is a declared status for material worked from but never sent, and
`Destination` says where the folder goes home. Invented data."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "outbox"))
import resolved as rv  # noqa: E402


class DeclaredForm(unittest.TestCase):
    def test_hanterad_is_declared(self):
        self.assertIn("handled", rv.DECLARED_STATUS)
        self.assertEqual(rv.DECLARED_STATUS["handled"], ["hanterad"])

    def test_canonical_word(self):
        self.assertEqual(rv.CANONICAL["handled"], "hanterad")

    def test_every_logical_name_has_a_canonical_word(self):
        self.assertEqual(set(rv.DECLARED_STATUS), set(rv.CANONICAL))

    def test_synonyms_resolve_to_handled(self):
        for word in ("hanterat", "behandlad", "använd", "förbrukad"):
            self.assertEqual(rv.SYNONYMS[word], "handled", word)

    def test_handled_is_not_confused_with_withdrawn(self):
        """The distinction is the whole point: withdrawn records a decision NOT to send."""
        self.assertNotEqual(rv.CANONICAL["handled"], rv.CANONICAL["withdrawn"])


class Vocabularies(unittest.TestCase):
    """ecosystem.yaml and resolved.py both declare the forms; they must agree."""

    def test_ecosystem_declares_the_same_forms(self):
        import yaml
        eco = yaml.safe_load((Path(__file__).resolve().parent.parent / "ecosystem.yaml").read_text(encoding="utf-8"))
        forms = None
        def walk(n):
            nonlocal forms
            if isinstance(n, dict):
                if "status_forms" in n:
                    forms = n["status_forms"]
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for v in n:
                    walk(v)
        walk(eco)
        self.assertIsNotNone(forms, "status_forms not found in ecosystem.yaml")
        self.assertEqual(set(forms), set(rv.DECLARED_STATUS),
                         "ecosystem.yaml and resolved.py declare different status forms")
        self.assertTrue(forms["handled"][0].startswith("hanterad"))


class LinkNormalisation(unittest.TestCase):
    """The drift check compares content, not bytes: a staged copy points relatively from
    _outbox/, its source from its own folder. 5 of 6 observed differences were this."""

    @staticmethod
    def strip_links(text):
        import re
        return re.sub(r"\]\([^)]*\)", "]()", text)

    def test_link_only_difference_is_not_drift(self):
        src = "See [the note](261008-summary.md) and [strategy](CAI-strategy.md).\n"
        staged = ("See [the note](../../_contacts/cai-nilsson/261008-summary.md) and "
                  "[strategy](../../_contacts/cai-nilsson/CAI-strategy.md).\n")
        self.assertNotEqual(src, staged)
        self.assertEqual(self.strip_links(src), self.strip_links(staged))

    def test_real_content_drift_survives_normalisation(self):
        src = "## 1. Verification status -- **ACME-9462, building**\n"
        staged = "## 1. Verification status\n"
        self.assertNotEqual(self.strip_links(src), self.strip_links(staged))


if __name__ == "__main__":
    unittest.main()
