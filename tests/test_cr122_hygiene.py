"""CR-122: link, YAML and task hygiene, report only.

    python3 -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "ops"))
import hygiene_check as hc  # noqa: E402


class Links(unittest.TestCase):
    def test_raw_parenthesis_found_encoded_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "260103-episode-guest-topic (live).md").write_text("x", encoding="utf-8")
            (d / "README.md").write_text(
                "- [live](260103-episode-guest-topic (live).md)\n"
                "- [live](260103-episode-guest-topic%20%28live%29.md)\n"
                "- [web](https://example.org/a_(b))\n", encoding="utf-8")
            found = hc.check_links(d)
            self.assertEqual(len(found), 1)
            self.assertEqual((found[0]["file"], found[0]["line"]), ("README.md", 1))

    def test_missing_target_found_and_code_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "sub").mkdir()
            (d / "260101-there.md").write_text("x", encoding="utf-8")
            (d / "sub" / "CHANGELOG.md").write_text(
                "[gone](260101-gone.md)\n```\n[x](nope.md)\n```\n[root-relative](260101-there.md)\n",
                encoding="utf-8")
            found = hc.check_links(d)
            self.assertEqual([f["line"] for f in found], [1])


class Yaml(unittest.TestCase):
    def test_escaped_letter_found_literal_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "a").mkdir()
            (d / "a" / "_insights.yaml").write_text('summary: "L\\xE4rdom"\n', encoding="utf-8")
            (d / "_tasks.yaml").write_text('task: "Lärdom"\nemoji_free: "\\x20"\n', encoding="utf-8")
            found = hc.check_yaml(d)
            self.assertEqual([f["file"] for f in found], ["a/_insights.yaml"])


class Tasks(unittest.TestCase):
    def test_title_status_scope_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "_tasks.yaml").write_text(
                "version: 2\ncontext: acme\nscope: editorial\nnext_id: 3\ntasks:\n"
                "  - {id: 1, title: Plan the next episode, status: archived, priority: P2, created: 260101,"
                " source: {type: analysis}}\n"
                "  - {id: 2, task: Link the guest page, status: pending, priority: P3, created: 260101}\n",
                encoding="utf-8")
            msgs = [f["message"] for f in hc.check_tasks(d)]
            self.assertEqual(len(msgs), 4, msgs)
            self.assertTrue(any("`title`" in m for m in msgs))
            self.assertTrue(any("archived" in m for m in msgs))
            self.assertTrue(any("editorial" in m for m in msgs))
            self.assertTrue(any("analysis" in m for m in msgs))

    def test_one_line_per_value_and_declared_source_terms_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            rows = "".join(f"  - {{id: {i}, task: x, status: pending, priority: P2, created: 260101,"
                           f" source: {{type: email}}}}\n" for i in range(1, 9))
            rows += "  - {id: 9, task: x, status: pending, priority: P2, created: 260101, source: {type: content}}\n"
            (d / "_tasks.yaml").write_text("version: 2\ncontext: acme\nscope: project\nnext_id: 10\ntasks:\n" + rows,
                                           encoding="utf-8")
            [f] = hc.check_tasks(d)
            self.assertIn("'email' on 8 task(s)", f["message"])
            self.assertIn("and 3 more", f["message"])

    def test_kind_checked_only_against_a_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            ledger = ("version: 2\ncontext: acme\nscope: project\nnext_id: 2\ntasks:\n"
                      "  - {id: 1, task: x, status: pending, priority: P2, created: 260101, kind: chore}\n")
            (d / "_tasks.yaml").write_text(ledger, encoding="utf-8")
            self.assertEqual(hc.check_tasks(d), [])
            (d / "_ops.yaml").write_text("profile: podcast\n", encoding="utf-8")
            self.assertEqual(len(hc.check_tasks(d)), 1)

    def test_valid_ledger_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "_tasks.yaml").write_text(
                "version: 2\ncontext: acme\nscope: project\nnext_id: 2\ntasks:\n"
                "  - {id: 1, task: x, status: completed, priority: P1, created: 260101,"
                " source: {type: meeting}}\n", encoding="utf-8")
            self.assertEqual(hc.run(d), [])


if __name__ == "__main__":
    unittest.main()
