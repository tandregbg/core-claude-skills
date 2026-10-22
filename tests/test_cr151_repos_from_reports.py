"""CR-151: the repository list is derived from the status reports, and proposed for confirmation.

A project declared one repository -- its own portal -- so the agenda, the movement block and
the digest read that one only, while the release depended on at least seven others. The only
place that said so was the daily status report, so the list could have been proposed from the
reports rather than from memory.

What is tested is the REQUIREMENT, not the shape of the implementation. Every test builds a
real vault of dated reports and runs the real helper over it, because the three ways the
previous waves' tests went green against broken code were all shortcuts around doing that:
asserting a literal string appears in the implementation's source, asserting the FORMAT of a
warning and never its content, and a fixture whose data could not distinguish the ordering it
claimed to assert. So: the day counts are asserted against fixtures where a wrong count is a
DIFFERENT NUMBER, the prose split against a fixture where a shape test would answer the
opposite, and the central safety property -- nothing written without a yes -- by reading the
config file back off disk byte for byte. Invented data.

    python3 -m unittest discover -s tests
"""

import datetime as dt
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "skills" / "ops"
sys.path.insert(0, str(OPS))
import build_agenda as ba  # noqa: E402
import build_movement as bm  # noqa: E402
import propose_repos as pr  # noqa: E402

END = dt.date(2026, 10, 21)          # a Wednesday

OPS_YAML = r"""workflows:
  post_processing:
    carry_forward:
      enabled: true
external_systems:
  repos:
    - url: github.com/acme/portal
      reads: [issues, pulls]
  vault_reports:
    - name: Daily status
      dir: status
      pattern: '^\d{6}-status\.md$'
"""

# One day's report. The repositories are named in the three shapes proposal 1 lists, and
# the counts below are what this content gives -- so a reader that drops one shape gives a
# different number, not a differently formatted same number.
REPORT = """# Status

Release branch cut from acme/core-api; acme/site rebuilt overnight.

| Repository | Merges | Note |
|---|---|---|
| core-api | 4 | refund rounding |
| proxy | 1 | header passthrough |
| portal | 2 | signup copy |

Blocked on proxy#88 and proxy PR #91. The database migration waits on acme/warehouse.

| Area | Closed |
|---|---|
| billing | 3 |
| mobile | 2 |
"""


def vault(ops_yaml: str = OPS_YAML, reports: dict[dt.date, str] | None = None,
          days: int = 12, body: str = REPORT):
    """A venture with one project, `days` consecutive WORKING days of reports back from END.

    Returns (project dir, meetings dir). `reports` overrides the generated series when a
    test needs particular content on particular days.
    """
    proj = Path(tempfile.mkdtemp()) / "venture" / "proj"
    (proj / "meetings").mkdir(parents=True)
    (proj / "status").mkdir()
    (proj / "_ops.yaml").write_text(ops_yaml, encoding="utf-8")
    (proj / "meetings" / "261021-daily-standup.md").write_text(
        "# Standup\n\n## Carried forward\n\n- **Refund rounding** — #12 · **Bob**\n", encoding="utf-8")
    if reports is None:
        reports, d, n = {}, END, 0
        while n < days:
            if d.weekday() < 5:
                reports[d] = body
                n += 1
            d -= dt.timedelta(days=1)
    for when, text in reports.items():
        (proj / "status" / f"{when.strftime('%y%m%d')}-status.md").write_text(text, encoding="utf-8")
    return proj, proj / "meetings"


def counted(proj: Path, days: int = 14, end: dt.date = END):
    cf = ba.config(proj / "meetings")
    return cf, pr.count_window(cf, pr.working_days_back(end, days), end)


def helper(meetings: Path, *args):
    r = subprocess.run([sys.executable, str(OPS / "propose_repos.py"), "--dir", str(meetings), *args],
                       capture_output=True, text=True)
    return r


class Window(unittest.TestCase):
    """The window is working days, and it is read through `build_movement`'s resolver."""

    def test_working_days_not_calendar_days(self):
        # 14 working days back from Wed 21 Oct 2026 is Fri 2 Oct, not Wed 7 Oct. A
        # calendar-day window reaches ten reports where this reaches fourteen, which is
        # what made a repository in every report read as named on ten days of fourteen.
        self.assertEqual(pr.working_days_back(END, 14), dt.date(2026, 10, 2))
        self.assertEqual(pr.working_days_back(END, 1), END)
        # No weekend is ever the start of a window.
        for n in range(1, 40):
            self.assertLess(pr.working_days_back(END, n).weekday(), 5, n)

    def test_window_reads_the_series_through_the_shared_resolver(self):
        # The directory is found by WALKING UP from the project root, which is
        # `build_movement.vault_report_dir`'s rule: a project nested under a venture
        # declares a folder that sits beside the venture, and every reader of
        # `vault_reports:` has to resolve it to the same path -- otherwise the window
        # counts mentions in a folder whose age nothing is reporting.
        #
        # The declaration is NOT written relative to the project root here (`../..`
        # would resolve either way and prove nothing). It is a bare `board-status`
        # that exists only two levels up, so a reader that joins it to the project
        # root alone finds nothing at all.
        proj, _md = vault()
        up = proj.parent.parent / "board-status"
        up.mkdir()
        (up / "261021-status.md").write_text(REPORT, encoding="utf-8")
        cf = ba.config(proj / "meetings")
        r = {"name": "Board", "dir": "board-status", "pattern": r"^\d{6}-status\.md$"}
        self.assertFalse((Path(cf["_root"]) / "board-status").exists())
        self.assertEqual(bm.vault_report_dir(cf, r), up.resolve())
        got = pr.window_files(cf, r, pr.working_days_back(END, 14), END)
        self.assertEqual([f.resolve() for _d, f in got], [(up / "261021-status.md").resolve()])

    def test_only_dated_files_inside_the_window(self):
        proj, _md = vault(days=12)
        # One report before the window and one undated name in the same folder.
        (proj / "status" / "260901-status.md").write_text(REPORT, encoding="utf-8")
        (proj / "status" / "status.md").write_text(REPORT, encoding="utf-8")
        cf = ba.config(proj / "meetings")
        r = cf["ext"]["vault_reports"][0]
        got = pr.window_files(cf, r, pr.working_days_back(END, 14), END)
        self.assertEqual(len(got), 12)
        self.assertNotIn("260901-status.md", [f.name for _d, f in got])
        self.assertNotIn("status.md", [f.name for _d, f in got])
        self.assertTrue(all(pr.working_days_back(END, 14) <= d <= END for d, _f in got))


class Counting(unittest.TestCase):
    """Proposal 1: the three shapes, counted in DAYS."""

    def test_days_named_not_mentions(self):
        # `proxy` is named four times in one report (a table cell, `proxy#88`,
        # `proxy PR #91` and the prose). Over twelve reports that is twelve DAYS, not
        # forty-eight mentions -- the number the measured reading turned on.
        _cf, (counts, read, problems) = counted(*vault()[:1])
        self.assertEqual(problems, [])
        self.assertEqual(len(read), 12)
        self.assertEqual(len(counts["proxy"]["days"]), 12)
        self.assertEqual(len(counts["core-api"]["days"]), 12)

    def test_the_three_shapes_each_find_their_own_repository(self):
        # One report, one shape each, so dropping a shape loses a NAME rather than
        # changing a count: `warehouse` is only ever a slug, `queue` only ever an item
        # citation, `proxy` only ever a repository-table cell.
        text = ("Waiting on acme/warehouse.\n\nqueue#404 is still open.\n\n"
                "| Repository | Merges |\n|---|---|\n| proxy | 2 |\n")
        _cf, (counts, _r, _p) = counted(vault(reports={END: text})[0])
        self.assertEqual(sorted(counts), ["proxy", "queue", "warehouse"])
        self.assertEqual(sorted(counts["warehouse"]["slugs"]), ["acme/warehouse"])
        self.assertEqual(sorted(counts["queue"]["items"]), [404])

    def test_distinct_items_are_counted_once_each(self):
        # `proxy#88` on every one of twelve days plus `proxy PR #91` is TWO distinct
        # items, not twenty-four mentions and not one.
        _cf, (counts, _r, _p) = counted(vault()[0])
        self.assertEqual(sorted(counts["proxy"]["items"]), [88, 91])

    def test_only_a_repository_column_is_read_as_repositories(self):
        # The fixture's second table is headed `Area` with cells `billing` and `mobile`.
        # A reader that took the first cell of every table would propose both -- which
        # is the failure that makes a count worthless, since a status report is mostly
        # tables. Neither is a candidate here.
        _cf, (counts, _r, _p) = counted(vault()[0])
        self.assertNotIn("mobile", counts)
        # `billing` reaches the counts only as prose, never as a repository candidate.
        self.assertNotIn("billing", counts)

    def test_a_date_is_not_a_repository(self):
        text = "Cut 2026/10 and shipped 3/4 of the backlog; see acme/site.\n"
        _cf, (counts, _r, _p) = counted(vault(reports={END: text})[0])
        self.assertEqual(sorted(counts), ["site"])

    def test_purpose_is_copied_from_the_report(self):
        _cf, (counts, _r, _p) = counted(vault()[0])
        # The report's own words, not composed: the line that first named it.
        self.assertIn("Release branch cut", counts["core-api"]["purpose"])
        self.assertNotIn("TODO", counts["core-api"]["purpose"])

    def test_a_series_that_cannot_be_read_is_reported_not_counted_as_empty(self):
        bad = OPS_YAML.replace("dir: status", "dir: no-such-folder")
        proj, _md = vault(bad)
        _cf, (counts, read, problems) = counted(proj)
        self.assertEqual(counts, {})
        self.assertEqual(read, [])
        self.assertEqual(len(problems), 1)
        self.assertIn("no-such-folder", problems[0])

    def test_no_dated_report_in_the_window_is_reported(self):
        proj, _md = vault(reports={dt.date(2026, 6, 1): REPORT})
        _cf, (counts, read, problems) = counted(proj)
        self.assertEqual((counts, read), ({}, []))
        self.assertEqual(len(problems), 1)
        self.assertIn("window", problems[0])


class Prose(unittest.TestCase):
    """Proposal 2: an ordinary word that matches a repository name is listed separately."""

    def test_an_ordinary_word_in_a_repository_column_is_prose(self):
        text = ("| Repository | Merges |\n|---|---|\n| scripts | 1 |\n| billing | 2 |\n"
                "| core-api | 4 |\n")
        cf, (counts, read, problems) = counted(vault(reports={END: text})[0])
        self.assertTrue(pr.probably_prose("scripts", counts["scripts"]))
        self.assertTrue(pr.probably_prose("billing", counts["billing"]))
        self.assertFalse(pr.probably_prose("core-api", counts["core-api"]))
        out = pr.proposal(cf, counts, read, problems, 14)
        # Both headings present, and each name under the RIGHT one -- the content, not
        # the format: a proposal that listed `scripts` as a repository to declare is the
        # wrong answer however well formatted.
        prose_part = out.split("Probably prose")[1]
        self.assertIn("scripts", prose_part)
        self.assertIn("billing", prose_part)
        self.assertNotIn("core-api", prose_part.split("\n\n")[0])

    def test_a_slug_makes_an_ordinary_word_a_repository(self):
        # `acme/scripts` is a repository however ordinary the word is. A list of words
        # alone would hide the repository genuinely called `scripts`.
        text = "Merged into acme/scripts today.\n"
        _cf, (counts, _r, _p) = counted(vault(reports={END: text})[0])
        self.assertFalse(pr.probably_prose("scripts", counts["scripts"]))

    def test_a_cited_item_makes_an_ordinary_word_a_repository(self):
        text = "| Repository | Merges |\n|---|---|\n| billing | 1 |\n\nAnd billing#214 landed.\n"
        _cf, (counts, _r, _p) = counted(vault(reports={END: text})[0])
        self.assertEqual(sorted(counts["billing"]["items"]), [214])
        self.assertFalse(pr.probably_prose("billing", counts["billing"]))


class NothingWithoutAYes(unittest.TestCase):
    """Proposal 3, the CENTRAL safety property: no config is edited without a confirmation."""

    def test_the_default_run_writes_nothing(self):
        proj, md = vault()
        before = (proj / "_ops.yaml").read_bytes()
        r = helper(md, "--date", "261021")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("PROPOSED, nothing written yet", r.stdout)
        # Byte for byte: a diff of any kind here is the defect the CR calls blocking.
        self.assertEqual((proj / "_ops.yaml").read_bytes(), before)

    def test_write_without_confirm_is_refused_and_writes_nothing(self):
        proj, md = vault()
        before = (proj / "_ops.yaml").read_bytes()
        r = helper(md, "--date", "261021", "--write")
        self.assertEqual(r.returncode, 1)
        self.assertIn("without a yes", r.stderr)
        self.assertEqual((proj / "_ops.yaml").read_bytes(), before)

    def test_a_name_the_reports_did_not_show_is_refused(self):
        proj, md = vault()
        before = (proj / "_ops.yaml").read_bytes()
        r = helper(md, "--date", "261021", "--write", "--confirm", "invented-repo")
        self.assertEqual(r.returncode, 1)
        self.assertIn("invented-repo", r.stderr)
        self.assertEqual((proj / "_ops.yaml").read_bytes(), before)

    def test_a_confirmed_entry_is_written_and_only_that_one(self):
        import yaml
        proj, md = vault()
        r = helper(md, "--date", "261021", "--write", "--confirm", "core-api")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = yaml.safe_load((proj / "_ops.yaml").read_text(encoding="utf-8"))
        urls = [e["url"] for e in d["external_systems"]["repos"]]
        # The hand-written declaration survives; the one confirmed name is added; the
        # ones NOT confirmed (site, proxy, warehouse) are not.
        self.assertEqual(urls, ["github.com/acme/portal", "github.com/acme/core-api"])
        added = d["external_systems"]["repos"][1]
        self.assertEqual(added["reads"], ["pulls", "releases"])      # proposal 4
        self.assertIn("Release branch cut", added["purpose"])
        # The rest of the config is untouched -- including the series this read.
        self.assertEqual(d["external_systems"]["vault_reports"][0]["dir"], "status")
        self.assertTrue(d["workflows"]["post_processing"]["carry_forward"]["enabled"])

    def test_the_written_block_names_its_basis_and_date(self):
        proj, md = vault()
        helper(md, "--date", "261021", "--write", "--confirm", "core-api")
        text = (proj / "_ops.yaml").read_text(encoding="utf-8")
        self.assertIn("CR-151", text)
        self.assertIn("2026-10-06 to 2026-10-21", text)              # the reports read
        self.assertIn(dt.date.today().isoformat(), text)             # the day confirmed
        self.assertIn("named on 12 day(s)", text)

    def test_a_hand_written_comment_survives_the_insertion(self):
        # A YAML re-dump would return the same data with every comment gone, and the
        # operator would be reading a diff about repositories that had also silently
        # deleted the reasons for everything else.
        proj, md = vault(OPS_YAML.replace("    - url: github.com/acme/portal",
                                          "    # the portal; declared by hand in March\n"
                                          "    - url: github.com/acme/portal"))
        helper(md, "--date", "261021", "--write", "--confirm", "core-api")
        text = (proj / "_ops.yaml").read_text(encoding="utf-8")
        self.assertIn("declared by hand in March", text)

    def test_a_project_with_no_repos_block_gets_one(self):
        import yaml
        proj, md = vault(OPS_YAML.replace("  repos:\n    - url: github.com/acme/portal\n"
                                          "      reads: [issues, pulls]\n", ""))
        r = helper(md, "--date", "261021", "--write", "--confirm", "core-api,site")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = yaml.safe_load((proj / "_ops.yaml").read_text(encoding="utf-8"))
        self.assertEqual([e["url"] for e in d["external_systems"]["repos"]],
                         ["github.com/acme/core-api", "github.com/acme/site"])
        self.assertEqual(d["external_systems"]["vault_reports"][0]["name"], "Daily status")

    def test_a_repository_with_no_organisation_is_marked_not_invented(self):
        # `proxy` is named only as a table cell and an item citation, so nothing in the
        # window says which organisation it is under. The entry has to SAY so rather
        # than carry an organisation the script picked.
        cf, (counts, read, problems) = counted(vault()[0])
        self.assertTrue(pr.no_url("proxy", counts["proxy"], pr.declared_slugs(cf)))
        self.assertFalse(pr.no_url("core-api", counts["core-api"], pr.declared_slugs(cf)))
        out = pr.proposal(cf, counts, read, problems, 14)
        row = next(l for l in out.splitlines() if l.strip().startswith("proxy"))
        self.assertIn("cannot be read", row)
        written = pr.block([("proxy", counts["proxy"])], "12 report(s)", END, {})
        self.assertNotIn("github.com/acme/proxy", written)
        self.assertIn("ORGANISATION-NOT-IN-THE-REPORTS", written)


class Rerun(unittest.TestCase):
    """Proposal 5: a re-run proposes again, and never removes."""

    def test_a_declared_repository_already_named_is_not_proposed_again(self):
        proj, md = vault()
        helper(md, "--date", "261021", "--write", "--confirm", "core-api")
        r = helper(md, "--date", "261021")
        self.assertEqual(r.returncode, 0, r.stderr)
        confirm_line = next(l for l in r.stdout.splitlines() if "--confirm" in l)
        self.assertNotIn("core-api", confirm_line)
        self.assertIn("site", confirm_line)
        # ...and the declared one is still SHOWN, as declared.
        row = next(l for l in r.stdout.splitlines() if l.strip().startswith("core-api"))
        self.assertIn("declared", row)
        self.assertNotIn("NOT DECLARED", row)

    def test_a_quiet_declared_repository_is_named_and_never_removed(self):
        import yaml
        proj, md = vault()
        before = yaml.safe_load((proj / "_ops.yaml").read_text(encoding="utf-8"))
        cf, (counts, read, problems) = counted(proj, days=40)
        # `portal` is in the reports; a repository the reports never name is quiet.
        self.assertEqual(pr.quiet(cf, counts, 40), [])
        cf2 = dict(cf)
        cf2["ext"] = dict(cf["ext"])
        cf2["ext"]["repos"] = cf["ext"]["repos"] + [{"url": "github.com/acme/archive"}]
        self.assertEqual(pr.quiet(cf2, counts, 40), ["archive"])
        out = pr.proposal(cf2, counts, read, problems, 40)
        self.assertIn("NOT removed", out)
        self.assertIn("archive", out.split("NOT removed")[1])
        # Printing it changed nothing on disk.
        self.assertEqual(yaml.safe_load((proj / "_ops.yaml").read_text(encoding="utf-8")), before)

    def test_a_short_window_never_calls_a_repository_quiet(self):
        # A two-day window that names one repository is not evidence that the others
        # are quiet, and a list of seven "quiet" repositories read once is read never.
        cf, (counts, _r, _p) = counted(vault()[0])
        cf2 = dict(cf)
        cf2["ext"] = dict(cf["ext"])
        cf2["ext"]["repos"] = cf["ext"]["repos"] + [{"url": "github.com/acme/archive"}]
        self.assertEqual(pr.quiet(cf2, counts, 14), [])
        self.assertEqual(pr.quiet(cf2, counts, 2), [])


class PreFlight(unittest.TestCase):
    """Proposal 6: the pre-flight warns, and does not refuse."""

    def test_an_undeclared_repository_named_on_many_days_is_a_row(self):
        proj, md = vault()
        rows = ba.check_rows(ba.config(md), md, [("261021", md / "261021-daily-standup.md")], END)
        hits = {n.split(": ", 1)[1]: (st, t) for n, st, t, _d in rows if n.startswith("repository: ")}
        # The four undeclared ones the reports name on twelve days, and not the
        # declared one, not the prose, not the area table's cells.
        self.assertEqual(sorted(hits), ["core-api", "proxy", "site", "warehouse"])
        self.assertEqual(hits["core-api"], (ba.UNDECLARED, "12d named"))
        self.assertNotIn("portal", hits)
        self.assertNotIn("billing", hits)
        self.assertNotIn("mobile", hits)

    def test_the_warning_names_the_helper_to_run(self):
        proj, md = vault()
        rows = ba.check_rows(ba.config(md), md, [("261021", md / "261021-daily-standup.md")], END)
        detail = next(d for n, _s, _t, d in rows if n == "repository: core-api")
        self.assertIn("propose_repos.py", detail)
        self.assertIn("not declared", detail)

    def test_the_warning_never_fails_the_check(self):
        # The declared sources are all there; a config short of a source is a judgement
        # for the operator, and a pre-flight that refused the build over it would block
        # a morning on a declaration only a person can write.
        self.assertNotIn(ba.UNDECLARED, ba.CHECK_BAD)
        proj, md = vault()
        rows = ba.check_rows(ba.config(md), md, [("261021", md / "261021-daily-standup.md")], END)
        undeclared_rows = [r for r in rows if r[1] == ba.UNDECLARED]
        self.assertTrue(undeclared_rows)
        self.assertFalse(any(r[1] in ba.CHECK_BAD for r in undeclared_rows))
        # ...and the row renders in the table the check prints.
        table = ba.check_table(rows)
        self.assertIn("repository: core-api", table)
        self.assertIn(ba.UNDECLARED, table)

    def test_a_few_days_is_not_yet_a_finding(self):
        # Two days is a coincidence; the threshold is strictly more than three.
        proj, md = vault(days=2)
        rows = ba.check_rows(ba.config(md), md, [("261021", md / "261021-daily-standup.md")], END)
        self.assertEqual([r for r in rows if r[1] == ba.UNDECLARED], [])

    def test_a_project_with_no_declared_report_still_gets_a_check(self):
        proj, md = vault(OPS_YAML.split("  vault_reports:")[0])
        rows = ba.check_rows(ba.config(md), md, [("261021", md / "261021-daily-standup.md")], END)
        self.assertEqual([r for r in rows if r[1] == ba.UNDECLARED], [])
        self.assertTrue(any(n == "previous note" for n, _s, _t, _d in rows))

    def test_the_row_and_the_proposal_agree_on_the_day_count(self):
        # One window reader. Two counts that could drift is exactly the defect this
        # repository warns about.
        proj, md = vault(days=7)
        cf = ba.config(md)
        rows = ba.check_rows(cf, md, [("261021", md / "261021-daily-standup.md")], END)
        from_row = {n.split(": ", 1)[1]: t for n, _s, t, _d in rows if n.startswith("repository: ")}
        _cf, (counts, _r, _p) = counted(proj)
        for name, when in from_row.items():
            self.assertEqual(when, f"{len(counts[name]['days'])}d named", name)


class Additive(unittest.TestCase):
    """A project declaring none of CR-151's keys behaves exactly as before."""

    def test_no_vault_reports_means_no_new_row_and_no_counts(self):
        proj, md = vault(OPS_YAML.split("  vault_reports:")[0])
        cf = ba.config(md)
        self.assertEqual(pr.count_window(cf, pr.working_days_back(END, 14), END), ({}, [], []))
        self.assertEqual(ba._undeclared_repos(cf, END), [])

    def test_the_default_reads_scope_is_conservative(self):
        # Proposal 4: a repository's issues are its own team's working surface, and
        # `issues` is added by the operator, never by the proposal.
        self.assertEqual(pr.DEFAULT_READS, ["pulls", "releases"])
        written = pr.block([("site", {"slugs": {"acme/site"}, "days": {END},
                                      "items": set(), "purpose": "the public site"})],
                           "12 report(s)", END, {})
        self.assertIn("reads: [pulls, releases]", written)
        self.assertNotIn("issues", written)


class Documented(unittest.TestCase):
    """The behaviour is in the skill, not only in the script."""

    def test_the_skill_documents_the_helper_and_the_confirmation(self):
        text = (OPS / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("propose_repos.py", text)
        self.assertIn("CR-151", text)
        self.assertIn("--confirm", text)
        self.assertIn("probably prose", text)
        schema = (ROOT / "skills" / "ops-config" / "schema.md").read_text(encoding="utf-8")
        self.assertIn("CR-151", schema)


if __name__ == "__main__":
    unittest.main()
