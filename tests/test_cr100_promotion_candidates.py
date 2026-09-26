"""CR-100: the promotion arithmetic, once, and a review that is honoured only while it still fits.

    python3 -m unittest discover -s tests

Each case writes a small invented `_insights.yaml` and runs the real script. The
arithmetic is shared by compile and a review surface, so a wrong answer here is
wrong in both places at once.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INSIGHTS = Path(__file__).resolve().parents[1] / "skills" / "insights"
sys.path.insert(0, str(INSIGHTS))
import promotion_candidates as pc  # noqa: E402

SCRIPT = INSIGHTS / "promotion_candidates.py"


def entry(i, date, tags, type_="preference", summary=None, **extra):
    e = {"id": i, "type": type_, "date": date, "summary": summary or f"Claim {i}",
         "tags": tags, "status": "active", "confidence": "hypothesis"}
    e.update(extra)
    return e


def write(folder: Path, entries, config=None):
    import yaml
    folder.mkdir(parents=True, exist_ok=True)
    doc = {"version": 2, "context": "acme", "insights": entries, "next_id": 99}
    (folder / "_insights.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    if config is not None:
        (folder / "_ops.yaml").write_text(yaml.safe_dump(
            {"workflows": {"knowledge_extraction": {"evolution": config}}}), encoding="utf-8")
    return folder


def run(target: Path, *flags) -> dict:
    out = subprocess.run([sys.executable, str(SCRIPT), str(target), *flags],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


THREE = [entry(1, "260101", ["billing", "invoices"]),
         entry(2, "260210", ["billing", "invoices", "email"]),
         entry(3, "260305", ["invoices", "billing"])]


class Gates(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def test_three_entries_with_two_shared_tags_form_one_group(self):
        write(self.root / "acme", THREE)
        groups = run(self.root)["candidate_groups"]
        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g["ids"], [1, 2, 3])
        self.assertEqual(g["canonical_id"], 1)
        self.assertEqual(g["distinct_dates"], 3)
        self.assertFalse(g["single_session"])

    def test_shared_primary_tag_alone_is_enough(self):
        write(self.root / "acme", [entry(1, "260101", ["pricing", "a"]),
                                   entry(2, "260102", ["pricing", "b"]),
                                   entry(3, "260103", ["pricing", "c"])])
        self.assertEqual(run(self.root)["candidate_groups"][0]["size"], 3)

    def test_one_shared_tag_that_is_not_primary_is_not_a_pair(self):
        write(self.root / "acme", [entry(1, "260101", ["a", "pricing"]),
                                   entry(2, "260102", ["b", "pricing"]),
                                   entry(3, "260103", ["c", "pricing"])])
        self.assertEqual(run(self.root)["candidate_groups"], [])

    def test_type_status_and_confidence_gates(self):
        rows = [entry(1, "260101", ["x", "y"]),
                entry(2, "260102", ["x", "y"], confidence="rule"),
                entry(3, "260103", ["x", "y"], status="superseded"),
                entry(4, "260104", ["x", "y"], type_="metric"),
                entry(5, "260105", ["x", "y"], type_="learning"),
                entry(6, "260106", ["x", "y"], confidence="high")]   # legacy value reads as hypothesis
        write(self.root / "acme", rows)
        self.assertEqual(run(self.root, "--threshold", "2")["candidate_groups"][0]["ids"], [1, 6])

    def test_threshold_from_config_and_flag(self):
        write(self.root / "acme", THREE, config={"compile_threshold": 4})
        self.assertEqual(run(self.root / "acme")["candidate_groups"], [])
        self.assertEqual(len(run(self.root / "acme", "--threshold", "3")["candidate_groups"]), 1)

    def test_single_session_is_marked_not_dropped(self):
        write(self.root / "acme", [entry(i, "260401", ["x", "y"]) for i in (1, 2, 3)])
        g = run(self.root)["candidate_groups"][0]
        self.assertTrue(g["single_session"])
        self.assertEqual(g["distinct_dates"], 1)

    def test_groups_never_cross_folders(self):
        write(self.root / "acme", THREE[:2])
        write(self.root / "other", THREE[2:])
        self.assertEqual(run(self.root)["candidate_groups"], [])

    def test_non_transitive_overlap_stays_one_component(self):
        # 1~2 share {a,b}; 2~3 share {c,d}; 1 and 3 share nothing. One group of three:
        # splitting is a judged step, so the generator keeps the superset.
        write(self.root / "acme", [entry(1, "260101", ["a", "b"]),
                                   entry(2, "260102", ["x", "a", "b", "c", "d"]),
                                   entry(3, "260103", ["c", "d"])])
        self.assertEqual(run(self.root)["candidate_groups"][0]["ids"], [1, 2, 3])

    def test_iso_dates_in_the_file_do_not_break_a_run(self):
        # Seen on a live corpus: an unquoted 2026-04-01 is a date object to YAML, in
        # `date` and in `source.date`. The run must neither crash nor split the dates.
        folder = self.root / "acme"
        folder.mkdir()
        (folder / "_insights.yaml").write_text(
            "insights:\n"
            "  - {id: 1, type: pattern, date: 2026-04-01, summary: A, tags: [x, y],"
            " source: {file: f.md, date: 2026-04-01}}\n"
            "  - {id: 2, type: pattern, date: 260401, summary: B, tags: [x, y]}\n"
            "  - {id: 3, type: pattern, date: 260502, summary: C, tags: [x, y]}\n",
            encoding="utf-8")
        g = run(self.root)["candidate_groups"][0]
        self.assertEqual(g["distinct_dates"], 2)

    def test_dot_folders_are_skipped(self):
        write(self.root / ".archive", THREE)
        write(self.root / "acme" / ".handoff", THREE)
        self.assertEqual(run(self.root)["folders_scanned"], 0)


class TopicTags(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def test_no_marking_without_configuration(self):
        write(self.root / "acme", THREE)
        for tag in run(self.root)["candidate_groups"][0]["shared_tags"]:
            self.assertNotIn("topic", tag)

    def test_marked_when_configured(self):
        write(self.root / "acme", THREE, config={"insight_topic_tags": ["billing"]})
        tags = {t["tag"]: t["topic"] for t in run(self.root / "acme")["candidate_groups"][0]["shared_tags"]}
        self.assertEqual(tags, {"billing": True, "invoices": False})


class Keys(unittest.TestCase):
    def test_key_is_stable_and_order_independent(self):
        self.assertEqual(pc.group_key(THREE), pc.group_key(list(reversed(THREE))))

    def test_any_member_change_changes_the_key(self):
        base = pc.group_key(THREE)
        for field, value in (("summary", "Changed"), ("date", "260999"), ("tags", ["billing"])):
            changed = [dict(e) for e in THREE]
            changed[1][field] = value
            self.assertNotEqual(pc.group_key(changed), base, field)
        self.assertNotEqual(pc.group_key(THREE[:2]), base)


class Reviews(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def review(self, decision, members, key=None, reason=None, split_from=None):
        r = {"decision": decision, "date": "260927", "by": "dashboard",
             "group": [m["id"] for m in members],
             "group_key": key or pc.group_key(members), "reason": reason}
        if split_from:
            r["split_from"] = split_from
        return r

    def state(self, rows):
        write(self.root / "acme", rows)
        return run(self.root)["candidate_groups"][0]

    def test_unreviewed(self):
        self.assertEqual(self.state(THREE)["review_state"], "unreviewed")

    def test_approved_while_the_key_matches(self):
        rows = [dict(e) for e in THREE]
        rows[0]["promotion_review"] = self.review("approved", THREE)
        g = self.state(rows)
        self.assertEqual(g["review_state"], "approved")
        self.assertEqual(g["review"]["on_entry"], 1)

    def test_rejected_while_the_key_matches(self):
        rows = [dict(e) for e in THREE]
        rows[0]["promotion_review"] = self.review("rejected", THREE, reason="topic-only tags")
        g = self.state(rows)
        self.assertEqual(g["review_state"], "rejected")
        self.assertEqual(g["review"]["reason"], "topic-only tags")

    def test_stale_after_a_member_changes(self):
        rows = [dict(e) for e in THREE]
        rows[0]["promotion_review"] = self.review("approved", THREE)
        rows[2]["summary"] = "Edited since the review"
        self.assertEqual(self.state(rows)["review_state"], "stale")

    def test_stale_after_a_member_is_added(self):
        rows = [dict(e) for e in THREE]
        rows[0]["promotion_review"] = self.review("approved", THREE)
        rows.append(entry(4, "260401", ["billing", "invoices"]))
        g = self.state(rows)
        # The newcomer may be a reversal: the old approval must not quietly narrow to 1-3.
        self.assertEqual(g["review_state"], "stale")
        self.assertEqual(g["subset_reviews"][0]["state"], "stale")

    def test_split_subset_is_reported_with_its_own_state(self):
        rows = [dict(e) for e in THREE] + [entry(4, "260401", ["billing", "invoices"])]
        whole = pc.group_key(rows)
        subset = [rows[0], rows[1], rows[3]]
        rows[0]["promotion_review"] = self.review("approved", subset, split_from=whole)
        g = self.state(rows)
        self.assertEqual(g["review_state"], "unreviewed")      # the remainder is still open
        self.assertEqual(g["subset_reviews"][0]["group"], [1, 2, 4])
        self.assertEqual(g["subset_reviews"][0]["state"], "approved")

    def test_split_goes_stale_when_the_group_changes(self):
        rows = [dict(e) for e in THREE] + [entry(4, "260401", ["billing", "invoices"])]
        whole = pc.group_key(rows)
        rows[0]["promotion_review"] = self.review("approved", [rows[0], rows[1], rows[3]],
                                                  split_from=whole)
        rows.append(entry(5, "260501", ["billing", "invoices"]))
        self.assertEqual(self.state(rows)["review_state"], "stale")


if __name__ == "__main__":
    unittest.main()
