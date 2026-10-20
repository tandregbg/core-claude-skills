"""CR-135: the ledger's `verksamhet:`, `projekt:`, `objekttyp:` against a declared vocabulary.
Report only; absent fields are never findings. Invented data.

    python3 -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "ops"))
sys.path.insert(0, str(ROOT / "skills" / "tasks"))
import hygiene_check as hc  # noqa: E402
import task_attributes as ta  # noqa: E402
import yaml  # noqa: E402

PORTFOLIO = (
    "# Projects\n\n## PORTFÖLJEN\n\n"
    "| Projekt | Typ | Verksamhet | Status | Sponsor | Maskin | Not |\n"
    "|---|---|---|---|---|---|---|\n"
    "| Acme Launch 2026 | projekt | Acme | aktiv | Bob | m1 | |\n"
    "| Bravo Tooling | löpande | Bravo | aktiv | Ravi | m1 | |\n"
    "\n### Sammanräkning\n")


def vault(tasks, vocab="verksamhet: [Acme, Bravo, Personal]\n", portfolio=PORTFOLIO):
    tmp = tempfile.TemporaryDirectory()
    d = Path(tmp.name)
    if vocab is not None:
        (d / "_config").mkdir()
        (d / "_config" / "task-attributes.yaml").write_text(vocab, encoding="utf-8")
    if portfolio is not None:
        (d / "_INDEX-projekt.md").write_text(portfolio, encoding="utf-8")
    (d / "acme").mkdir()
    (d / "acme" / "_tasks.yaml").write_text(tasks, encoding="utf-8")
    return tmp, d


def msgs(tasks, **kw):
    tmp, d = vault(tasks, **kw)
    with tmp:
        return [f["message"] for f in hc.check_tasks(d)]


class Attributes(unittest.TestCase):
    def test_absent_fields_are_never_findings(self):
        m = msgs("tasks:\n  - {id: 1, task: a, status: pending}\n"
                 "  - {id: 2, task: b, status: pending, context: uppföljning}\n")
        self.assertEqual(m, [])

    def test_declared_venture_is_clean_undeclared_is_grouped(self):
        m = msgs("tasks:\n"
                 "  - {id: 1, task: a, status: pending, verksamhet: Acme}\n"
                 "  - {id: 2, task: b, status: pending, verksamhet: 'Acme?'}\n"
                 "  - {id: 3, task: c, status: pending, verksamhet: 'Acme?'}\n")
        self.assertEqual(len(m), 1)
        self.assertIn("'Acme?'", m[0])
        self.assertIn("2 task(s): 2, 3", m[0])

    def test_projekt_matches_by_prefix_and_flags_the_unknown(self):
        m = msgs("tasks:\n"
                 "  - {id: 1, task: a, status: pending, projekt: acme launch}\n"
                 "  - {id: 2, task: b, status: pending, projekt: Bravo}\n"
                 "  - {id: 3, task: c, status: pending, projekt: Delta Mapping}\n")
        self.assertEqual(len(m), 1)
        self.assertIn("'Delta Mapping' matches no row", m[0])

    def test_portfolio_row_with_no_entries_is_reported_over_the_whole_vault(self):
        m = msgs("tasks:\n  - {id: 1, task: a, status: pending, projekt: Acme Launch}\n")
        self.assertEqual(len(m), 1)
        self.assertIn("portfolio row 'Bravo Tooling' has no ledger entries", m[0])

    def test_no_unused_rows_before_any_entry_names_a_project(self):
        self.assertEqual(msgs("tasks:\n  - {id: 1, task: a, status: pending}\n"), [])

    def test_objekttyp_other_than_task_is_a_move_candidate(self):
        m = msgs("tasks:\n"
                 "  - {id: 1, task: a, status: pending, objekttyp: Löpande ansvar}\n"
                 "  - {id: 2, task: b, status: pending, objekttyp: Uppgift}\n"
                 "  - {id: 3, task: c, status: pending, objekttyp: Gadget}\n")
        self.assertEqual(len(m), 2)
        self.assertTrue(any("Löpande ansvar is filed as a task" in x for x in m))
        self.assertTrue(any("'Gadget' is not one of" in x for x in m))

    def test_a_vault_declaring_nothing_gets_no_vocabulary_findings(self):
        m = msgs("tasks:\n  - {id: 1, task: a, status: pending, verksamhet: Whatever, projekt: Nothing}\n",
                 vocab=None, portfolio=None)
        self.assertEqual(m, [])

    def test_staging_validation_refuses_before_writing(self):
        tmp, d = vault("tasks: []\n")
        with tmp:
            vocab = ta.load(d)
            self.assertEqual(ta.validate({"verksamhet": "Bravo", "projekt": "Bravo Tooling"}, vocab), [])
            self.assertEqual(len(ta.validate({"verksamhet": "Nowhere"}, vocab)), 1)
            self.assertEqual(ta.main(["--validate", '{"verksamhet": "Nowhere"}', "--root", str(d)]), 1)
            self.assertEqual(ta.main(["--validate", '{"verksamhet": "Acme"}', "--root", str(d)]), 0)

    def test_objekttyp_enum_is_declared_in_the_contract(self):
        eco = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
        self.assertEqual(tuple(eco["task_attributes"]["objekttyp"]), ta.DEFAULT_OBJEKTTYP)
        self.assertEqual(len(ta.DEFAULT_OBJEKTTYP), 7)


if __name__ == "__main__":
    unittest.main()
