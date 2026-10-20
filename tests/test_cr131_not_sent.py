"""CR-131: a *not sent* outcome needs no documented reason. Invented data."""

import datetime
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "outbox"))
import resolved as rs  # noqa: E402

TODAY = datetime.date(2026, 10, 20)


def manifest(status, note=None, outcome=""):
    lines = ["# Outbox -- test", "", f"**Status:** {status}"]
    if note is not None:
        lines.append(f"**Statusnot:** {note}")
    lines += ["**Kontakt:** Bob (Acme)", "", "## Utfall", "", outcome, ""]
    return "\n".join(lines)


class NotSentOutcome(unittest.TestCase):
    def plan(self, text):
        with tempfile.TemporaryDirectory() as d:
            vault = Path(d)
            folder = vault / "_outbox" / "261001-bob_recap"
            folder.mkdir(parents=True)
            (folder / "_manifest.md").write_text(text, encoding="utf-8")
            [entry] = rs.plan(vault, vault / "_outbox", TODAY)["resolved"]
            return entry

    def test_empty_note_gives_bare_outcome(self):
        e = self.plan(manifest("avskriven 2026-10-01"))
        self.assertEqual(e["outcome"], "Skickades inte.")
        self.assertEqual(e["problems"], [])

    def test_note_is_kept_as_reason(self):
        e = self.plan(manifest("avskriven 2026-10-01", "tas muntligt"))
        self.assertEqual(e["outcome"], "Skickades inte: tas muntligt")

    def test_written_outcome_is_untouched(self):
        e = self.plan(manifest("avskriven 2026-10-01", None, "Skickades inte."))
        self.assertTrue(e["outcome_present"])
        self.assertNotIn("outcome", e)


if __name__ == "__main__":
    unittest.main()
