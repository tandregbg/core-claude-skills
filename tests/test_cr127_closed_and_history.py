"""CR-127: `closed:` on finished tasks and milestone provenance, both report only.
Invented data.

    python3 -m unittest discover -s tests
"""
import datetime
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "ops"))
import build_agenda as ba  # noqa: E402
import hygiene_check as hc  # noqa: E402
import yaml  # noqa: E402

DAY = datetime.date(2026, 10, 1)


class Closed(unittest.TestCase):
    def findings(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "_tasks.yaml").write_text(body, encoding="utf-8")
            return [f["message"] for f in hc.check_tasks(d)]

    def test_finished_without_closing_day_is_counted_with_ids(self):
        msgs = self.findings(
            "tasks:\n"
            "  - {id: 1, task: a, status: completed, closed: 261001}\n"
            "  - {id: 2, task: b, status: completed}\n"
            "  - {id: 3, task: c, status: cancelled}\n"
            "  - {id: 4, task: d, status: completed, completed: 260901}\n"
            "  - {id: 5, task: e, status: pending}\n")
        self.assertEqual(len(msgs), 1)
        self.assertIn("2 finished task(s) with no closing day", msgs[0])
        self.assertIn("2, 3", msgs[0])

    def test_legacy_completed_alias_and_closed_are_clean(self):
        self.assertEqual(self.findings(
            "tasks:\n  - {id: 1, task: a, status: completed, closed: 261001}\n"
            "  - {id: 2, task: b, status: cancelled, completed: 260901}\n"), [])


class Provenance(unittest.TestCase):
    def check(self, ms):
        return ba.config_checks({"milestone": ms, "_root": tempfile.gettempdir()}, [], DAY, None)

    def test_date_without_set_on_is_a_finding(self):
        out = self.check({"name": "Beta", "date": "2027-01-01"})
        self.assertTrue(any("no `set_on`" in o for o in out))

    def test_date_with_set_on_is_clean(self):
        self.assertEqual(self.check({"name": "Beta", "date": "2027-01-01", "set_on": "2026-09-01"}), [])

    def test_history_entry_missing_reason_or_source(self):
        out = self.check({"name": "Beta", "date": "2027-01-01", "set_on": "2026-09-01", "history": [
            {"date": "2026-12-01", "set_on": "2026-08-01", "reason": "moved", "source": "a.md"},
            {"date": "2026-12-15", "set_on": "2026-08-15", "reason": "moved"}]})
        self.assertEqual(len(out), 1)
        self.assertIn("entry 2 has no `source`", out[0])

    def test_no_history_behaves_as_before(self):
        self.assertEqual(self.check({"name": "Beta", "set_on": "2026-09-01"}), [])


class Contract(unittest.TestCase):
    def test_contract_declares_the_cr(self):
        eco = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
        self.assertGreaterEqual(eco["contract_version"], 44)
        self.assertEqual(eco["schemas"]["ops_config"], "1.7")
        self.assertEqual(eco["schemas"]["tasks"], 2)


if __name__ == "__main__":
    unittest.main()
