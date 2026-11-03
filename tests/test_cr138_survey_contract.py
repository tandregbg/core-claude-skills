"""CR-138: the task audit's shape is contracted in the skill, not only in the script.

The format drifted twice because `skills/inbox/SKILL.md` said nothing about it, and
the operator was the only detector. These assertions are that detector -- and they
only are one if they compare the section against the generator rather than against
themselves. A first pass asserted that English phrases were present in SKILL.md;
three claims in the section were then rewritten into values the script never emits
and every assertion still passed. So the contract is checked the only way that
binds it: build a small vault, run `survey.py` over it, and require that what the
section documents is what the script printed.

**Re-derived 2026-11-03 for CR-162 and CR-163 (v1.93.1).** CR-162 replaced
`render_table()` with `render_living()` -- venture first, context beneath, the state
travelling with the row in `Läge` instead of defining the sections -- and rewrote the
section around the new shape, but this file still called the removed function, so every
class errored and the detector was off for a week. Renaming the call was not enough:
fourteen assertions described the superseded output. Re-deriving them found five claims
the rewritten section still carried from the old one, each corrected in SKILL.md in the
same release -- the `Läge` dash, the per-state header table, the context ordering, the
truncation width, and a `### Utanför tabellen` list the living view does not emit.

Invented data throughout: Acme, Bravo, Bob, Ravi, Dee.

    python3 -m unittest discover -s tests
"""
import datetime
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "inbox"))
import survey as sv  # noqa: E402

SKILL = (ROOT / "skills" / "inbox" / "SKILL.md").read_text(encoding="utf-8")
TODAY = datetime.date(2026, 10, 21)
# The vault's own view names, from settings rather than from a literal here (CR-171).
VIEW_FILES = sv.view_files(ROOT / "nonexistent-vault")

# One open entry per state, so every branch of render_living is exercised: #1 is
# overdue, #2 has `created` and no date, #3 has a priority and no date, #4 has
# neither, #5 is dated forward. #6 is closed and must not appear anywhere. #7 is a
# standing chore (CR-163). #8 carries a `due` the date parser cannot read. #9 is
# long enough to be truncated, and sits in a context the venture map does not know.
LEDGER = """tasks:
  - id: 1
    task: Ring Bob om avtalet
    context: acme
    status: pending
    due: "261001"
    created: "260901"
  - id: 2
    task: Bolagen och tankar framat
    context: bravo
    status: pending
    created: "260801"
  - id: 3
    task: Skicka underlaget till Ravi
    context: bravo
    status: pending
    priority: P1
    created: "260901"
  - id: 4
    task: Dee och hennes onskelista
    context: acme
    status: pending
  - id: 5
    task: Boka resan
    context: acme
    status: pending
    due: "271201"
    created: "261001"
  - id: 6
    task: Kolla gamla siffror
    context: acme
    status: completed
    completed: "261021"
  - id: 7
    task: Veckovis genomgang av registret
    context: rutin
    status: pending
    recurring: true
  - id: 8
    task: Trasigt datum
    context: acme
    status: pending
    due: snart
  - id: 9
    task: En mycket lang uppgift som skrivits ut i sin helhet och som darfor maste kortas innan den skrivs in
    context: nyttprojekt
    status: pending
    created: "260801"
"""

REGISTER = """items:
  - id: in-1
    title: A note from a team member
    file: note-one.md
    status: pending
    created: "261001"
  - id: in-2
    title: A filed note
    file: note-two.md
    status: filed
    created: "260901"
    output_file: out.md
"""

# The map and the portfolio are the operator's, declared in the vault; the audit
# groups by what they say, so the fixture has to carry both (CR-162).
KARTA = """karta:
  acme: Acme
  bravo: Bravo
  rutin: kontextstyrd
"""

PORTFOLIO = """# Projekt

## PORTFÖLJEN

| Projekt | Verksamhet | Läge | Nästa | Ägare | Datum | Not |
|---|---|---|---|---|---|---|
| Acme Omstart | Acme | aktiv | — | — | — | — |

### Sammanräkning
"""

OPEN_IDS = ("#1", "#2", "#3", "#4", "#5", "#7", "#8", "#9")
CLOSED_ID = "#6"
# The five words the section documents for `Läge`, one per state.
LAGE_WORDS = ("förfallen", "prio utan datum", "ingen ålder", "odaterad", "framåt")


def section():
    """The `/inbox survey` section, up to the next sibling heading."""
    start = SKILL.index("### `/inbox survey`")
    rest = SKILL[start + 4:]
    nxt = rest.find("\n### `/inbox")
    return rest[:nxt] if nxt != -1 else rest


def flat(text):
    """One line, so an assertion is about the words and not the line wrapping."""
    return " ".join(text.split())


def body_rows(audit):
    """The entry rows: every line that opens on an id cell."""
    return [l for l in audit.splitlines() if l.startswith("| `#")]


def cells(row):
    return [c.strip() for c in row.split("|")[1:-1]]


class Fixture(unittest.TestCase):
    """A vault on disk, so the assertions run the generator and not a stand-in."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.vault = Path(cls._tmp.name)
        inbox = cls.vault / "_inbox"
        inbox.mkdir()
        (inbox / "_tasks.yaml").write_text(LEDGER, encoding="utf-8")
        (inbox / "_inbox.yaml").write_text(REGISTER, encoding="utf-8")
        (inbox / "note-one.md").write_text("a captured note\n", encoding="utf-8")
        (cls.vault / "_config").mkdir()
        (cls.vault / "_config" / "verksamhet-karta.yaml").write_text(KARTA, encoding="utf-8")
        (cls.vault / "_INDEX-projekt.md").write_text(PORTFOLIO, encoding="utf-8")
        cls.states = sv.all_open(cls.vault, TODAY)
        cls.survey = sv.survey(cls.vault, TODAY)
        cls.audit = sv.render_living(cls.vault, cls.survey, cls.states, TODAY)
        cls.section = section()
        cls.flat_section = flat(cls.section)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_cli(self, *flags):
        """`survey.py` through `main()`, which is where the flag order lives."""
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = sv.main(["--vault", str(self.vault), "--today", TODAY.isoformat(), *flags])
        self.assertEqual(rc, 0)
        return buf.getvalue()

    def shape_row(self, element):
        for line in self.section.splitlines():
            if line.startswith(f"| {element} |"):
                return line
        self.fail(f"the shape table has no {element} row")


class TheFixtureIsWorthTrusting(Fixture):
    """If the vault does not produce every documented case, the rest proves nothing."""

    def test_the_audit_is_what_the_cli_prints(self):
        self.assertEqual(self.audit.strip(), self.run_cli("--table", "--markdown").strip())

    def test_the_fixture_exercises_a_mapped_and_an_unmapped_venture(self):
        self.assertIn("## Acme — ", self.audit)
        self.assertIn("## Utan post i kartan — ", self.audit)


class SectionPlacement(Fixture):
    def test_the_section_exists_next_to_triage(self):
        self.assertIn("### `/inbox survey`", SKILL)
        self.assertLess(SKILL.index("### `/inbox triage"), SKILL.index("### `/inbox survey`"))
        self.assertLess(SKILL.index("### `/inbox survey`"), SKILL.index("### `/inbox help`"))

    def test_names_the_generator_and_the_stable_filename(self):
        # CR-171: the stable filename is the vault's, so the section names the SETTINGS
        # KEY and never the name. Asserting the name here is what made this test file one
        # of the two places the name leaked into the suite.
        self.assertIn("survey.py", self.section)
        self.assertIn("view_files.tasks_view", self.section)
        self.assertIn("stable filename", self.section)
        for name in VIEW_FILES.values():
            self.assertNotIn(name, self.section, "a vault's display filename is not ours to spell")

    def test_the_failure_is_named_in_one_line(self):
        self.assertIn("a subset presented in this file's name is a regression",
                      self.flat_section)

    def test_relationship_to_the_triage_doc_is_stated(self):
        self.assertIn("view_files.triage", self.flat_section)
        self.assertIn("what do I do now", self.flat_section)
        self.assertIn("what is there", self.flat_section)


class DocumentedRowIsTheGeneratedRow(Fixture):
    """DEFECT 3: the documented Row has to be the row the script prints."""

    def test_the_header_row_is_quoted_from_the_output(self):
        # `| # | Verksamhet | Projekt | Läge | Uppgift | Förslag | | Godta |` -- the
        # signal column's header cell is empty. The section writes the pipes escaped,
        # as a markdown table cell must.
        self.assertIn("| # | Verksamhet | Projekt | Läge | Uppgift | Förslag | | Godta |", self.audit)
        self.assertIn(r"`# \| Verksamhet \| Projekt \| Läge \| Uppgift \| Förslag \| \| Godta`",
                      self.section)

    def test_the_section_does_not_claim_a_signal_column_heading(self):
        # The falsified contract an earlier verifier planted was a `✓/?` header cell.
        # It is not in the output, so it must not be in the section either.
        self.assertNotIn("| Förslag | ✓/? | Godta |", self.audit)
        self.assertNotIn(r"Förslag \| ✓/? \| Godta", self.section)
        self.assertIn("header cell is empty", self.flat_section)

    def test_every_row_has_the_documented_eight_cells(self):
        rows = body_rows(self.audit)
        self.assertEqual(len(rows), len(OPEN_IDS))
        for r in rows:
            self.assertEqual(len(cells(r)), 8, r)
        self.assertIn("Eight cells", self.section)

    def test_a_forward_dated_entry_is_a_row_like_any_other(self):
        # CR-162: the flat `DATERADE FRAMÅT` section is gone, so the three-cell
        # exception has nothing to attach to and the entry is decidable.
        self.assertNotIn("## DATERADE FRAMÅT", self.audit)
        forward = [r for r in body_rows(self.audit) if "framåt" in cells(r)[3]]
        self.assertEqual(len(forward), 1)
        self.assertEqual(len(cells(forward[0])), 8)
        self.assertEqual(cells(forward[0])[5], "**LÅT STÅ**")
        row = self.shape_row("A forward-dated entry")
        self.assertIn("Carries a `Godta` cell like any other", row)
        self.assertIn("framåt YYMMDD", row)

    def test_the_cells_are_in_the_documented_order(self):
        row = next(r for r in body_rows(self.audit) if cells(r)[0].startswith("`#1`"))
        venture, project, lage, task, proposal, mark, godta = cells(row)[1:]
        self.assertEqual(venture, "Acme")
        self.assertEqual(project, "Acme Omstart")
        self.assertTrue(lage.startswith("förfallen"), lage)
        self.assertEqual(task, "Ring Bob om avtalet")
        self.assertTrue(proposal.startswith("**") and proposal.endswith("**"), proposal)
        self.assertIn(mark, ("✓", "?"))
        self.assertEqual(godta, "")

    def test_an_unmapped_context_writes_a_dash_in_both_columns(self):
        row = next(r for r in body_rows(self.audit) if cells(r)[0] == "`#9`")
        self.assertEqual(cells(row)[1], "—")
        self.assertEqual(cells(row)[2], "—")
        self.assertIn("a dash where the context maps to neither", self.flat_section)

    def test_the_documented_truncation_width_is_the_real_one(self):
        row = next(r for r in body_rows(self.audit) if cells(r)[0] == "`#9`")
        task = cells(row)[4]
        self.assertTrue(task.endswith("…"), task)
        self.assertLessEqual(len(task), 71)
        self.assertNotIn(" …", task, "truncation cuts at a word boundary")
        self.assertIn("truncated to 70 characters", self.flat_section)


class TheStateTravelsWithTheRow(Fixture):
    """CR-162: the five states are unchanged; a state is no longer a section."""

    def test_no_state_is_a_section_heading_any_more(self):
        for st in sv.ORDER:
            self.assertNotIn(f"## {st}", self.audit)
        self.assertIn("a state is no longer a section", self.flat_section)

    def test_the_sections_are_ventures_and_the_subsections_contexts(self):
        self.assertRegex(self.audit, r"\n## [^\n]+ — \d+ poster\n")
        self.assertRegex(self.audit, r"\n### `[^`]+` — \d+")
        row = self.shape_row("Grouping")
        self.assertIn("## <Verksamhet>", row)
        self.assertIn("Utan post i kartan", row)

    def test_every_lage_cell_opens_on_a_documented_word(self):
        documented = self.shape_row("States")
        for r in body_rows(self.audit):
            lage = cells(r)[3]
            self.assertTrue(any(lage.startswith(w) for w in LAGE_WORDS), lage)
            self.assertIn(lage.split()[0], documented)

    def test_every_documented_word_is_one_the_script_emits(self):
        emitted = {cells(r)[3] for r in body_rows(self.audit)}
        for word in LAGE_WORDS:
            self.assertTrue(any(l.startswith(word) for l in emitted),
                            f"the section documents `{word}`, which the script did not print")

    def test_the_five_states_are_still_the_scripts_five(self):
        self.assertEqual(len(sv.ORDER), 5)
        self.assertEqual(len(LAGE_WORDS), 5)
        self.assertIn("The five states are unchanged", self.section)

    def test_every_documented_bucket_name_is_one_propose_for_can_return(self):
        emitted = {sv.propose_for(st, r, TODAY)[0]
                   for st, rows in self.states.items() for r in rows}
        self.assertTrue(emitted)
        for b in emitted:
            self.assertIn(b, self.section)


class DocumentedCoverageRule(Fixture):
    def test_coverage_rule_is_exactly_once_and_the_output_obeys_it(self):
        self.assertIn("appears exactly once", self.flat_section)
        for i in OPEN_IDS:
            self.assertEqual(self.audit.count(f"| `{i}`"), 1,
                             f"{i} is not in the audit exactly once")
        self.assertNotIn(f"`{CLOSED_ID}`", self.audit)

    def test_the_header_count_is_the_ledgers_own_open_count(self):
        self.assertIn(f"**{self.survey['ledger']['open']} öppna poster.**", self.audit)
        self.assertEqual(self.survey["ledger"]["open"], len(OPEN_IDS))
        self.assertIn("the ledger's own open count", self.flat_section)

    def test_the_venture_counts_add_up_to_the_open_count(self):
        counts = [int(m) for m in re.findall(r"\n## [^\n]+ — (\d+) poster\n", self.audit)]
        self.assertEqual(sum(counts), len(OPEN_IDS))


class DocumentedGodtaColumn(Fixture):
    def test_godta_is_documented_and_left_empty_in_the_output(self):
        self.assertIn("`Godta`", self.flat_section)
        self.assertIn("Left **empty** by the generator", self.flat_section)
        for token in ("`261027`", "`R`", "`Ö`", "`S`"):
            self.assertIn(token, self.flat_section)
        # The legend the section quotes is the legend the generator prints.
        self.assertIn("**Godta:** tom = förslaget gäller.", self.audit)
        self.assertIn("`261027`", self.audit)
        for row in body_rows(self.audit):
            self.assertTrue(row.endswith("| |"), row)

    def test_the_signal_mark_is_in_the_body_and_the_operator_reads_guesses_first(self):
        marks = {cells(r)[6] for r in body_rows(self.audit)}
        self.assertTrue(marks <= {"✓", "?"}, marks)
        self.assertIn("The operator reads the guesses first", self.section)


class DocumentedLageColumn(Fixture):
    """DEFECT 4 re-derived: `Läge` carries the state, and only overdue carries an age."""

    def test_only_an_overdue_row_carries_an_age(self):
        by_id = {cells(r)[0]: cells(r)[3] for r in body_rows(self.audit)}
        self.assertEqual(by_id["`#1`"], "förfallen 20 d")
        for row_id in ("`#2`", "`#3` `P1`", "`#4`"):
            self.assertNotRegex(by_id[row_id], r"\d",
                                f"{row_id} should carry no number in Läge")
        self.assertIn("the operator sees no date here", self.flat_section)

    def test_the_cell_is_the_state_word_and_not_a_dash(self):
        # The claim this replaces said every non-overdue cell is a dash, which was
        # true of CR-138's `Ålder` column and never of CR-162's `Läge`.
        for r in body_rows(self.audit):
            self.assertNotEqual(cells(r)[3], "—")
        row = self.shape_row("`Läge` (was `Ålder`)")
        self.assertIn("state word", row.lower())
        self.assertNotIn("the cell is a dash", row)

    def test_no_undated_state_can_supply_a_well_formed_due_date(self):
        for st, rows in self.states.items():
            if st == "DATERADE FRAMÅT":
                continue
            for r in rows:
                if not r.get("age_days") and r.get("due"):
                    self.assertIsNone(sv.as_date(r["due"]),
                                      f"{st} #{r['id']} could render a well-formed due date")

    def test_an_unparseable_due_prints_its_raw_value_beside_the_state(self):
        # The documented exception: `age_days` stays unset for a `due` the date
        # parser cannot read, so the fallback prints the raw string -- the one way
        # a date reaches this column.
        row = next(r for r in body_rows(self.audit) if cells(r)[0] == "`#8`")
        self.assertEqual(cells(row)[3], "ingen ålder snart")
        self.assertIn("the raw value is printed in this column", self.flat_section)


class DocumentedHeader(Fixture):
    def test_every_documented_header_element_is_in_the_header(self):
        head = self.audit.split("\n## ")[0]
        self.assertIn("öppna poster", head)
        self.assertIn("Godta", head)
        self.assertIn("✓", head)
        self.assertIn("?", head)
        self.assertIn("Förslagen:", head)

    def test_the_movement_line_appears_only_when_something_moved(self):
        head = self.audit.split("\n## ")[0]
        self.assertIn("ur registret.**", head)          # #6 was completed today
        self.assertIn("shown only when something did", self.flat_section)

    def test_the_summary_table_is_per_venture_not_per_state(self):
        # The claim this replaces said per-state, which was CR-138's grouping.
        head = self.audit.split("\n## ")[0]
        self.assertIn("| Verksamhet | Poster | Varav att läsa |", head)
        for st in sv.ORDER:
            self.assertNotIn(st, head)
        self.assertIn("summary table of where the proposals fall, per venture",
                      self.flat_section)

    def test_the_header_repeats_the_command_that_regenerates_it(self):
        self.assertIn("--table --markdown", self.audit.split("\n## ")[0])
        self.assertIn("repeats the command that regenerates it", self.flat_section)


class DocumentedProposals(Fixture):
    def test_a_standing_chore_is_always_let_be_with_a_signal(self):
        # CR-163, documented in the Buckets row.
        row = next(r for r in body_rows(self.audit) if cells(r)[0] == "`#7`")
        self.assertEqual(cells(row)[5], "**LÅT STÅ**")
        self.assertEqual(cells(row)[6], "✓")
        self.assertIn("`recurring: true` is always proposed `LÅT STÅ`", self.flat_section)

    def test_the_proposals_are_labelled_a_reading_and_not_a_decision(self):
        self.assertIn("Förslagen är en läsning av texten, inte ett beslut.", self.flat_section)


class DocumentedOrdering(Fixture):
    def test_contexts_are_ordered_largest_first(self):
        self.assertIn("contexts largest first", self.flat_section)
        for block in self.audit.split("\n## ")[1:]:
            counts = [int(m) for m in re.findall(r"^### `[^`]+` — (\d+)", block, re.M)]
            self.assertEqual(counts, sorted(counts, reverse=True),
                             "a context heading is out of order: %r" % counts)

    def test_rows_are_ordered_oldest_first_within_a_context(self):
        for block in self.audit.split("\n### ")[1:]:
            ages = []
            for r in body_rows(block):
                m = re.match(r"förfallen (\d+) d", cells(r)[3])
                ages.append(int(m.group(1)) if m else 0)
            self.assertEqual(ages, sorted(ages, reverse=True), ages)


class DocumentedViewMatrix(Fixture):
    """DEFECT 2 and DEFECT 5: five views, and `--migration` ignores `--markdown`."""

    def test_the_inventory_says_five_not_four(self):
        self.assertIn("**The views.** Five", self.section)
        self.assertNotIn("**The views.** Four", self.section)

    def test_every_documented_invocation_is_a_distinct_real_view(self):
        views = {
            (): self.run_cli(),
            ("--markdown",): self.run_cli("--markdown"),
            ("--table",): self.run_cli("--table"),
            ("--table", "--markdown"): self.run_cli("--table", "--markdown"),
            ("--undated",): self.run_cli("--undated"),
            ("--undated", "--markdown"): self.run_cli("--undated", "--markdown"),
            ("--migration",): self.run_cli("--migration"),
        }
        self.assertEqual(len(set(views.values())), len(views),
                         "two documented views render the same thing")
        for flags in views:
            cell = "*(no flag)*" if not flags else "`" + " ".join(flags) + "`"
            self.assertIn(f"| {cell} |", self.section)

    def test_migration_does_not_consult_markdown(self):
        self.assertEqual(self.run_cli("--migration"), self.run_cli("--migration", "--markdown"))
        self.assertIn("does not consult `--markdown` at all", self.flat_section)
        self.assertNotIn("| `--migration --markdown` |", self.section)

    def test_table_and_undated_without_markdown_print_json(self):
        json.loads(self.run_cli("--table"))
        json.loads(self.run_cli("--undated"))
        json.loads(self.run_cli())
        self.assertIn("`--table` and `--undated` without `--markdown` print JSON",
                      self.flat_section)

    def test_the_documented_flag_precedence_is_the_order_main_tests(self):
        self.assertEqual(self.run_cli("--migration", "--table", "--markdown"),
                         self.run_cli("--migration"))
        self.assertEqual(self.run_cli("--table", "--undated", "--markdown"),
                         self.run_cli("--table", "--markdown"))
        self.assertIn("`--migration` wins over `--table`, which wins over `--undated`",
                      self.flat_section)

    def test_the_migration_worksheet_is_still_a_different_question(self):
        # CR-162 moved the venture grouping into the audit, so the two views now
        # look alike and the section has to say what still separates them. It is
        # NOT the `Godta` column: the worksheet has one too, which the section
        # denied until this was re-derived. The unit is what differs.
        self.assertIn("verksamhet-karta.yaml", self.section)
        migration = self.run_cli("--migration")
        self.assertIn("| # | Ålder | Uppgift | Godta |", migration)
        self.assertIn("the column is not what tells the two apart", self.flat_section)
        self.assertIn("the worksheet decides a context value, the audit decides an entry",
                      self.flat_section)
        self.assertIn("it maps context *values* to ventures and projects", self.flat_section)


class ScriptDocstringAgreesWithTheSection(Fixture):
    def test_the_docstring_no_longer_calls_the_audit_a_half(self):
        doc = sv.__doc__
        self.assertIn("--table --markdown", doc)
        self.assertIn("SKILL.md", doc)
        self.assertIn("exactly once", doc)

    def test_the_docstring_and_the_section_agree_on_the_view_count(self):
        self.assertIn("Five views", sv.__doc__)
        self.assertIn("**The views.** Five", self.section)

    def test_the_docstring_lists_no_invocation_the_section_omits(self):
        # DEFECT 5 was the two disagreeing. `--migration --markdown` is gone
        # from both, because the flag does nothing on that path.
        self.assertNotIn("--migration --markdown", sv.__doc__)
        for flags in ("--markdown", "--table --markdown", "--undated --markdown", "--migration"):
            self.assertIn(flags, sv.__doc__)


class EveryShapeClaimIsBoundToTheOutput(Fixture):
    """Claims the living view does NOT keep, so the section may not make them."""

    def test_the_section_does_not_promise_an_outside_the_table_list(self):
        # `render_table` ended with `### Utanför tabellen` and its own `Godta`
        # column; `render_living` does not emit it. The register-level findings
        # live in the situation view instead, where they are not decidable.
        self.assertNotIn("### Utanför tabellen", self.audit)
        self.assertIn("odeklarerat statusord", self.run_cli("--markdown"))
        self.assertIn("the living view does not emit it", self.flat_section)

    def test_the_section_does_not_describe_a_flat_forward_dated_section(self):
        self.assertNotIn("is flat, with no context level", self.section)

    def test_the_audit_writes_no_file(self):
        before = sorted(p.name for p in (self.vault / "_inbox").iterdir())
        self.run_cli("--table", "--markdown")
        self.assertEqual(sorted(p.name for p in (self.vault / "_inbox").iterdir()), before)
        self.assertIn("the script writes no file", self.flat_section)

    def test_it_enforces_and_decides_nothing(self):
        self.assertIn("It writes nothing, enforces nothing and decides nothing",
                      self.flat_section)


if __name__ == "__main__":
    unittest.main()
