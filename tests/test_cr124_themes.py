"""CR-124: the themes registry, checked in three directions; quarters by original date.

    python3 -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "ops"))
import themes  # noqa: E402
import hygiene_check as hc  # noqa: E402


def build(tmp, enabled=True):
    p = Path(tmp) / "acme-podcast"
    (p / "episodes").mkdir(parents=True)
    (p / "_ops.yaml").write_text(yaml.safe_dump({"profile": "podcast", "themes": {"enabled": enabled}}),
                                 encoding="utf-8")
    (p / "episodes" / "260103-episode-guest-hiring.md").write_text(
        "# Hiring\n\n**Themes:** T01 (primary), T02\n**Originally published:** 2024-11-20\n", encoding="utf-8")
    (p / "episodes" / "260210-episode-guest-pricing.md").write_text(
        "# Pricing\n\nThemes: T02 (primary), T01\n", encoding="utf-8")
    reg = {"schema": 1, "next_id": 3, "themes": [
        {"id": "T01", "name": "Early hiring", "status": "active",
         "units": [{"source": "260103-episode-guest-hiring.md", "role": "primary"},
                   {"source": "260210-episode-guest-pricing.md", "role": "secondary"}],
         "insight_ids": [1]},
        {"id": "T02", "name": "Pricing", "status": "active",
         "units": [{"source": "260103-episode-guest-hiring.md", "role": "secondary"},
                   {"source": "260210-episode-guest-pricing.md", "role": "primary"}],
         "insight_ids": [2]}]}
    (p / "_themes.yaml").write_text(yaml.safe_dump(reg, sort_keys=False), encoding="utf-8")
    ins = {"version": 3, "insights": [
        {"id": 1, "type": "claim", "source": "260103-episode-guest-hiring.md", "themes": ["T01"]},
        {"id": 2, "type": "claim", "source": "260210-episode-guest-pricing.md", "themes": ["T02"]}],
        "next_id": 3}
    (p / "_insights.yaml").write_text(yaml.safe_dump(ins, sort_keys=False), encoding="utf-8")
    return p


def edit(path, fn):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


class Checks(unittest.TestCase):
    def test_consistent_project_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(themes.check(build(tmp)), [])

    def test_unknown_theme_on_an_insight(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = build(tmp)
            edit(p / "_insights.yaml", lambda d: d["insights"][0]["themes"].append("T09"))
            msgs = [f["message"] for f in themes.check(p)]
            self.assertTrue(any("T09" in m and "not in" in m for m in msgs), msgs)

    def test_registry_unit_missing_from_summary_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = build(tmp)
            (p / "episodes" / "260210-episode-guest-pricing.md").write_text(
                "Themes: T02 (primary), T03\n", encoding="utf-8")
            found = themes.check(p)
            self.assertTrue(any(f["file"] == "260210-episode-guest-pricing.md" and "T01" in f["message"]
                                for f in found), found)

    def test_insight_ids_two_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = build(tmp)
            edit(p / "_themes.yaml", lambda d: d["themes"][0].update(insight_ids=[]))
            self.assertTrue(any("lacks #1" in f["message"] for f in themes.check(p)))
        with tempfile.TemporaryDirectory() as tmp:
            p = build(tmp)
            edit(p / "_themes.yaml", lambda d: d["themes"][0].update(insight_ids=[1, 2]))
            self.assertTrue(any("#2 is in T01" in f["message"] for f in themes.check(p)))

    def test_three_primary_themes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = build(tmp)
            (p / "episodes" / "260103-episode-guest-hiring.md").write_text(
                "Themes: T01 (primary), T02 (primary), T03 (primary)\n", encoding="utf-8")
            self.assertTrue(any("3 primary" in f["message"] for f in themes.check(p)))

    def test_disabled_project_runs_no_theme_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = build(tmp, enabled=False)
            edit(p / "_insights.yaml", lambda d: d["insights"][0]["themes"].append("T09"))
            self.assertEqual(hc.check_themes(p), [])


class Quarters(unittest.TestCase):
    def test_original_date_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            q = themes.quarters(build(tmp))
            self.assertEqual(q["T01"], {"2024-Q4": 1, "2026-Q1": 1})


if __name__ == "__main__":
    unittest.main()
