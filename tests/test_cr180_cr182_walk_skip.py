"""CR-180 + CR-182: two reading surfaces for a person, and one list of folders every walk skips.

`_callcards/` (one generated card per contact) and `_toread/` (reading copies of material written
for the user) carry an UNDERSCORE so a phone can pin them -- a dot-folder is hidden in the editor and
the phone's file app. That is exactly what makes them dangerous to the suite: most walkers drop
every dot-folder and believe that is enough. These tests hold the two properties the CRs rest on:

1. the contract declares the surfaces and ONE `walk_skip` list, read through one module, and
2. every script that walks the vault for material skips both, while still finding the same file
   one folder over.

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


def load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, [name + ".py"]
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    return mod


WS = load("skills/ops-base/walk_skip.py", "walk_skip")
BLOCKED = ("_callcards", "_toread")


def conventions():
    return {c["id"]: c for c in CONTRACT["vault_conventions"]["conventions"]}


def make_vault(tmp: Path, filename: str, body: str = "x: 1\n") -> Path:
    """A vault with the same file in a living folder and in both blocked surfaces."""
    (tmp / "_inbox").mkdir()
    for d in ("contacts/alex", "_callcards", "_toread/sub"):
        (tmp / d).mkdir(parents=True)
        (tmp / d / filename).write_text(body, encoding="utf-8")
    return tmp


def rel_parts(paths, root):
    return [Path(p).resolve().relative_to(root.resolve()).parts[0] for p in paths]


class ContractTest(unittest.TestCase):
    def test_both_surfaces_are_declared_at_the_root(self):
        paths = {e["path"] for e in CONTRACT["vault_conventions"]["vault_root"]}
        self.assertIn("_callcards/", paths)
        self.assertIn("_toread/", paths)

    def test_walk_skip_is_one_invariant_list_holding_both(self):
        conv = conventions()["walk_skip"]
        self.assertEqual(conv["level"], "invariant")
        for name in ("_callcards/", "_toread/", ".handoff/", ".transcripts/", ".archive/"):
            self.assertIn(name, conv["paths"])

    def test_both_are_singletons(self):
        surfaces = conventions()["singleton_surfaces"]["surfaces"]
        self.assertIn("_callcards/", surfaces)
        self.assertIn("_toread/", surfaces)

    def test_callcards_is_a_named_exception_to_structural_isolation(self):
        self.assertIn("_callcards/", conventions()["generated_view_isolation"]["exceptions"])

    def test_binary_archive_is_declared(self):
        self.assertIn("binary_archive", conventions())

    def test_contract_version_moved(self):
        self.assertGreaterEqual(CONTRACT["contract_version"], 52)


class WalkSkipModuleTest(unittest.TestCase):
    def test_names_come_from_the_contract(self):
        names = WS.contract_names()
        for n in BLOCKED + (".handoff", ".transcripts"):
            self.assertIn(n, names)
        self.assertTrue(all(not n.endswith("/") for n in names))

    def test_a_vault_can_add_but_not_remove(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "_inbox").mkdir()
            (tmp / "_config").mkdir()
            (tmp / "_config" / "base.yaml").write_text(
                "vault_conventions:\n  walk_skip: ['_cards/']\n", encoding="utf-8")
            names = WS.names(tmp)
            self.assertIn("_cards", names)
            for n in BLOCKED:
                self.assertIn(n, names)
            self.assertTrue(WS.skip("_cards", tmp))
            self.assertFalse(WS.skip("contacts", tmp))

    def test_outside_a_vault_the_contract_list_still_applies(self):
        self.assertTrue(WS.skip("_toread", None))
        self.assertTrue(WS.skip("_callcards/", None))


class WalkersSkipTheSurfacesTest(unittest.TestCase):
    """Every script walk that reads vault material for a skill finds the living copy only."""

    def assert_only_living(self, found, root):
        tops = rel_parts(found, root)
        self.assertIn("contacts", tops, "the living file must still be found")
        for b in BLOCKED:
            self.assertNotIn(b, tops, f"walked into {b}/")

    def test_compile_status(self):
        mod = load("skills/insights/compile_status.py", "compile_status")
        with tempfile.TemporaryDirectory() as t:
            root = make_vault(Path(t), "_insights.yaml")
            self.assert_only_living(list(mod.insight_files(root)), root)

    def test_promotion_candidates(self):
        mod = load("skills/insights/promotion_candidates.py", "promotion_candidates")
        with tempfile.TemporaryDirectory() as t:
            root = make_vault(Path(t), "_insights.yaml")
            self.assert_only_living(list(mod.insight_files(root)), root)

    def test_hygiene_check(self):
        mod = load("skills/ops/hygiene_check.py", "hygiene_check")
        with tempfile.TemporaryDirectory() as t:
            root = make_vault(Path(t), "260101-summary-a.md", "# a\n")
            found = [p for p in mod.walk(root) if p.name.endswith(".md")]
            self.assert_only_living(found, root)

    def test_themes(self):
        mod = load("skills/ops/themes.py", "themes")
        with tempfile.TemporaryDirectory() as t:
            root = make_vault(Path(t), "260101-summary-a.md", "# a\n")
            found = [p for p in mod._walk(root) if p.name.endswith(".md")]
            self.assert_only_living(found, root)

    def test_list_projects(self):
        mod = load("skills/ops/list_projects.py", "list_projects")
        body = "series:\n  name: weekly\n"
        with tempfile.TemporaryDirectory() as t:
            root = make_vault(Path(t), "_ops.yaml", body)
            self.assert_only_living(mod.find_series(root), root)

    def test_resolved_skips_the_surfaces(self):
        mod = load("skills/outbox/resolved.py", "resolved")
        for b in BLOCKED:
            self.assertIn(b, mod.SKIP_DIRS)


class ProseTest(unittest.TestCase):
    """The rule reaches the skills a person and a session read."""

    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_ops_base_names_the_list_and_the_module(self):
        text = self.read("skills/ops-base/SKILL.md")
        self.assertIn("walk_skip", text)
        self.assertIn("walk_skip.py", text)
        self.assertIn("`_toread/`", text)
        self.assertIn("Prospects live with the person", text)

    def test_outbox_scope_sends_reading_copies_elsewhere(self):
        text = self.read("skills/outbox/SKILL.md")
        self.assertIn("Is it going to leave the vault?", text)
        self.assertIn("`_toread/`", text)

    def test_inline_skip_lists_carry_both(self):
        for rel in ("skills/insights/SKILL.md", "skills/transcript/SKILL.md",
                    "skills/ops/SKILL.md", "skills/analytics/SKILL.md"):
            text = self.read(rel)
            self.assertIn("`_callcards/`, `_toread/`", text, rel)


if __name__ == "__main__":
    unittest.main()
