"""CR-152: the ledger's source vocabulary is the contract's, and shape is not channel.

Both enums lived as tuples inside `hygiene_check.py` -- the same place the status enum
lived before CR-048 moved it into the contract, with a rationale that reads as a
prediction of this CR: *declared here because it was not, and three other dialects grew
in its absence.* Three grew in the status field. Twenty-two grew in the neighbouring one,
because `type` asks for the SHAPE and a person filing a task knows the CHANNEL first:
`email` plus `mail` held 105 rows on one vault against 6 for `correspondence`, the
declared word for the same material.

The assertions that matter are about the three decisions, not the data: the enums come
from the contract, an alias is read and reported once per LEDGER rather than once per row
(CR-120 -- a wall is a check that has stopped working), and the channel field is open
because closing it is what produced the dialects in the first place.

    python3 -m unittest discover -s tests
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))

sys.path.insert(0, str(ROOT / "skills" / "ops"))
import hygiene_check as HC  # noqa: E402


def ledger(rows, scope="project"):
    out = f"version: 2\nscope: {scope}\ncontext: acme\ntasks:\n"
    for i, (stype, extra) in enumerate(rows, 1):
        out += f"- id: {i}\n  task: t{i}\n  status: pending\n  source:\n    type: {stype}\n"
        if extra:
            out += f"    channel: {extra}\n"
    return out


class TheContractCarriesTheVocabulary(unittest.TestCase):
    def test_both_enums_are_declared(self):
        self.assertIn("task_source_types", CONTRACT)
        self.assertIn("task_scopes", CONTRACT)

    def test_the_two_missing_words_are_in(self):
        # `analysis`: work the owner derived from reading their own material -- 22 rows over
        # four ledgers. `contact`: a ledger in a contact folder, a shape with no correct
        # value to write since the vault began.
        self.assertIn("analysis", CONTRACT["task_source_types"])
        self.assertIn("contact", CONTRACT["task_scopes"])

    def test_nothing_that_was_declared_was_removed(self):
        for word in ("meeting", "decision", "manual", "imported", "content", "correspondence"):
            self.assertIn(word, CONTRACT["task_source_types"])
        for word in ("root", "org", "project", "personal"):
            self.assertIn(word, CONTRACT["task_scopes"])

    def test_the_checker_reads_the_contract_not_its_own_tuple(self):
        types, scopes, aliases, scope_aliases = HC.task_vocabulary()
        self.assertEqual(list(types), list(CONTRACT["task_source_types"]))
        self.assertEqual(list(scopes), list(CONTRACT["task_scopes"]))
        self.assertEqual(set(aliases), set(CONTRACT["task_source_aliases"]))
        self.assertEqual(scope_aliases, {k: str(v) for k, v in CONTRACT["task_scope_aliases"].items()})

    def test_every_alias_resolves_to_a_declared_type(self):
        for word, target in CONTRACT["task_source_aliases"].items():
            self.assertIn(target["type"], CONTRACT["task_source_types"], word)
        for word, target in CONTRACT["task_scope_aliases"].items():
            self.assertIn(target, CONTRACT["task_scopes"], word)

    def test_no_alias_shadows_a_canonical_word(self):
        # An alias for a word that is already legal would make the same value mean two things.
        self.assertFalse(set(CONTRACT["task_source_aliases"]) & set(CONTRACT["task_source_types"]))

    def test_the_channel_list_is_a_starter_set_and_not_an_enum(self):
        # Closing it would reproduce the defect one field over. The key name says it is
        # observed, not permitted, and no checker reads it.
        self.assertIn("task_source_channels_seen", CONTRACT)
        self.assertNotIn("task_source_channels", CONTRACT)

    def test_async_is_deliberately_in_neither_list(self):
        # Not a shape: the rows under it are a pre-meeting update, a self-raised infra task
        # and three spreadsheet items. Mapping it to the nearest word is how that word loses
        # its meaning, so it stays a finding -- a question for a person.
        self.assertNotIn("async", CONTRACT["task_source_types"])
        self.assertNotIn("async", CONTRACT["task_source_aliases"])


class TheCheckIsQuieterAndSharper(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, body):
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "_tasks.yaml").write_text(body, encoding="utf-8")

    def tasks_findings(self):
        return [f for f in HC.check_tasks(self.root) if "TASKS" in str(f) or True]

    def messages(self):
        return [str(f) for f in HC.check_tasks(self.root)]

    def test_an_aliased_word_is_one_line_per_ledger_not_one_per_row(self):
        self.write("a", ledger([("email", None)] * 6 + [("chat", None)] * 4))
        msgs = [m for m in self.messages() if "legacy source word" in m]
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn("10 task(s)", msgs[0])
        self.assertIn("email -> correspondence", msgs[0])

    def test_the_advisory_says_what_the_word_resolves_to(self):
        self.write("a", ledger([("email", None)]))
        msg = [m for m in self.messages() if "legacy source word" in m][0]
        self.assertIn("channel email", msg)
        self.assertIn("nothing here is rewritten", msg)

    def test_an_unknown_word_is_still_a_finding(self):
        self.write("a", ledger([("async", None), ("async", None)]))
        msgs = [m for m in self.messages() if "source.type 'async'" in m]
        self.assertEqual(len(msgs), 1)
        self.assertIn("2 task(s)", msgs[0])

    def test_a_canonical_word_produces_nothing(self):
        self.write("a", ledger([("correspondence", "email"), ("analysis", None)]))
        self.assertFalse([m for m in self.messages() if "source.type" in m or "legacy" in m])

    def test_the_new_scope_is_legal_and_the_legacy_one_is_advisory(self):
        self.write("c", ledger([("meeting", None)], scope="contact"))
        self.assertFalse([m for m in self.messages() if "scope" in m])
        self.write("m", ledger([("meeting", None)], scope="management"))
        msgs = [m for m in self.messages() if "scope 'management'" in m]
        self.assertEqual(len(msgs), 1)
        self.assertIn("read as 'org'", msgs[0])

    def test_an_unknown_scope_is_still_a_finding(self):
        self.write("x", ledger([("meeting", None)], scope="galaxy"))
        msgs = [m for m in self.messages() if "scope 'galaxy'" in m]
        self.assertEqual(len(msgs), 1)
        self.assertIn("is not one of", msgs[0])

    def test_channel_is_never_checked(self):
        self.write("a", ledger([("correspondence", "carrier-pigeon")]))
        self.assertFalse([m for m in self.messages() if "channel" in m and "legacy" not in m])

    def test_nothing_is_rewritten(self):
        body = ledger([("email", None)])
        self.write("a", body)
        HC.check_tasks(self.root)
        self.assertEqual((self.root / "a" / "_tasks.yaml").read_text(encoding="utf-8"), body)


class TheSkillsSayIt(unittest.TestCase):
    def test_the_tasks_skill_documents_the_two_questions(self):
        t = (ROOT / "skills" / "tasks" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("source.channel", t)
        self.assertIn("Open, and deliberately so", t)
        self.assertIn("task_source_aliases", t)

    def test_the_ops_check_says_an_alias_is_not_a_finding(self):
        t = (ROOT / "skills" / "ops" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("task_source_aliases", t)
        self.assertIn("one advisory\n   line per ledger", t)


if __name__ == "__main__":
    unittest.main()
