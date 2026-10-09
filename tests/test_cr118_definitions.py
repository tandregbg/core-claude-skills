"""CR-118: company standards and project definitions, resolved and counted. Invented data."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_agenda as ba  # noqa: E402


class Definitions(unittest.TestCase):
    def setUp(self):
        self.v = Path(tempfile.mkdtemp())
        org = self.v / "acme"
        (org / "ops" / "_standards").mkdir(parents=True)
        (org / "_ops.yaml").write_text("standards: ops/_standards\n", encoding="utf-8")
        self.p = org / "_projects" / "app"
        (self.p / "meetings").mkdir(parents=True)
        (self.p / "_ops.yaml").write_text(
            "definitions: terms.md\nworkflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n",
            encoding="utf-8")
        (self.p / "terms.md").write_text(
            "| Term | Status |\n|---|---|\n| **Lane** | **local** |\n| **Gate** | proposed upward |\n| **Odd** | |\n\n"
            "| Role | Who |\n|---|---|\n| **Lead** | Ann |\n", encoding="utf-8")

    def test_resolves_both_levels_and_counts_only_status_tables(self):
        cf = ba.config(self.p / "meetings")
        d = ba.definitions(cf)
        self.assertTrue(str(d["standards"]).endswith("ops/_standards"))
        self.assertEqual(d["definitions"].name, "terms.md")
        self.assertEqual((d["local"], d["upward"], d["unmarked"]), (1, 1, 1))

    def test_nothing_declared(self):
        cf = {"_root": self.v}
        d = ba.definitions(cf)
        self.assertIsNone(d["definitions"]); self.assertIsNone(d["standards"])


if __name__ == "__main__":
    unittest.main()
