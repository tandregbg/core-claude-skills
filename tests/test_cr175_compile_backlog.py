"""CR-175: the compile backlog is one number, computed once.

CR-020 wrote `last_compiled` so a never-running synthesis loop would be visible, and
`/ops check` class 2 has read it correctly all along -- per folder. On a 133-ledger vault
that means the operator meets the fact once per folder among a thousand other findings
and never sees the total. The instrument was fine; the sentence was missing.

These assertions are about the three properties that make the line worth having: the
arithmetic is in ONE place (so `check`, `status` and `analytics` cannot disagree), NEVER
and STALE are counted apart (a setup gap and a cadence gap have different fixes), and a
file that cannot be read is named rather than dropped or fatal (CR-145, CR-177).

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
SCRIPT = ROOT / "skills" / "insights" / "compile_status.py"


def load():
    spec = importlib.util.spec_from_file_location("compile_status", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ["compile_status.py"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    return mod


CS = load()


def ledger(entries, compiled=None):
    head = "version: 2\n"
    if compiled:
        head += f"last_compiled: '{compiled}'\n"
    head += "insights:\n"
    for i, date in enumerate(entries, 1):
        head += f"- id: {i}\n  type: learning\n  date: '{date}'\n  summary: s{i}\n  status: active\n"
    return head


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.vault = Path(cls._tmp.name)
        plan = {
            # never compiled: no stamp at all
            "never-a": ledger(["260901", "260902", "260903"]),
            "never-b": ledger(["261001"]),
            # stale: compiled, then entries kept arriving
            "stale-a": ledger(["260901", "261015"], compiled="260901"),
            # current: compiled after its newest entry
            "fresh-a": ledger(["260901", "260902"], compiled="261101"),
            "fresh-b": ledger(["260801"], compiled="260805"),
        }
        for name, body in plan.items():
            d = cls.vault / name
            d.mkdir()
            (d / "_insights.yaml").write_text(body, encoding="utf-8")
        # a file outside the loop entirely
        d = cls.vault / "listshaped"
        d.mkdir()
        (d / "_insights.yaml").write_text("- id: 1\n  topic: x\n", encoding="utf-8")
        # a ledger inside a skipped surface must not be counted at all
        d = cls.vault / "live" / ".archive"
        d.mkdir(parents=True)
        (d / "_insights.yaml").write_text(ledger(["260101"]), encoding="utf-8")
        cls.report = CS.scan(cls.vault)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()


class TheCounts(Fixture):
    def test_never_and_stale_are_counted_apart(self):
        # One finding with an `or` in it is what this CR exists to split.
        self.assertEqual(len(self.report["never"]), 2)
        self.assertEqual(len(self.report["stale"]), 1)
        self.assertEqual(len(self.report["current"]), 2)

    def test_the_ledger_and_entry_totals_are_the_corpus(self):
        self.assertEqual(self.report["ledgers"], 5)
        self.assertEqual(self.report["entries"], 9)

    def test_a_skipped_surface_is_not_part_of_the_corpus(self):
        folders = [r["folder"] for k in ("never", "stale", "current") for r in self.report[k]]
        self.assertFalse([f for f in folders if ".archive" in f])

    def test_stale_carries_how_far_behind_it_is(self):
        self.assertEqual(self.report["stale"][0]["behind_days"], 44)

    def test_never_is_ordered_by_what_is_at_stake(self):
        # The largest uncompiled ledger first: the operator reads the top of the list.
        self.assertEqual([r["entries"] for r in self.report["never"]], [3, 1])


class TheLine(Fixture):
    def test_the_line_states_every_number_a_reader_needs(self):
        line = CS.line(self.report)
        for part in ("5 ledgers", "9 entries", "2 never compiled", "1 stale", "2 current"):
            self.assertIn(part, line)

    def test_the_consequence_names_the_entries_at_stake(self):
        why = CS.consequence(self.report)
        self.assertIn("4 entries", why)          # 3 + 1 in the two uncompiled ledgers
        self.assertIn("can become a rule", why)

    def test_there_is_no_consequence_line_when_nothing_is_uncompiled(self):
        clean = dict(self.report, never=[])
        self.assertIsNone(CS.consequence(clean))


class UnreadableIsNamedNotDropped(Fixture):
    def test_the_list_shaped_file_is_reported(self):
        self.assertEqual(len(self.report["unreadable"]), 1)
        self.assertIn("not a mapping", self.report["unreadable"][0]["error"])

    def test_it_is_not_counted_as_a_ledger(self):
        # Outside the loop is worse than stale, and must not inflate "current".
        self.assertEqual(self.report["ledgers"], 5)

    def test_the_scan_completes_despite_it(self):
        self.assertEqual(len(self.report["current"]), 2)


class OneArithmeticForThreeReaders(Fixture):
    """The reason this is a script: `check`, `status` and `analytics` read the same one."""

    def test_the_three_skills_all_point_at_this_script(self):
        for skill in ("ops", "insights", "analytics"):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("compile_status.py", text, skill)

    def test_the_cli_matches_the_library(self):
        r = subprocess.run([sys.executable, str(SCRIPT), str(self.vault), "--json"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(len(d["never"]), len(self.report["never"]))
        self.assertEqual(d["entries"], self.report["entries"])

    def test_quiet_prints_the_line_and_stops(self):
        r = subprocess.run([sys.executable, str(SCRIPT), str(self.vault), "--quiet"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("5 ledgers", r.stdout)
        self.assertNotIn("Never compiled (", r.stdout)

    def test_it_writes_nothing(self):
        before = sorted(p.name for p in (self.vault / "never-a").iterdir())
        subprocess.run([sys.executable, str(SCRIPT), str(self.vault)], capture_output=True)
        self.assertEqual(sorted(p.name for p in (self.vault / "never-a").iterdir()), before)


if __name__ == "__main__":
    unittest.main()
