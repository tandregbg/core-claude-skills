"""CR-177: one malformed _insights.yaml must not take the whole candidate scan down.

`promotion_candidates.py` is, by CR-100's design, the single arithmetic for promotion --
compile reads it and a review surface reads it, so they cannot drift apart. That makes it a
chokepoint: before this fix, one file in one folder that parsed as a LIST rather than a
mapping raised AttributeError on `doc.get` and stopped the scan for every other folder.

A file that does not parse at all was already handled. A file that parses into the wrong
shape has the same outcome -- this scan cannot use it -- and now gets the same treatment: a
named entry in `unreadable`, and the scan continues. A crash is not a report (CR-145).

    python3 -m unittest discover -s tests
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "insights" / "promotion_candidates.py"


def load():
    spec = importlib.util.spec_from_file_location("promotion_candidates", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["promotion_candidates.py"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    return mod


PC = load()

# A healthy folder with one promotable group: same type, a shared primary tag, three dates.
GOOD = """version: 2
context: acme
next_id: 4
insights:
- id: 1
  type: learning
  date: '260901'
  summary: A measured number needs its basis stated or it is read wrong
  tags: [measurement, reporting]
  status: active
- id: 2
  type: learning
  date: '260902'
  summary: A figure with no cohort cannot be used
  tags: [measurement, cohort]
  status: active
- id: 3
  type: learning
  date: '260903'
  summary: A metric with no trend says nothing on its own
  tags: [measurement, trend]
  status: active
"""

# Parses, but the top level is a list: a hand-written corpus in a foreign schema.
LIST_SHAPED = """- id: 1
  date: 2026-10-15
  topic: verification
  insight: >
    A whole programme was reported with no outcome measure at all.
"""

# Does not parse at all: an unquoted colon inside a plain scalar.
UNPARSEABLE = """version: 2
insights:
- id: 1
  summary: the rule is this: never do that
  tags: [a]
"""


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.vault = Path(cls._tmp.name)
        for name, body in (("good", GOOD), ("listshaped", LIST_SHAPED), ("broken", UNPARSEABLE)):
            d = cls.vault / name
            d.mkdir()
            (d / "_insights.yaml").write_text(body, encoding="utf-8")
        cls.report = PC.scan(cls.vault, 3, None)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def unreadable_for(self, folder):
        return [u for u in self.report["unreadable"] if folder in u["file"]]


class TheScanCompletes(Fixture):
    def test_the_good_folder_still_produces_its_group(self):
        # The whole point: the healthy folder is scanned despite its malformed neighbours.
        groups = self.report["candidate_groups"]
        self.assertEqual(len(groups), 1, groups)
        self.assertEqual(sorted(m["id"] for m in groups[0]["members"]), [1, 2, 3])

    def test_only_the_healthy_folder_counts_as_scanned(self):
        self.assertEqual(self.report["folders_scanned"], 1)


class BothMalformedShapesAreReported(Fixture):
    def test_the_list_shaped_file_is_named_with_its_type(self):
        hits = self.unreadable_for("listshaped")
        self.assertEqual(len(hits), 1, self.report["unreadable"])
        self.assertIn("not a mapping", hits[0]["error"])
        self.assertIn("list", hits[0]["error"])

    def test_the_unparseable_file_keeps_its_existing_handling(self):
        hits = self.unreadable_for("broken")
        self.assertEqual(len(hits), 1, self.report["unreadable"])
        self.assertIn("Error", hits[0]["error"])

    def test_neither_is_silently_dropped(self):
        self.assertEqual(len(self.report["unreadable"]), 2)


class TheCliSurvivesIt(Fixture):
    def test_json_output_parses_and_carries_both(self):
        r = subprocess.run([sys.executable, str(SCRIPT), str(self.vault)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(len(d["unreadable"]), 2)


if __name__ == "__main__":
    unittest.main()
