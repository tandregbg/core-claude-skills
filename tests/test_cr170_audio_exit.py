"""CR-170: audio has an exit, and the verification that makes removal defensible.

`audio_transcript_pairing` said where audio IS and nothing about where it GOES, so the
folder only ever grew: one vault reached 64 files and 1.6 GB in 14 days after a retired
watcher was replaced and nothing took over the exit. The pairing rule alone is satisfied
by any new capture tool on its first day, which is why the failure is available to any
suite that swaps capture tools.

The verification method is part of the proposal and is tested here as code, because it is
the part that decides whether a file may be deleted. Of 64 measured pairs, 37 existed in
the archive and NONE was byte-identical -- container timestamps differ -- while 64 of 64
matched on `mdat`. These tests build that situation on disk rather than describing it.

    python3 -m unittest discover -s tests
"""
import importlib.util
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOC = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
VC = DOC["vault_conventions"]
CONVENTIONS = {c["id"]: c for c in VC["conventions"]}
ROOTS = {e["path"]: e for e in VC["vault_root"] if isinstance(e, dict) and "path" in e}
INBOX_SKILL = (ROOT / "skills" / "inbox" / "SKILL.md").read_text(encoding="utf-8")
OPS_SKILL = (ROOT / "skills" / "ops" / "SKILL.md").read_text(encoding="utf-8")
SCHEMA = (ROOT / "docs" / "schemas" / "inbox.md").read_text(encoding="utf-8")
TOOL = ROOT / "skills" / "inbox" / "audio_verify.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("audio_verify", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AV = load_tool()


def box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload) + 8) + kind + payload


def m4a(sound: bytes, tail: bytes = b"A") -> bytes:
    """An ISO-BMFF file: same sound, different container metadata per `tail`."""
    return (box(b"ftyp", b"M4A isom")
            + box(b"mdat", sound)
            + box(b"moov", b"\x00" * 32 + b"muxed-at-" + tail))


def flat(text):
    return " ".join(text.split())


class TheConventionHasADispositionHalf(unittest.TestCase):
    def test_the_pairing_rule_still_says_what_it_said(self):
        rule = CONVENTIONS["audio_transcript_pairing"]["rule"]
        self.assertIn("paired by basename", rule)
        self.assertIn("Tools that rename one must rename the other", rule)
        self.assertEqual(CONVENTIONS["audio_transcript_pairing"]["level"], "invariant")

    def test_routed_audio_leaves_the_inbox(self):
        rule = flat(CONVENTIONS["audio_transcript_pairing"]["rule"])
        self.assertIn("the audio LEAVES the inbox", rule)
        self.assertIn("the inbox is not it", rule)

    def test_the_destination_is_declared_and_has_a_default(self):
        self.assertIn("audio_archive", ROOTS["_inbox/.audio/"])
        self.assertEqual(ROOTS["_inbox/.audio/"]["audio_archive"], ".archive/.audio/")
        self.assertNotIn("_inbox", ROOTS["_inbox/.audio/"]["audio_archive"],
                         "the inbox may not be the audio's destination")

    def test_the_entry_no_longer_promises_indefinite_storage(self):
        life = ROOTS["_inbox/.audio/"]["lifecycle"]
        self.assertIn("IN TRANSIT", life)
        self.assertNotIn("kept indefinitely by default;", life)


class ThePointerTravelsWithTheFile(unittest.TestCase):
    def test_all_three_pointer_fields_are_in_the_schema(self):
        for field in ("audio_path", "audio_path_was", "audio_archived"):
            self.assertIn(field, SCHEMA)

    def test_the_convention_names_the_same_three(self):
        rule = CONVENTIONS["audio_transcript_pairing"]["rule"]
        for field in ("audio_path", "audio_path_was", "audio_archived"):
            self.assertIn(field, rule)

    def test_the_reason_is_recorded_not_just_the_fields(self):
        # An archive whose filenames cannot be resolved back to a conversation is a heap.
        self.assertIn("is a heap", flat(CONVENTIONS["audio_transcript_pairing"]["rule"]))

    def test_the_skill_updates_the_pointers_where_it_archives(self):
        self.assertIn("audio_path_was", INBOX_SKILL)
        self.assertIn("audio_archived", INBOX_SKILL)


class TheVerificationIsOnSoundNotOnBytes(unittest.TestCase):
    """The measured situation, rebuilt: same sound, different container."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        sound = b"THE SAME RECORDING " * 64
        (self.d / "a.m4a").write_bytes(m4a(sound, b"A"))
        (self.d / "b.m4a").write_bytes(m4a(sound, b"B-longer-tail"))
        (self.d / "other.m4a").write_bytes(m4a(b"A DIFFERENT RECORDING " * 64))

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_two_files_really_are_not_byte_identical(self):
        # If they were, the test would prove nothing about the method.
        self.assertNotEqual((self.d / "a.m4a").read_bytes(), (self.d / "b.m4a").read_bytes())

    def test_same_sound_different_container_verifies(self):
        r = AV.verify(self.d / "a.m4a", self.d / "b.m4a")
        self.assertTrue(r["verified"])
        self.assertEqual(r["basis"], "mdat")
        self.assertFalse(r["bytes_identical"])

    def test_different_sound_does_not_verify(self):
        r = AV.verify(self.d / "a.m4a", self.d / "other.m4a")
        self.assertFalse(r["verified"])

    def test_a_byte_compare_would_have_rejected_a_true_pair(self):
        # The point of the whole method, asserted rather than claimed.
        self.assertFalse(AV.verify(self.d / "a.m4a", self.d / "b.m4a")["bytes_identical"])
        self.assertTrue(AV.verify(self.d / "a.m4a", self.d / "b.m4a")["verified"])

    def test_the_hash_covers_every_mdat_in_order(self):
        sound = b"ONE " * 16, b"TWO " * 16
        multi = (box(b"ftyp", b"M4A isom") + box(b"mdat", sound[0]) + box(b"mdat", sound[1]))
        single = box(b"ftyp", b"M4A isom") + box(b"mdat", sound[0] + sound[1])
        (self.d / "multi.m4a").write_bytes(multi)
        (self.d / "single.m4a").write_bytes(single)
        self.assertEqual(AV.content_hash(self.d / "multi.m4a")[0],
                         AV.content_hash(self.d / "single.m4a")[0])

    def test_a_file_with_no_mdat_says_which_basis_it_used(self):
        (self.d / "plain.wav").write_bytes(b"RIFF....WAVEfmt not iso-bmff at all")
        h, basis = AV.content_hash(self.d / "plain.wav")
        self.assertEqual(basis, "whole-file")
        # And a mixed-basis comparison must not silently pass.
        self.assertFalse(AV.verify(self.d / "plain.wav", self.d / "a.m4a")["verified"])

    def test_a_truncated_file_does_not_raise(self):
        (self.d / "cut.m4a").write_bytes(m4a(b"SOUND" * 40)[:60])
        AV.content_hash(self.d / "cut.m4a")          # must not raise


class TheToolReportsAndNeverRemoves(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        self.inbox = self.d / "audio"
        self.archive = self.d / "archive"
        self.inbox.mkdir()
        self.archive.mkdir()
        sound = b"MEETING " * 64
        (self.inbox / "261029-100234.m4a").write_bytes(m4a(sound, b"A"))
        (self.archive / "261029-100234.m4a").write_bytes(m4a(sound, b"B-remuxed"))
        (self.inbox / "261030-090000.m4a").write_bytes(m4a(b"ONLY COPY " * 64))

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, *args):
        r = subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)
        return r.stdout + r.stderr

    def test_a_pair_verifies_and_a_lone_file_is_named_as_such(self):
        out = self.run_tool("--dir", str(self.inbox), "--against", str(self.archive))
        self.assertIn("[VERIFIED] 261029-100234.m4a", out)
        self.assertIn("bytes differ, sound does not", out)
        self.assertIn("[NO COUNTERPART] 261030-090000.m4a", out)

    def test_nothing_is_removed(self):
        before = sorted(p.name for p in self.inbox.iterdir())
        self.run_tool("--dir", str(self.inbox), "--against", str(self.archive))
        self.assertEqual(sorted(p.name for p in self.inbox.iterdir()), before)
        self.assertIn("Nothing was removed",
                      self.run_tool("--dir", str(self.inbox), "--against", str(self.archive)))

    def test_the_only_copy_case_is_the_one_a_naive_sweep_would_delete(self):
        # 27 of 64 measured files existed only in the vault, 8 of them meeting recordings.
        out = self.run_tool("--dir", str(self.inbox), "--against", str(self.archive))
        self.assertIn("1 without a counterpart", out)


class TheCheckCountsTheDefect(unittest.TestCase):
    def test_check_reports_audio_whose_entry_is_archived(self):
        self.assertIn("Audio whose entry is already archived", OPS_SKILL)

    def test_the_offered_action_is_a_verification_first(self):
        self.assertIn("audio_verify.py", OPS_SKILL)
        self.assertIn("compares `mdat` payloads rather than bytes", flat(OPS_SKILL))

    def test_the_only_copy_warning_survives_into_the_check(self):
        self.assertIn("the only copy", flat(OPS_SKILL))


if __name__ == "__main__":
    unittest.main()
