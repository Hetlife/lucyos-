"""S-15: contract C4 says OpenClaw is replaceable -- LucyOS's own core must
never depend on it existing.  This proves that claim by running the whole
core lifecycle with no OpenClaw process, no gateway port configured, and no
OpenClaw-related environment variable set.

Test-only: if any step here fails because core code actually reaches for
something OpenClaw-specific, that is the finding -- this file must not be
weakened to make it pass.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Any env var whose name suggests it configures an OpenClaw process/gateway.
# None of these are read by aion_core today (verified by grep across
# aion_core/ and bridges/); scrubbing them anyway is what proves it, not an
# assumption.
_OPENCLAW_ENV_PREFIXES = ("OPENCLAW_", "GATEWAY_")


class OpenClawIndependenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aion-test-noclaw-"))
        self._saved_env = dict(os.environ)
        for key in list(os.environ):
            if key.startswith(_OPENCLAW_ENV_PREFIXES) or key == "OPENCLAW":
                os.environ.pop(key, None)
        os.environ["AION_HOME"] = str(self.tmp)
        os.environ.pop("AION_DB", None)
        from aion_core import db
        db.close()

    def tearDown(self):
        from aion_core import db
        db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.clear()
        os.environ.update(self._saved_env)

    def test_full_lifecycle_with_no_openclaw_present(self):
        for key in os.environ:
            self.assertFalse(
                key.startswith(_OPENCLAW_ENV_PREFIXES) or key == "OPENCLAW",
                f"OpenClaw-related env var {key} leaked into a supposedly clean run",
            )

        from aion_core import approvals, backup, bootstrap, resume, seed, tasks

        # init
        n_created = bootstrap.ensure()
        self.assertGreater(n_created, 0)
        self.assertTrue((self.tmp / "state").is_dir())

        # seed
        seeded = seed.apply()
        self.assertFalse(seeded["skipped"])
        self.assertGreater(len(seeded["tasks"]), 0)

        # create and transition a task
        task_id = tasks.create("independence check task")
        row = tasks.get(task_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "READY")
        tasks.update(task_id, status="RUNNING")
        tasks.update(task_id, status="DONE", evidence="proved without OpenClaw")
        row = tasks.get(task_id)
        self.assertEqual(row["status"], "DONE")

        # create and decide an approval
        approval_id = approvals.create(
            "prove OpenClaw independence",
            why="contract C4 replaceability test",
            task_id=task_id,
        )
        pending_before = [a["approval_id"] for a in approvals.pending()]
        self.assertIn(approval_id, pending_before)
        result = approvals.decide(approval_id, approvals.APPROVED, by="owner")
        self.assertEqual(result["status"], approvals.APPROVED)
        pending_after = [a["approval_id"] for a in approvals.pending()]
        self.assertNotIn(approval_id, pending_after)

        # take and verify a backup
        backup_path = backup.create()
        self.assertTrue(backup_path.exists())
        verify_result = backup.verify()
        self.assertTrue(verify_result["ok"], f"backup did not verify clean: {verify_result}")

        # boot
        boot_result = resume.boot()
        self.assertIsInstance(boot_result, dict)


if __name__ == "__main__":
    unittest.main()
