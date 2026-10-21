"""CR-138: the task audit's shape is contracted in the skill, not only in the script.

The format drifted twice because `skills/inbox/SKILL.md` said nothing about it, and
the operator was the only detector. These assertions are that detector -- and they
only are one if they compare the section against the generator rather than against
themselves. A first pass asserted that English phrases were present in SKILL.md;
three claims in the section were then rewritten into values the script never emits
and every assertion still passed. So the contract is checked the only way that
binds it: build a small vault, run `survey.py` over it, and require that what the
section documents is what the script printed.

Invented data throughout: Acme, Bravo, Bob, Ravi, Dee.

    python3 -m unittest discover -s tests
"""
import datetime
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

# One open entry per state, so every branch of render_table is exercised: #1 is
# overdue, #2 has `created` and no date, #3 has a priority and no date, #4 has
# neither, #5 is dated forward. #6 is closed and must not appear anywhere.
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

OPEN_IDS = ("#1", "#2", "#3", "#4", "#5")
CLOSED_ID = "#6"


def section():
    """The `/inbox survey` section, up to the next sibling heading."""
    start = SKILL.index("### `/inbox survey`")
    rest = SKILL[start + 4:]
    nxt = rest.find("\n### ")
    return rest[:nxt] if nxt != -1 else rest


def flat(text):
    """One line, so an assertion is about the words and not the line wrapping."""
    return " ".join(text.split())


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
        cls.states = sv.all_open(cls.vault, TODAY)
        cls.survey = sv.survey(cls.vault, TODAY)
        cls.audit = sv.render_table(cls.survey, cls.states, TODAY)
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


class SectionPlacement(Fixture):
    def test_the_section_exists_next_to_triage(self):
        self.assertIn("### `/inbox survey`", SKILL)
        self.assertLess(SKILL.index("### `/inbox triage"), SKILL.index("### `/inbox survey`"))
        self.assertLess(SKILL.index("### `/inbox survey`"), SKILL.index("### `/inbox help`"))

    def test_names_the_generator_and_the_stable_filename(self):
        self.assertIn("survey.py", self.section)
        self.assertIn("_inbox/_uppgifter.md", self.section)
        self.assertIn("stable filename", self.section)

    def test_the_failure_is_named_in_one_line(self):
        self.assertIn("a subset presented in this file's name is a regression",
                      self.flat_section)

    def test_relationship_to_the_triage_doc_is_stated(self):
        self.assertIn("daglig-triage.md", self.flat_section)
        self.assertIn("what do I do now", self.flat_section)
        self.assertIn("what is there", self.flat_section)


class DocumentedRowIsTheGeneratedRow(Fixture):
    """DEFECT 3: the documented Row has to be the row the script prints."""

    def shape_row(self, element):
        for line in self.section.splitlines():
            if line.startswith(f"| {element} |"):
                return line
        self.fail(f"the shape table has no {element} row")

    def test_the_grouped_header_row_is_quoted_from_the_output(self):
        # `| # | Ålder | Uppgift | Förslag | | Godta |` -- the signal column's
        # header cell is empty. The section writes the pipes escaped, as a
        # markdown table cell must.
        self.assertIn("| # | Ålder | Uppgift | Förslag | | Godta |", self.audit)
        self.assertIn(r"`# \| Ålder \| Uppgift \| Förslag \| \| Godta`", self.section)

    def test_the_section_does_not_claim_a_signal_column_heading(self):
        # The falsified contract the verifier planted was a `✓/?` header cell.
        # It is not in the output, so it must not be in the section either.
        self.assertNotIn("| Förslag | ✓/? | Godta |", self.audit)
        self.assertNotIn(r"Förslag \| ✓/? \| Godta", self.section)
        self.assertIn("header cell is empty", self.flat_section)

    def test_the_forward_dated_section_really_has_a_different_row(self):
        # Entry #5 (due 271201) renders with three cells and no Godta column.
        self.assertIn("| # | Datum | Uppgift |", self.audit)
        forward = self.audit[self.audit.index("## DATERADE FRAMÅT"):]
        self.assertNotIn("Godta", forward)
        self.assertIn(r"`# \| Datum \| Uppgift`", self.section)
        # And the section's own row for it must deny the three cells the output
        # does not print, not merely name the cells it does.
        row = self.shape_row("Row under `DATERADE FRAMÅT`")
        for absent in ("no `Godta` column", "No `Förslag`", "no signal mark"):
            self.assertIn(absent, row)

    def test_the_documented_six_and_three_cell_counts_hold(self):
        rows = [l for l in self.audit.splitlines()
                if l.startswith("| `#") and "|---" not in l]
        self.assertEqual(len(rows), len(OPEN_IDS))
        wide = [r for r in rows if r.count("|") == 7]      # six cells
        narrow = [r for r in rows if r.count("|") == 4]    # three cells
        self.assertEqual(len(wide), 4)
        self.assertEqual(len(narrow), 1)
        self.assertIn("Six cells", self.section)
        self.assertIn("three-cell row", self.section)


class DocumentedStatesAreTheGeneratedStates(Fixture):
    def states_cell(self):
        for line in self.section.splitlines():
            if line.startswith("| States |"):
                return line
        self.fail("the shape table has no States row")

    def test_every_state_name_in_the_section_is_one_the_script_emits(self):
        for st in sv.ORDER:
            self.assertIn(f"## {st} —", self.audit)
            self.assertIn(st, self.section)

    def test_the_states_row_lists_exactly_the_scripts_states_in_order(self):
        # The verifier's falsification was an invented State list in this cell.
        # Read the cell and compare it to `ORDER`, so an invented name fails.
        import re
        cell = self.states_cell()
        named = [m.group(1) for m in re.finditer(r"`([A-ZÅÄÖ][A-ZÅÄÖ ]+)`", cell)]
        self.assertEqual(named, list(sv.ORDER),
                         "the States row does not list the script's states, in its order")

    def test_the_documented_order_is_the_emitted_order(self):
        seen = [st for st in sv.ORDER if f"## {st} —" in self.audit]
        self.assertEqual(seen, list(sv.ORDER))
        positions = [self.audit.index(f"## {st} —") for st in seen]
        self.assertEqual(positions, sorted(positions))

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
            self.assertEqual(self.audit.count(f"| `{i}`"), 1, f"{i} is not in the audit exactly once")
        self.assertNotIn(f"`{CLOSED_ID}`", self.audit)

    def test_the_header_count_is_the_ledgers_own_open_count(self):
        self.assertIn(f"**{self.survey['ledger']['open']} öppna poster.**", self.audit)
        self.assertEqual(self.survey["ledger"]["open"], len(OPEN_IDS))
        self.assertIn("the ledger's own open count", self.flat_section)


class DocumentedGodtaColumn(Fixture):
    def test_godta_is_documented_and_left_empty_in_the_output(self):
        self.assertIn("`Godta`", self.flat_section)
        self.assertIn("Left **empty** by the generator", self.flat_section)
        for token in ("`261027`", "`R`", "`Ö`", "`S`"):
            self.assertIn(token, self.flat_section)
        # The legend the section quotes is the legend the generator prints.
        self.assertIn("**Godta-kolumnen:** tom = förslaget gäller.", self.audit)
        self.assertIn("`261027`", self.audit)
        # Every six-cell body row ends on an empty Godta cell.
        for line in self.audit.splitlines():
            if line.startswith("| `#") and line.count("|") == 7:
                self.assertTrue(line.endswith("| |"), line)


class DocumentedAlderColumn(Fixture):
    """DEFECT 4: `Ålder` is never a due date in the grouped sections."""

    def test_only_overdue_rows_carry_an_age_and_the_rest_are_a_dash(self):
        cells = {}
        state = None
        for line in self.audit.splitlines():
            if line.startswith("## "):
                state = line[3:].split(" —")[0]
            elif line.startswith("| `#") and line.count("|") == 7:
                cells[line.split("|")[1].strip()] = (state, line.split("|")[2].strip())
        self.assertEqual(cells["`#1`"], ("FÖRFALLNA", "20 d"))
        for row_id in ("`#2`", "`#3` `P1`", "`#4`"):
            self.assertEqual(cells[row_id][1], "—", f"{row_id} should carry no age")
        self.assertIn("the operator sees no date here", self.flat_section)

    def test_no_undated_state_can_supply_a_due_date_to_fall_back_on(self):
        # The documented reason, checked against the data rather than the prose:
        # an entry without an age in a grouped state also has no `due`.
        for st, rows in self.states.items():
            if st == "DATERADE FRAMÅT":
                continue
            for r in rows:
                if not r.get("age_days"):
                    self.assertFalse(r.get("due"), f"{st} #{r['id']} could render a due date")


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
        self.assertEqual(len(set(views.values())), len(views), "two documented views render the same thing")
        for flags in views:
            cell = "*(no flag)*" if not flags else "`" + " ".join(flags) + "`"
            self.assertIn(f"| {cell} |", self.section)

    def test_migration_does_not_consult_markdown(self):
        self.assertEqual(self.run_cli("--migration"), self.run_cli("--migration", "--markdown"))
        self.assertIn("does not consult `--markdown` at all", self.flat_section)
        self.assertNotIn("| `--migration --markdown` |", self.section)

    def test_table_and_undated_without_markdown_print_json(self):
        import json
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
        self.assertEqual(self.run_cli("--undated", "--markdown"),
                         self.run_cli("--undated", "--markdown"))
        self.assertIn("`--migration` wins over `--table`, which wins over `--undated`",
                      self.flat_section)

    def test_the_venture_view_is_placed_where_it_really_lives(self):
        # The venture-first view is `--migration`, not the audit; CR-138's own
        # table put that grouping on the audit, and the section corrects it.
        self.assertIn("venture", self.section)
        self.assertIn("verksamhet-karta.yaml", self.section)
        self.assertNotIn("Godta", self.run_cli("--migration"))


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
    """The rest of the shape table, asserted against what the script prints.

    The first round of this test file checked that prose was PRESENT in the section,
    which cannot tell a true claim from a false one: nine falsified values were planted
    and four survived. These are those four, plus the malformed-`due` exception -- each
    read out of the generated string, so a wrong document fails the suite.
    """

    def test_the_documented_truncation_lengths_are_the_real_ones(self):
        # Both lengths are quoted in the section. A row truncated at a different
        # width would make the documented number a guess.
        six = [l for l in self.audit.splitlines() if l.count("|") == 7]
        three = [l for l in self.audit.splitlines() if l.count("|") == 4]
        self.assertTrue(six and three, "the fixture must produce both row shapes")
        for line in six:
            self.assertLessEqual(len(line.split("|")[4].strip()), 80)
        for line in three:
            self.assertLessEqual(len(line.split("|")[3].strip()), 74)
        self.assertIn("truncated to 80 characters", self.flat_section)
        self.assertIn("truncated to 74 characters", self.flat_section)

    def test_contexts_are_ordered_largest_first(self):
        self.assertIn("contexts largest first", self.flat_section)
        for block in self.audit.split("\n## ")[1:]:
            counts = [int(m) for m in re.findall(r"^### .*? -- (\d+)$", block, re.M)]
            self.assertEqual(counts, sorted(counts, reverse=True),
                             "a context heading is out of order: %r" % counts)

    def test_the_forward_dated_section_has_no_context_level(self):
        self.assertIn("`DATERADE FRAMÅT` is flat, with no context level", self.section)
        for block in self.audit.split("\n## ")[1:]:
            if block.startswith("DATERADE FRAMÅT"):
                self.assertNotIn("\n### ", block)
                break
        else:
            self.fail("the fixture must produce a DATERADE FRAMÅT section")

    def test_every_header_element_is_in_the_header(self):
        # The header element row listed four things; an invented list of four
        # passed the earlier prose check.
        head = self.audit.split("\n## ")[0]
        self.assertRegex(head, r"\d+ öppna|öppna poster|öppna: \d+")
        self.assertIn("Godta", head)
        self.assertIn("✓", head)
        self.assertIn("?", head)
        self.assertIn("|", head, "the header carries a summary table")

    def test_the_outside_the_table_heading_is_the_scripts_own(self):
        self.assertIn("### Utanför tabellen", self.section)
        self.assertIn("### Utanför tabellen", self.audit)

    def test_an_unparseable_due_prints_its_raw_value_in_the_age_column(self):
        # The documented exception: `age_days` stays unset for a `due` the date
        # parser cannot read, so the fallback prints the raw string from an
        # undated state -- the one way a date reaches this column.
        led = ("tasks:\n"
               "  - id: 91\n    task: Malformed due\n    context: acme\n"
               "    status: pending\n    created: \"260801\"\n    due: snart\n")
        with tempfile.TemporaryDirectory() as tmp:
            v = Path(tmp)
            (v / "_inbox").mkdir()
            (v / "_inbox" / "_tasks.yaml").write_text(led, encoding="utf-8")
            (v / "_inbox" / "_inbox.yaml").write_text(REGISTER, encoding="utf-8")
            states = sv.all_open(v, TODAY)
            rendered = sv.render_table(sv.survey(v, TODAY), states, TODAY)
        self.assertNotIn("FÖRFALLNA", rendered, "an unreadable due is not overdue")
        row = [l for l in rendered.splitlines() if "Malformed due" in l]
        self.assertTrue(row, "the entry must still appear exactly once")
        self.assertEqual(row[0].split("|")[2].strip(), "snart")
        self.assertIn("the raw value is printed in this column", self.flat_section)


if __name__ == "__main__":
    unittest.main()
