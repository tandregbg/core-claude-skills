"""CR-143: generated text uses the roster's names and pronouns, and a lint checks it.

A team member's name is also a common female name when shortened, and the member is male.
The roster carried the full name, the aliases and a note; an assistant wrote the short form
and the wrong pronoun in two separate drafts, once in each of two sessions, after the roster
and its own notes had both said otherwise. Two incidents in about ten days, both caught by
the operator, none by a check.

What is tested is the REQUIREMENT in both directions, because a pronoun lint fails in two
ways and only one of them is loud: the wrong-pronoun line and the ambiguous short form must
FIRE, and ordinary prose about a team, a plural subject and a possessive like "their
release" must stay CLEAN. A lint that fires on ordinary sentences is switched off, and then
it checks nothing. Invented data.

    python3 -m unittest discover -s tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "skills" / "ops"
sys.path.insert(0, str(OPS))
sys.path.insert(0, str(ROOT / "skills" / "outbox"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_agenda as ba  # noqa: E402
import hygiene_check as hc  # noqa: E402
import resolved as rs  # noqa: E402
from test_cr101_agenda_draft import PULLS, build  # noqa: E402

# Dee is the measured case: male, and the first word of the declared name reads as a common
# female name, so the roster declares both the pronouns and the short form to write instead.
# Ann declares `she`; Cai declares `they`; Bob declares nothing at all, which is the entry
# the lint must leave entirely alone.
PEOPLE = ("people:\n"
          "  - name: Dee Okafor\n    aliases: [Deedee]\n    pronouns: he\n"
          "    canonical_short: Dee O\n"
          "  - name: Ann Rivera\n    pronouns: she\n"
          "  - name: Cai Nordin\n    pronouns: they\n"
          "  - name: Bob Lindqvist\n")
# The login-collision roster (defect pass): `Deepa` is the canonical short form and `Dee` is
# a declared alias, and `dee` is also the GitHub login the repo's data carries -- so every
# repo-detail line the generator writes from `author.login` or `assignees[].login` names a
# short form the lint reports. That is the case the generated-text check missed.
PEOPLE_LOGIN = ("people:\n"
                "  - name: Deepa Raman\n    aliases: [Dee]\n    pronouns: she\n"
                "    canonical_short: Deepa\n"
                "  - name: Bob Lindqvist\n    pronouns: he\n")
LOGIN_ENTRIES = ba.roster_entries({"people": [
    {"name": "Deepa Raman", "aliases": ["Dee"], "pronouns": "she", "canonical_short": "Deepa"},
    {"name": "Bob Lindqvist", "pronouns": "he"},
]})

ENTRIES = ba.roster_entries({"people": [
    {"name": "Dee Okafor", "aliases": ["Deedee"], "pronouns": "he", "canonical_short": "Dee O"},
    {"name": "Ann Rivera", "pronouns": "she"},
    {"name": "Cai Nordin", "pronouns": "they"},
    {"name": "Bob Lindqvist"},
]})


def found(text):
    """Just the descriptions `pronoun_lines` reports for a one-or-more-line text."""
    return [what for _n, what in ba.pronoun_lines(text, ENTRIES)]


class WrongPronounFires(unittest.TestCase):
    """Proposal 2: the line that was actually written has to fail."""

    def test_the_measured_incident_fires_with_both_findings(self):
        # The draft as it was written: the short form AND the wrong pronoun on one line.
        got = found("Dee reviewed the import and she signed it off.")
        self.assertEqual(len(got), 2, got)
        self.assertTrue(any("`dee` is ambiguous" in g and "Dee O" in g for g in got), got)
        self.assertTrue(any("Dee Okafor is `he`" in g and "writes `she`" in g for g in got), got)

    def test_every_gendered_form_of_the_other_pronoun_fires(self):
        for word in ("she", "her", "hers", "herself"):
            got = found(f"Dee Okafor closed the retest and {word} filed the result.")
            self.assertTrue(any("writes `" + word + "`" in g for g in got), (word, got))
        for word in ("he", "him", "his", "himself"):
            got = found(f"Ann Rivera closed the retest and {word} filed the result.")
            self.assertTrue(any("writes `" + word + "`" in g for g in got), (word, got))

    def test_the_finding_names_the_declared_form_so_the_fix_is_in_it(self):
        [got] = found("Ann Rivera led the review; his summary is filed.")
        self.assertIn("Ann Rivera is `she` in the roster", got)
        self.assertIn("writes `his`", got)

    def test_the_declared_pronoun_is_clean(self):
        self.assertEqual(found("Dee Okafor closed the retest and he filed the result."), [])
        self.assertEqual(found("Ann Rivera closed the retest and she filed the result."), [])

    def test_an_alias_resolves_to_the_same_person(self):
        # `Deedee` is a declared alias of a `he` entry, so a gendered pronoun after it is
        # the same wrong fact -- resolution is the roster's, not the full name's.
        got = found("Deedee reviewed the import and her note is attached.")
        self.assertTrue(any("Dee Okafor is `he`" in g for g in got), got)

    def test_a_first_name_resolves_like_every_other_roster_reader(self):
        got = found("Ann picked up the retest and his summary followed.")
        self.assertTrue(any("Ann Rivera is `she`" in g for g in got), got)


class OrdinaryProseStaysClean(unittest.TestCase):
    """The other direction, and the one that decides whether the lint survives.

    `they` is the ordinary plural as well as a singular pronoun, so a naive rule fires on
    almost every sentence a standup writes. Each of these is a sentence somebody writes
    every day; a finding on any of them is a lint that gets switched off.
    """

    def test_plural_they_them_their_is_never_a_finding(self):
        for line in ("The team said they would finish the import on Friday.",
                     "Ann Rivera and Dee Okafor agreed; their release is Friday.",
                     "Dee Okafor asked the reviewers and they came back the same day.",
                     "Ann Rivera owns the rollout and their release notes are drafted.",
                     "Cai Nordin filed the retest and they closed it."):
            self.assertEqual(found(line), [], line)

    def test_a_plural_subject_of_two_declared_people_is_not_a_finding(self):
        # The pronoun may belong to either, so it is a sentence to rewrite and not a wrong
        # fact. Both orders, and with the gendered pronoun of each declaration.
        for line in ("Ann Rivera and Dee Okafor met; he agreed to the scope.",
                     "Dee Okafor and Ann Rivera met; she agreed to the scope.",
                     "Dee Okafor, Ann Rivera and Bob Lindqvist reviewed it; his point stands."):
            self.assertEqual(found(line), [], line)

    def test_a_gendered_pronoun_with_nobody_declared_on_the_line_is_not_a_finding(self):
        for line in ("He reviewed the import before the standup.",
                     "The reporter said her account was locked.",
                     "Bob Lindqvist closed the retest and she asked for a second pass."):
            self.assertEqual(found(line), [], line)

    def test_a_pronoun_before_the_name_is_not_read_back_onto_it(self):
        # A previous subject and a new one. Reading the pronoun forward onto the later name
        # is how a lint starts being wrong about correct prose.
        self.assertEqual(found("He reviewed it; Ann Rivera is next."), [])

    def test_the_full_name_is_never_its_own_ambiguous_short_form(self):
        # `Dee` is the first word of `Dee Okafor`, and a token test reported the one
        # spelling that is never ambiguous, on every line naming the person.
        self.assertEqual(found("Dee Okafor owns the import."), [])

    def test_the_canonical_short_form_is_not_reported_as_the_ambiguous_one(self):
        self.assertEqual(found("Dee O owns the import."), [])

    def test_a_fenced_block_is_skipped(self):
        text = "```\nDee reviewed it and she signed off.\n```\nDee O reviewed it and he signed off.\n"
        self.assertEqual(found(text), [])

    def test_a_repo_login_in_an_accountability_slot_is_not_a_short_form(self):
        # DEFECT PASS, condition 5. `dee` is a GitHub login the repo's data carries and
        # also the short form of a declared person, so the lint fired on every
        # repo-detail line THIS MODULE writes -- a wall of findings about the
        # generator's own output, and the operator switches the check off. What rules the
        # line out is an IDENTIFIER BEFORE the name: the line is a statement about an
        # item, and the name after it is the slot filled from `author.login`.
        for line in ("- acme/app #12 Import fix (dee)",
                     "- acme/app #13 Settings page (dee) — waiting 3 day(s)",
                     "- #7 Retest — dee",
                     "| [#3](https://x/3) | api | **open** | dee | Timeout on retry |",
                     "- TICK-9 Import fix — dee"):
            self.assertEqual(found(line), [], line)

    def test_a_login_slot_is_not_a_wrong_pronoun_either(self):
        # The same condition on the other finding: a pronoun after a login slot is not a
        # claim about the person whose short form the login happens to equal.
        for line in ("- acme/app #12 Import fix (dee) and her retest is queued",
                     "- #7 Retest — ann, and his review is pending"):
            self.assertEqual(found(line), [], line)

    def test_prose_about_a_person_still_fires_when_the_id_comes_after(self):
        # The narrowing is POSITION, not "the line mentions an issue": prose names the
        # person FIRST. A rule that could be switched off by appending `#12` is not a
        # rule -- CR-150 records the same correction.
        self.assertTrue(any("`dee` is ambiguous" in g for g in found("Dee closed #12 yesterday.")))
        got = found("Dee Okafor reviewed #12 and she signed it off.")
        self.assertTrue(any("Dee Okafor is `he`" in g for g in got), got)

    def test_a_word_containing_a_pronoun_is_not_a_pronoun(self):
        for line in ("Ann Rivera rewrote the shell script.",
                     "Dee Okafor checked the cache coherence."):
            self.assertEqual(found(line), [], line)


class UnlistedDefaultsToThey(unittest.TestCase):
    """Proposal 3, the heart of the CR: a name does not tell you anyone's pronouns."""

    def test_no_pronouns_declared_means_they(self):
        self.assertEqual(ba.pronoun_of({"name": "Bob Lindqvist"}), "they")
        self.assertEqual(ba.pronoun_of({}), "they")
        self.assertEqual(ba.pronoun_of(None), "they")

    def test_an_undeclared_value_falls_to_they_rather_than_being_honoured(self):
        self.assertEqual(ba.pronoun_of({"name": "Bob", "pronouns": "male"}), "they")
        self.assertEqual(ba.pronoun_of({"name": "Bob", "pronouns": ""}), "they")

    def test_a_declared_value_is_returned_whatever_the_case(self):
        self.assertEqual(ba.pronoun_of({"pronouns": "He"}), "he")
        self.assertEqual(ba.pronoun_of({"pronouns": " she "}), "she")
        self.assertEqual(ba.pronoun_of({"pronouns": "they"}), "they")

    def test_a_they_entry_has_no_gendered_form_to_contradict(self):
        # Cai declares `they`. Neither gendered pronoun is a finding against that entry:
        # `they` is correct for them, and the lint has no second opinion about it.
        for word in ("he", "she", "his", "her"):
            self.assertEqual(found(f"Cai Nordin filed the retest and {word} closed it."), [], word)

    def test_an_entry_declaring_nothing_is_left_entirely_alone(self):
        for word in ("he", "she", "him", "hers"):
            self.assertEqual(found(f"Bob Lindqvist filed it and {word} closed it."), [], word)

    def test_an_unlisted_name_is_not_resolved_at_all(self):
        self.assertEqual(found("Ravi Shankar filed the retest and she closed it."), [])

    def test_no_declarations_at_all_means_no_findings(self):
        plain = ba.roster_entries({"people": [{"name": "Ann Rivera"}, {"name": "Bob Lindqvist"}]})
        self.assertEqual(ba.pronoun_lines("Ann Rivera closed it and his summary followed.", plain), [])


class AmbiguousShortForm(unittest.TestCase):
    """Proposal 1: the ambiguous short form is reported WITH the canonical one."""

    def test_the_canonical_form_is_named_in_the_finding(self):
        [got] = found("Dee owns the import.")
        self.assertIn("`dee` is ambiguous", got)
        self.assertIn("write `Dee O`", got)

    def test_an_alias_short_form_is_reported_too(self):
        [got] = found("Deedee owns the import.")
        self.assertIn("write `Dee O`", got)

    def test_an_entry_declaring_no_canonical_short_is_not_reported(self):
        # Ann declares `pronouns:` but no `canonical_short:`, so the short spelling of her
        # name is the ordinary one and says nothing ambiguous.
        self.assertEqual(found("Ann owns the import."), [])

    def test_short_form_fires_without_any_pronoun_on_the_line(self):
        self.assertTrue(found("Dee owns the import."))


class RosterResolutionIsShared(unittest.TestCase):
    """CR-150's resolver, not a second one: two that disagree is the drift to avoid."""

    def test_entries_partition_exactly_the_roster_cr150_resolves(self):
        cf = {"people": [{"name": "Dee Okafor", "aliases": ["Deedee"]},
                         {"name": "Ann Rivera"}, {"name": "Cai Nordin"}]}
        union = set().union(*(keys for _e, keys in ba.roster_entries(cf)))
        self.assertEqual(union, ba.roster_names(cf))
        self.assertIn("deedee", union)
        self.assertIn("ann", union)          # first name, as CR-150 resolves it

    def test_keys_of_one_entry_is_roster_names_of_one(self):
        e = {"name": "Dee Okafor", "aliases": ["Deedee"]}
        self.assertEqual(ba.keys_of(e), ba.roster_names({"people": [e]}))


class ConfigCheck(unittest.TestCase):
    """An undeclared `pronouns:` value is reported, never guessed at."""

    def test_an_undeclared_value_is_a_config_finding_naming_the_person(self):
        agenda, _ = build("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
                          "milestone:\n  name: Beta\n  date: 2027-01-01\n  set_on: 2026-09-01\n"
                          "people:\n  - name: Dee Okafor\n    pronouns: male\n",
                          note_items="- **Import** - #1 - **Dee Okafor**\n")
        self.assertIn("`pronouns: male` for Dee Okafor", agenda)
        self.assertIn("defaults to `they`", agenda)

    def test_a_declared_value_is_not_a_finding(self):
        agenda, _ = build("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
                          "milestone:\n  name: Beta\n  date: 2027-01-01\n  set_on: 2026-09-01\n"
                          "people:\n  - name: Dee Okafor\n    pronouns: he\n",
                          note_items="- **Import** - #1 - **Dee Okafor**\n")
        self.assertNotIn("is not one of", agenda)


class GeneratedTextIsClean(unittest.TestCase):
    """Proposal 2 over what the generator itself writes, so a renderer that grows a
    pronoun later fails here rather than in somebody's outbox."""

    def test_every_generated_file_is_clean_against_the_roster(self):
        agenda, _ = build("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
                          "      layout: card\n"
                          "milestone:\n  name: Beta\n  date: 2027-01-01\n  set_on: 2026-09-01\n"
                          + PEOPLE,
                          note_items="- **Import** - #1 - **Dee Okafor**\n"
                                     "- **Retest** - #2 - **Ann Rivera**\n")
        meetings = Path(build.last_meetings)
        files = sorted(meetings.glob("260924-*.md"))
        self.assertTrue(files)
        for f in files:
            self.assertEqual(ba.pronoun_lines(f.read_text(encoding="utf-8"), ENTRIES), [], f.name)
        self.assertEqual(ba.pronoun_lines(agenda, ENTRIES), [])

    def test_repo_detail_lines_built_from_logins_are_clean(self):
        # DEFECT PASS: the case this class missed. `external_systems.repos` is declared,
        # the repo's data carries the login `bob`, and the roster declares a person whose
        # `canonical_short:` collides with it -- so every line the generator writes from
        # `author.login` named a short form the lint reported. The orchestrator reproduced
        # it on exactly this shape.
        agenda, _ = build("workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
                          "      layout: card\n"
                          "external_systems:\n  repos:\n"
                          "    - url: https://github.com/acme/app\n"
                          "milestone:\n  name: Beta\n  date: 2027-01-01\n  set_on: 2026-09-01\n"
                          + PEOPLE_LOGIN,
                          repo={"reads": ["issues", "pulls"], "pulls": PULLS,
                                "issues": [{"number": 21, "title": "Import fails on retry",
                                            "state": "OPEN", "createdAt": "2026-09-23T09:00:00Z",
                                            "updatedAt": "2026-09-23T09:00:00Z",
                                            "assignees": [{"login": "dee"}],
                                            "labels": [{"name": "area:api"}]}]},
                          note_items="- **Import** - #1 - **Deepa Raman**\n")
        meetings = Path(build.last_meetings)
        files = sorted(meetings.glob("260924-*.md"))
        self.assertTrue(files)
        # The fixture has to actually put a login on a line, or this test passes for the
        # wrong reason and would stay green against the broken rule. On the card layout
        # the repo detail is in the details file, which is one of the files checked below.
        whole = "\n".join(f.read_text(encoding="utf-8") for f in files)
        self.assertIn("(bob)", whole)
        self.assertIn("dee", whole)
        for f in files:
            self.assertEqual(ba.pronoun_lines(f.read_text(encoding="utf-8"), LOGIN_ENTRIES),
                             [], f.name)
        self.assertEqual(ba.pronoun_lines(agenda, LOGIN_ENTRIES), [])


class ThirdPartyPronoun(unittest.TestCase):
    """DEFECT PASS: the wrong-pronoun rule reads POSITION, and says so.

    A pronoun belonging to a third party, on a line naming one declared person, was
    reported as that person's wrong pronoun. A line-based lint cannot resolve anaphora --
    `Dee led the review; his summary is filed` and `Dee filed the ticket the reporter
    raised; her account was locked` are structurally identical -- so the fix is to narrow
    what counts (the one intervening referent the lint can SEE) and to be honest about the
    rest in the finding itself.
    """

    def test_another_person_named_between_the_name_and_the_pronoun_is_not_a_finding(self):
        for line in ("Dee Okafor spoke to Ravi Shankar and she agreed to the scope.",
                     "Ann Rivera handed it to Ravi Shankar; his review is pending.",
                     "Dee Okafor met Deepa Raman and she signed it off."):
            self.assertEqual(found(line), [], line)

    def test_the_narrowing_does_not_silence_the_measured_incident(self):
        # Nothing is named between the name and the pronoun, so the finding stands. This
        # is the pair that keeps the narrowing from becoming "report nothing".
        got = found("Dee Okafor reviewed the import and she signed it off.")
        self.assertTrue(any("Dee Okafor is `he`" in g for g in got), got)

    def test_the_persons_own_second_word_is_not_an_intervening_person(self):
        # The span read is from the END of the matched spelling. From its start, the
        # name's own second word (`Okafor`) sits inside the span and reads as another
        # person on every line, which reports nothing at all.
        self.assertTrue(found("Dee Okafor reviewed it and she signed off."))

    def test_an_area_or_a_team_is_not_an_intervening_person(self):
        # A single capitalised word is the shape every team, area and total has, which is
        # why only a TWO-word name counts. Narrowing on one word would silence the rule
        # for any sentence mentioning a component.
        got = found("Ann Rivera moved it to Backend and his note followed.")
        self.assertTrue(any("Ann Rivera is `she`" in g for g in got), got)

    def test_the_finding_says_it_read_position_and_not_reference(self):
        # The honest half. A reader who gets a finding about a third party's pronoun has
        # to be able to tell from the finding that the check did not resolve the referent.
        [got] = found("Ann Rivera led the review; his summary is filed.")
        self.assertIn("confirm the pronoun refers to them", got)
        self.assertIn("position, not reference", got)

    def test_a_role_noun_referent_is_a_finding_the_check_admits_it_cannot_resolve(self):
        # Documented residual, asserted so it is a DECISION and not an accident: `the
        # reporter` denotes a person and the lint cannot know that without a word list,
        # which is what CR-150 records going wrong. It fires, and it says why it might be
        # wrong -- it does not claim the pronoun is this person's.
        [got] = found("Dee Okafor filed the ticket the reporter raised; her account was locked.")
        self.assertIn("confirm the pronoun refers to them", got)
        self.assertNotIn("contradicts", got)


class OpsCheckSurface(unittest.TestCase):
    """The `/ops check` finding: the file, the line, and the fix."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / ".claude").mkdir()
        (self.d / ".claude" / "ops-config.yaml").write_text(
            "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n" + PEOPLE,
            encoding="utf-8")

    def write(self, name, body):
        (self.d / name).write_text(body, encoding="utf-8")

    def kinds(self):
        return hc.run(self.d, only=("pronouns",))

    def test_a_wrong_pronoun_in_a_file_is_a_finding_on_its_line(self):
        self.write("recap.md", "# Recap\n\nThe import landed.\nDee Okafor reviewed it and she signed off.\n")
        [f] = self.kinds()
        self.assertEqual(f["kind"], "pronouns")
        self.assertEqual(f["line"], 4)
        self.assertIn("recap.md", f["file"])
        self.assertIn("Dee Okafor is `he`", f["message"])
        self.assertIn("CR-143", f["message"])

    def test_an_ambiguous_short_form_in_a_file_is_a_finding(self):
        self.write("post.md", "# Post\n\nDee owns the import.\n")
        [f] = self.kinds()
        self.assertIn("write `Dee O`", f["message"])

    def test_ordinary_prose_about_a_team_produces_no_finding(self):
        self.write("note.md", "# Standup\n\nThe reviewers came back and they closed it.\n"
                              "Ann Rivera and Dee Okafor agreed; their release is Friday.\n"
                              "Dee O reviewed it and he signed off.\n")
        self.assertEqual(self.kinds(), [])

    def test_a_file_outside_every_declaring_scope_yields_nothing(self):
        other = Path(tempfile.mkdtemp())
        (other / "recap.md").write_text("Dee Okafor reviewed it and she signed off.\n", encoding="utf-8")
        self.assertEqual(hc.run(other, only=("pronouns",)), [])

    def test_the_nearest_declaration_governs(self):
        # A project redeclaring Dee as `she` governs its own files: nearest wins, exactly
        # as CR-150's roster resolution does.
        proj = self.d / "proj"
        (proj / ".claude").mkdir(parents=True)
        (proj / ".claude" / "ops-config.yaml").write_text(
            "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n"
            "people:\n  - name: Dee Okafor\n    pronouns: she\n", encoding="utf-8")
        (proj / "recap.md").write_text("Dee Okafor reviewed it and she signed off.\n", encoding="utf-8")
        self.write("outer.md", "Dee Okafor reviewed it and she signed off.\n")
        got = {Path(f["file"]).name: f["message"] for f in self.kinds()}
        self.assertNotIn("recap.md", got)
        self.assertIn("outer.md", got)

    def test_the_check_is_registered_and_selectable(self):
        self.assertIn("pronouns", hc.CHECKS)
        self.write("recap.md", "Dee Okafor reviewed it and she signed off.\n")
        r = subprocess.run([sys.executable, str(OPS / "hygiene_check.py"), str(self.d),
                            "--json", "--only", "pronouns"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        [f] = json.loads(r.stdout)
        self.assertEqual(f["kind"], "pronouns")


class StagingGate(unittest.TestCase):
    """Proposal 4: the lint runs at staging, so the draft never reaches the outbox."""

    def setUp(self):
        self.vault = Path(tempfile.mkdtemp())
        (self.vault / ".claude").mkdir()
        (self.vault / ".claude" / "ops-config.yaml").write_text(
            "workflows:\n  post_processing:\n    carry_forward:\n      enabled: true\n" + PEOPLE,
            encoding="utf-8")
        self.folder = self.vault / "_outbox" / "260101-proj_recap"
        self.folder.mkdir(parents=True)

    def manifest(self, body):
        return ("# Outbox -- recap\n\n**Status:** draft\n"
                "**Kanonisk källa:** ingen (originalet bor här)\n\n## Body\n\n" + body)

    def test_a_wrong_pronoun_refuses_the_manifest(self):
        got = rs.staging_problems(self.manifest("Dee Okafor reviewed it and she signed off.\n"),
                                  self.folder)
        self.assertTrue(got)
        self.assertTrue(any("Dee Okafor is `he`" in g and "CR-143" in g for g in got), got)

    def test_an_ambiguous_short_form_refuses_the_manifest(self):
        got = rs.staging_problems(self.manifest("Dee owns the import.\n"), self.folder)
        self.assertTrue(any("write `Dee O`" in g for g in got), got)

    def test_a_clean_draft_passes(self):
        self.assertEqual(rs.staging_problems(
            self.manifest("Dee O reviewed it and he signed off.\n"
                          "The reviewers came back and they closed it.\n"
                          "Ann Rivera and Dee Okafor agreed; their release is Friday.\n"),
            self.folder), [])

    def test_the_body_is_checked_not_only_the_header(self):
        # The draft is the body. A gate reading only the header block would pass the one
        # thing it exists to stop.
        text = self.manifest("x\n" * 80 + "Dee Okafor reviewed it and she signed off.\n")
        self.assertTrue(any("Dee Okafor is `he`" in g for g in rs.staging_problems(text, self.folder)))

    def test_cr132_requirements_still_decide_on_their_own(self):
        # Additive: a manifest with a clean body and a missing source is still refused for
        # the source, and the pronoun lint adds nothing to it.
        text = "# t\n\n**Status:** draft\n\nDee O reviewed it and he signed off.\n"
        [got] = rs.staging_problems(text, self.folder)
        self.assertIn("Kanonisk källa", got)

    def test_no_path_means_cr132_alone_and_never_a_guess(self):
        # Validated with no destination: there is no declared roster to read, and the gate
        # does not infer one from a name.
        self.assertEqual(
            rs.staging_problems(self.manifest("Dee Okafor reviewed it and she signed off.\n")), [])

    def test_no_path_does_not_fall_back_to_the_working_directory(self):
        # The nearest config to the PROCESS is not the destination's config (mutation pass):
        # a draft piped in from inside some project's folder would otherwise be judged
        # against that project's roster, which is not where it is going. Run from the vault
        # that DOES declare the roster, with no destination given: still CR-132 alone.
        here = Path.cwd()
        try:
            os.chdir(self.folder)
            self.assertEqual(rs.staging_problems(
                self.manifest("Dee Okafor reviewed it and she signed off.\n")), [])
        finally:
            os.chdir(here)

    def test_no_declaring_config_means_cr132_alone(self):
        bare = Path(tempfile.mkdtemp())
        self.assertEqual(
            rs.staging_problems(self.manifest("Dee Okafor reviewed it and she signed off.\n"), bare),
            [])

    def test_the_cli_refuses_the_file_and_exits_1(self):
        m = self.folder / "_manifest.md"
        m.write_text(self.manifest("Dee Okafor reviewed it and she signed off.\n"), encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "skills" / "outbox" / "resolved.py"),
                            "--validate", str(m)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        out = json.loads(r.stdout)
        self.assertFalse(out["ok"])
        self.assertTrue(any("Dee Okafor is `he`" in p for p in out["problems"]), out)

    def test_the_cli_reads_the_roster_from_the_destination_for_stdin(self):
        script = str(ROOT / "skills" / "outbox" / "resolved.py")
        draft = self.manifest("Dee Okafor reviewed it and she signed off.\n")
        r = subprocess.run([sys.executable, script, "--validate", "-", "--roster", str(self.folder)],
                           input=draft, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertTrue(any("Dee Okafor is `he`" in p
                            for p in json.loads(r.stdout)["problems"]))
        # Without --roster the same draft passes: no destination, no declared roster.
        r = subprocess.run([sys.executable, script, "--validate", "-"],
                           input=draft, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


class OneScopeResolution(unittest.TestCase):
    """DEFECT PASS: the gate and the check resolved the roster by TWO walks, and the two
    disagreed -- which is the outcome this module's own design comment says must not
    happen. `build_agenda.pronoun_scope` is now the one resolution and both call it.

    The reproducer is a project that declares its roster in `.claude/ops-config.yaml` and
    holds NO plain file at its own level. `/ops check`'s scope list came off `walk()`,
    which skips dotted folders, so the project never appeared as a scope and the file was
    read against the VENTURE's roster; the gate's upward walk found the project's. Same
    text, same config, two answers.
    """

    def setUp(self):
        # The venture declares Dee as `he`; the project redeclares them as `she`. The
        # project's only child is the folder holding the manifest, so the project level
        # itself contributes no plain file -- that is the whole reproducer.
        self.vault = Path(tempfile.mkdtemp())
        (self.vault / ".claude").mkdir()
        (self.vault / ".claude" / "ops-config.yaml").write_text(
            "people:\n  - name: Dee Okafor\n    pronouns: he\n", encoding="utf-8")
        self.proj = self.vault / "proj"
        (self.proj / ".claude").mkdir(parents=True)
        self.folder = self.proj / "_outbox" / "260101-proj_recap"
        self.folder.mkdir(parents=True)

    def declare_project(self, pronouns):
        (self.proj / ".claude" / "ops-config.yaml").write_text(
            f"people:\n  - name: Dee Okafor\n    pronouns: {pronouns}\n", encoding="utf-8")

    def manifest(self, body):
        return ("# Outbox -- recap\n\n**Status:** draft\n"
                "**Kanonisk källa:** ingen (originalet bor här)\n\n## Body\n\n" + body)

    def both(self, body):
        """`(gate refuses, check reports)` for one text under one config."""
        text = self.manifest(body)
        (self.folder / "_manifest.md").write_text(text, encoding="utf-8")
        return (bool(rs.staging_problems(text, self.folder)),
                bool(hc.run(self.vault, only=("pronouns",))))

    LINE = "Dee Okafor reviewed it and she signed off.\n"

    def test_a_draft_that_passes_the_gate_cannot_become_a_finding(self):
        # The project declares `she`, so the draft is CORRECT where it is going. The gate
        # passed it and the check then reported it against the venture's `he`.
        self.declare_project("she")
        gate, check = self.both(self.LINE)
        self.assertFalse(gate)
        self.assertFalse(check, "a draft the gate accepted became an /ops check finding")

    def test_a_draft_the_gate_refuses_is_a_finding_too(self):
        # The other direction, so the agreement is not "both stayed silent".
        self.declare_project("he")
        gate, check = self.both(self.LINE)
        self.assertTrue(gate)
        self.assertTrue(check, "a draft the gate refused produced no /ops check finding")

    def test_both_surfaces_resolve_the_same_scope_for_the_same_file(self):
        # Not just the same verdict: the same roster entry, so the two cannot agree today
        # by coincidence and diverge on the next shape.
        self.declare_project("she")
        m = self.folder / "_manifest.md"
        m.write_text(self.manifest(self.LINE), encoding="utf-8")
        self.assertEqual([ba.pronoun_of(e) for e, _k in rs.roster_entries_for(self.folder)],
                         [ba.pronoun_of(e) for e, _k in ba.pronoun_scope(m)])

    def test_the_gate_holds_no_walk_of_its_own(self):
        # The resolution is shared, not copied: the gate resolves through the generator's
        # function, so a change to the rule reaches both surfaces at once.
        self.declare_project("she")
        calls = []
        real = ba.pronoun_scope
        ba.pronoun_scope = lambda path: (calls.append(Path(path)), real(path))[1]
        try:
            rs.roster_entries_for(self.folder)
        finally:
            ba.pronoun_scope = real
        self.assertEqual(len(calls), 1, calls)

    def test_nearest_declaration_still_wins_for_the_shared_resolution(self):
        # The sharing must not have flattened the rule to "the outermost config": a
        # project redeclaring its roster is read against its own.
        self.declare_project("she")
        [(e, _k)] = ba.pronoun_scope(self.folder / "_manifest.md")
        self.assertEqual(ba.pronoun_of(e), "she")

    def test_a_scope_declaring_nothing_checkable_is_passed_over(self):
        # A roster that names people but declares neither `pronouns:` nor
        # `canonical_short:` says nothing the lint can check, so resolution keeps walking
        # up rather than treating the nearer silence as a declaration.
        (self.proj / ".claude" / "ops-config.yaml").write_text(
            "people:\n  - name: Ann Rivera\n", encoding="utf-8")
        [(e, _k)] = ba.pronoun_scope(self.folder / "_manifest.md")
        self.assertEqual(e.get("name"), "Dee Okafor")
        self.assertEqual(ba.pronoun_of(e), "he")

    def test_a_file_above_every_declaration_resolves_to_nothing(self):
        bare = Path(tempfile.mkdtemp())
        self.assertEqual(ba.pronoun_scope(bare / "recap.md"), [])
        self.assertEqual(ba.pronoun_scope(None), [])


class Documented(unittest.TestCase):
    """The config keys and the two surfaces are declared where a reader looks for them."""

    def test_the_roster_fields_are_in_the_schema(self):
        schema = (ROOT / "skills" / "ops-config" / "schema.md").read_text(encoding="utf-8")
        self.assertIn("pronouns: he|she|they", schema)
        self.assertIn("canonical_short:", schema)

    def test_the_check_is_listed_where_the_checks_are_listed(self):
        self.assertIn("pronouns", hc.__doc__)
        self.assertIn("pronouns", (OPS / "SKILL.md").read_text(encoding="utf-8"))

    def test_skill_md_states_what_the_pronoun_check_cannot_know(self):
        # DEFECT PASS: a check whose findings an operator has to dismiss sometimes has to
        # SAY so where the operator reads about it, or the dismissals read as the check
        # being broken and it gets switched off.
        skill = (OPS / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("reads POSITION, not", skill)
        self.assertIn("role noun still produces a finding", skill)
        self.assertIn("cannot resolve", skill)

    def test_skill_md_states_the_login_slot_exclusion(self):
        skill = (OPS / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("IDENTIFIER precedes the name", skill)
        self.assertIn("accountability slot", skill)

    def test_skill_md_states_that_one_resolution_serves_both_surfaces(self):
        skill = (OPS / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pronoun_scope", skill)
        self.assertIn("Two walks", skill)


if __name__ == "__main__":
    unittest.main()


class OnlyAPersonIsASecondReferent(unittest.TestCase):
    """The referent narrowing admits another DECLARED PERSON, not any capitalised phrase.

    The first narrowing matched any two-word Title Case phrase between the name and the
    pronoun, so an artefact or an area title silenced a genuine wrong pronoun -- the
    check reads position, and a thing is not a candidate referent for `he` or `she`.
    """

    def test_another_declared_person_suppresses_the_finding(self):
        # Two candidates, so the pronoun may belong to either: a sentence to rewrite,
        # not a wrong fact, and this check does not resolve reference.
        for line in ("Ann Rivera asked Dee Okafor and she agreed",
                     "Ann Rivera asked Cai Nordin and she agreed"):
            with self.subTest(line=line):
                self.assertEqual(ba.pronoun_lines(line, ENTRIES), [])

    def test_a_title_between_the_name_and_the_pronoun_does_not_suppress_it(self):
        # One candidate only. The capitalised phrase is an artefact or an area.
        for line in ("Ann Rivera reviewed the Payment Webhook and he signed off",
                     "Ann Rivera owns the Release Branch; he confirmed it",
                     "Ann Rivera closed the Refund Rounding ticket, so he is clear"):
            with self.subTest(line=line):
                hits = ba.pronoun_lines(line, ENTRIES)
                self.assertTrue(hits, "a title hid a wrong pronoun")
                self.assertIn("Ann Rivera", hits[0][1])

    def test_an_undeclared_person_also_suppresses_it(self):
        # The roster is not exhaustive: an undeclared colleague is still a candidate
        # referent, so the line is a sentence to rewrite rather than a wrong fact. This
        # is the half the narrowing keeps -- a thing is excluded, a person is not.
        line = "Ann Rivera handed it to Ravi Shankar and he took over"
        self.assertEqual(ba.pronoun_lines(line, ENTRIES), [])

    def test_a_possessive_title_is_a_thing_not_a_person(self):
        line = "Ann Rivera closed its Refund Rounding ticket, so he is clear"
        self.assertTrue(ba.pronoun_lines(line, ENTRIES),
                        "a possessive title is an object and hid a wrong pronoun")
