"""CR-123: a podcast profile, insights schema 3, consensus that is never a rule.

    python3 -m unittest discover -s tests

Invented data only. Each case builds a small project with an `_ops.yaml` and an
`_insights.yaml` and runs the real scripts.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "ops-config"))
sys.path.insert(0, str(ROOT / "skills" / "insights"))
import profiles  # noqa: E402
import promotion_candidates as pc  # noqa: E402
import profile_migrate as pm  # noqa: E402


def project(tmp, profile=None, extra=None):
    p = Path(tmp) / "acme-podcast"
    p.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if profile:
        cfg["profile"] = profile
    cfg.update(extra or {})
    if cfg:
        (p / "_ops.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


def insights(folder, entries, version=3):
    doc = {"version": version, "context": "acme-podcast", "insights": entries, "next_id": 99}
    (folder / "_insights.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
                                           encoding="utf-8")


def claim(i, source, voice, confirmations=(), **extra):
    e = {"id": i, "type": "claim", "date": 260101, "summary": f"Claim {i}", "tags": ["hiring"],
         "status": "active", "confidence": "hypothesis", "source": source, "voice": voice,
         "confirmations": [dict(c) for c in confirmations]}
    e.update(extra)
    return e


class Profiles(unittest.TestCase):
    def test_no_profile_is_meeting_and_equals_old_behaviour(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = profiles.resolve(project(tmp))
            self.assertEqual(r["name"], "meeting")
            v = r["values"]
            self.assertEqual(v["summary_folder"], "meetings/")
            self.assertEqual(v["promotes_to"], "rule")
            self.assertEqual(v["count_by"], "date")
            self.assertEqual(tuple(v["promotable_types"]), pc.PROMOTABLE)

    def test_podcast_and_nearest_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp, "podcast", {"profiles": {"podcast": {"consensus_threshold": 4}}})
            sub = p / "episodes"
            sub.mkdir()
            r = profiles.resolve(sub)
            self.assertEqual(r["name"], "podcast")
            self.assertEqual(r["values"]["consensus_threshold"], 4)
            self.assertEqual(r["values"]["count_by"], "unit")

    def test_unknown_profile_falls_back_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = profiles.resolve(project(tmp, "radio"))
            self.assertEqual(r["name"], "meeting")
            self.assertTrue(r["warnings"])


class Counting(unittest.TestCase):
    def test_same_date_units_count_by_unit_not_date(self):
        confs = [{"source": f"260101-episode-guest-{n}.md", "date": 260101, "voice": "guest"} for n in range(1, 5)]
        e = claim(1, "260101-episode-guest-0.md", "guest", confs)
        n_unit = pm.counts(e, {"count_by": "unit", "owner_voice": "host"})
        n_date = pm.counts(e, {"count_by": "date", "owner_voice": "host"})
        self.assertEqual(n_unit["confirmation_count"], 5)
        self.assertEqual(n_date["confirmation_count"], 1)
        self.assertEqual(n_unit["independent_count"], 5)

    def test_owner_voice_alone_never_reaches_consensus(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp, "podcast")
            confs = [{"source": f"26010{n}-episode-guest.md", "voice": "host"} for n in range(2, 6)]
            insights(p, [claim(1, "260101-episode-guest.md", "host", confs)])
            report = pc.scan(p, 3, None)
            self.assertEqual(report["consensus_candidates"], [])

    def test_three_independent_voices_make_a_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp, "podcast")
            confs = [{"source": "260102-episode-guest.md", "voice": "guest"},
                     {"source": "260103-episode-guest.md", "voice": "both"}]
            insights(p, [claim(1, "260101-episode-guest.md", "guest", confs)])
            report = pc.scan(p, 3, None)
            [c] = report["consensus_candidates"]
            self.assertEqual((c["independent_count"], c["owner_count"]), (3, 1))

    def test_contradiction_blocks_and_marks_existing_consensus_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp, "podcast")
            confs = [{"source": f"26010{n}-episode-guest.md", "voice": "guest"} for n in (2, 3)]
            e = claim(1, "260101-episode-guest.md", "guest", confs, confidence="consensus",
                      contradicted_by=[{"source": "260110-episode-guest.md", "voice": "guest"}])
            insights(p, [e])
            report = pc.scan(p, 3, None)
            self.assertEqual(report["consensus_candidates"], [])
            self.assertEqual([c["id"] for c in report["consensus_stale"]], [1])

    def test_profile_types_drive_the_candidate_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp, "podcast")
            entries = [claim(i, f"26010{i}-episode-guest.md", "guest") for i in range(1, 4)]
            entries += [dict(claim(i, f"26010{i}-episode-guest.md", "guest"), type="quote") for i in range(4, 7)]
            insights(p, entries)
            groups = pc.scan(p, 3, None)["candidate_groups"]
            self.assertEqual([g["type"] for g in groups], ["claim"])
            self.assertEqual(groups[0]["count_by"], "unit")
            self.assertEqual(groups[0]["promotes_to"], "consensus")

    def test_meeting_profile_output_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = project(tmp)
            entries = [{"id": i, "type": "preference", "date": 260101 + i, "summary": f"P{i}",
                        "tags": ["x", "y"], "status": "active"} for i in range(1, 4)]
            insights(p, entries, version=2)
            [g] = pc.scan(p, 3, None)["candidate_groups"]
            self.assertEqual(g["confirmation_count"], g["distinct_dates"])
            self.assertEqual(g["promotes_to"], "rule")


class ConsensusIsNeverARule(unittest.TestCase):
    def test_step_05_loads_rule_only(self):
        text = (ROOT / "skills" / "transcript" / "SKILL.md").read_text(encoding="utf-8")
        step = text.split("## Step 0.5", 1)[1].split("\n## ", 1)[0]
        self.assertIn("confidence: rule", step)
        self.assertIn("consensus", step)          # named, and named as excluded
        self.assertRegex(step, r"(?i)never load|not loaded|is never loaded")

    def test_consensus_is_not_a_promotion_candidate_again(self):
        self.assertFalse(pc.is_candidate({"id": 1, "type": "claim", "confidence": "consensus"},
                                         ("claim",)))

    def test_contract_declares_schema_3_and_the_podcast_types(self):
        eco = yaml.safe_load((ROOT / "ecosystem.yaml").read_text(encoding="utf-8"))
        self.assertEqual(eco["schemas"]["insights"], 3)
        self.assertIn("tool_tip", eco["insight_types"]["podcast"])
        base = yaml.safe_load((ROOT / "skills" / "ops-config" / "base.yaml").read_text(encoding="utf-8"))
        self.assertEqual(base["profiles"]["podcast"]["insight_types"], "podcast")
        for t in base["profiles"]["podcast"]["promotable_types"]:
            self.assertIn(t, eco["insight_types"]["podcast"])


MIGRATE_SOURCE = """# corpus for an invented podcast -- comments must survive
version: 2
context: acme-podcast
insights:
  - id: 1
    type: learning
    summary: "Anställ långsamt, avskeda snabbt"   # keeps å/ä/ö
    source: 260101-episode-guest.md
    date: 260101
    tags: [hiring]
    status: active
    confidence: rule
    confirmations:
      - {source: "260102-episode-guest.md", date: 260102}
      - source: 260103-episode-guest.md
        date: 260103
  - id: 2
    type: quote
    summary: "Ett citat"
    source: 260101-episode-guest.md
    date: 260101
    status: active
next_id: 3
"""


class Migrate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = project(self.tmp.name, "podcast")
        (self.p / "_insights.yaml").write_text(MIGRATE_SOURCE, encoding="utf-8")
        self.plan = {"entries": {1: {"type": "claim", "voice": "guest", "confidence": "consensus"},
                                 2: {"voice": "host"}},
                     "confirmations": {1: {"260102-episode-guest.md": "guest",
                                           "260103-episode-guest.md": "both"}}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_writes_nothing(self):
        r = pm.migrate(self.p, self.plan, apply=False)
        self.assertIsNone(r["problem"])
        self.assertEqual((self.p / "_insights.yaml").read_text(encoding="utf-8"), MIGRATE_SOURCE)
        row = next(x for x in r["rows"] if x["id"] == 1)
        self.assertEqual((row["confirmation_count"], row["independent_count"], row["owner_count"]), (3, 3, 1))

    def test_apply_keeps_comments_and_swedish_and_sets_fields(self):
        r = pm.migrate(self.p, self.plan, apply=True)
        self.assertTrue(r["written"], r)
        text = (self.p / "_insights.yaml").read_text(encoding="utf-8")
        self.assertIn("# corpus for an invented podcast", text)
        self.assertIn("# keeps å/ä/ö", text)
        self.assertIn("Anställ långsamt", text)
        doc = yaml.safe_load(text)
        self.assertEqual(doc["version"], 3)
        e = doc["insights"][0]
        self.assertEqual((e["type"], e["voice"], e["confidence"]), ("claim", "guest", "consensus"))
        self.assertEqual([c["voice"] for c in e["confirmations"]], ["guest", "both"])
        self.assertEqual(e["independent_count"], 3)

    def test_plan_may_not_create_a_rule(self):
        self.plan["entries"][2] = {"confidence": "rule"}
        self.assertIn("error", pm.migrate(self.p, self.plan, apply=True))

    def test_refused_on_a_meeting_profile(self):
        (self.p / "_ops.yaml").write_text("profile: meeting\n", encoding="utf-8")
        self.assertIn("error", pm.migrate(self.p, self.plan, apply=True))


if __name__ == "__main__":
    unittest.main()
