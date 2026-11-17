"""CR-179: a declared meeting schedule, and an unattended run that stops at staged.

One test class per bullet of the CR's Tests section, plus the reader's own edges. Every
vault here is built in a temporary folder from invented data and run through the real
scripts.

    python3 -m unittest discover -s tests
"""
import datetime
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OPS = ROOT / "skills" / "ops"
sys.path.insert(0, str(OPS))
import build_agenda as ba  # noqa: E402
import meeting_schedule as ms  # noqa: E402
import run_report as rr  # noqa: E402

CF = "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
STANDUP = ("meeting_types:\n  standup:\n    preparation_mode: single\n"
           "meetings:\n  - type: standup\n    days: [mon, thu]\n    time: \"08:30\"\n"
           "    timezone: Europe/Stockholm\n    unattended: [prepare, process]\n")
NOTE = "# Standup\n\n## Carried forward\n\n- **Payment retry:** Bob\n"
# A Tuesday, so the next declared session (mon, thu) is Thursday 261119.
NOW = "2026-11-17T09:00:00+01:00"


def vault(ops_yaml: str, notes=("261116",)):
    """A vault with one venture and one project; returns (vault, project, meetings)."""
    v = Path(tempfile.mkdtemp())
    (v / "_outbox").mkdir()
    proj = v / "venture" / "proj"
    md = proj / "meetings"
    md.mkdir(parents=True)
    (proj / "_ops.yaml").write_text(ops_yaml, encoding="utf-8")
    for d in notes:
        (md / f"{d}-daily-standup.md").write_text(NOTE, encoding="utf-8")
    return v, proj, md


def script(name, *args, cwd=None):
    return subprocess.run([sys.executable, str(OPS / name), *map(str, args)],
                          capture_output=True, text=True, cwd=cwd)


def brief(md: Path, now: str = NOW) -> str:
    r = script("project_brief.py", "--dir", md, "--now", now)
    assert r.returncode == 0, r.stderr
    return r.stdout


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


# ---- 1. `meetings:` parses; orient names the next session; absent changes nothing ----

class Parses(unittest.TestCase):
    def test_a_full_entry_parses_with_defaults(self):
        entries, problems = ms.parse(yaml.safe_load(STANDUP)["meetings"], {"standup": {}})
        self.assertEqual(problems, [])
        e = entries[0]
        self.assertEqual((e["type"], e["days"], e["time"]), ("standup", (0, 3), "08:30"))
        self.assertEqual(e["duration"], datetime.timedelta(minutes=30))
        self.assertEqual(e["prepare_lead"], datetime.timedelta(minutes=45))
        self.assertEqual(e["transcript_wait"], datetime.timedelta(hours=4))
        self.assertEqual(e["unattended"], ("prepare", "process"))
        self.assertFalse(e["apply_ledgers"])

    def test_weekdays_and_durations(self):
        entries, _ = ms.parse([{"type": "x", "days": "weekdays", "time": "9:05",
                                "duration": "1h30m", "prepare_lead": 20}])
        self.assertEqual(entries[0]["days"], (0, 1, 2, 3, 4))
        self.assertEqual(entries[0]["time"], "09:05")
        self.assertEqual(entries[0]["duration"], datetime.timedelta(minutes=90))
        self.assertEqual(entries[0]["prepare_lead"], datetime.timedelta(minutes=20))

    def test_a_typo_in_days_is_reported_and_does_not_empty_the_schedule(self):
        entries, problems = ms.parse([{"type": "x", "days": ["mon", "tursday"], "time": "08:30"}])
        self.assertEqual(entries[0]["days"], (0,))
        self.assertTrue(any("tursday" in p for p in problems))

    def test_malformed_entries_are_skipped_with_a_reason_never_a_crash(self):
        entries, problems = ms.parse([{"days": ["mon"], "time": "08:30"},
                                      {"type": "a", "days": ["mon"], "time": "8.30"},
                                      {"type": "b", "days": ["xx"], "time": "08:30"},
                                      {"type": "c", "days": ["mon"], "time": "08:30", "timezone": "Mars/Base"},
                                      "nonsense"])
        self.assertEqual(entries, [])
        self.assertEqual(len(problems), 6)   # b also reports its unknown day

    def test_an_unknown_unattended_step_is_dropped(self):
        entries, problems = ms.parse([{"type": "x", "days": ["mon"], "time": "08:30",
                                       "unattended": ["prepare", "send"]}])
        self.assertEqual(entries[0]["unattended"], ("prepare",))
        self.assertTrue(any("'send'" in p for p in problems))

    def test_a_type_missing_from_meeting_types_is_reported(self):
        _e, problems = ms.parse([{"type": "x", "days": ["mon"], "time": "08:30"}], {"other": {}})
        self.assertTrue(any("not a key in meeting_types" in p for p in problems))

    def test_windows(self):
        e = ms.parse(yaml.safe_load(STANDUP)["meetings"])[0][0]
        start = ms.next_meeting([e], datetime.datetime.fromisoformat(NOW))[1]
        w = ms.windows(e, start)
        self.assertEqual(start.strftime("%y%m%d %H:%M"), "261119 08:30")
        self.assertEqual(w["prepare_at"].strftime("%H:%M"), "07:45")
        self.assertEqual(w["ready_by"].strftime("%H:%M"), "08:00")
        self.assertEqual(w["transcript_by"].strftime("%H:%M"), "13:00")

    def test_a_meeting_later_today_is_the_next_one(self):
        e = ms.parse([{"type": "x", "days": ["tue"], "time": "10:00", "timezone": "Europe/Stockholm"}])[0][0]
        start = ms.next_meeting([e], datetime.datetime.fromisoformat(NOW))[1]
        self.assertEqual(start.strftime("%y%m%d %H:%M"), "261117 10:00")


class Resolution(unittest.TestCase):
    def test_nearest_declaration_wins_whole(self):
        v, proj, md = vault(CF + STANDUP)
        (v / "venture" / "_ops.yaml").write_text(
            "meetings:\n  - type: weekly\n    days: [fri]\n    time: \"10:00\"\n", encoding="utf-8")
        d = ms.declared(md)
        self.assertEqual([e["type"] for e in d["meetings"]], ["standup"])
        self.assertEqual(d["file"], (proj / "_ops.yaml").resolve())

    def test_an_empty_list_stops_the_walk(self):
        v, proj, md = vault(CF + "meetings: []\n")
        (v / "venture" / "_ops.yaml").write_text(
            "meetings:\n  - type: weekly\n    days: [fri]\n    time: \"10:00\"\n", encoding="utf-8")
        self.assertEqual(ms.declared(md)["meetings"], [])

    def test_the_vault_layer_is_read_last(self):
        v, proj, md = vault(CF)
        (v / "_config").mkdir()
        (v / "_config" / "base.yaml").write_text(
            "meetings:\n  - type: weekly\n    days: [fri]\n    time: \"10:00\"\n", encoding="utf-8")
        self.assertEqual([e["type"] for e in ms.declared(md)["meetings"]], ["weekly"])

    def test_absent_is_not_declared(self):
        _v, _p, md = vault(CF)
        self.assertEqual(ms.declared(md), {"meetings": [], "problems": [], "file": None})

    def test_the_agenda_reads_the_declared_days_when_none_other_is_declared(self):
        _v, _p, md = vault(CF + STANDUP)
        self.assertEqual(ba.config(md)["schedule_days"], ["monday", "thursday"])

    def test_schedule_days_keeps_precedence(self):
        _v, _p, md = vault(CF.rstrip("\n") + "\n      schedule_days: [friday]\n" + STANDUP)
        self.assertEqual(ba.config(md)["schedule_days"], ["friday"])

    def test_absent_leaves_the_agenda_config_as_before(self):
        _v, _p, md = vault(CF)
        cf = ba.config(md)
        self.assertIsNone(cf["schedule_days"])
        self.assertEqual(cf["meetings"], [])

    def test_the_cli_prints_json_for_a_scheduler(self):
        _v, _p, md = vault(CF + STANDUP)
        r = script("meeting_schedule.py", "--dir", md, "--json", "--now", NOW)
        d = json.loads(r.stdout)
        self.assertEqual(d["meetings"][0]["next"]["prepare_at"], "2026-11-19T07:45:00+01:00")
        self.assertEqual(d["meetings"][0]["unattended"], ["prepare", "process"])


class Orient(unittest.TestCase):
    def test_orient_names_the_next_session_from_the_declaration(self):
        _v, _p, md = vault(CF + STANDUP)
        out = brief(md)
        self.assertIn("next session    261119 08:30 standup (declared)  — agenda NOT GENERATED", out)
        self.assertIn("unattended      prepare from 07:45, process — ledgers proposed", out)

    def test_the_declaration_overrides_the_inference_from_the_last_note(self):
        # The newest note is a Monday; inferred, the next weekday would be Tuesday 261117.
        _v, _p, md = vault(CF + STANDUP)
        self.assertNotIn("next session    261117", brief(md))

    def test_the_agenda_state_is_read_for_the_declared_day(self):
        _v, _p, md = vault(CF + STANDUP)
        (md / "261119-agenda-daily-standup.md").write_text("# Agenda\n", encoding="utf-8")
        self.assertIn("261119 08:30 standup (declared)  — agenda exists", brief(md))

    def test_a_problem_in_the_declaration_is_shown(self):
        _v, _p, md = vault(CF + STANDUP.replace("[mon, thu]", "[mon, thu, tursday]"))
        self.assertIn("schedule        ⚠ meetings[1] (standup): unknown day 'tursday'", brief(md))

    def test_with_no_note_the_declared_session_is_still_named(self):
        _v, _p, md = vault(CF + STANDUP, notes=())
        self.assertIn("next session    261119 08:30 standup (declared)", brief(md))

    def test_an_absent_block_changes_nothing(self):
        _v, _p, md = vault(CF)
        out = brief(md)
        expected = ba.next_session("261116", None)
        self.assertIn(f"    next session    {expected}  — agenda NOT GENERATED\n", out)
        for word in ("(declared)", "unattended", "schedule "):
            self.assertNotIn(word, out)


# ---- 2. An unattended preparation with a fetch record in auth_required -----------------

class FetchProblems(unittest.TestCase):
    def build(self, *flags, layout=None):
        _v, proj, md = vault(CF + (f"layout: {layout}\n" if layout else "") + STANDUP
                             + "external_systems:\n  jira:\n    - project: ABC\n")
        board = proj.parent / ".jirameta" / "abc"
        board.mkdir(parents=True)
        (board / "_project.json").write_text(json.dumps({"project": "ABC"}), encoding="utf-8")
        (proj.parent / ".jirameta" / "_fetch.json").write_text(json.dumps(
            {"result": "auth_required", "last_attempt": "2026-11-17T06:30:00+01:00",
             "last_success": "2026-11-14T06:30:00+01:00"}), encoding="utf-8")
        r = script("build_agenda.py", "--dir", md, "--date", "261119", *flags)
        self.assertEqual(r.returncode, 0, r.stderr)
        return proj, md, (md / "261119-agenda-daily-standup.md").read_text(encoding="utf-8")

    def test_the_card_carries_fetch_problems(self):
        _p, _md, agenda = self.build("--unattended", layout="card")
        self.assertIn("## Fetch problems", agenda)
        block = agenda.split("## Fetch problems", 1)[1].split("\n## ", 1)[0]
        self.assertIn("tickets: data is from", block)
        self.assertIn("login required", block)

    def test_the_list_layout_carries_it_too(self):
        _p, _md, agenda = self.build("--unattended")
        self.assertIn("## Fetch problems", agenda)

    def test_the_attended_agenda_is_unchanged(self):
        _p, _md, agenda = self.build()
        self.assertNotIn("## Fetch problems", agenda)
        self.assertIn("Fetch failed", agenda)

    def test_the_run_report_copies_the_block(self):
        proj, md, _a = self.build("--unattended", layout="card")
        r = script("run_report.py", "write", "--dir", md, "--step", "prepare", "--date", "261119",
                   "--written", md / "261119-agenda-daily-standup.md")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        fm = rr.read_report(proj / ".runs" / "261119-prepare-standup.md")
        self.assertTrue(any("login required" in x for x in fm["fetch_problems"]))


# ---- 3. An ambiguous attribution: [OPEN] in the summary, in the report, no ledger -------

class OpenQuestions(unittest.TestCase):
    def setUp(self):
        self.v, self.proj, self.md = vault(CF + STANDUP)
        (self.proj / "CHANGELOG.md").write_text("# Changelog\n\n## [2026-11-16]\n- standup\n", encoding="utf-8")
        (self.proj / "_tasks.yaml").write_text("tasks:\n- id: t1\n  task: old\n", encoding="utf-8")
        self.summary = self.md / "261119-summary-standup.md"
        self.summary.write_text(
            "# Standup\n\n| # | Action | Owner |\n|---|---|---|\n"
            "| 1 | Retry payments | ? [OPEN: \"Al\" in the recording -- Alex or Alice?] |\n\n"
            "## Carried forward\n\n- **Payment retry:** ?\n", encoding="utf-8")
        self.proposals = self.v / "proposals.yaml"
        self.proposals.write_text(yaml.safe_dump([
            {"file": "CHANGELOG.md", "op": "insert_before", "anchor": "## [2026-11-16]",
             "text": "## [2026-11-19]\n- standup: payments retry discussed\n", "why": "the changelog line"},
            {"file": "_tasks.yaml", "op": "append", "text": "- id: t2\n  task: retry payments\n"}],
            sort_keys=False), encoding="utf-8")
        self.before = snapshot(self.proj)

    def write(self):
        r = script("run_report.py", "write", "--dir", self.md, "--step", "process", "--date", "261119",
                   "--type", "standup", "--written", self.summary, "--proposed", self.proposals)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout, rr.read_report(self.proj / ".runs" / "261119-process-standup.md")

    def test_the_marker_is_listed_first_in_the_report(self):
        out, fm = self.write()
        self.assertEqual(fm["open"], [{"file": "meetings/261119-summary-standup.md", "line": 5,
                                       "question": "\"Al\" in the recording -- Alex or Alice?"}])
        body = out[out.index("\n---\n\n# Run report") + 6:]
        self.assertTrue(body.startswith("# Run report -- process standup 261119\n\n## Open questions (1)"))

    def test_no_ledger_is_written(self):
        self.write()
        after = snapshot(self.proj)
        self.assertIsNotNone(after.pop(".runs/261119-process-standup.md", None))
        self.assertEqual(after, self.before)

    def test_the_changes_are_proposed_in_the_report(self):
        out, fm = self.write()
        self.assertEqual([(c["id"], c["file"], c["op"]) for c in fm["proposed"]],
                         [(1, "CHANGELOG.md", "insert_before"), (2, "_tasks.yaml", "append")])
        self.assertEqual(fm["applied"], [])
        self.assertFalse(fm["apply_ledgers"])
        self.assertIn("not written. From the attended session: `/ops apply <folder> 261119`", out)

    def test_the_run_may_not_apply_them_itself_without_apply_ledgers(self):
        self.write()
        r = script("run_report.py", "apply", self.proj, "261119", "--write", "--unattended")
        self.assertEqual(r.returncode, rr.EXIT_NOT_ALLOWED, r.stdout)
        self.assertEqual(snapshot(self.proj)["CHANGELOG.md"], self.before["CHANGELOG.md"])

    def test_with_apply_ledgers_the_run_applies_them(self):
        (self.proj / "_ops.yaml").write_text(CF + STANDUP + "    apply_ledgers: true\n", encoding="utf-8")
        self.write()
        r = script("run_report.py", "apply", self.proj, "261119", "--write", "--unattended")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("## [2026-11-19]", (self.proj / "CHANGELOG.md").read_text(encoding="utf-8"))
        fm = rr.read_report(self.proj / ".runs" / "261119-process-standup.md")
        self.assertEqual(fm["applied_by"], "unattended run")

    def test_a_ready_outbox_status_is_a_problem(self):
        item = self.v / "_outbox" / "261119-contact-team_standup"
        item.mkdir()
        (item / "_manifest.md").write_text("# Recap\n\n**Status:** klar-att-skicka\n", encoding="utf-8")
        (item / "notes.md").write_text("undated\n", encoding="utf-8")
        probs = rr.written_problems([item / "_manifest.md", item / "notes.md"], self.proj)
        self.assertTrue(any("an unattended run stages `draft` only" in p for p in probs))
        self.assertTrue(any("notes.md: not a new dated file" in p for p in probs))
        (item / "_manifest.md").write_text("# Recap\n\n**Status:** draft\n", encoding="utf-8")
        self.assertEqual(rr.written_problems([item / "_manifest.md"], self.proj), [])

    def test_allowed_follows_the_declaration(self):
        r = script("run_report.py", "allowed", "--dir", self.md, "--step", "process")
        self.assertEqual(r.returncode, 0)
        _v, _p, md2 = vault(CF)
        r = script("run_report.py", "allowed", "--dir", md2, "--step", "prepare")
        self.assertEqual(r.returncode, rr.EXIT_NOT_ALLOWED)
        self.assertIn("absent means off", r.stdout)
        _v, _p, md3 = vault(CF + STANDUP.replace("[prepare, process]", "[prepare]"))
        self.assertEqual(script("run_report.py", "allowed", "--dir", md3, "--step", "process").returncode,
                         rr.EXIT_NOT_ALLOWED)


# ---- 4. An existing file at an output path: the run stops; the file is unchanged ---------

class ExistingFile(unittest.TestCase):
    def test_the_generator_stops_on_any_file_of_the_set(self):
        _v, _p, md = vault(CF + "layout: card\n" + STANDUP)
        details = md / ba.details_name(ba.config(md), "261119")
        details.write_text("hand-written\n", encoding="utf-8")
        r = script("build_agenda.py", "--dir", md, "--date", "261119", "--unattended")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unattended run stopped", r.stderr)
        self.assertIn(details.name, r.stderr)
        self.assertEqual(details.read_text(encoding="utf-8"), "hand-written\n")
        self.assertFalse((md / "261119-agenda-daily-standup.md").exists())

    def test_the_guard_stops_and_reports(self):
        _v, proj, md = vault(CF + STANDUP)
        taken = md / "261119-summary-standup.md"
        taken.write_text("by hand\n", encoding="utf-8")
        before = snapshot(proj)
        r = script("run_report.py", "guard", taken, md / "261119-agenda-daily-standup.md")
        self.assertEqual(r.returncode, rr.EXIT_EXISTS)
        self.assertIn(f"EXISTS {taken}", r.stdout)
        self.assertEqual(snapshot(proj), before)
        r = script("run_report.py", "write", "--dir", md, "--step", "process", "--date", "261119",
                   "--stopped", f"{taken.name} exists")
        fm = rr.read_report(proj / ".runs" / "261119-process-standup.md")
        self.assertEqual((fm["status"], fm["stopped"]), ("stopped", f"{taken.name} exists"))
        self.assertEqual(taken.read_text(encoding="utf-8"), "by hand\n")

    def test_the_guard_is_clear_when_nothing_exists(self):
        _v, _p, md = vault(CF)
        self.assertEqual(script("run_report.py", "guard", md / "261119-x.md").returncode, 0)

    def test_a_same_day_rerun_gets_a_new_report_not_an_overwrite(self):
        _v, proj, md = vault(CF + STANDUP)
        for _ in range(2):
            script("run_report.py", "write", "--dir", md, "--step", "prepare", "--date", "261119")
        self.assertEqual(sorted(p.name for p in (proj / ".runs").iterdir()),
                         ["261119-prepare-standup.md", "261119b-prepare-standup.md"])


# ---- 5. apply writes exactly the proposed changes and nothing else ---------------------

class Apply(unittest.TestCase):
    CHANGELOG = "# Changelog\n\n## [2026-11-16]\n- standup\n"
    TASKS = "tasks:\n- id: t1\n  task: old\n"

    def setUp(self):
        self.v, self.proj, self.md = vault(CF + STANDUP)
        (self.proj / "CHANGELOG.md").write_text(self.CHANGELOG, encoding="utf-8")
        (self.proj / "_tasks.yaml").write_text(self.TASKS, encoding="utf-8")
        (self.proj / "README.md").write_text("# Meetings\n\n| Date | Note |\n|---|---|\n", encoding="utf-8")

    def report(self, changes):
        f = self.v / "p.yaml"
        f.write_text(yaml.safe_dump(changes, sort_keys=False), encoding="utf-8")
        r = script("run_report.py", "write", "--dir", self.md, "--step", "process", "--date", "261119",
                   "--proposed", f)
        self.assertEqual(r.returncode, 0, r.stdout)
        return self.proj / ".runs" / "261119-process-standup.md"

    CHANGES = [
        {"file": "CHANGELOG.md", "op": "insert_before", "anchor": "## [2026-11-16]",
         "text": "## [2026-11-19]\n- standup\n"},
        {"file": "_tasks.yaml", "op": "append", "text": "- id: t2\n  task: new\n"},
        {"file": "README.md", "op": "insert_after", "anchor": "|---|---|",
         "text": "| 261119 | [summary](meetings/261119-summary-standup.md) |\n"},
    ]

    def test_exactly_the_proposed_text_and_nothing_else(self):
        rp = self.report(self.CHANGES)
        before = snapshot(self.v)
        r = script("run_report.py", "apply", self.proj, "261119", "--write")
        self.assertEqual(r.returncode, 0, r.stdout)
        after = snapshot(self.v)
        changed = {k for k in after if after[k] != before.get(k)} | (set(before) - set(after))
        rel = lambda p: str(p.relative_to(self.v))   # noqa: E731
        self.assertEqual(changed, {rel(self.proj / "CHANGELOG.md"), rel(self.proj / "_tasks.yaml"),
                                   rel(self.proj / "README.md"), rel(rp)})
        self.assertEqual((self.proj / "CHANGELOG.md").read_text(encoding="utf-8"),
                         "# Changelog\n\n## [2026-11-19]\n- standup\n## [2026-11-16]\n- standup\n")
        self.assertEqual((self.proj / "_tasks.yaml").read_text(encoding="utf-8"),
                         self.TASKS + "- id: t2\n  task: new\n")
        self.assertEqual((self.proj / "README.md").read_text(encoding="utf-8"),
                         "# Meetings\n\n| Date | Note |\n|---|---|\n"
                         "| 261119 | [summary](meetings/261119-summary-standup.md) |\n")
        fm = rr.read_report(rp)
        self.assertEqual((fm["applied"], fm["applied_by"]), ([1, 2, 3], "attended session"))

    def test_without_write_nothing_is_written(self):
        self.report(self.CHANGES)
        before = snapshot(self.v)
        r = script("run_report.py", "apply", self.proj, "261119")
        self.assertEqual(r.returncode, 0)
        self.assertIn("nothing written", r.stdout)
        self.assertIn("+ ## [2026-11-19]", r.stdout)
        self.assertEqual(snapshot(self.v), before)

    def test_all_or_nothing(self):
        bad = self.CHANGES + [{"file": "CHANGELOG.md", "op": "insert_before",
                               "anchor": "## [1999-01-01]", "text": "x\n"}]
        self.report(bad)
        before = snapshot(self.v)
        r = script("run_report.py", "apply", self.proj, "--write")
        self.assertEqual(r.returncode, rr.EXIT_REFUSED)
        self.assertIn("found 0 times", r.stdout)
        self.assertEqual(snapshot(self.v), before)

    def test_a_yaml_ledger_that_would_break_is_refused(self):
        self.report([{"file": "_tasks.yaml", "op": "append", "text": "  - : : [\n"}])
        before = snapshot(self.v)
        r = script("run_report.py", "apply", self.proj, "261119", "--write")
        self.assertEqual(r.returncode, rr.EXIT_REFUSED)
        self.assertIn("would no longer parse", r.stdout)
        self.assertEqual(snapshot(self.v), before)

    def test_applied_once_only(self):
        self.report(self.CHANGES)
        self.assertEqual(script("run_report.py", "apply", self.proj, "--write").returncode, 0)
        once = snapshot(self.v)
        r = script("run_report.py", "apply", self.proj, "--write")
        self.assertEqual(r.returncode, rr.EXIT_NOTHING)
        self.assertEqual(snapshot(self.v), once)

    def test_only_applies_a_subset_and_leaves_the_rest_pending(self):
        rp = self.report(self.CHANGES)
        r = script("run_report.py", "apply", self.proj, "261119", "--only", "2", "--write")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual((self.proj / "CHANGELOG.md").read_text(encoding="utf-8"), self.CHANGELOG)
        self.assertEqual(rr.read_report(rp)["applied"], [2])
        self.assertEqual(script("run_report.py", "apply", self.proj, "--write").returncode, 0)
        self.assertEqual(rr.read_report(rp)["applied"], [1, 2, 3])

    def test_a_proposal_into_a_dot_folder_or_out_of_the_vault_is_left_out(self):
        rp = self.report([{"file": "../../.transcripts/x.md", "op": "append", "text": "x\n"},
                          {"file": "../../../elsewhere.md", "op": "create", "text": "x\n"},
                          {"file": "CHANGELOG.md", "op": "rewrite", "text": "x\n"}])
        fm = rr.read_report(rp)
        self.assertEqual(fm["proposed"], [])
        self.assertEqual(len(fm["problems"]), 3)

    def test_create_never_overwrites(self):
        self.report([{"file": "CHANGELOG.md", "op": "create", "text": "new\n"}])
        r = script("run_report.py", "apply", self.proj, "--write")
        self.assertEqual(r.returncode, rr.EXIT_REFUSED)
        self.assertEqual((self.proj / "CHANGELOG.md").read_text(encoding="utf-8"), self.CHANGELOG)


# ---- the contract and the skill say the same thing -------------------------------------

class Contract(unittest.TestCase):
    def test_contract_declares_the_block_and_the_subcommand(self):
        doc = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
        self.assertEqual(set(doc["meetings"]["fields"]),
                         {"type", "days", "time", "timezone", "duration", "prepare_lead",
                          "transcript_wait", "unattended", "apply_ledgers"})
        self.assertEqual(doc["meetings"]["fields"]["unattended"]["values"], list(ms.STEPS))
        self.assertEqual(doc["meetings"]["run_report"]["proposed_ops"], list(rr.OPS))
        ops = next(s for s in doc["skills"]["user_invocable"] if s["name"] == "ops")
        self.assertIn("apply", ops["subcommands"])

    def test_skill_documents_the_four_differences_and_the_marker(self):
        text = (OPS / "SKILL.md").read_text(encoding="utf-8")
        for needle in ("### `apply <folder> [YYMMDD]`", "[OPEN: <question>]", "**always `draft`.**",
                       "**proposed, not written**", "**new dated files only**",
                       "**The run report is the session's final output:**"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
