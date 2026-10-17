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
