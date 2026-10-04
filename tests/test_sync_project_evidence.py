"""CE-5-02: evidence sync copies new packets, skips unchanged ones, refuses secrets.

Uses a LOCAL bare git repo as the "remote": no network anywhere.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import sync_project_evidence as sync  # noqa: E402

GOOD = "TASK_ID: CE-TEST\nSTATUS: DONE\n"
# Built at runtime so this file itself never contains a token-shaped literal.
FAKE_TOKEN = "ghp_" + "A1b2C3d4E5" * 3 + "F6g7H8"


def _git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


class SyncEvidenceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        # Bare "remote" seeded from a work tree holding one packet.
        self.bare = tmp / "remote.git"
        work = tmp / "work"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(self.bare)], check=True, capture_output=True)
        subprocess.run(["git", "clone", str(self.bare), str(work)], check=True, capture_output=True)
        self.ev_src = work / ".autonomous" / "capital_engine" / "EVIDENCE"
        self.ev_src.mkdir(parents=True)
        (self.ev_src / "CE-TEST.md").write_text(GOOD)
        self.work = work
        self._commit("add packet")
        # Fake LucyOS tree + AION_HOME.
        self.projects = tmp / "PROJECTS"
        (self.projects / "demo").mkdir(parents=True)
        (self.projects / "demo" / "project.json").write_text(json.dumps({"repos": [str(self.bare)]}))
        self.home = tmp / "home"
        self.evidence = self.projects / "demo" / "evidence"
        self._env = {k: os.environ.get(k) for k in ("AION_HOME", "AION_PROJECTS_DIR")}
        os.environ["AION_HOME"] = str(self.home)
        os.environ["AION_PROJECTS_DIR"] = str(self.projects)
        self.addCleanup(self._restore)

    def _restore(self):
        for k, v in self._env.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def _commit(self, msg):
        _git(self.work, "add", "-A")
        _git(self.work, "commit", "-m", msg)
        _git(self.work, "push", "origin", "HEAD:main")

    def _run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = sync.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_new_packet_copied_then_unchanged_not_recopied(self):
        rc, out, _ = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("COPIED", out)
        self.assertEqual((self.evidence / "CE-TEST.md").read_text(), GOOD)
        first_mtime = (self.evidence / "CE-TEST.md").stat().st_mtime_ns
        rc, out, _ = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("SKIPPED", out)
        self.assertNotIn("COPIED", out)
        self.assertEqual((self.evidence / "CE-TEST.md").stat().st_mtime_ns, first_mtime)

    def test_changed_packet_is_pulled_and_recopied(self):
        self._run()
        (self.ev_src / "CE-TEST.md").write_text(GOOD + "NOTE: updated\n")
        self._commit("update")
        rc, out, _ = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("COPIED", out)
        self.assertIn("updated", (self.evidence / "CE-TEST.md").read_text())

    def test_secret_like_packet_is_refused_and_reported(self):
        (self.ev_src / "CE-BAD.md").write_text(f"STATUS: DONE\nnote {FAKE_TOKEN}\n")
        self._commit("bad packet")
        rc, out, _ = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("REFUSED", out)
        self.assertIn("CE-BAD.md", out)
        self.assertIn("WARNING", out)
        self.assertNotIn(FAKE_TOKEN, out)
        self.assertFalse((self.evidence / "CE-BAD.md").exists())
        self.assertTrue((self.evidence / "CE-TEST.md").exists())  # clean packet still synced

    def test_dry_run_copies_nothing(self):
        rc, out, _ = self._run("--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("WOULD COPY", out)
        self.assertFalse(self.evidence.exists())

    def test_git_failure_exits_nonzero(self):
        (self.projects / "demo" / "project.json").write_text(
            json.dumps({"repos": [str(self.bare) + "-missing"]}))
        rc, _, err = self._run()
        self.assertNotEqual(rc, 0)
        self.assertIn("GIT FAILED", err)

    def test_disallowed_repo_entry_is_refused(self):
        (self.projects / "demo" / "project.json").write_text(json.dumps({"repos": ["ext::sh -c id"]}))
        rc, _, err = self._run()
        self.assertNotEqual(rc, 0)
        self.assertIn("not allowed", err)

    def test_github_shorthand_becomes_https_url(self):
        self.assertEqual(sync.clone_url("github.com/hetlife/strategy-factory"),
                         "https://github.com/hetlife/strategy-factory")


if __name__ == "__main__":
    unittest.main()
