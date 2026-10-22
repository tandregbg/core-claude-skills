"""CR-157: when the archiver reads less than the project declared, the source line says so.

Invented data. A project cannot widen what an archiver fetches by editing its own config: the
scope that counts is the one the archive RECORDED in `_repo.json`. The generator used to print
`neither issues nor pulls in declared reads -- skipped` for a repository the project had
declared with pull requests, without saying whose reads it meant, and the line was cut at 44
characters in the sources block.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cr101_agenda_draft import build, CF  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_agenda as ba  # noqa: E402

DECLARES_PULLS = ("external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"
                  "      reads: [pulls, releases]\n")
DECLARES_NOTHING = "external_systems:\n  repos:\n    - url: https://github.com/acme/app\n"


class ScopeText(unittest.TestCase):
    def test_both_lists_and_whose_decision(self):
        t = ba.scope_text("acme/app", ["docs"], ["pulls", "releases"])
        self.assertIn("the archive reads only docs", t)
        self.assertIn("the project asked for pulls, releases", t)
        self.assertIn("the archiver's own configuration decides", t)
        self.assertNotIn("skipped", t)

    def test_skipped_is_added_when_the_repo_cannot_be_used(self):
        self.assertTrue(ba.scope_text("acme/app", ["docs"], ["pulls"], skipped=True).endswith("— skipped"))

    def test_an_empty_record_reads_as_nothing(self):
        self.assertIn("the archive reads only nothing", ba.scope_text("acme/app", [], ["pulls"]))


class ScopeMismatches(unittest.TestCase):
    def archive(self, reads, declared_cfg):
        root = Path(tempfile.mkdtemp())
        (root / ".githubmeta" / "app").mkdir(parents=True)
        (root / ".githubmeta" / "app" / "_repo.json").write_text(
            json.dumps({"slug": "app", "repo": "acme/app", "reads": reads}), encoding="utf-8")
        proj = root / "proj"
        proj.mkdir()
        return {"_root": proj, "ext": declared_cfg}

    def declared(self, reads):
        return {"repos": [{"url": "https://github.com/acme/app", "reads": reads}]}

    def test_an_archive_that_reads_less_is_reported_with_what_is_missing(self):
        cf = self.archive(["docs"], self.declared(["pulls", "releases"]))
        self.assertEqual(ba.scope_mismatches(cf), [("acme/app", ["docs"], ["pulls", "releases"])])

    def test_only_the_missing_kinds_are_named(self):
        cf = self.archive(["pulls", "docs"], self.declared(["pulls", "releases"]))
        self.assertEqual(ba.scope_mismatches(cf), [("acme/app", ["pulls", "docs"], ["releases"])])

    def test_an_archive_that_reads_more_is_silent(self):
        cf = self.archive(["docs", "issues", "pulls", "releases"], self.declared(["pulls"]))
        self.assertEqual(ba.scope_mismatches(cf), [])

    def test_a_project_that_declared_no_reads_has_nothing_to_compare(self):
        cf = self.archive(["docs"], {"repos": [{"url": "https://github.com/acme/app"}]})
        self.assertEqual(ba.scope_mismatches(cf), [])

    def test_the_check_does_not_fail_on_a_note(self):
        self.assertNotIn(ba.NOTE, ba.CHECK_BAD)


class SourcesBlock(unittest.TestCase):
    def test_a_declared_scope_the_archive_ignores_is_named_in_full(self):
        agenda, _ = build(CF + DECLARES_PULLS, repo={"reads": ["docs"], "pulls": []})
        self.assertIn("the archive reads only docs; the project asked for pulls, releases;", agenda)
        self.assertIn("the archiver's own configuration decides — skipped", agenda)

    def test_a_partial_scope_is_a_scope_note_not_an_unread_source(self):
        agenda, _ = build(CF + DECLARES_PULLS, repo={"reads": ["pulls"], "pulls": []})
        line = next(l for l in agenda.split("\n") if "the archive reads only pulls" in l and l.strip().startswith("repo"))
        self.assertIn("SCOPE", line)
        self.assertNotIn("NOT READ", line)

    def test_a_repo_whose_archive_reads_what_was_declared_has_no_scope_line(self):
        agenda, _ = build(CF + DECLARES_PULLS, repo={"reads": ["pulls", "releases"], "pulls": []})
        self.assertNotIn("the archive reads only", agenda)

    def test_no_declared_reads_keeps_the_plain_reason(self):
        agenda, _ = build(CF + DECLARES_NOTHING, repo={"reads": ["docs"], "pulls": []})
        self.assertIn("the archive reads only docs, neither issues nor pulls — skipped", agenda)


if __name__ == "__main__":
    unittest.main()
