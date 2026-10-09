"""CR-116: report series kept in the vault are declared like repo reports and shown
with their age. Local files only. All data here is invented."""

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "ops"))
import build_movement as bm  # noqa: E402


class VaultReports(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.proj = self.root / "org" / "proj"
        self.proj.mkdir(parents=True)
        rep = self.root / "org" / "board" / "status"
        rep.mkdir(parents=True)
        for n in ("260924-board-status.md", "260925-board-status.md", "260925b-board-status.md", "_TEMPLATE.md"):
            (rep / n).write_text("x", encoding="utf-8")

    def cf(self, **extra):
        r = {"name": "Board status", "dir": "../board/status", "pattern": r"^\d{6}[a-z]?-board-status\.md$"}
        r.update(extra)
        return {"_root": self.proj, "ext": {"vault_reports": [r]}}

    def test_newest_of_a_dated_series_with_age(self):
        lines, states = bm.vault_reports(self.cf(), dt.date(2026, 9, 26))
        self.assertIn("newest 260925b-board-status.md · 1d old", lines[0])
        self.assertEqual(states[0][3], 1)

    def test_missing_dir_says_so(self):
        cf = {"_root": self.proj, "ext": {"vault_reports": [{"name": "X", "dir": "nowhere", "pattern": "."}]}}
        lines, _ = bm.vault_reports(cf, dt.date(2026, 9, 26))
        self.assertIn("NOT FOUND", lines[0])

    def test_owner_is_carried(self):
        _, states = bm.vault_reports(self.cf(owner="Ann"), dt.date(2026, 9, 26))
        self.assertEqual(states[0][1], "Ann")


if __name__ == "__main__":
    unittest.main()
