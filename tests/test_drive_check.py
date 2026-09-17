"""Drive capability probe (S-07): must answer list/read/write honestly,
never leak rclone stderr or a remote path, and never require rclone to be
installed at all."""
import subprocess
from unittest.mock import patch

from bridges.drive_bridge import capability
from tests.base import AionTest


def _run(returncode, stdout=b""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


class TestDriveCapability(AionTest):
    def test_rclone_missing_reports_cleanly(self):
        with patch("shutil.which", return_value=None):
            cap = capability()
        self.assertEqual(cap, {"list": False, "read": False, "write": False,
                               "detail": "rclone not installed"})

    def test_full_read_write_round_trip_succeeds(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if "cat" in cmd:
                return _run(0, b"x")
            return _run(0, b"")

        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.run", side_effect=fake_run):
            cap = capability()
        self.assertEqual(cap["list"], True)
        self.assertEqual(cap["write"], True)
        self.assertEqual(cap["read"], True)
        self.assertIn("list=ok", cap["detail"])
        self.assertIn("write=ok", cap["detail"])
        self.assertIn("read=ok", cap["detail"])
        # the probe file must always be deleted after a successful write
        self.assertTrue(any("deletefile" in c for c in calls))

    def test_read_only_remote_reports_write_false(self):
        def fake_run(cmd, **kwargs):
            if "lsd" in cmd:
                return _run(0, b"")
            return _run(1, b"")  # rcat and everything after fails

        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.run", side_effect=fake_run):
            cap = capability()
        self.assertEqual(cap["list"], True)
        self.assertEqual(cap["write"], False)
        self.assertEqual(cap["read"], False)

    def test_probe_is_deleted_even_if_the_read_back_check_fails(self):
        def fake_run(cmd, **kwargs):
            if "cat" in cmd:
                return _run(0, b"WRONG CONTENT")  # write "succeeded" but content mismatches
            return _run(0, b"")

        calls = []

        def tracking_run(cmd, **kwargs):
            calls.append(cmd)
            return fake_run(cmd, **kwargs)

        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.run", side_effect=tracking_run):
            cap = capability()
        self.assertFalse(cap["read"])  # content didn't match -> not a verified read
        self.assertTrue(any("deletefile" in c for c in calls))

    def test_never_leaks_stderr_or_remote_path_in_detail(self):
        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.run", return_value=_run(1, b"")):
            cap = capability()
        self.assertNotIn("gdrive:", cap["detail"])
        self.assertNotIn("MARK2_SHARED", cap["detail"])

    def test_timeout_and_missing_binary_are_treated_as_failure_not_a_crash(self):
        with patch("shutil.which", return_value="/usr/bin/rclone"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rclone", 15)):
            cap = capability()  # must not raise
        self.assertFalse(cap["list"])
        self.assertFalse(cap["write"])


if __name__ == "__main__":
    import unittest
    unittest.main()
