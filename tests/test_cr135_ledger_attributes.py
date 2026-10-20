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

    def test_objekttyp_is_case_insensitive_and_names_the_declared_form(self):
        tmp, d = vault("tasks: []\n")
        with tmp:
            vocab = ta.load(d)
            self.assertEqual(ta.validate({"objekttyp": "uppgift"}, vocab), [])
            r = ta.validate({"objekttyp": "löpande ansvar"}, vocab)
            self.assertEqual(len(r), 1)
            self.assertIn("Löpande ansvar is filed as a task", r[0][2])

    def test_non_string_values_are_a_type_finding(self):
        tmp, d = vault("tasks: []\n")
        with tmp:
            vocab = ta.load(d)
            r = ta.validate({"verksamhet": ["Acme"], "projekt": 7, "objekttyp": {"a": 1}}, vocab)
            self.assertEqual([x[0] for x in r], ["verksamhet", "projekt", "objekttyp"])
            self.assertTrue(all("must be a string" in x[2] for x in r))

    def test_swedish_letters_and_middle_dot_values(self):
        pf = PORTFOLIO + ""
        pf = pf.replace("| Bravo Tooling |", "| └ Ål |  projekt | Åre·Bolag | aktiv | Ravi | m1 | |\n| Bravo Tooling |", 1)
        tmp, d = vault("tasks: []\n", vocab="verksamhet: [Åre·Bolag, Ödla, Acme]\n", portfolio=pf)
        with tmp:
            vocab = ta.load(d)
            self.assertEqual(ta.validate({"verksamhet": "Åre·Bolag", "projekt": "Ål"}, vocab), [])
            self.assertEqual(ta.validate({"verksamhet": "Ödla"}, vocab), [])
            self.assertEqual(len(ta.validate({"verksamhet": "Odla"}, vocab)), 1)

    def test_short_project_name_matches_itself_not_as_a_prefix(self):
        projects = {"ål": "Ål", "goa2026": "Goa 2026"}
        self.assertEqual(ta.survey.match_project("Ål", projects), "Ål")
        self.assertIsNone(ta.survey.match_project("Å", projects))
        self.assertIsNone(ta.survey.match_project("go", projects))
        self.assertEqual(ta.survey.match_project("goa", projects), "Goa 2026")

    def test_ledger_mixing_old_and_new_entries(self):
        m = msgs("tasks:\n"
                 "  - {id: 1, task: old, status: pending, context: legacy text}\n"
                 "  - {id: 2, task: new, status: pending, verksamhet: Acme, projekt: Acme Launch, objekttyp: Uppgift}\n"
                 "  - {id: 3, task: bad, status: pending, verksamhet: Nowhere}\n"
                 "  - {id: 4, task: new, status: pending, projekt: Bravo}\n")
        self.assertEqual(len(m), 1)
        self.assertIn("'Nowhere'", m[0])

    def test_skill_makes_validation_a_precondition_of_writing(self):
        t = (ROOT / "skills" / "tasks" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("do not write the entry if it exits 1", t)


if __name__ == "__main__":
    unittest.main()
