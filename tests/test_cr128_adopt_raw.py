"""CR-128: a raw transcript archived at delivery is adopted, not written again.

    python3 -m unittest discover -s tests
"""
import datetime
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "ops-base"))
sys.path.insert(0, str(ROOT / "skills" / "ops"))
import raw_archive as ra  # noqa: E402
import hygiene_check as hc  # noqa: E402

TS = ROOT / "skills" / "ops-base" / "raw_archive.py"


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


class Hardening(unittest.TestCase):
    def test_merged_find_by_either_id_and_append(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("capA", "one\n"), ("capB", "two\n")])
            raws = [v / ".transcripts" / "capA-raw.md", v / ".transcripts" / "capB-raw.md"]
            out = ra.adopt_merged(raws, "s", "a/s.md", ["a/s.md"])
            self.assertEqual(ra.find(v, None, "capA"), out)
            self.assertEqual(ra.find(v, None, "capB"), out)
            ra.adopt_one(ra.find(v, None, "capB"), "s2", "b/s2.md", ["b/s2.md"])
            self.assertEqual(len(list((v / ".transcripts").iterdir())), 1)

    def test_merged_bodies_byte_identical_incl_empty_and_substring(self):
        bodies = ["\nabc\n", "", "\nabc\n\n  tail \r\n"]
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("c1", "x"), ("c2", "x"), ("c3", "x")])
            raws = []
            for sid, b in zip(("c1", "c2", "c3"), bodies):
                p = v / ".transcripts" / f"{sid}-raw.md"
                p.write_text(raw(sid, "").rstrip("\n") + "\n" + b, encoding="utf-8", newline="")
                raws.append(p)
            out = ra.adopt_merged(raws, "m", "a/m.md", [])
            body = ra.split(out.read_text(encoding="utf-8", newline=""))[1]
            for b in bodies:
                self.assertIn(b, body)
            self.assertEqual(len(list((v / ".transcripts").iterdir())), 1)

    def test_merged_comparison_failure_keeps_originals(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("c1", "a\n"), ("c2", "b\n")])
            raws = [v / ".transcripts" / "c1-raw.md", v / ".transcripts" / "c2-raw.md"]
            real = ra.split
            calls = []

            def bad(text):
                fm, body = real(text)
                calls.append(1)
                return (fm, body + "!") if len(calls) == 3 else (fm, body)
            ra.split = bad
            try:
                with self.assertRaises(RuntimeError):
                    ra.adopt_merged(raws, "m", "a/m.md", [])
            finally:
                ra.split = real
            self.assertTrue(all(r.exists() for r in raws))
            self.assertFalse((v / ".transcripts" / "m-raw.md").exists())

    def test_frontmatter_at_eof_and_crlf(self):
        self.assertEqual(ra.split("---\na: 1\n---")[0], "a: 1")
        fm, body = ra.split("---\r\na: 1\r\nb: 2\r\n---\r\nbody\r\n")
        self.assertEqual((fm, body), ("a: 1\nb: 2", "body\r\n"))
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x-raw.md"
            p.write_text(raw("x", "").rstrip("\n").replace("\n", "\r\n"), encoding="utf-8", newline="")
            out = ra.adopt_one(p, "stem", "a/stem.md", ["a/stem.md"])
            text = out.read_text(encoding="utf-8", newline="")
            self.assertNotIn("\r\n\n", text)
            self.assertTrue(text.startswith("---\r\n"))
            self.assertEqual(ra.get(ra.split(text)[0], "summary"), "a/stem.md")

    def test_yaml_special_paths_quoted_and_read_back(self):
        weird = "_contacts/åsa/260101-summary: plan # v2.md"
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("cap1", "x")])
            out = ra.adopt_one(ra.find(v, None, "cap1"), "261002-summary-Åsa-Örjan", weird, [weird], "ok: yes")
            text = out.read_text(encoding="utf-8")
            try:
                import yaml
                data = yaml.safe_load(ra.split(text)[0])
                self.assertEqual(data["summary"], weird)
                self.assertEqual(data["created_files"], [weird])
                self.assertEqual(data["disposition"], "ok: yes")
            except ImportError:
                pass
            fm = ra.split(text)[0]
            self.assertEqual(ra.get(fm, "summary"), weird)
            self.assertEqual(ra._items(fm, "summaries"), [weird])
            self.assertEqual(out.name, "261002-summary-Åsa-Örjan-raw.md")

    def test_pending_forms(self):
        for v in ("", '""', "''", "null", "~", "# not filed yet"):
            self.assertTrue(ra.is_pending(f"summary: {v}\nx: 1"), v)
        self.assertFalse(ra.is_pending("summary: a/b.md"))
        self.assertFalse(ra.is_pending(None))

    def test_no_external_id_fallback(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("cap9", "x")])
            (v / "_inbox" / "item.md").write_text("---\nexternal_id: cap9\n---\n", encoding="utf-8")
            self.assertIsNone(ra.find(v, "_inbox/item.md"))
            (v / "_inbox" / "item.md").write_text("---\nsource_id: cap9\n---\n", encoding="utf-8")
            self.assertEqual(ra.find(v, "_inbox/item.md").name, "cap9-raw.md")


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        import subprocess
        return subprocess.run([sys.executable, str(TS), *args], capture_output=True, text=True)

    def test_adopt_single_and_nothing_pending(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("cap1", "hej\n")])
            r = self.run_cli("adopt", str(v), "261003-summary-Åke", "--summary", "a/s.md",
                             "--created", "a/s.md", "--inbox", "_inbox/cap1.md")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((v / ".transcripts" / "261003-summary-Åke-raw.md").exists())
            r = self.run_cli("adopt", str(v), "x", "--summary", "a/x.md", "--source-id", "unknown")
            self.assertEqual(r.returncode, 1)
            self.assertIn("nothing pending", r.stdout)
            self.assertEqual(len(list((v / ".transcripts").iterdir())), 1)

    def test_mixed_adopted_and_pending(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [("old", "first\n"), ("new", "second\n")])
            ra.adopt_one(ra.find(v, None, "old"), "s1", "a/s1.md", ["a/s1.md"])
            r = self.run_cli("adopt", str(v), "s2", "--summary", "b/s2.md", "--created", "b/s2.md",
                             "--source-id", "old", "--source-id", "new")
            self.assertEqual(r.returncode, 0, r.stderr)
            names = sorted(p.name for p in (v / ".transcripts").iterdir())
            self.assertEqual(names, ["s1-raw.md", "s2-raw.md"])
            fm1 = ra.split((v / ".transcripts" / "s1-raw.md").read_text(encoding="utf-8"))[0]
            self.assertEqual(ra._items(fm1, "summaries"), ["a/s1.md", "b/s2.md"])
            fm2 = ra.split((v / ".transcripts" / "s2-raw.md").read_text(encoding="utf-8"))[0]
            self.assertEqual(ra._items(fm2, "summaries"), ["b/s2.md"])


class CheckMore(unittest.TestCase):
    def test_variants_and_dates(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [])
            d = v / ".transcripts"
            (d / "q-raw.md").write_text(raw("q", "x", summary='""'), encoding="utf-8")
            (d / "nodate-raw.md").write_text(raw("nodate", "x", date="").replace("date: ", "date:"),
                                             encoding="utf-8")
            (d / "baddate-raw.md").write_text(raw("baddate", "x", date="99xx99"), encoding="utf-8")
            (d / "eof-raw.md").write_text(raw("eof", "").rstrip("\n").split("\n---\n")[0] + "\n---",
                                          encoding="utf-8")
            old = datetime.datetime(2026, 9, 1).timestamp()
            for p in d.iterdir():
                os.utime(p, (old, old))
            found = hc.check_raw(v, today=datetime.date(2026, 10, 21))
            files = sorted(f["file"] for f in found)
            self.assertIn(".transcripts/nodate-raw.md", files)
            self.assertIn(".transcripts/baddate-raw.md", files)
            self.assertIn(".transcripts/q-raw.md", files)

    def test_only_head_is_read(self):
        with tempfile.TemporaryDirectory() as t:
            v = setup(t, [])
            p = v / ".transcripts" / "big-raw.md"
            p.write_text(raw("big", "x" * 300000, date="260101"), encoding="utf-8")
            reads = []
            real = open

            def spy(f, *a, **k):
                h = real(f, *a, **k)
                if str(f).endswith("big-raw.md"):
                    orig = h.read
                    h.read = lambda n=-1: (reads.append(n), orig(n))[1]
                return h
            import builtins
            builtins.open = spy
            try:
                found = hc.check_raw(v, today=datetime.date(2026, 10, 21))
            finally:
                builtins.open = real
            self.assertEqual(len(found), 1)
            self.assertTrue(reads and all(n != -1 and n <= ra.HEAD_BYTES for n in reads))


if __name__ == "__main__":
    unittest.main()
