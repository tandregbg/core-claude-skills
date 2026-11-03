"""CR-172: the watcher read the wrong tree, and said nothing about the one it was given.

`privacy-scan.sh --tree` resolved its file list with `git -C "$REPO" ls-files`, which prints
REPO-RELATIVE paths, and then piped them into `xargs -0 cat` running in the CALLER's directory.
Two effects, and the second is the one that made it invisible:

1. Where a path existed in both trees, the caller's copy was scanned instead of the repository's.
   Run from a vault whose `CLAUDE.md` shares the name, the watcher reported six findings that were
   all the vault's own legitimate content.
2. Where a path existed ONLY in the repository, `cat` failed and `2>/dev/null` ate the error, so
   the file was skipped in silence. Most of the repository was never scanned at all.

The declared command in a vault config is `bash <repo>/scripts/privacy-scan.sh --tree`, run by
`/ops check` from the vault root -- so the scheduled watcher had been answering a different
question since the script was written on 2026-07-10. The blocking gate was never affected: the
pre-push hook pipes added lines through `--stdin`, which resolves no paths.

Both halves are asserted here, because fixing only the first leaves the silent half free to
return. A throwaway repository is built per test so the real one is never touched.

    python3 -m unittest discover -s tests
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "privacy-scan.sh"
ALLOWLIST = ROOT / "scripts" / "githooks" / "allowed-examples.txt"


# The planted string is a BUILTIN *command* pattern rather than an identifier: a fixture has
# to trip the scanner without carrying anything real about any network. An address from the
# measured vault was the first draft and the gate rejected the commit -- correctly.
#
# It is ASSEMBLED AT RUNTIME so the literal never appears in this file. No tracked file in
# the repository contains a built-in pattern, the hook excludes nothing, and a test is a bad
# reason to be the first exception: the alternative is an exclusion for `tests/`, which is a
# hole someone later puts a real credential through.
PLANTED = "sshpass" + " -p hunter2"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class PrivacyScanTree(unittest.TestCase):
    """A throwaway repository with the script inside it, so REPO resolves to the fixture."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cr172-repo-"))
        self.elsewhere = Path(tempfile.mkdtemp(prefix="cr172-cwd-"))
        (self.tmp / "scripts" / "githooks").mkdir(parents=True)
        shutil.copy2(SCAN, self.tmp / "scripts" / "privacy-scan.sh")
        shutil.copy2(ALLOWLIST, self.tmp / "scripts" / "githooks" / "allowed-examples.txt")
        (self.tmp / "docs").mkdir()
        (self.tmp / "docs" / "clean.md").write_text("# Clean\n\nNothing of interest here.\n",
                                                    encoding="utf-8")
        _git(self.tmp, "init")
        # The denylist is the operator's private file; a test must not depend on it.
        _git(self.tmp, "config", "guard.denylist", "")
        _git(self.tmp, "add", "-A")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.elsewhere, ignore_errors=True)

    def run_scan(self, cwd):
        return subprocess.run(["bash", str(self.tmp / "scripts" / "privacy-scan.sh"), "--tree"],
                              cwd=str(cwd), capture_output=True, text=True)

    # --- half one: the answer may not depend on where the scan was started -------------

    def test_same_verdict_from_any_directory(self):
        """The declared command is run from a vault; the answer must be the repository's."""
        from_repo = self.run_scan(self.tmp)
        from_elsewhere = self.run_scan(self.elsewhere)
        self.assertEqual(from_repo.stdout, from_elsewhere.stdout,
                         "the verdict changed with the working directory")
        self.assertEqual(from_repo.returncode, from_elsewhere.returncode)

    def test_a_colliding_name_outside_the_repo_is_not_scanned(self):
        """The measured failure: a file of the same name in the caller's directory was read.

        `docs/clean.md` is clean in the repository and carries a secret in the caller's tree.
        A scan that reads the caller's copy reports a finding; the repository's answer is clean.
        """
        (self.elsewhere / "docs").mkdir()
        (self.elsewhere / "docs" / "clean.md").write_text(
            PLANTED + " not-in-the-repository\n", encoding="utf-8")
        res = self.run_scan(self.elsewhere)
        self.assertNotIn("sshpass", res.stdout,
                         "the scan read the caller's file instead of the repository's")
        self.assertEqual(res.returncode, 0, res.stdout)

    # --- half two: a file only the repository has must actually be read ----------------

    def test_a_repo_only_file_is_read(self):
        """The silent half. `cat` on a repo-relative path failed outside the repo and
        `2>/dev/null` hid it, so a file with no counterpart was skipped without a word."""
        (self.tmp / "docs" / "only-in-repo.md").write_text(
            "a line with " + PLANTED + "\n", encoding="utf-8")
        _git(self.tmp, "add", "-A")
        res = self.run_scan(self.elsewhere)
        self.assertIn("sshpass", res.stdout,
                      "a file only the repository has was not scanned")
        self.assertEqual(res.returncode, 1)

    def test_an_unreadable_tracked_file_is_reported_not_skipped(self):
        """An unscanned file is not a clean one, so it is named rather than swallowed."""
        gone = self.tmp / "docs" / "tracked-then-removed.md"
        gone.write_text("# tracked\n", encoding="utf-8")
        _git(self.tmp, "add", "-A")
        gone.unlink()                       # tracked in the index, absent on disk
        res = self.run_scan(self.elsewhere)
        self.assertIn("UNSCANNED", res.stdout,
                      "an unreadable tracked file passed as clean")
        self.assertEqual(res.returncode, 1)

    # --- the gate itself was never affected, and that is why the risk was bounded ------

    def test_stdin_mode_resolves_no_paths(self):
        """The pre-push hook pipes added lines through --stdin, so it never had this bug."""
        res = subprocess.run(["bash", str(self.tmp / "scripts" / "privacy-scan.sh"), "--stdin"],
                             input="a line mentioning " + PLANTED + "\n",
                             cwd=str(self.elsewhere), capture_output=True, text=True)
        self.assertIn("sshpass", res.stdout)
        self.assertEqual(res.returncode, 1)


if __name__ == "__main__":
    unittest.main()
