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
