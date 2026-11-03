"""CR-171: a vault's file names are data to the suite, and a check keeps them out of it.

Two halves. The grandfather clause in `system_file_language` recorded its REASON as an
enumerated list -- five Swedish register names -- when the reason is a test: is the name
read by a script, and does renaming cost more than the consistency gains? A list goes
stale where the test would not, and on one vault four more files met the test and were
named in no list, so a reader comparing vault against contract found four violations that
were not violations.

The sharper half: two vault-local display filenames had leaked into the suite as literals
-- a triage document in a skip-list in code, a generated view asserted as contract text in
a test -- which is exactly what `identifier_language` has forbidden since CR-049. They
arrived AFTER that rule shipped, which is the argument for a check rather than another
sentence. The check is the part worth more than the entry.

    python3 -m unittest discover -s tests
"""
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
CONVENTIONS = {c["id"]: c for c in DOC["vault_conventions"]["conventions"]}
BASE = yaml.safe_load((ROOT / "skills" / "ops-config" / "base.yaml").read_text(encoding="utf-8"))
CHECK = ROOT / "scripts" / "check-terms.py"

sys.path.insert(0, str(ROOT / "skills" / "inbox"))
import survey as sv  # noqa: E402


def flat(text):
    return " ".join(text.split())


class TheGrandfatherClauseIsATest(unittest.TestCase):
    def test_the_rule_states_the_test(self):
        rule = flat(CONVENTIONS["system_file_language"]["rule"])
        self.assertIn("A TEST, NOT A LIST", rule)
        self.assertIn("READ BY A SCRIPT", rule)
        self.assertIn("cost more than the consistency gains", rule)

    def test_the_old_list_survives_as_examples(self):
        rule = CONVENTIONS["system_file_language"]["rule"]
        for name in ("_INDEX-agare.md", "_INDEX-koppling.md", "_INDEX-maskiner.md",
                     "_INDEX-objektmodell.md", "_INDEX-verksamheter.md"):
            self.assertIn(name, rule, "the examples were dropped, not demoted")
        self.assertIn("EXAMPLES of the test passing, not its boundary", rule)

    def test_the_vault_declares_its_own_rather_than_the_contract_enumerating(self):
        self.assertIn("view_files in the config chain",
                      flat(CONVENTIONS["system_file_language"]["rule"]))

    def test_the_asymmetric_cost_is_recorded_because_it_is_what_the_test_weighs(self):
        rule = flat(CONVENTIONS["system_file_language"]["rule"])
        self.assertIn("asymmetric", rule)
        self.assertIn("same rule, two prices", rule)


class TheNamesLiveInSettings(unittest.TestCase):
    def test_view_files_is_declared_in_the_config_defaults(self):
        self.assertIn("view_files", BASE)
        self.assertIn("triage", BASE["view_files"])
        self.assertIn("tasks_view", BASE["view_files"])

    def test_the_suite_reads_them_from_there(self):
        self.assertEqual(sv.view_files(ROOT / "no-such-vault"),
                         {k: str(v) for k, v in BASE["view_files"].items()})

    def test_a_vault_overrides_them_without_touching_the_suite(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "_config").mkdir()
        (d / "_config" / "base.yaml").write_text(
            "view_files:\n  triage: daily-triage.md\n", encoding="utf-8")
        resolved = sv.view_files(d)
        self.assertEqual(resolved["triage"], "daily-triage.md")
        self.assertEqual(resolved["tasks_view"], BASE["view_files"]["tasks_view"],
                         "an unset key must fall back, not disappear")

    def test_no_name_is_spelled_in_the_script_itself(self):
        # A default spelled in code is the same literal one indirection further away.
        src = (ROOT / "skills" / "inbox" / "survey.py").read_text(encoding="utf-8")
        for name in BASE["view_files"].values():
            self.assertNotIn(str(name), src)

    def test_the_resident_set_still_covers_the_declared_views(self):
        import datetime
        import tempfile
        d = Path(tempfile.mkdtemp())
        inbox = d / "_inbox"
        inbox.mkdir()
        (inbox / "_tasks.yaml").write_text("tasks: []\n", encoding="utf-8")
        (inbox / "_inbox.yaml").write_text("items: []\n", encoding="utf-8")
        for name in BASE["view_files"].values():
            (inbox / str(name)).write_text("a view\n", encoding="utf-8")
        (inbox / "a-real-content-file.md").write_text("material\n", encoding="utf-8")
        s = sv.survey(d, datetime.date(2026, 11, 3))
        # `unexpected` is what has taken up residence in a folder that is a door. A
        # declared view is furniture, not residence -- that is what the skip-list is for,
        # and it is now resolved from settings rather than spelled in the script.
        unexpected = s["folder"]["unexpected"]
        for name in BASE["view_files"].values():
            self.assertNotIn(str(name), unexpected, "a declared view counted as content")
        self.assertIn("a-real-content-file.md", unexpected)


class TheCheckCatchesTheLeak(unittest.TestCase):
    def run_check(self):
        r = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_the_tree_is_clean_today(self):
        rc, out = self.run_check()
        self.assertEqual(rc, 0, out)
        self.assertIn("[OK] view filenames", out)

    def test_the_check_is_not_vacuous(self):
        # Plant the leak the CR found, in the place it found it, and require a failure.
        victim = ROOT / "skills" / "inbox" / "SKILL.md"
        original = victim.read_text(encoding="utf-8")
        name = str(BASE["view_files"]["triage"])
        try:
            victim.write_text(original + f"\n<!-- planted: {name} -->\n", encoding="utf-8")
            rc, out = self.run_check()
            self.assertEqual(rc, 1)
            self.assertIn("[DRIFT] view filenames", out)
            self.assertIn(name, out)
        finally:
            victim.write_text(original, encoding="utf-8")
        rc, _ = self.run_check()
        self.assertEqual(rc, 0, "the check did not go clean again after the plant was removed")

    def test_settings_is_the_one_place_the_name_may_appear(self):
        src = (ROOT / "skills" / "ops-config" / "base.yaml").read_text(encoding="utf-8")
        for name in BASE["view_files"].values():
            self.assertIn(str(name), src)
        rc, _ = self.run_check()
        self.assertEqual(rc, 0, "the settings file must not fail its own check")


class TheRuleItEnforcesSaysSo(unittest.TestCase):
    def test_identifier_language_names_the_enforcement(self):
        rule = flat(CONVENTIONS["identifier_language"]["rule"])
        self.assertIn("ENFORCED SINCE CR-171", rule)
        self.assertIn("check-terms.py", rule)

    def test_it_records_that_the_leaks_arrived_after_the_rule(self):
        rule = flat(CONVENTIONS["identifier_language"]["rule"])
        self.assertIn("AFTER this rule shipped", rule)


if __name__ == "__main__":
    unittest.main()
