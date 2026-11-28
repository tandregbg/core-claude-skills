"""CR-184, CR-185, CR-186: a call card follows its material; a folder says which contact it is about;
an alias can hold only under a path.

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
SCHEMA = (ROOT / "skills" / "ops-config" / "contact-meta-schema.md").read_text(encoding="utf-8")


def load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, [name + ".py"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    return mod


CN = load("skills/ops-base/contact_names.py", "contact_names")
HC = load("skills/ops/hygiene_check.py", "hygiene_check")


def paths(contract):
    """Every declared surface ({path: entry}) wherever the contract nests it."""
    out = {}

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("path"), str) and "purpose" in o:
                out[o["path"]] = o
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(contract)
    return out


def vault(files):
    root = Path(tempfile.mkdtemp())
    (root / "_inbox").mkdir()                       # what makes it a vault (walk_skip.vault_root)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


TWO_ERIKS = {
    "_contacts/erik-sandberg/_meta.yaml":
        'version: 1\ndisplay_name: "Erik Sandberg"\naliases: ["Sandberg"]\n'
        'aliases_within:\n  "acme/":\n    - "Erik"\n',
    "_contacts/erik-lindgren/_meta.yaml": 'version: 1\naliases: ["Erik"]\n',      # name from the folder
    "_contacts/carol-jones/_meta.yaml": 'version: 1\naliases: ["Erik"]\n',
    "acme/meetings/management/Erik/_meta.yaml": 'version: 1\ncontact: erik-sandberg\n',
    "acme/meetings/management/Erik/260101-one-on-one.md": "# 1:1\n",
}


class TestCR184Contract(unittest.TestCase):
    def test_the_card_schema_carries_no_fixed_count(self):
        raw = (ROOT / "ecosystem.yaml").read_text(encoding="utf-8")
        line = next(l for l in raw.splitlines() if l.strip().startswith('- path: "_callcards/"'))
        block = raw[raw.index(line):raw.index("lifecycle:", raw.index(line))]
        self.assertNotIn("at most 15", block)
        self.assertIn("YYMMDD", block)                   # every point carries its source date
        self.assertIn("follows the material", block)
        self.assertIn("connected to the person", block)


class TestCR185FolderContact(unittest.TestCase):
    def setUp(self):
        self.v = vault(TWO_ERIKS)

    def test_a_folder_outside_contacts_names_its_contact(self):
        f = self.v / "acme/meetings/management/Erik"
        self.assertEqual(CN.folder_contact(f), "erik-sandberg")
        self.assertEqual(CN.person_of_folder(f), "erik-sandberg")

    def test_inside_contacts_the_key_is_ignored(self):
        (self.v / "_contacts/carol-jones/_meta.yaml").write_text('contact: erik-sandberg\n', encoding="utf-8")
        self.assertIsNone(CN.folder_contact(self.v / "_contacts/carol-jones"))

    def test_without_the_key_display_name_then_folder_name(self):
        f = self.v / "acme/meetings/weekly"
        f.mkdir(parents=True)
        self.assertEqual(CN.person_of_folder(f), "weekly")
        (f / "_meta.yaml").write_text('display_name: "[Weekly]"\n', encoding="utf-8")
        self.assertEqual(CN.person_of_folder(f), "[Weekly]")

    def test_ops_check_reports_a_contact_that_does_not_exist(self):
        self.assertEqual(HC.check_contacts(self.v), [])
        bad = self.v / "acme/meetings/management/Dan/_meta.yaml"
        bad.parent.mkdir(parents=True)
        bad.write_text('contact: dan-smith\n', encoding="utf-8")
        found = HC.check_contacts(self.v)
        self.assertEqual([f["file"] for f in found], ["acme/meetings/management/Dan/_meta.yaml"])
        self.assertIn("dan-smith", found[0]["message"])
        self.assertIn("contacts", HC.CHECKS)

    def test_the_card_naming_rule_points_at_the_key(self):
        card = paths(CONTRACT)["_callcards/"]
        self.assertIn("contact", card["naming"])

    def test_the_meta_entry_names_the_key(self):
        meta = paths(CONTRACT)["<folder>/_meta.yaml"]
        self.assertIn("contact", meta["purpose"])
        self.assertEqual(meta["schema"], "contact-meta v1.2")


class TestCR186ScopedAliases(unittest.TestCase):
    def setUp(self):
        self.c = CN.load(vault(TWO_ERIKS))

    def test_scoped_wins_over_shared_inside_its_scope(self):
        self.assertEqual(CN.resolve_in_file("Erik", "acme/meetings/260101-standup.md", self.c), "erik-sandberg")

    def test_outside_the_scope_the_name_stays_shared(self):
        self.assertIsNone(CN.resolve_in_file("Erik", "other/260101-notes.md", self.c))

    def test_longest_prefix_wins_and_a_same_prefix_tie_is_nobodys(self):
        c = {"a": {"display_name": "A", "names": ["A"], "scoped": [("acme/", "Erik")]},
             "b": {"display_name": "B", "names": ["B"], "scoped": [("acme/meetings/", "Erik")]}}
        self.assertEqual(CN.scoped_owner("acme/meetings/x.md", "Erik", c), "b")
        self.assertEqual(CN.scoped_owner("acme/other/x.md", "Erik", c), "a")
        c["b"]["scoped"] = [("acme/", "Erik")]
        self.assertIsNone(CN.scoped_owner("acme/x.md", "Erik", c))

    def test_a_fuller_name_still_matches_as_itself(self):
        self.assertEqual(CN.resolve_in_file("Erik Lindgren", "acme/x.md", self.c), "erik-lindgren")
        self.assertEqual(CN.resolve_in_file("Erik Sandberg", "other/x.md", self.c), "erik-sandberg")

    def test_a_typed_query_is_unchanged_by_scopes(self):
        slug, candidates = CN.resolve_query("Erik", self.c)
        self.assertIsNone(slug)
        self.assertEqual(candidates, ["carol-jones", "erik-lindgren"])
        self.assertEqual(CN.resolve_query("Erik Sandberg", self.c)[0], "erik-sandberg")

    def test_the_schema_documents_both_keys(self):
        self.assertIn("Contact Metadata Schema v1.2", SCHEMA)
        for word in ("aliases_within", "contact:", "longest", "tie"):
            self.assertIn(word, SCHEMA)


class TestReviewFindings(unittest.TestCase):
    """Edge cases found in the pre-push review of 1.99.0."""

    def test_a_same_prefix_tie_does_not_fall_through_to_a_global_owner(self):
        c = {"a": {"display_name": "A", "names": ["A"], "scoped": [("acme/", "Erik")]},
             "b": {"display_name": "B", "names": ["B"], "scoped": [("acme/", "Erik")]},
             "c": {"display_name": "C", "names": ["C", "Erik"], "scoped": []}}
        self.assertIsNone(CN.resolve_in_file("Erik", "acme/x.md", c))
        self.assertEqual(CN.resolve_in_file("Erik", "other/x.md", c), "c")

    def test_scalar_and_empty_values(self):
        v = vault({"_contacts/erik-sandberg/_meta.yaml":
                   'display_name: "Erik Sandberg"\naliases: Sandberg\naliases_within:\n  "acme/": null\n  "/": ["Erik"]\n  "ops/": Erik\n'})
        c = CN.load(v)["erik-sandberg"]
        self.assertIn("Sandberg", c["names"])
        self.assertFalse(any(len(n) == 1 for n in c["names"]))        # a scalar is one name, not letters
        self.assertEqual(c["scoped"], [("ops/", "Erik")])               # null and "/" give nothing

    def test_paths_as_path_objects_and_dot_slash(self):
        c = CN.load(vault(TWO_ERIKS))
        self.assertEqual(CN.resolve_in_file("Erik", Path("acme/x.md"), c), "erik-sandberg")
        self.assertEqual(CN.resolve_in_file("Erik", "./acme/x.md", c), "erik-sandberg")

    def test_outside_a_vault_the_check_reports_nothing(self):
        root = Path(tempfile.mkdtemp())                                # no _inbox/_outbox/.obsidian
        (root / "_contacts" / "erik-sandberg").mkdir(parents=True)
        (root / "x").mkdir()
        (root / "x" / "_meta.yaml").write_text("contact: erik-sandberg\n", encoding="utf-8")
        self.assertEqual(HC.check_contacts(root), [])

    def test_contact_must_be_one_exact_folder_name(self):
        v = vault(TWO_ERIKS)
        for bad in ("../acme", "Erik-Sandberg", ".hidden"):
            with self.subTest(bad=bad):
                (v / "acme/meetings/management/Erik/_meta.yaml").write_text(f"contact: '{bad}'\n", encoding="utf-8")
                self.assertEqual(len(HC.check_contacts(v)), 1, bad)


class TestContract(unittest.TestCase):
    def test_contract_53(self):
        self.assertEqual(CONTRACT["contract_version"], 53)


if __name__ == "__main__":
    unittest.main()
