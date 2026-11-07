"""Exercise the real shell wrapper against a hermetic fake AION executable."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class BuildLoopExitTest(unittest.TestCase):
    def run_loop(self, **settings):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            source = Path(__file__).resolve().parents[1] / "scripts" / "build_loop.sh"
            shutil.copyfile(source, root / "scripts" / "build_loop.sh")
            fake = root / "aion"
            fake.write_text("""#!/bin/sh
printf '%s\\n' "$1" >> "$AION_TEST_CALLS"
case "$1" in
 boot) exit "${BOOT_EXIT:-0}" ;;
 milestones) printf '%s\\n' "${MILESTONE:-none}"; exit 0 ;;
 work) exit "${WORK_EXIT:-0}" ;;
 sync-docs) exit "${SYNC_EXIT:-0}" ;;
 supervisor) exit "${SUPERVISOR_EXIT:-0}" ;;
 whatsapp) exit 0 ;;
 *) exit 99 ;;
esac
""")
            fake.chmod(0o700)
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("AION_", "BOOT_EXIT", "WORK_EXIT",
                                        "SYNC_EXIT", "SUPERVISOR_EXIT", "MILESTONE"))}
            env.update(AION_HOME=str(root / "brain"),
                       AION_TEST_CALLS=str(root / "calls"))
            env.update({k: str(v) for k, v in settings.items()})
            result = subprocess.run(["bash", str(root / "scripts" / "build_loop.sh")],
                                    env=env, capture_output=True, text=True, timeout=10)
            return result, (root / "calls").read_text().splitlines()

    def test_worker_failure_reaches_scheduler(self):
        result, calls = self.run_loop(WORK_EXIT=7)
        self.assertEqual(result.returncode, 7)
        self.assertIn("supervisor", calls)

    def test_boot_failure_prevents_work(self):
        result, calls = self.run_loop(BOOT_EXIT=9)
        self.assertEqual(result.returncode, 9)
        self.assertEqual(calls, ["boot"])

    def test_idle_success_remains_success(self):
        result, calls = self.run_loop()
        self.assertEqual(result.returncode, 0)
        self.assertIn("work", calls)

    def test_advisory_failures_do_not_erase_worker_failure(self):
        result, _ = self.run_loop(WORK_EXIT=7, SYNC_EXIT=4, SUPERVISOR_EXIT=5)
        self.assertEqual(result.returncode, 7)

    def test_advisory_failure_does_not_fail_successful_work(self):
        result, _ = self.run_loop(SUPERVISOR_EXIT=5)
        self.assertEqual(result.returncode, 0)
        self.assertIn("warning", result.stderr)

    def test_milestone_still_pauses_without_work(self):
        result, calls = self.run_loop(MILESTONE="M1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("whatsapp", calls)
        self.assertNotIn("work", calls)
