"""CR-133: a sent item ages out. Invented data."""

import datetime
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "outbox"))
import resolved as rs  # noqa: E402

TODAY = datetime.date(2026, 10, 20)


def manifest(status="skickad 2026-08-01", replies=None, outcome=""):
    lines = ["# Outbox -- test", "", f"**Status:** {status}", ""]
    if replies is not None:
        lines += ["## Svar förväntas på", ""] + replies + [""]
    lines += ["## Utfall", "", outcome, ""]
    return "\n".join(lines)


class AgesOut(unittest.TestCase):
    def offer(self, text, name="260801-bob_recap"):
        return rs.offered_outcome(text, name, TODAY)

    def test_no_reply_section_is_finished_when_sent(self):
        self.assertEqual(self.offer(manifest()),
                         "Skickat 2026-08-01. Inget svar förväntades.")
        self.assertTrue(rs.is_closable(manifest()))

    def test_outcome_outranks_unticked_boxes(self):
        text = manifest(replies=["- [ ] svar"], outcome="Bob svarade muntligt.")
        self.assertTrue(rs.is_closable(text))
        self.assertIsNone(self.offer(text))

    def test_old_unanswered_item_is_offered_not_closable(self):
        text = manifest(replies=["- [ ] svar"])
        self.assertEqual(self.offer(text),
                         "Skickat 2026-08-01. Inget svar inkom inom 80 dagar.")
        self.assertFalse(rs.is_closable(text))

    def test_recent_unanswered_item_is_left_alone(self):
        self.assertIsNone(self.offer(manifest("skickad 2026-10-10", ["- [ ] svar"])))

    def test_falls_back_to_folder_date_and_ignores_drafts(self):
        self.assertEqual(self.offer(manifest("skickad"), "260901-bob_recap"),
                         "Skickat 2026-09-01. Inget svar förväntades.")
        self.assertIsNone(self.offer(manifest("draft")))

    def test_survey_counts_aged_out(self):
        with tempfile.TemporaryDirectory() as d:
            vault = Path(d)
            for name, text in (("260801-bob_a", manifest(replies=["- [ ] svar"])),
                               ("260801-bob_b", manifest())):
                f = vault / "_outbox" / name
                f.mkdir(parents=True)
                (f / "_manifest.md").write_text(text, encoding="utf-8")
            sv = rs.survey(vault, vault / "_outbox", TODAY)
            self.assertEqual(sv["counts"]["ages_out"], 1)
            self.assertEqual(sv["counts"]["closable"], 1)


if __name__ == "__main__":
    unittest.main()
