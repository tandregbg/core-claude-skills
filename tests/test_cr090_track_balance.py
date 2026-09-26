"""CR-090: the round shows each person's last track, and the balance across tracks.

    python3 -m unittest discover -s tests

Each case builds a small project, runs the real build_agenda.py, and reads the agenda -
the round is where a carried value can read as a confirmed one, so it is checked as
rendered, not as a return value.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OPS = Path(__file__).resolve().parents[1] / "skills" / "ops"
sys.path.insert(0, str(OPS))
import build_agenda as ba  # noqa: E402

ROUND = ("| | Track | Owed into today |\n|---|---|---|\n"
         "| **Ann** | web app | |\n| **Bo** | Web App *(carried)* | |\n| **Cai** | billing area | |\n")


def build(tracks=True, note_round=ROUND, window=None, earlier=None) -> str:
    root = Path(tempfile.mkdtemp()) / "proj"
    meetings = root / "meetings"
    meetings.mkdir(parents=True)
    cfg = ["workflows:", "  post_processing:", "    carry_forward:", "      enabled: true",
           "      round_columns: [Track]"]
    if window:
        cfg.append(f"      balance_window: {window}")
    cfg += ["people:", "  - name: Ann", "  - name: Bo", "  - name: Cai"]
    if tracks:
        cfg += ["tracks: [web app, website, onboarding]"]
    (root / "_ops.yaml").write_text("\n".join(cfg) + "\n", encoding="utf-8")
    if earlier:
        (meetings / "260921-daily-standup.md").write_text(
            "# Standup\n\n" + earlier + "\n## Carried forward\n\n- nothing carried\n", encoding="utf-8")
    (meetings / "260922-daily-standup.md").write_text(
        "# Standup\n\n" + (note_round or "No round table today.\n")
        + "\n## Carried forward\n\n- nothing carried\n", encoding="utf-8")
    subprocess.run([sys.executable, str(OPS / "build_agenda.py"), "--dir", str(meetings),
                    "--date", "260923"], check=True, capture_output=True, text=True)
    return (meetings / "260923-agenda-daily-standup.md").read_text(encoding="utf-8")


def row(agenda: str, name: str) -> list[str]:
    line = next(l for l in agenda.splitlines() if l.startswith(f"| **{name}**"))
    return [c.strip() for c in line.strip("|").split("|")]


class Helpers(unittest.TestCase):
    def test_declared_track_matches_case_insensitively_and_returns_declared_spelling(self):
        self.assertEqual(ba.declared_track("Web App", ["web app", "website"]), "web app")
        self.assertIsNone(ba.declared_track("billing area", ["web app"]))


class Round(unittest.TestCase):
    def test_last_track_carried_and_track_left_blank(self):          # verification 1
        a = build()
        head = next(l for l in a.splitlines() if "Last track" in l)
        self.assertEqual([c.strip() for c in head.strip("|").split("|")], ["", "Track", "Last track", "Owed into today"])
        ann = row(a, "Ann")
        self.assertEqual(ann[1], "")                                   # Track: stated in the room
        self.assertEqual(ann[2], "web app *(carried)*")
        self.assertEqual(row(a, "Bo")[2], "web app *(carried)*")       # declared spelling

    def test_non_track_value_is_not_carried(self):                      # verification 2
        self.assertEqual(row(build(), "Cai")[2], "")

    def test_balance_lists_every_declared_track_zeros_included(self):   # verification 3
        a = build()
        self.assertIn("Last session by track: web app 2 · website 0 · onboarding 0", a)
        self.assertIn("website and onboarding had no one. Intended, or unbalanced?", a)

    def test_no_round_table_says_so(self):                              # verification 4
        a = build(note_round=None)
        self.assertNotIn("Last track", a)
        self.assertNotIn("by track:", a)
        self.assertIn("not recorded", next(l for l in a.splitlines() if l.lstrip().startswith("round")))

    def test_without_tracks_behaviour_is_cr084(self):                   # verification 5
        a = build(tracks=False)
        self.assertNotIn("Last track", a)
        self.assertNotIn("by track:", a)
        self.assertEqual(row(a, "Ann")[1], "web app *(carried)*")

    def test_balance_window_counts_several_sessions(self):
        earlier = ("| | Track | Owed into today |\n|---|---|---|\n"
                   "| **Ann** | website | |\n| **Bo** | onboarding | |\n")
        a = build(window=5, earlier=earlier)
        self.assertIn("Last 2 sessions by track: web app 2 · website 1 · onboarding 1", a)
        self.assertNotIn("had no one", a)


if __name__ == "__main__":
    unittest.main()
