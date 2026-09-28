"""CR-103: filing what was never sent -- the deterministic plan behind `close --all-resolved`.

Invented data only. The helper plans; it never moves, writes or deletes.
"""

import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OUTBOX_SKILL = Path(__file__).resolve().parent.parent / "skills" / "outbox"
sys.path.insert(0, str(OUTBOX_SKILL))
import resolved as rs  # noqa: E402

TODAY = datetime.date(2026, 10, 1)


def manifest(status: str, note: str | None = None, contact: str = "Bob (Acme)",
             outcome: str = "*(filled in when sent)*") -> str:
    lines = ["# Outbox -- test", "", f"**Status:** {status}"]
    if note is not None:
        lines.append(f"**Statusnot:** {note}")
    lines += [f"**Kontakt:** {contact}", "**Kanal:** mejl", "",
              "## Utfall", "", outcome, ""]
    return "\n".join(lines)


class Plan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        self.outbox = self.vault / "_outbox"
        self.outbox.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def item(self, name: str, text: str) -> Path:
        folder = self.outbox / name
        folder.mkdir()
        (folder / "_manifest.md").write_text(text, encoding="utf-8")
        (folder / "reply.md").write_text("body", encoding="utf-8")
        return folder

    def snapshot(self) -> dict:
        return {str(p.relative_to(self.vault)): p.read_bytes()
                for p in self.vault.rglob("*") if p.is_file()}

    def run_plan(self) -> dict:
        return rs.plan(self.vault, self.outbox, TODAY)

    def test_the_two_item_acceptance_case(self):
        self.item("260928-contact_offer",
                  manifest("avskriven 2026-09-28",
                           "ersatt av 260928-contact_offer-revised (skickad 2026-09-28); first draft"))
        self.item("260928-contact_offer-revised", manifest("skickad 2026-09-28", "sent by mail"))
        before = self.snapshot()
        result = self.run_plan()
        self.assertEqual(self.snapshot(), before, "planning must not touch a file")

        [draft] = result["resolved"]
        self.assertEqual(draft["kind"], "superseded")
        self.assertEqual(draft["replaced_by"], "260928-contact_offer-revised")
        self.assertEqual(draft["replacing"]["where"], "_outbox")
        self.assertEqual(draft["archive_subdir"], ".archive/260928-offer-superseded")
        self.assertEqual(draft["outcome"], "Ersatt av 260928-contact_offer-revised (skickad 2026-09-28)")
        self.assertEqual(draft["timeline_line_for_replacing"],
                         "- 2026-10-01: Ersätter 260928-contact_offer (avskriven 2026-09-28)")
        self.assertEqual(draft["problems"], [])
        self.assertEqual(result["counts"]["superseded"], 1)

    def test_a_withdrawn_item_without_the_form_closes_as_today(self):
        self.item("260920-person-d_recap",
                  manifest("avskriven 2026-09-21", "tas muntligt vid nästa samtal"))
        [entry] = self.run_plan()["resolved"]
        self.assertEqual(entry["kind"], "withdrawn")
        self.assertNotIn("archive_subdir", entry)
        self.assertEqual(entry["outcome"], "Skickades inte: tas muntligt vid nästa samtal")

    def test_a_missing_replacing_item_is_reported_not_guessed(self):
        self.item("260928-contact_offer",
                  manifest("avskriven 2026-09-28", "ersatt av 260928-person-e_nowhere"))
        [entry] = self.run_plan()["resolved"]
        self.assertEqual(entry["kind"], "withdrawn")
        self.assertFalse(entry["replacing"]["found"])
        self.assertTrue(any("260928-person-e_nowhere" in p for p in entry["problems"]))

    def test_a_replacing_item_already_closed_is_found_by_its_recorded_origin(self):
        self.item("260928-contact_offer",
                  manifest("avskriven 2026-09-28", "ersatt av 260928-contact_offer-revised"))
        closed = self.vault / "_contacts" / "bob" / "260928-offer-revised"
        closed.mkdir(parents=True)
        (closed / "_manifest.md").write_text(
            manifest("arkiverad 2026-09-30") + "\n## Tidslinje\n\n- 2026-09-30: stängd från "
            "`_outbox/260928-contact_offer-revised`\n", encoding="utf-8")
        [entry] = self.run_plan()["resolved"]
        self.assertEqual(entry["kind"], "superseded")
        self.assertEqual(entry["replacing"]["where"], "closed")
        self.assertIn("arkiverad 2026-09-30", entry["outcome"])

    def test_undeclared_status_names_the_closest_declared_one(self):
        self.item("260928-person-a_note", manifest("redo att skicka"))
        self.item("260928-person-a_other", manifest("klar-att-skicka"))
        self.item("260928-person-a_mail", manifest("utkast -- ligger i Mail"))
        [u] = self.run_plan()["undeclared_status"]
        self.assertEqual(u["item"], "260928-person-a_note")
        self.assertEqual(u["closest"], "klar-att-skicka")

    def test_an_undeclared_word_with_no_likely_meaning_gets_no_guess(self):
        self.item("260928-person-f_x", manifest("blockerad"))
        [u] = self.run_plan()["undeclared_status"]
        self.assertIsNone(u["closest"])

    def test_no_note_and_no_outcome_is_a_problem(self):
        self.item("260928-person-f_y", manifest("avskriven 2026-09-28"))
        [entry] = self.run_plan()["resolved"]
        self.assertTrue(any("cannot say why" in p for p in entry["problems"]))

    def test_an_existing_outcome_is_not_replaced(self):
        self.item("260928-person-f_z", manifest("avskriven 2026-09-28", "no longer needed",
                                           outcome="Beslut: tas i nästa möte."))
        [entry] = self.run_plan()["resolved"]
        self.assertTrue(entry["outcome_present"])
        self.assertNotIn("outcome", entry)


class Parsing(unittest.TestCase):
    def test_the_note_form_with_backticks_and_trailing_text(self):
        m = rs.SUPERSEDED_NOTE.match("ersatt av `260928-person-d_reply-v2`; kept for the record")
        self.assertEqual(m.group(1), "260928-person-d_reply-v2")

    def test_a_note_that_merely_mentions_it_is_not_the_form(self):
        self.assertIsNone(rs.SUPERSEDED_NOTE.match("sent after 260928-person-d_reply was ersatt av x"))

    def test_status_kinds(self):
        self.assertEqual(rs.status_kind("skickad 2026-09-28"), "sent")
        self.assertEqual(rs.status_kind("avskriven 2026-09-28"), "withdrawn")
        self.assertEqual(rs.status_kind("draft"), "draft")
        self.assertIsNone(rs.status_kind("skickadx"))
        # A hand edit sometimes bolds the value; it is still the declared word.
        self.assertEqual(rs.status_kind("**skickad 2026-09-28**"), "sent")
        self.assertEqual(rs.closest_declared("obsolet"), "avskriven")

    def test_subject(self):
        self.assertEqual(rs.subject_of("260928-contact_offer-revised"), "offer-revised")
        self.assertEqual(rs.subject_of("260928-weekly-recap"), "weekly-recap")


class Cli(unittest.TestCase):
    def test_json_and_text_from_the_command_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            item = vault / "_outbox" / "260928-contact_offer"
            item.mkdir(parents=True)
            (item / "_manifest.md").write_text(manifest("redo att skicka"), encoding="utf-8")
            script = str(OUTBOX_SKILL / "resolved.py")
            out = subprocess.run([sys.executable, script, "--vault", tmp, "--today", "2026-10-01"],
                                 capture_output=True, text=True, check=True).stdout
            self.assertEqual(json.loads(out)["undeclared_status"][0]["closest"], "klar-att-skicka")
            text = subprocess.run([sys.executable, script, "--vault", tmp, "--text"],
                                  capture_output=True, text=True, check=True).stdout
            self.assertIn("UNDECLARED STATUS", text)


if __name__ == "__main__":
    unittest.main()
