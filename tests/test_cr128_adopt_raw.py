"""CR-128: a raw transcript archived at delivery is adopted, not written again.

    python3 -m unittest discover -s tests
"""
import datetime
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "ops-base"))
sys.path.insert(0, str(ROOT / "skills" / "ops"))
import raw_archive as ra  # noqa: E402
import hygiene_check as hc  # noqa: E402


def raw(sid, body, date="261001", summary=""):
    return (f"---\ntype: raw-transcript\ndate: {date}\nsource: deep-thought\nsource_id: {sid}\n"
            f"source_file: {sid}.m4a\nduration: 60\nvariant: text\nsummary: {summary}\nsummaries: []\n"
            f"disposition: pending -- archived by a client\ncreated_files: []\n"
            f"inbox: _inbox/{sid}.md\nwritten_by: record-me-mac\n---\n\n{body}")


def setup(tmp, ids_bodies):
    v = Path(tmp)
    (v / ".transcripts").mkdir()
    (v / "_inbox").mkdir()
    for sid, body in ids_bodies:
        (v / ".transcripts" / f"{sid}-raw.md").write_text(raw(sid, body), encoding="utf-8")
        (v / "_inbox" / f"{sid}.md").write_text(
            f"---\nid: {sid}\nstatus: pending\nraw_transcript: .transcripts/{sid}-raw.md\n---\n", encoding="utf-8")
    return v


class Adopt(unittest.TestCase):
    def test_single_renamed_filled_body_identical(self):
        body = "Anna: hej.\n\n  Bo: tjena  \n"
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("cap1", body)])
            f = ra.find(v, "_inbox/cap1.md")
            out = ra.adopt_one(f, "261002-summary-Anna-Bo-plan", "_contacts/x/261002-summary-Anna-Bo-plan.md",
                               ["_contacts/x/261002-summary-Anna-Bo-plan.md"], "one session")
            self.assertEqual(out.name, "261002-summary-Anna-Bo-plan-raw.md")
            self.assertEqual([p.name for p in (v / ".transcripts").iterdir()], [out.name])
            fm, b = ra.split(out.read_text(encoding="utf-8"))
            self.assertEqual(b, "\n" + body)
            self.assertEqual(ra.get(fm, "written_by"), "record-me-mac")
            self.assertEqual(ra.get(fm, "source_id"), "cap1")
            self.assertTrue(ra.get(fm, "summary").endswith("plan.md"))
            self.assertEqual(len(ra._items(fm, "summaries")), 1)

    def test_find_by_source_id_without_pointer(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("cap2", "x")])
            self.assertEqual(ra.find(v, None, "cap2").name, "cap2-raw.md")
            self.assertIsNone(ra.find(v, None, "nope"))

    def test_merged_two_originals_gone(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("capA", "first body\n"), ("capB", "second body\n")])
            raws = [v / ".transcripts" / "capA-raw.md", v / ".transcripts" / "capB-raw.md"]
            out = ra.adopt_merged(raws, "261002-summary-merged", "a/261002-summary-merged.md", ["a/b.md"])
            self.assertEqual([p.name for p in (v / ".transcripts").iterdir()], [out.name])
            text = out.read_text(encoding="utf-8")
            self.assertIn("\nfirst body\n", text)
            self.assertIn("\nsecond body\n", text)
            self.assertIn("capA, capB", text)

    def test_second_summary_appends_without_rename(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("cap3", "body\n")])
            out = ra.adopt_one(ra.find(v, None, "cap3"), "s1", "a/s1.md", ["a/s1.md"])
            again = ra.adopt_one(out, "s2", "b/s2.md", ["b/s2.md"])
            self.assertEqual(again, out)
            fm, _ = ra.split(out.read_text(encoding="utf-8"))
            self.assertEqual(ra._items(fm, "summaries"), ["a/s1.md", "b/s2.md"])
            self.assertEqual(ra._items(fm, "created_files"), ["a/s1.md", "b/s2.md"])

    def test_nothing_pending_returns_none(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / ".transcripts").mkdir()
            self.assertIsNone(ra.find(t, None, "pasted"))


class Check(unittest.TestCase):
    def test_old_pending_listed_young_and_filed_not(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("old", "x"), ("young", "x")])
            (v / ".transcripts" / "old-raw.md").write_text(raw("old", "x", date="261001"), encoding="utf-8")
            (v / ".transcripts" / "young-raw.md").write_text(raw("young", "x", date="261015"), encoding="utf-8")
            (v / ".transcripts" / "filed-raw.md").write_text(
                raw("filed", "x", date="260901", summary="a/s.md"), encoding="utf-8")
            found = hc.check_raw(v, today=datetime.date(2026, 10, 21))
            self.assertEqual([f["file"] for f in found], [".transcripts/old-raw.md"])
            self.assertIn("_inbox/old.md", found[0]["message"])
            self.assertIn("20 days", found[0]["message"])


if __name__ == "__main__":
    unittest.main()
