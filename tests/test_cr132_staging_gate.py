"""CR-132: source and declared status are required when a manifest is staged. Invented data."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "skills" / "outbox"
sys.path.insert(0, str(HERE))
import resolved as rs  # noqa: E402


def manifest(status="draft", source="_contacts/bob/leverans/260101-onepager.md"):
    lines = ["# Outbox -- test", ""]
    if status is not None:
        lines.append(f"**Status:** {status}")
    lines.append("**Kontakt:** Bob (Acme)")
    if source is not None:
        lines.append(f"**Kanonisk källa:** {source}")
    return "\n".join(lines) + "\n"


class StagingGate(unittest.TestCase):
    def test_complete_manifest_passes(self):
        self.assertEqual(rs.staging_problems(manifest()), [])
        self.assertEqual(rs.staging_problems(manifest("klar-att-skicka", "ingen (originalet bor här)")), [])

    def test_missing_source_is_refused(self):
        [p] = rs.staging_problems(manifest(source=None))
        self.assertIn("Kanonisk källa", p)

    def test_blank_or_placeholder_source_is_refused(self):
        for src in ("", "[path to the source doc]", "TBD"):
            self.assertTrue(rs.staging_problems(manifest(source=src)), src)

    def test_free_status_phrase_is_refused_with_hint(self):
        [p] = rs.staging_problems(manifest(status="redo att skickas"))
        self.assertIn("klar-att-skicka", p)

    def test_colon_inside_bold_is_refused(self):
        text = "# t\n\n**Status: SKICKAD 2026-10-01.**\n**Kanonisk källa:** ingen (originalet bor här)\n"
        [p] = rs.staging_problems(text)
        self.assertIn("colon outside the bold", p)

    def test_emphasis_around_value_is_refused(self):
        self.assertTrue(rs.staging_problems(manifest(status="**draft**")))

    def test_no_status_line(self):
        [p] = rs.staging_problems(manifest(status=None))
        self.assertIn("Status", p)

    def test_free_phrase_with_declared_leading_word_is_refused(self):
        for st in ("draft men inte klar", "skickad inte", "klar-att-skicka kanske", "draft, men inte klar"):
            self.assertTrue(rs.staging_problems(manifest(status=st)), st)

    def test_declared_word_with_date_or_note_passes(self):
        for st in ("skickad 2026-10-01", "avskriven (ersatt av 261001-x)", "skickad - 2026-10-01", "utkast"):
            self.assertEqual(rs.staging_problems(manifest(status=st)), [], st)

    def test_non_canonical_source_is_refused(self):
        for src in ("ingen", "ingen (originalet finns inte)", "n/a", "<path>", "…", "**x**", "none"):
            self.assertTrue(rs.staging_problems(manifest(source=src)), src)

    def test_path_and_ascii_no_source_pass(self):
        for src in ("ingen (originalet bor har)", "Ingen (originalet bor här)", "`_contacts/bob/x.md`",
                    "~/repos/other/README.md", "_contacts/bob/leverans/"):
            self.assertEqual(rs.staging_problems(manifest(source=src)), [], src)

    def test_ascii_source_label_is_read(self):
        text = "# t\n\n**Status:** draft\n**Kanonisk kalla:** ingen (originalet bor har)\n"
        self.assertEqual(rs.staging_problems(text), [])

    def test_status_in_code_fence_or_body_does_not_count(self):
        text = "# t\n\n```\n**Status:** draft\n```\n**Kanonisk källa:** a/b.md\n"
        [p] = rs.staging_problems(text)
        self.assertIn("no `**Status:**", p)
        late = "# t\n" + "x\n" * 70 + "**Status:** draft\n**Kanonisk källa:** a/b.md\n"
        self.assertTrue(rs.staging_problems(late))

    def test_source_after_header_block_is_refused(self):
        text = "# t\n**Status:** draft\n" + "x\n" * 70 + "**Kanonisk källa:** a/b.md\n"
        [p] = rs.staging_problems(text)
        self.assertIn("Kanonisk källa", p)

    def test_misplaced_status_forms_get_the_colon_message(self):
        for line in ("**Status** : draft", "- **Status:** draft", "**Status : draft**"):
            text = f"# t\n\n{line}\n**Kanonisk källa:** a/b.md\n"
            [p] = rs.staging_problems(text)
            self.assertIn("colon outside the bold", p, line)

    def test_cli_missing_file_and_stdin(self):
        script = str(HERE / "resolved.py")
        r = subprocess.run([sys.executable, script, "--validate", "/nonexistent/m.md"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["ok"])
        r = subprocess.run([sys.executable, script, "--validate", "-"], input=manifest(),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        r = subprocess.run([sys.executable, script, "--validate", "-"], input=b"\xff\xfe",
                           capture_output=True)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["ok"])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            good, bad = Path(d, "good.md"), Path(d, "bad.md")
            good.write_text(manifest(), encoding="utf-8")
            bad.write_text(manifest(source=None), encoding="utf-8")
            run = lambda f: subprocess.run([sys.executable, str(HERE / "resolved.py"), "--validate", str(f)],
                                           capture_output=True, text=True)
            self.assertEqual(run(good).returncode, 0)
            r = run(bad)
            self.assertEqual(r.returncode, 1)
            self.assertFalse(json.loads(r.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
