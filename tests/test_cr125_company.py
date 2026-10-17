"""CR-125: the company profile. Every fixture is an invented company.

    python3 -m unittest discover -s tests
"""
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "company"))
import company_tool as ct  # noqa: E402

TODAY = "2026-10-14"


def init(tmp, level="basic", name="acme"):
    org = Path(tmp) / name
    org.mkdir()
    rc = ct.main(["init", str(org), "--vertical", name, "--level", level, "--today", TODAY])
    return org, rc


def findings(root, **kw):
    out = []
    for d in ct.find_company_dirs(Path(root)):
        out += ct.check_dir(d, kw.get("max_age_days", 365), datetime.date.fromisoformat(kw.get("today", TODAY)))
    return out


class Init(unittest.TestCase):
    def test_all_nine_facets_at_every_level_and_clean_check(self):
        for level, n in (("public", 9), ("basic", 9), ("standard", 9), ("complete", 9)):
            with tempfile.TemporaryDirectory() as tmp:
                org, rc = init(tmp, level)
                self.assertEqual(rc, 0)
                facets = sorted(p.name for p in (org / "_company").glob("*-acme.md"))
                self.assertEqual(len(facets), n, level)
                self.assertEqual(findings(org), [], level)

    def test_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            org, _ = init(tmp)
            marker = org / "_company" / "company-acme.md"
            marker.write_text("hand-written", encoding="utf-8")
            self.assertEqual(ct.main(["init", str(org), "--vertical", "acme"]), 2)
            self.assertEqual(marker.read_text(encoding="utf-8"), "hand-written")

    def test_no_question_text_in_skeleton(self):
        with tempfile.TemporaryDirectory() as tmp:
            org, _ = init(tmp, "complete")
            for p in (org / "_company").glob("*.md"):
                self.assertNotIn("?", p.read_text(encoding="utf-8"), p.name)


class Check(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.org, _ = init(self._t.name)
        self.d = self.org / "_company"

    def tearDown(self):
        self._t.cleanup()

    def kinds(self, **kw):
        return sorted({f["kind"] for f in findings(self.org, **kw)})

    def test_stale_by_age_and_by_status(self):
        self.assertEqual(self.kinds(today="2028-01-01"), ["stale"])
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8").replace("status: draft", "status: stale"), encoding="utf-8")
        self.assertTrue(any("status is stale" in f["message"] for f in findings(self.org)))

    def test_review_date_resets_the_clock(self):
        for p in self.d.glob("*-acme.md"):
            p.write_text(p.read_text(encoding="utf-8").replace("reviewed:\n", "reviewed: 2027-12-30 by owner\n"), encoding="utf-8")
        # "2027-12-30 by owner" is not a bare date: falls back to generated, so still stale
        self.assertEqual(self.kinds(today="2028-01-01"), ["stale"])
        for p in self.d.glob("*-acme.md"):
            p.write_text(p.read_text(encoding="utf-8").replace("reviewed: 2027-12-30 by owner", "reviewed: 2027-12-30"), encoding="utf-8")
        self.assertEqual(self.kinds(today="2028-01-01"), [])

    def test_locked_without_sources(self):
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8").replace("status: draft", "status: final"), encoding="utf-8")
        self.assertEqual(self.kinds(), ["unsourced"])

    def test_frontmatter_enums(self):
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8").replace("facet: company", "facet: nonsense").replace("status: draft", "status: maybe"), encoding="utf-8")
        msgs = [f["message"] for f in findings(self.org) if f["kind"] == "schema"]
        self.assertEqual(len(msgs), 2)

    def test_credential_value_found_reference_not(self):
        (self.d / "README.md").write_text((self.d / "README.md").read_text(encoding="utf-8") + "\napi_key: env:RANKING_KEY_NAME_IS_LONG\n", encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        (self.d / "README.md").write_text((self.d / "README.md").read_text(encoding="utf-8") + "\nsk-" + "a" * 24 + "\n", encoding="utf-8")
        self.assertEqual(self.kinds(), ["credential"])

    def test_sources_schema(self):
        good = ("vertical: acme\nupdated: 2026-01-05\nexclude:\n  - {path: \"_personal/\", reason: \"private\"}\n"
                "sources:\n  - {id: s-site, kind: url, path: \"https://example.com\", authority: public, feeds: [public], note: \"site\"}\n"
                "  - {id: s-context, kind: vault, path: \"vault:notes/\", authority: draft, feeds: []}\n")
        (self.d / "sources.yaml").write_text(good, encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        for bad in (good.replace("authority: public", "authority: maybe"), good.replace("s-site", "site"),
                    good.replace("updated: 2026-01-05\n", ""), good.replace("kind: url", "kind: web"),
                    good + "  - {id: s-site, kind: url, path: x, authority: draft, feeds: []}\n",
                    good.replace("feeds: [public]", "feeds: [public, public]")):
            (self.d / "sources.yaml").write_text(bad, encoding="utf-8")
            self.assertEqual(self.kinds(), ["schema"], bad)

    def test_brands_schema_and_unknown(self):
        good = ("vertical: acme\nbrands:\n  - id: acme\n    name: Acme\n    kind: company\n    relation: masterbrand\n"
                "    status: unknown\n    ip_owner: unknown\n    operator: unknown\n    voice: unknown\n    tokens: unknown\n"
                "    images: unknown\n    design: unknown\n    source: \"owner, 2026-01-05\"\n    domains:\n"
                "      - {domain: example.com, role: site, public: unknown, languages: unknown, hosting: unknown, dns: unknown,"
                " search_console: unknown, analytics: unknown, llm_visibility: {tracked: false}}\n")
        (self.d / "brands.yaml").write_text(good, encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        for bad in (good.replace("status: unknown", "status: sort-of"), good.replace("relation: masterbrand", "relation: sub-brand-of:ghost"),
                    good.replace("public: unknown", "public: null"), good.replace("kind: company", "kind: firm")):
            (self.d / "brands.yaml").write_text(bad, encoding="utf-8")
            self.assertEqual(self.kinds(), ["schema"], bad)

    def test_unknown_is_required_not_optional(self):
        good = ("vertical: acme\nbrands:\n  - id: acme\n    name: Acme\n    kind: company\n    relation: masterbrand\n"
                "    status: unknown\n    ip_owner: unknown\n    operator: unknown\n    voice: unknown\n    tokens: unknown\n"
                "    images: unknown\n    design: unknown\n    source: \"owner, 2026-01-05\"\n    domains:\n"
                "      - {domain: example.com, role: site, public: unknown, languages: [en, sv], hosting: unknown, dns: unknown,"
                " search_console: unknown, analytics: unknown}\n")
        (self.d / "brands.yaml").write_text(good, encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        for omitted in ("    design: unknown\n", "    voice: unknown\n"):
            (self.d / "brands.yaml").write_text(good.replace(omitted, ""), encoding="utf-8")
            self.assertEqual(self.kinds(), ["schema"], omitted)
        (self.d / "brands.yaml").write_text(good.replace(" dns: unknown,", ""), encoding="utf-8")
        self.assertEqual(self.kinds(), ["schema"])

    def test_unquoted_no_gets_a_hint(self):
        good = ("vertical: acme\nbrands:\n  - id: acme\n    name: Acme\n    kind: company\n    relation: masterbrand\n"
                "    status: unknown\n    ip_owner: unknown\n    operator: unknown\n    voice: unknown\n    tokens: unknown\n"
                "    images: unknown\n    design: unknown\n    source: x\n    domains:\n"
                "      - {domain: example.no, role: site, public: true, languages: [no, sv], hosting: unknown, dns: unknown,"
                " search_console: unknown, analytics: unknown}\n")
        (self.d / "brands.yaml").write_text(good, encoding="utf-8")
        msgs = [f["message"] for f in findings(self.org)]
        self.assertTrue(any("YAML boolean" in m and "quote" in m for m in msgs), msgs)
        (self.d / "brands.yaml").write_text(good.replace("[no, sv]", '["no", sv]'), encoding="utf-8")
        self.assertEqual(self.kinds(), [])

    def test_feeds_must_be_facets(self):
        base = ("vertical: acme\nupdated: 2026-01-05\nsources:\n"
                "  - {id: s-site, kind: url, path: \"https://example.com\", authority: public, feeds: [FEEDS]}\n")
        (self.d / "sources.yaml").write_text(base.replace("FEEDS", "public, essence"), encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        (self.d / "sources.yaml").write_text(base.replace("FEEDS", "bogus"), encoding="utf-8")
        self.assertEqual(self.kinds(), ["schema"])

    def test_source_markers_resolve(self):
        (self.d / "sources.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nsources:\n"
            "  - {id: s-site, kind: url, path: \"https://example.com\", authority: public, feeds: [company]}\n", encoding="utf-8")
        p = self.d / "company-acme.md"
        base = p.read_text(encoding="utf-8")
        p.write_text(base + "\nFounded 2020 [s1]. Sells widgets [s-site].\n\n## Sources\n\n- [s1] vault:notes/history.md\n", encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        p.write_text(base + "\nFounded 2020 [s1]. Sells widgets [s-nope].\n", encoding="utf-8")
        msgs = sorted(f["message"] for f in findings(self.org) if f["kind"] == "marker")
        self.assertEqual(len(msgs), 2, msgs)
        p.write_text(base.replace("sources: []", "sources: [s-ghost]"), encoding="utf-8")
        self.assertEqual(self.kinds(), ["marker"])

    def test_display_name_must_agree(self):
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8").replace("# acme -- company", "# Acme Ltd -- company"), encoding="utf-8")
        self.assertEqual(self.kinds(), ["name"])

    def test_summary_counts_open_items_and_decisions(self):
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n**Decision needed:** keep the name? (owner)\n_Not provided yet._\n", encoding="utf-8")
        rows = {r[0]: r[1:] for r in ct.summarise(self.d)}
        self.assertEqual(rows["company"], (2, 1))

    def test_brand_kind_system_and_status_planned(self):
        good = ("vertical: acme\nbrands:\n  - id: acme\n    name: Acme\n    kind: system\n    relation: masterbrand\n"
                "    status: planned\n    ip_owner: unknown\n    operator: unknown\n    voice: unknown\n    tokens: unknown\n"
                "    images: unknown\n    design: unknown\n    source: x\n    domains: []\n")
        (self.d / "brands.yaml").write_text(good, encoding="utf-8")
        self.assertEqual(self.kinds(), [])

    def test_captured_copy_fields(self):
        (self.d / "sources.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nsources:\n"
            "  - {id: s-copy, kind: vault, path: \"vault:web/about.md\", authority: public, feeds: [public], "
            "origin_url: \"https://example.com/about\", as_of: 2026-01-04}\n", encoding="utf-8")
        self.assertEqual(self.kinds(), [])

    def test_strict_reports_what_the_graph_needs(self):
        (self.d / "sources.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nlabels: {Q: open strategy question}\nsources:\n"
            "  - {id: s-a, kind: vault, path: x.md, authority: current, feeds: [company], curation: original}\n"
            "  - {id: s-b, kind: vault, path: y.md, authority: draft, feeds: [offering], curation: original}\n", encoding="utf-8")
        good_readme = (self.d / "README.md").read_text(encoding="utf-8").replace("## Decisions\n", "## Decisions\n\nkeep the name?\n")
        (self.d / "README.md").write_text(good_readme.replace("## Conflicts\n","## Conflicts\n\n- C1 Name. A [s-a] versus B [s-b]. Touches: company.\n"), encoding="utf-8")
        p = self.d / "company-acme.md"
        base = p.read_text(encoding="utf-8")
        p.write_text(base + "\nFact [s1].\n\n## Sources\n\n- [s1] s-a: x.md\n\n**Decision needed:** keep the name? (owner)\n", encoding="utf-8")

        def strict():
            return [f["message"] for f in ct.check_strict(self.d)]
        self.assertEqual(strict(), [])
        (self.d / "README.md").write_text(good_readme.replace("## Conflicts\n","## Conflicts\n\n- 1 Name. A [s-a] versus B [s-b]. Touches: company.\n"), encoding="utf-8")
        self.assertTrue(any("C<n>" in m for m in strict()))
        (self.d / "README.md").write_text(good_readme.replace("## Conflicts\n","## Conflicts\n\n- C1 Name. only [s-a]. Touches: company.\n"), encoding="utf-8")
        self.assertTrue(any("both sides" in m for m in strict()))
        (self.d / "README.md").write_text(good_readme, encoding="utf-8")
        p.write_text(base + "\nFact [s1].\n\n- [s1] x.md\n", encoding="utf-8")
        self.assertTrue(any("names no register id" in m for m in strict()))
        p.write_text(base + "\nFact [s-b].\n", encoding="utf-8")
        self.assertTrue(any("feeds" in m for m in strict()))
        p.write_text(base + "\n- Decision for the owner: keep the name?\n**Decision needed:** and this one\n", encoding="utf-8")
        self.assertEqual(sum("decision" in m for m in strict()), 3)   # old form, no owner role, not listed in README

    def test_provenance_in_strict(self):
        def reg(*rows):
            (self.d / "sources.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nsources:\n" + "".join(rows), encoding="utf-8")

        def msgs():
            return [f["message"] for f in ct.check_strict(self.d) if f["kind"] == "provenance"]
        reg("  - {id: s-a, kind: vault, path: x.pdf, authority: current, feeds: [company], curation: original, pages: 12}\n")
        r = self.d / "README.md"
        with_heading = r.read_text(encoding="utf-8")
        self.assertIn("## Reviewer notes and extraction losses", with_heading)   # the init skeleton carries it
        r.write_text(with_heading.replace("## Reviewer notes and extraction losses", "## Notes"), encoding="utf-8")
        self.assertEqual(msgs(), ["paged originals are used, so README needs '## Reviewer notes and extraction losses'"])
        r.write_text(with_heading, encoding="utf-8")
        self.assertEqual(msgs(), [])
        reg("  - {id: s-a, kind: vault, path: x.pdf, authority: current, feeds: [company]}\n")
        self.assertTrue(any("original, derived or curated" in m for m in msgs()))
        reg("  - {id: s-a, kind: vault, path: x.md, authority: binding, feeds: [company], curation: curated}\n")
        got = msgs()
        self.assertTrue(any("derived_from" in m for m in got) and any("decided_by" in m for m in got) and any("cannot be binding" in m for m in got))
        reg("  - {id: s-a, kind: vault, path: x.pdf, authority: current, feeds: [company], curation: original, pages: 12}\n")
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nOk [s-a] (p. 12). Too far [s-a] (pp. 11-13).\n", encoding="utf-8")
        self.assertEqual(sum("beyond the 12 pages" in m for m in msgs()), 1)

    def test_coverage_rules(self):
        base = "vertical: acme\nupdated: 2026-01-05\nruleset: company-coverage/3.2\nitems:\n"
        (self.d / "company-acme.md").write_text((self.d / "company-acme.md").read_text(encoding="utf-8") + "\nFounded 2020.\n", encoding="utf-8")
        (self.d / "coverage.yaml").write_text(base + "  - {id: P-01, facet: company, status: answered, where: \"company-acme.md:12\"}\n"
                                              "  - {id: P-02, facet: company, status: open, reason: \"not in the sources\", close_with: us}\n"
                                              "  - {id: P-03, facet: company, status: na, reason: \"sole trader\"}\n", encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        for bad in ("  - {id: P-04, facet: company, status: answered}\n", "  - {id: P-04, facet: company, status: open}\n",
                    "  - {id: P-04, facet: company, status: answered, where: ghost.md}\n", "  - {id: P-01, facet: company, status: open, reason: x, close_with: us}\n  - {id: P-01, facet: company, status: open, reason: y, close_with: us}\n",
                    "  - {id: P-04, facet: Not-A-Group, status: open, reason: x, close_with: us}\n", "  - {id: P-04, facet: company, status: maybe}\n"):
            (self.d / "coverage.yaml").write_text(base + bad, encoding="utf-8")
            self.assertEqual(self.kinds(), ["schema"], bad)
        (self.d / "coverage.yaml").write_text(base + "  - {id: P-04, facet: company, status: partial, where: company-acme.md, remainder: workshop}\n", encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8").replace("status: draft", "status: final").replace("sources: []", "sources: [\"vault:x.md\"]"), encoding="utf-8")
        self.assertEqual(self.kinds(), ["schema"])

    def test_classification_rules_are_enforced(self):
        base = "vertical: acme\nupdated: 2026-01-05\nruleset: company-coverage/3.2\nitems:\n"
        (self.d / "company-acme.md").write_text((self.d / "company-acme.md").read_text(encoding="utf-8") + "\nFounded 2020.\n", encoding="utf-8")
        ok = ("  - {id: A-1, facet: company, status: partial, where: company-acme.md, remainder: decision}\n"
              "  - {id: A-2, facet: company, status: open, reason: r, close_with: customer}\n")
        (self.d / "coverage.yaml").write_text(base + ok, encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        for bad in ("  - {id: A-3, facet: company, status: partial, where: company-acme.md}\n",
                    "  - {id: A-3, facet: company, status: open, reason: r}\n",
                    "  - {id: A-3, facet: company, status: open, reason: r, close_with: nobody}\n",
                    "  - {id: A-3, facet: company, status: decision, reason: r, close_with: us}\n",
                    "  - {id: A-3, facet: company, status: answered, where: company-acme.md, remainder: open}\n"):
            (self.d / "coverage.yaml").write_text(base + bad, encoding="utf-8")
            self.assertEqual(self.kinds(), ["schema"], bad)
        (self.d / "coverage.yaml").write_text(base.replace("company-coverage/3.2", "v1") + ok, encoding="utf-8")
        self.assertEqual(self.kinds(), ["schema"])

    def test_coverage_accepts_a_question_sets_extra_groups(self):
        base = "vertical: acme\nupdated: 2026-01-05\nruleset: company-coverage/3.2\nitems:\n"
        (self.d / "coverage.yaml").write_text(base + "  - {id: D-01, facet: brands, status: open, reason: r, close_with: us}\n"
                                              "  - {id: A-01, facet: sources, status: workshop, reason: r}\n", encoding="utf-8")
        self.assertEqual(self.kinds(), [])
        (self.d / "coverage.yaml").write_text(base + "  - {id: D-01, facet: Brands, status: workshop, reason: r}\n", encoding="utf-8")
        self.assertEqual(self.kinds(), ["schema"])

    def test_ruleset_may_carry_a_minor_version(self):
        base = "vertical: acme\nupdated: 2026-01-05\nruleset: %s\nitems: []\n"
        for ok in ("company-coverage/3", "company-coverage/3.2"):
            (self.d / "coverage.yaml").write_text(base % ok, encoding="utf-8")
            self.assertEqual(self.kinds(), [], ok)
        (self.d / "coverage.yaml").write_text(base % "company-coverage/3.1.2", encoding="utf-8")
        self.assertEqual(self.kinds(), ["schema"])

    def test_items_file_finds_silent_omissions(self):
        (self.d / "coverage.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nitems:\n"
            "  - {id: P-01, facet: company, status: open, reason: gap, close_with: customer}\n", encoding="utf-8")
        wanted = ["P-01", "P-02", "P-03"]
        found = ct.check_items(self.d, wanted)
        self.assertEqual(len(found), 1)
        self.assertIn("P-02, P-03", found[0]["message"])
        self.assertEqual(ct.check_items(self.d, ["P-01"]), [])
        j = Path(self._t.name) / "items.json"
        j.write_text(json.dumps([{"id": "P-01"}, {"id": "P-09", "required": False}, "P-02"]), encoding="utf-8")
        self.assertEqual(ct.load_wanted(j), ["P-01", "P-02"])

    def test_init_with_template_writes_coverage_skeleton(self):
        org = Path(self._t.name) / "tpl"
        org.mkdir()
        self.assertEqual(ct.main(["init", str(org), "--vertical", "tpl", "--template", "some/path", "--today", TODAY]), 0)
        self.assertTrue((org / "_company" / "coverage.yaml").exists())
        self.assertEqual(findings(org), [])

    def test_strict_is_off_by_default(self):
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n- Decision for the owner: x\n", encoding="utf-8")
        self.assertEqual(self.kinds(), [])

    def test_copy_outside_company_folder(self):
        (self.org / "positioning-acme.md").write_text(
            "---\nvertical: acme\nfacet: positioning\nstatus: draft\n---\n\n# copy\n", encoding="utf-8")
        (self.org / "notes-acme.md").write_text("---\nvertical: acme\nfacet: positioning\n---\n", encoding="utf-8")
        found = ct.check_copies(Path(self._t.name), ct.find_company_dirs(Path(self._t.name)))
        self.assertEqual([Path(f["file"]).name for f in found], ["positioning-acme.md"])

    def test_dot_folders_and_missing_folder_are_quiet(self):
        hidden = Path(self._t.name) / ".archive" / "old" / "_company"
        hidden.mkdir(parents=True)
        self.assertEqual(len(ct.find_company_dirs(Path(self._t.name))), 1)
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(findings(empty), [])


class Config(unittest.TestCase):
    """The `company:` block is read from <org>/_ops.yaml (and the vault's _config/base.yaml)."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.org = Path(self._t.name) / "acme"
        self.org.mkdir()

    def tearDown(self):
        self._t.cleanup()

    def write_ops(self, text):
        (self.org / "_ops.yaml").write_text(text, encoding="utf-8")

    def test_defaults_without_a_config(self):
        cfg, problems = ct.load_config(self.org)
        self.assertEqual((cfg["level"], cfg["language"], cfg["max_age_days"], cfg["template"], cfg["level_map"]), ("basic", "en", 365, None, {}))
        self.assertEqual(problems, [])

    def test_org_config_overrides_the_vault_base(self):
        (Path(self._t.name) / "_config").mkdir()
        (Path(self._t.name) / "_config" / "base.yaml").write_text("company:\n  level: standard\n  language: sv\n  max_age_days: 90\n", encoding="utf-8")
        self.write_ops("company:\n  language: en\n")
        cfg, _ = ct.load_config(self.org)
        self.assertEqual((cfg["level"], cfg["language"], cfg["max_age_days"]), ("standard", "en", 90))

    def test_bad_values_are_reported_and_fall_back(self):
        self.write_ops("company:\n  level: light\n  max_age_days: soon\n  level_map: {basic: ''}\n")
        cfg, problems = ct.load_config(self.org)
        self.assertEqual(len(problems), 3)
        self.assertEqual((cfg["level"], cfg["max_age_days"], cfg["level_map"]), ("basic", 365, {}))

    def test_init_takes_level_language_and_template_from_the_config(self):
        self.write_ops("company:\n  level: standard\n  language: sv\n  template: some/path\n")
        self.assertEqual(ct.main(["init", str(self.org), "--vertical", "acme", "--today", TODAY]), 0)
        text = (self.org / "_company" / "company-acme.md").read_text(encoding="utf-8")
        self.assertIn("level: standard", text)
        self.assertIn("language: sv", text)
        self.assertTrue((self.org / "_company" / "coverage.yaml").exists())
        self.assertIn("ruleset: company-coverage/3.2", (self.org / "_company" / "coverage.yaml").read_text(encoding="utf-8"))
        self.assertEqual(ct.main(["check", str(self.org), "--strict", "--today", TODAY]), 0)   # the skeleton passes the strict check

    def test_max_age_comes_from_the_config_and_the_flag_wins(self):
        self.assertEqual(ct.main(["init", str(self.org), "--vertical", "acme", "--today", TODAY]), 0)
        self.write_ops("company:\n  max_age_days: 10\n")
        self.assertEqual(ct.main(["check", str(self.org), "--today", "2026-12-01"]), 1)
        self.assertEqual(ct.main(["check", str(self.org), "--today", "2026-12-01", "--max-age-days", "365"]), 0)

    def test_level_map_names_are_accepted_in_frontmatter(self):
        self.assertEqual(ct.main(["init", str(self.org), "--vertical", "acme", "--today", TODAY]), 0)
        p = self.org / "_company" / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8").replace("level: basic", "level: medium"), encoding="utf-8")
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY]), 1)
        self.write_ops("company:\n  level_map: {standard: medium}\n")
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY]), 0)


class Hygiene(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.org, _ = init(self._t.name)
        self.d = self.org / "_company"

    def tearDown(self):
        self._t.cleanup()

    def test_question_wording_in_the_profile_is_reported_without_repeating_it(self):
        q = Path(self._t.name) / "items.json"
        q.write_text(json.dumps({"items": [{"id": "Z-01", "q": "Describe the one promise the company makes to every customer before anything else"}]}), encoding="utf-8")
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nDescribe the one promise the company makes to every customer.\nUnrelated sentence about widgets and tea.\n", encoding="utf-8")
        found = ct.check_leak(self.d, ct.load_questions(q))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["kind"], "leak")
        self.assertIn("Z-01", found[0]["message"])
        self.assertNotIn("promise", found[0]["message"])
        p.write_text(p.read_text(encoding="utf-8").replace("Describe the one promise the company makes to every customer.", "We promise delivery."), encoding="utf-8")
        self.assertEqual(ct.check_leak(self.d, ct.load_questions(q)), [])

    def test_leak_flag_runs_from_the_command_line(self):
        q = Path(self._t.name) / "items.json"
        q.write_text(json.dumps([{"id": "Z-02", "q": "Which three words would a customer use to describe the company today"}]), encoding="utf-8")
        p = self.d / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nWhich three words would a customer use to describe the company today?\n", encoding="utf-8")
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY, "--leak-from", str(q)]), 1)

    def test_where_must_point_at_a_line_that_exists(self):
        (self.d / "company-acme.md").write_text((self.d / "company-acme.md").read_text(encoding="utf-8") + "\nFounded 2020.\n", encoding="utf-8")
        n = len((self.d / "company-acme.md").read_text(encoding="utf-8").split("\n"))
        base = "vertical: acme\nupdated: 2026-01-05\nruleset: company-coverage/3.2\nitems:\n"
        for ok in (f"company-acme.md:{n}", "company-acme.md:3-5", "company-acme.md"):
            (self.d / "coverage.yaml").write_text(base + f"  - {{id: A-1, facet: company, status: answered, where: \"{ok}\"}}\n", encoding="utf-8")
            self.assertEqual([f["kind"] for f in findings(self.org)], [], ok)
        for bad in (f"company-acme.md:{n + 50}", "company-acme.md:0", "company-acme.md:x", "company-acme.md:9-3"):
            (self.d / "coverage.yaml").write_text(base + f"  - {{id: A-1, facet: company, status: answered, where: \"{bad}\"}}\n", encoding="utf-8")
            self.assertEqual([f["kind"] for f in findings(self.org)], ["schema"], bad)

    def test_ruleset_is_required_in_coverage(self):
        (self.d / "coverage.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nitems: []\n", encoding="utf-8")
        self.assertEqual([f["kind"] for f in findings(self.org)], ["schema"])

    def test_touches_must_be_a_labelled_list_of_facets(self):
        (self.d / "sources.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nsources:\n"
            "  - {id: s-a, kind: vault, path: x.md, authority: current, feeds: [company], curation: original}\n", encoding="utf-8")
        r = self.d / "README.md"
        good = r.read_text(encoding="utf-8")

        def run(entry):
            r.write_text(good.replace("## Conflicts\n", "## Conflicts\n\n" + entry + "\n"), encoding="utf-8")
            return [f["message"] for f in ct.check_strict(self.d) if "C1" in f["message"]]
        self.assertEqual(run("- C1 Name. A [s-a] versus B [s-a]. Touches: company, brand."), [])
        self.assertTrue(any("no 'Touches" in m for m in run("- C1 Name. A [s-a] versus B [s-a], and the company is affected.")))
        self.assertTrue(any("not facets" in m for m in run("- C1 Name. A [s-a] versus B [s-a]. Touches: company, planets.")))

    def test_decision_must_be_listed_in_the_readme_and_sources_in_the_frontmatter(self):
        (self.d / "sources.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nsources:\n"
            "  - {id: s-a, kind: vault, path: x.md, authority: current, feeds: [company], curation: original}\n"
            "  - {id: s-b, kind: vault, path: y.md, authority: current, feeds: [company], curation: original}\n", encoding="utf-8")
        p = self.d / "company-acme.md"
        base = p.read_text(encoding="utf-8")
        p.write_text(base.replace("sources: []", "sources: [s-a]") + "\nFact [s-a]. Other [s-b].\n**Decision needed:** keep the name? (owner)\n", encoding="utf-8")
        got = [f["message"] for f in ct.check_strict(self.d)]
        self.assertTrue(any("not listed under '## Decisions'" in m for m in got), got)
        self.assertTrue(any("s-b" in m and "frontmatter" in m for m in got), got)

    def test_summary_reports_coverage_counts(self):
        (self.d / "coverage.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nruleset: company-coverage/3.2\nitems:\n"
            "  - {id: A-1, facet: company, status: open, reason: r, close_with: us}\n"
            "  - {id: A-2, facet: company, status: workshop, reason: r}\n"
            "  - {id: B-1, facet: brands, status: open, reason: r, close_with: customer}\n", encoding="utf-8")
        cov = ct.coverage_summary(self.d)
        self.assertEqual(cov["company"], {"open": 1, "workshop": 1})
        self.assertEqual(cov["brands"], {"open": 1})


class ItemBank(unittest.TestCase):
    ITEMS = [{"id": "Z-01", "level": "light", "q": "Describe the one promise the company makes to every customer before anything else"},
             {"id": "Z-02", "level": "medium", "q": "Which three words would a customer use to describe the company today"},
             {"id": "Z-03", "level": "full", "q": "What does the company refuse to do even when a customer asks for it politely"},
             {"id": "Z-04", "level": "optional", "q": "Optional extra question that nobody has to answer for this level at all"}]

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)
        self.org, _ = init(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def raw(self):
        """The server's answer exactly as saved: a JSON-RPC result whose text is JSON."""
        f = self.tmp / "raw.json"
        f.write_text(json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps({"count": 4, "items": self.ITEMS}, indent=2)}]}}), encoding="utf-8")
        return f

    def test_a_saved_server_answer_is_unwrapped_for_every_use(self):
        f = self.raw()
        self.assertEqual(len(ct.load_questions(f)), 4)
        self.assertEqual(ct.load_wanted(f), ["Z-01", "Z-02", "Z-03", "Z-04"])

    def test_leak_check_on_the_raw_answer_finds_an_echo_and_never_passes_empty(self):
        p = self.org / "_company" / "company-acme.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nWhich three words would a customer use to describe the company today?\n", encoding="utf-8")
        found = ct.check_leak(self.org / "_company", ct.load_questions(self.raw()))
        self.assertEqual([f["message"].split()[4] for f in found], ["Z-02"])
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY, "--leak-from", str(self.raw())]), 1)
        empty = self.tmp / "empty.json"
        empty.write_text("[]", encoding="utf-8")
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY, "--leak-from", str(empty)]), 2)

    def test_leak_check_also_reads_yaml_files(self):
        y = self.org / "_company" / "coverage.yaml"
        y.write_text("vertical: acme\nupdated: 2026-01-05\nruleset: company-coverage/3.2\nitems:\n"
                     "  - {id: A-1, facet: company, status: open, reason: \"What does the company refuse to do even when a customer asks for it politely\", close_with: us}\n", encoding="utf-8")
        found = ct.check_leak(self.org / "_company", ct.load_questions(self.raw()))
        self.assertTrue(any(f["file"].endswith("coverage.yaml") for f in found))

    def test_bad_input_files_are_refused_with_a_message(self):
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY, "--items", str(self.tmp / "nope.json")]), 2)
        bad = self.tmp / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY, "--items", str(bad)]), 2)

    def test_required_ids_follow_level_map_and_level_order(self):
        cfg = {"level_map": {"basic": "light", "standard": "medium"}, "level_order": ["public", "light", "medium", "full"]}
        f = self.raw()
        self.assertEqual(ct.required_ids(f, "basic", cfg), ["Z-01"])
        self.assertEqual(ct.required_ids(f, "standard", cfg), ["Z-01", "Z-02"])
        with self.assertRaises(ct.InputError):
            ct.required_ids(f, "complete", cfg)
        with self.assertRaises(ct.InputError):
            ct.required_ids(f, "basic", {"level_map": {"basic": "light"}, "level_order": []})

    def test_required_ids_command_and_items_from_flag(self):
        (self.org / "_ops.yaml").write_text("company:\n  level: standard\n  level_map: {standard: medium}\n  level_order: [public, light, medium, full]\n", encoding="utf-8")
        out = self.tmp / "ids.json"
        self.assertEqual(ct.main(["required-ids", str(self.org), "--items-from", str(self.raw()), "--out", str(out)]), 0)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8")), ["Z-01", "Z-02"])
        cov = self.org / "_company" / "coverage.yaml"
        cov.write_text("vertical: acme\nupdated: 2026-01-05\nruleset: company-coverage/3.2\nitems:\n"
                       "  - {id: Z-01, facet: company, status: open, reason: r, close_with: us}\n", encoding="utf-8")
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY, "--items-from", str(self.raw())]), 1)
        cov.write_text(cov.read_text(encoding="utf-8") + "  - {id: Z-02, facet: company, status: open, reason: r, close_with: us}\n", encoding="utf-8")
        self.assertEqual(ct.main(["check", str(self.org), "--today", TODAY, "--items-from", str(self.raw())]), 0)


class Citations(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.org, _ = init(self._t.name)
        self.d = self.org / "_company"
        (self.d / "sources.yaml").write_text("vertical: acme\nupdated: 2026-01-05\nsources:\n"
            "  - {id: s-a, kind: vault, path: x.pdf, authority: current, feeds: [company], curation: original, pages: 20}\n", encoding="utf-8")
        self.base = (self.d / "company-acme.md").read_text(encoding="utf-8").replace("sources: []", "sources: [s-a]")

    def tearDown(self):
        self._t.cleanup()

    def strict(self, body):
        (self.d / "company-acme.md").write_text(self.base + body, encoding="utf-8")
        return [f["message"] for f in ct.check_strict(self.d)]

    def test_citation_forms(self):
        for ok in ("Fact [s-a] (p. 3).", "Fact [s-a] (pp. 3-5).", "Fact [s-a] (p. 18, specimen).", "Fact [s-a] (section: History).", "Fact [s-a]."):
            self.assertEqual([m for m in self.strict("\n" + ok + "\n") if "citation" in m], [], ok)
        for bad in ("Fact [s-a] (page three).", "Fact [s-a] (p3).", "Fact [s-a] (sect History)."):
            self.assertEqual(len([m for m in self.strict("\n" + bad + "\n") if "citation" in m]), 1, bad)

    def test_page_note_does_not_hide_a_page_beyond_the_count(self):
        self.assertEqual(len([m for m in self.strict("\nFact [s-a] (p. 25, specimen).\n") if "beyond the 20 pages" in m]), 1)

    def test_bullets_that_state_something_need_a_marker(self):
        long = "- The company delivers its tours with a crew that speaks several languages and knows the route well."
        self.assertEqual(len([m for m in self.strict("\n" + long + "\n") if "carries no" in m]), 1)
        self.assertEqual([m for m in self.strict("\n" + long + " [s-a] (p. 2)\n") if "carries no" in m], [])
        self.assertEqual([m for m in self.strict("\nThe crew, as stated [s-a] (p. 2):\n\n" + long + "\n") if "carries no" in m], [])
        self.assertEqual([m for m in self.strict("\n- Short note.\n") if "carries no" in m], [])
        self.assertEqual([m for m in self.strict("\n- A longer line that is just a gap and nothing else to say here: _Not provided yet._\n") if "carries no" in m], [])


class Noise(unittest.TestCase):
    def test_a_drawing_read_as_text_is_flagged_and_a_page_of_prose_is_not(self):
        drawing = " ".join(["12", "4", "x", "0.5", "7", "ab", "3", "9"] * 80)
        prose = " ".join(["The company builds boats and runs tours for guests in several cities every day."] * 40)
        self.assertTrue(ct.page_noise(drawing))
        self.assertFalse(ct.page_noise(prose))
        self.assertFalse(ct.page_noise("12 4 x"))


class Extract(unittest.TestCase):
    PDF = (b"%PDF-1.1\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
           b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
           b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 10 50 Td (Hello Acme page one) Tj ET\nendstream endobj\n"
           b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\ntrailer<</Root 1 0 R/Size 6>>\n%%EOF\n")
    HTML = ("<html><head><title>About Acme</title><link rel=\"canonical\" href=\"https://acme.example/about\">"
            "<style>x{}</style></head><body><nav>Menu</nav><h1>We build widgets</h1><p>Founded 2020.</p><script>var x=1;</script></body></html>")

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.org = Path(self._t.name) / "acme"
        (self.org / "source-documents").mkdir(parents=True)

    def tearDown(self):
        self._t.cleanup()

    def test_html_text_title_and_address(self):
        (self.org / "source-documents" / "about.html").write_text(self.HTML, encoding="utf-8")
        self.assertEqual(ct.main(["extract", str(self.org), "--today", TODAY]), 0)
        txt = (self.org / ".extracted" / "about.txt").read_text(encoding="utf-8")
        self.assertIn("We build widgets", txt)
        self.assertIn("origin_url: https://acme.example/about", txt)
        self.assertNotIn("var x", txt)
        man = (self.org / ".extracted" / "_manifest.md").read_text(encoding="utf-8")
        self.assertIn("https://acme.example/about", man)
        self.assertIn("never edited", man)

    def test_missing_source_folder_is_refused(self):
        (self.org / "source-documents").rmdir()
        self.assertEqual(ct.main(["extract", str(self.org)]), 2)

    def test_pdf_pages_and_thin_page_note(self):
        if not ct.shutil.which("pdftotext"):
            self.skipTest("pdftotext not installed")
        (self.org / "source-documents" / "deck.pdf").write_bytes(self.PDF)
        self.assertEqual(ct.main(["extract", str(self.org), "--today", TODAY]), 0)
        txt = (self.org / ".extracted" / "deck.txt").read_text(encoding="utf-8")
        self.assertIn("=== page 1 ===", txt)
        self.assertIn("Hello Acme page one", txt)
        self.assertIn("pages: 1", txt)
        self.assertIn("fewer than 25 words", (self.org / ".extracted" / "_manifest.md").read_text(encoding="utf-8"))

    def test_extracted_folder_is_not_a_profile_and_sources_untouched(self):
        p = self.org / "source-documents" / "about.html"
        p.write_text(self.HTML, encoding="utf-8")
        before = p.read_bytes()
        ct.main(["extract", str(self.org)])
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual(ct.find_company_dirs(Path(self._t.name)), [])


class Contract(unittest.TestCase):
    """The repository side: the contract names what the skill implements, and carries no template."""

    def test_schemas_parse_and_agree_with_the_tool(self):
        for n in ("company-sources", "company-brands"):
            json.loads((ROOT / "docs" / "schemas" / f"{n}.schema.json").read_text(encoding="utf-8"))

    def test_facets_in_contract_equal_facets_in_tool(self):
        text = (ROOT / "skills" / "company" / "references" / "contract.md").read_text(encoding="utf-8")
        for f in ct.FACETS:
            self.assertIn(f"| `{f}` |", text, f)

    def test_ecosystem_declares_the_folder_and_the_skill(self):
        import yaml
        eco = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
        self.assertGreaterEqual(eco["contract_version"], 43)
        self.assertIn("company", [s["name"] for s in eco["skills"]["user_invocable"]])
        paths = [e["path"] for e in eco["vault_conventions"]["per_folder"]]
        self.assertIn("<org>/_company/", paths)
        base = yaml.safe_load((ROOT / "skills" / "ops-config" / "base.yaml").read_text(encoding="utf-8"))
        self.assertIsNone(base["company"]["template"])
        self.assertEqual(base["company"]["services"], {})

    def test_skill_carries_no_question_text(self):
        # the open skill and its contract state structure only; a question set is read from company.template
        for p in (ROOT / "skills" / "company").rglob("*.md"):
            self.assertNotIn("?", p.read_text(encoding="utf-8"), f"{p.name} contains a question")


if __name__ == "__main__":
    unittest.main()
