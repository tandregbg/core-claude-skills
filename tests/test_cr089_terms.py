"""CR-089: the skills say what the contract says, in the contract's words.

    python3 -m unittest discover -s tests

The parser is the part that can be wrong quietly: a heading it cannot read, or a section
it cuts short at a `## ` inside an example, reads as a missing subcommand - or worse, as a
clean result. So the parser is tested on the shapes the skills actually use, and the whole
repo is checked end to end.
"""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_terms", ROOT / "scripts" / "check-terms.py")
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)


class HeadingName(unittest.TestCase):
    def test_bare(self):
        self.assertEqual(ct.heading_name("### `status` -- Show", "ops"), "status")

    def test_arguments_dropped(self):
        self.assertEqual(ct.heading_name("### `orient <folder>` -- where", "ops"), "orient")
        self.assertEqual(ct.heading_name('### `/tasks add "description"`', "tasks"), "add")

    def test_two_word_subcommand_kept(self):
        self.assertEqual(ct.heading_name("### `project new <name>` -- create", "ops"), "project new")

    def test_flag_kept(self):
        self.assertEqual(ct.heading_name("### `close --all-sent` (CR-019)", "outbox"), "close --all-sent")

    def test_skill_prefix_and_numbering(self):
        self.assertEqual(ct.heading_name("### `/inbox route [id|all]` -- Route", "inbox"), "route")
        self.assertEqual(ct.heading_name("### 3. `check` -- Verify", "update-skills"), "check")

    def test_default_heading_is_not_a_subcommand(self):
        self.assertIsNone(ct.heading_name("### `/inbox [content]` -- Default", "inbox"))


class Section(unittest.TestCase):
    def test_fenced_heading_does_not_end_the_section(self):
        text = "## SUBCOMMANDS\n### `status`\n```\n## /ops Configuration Status\n```\n### `help`\n## NEXT\n### `x`\n"
        self.assertEqual(ct.subcommand_section(text).splitlines(), ["### `status`", "### `help`"])

    def test_no_section(self):
        self.assertIsNone(ct.subcommand_section("## Usage\n### `x`\n"))


class Phrases(unittest.TestCase):
    def test_inline_code_is_not_prose(self):
        lines = dict(ct.prose_lines_from("see `the note` here\nthe note is prose\n"))
        self.assertNotIn("the note", lines[1])
        self.assertIn("the note", lines[2])


class Repo(unittest.TestCase):
    def test_repository_is_clean(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check-terms.py")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
