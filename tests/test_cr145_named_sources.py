"""CR-145: a failed or missing source is named in the output, and direct messages
can be declared. Invented data.

Four proposals, each with a measured failure behind it: one-to-one replies the archive
could not see, a fetch that failed for a morning while the sections below read as
current, two recordings of one meeting with nothing saying which was the source, and a
recording store a check reported as never looked at.

Every assertion here is about OUTPUT a reader sees -- a line of the agenda, a row of
the pre-flight table, a record a caller receives. None of them reads the implementation's
source text, and none of them asserts only the shape of a warning: the three failures the
earlier waves shipped were tests green against wrong code for exactly those reasons.

    python3 -m unittest discover -s tests
"""

import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OPS = Path(__file__).resolve().parents[1] / "skills" / "ops"
sys.path.insert(0, str(OPS))
import build_agenda as ba  # noqa: E402

NOTE_DAY = "260922"
NOTE_DATE = datetime.date(2026, 9, 22)
BUILD_DAY = "260923"
AFTER = datetime.date(2026, 9, 23)
# `people:` sits at the document root, beside `external_systems:` -- that is where
# `config()` reads it, and a roster nested under `carry_forward` would resolve to
# nothing and make every roster assertion below vacuously green.
PEOPLE = "people:\n  - name: Ravi Mehta\n    aliases: [Ravee]\n  - name: Bob\n"
BASE = ("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n") + PEOPLE
# *Built from* (CR-117) is the CARD's head block, so the tests that assert it declare the
# card layout. `milestone:` comes with it: a card without one is a config finding, and a
# finding line in the head block is not what these tests are reading.
CARD_KEYS = "      layout: card\n"
MILESTONE = "milestone:\n  name: Rollout\n  date: 2026-10-15\n"


def as_card(cfg: str) -> str:
    return cfg.replace("      enabled: true\n", "      enabled: true\n" + CARD_KEYS) + MILESTONE
ITEMS = "- **Payment retry** — #12 · **Bob**\n"


def vault(ops_yaml: str, chats: dict[str, dict] | None = None,
          fetch: dict | None = None, transcripts: list[dict] | None = None):
    """A venture with one project, optionally a chat archive and a recording archive.

    `chats` maps a platform id to {"name": folder, "messages": {date: text}}; the archive
    is written the way the archiver writes it (CR-047), so the id match the reader performs
    is the real one and not a stub.
    """
    venture = Path(tempfile.mkdtemp()) / "venture"
    meetings = venture / "proj" / "meetings"
    meetings.mkdir(parents=True)
    (venture / "proj" / "_ops.yaml").write_text(ops_yaml, encoding="utf-8")
    (meetings / f"{NOTE_DAY}-daily-standup.md").write_text(
        f"# Standup\n\n## Carried forward\n\n{ITEMS}", encoding="utf-8")
    if chats is not None:
        root = venture / ".teamschats"
        for cid, spec in chats.items():
            d = root / spec["name"]
            d.mkdir(parents=True)
            (d / "_chat.json").write_text(json.dumps({"chat_id": cid}), encoding="utf-8")
            for day, text in (spec.get("messages") or {}).items():
                (d / f"{day}.md").write_text(text, encoding="utf-8")
        root.mkdir(parents=True, exist_ok=True)
        (root / "_fetch.json").write_text(json.dumps(
            fetch or {"result": "ok", "last_success": "2026-09-23T06:30:00+02:00",
                      "last_attempt": "2026-09-23T06:30:00+02:00"}), encoding="utf-8")
    if transcripts is not None:
        d = venture / "proj" / ".recordings"
        d.mkdir(parents=True)
        (d / "store.json").write_text(json.dumps(transcripts), encoding="utf-8")
    return venture, meetings


def cf_of(meetings: Path) -> dict:
    return ba.config(meetings.resolve())


def build(meetings: Path, *extra) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(OPS / "build_agenda.py"),
                           "--dir", str(meetings), "--date", BUILD_DAY, *extra],
                          capture_output=True, text=True)


def agenda_text(meetings: Path) -> str:
    return (meetings / f"{BUILD_DAY}-agenda-daily-standup.md").read_text(encoding="utf-8")


def details_text(meetings: Path) -> str:
    return (meetings / f"{BUILD_DAY}-agenda-details-daily-standup.md").read_text(encoding="utf-8")


def check_rows(meetings: Path):
    cf = cf_of(meetings)
    hist = [(NOTE_DAY, meetings / f"{NOTE_DAY}-daily-standup.md")]
    return ba.check_rows(cf, meetings, hist, today=AFTER, reports=[])


# --------------------------------------------------------------- proposal 1
DIRECT_CFG = (BASE + "external_systems:\n  chats:\n"
              "    - id: \"group-1\"\n      name: \"Acme standup\"\n"
              "    - id: \"dm-1\"\n      name: \"1:1 thread\"\n"
              "      kind: direct\n      person: Ravee\n")
DIRECT_ARCHIVE = {
    "group-1": {"name": "acme-standup",
                "messages": {"2026-09-23": "### Bob 09:00\nretry is live\n"}},
    "dm-1": {"name": "dm-thread",
             "messages": {"2026-09-23": "### Ravi Mehta 10:15\nthe refund answer is yes\n"}},
}


class DirectChatRead(unittest.TestCase):
    """A `kind: direct` chat is read, and its REPLY reaches the digest source list."""

    def test_direct_reply_is_read_as_a_message(self):
        """The measured failure: the reply existed and nothing downstream could see it.

        So the assertion is the reply's own TEXT arriving in the record, not that a record
        exists -- an empty record for a declared direct chat is exactly the old behaviour.
        """
        _v, m = vault(DIRECT_CFG, chats=DIRECT_ARCHIVE)
        recs = ba.from_chat(cf_of(m), AFTER)
        direct = [c for c in recs if c["kind"] == "direct"]
        self.assertEqual(len(direct), 1, recs)
        said = " ".join(line for _d, line in direct[0]["messages"])
        self.assertIn("the refund answer is yes", said)
        self.assertEqual(direct[0]["person"], "Ravi Mehta",
                         "the alias `Ravee` resolves to the roster's own spelling")

    def test_group_chat_keeps_its_kind_and_name(self):
        """The default is unchanged: an entry declaring no kind is a group chat."""
        _v, m = vault(DIRECT_CFG, chats=DIRECT_ARCHIVE)
        recs = ba.from_chat(cf_of(m), AFTER)
        group = [c for c in recs if c["kind"] == "group"]
        self.assertEqual([c["name"] for c in group], ["Acme standup"])
        self.assertIsNone(group[0]["person"])

    def test_source_line_names_the_person_not_the_chat_title(self):
        """A reader needs to know WHOSE reply arrived. `1:1 thread` says nothing."""
        _v, m = vault(DIRECT_CFG, chats=DIRECT_ARCHIVE)
        self.assertEqual(build(m).returncode, 0)
        text = agenda_text(m)
        src = [l for l in text.splitlines() if l.startswith("  chat ")]
        self.assertTrue(any("direct: Ravi Mehta" in l for l in src), src)
        self.assertTrue(any("Acme standup" in l for l in src), src)

    def test_built_from_line_lists_the_direct_chat(self):
        """The acceptance bullet: a direct reply appears in the digest source list."""
        _v, m = vault(as_card(DIRECT_CFG), chats=DIRECT_ARCHIVE)
        self.assertEqual(build(m).returncode, 0)
        built = [l for l in agenda_text(m).splitlines() if "**Built from**" in l]
        self.assertEqual(len(built), 1, agenda_text(m))
        self.assertIn("direct: Ravi Mehta", built[0])
        self.assertNotIn("chat direct", built[0],
                         "a direct chat already carries its own word")

    def test_direct_messages_are_counted_in_the_digest_total(self):
        """Two messages in two chats is two messages to read, not one."""
        _v, m = vault(DIRECT_CFG, chats=DIRECT_ARCHIVE)
        r = build(m)
        self.assertIn("2 chat message(s)", r.stdout, r.stdout)
        self.assertIn("direct: Ravi Mehta: 1", r.stdout, r.stdout)

    def test_the_digest_marker_names_the_person_prepare_must_go_and_read(self):
        """`prepare` reads this marker to know where the traffic was. For a direct chat
        the answer is a person, which is the fact the operator relayed by hand."""
        _v, m = vault(DIRECT_CFG, chats=DIRECT_ARCHIVE)
        self.assertEqual(build(m).returncode, 0)
        marker = [l for l in agenda_text(m).splitlines() if "DIGEST:" in l]
        self.assertEqual(len(marker), 1, agenda_text(m))
        self.assertIn("direct: Ravi Mehta 1", marker[0])
        self.assertNotIn("1:1 thread", marker[0],
                         "a conversation title says nothing about whose reply is waiting")

    def test_unresolved_person_is_a_config_finding_and_the_chat_is_still_read(self):
        """A name no roster entry answers to must not cost the source."""
        cfg = DIRECT_CFG.replace("person: Ravee", "person: Cai")
        _v, m = vault(cfg, chats=DIRECT_ARCHIVE)
        findings = ba.config_checks(cf_of(m), [(NOTE_DAY, m / f"{NOTE_DAY}-daily-standup.md")],
                                    AFTER, None)
        self.assertTrue(any("person: Cai" in f and "no `people:` entry" in f for f in findings),
                        findings)
        recs = ba.from_chat(cf_of(m), AFTER)
        direct = [c for c in recs if c["kind"] == "direct"][0]
        self.assertTrue(direct["messages"], "the chat is read regardless of the name")
        self.assertEqual(direct["person"], "Cai", "the declared spelling is kept, not dropped")

    def test_direct_with_no_person_is_a_config_finding(self):
        cfg = DIRECT_CFG.replace("      kind: direct\n      person: Ravee\n", "      kind: direct\n")
        _v, m = vault(cfg, chats=DIRECT_ARCHIVE)
        findings = ba.config_checks(cf_of(m), [(NOTE_DAY, m / f"{NOTE_DAY}-daily-standup.md")],
                                    AFTER, None)
        self.assertTrue(any("no `person:`" in f for f in findings), findings)

    def test_unknown_kind_reads_as_group_and_is_reported(self):
        """A kind nobody implemented must not turn a declared chat into an unread one."""
        cfg = DIRECT_CFG.replace("kind: direct", "kind: broadcast")
        _v, m = vault(cfg, chats=DIRECT_ARCHIVE)
        recs = ba.from_chat(cf_of(m), AFTER)
        odd = [c for c in recs if c["name"] == "1:1 thread"][0]
        self.assertEqual(odd["kind"], "group")
        self.assertTrue(odd["messages"], "still read")
        findings = ba.config_checks(cf_of(m), [(NOTE_DAY, m / f"{NOTE_DAY}-daily-standup.md")],
                                    AFTER, None)
        self.assertTrue(any("kind: broadcast" in f for f in findings), findings)

    def test_a_direct_chat_that_was_not_read_names_the_person(self):
        """The NOT-READ line, which is the one a reader sees when the source failed.

        Defect pass: every other place the kind reaches the output was covered, and this
        one was not -- the line that says a declared chat could not be read still printed
        the conversation TITLE. That is the worst place to lose the name: the operator is
        being told a reply did not arrive, and `1:1 thread` does not say whose. The direct
        chat is declared and absent from the archive, so `problem` is set and no messages
        are read.
        """
        _v, m = vault(DIRECT_CFG, chats={"group-1": DIRECT_ARCHIVE["group-1"]})
        r = build(m)
        self.assertEqual(r.returncode, 0, r.stderr)
        unread = [l for l in r.stdout.splitlines() if "chat not read" in l]
        self.assertEqual(len(unread), 1, r.stdout)
        self.assertIn("direct: Ravi Mehta", unread[0], unread[0])
        self.assertNotIn("1:1 thread", unread[0],
                         "a conversation title does not say whose reply failed to arrive")


# --------------------------------------------------------------- proposal 2
FAILED_FETCH = {"result": "auth_required",
                "last_success": "2026-09-21T06:30:00+02:00",
                "last_attempt": "2026-09-23T06:30:00+02:00"}
PLAIN_CHAT_CFG = (BASE + "external_systems:\n  chats:\n"
                  "    - id: \"group-1\"\n      name: \"Acme standup\"\n")


class FailedFetchNamedInTheHeader(unittest.TestCase):
    """CR-140 already names a failed fetch in the header. CR-145's requirement is the
    part CR-140 left out: WHEN the data the reader is about to read is from."""

    def test_header_names_the_failure_and_the_age_of_what_is_left(self):
        _v, m = vault(PLAIN_CHAT_CFG, chats={"group-1": {"name": "acme-standup"}},
                      fetch=FAILED_FETCH)
        self.assertEqual(build(m).returncode, 0)
        warn = [l for l in agenda_text(m).splitlines() if "Fetch failed" in l]
        self.assertEqual(len(warn), 1, "one line about one fetch, never two")
        # The content, not the format: the last SUCCESS was 21 September, so that is the
        # day the sections below are reading. A line that named only the failure would
        # leave a reader with no way to judge whether to read on -- the measured failure.
        self.assertIn("260921", warn[0], warn[0])
        self.assertIn("data is from", warn[0], warn[0])
        self.assertIn("login required", warn[0], warn[0])

    def test_a_record_with_no_success_says_so_rather_than_implying_a_time(self):
        _v, m = vault(PLAIN_CHAT_CFG, chats={"group-1": {"name": "acme-standup"}},
                      fetch={"result": "error", "detail": "token rejected",
                             "last_attempt": "2026-09-23T06:30:00+02:00"})
        self.assertEqual(build(m).returncode, 0)
        warn = [l for l in agenda_text(m).splitlines() if "Fetch failed" in l]
        self.assertEqual(len(warn), 1)
        self.assertIn("no successful fetch on record", warn[0], warn[0])
        self.assertNotIn("data is from", warn[0], warn[0])

    def test_a_successful_fetch_puts_no_warning_in_the_header(self):
        _v, m = vault(PLAIN_CHAT_CFG, chats={"group-1": {"name": "acme-standup"}})
        self.assertEqual(build(m).returncode, 0)
        self.assertNotIn("Fetch failed", agenda_text(m))


# --------------------------------------------------------------- proposals 3 and 4
TWO_RECORDINGS = [
    {"day": "2026-09-23", "id": "rec-own", "title": "Acme standup",
     "duration": "41:10", "variant": "speaker-1"},
    {"day": "2026-09-23", "id": "rec-notetaker", "title": "Acme standup",
     "duration": "38:02", "variant": "named-speakers"},
]
REC_CFG = (BASE + "external_systems:\n  transcripts:\n"
           "    store: \"a meeting store\"\n    match: [\"Acme standup\"]\n"
           "    archive: \".recordings\"\n    prefer: named-speakers\n")


class RecordingPreference(unittest.TestCase):
    """Two recordings of one meeting: one declared source, both listed."""

    def test_named_speakers_preference_chooses_the_shorter_named_recording(self):
        """The fixture is built so the two orders DISAGREE: the named-speaker recording
        is the SHORTER one, so a preference that is ignored (or a default fallback to
        longest) picks the other. A fixture whose data cannot distinguish the orders it
        claims to assert is the third failure the earlier waves shipped."""
        chosen = ba.choose_recordings(TWO_RECORDINGS, "named-speakers")
        used = [r["id"] for r in chosen if r.get("used")]
        self.assertEqual(used, ["rec-notetaker"])

    def test_no_preference_falls_back_to_the_longest(self):
        chosen = ba.choose_recordings(TWO_RECORDINGS, ba.RECORDING_DEFAULT_PREFERENCE)
        self.assertEqual([r["id"] for r in chosen if r.get("used")], ["rec-own"])

    def test_both_recordings_are_listed_one_marked_used(self):
        """The acceptance bullet. Silently dropping the second is the failure."""
        chosen = ba.choose_recordings(TWO_RECORDINGS, "named-speakers")
        self.assertEqual(len(chosen), 2, "nothing is removed")
        self.assertEqual(sorted(r.get("used", False) for r in chosen), [False, True])

    def test_a_variant_that_says_speakers_are_not_named_is_not_named(self):
        """Defect pass, and the one that could pick the WRONG recording.

        `named` was in the accepted word list and matching was by substring, so
        `unnamed-speakers`, `unnamed` and `renamed-v2` all reported named speakers. Each
        of those is a variant whose speakers are not named, or that says nothing about
        them, and `prefer: named-speakers` would have selected it. Asserted on
        `has_named_speakers` AND on the choice it drives, because reading the predicate
        right and still choosing wrong is the failure that matters.
        """
        for variant in ("unnamed-speakers", "unnamed", "renamed-v2", "un-named",
                        "not-named-speakers", "no named speakers", "speaker-1"):
            with self.subTest(variant=variant):
                self.assertFalse(ba.has_named_speakers({"variant": variant}),
                                 f"{variant} does not say the speakers are named")

    def test_the_spellings_that_do_say_named_speakers_still_count(self):
        """The fix must not cost the real spellings: the archiver owns them, and a
        variant carrying more than the phrase (`notetaker_named-speakers`) is still that
        archiver saying speakers are named."""
        for variant in ("named-speakers", "Named Speakers", "named speakers v2",
                        "speaker-names", "notetaker_named-speakers"):
            with self.subTest(variant=variant):
                self.assertTrue(ba.has_named_speakers({"variant": variant}), variant)

    def test_a_preference_never_selects_the_explicitly_unnamed_recording(self):
        """The defect's consequence, on the output. The unnamed recording is the LONGER
        one, so reporting it as named made it win on both keys of the order and the
        operator's declared preference selected its opposite."""
        recs = [{"day": "2026-09-23", "id": "rec-unnamed", "title": "Acme standup",
                 "duration": "55:00", "variant": "unnamed-speakers"},
                {"day": "2026-09-23", "id": "rec-notetaker", "title": "Acme standup",
                 "duration": "38:02", "variant": "named-speakers"}]
        chosen = ba.choose_recordings(recs, "named-speakers")
        self.assertEqual([r["id"] for r in chosen if r.get("used")], ["rec-notetaker"])

    def test_duration_is_read_in_the_spellings_an_archiver_writes(self):
        self.assertEqual(ba._duration_seconds("41:10"), 2470)
        self.assertEqual(ba._duration_seconds("1:02:00"), 3720)
        self.assertEqual(ba._duration_seconds("90"), 90)
        self.assertEqual(ba._duration_seconds("about an hour"), 0,
                         "unreadable sorts last, never first")

    def test_the_details_file_lists_both_recordings(self):
        """On the card layout the list belongs in the companion details file."""
        _v, m = vault(as_card(REC_CFG), transcripts=TWO_RECORDINGS)
        r = build(m, "--skip-unprocessed")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = details_text(m)
        self.assertIn("rec-notetaker", d)
        self.assertIn("rec-own", d)
        self.assertIn("named-speakers", d)
        used_row = [l for l in d.splitlines() if "rec-notetaker" in l and l.startswith("|")]
        other_row = [l for l in d.splitlines() if "rec-own" in l and l.startswith("|")]
        self.assertTrue(used_row and "**used**" in used_row[0], used_row)
        self.assertTrue(other_row and "not used" in other_row[0], other_row)
        self.assertNotIn("rec-notetaker", agenda_text(m),
                         "which capture a transcript came from is detail, not card content")

    def test_the_stop_message_names_the_source_and_the_other_recording(self):
        """Without --skip-unprocessed the build stops; that message is the first place
        the caller learns which recording to process."""
        _v, m = vault(REC_CFG, transcripts=TWO_RECORDINGS)
        r = build(m)
        self.assertNotEqual(r.returncode, 0)
        out = r.stderr + r.stdout
        src_line = [l for l in out.splitlines() if "rec-notetaker" in l]
        other = [l for l in out.splitlines() if "rec-own" in l]
        self.assertTrue(src_line and "the source" in src_line[0], src_line)
        self.assertTrue(other and "not the source" in other[0], other)

    def test_unknown_preference_falls_back_and_is_reported(self):
        cfg = REC_CFG.replace("prefer: named-speakers", "prefer: shortest")
        _v, m = vault(cfg, transcripts=TWO_RECORDINGS)
        cf = cf_of(m)
        self.assertEqual(ba.recording_preference(cf), ba.RECORDING_DEFAULT_PREFERENCE)
        findings = ba.config_checks(cf, [(NOTE_DAY, m / f"{NOTE_DAY}-daily-standup.md")],
                                    AFTER, None)
        self.assertTrue(any("prefer: shortest" in f for f in findings), findings)


CONNECTED_CFG = (BASE + "external_systems:\n  transcripts:\n"
                 "    store: \"a meeting store\"\n    match: [\"Acme standup\"]\n"
                 "    connected: true\n")


class ConnectedStoreIsChecked(unittest.TestCase):
    """Proposal 4: a connected store earns `checked`, and only when declared."""

    def recording_row(self, m):
        rows = [r for r in check_rows(m) if r[0] == "recording source"]
        self.assertEqual(len(rows), 1, rows)
        return rows[0]

    def test_a_connected_store_is_checked(self):
        _v, m = vault(CONNECTED_CFG)
        label, state, _t, detail = self.recording_row(m)
        self.assertEqual(state, "checked")
        self.assertIn("connected", detail)
        self.assertIn("a meeting store", detail)

    def test_a_store_that_is_not_connected_is_still_not_checked(self):
        """The operator's decision: an undeclared connection is never inferred."""
        _v, m = vault(CONNECTED_CFG.replace("    connected: true\n", ""))
        _l, state, _t, detail = self.recording_row(m)
        self.assertEqual(state, ba.UNCHECKED)
        self.assertIn("prepare checks", detail)

    def test_connected_without_a_store_names_nothing_and_is_reported(self):
        cfg = CONNECTED_CFG.replace("    store: \"a meeting store\"\n", "")
        _v, m = vault(cfg)
        _l, state, _t, _d = self.recording_row(m)
        self.assertEqual(state, ba.UNCHECKED,
                         "`connected: true` alone names nothing to connect to")
        findings = ba.config_checks(cf_of(m), [(NOTE_DAY, m / f"{NOTE_DAY}-daily-standup.md")],
                                    AFTER, None)
        self.assertTrue(any("connected: true" in f and "no `store:`" in f for f in findings),
                        findings)

    def test_the_yaml_truthy_spellings_are_the_declaration_they_look_like(self):
        """Defect pass. The flag was tested with `is True`, so a quoted `"true"` and a
        `1` -- both of which YAML permits and neither of which arrives as a bool -- fell
        through to not-connected AND produced no finding: the operator declared the
        connection, got the old *not checked* row, and was told nothing. Asserted on the
        pre-flight ROW, which is what proposal 4 exists to change."""
        for spelling in ('"true"', "1", "yes", "on"):
            with self.subTest(spelling=spelling):
                _v, m = vault(CONNECTED_CFG.replace("connected: true",
                                                    f"connected: {spelling}"))
                _l, state, _t, detail = self.recording_row(m)
                self.assertEqual(state, "checked", f"connected: {spelling}")
                self.assertIn("connected", detail)

    def test_a_declared_no_is_not_connected_and_is_not_a_finding(self):
        """`connected: false` is an answer, not a mistake: it says the close-out has no
        way in, which is the same row as declaring nothing and must not be reported."""
        for spelling in ("false", '"false"', "no", "0"):
            with self.subTest(spelling=spelling):
                _v, m = vault(CONNECTED_CFG.replace("connected: true",
                                                    f"connected: {spelling}"))
                _l, state, _t, _d = self.recording_row(m)
                self.assertEqual(state, ba.UNCHECKED, f"connected: {spelling}")
                findings = ba.config_checks(
                    cf_of(m), [(NOTE_DAY, m / f"{NOTE_DAY}-daily-standup.md")], AFTER, None)
                self.assertFalse([f for f in findings if "connected" in f], findings)

    def test_a_value_that_is_neither_a_yes_nor_a_no_is_reported(self):
        """Consistent with every other key this CR adds: an unknown `kind:` and an
        unknown `prefer:` each fall back AND say so. A flag that silently means no is the
        one case where the operator cannot find out why the row did not change."""
        _v, m = vault(CONNECTED_CFG.replace("connected: true", "connected: maybe"))
        _l, state, _t, _d = self.recording_row(m)
        self.assertEqual(state, ba.UNCHECKED, "an unreadable flag is never a yes")
        findings = ba.config_checks(cf_of(m), [(NOTE_DAY, m / f"{NOTE_DAY}-daily-standup.md")],
                                    AFTER, None)
        said = [f for f in findings if "connected" in f]
        self.assertEqual(len(said), 1, findings)
        self.assertIn("maybe", said[0], said[0])
        self.assertIn("not checked", said[0], said[0])

    def test_a_connected_store_never_fails_the_pre_flight(self):
        """The script does not fetch, so this row reports a declaration and never a
        reached store -- it must not change the exit code in either direction."""
        _v, m = vault(CONNECTED_CFG)
        self.assertNotIn(self.recording_row(m)[1], ba.CHECK_BAD)

    def test_the_sources_block_agrees_with_the_pre_flight_row(self):
        _v, m = vault(CONNECTED_CFG)
        self.assertEqual(build(m).returncode, 0)
        rec_lines = [l for l in agenda_text(m).splitlines() if l.startswith("  record ")]
        self.assertEqual(len(rec_lines), 1, rec_lines)
        self.assertIn("connected", rec_lines[0])
        self.assertNotIn("prepare checks", rec_lines[0])


class Additive(unittest.TestCase):
    """A project declaring none of the new keys behaves as it did."""

    def test_a_chat_entry_with_no_kind_is_a_group_chat_everywhere(self):
        _v, m = vault(as_card(PLAIN_CHAT_CFG), chats={
            "group-1": {"name": "acme-standup",
                        "messages": {"2026-09-23": "### Bob 09:00\nretry is live\n"}}})
        self.assertEqual(build(m).returncode, 0)
        text = agenda_text(m)
        self.assertNotIn("direct:", text)
        built = [l for l in text.splitlines() if "**Built from**" in l][0]
        self.assertIn("chat Acme standup", built)

    def test_no_recording_declaration_writes_no_recordings_section(self):
        _v, m = vault(PLAIN_CHAT_CFG, chats={"group-1": {"name": "acme-standup"}})
        self.assertEqual(build(m).returncode, 0)
        self.assertNotIn("Recordings of this series", agenda_text(m))


if __name__ == "__main__":
    unittest.main()
