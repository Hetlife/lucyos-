"""The authority verifier must refuse what the contract forbids — in git, not in prose."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VERIFIER = REPO / "scripts" / "verify_authority.py"


def run(args, cwd):
    return subprocess.run([sys.executable, str(VERIFIER), *args], cwd=cwd,
                          capture_output=True, text=True)


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class TestAuthorityVerifier(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="authority-"))
        git(self.tmp, "init", "-q", "-b", "integration")
        git(self.tmp, "config", "user.email", "t@t")
        git(self.tmp, "config", "user.name", "t")
        (self.tmp / ".lucy/authority").mkdir(parents=True)
        (self.tmp / "aion_core").mkdir()
        (self.tmp / "aion_core/db.py").write_text("import sqlite3\n")
        (self.tmp / "aion_core/free.py").write_text("x = 1\n")
        self.baseline = {
            "protected_paths": [".lucy/authority/**", "aion_core/db.py"],
            "aion_core_modules": ["db", "free"],
            "sqlite_connect_allowed": ["aion_core/db.py"],
            "service_unit_dirs": ["systemd/"],
            "task_overrides": {"S-01": ["aion_core/db.py"]},
            "protected_file_hashes": {},
            "fable_freeze_sha": "PENDING",
        }
        self._write_baseline()
        git(self.tmp, "add", "-A")
        git(self.tmp, "commit", "-q", "-m", "base")
        git(self.tmp, "checkout", "-q", "-b", "task/S-09-thing")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_baseline(self):
        (self.tmp / ".lucy/authority/HIGH_MODEL_BASELINE.json").write_text(json.dumps(self.baseline))

    def _commit(self, msg):
        git(self.tmp, "add", "-A")
        git(self.tmp, "commit", "-q", "-m", msg)

    def test_unprotected_change_passes(self):
        (self.tmp / "aion_core/free.py").write_text("x = 2\n")
        self._commit("free change")
        r = run(["strict", "--base", "integration", "--branch", "task/S-09-thing"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_protected_change_without_override_fails(self):
        (self.tmp / "aion_core/db.py").write_text("import sqlite3\n# changed\n")
        self._commit("touch db")
        r = run(["strict", "--base", "integration", "--branch", "task/S-09-thing"], self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no override", r.stdout)

    def test_protected_change_with_override_from_base_passes(self):
        (self.tmp / "aion_core/db.py").write_text("import sqlite3\n# changed\n")
        self._commit("touch db\n\nTask-ID: S-01")
        r = run(["strict", "--base", "integration"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_branch_cannot_grant_itself_an_override(self):
        # The branch edits the baseline to add its own override: must still fail,
        # because the verifier reads the baseline from BASE and the baseline path
        # itself is constitutional.
        self.baseline["task_overrides"]["S-09"] = ["aion_core/db.py"]
        self._write_baseline()
        (self.tmp / "aion_core/db.py").write_text("import sqlite3\n# changed\n")
        self._commit("self-grant")
        r = run(["strict", "--base", "integration", "--branch", "task/S-09-thing"], self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("constitutional", r.stdout)

    def test_undeclared_task_id_fails(self):
        (self.tmp / "aion_core/db.py").write_text("import sqlite3\n# changed\n")
        self._commit("no task id")
        r = run(["strict", "--base", "integration", "--branch", "feature/no-id"], self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("undeclared", r.stdout)

    def test_anti_dup_catches_second_state_store_and_new_module(self):
        (self.tmp / "aion_core/free.py").write_text("import sqlite3\nc = sqlite3.connect('x')\n")
        (self.tmp / "aion_core/scheduler2.py").write_text("import apscheduler\n")
        self._commit("dup")
        r = run(["anti-dup", "--base", "integration"], self.tmp)
        self.assertEqual(r.returncode, 1)
        out = r.stdout
        self.assertIn("sqlite3.connect", out)
        self.assertIn("not in baseline allowlist", out)
        self.assertIn("orchestration/scheduler import", out)
        self.assertIn("named like a control-plane", out)

    def test_anti_dup_passes_on_ordinary_change(self):
        (self.tmp / "aion_core/free.py").write_text("x = 3\n")
        self._commit("fine")
        r = run(["anti-dup", "--base", "integration"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_freeze_then_self_detects_drift(self):
        r = run(["freeze", "--sha", "PENDING"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(run(["self"], self.tmp).returncode, 0)
        (self.tmp / "aion_core/db.py").write_text("drifted\n")
        r = run(["self"], self.tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("hash drift", r.stdout)


if __name__ == "__main__":
    unittest.main()
