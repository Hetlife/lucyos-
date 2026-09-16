"""The platform adapter layer (contract C1) must answer honestly: a fact it
cannot verify is None, never a guessed False. Both adapters are exercised
directly (not via host.current()) so these tests run on any platform."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from aion_core import host
from aion_core.host.base import HostAdapter, NullHostAdapter
from aion_core.host.linux import LinuxHost
from aion_core.host.macos import MacOSHost


def _completed(returncode, stdout=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


class TestNullHostAdapter(unittest.TestCase):
    def test_never_raises_and_service_active_is_none(self):
        a = NullHostAdapter()
        self.assertEqual(a.name(), "unknown")
        self.assertEqual(a.scheduler_kind(), "native-timer")
        self.assertIsNone(a.service_active("anything"))
        self.assertIsInstance(a.service_install_hint("anything"), str)

    def test_probe_returns_only_capability_facts(self):
        probe = NullHostAdapter().probe()
        self.assertEqual(set(probe), {"name", "scheduler_kind", "service_unit_dir"})


class TestCurrentNeverRaises(unittest.TestCase):
    def test_current_selects_something_without_raising(self):
        adapter = host.current()  # exercises the real platform.system() path
        self.assertIsInstance(adapter, HostAdapter)
        self.assertIn(adapter.name(), ("linux", "macos", "unknown"))

    def test_unrecognized_platform_falls_back_to_null_adapter(self):
        with patch("platform.system", return_value="PlaywrightOS"):
            adapter = host.current()
        self.assertIsInstance(adapter, NullHostAdapter)
        self.assertIsNone(adapter.service_active("x"))  # never raises, never guesses


class TestLinuxHost(unittest.TestCase):
    def setUp(self):
        self.host = LinuxHost()

    def test_identity_and_scheduler(self):
        self.assertEqual(self.host.name(), "linux")
        self.assertEqual(self.host.scheduler_kind(), "systemd")
        self.assertTrue(str(self.host.service_unit_dir()).endswith("systemd"))

    def test_service_active_true_on_returncode_0(self):
        with patch("subprocess.run", return_value=_completed(0)):
            self.assertIs(self.host.service_active("aion-work.timer"), True)

    def test_service_active_false_on_returncode_3(self):
        with patch("subprocess.run", return_value=_completed(3)):
            self.assertIs(self.host.service_active("aion-work.timer"), False)

    def test_service_active_none_on_unexpected_returncode(self):
        with patch("subprocess.run", return_value=_completed(42)):
            self.assertIsNone(self.host.service_active("aion-work.timer"))

    def test_service_active_none_when_systemctl_missing(self):
        with patch("subprocess.run", side_effect=OSError("no such binary")):
            self.assertIsNone(self.host.service_active("aion-work.timer"))

    def test_service_active_none_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("systemctl", 5)):
            self.assertIsNone(self.host.service_active("aion-work.timer"))


class TestMacOSHost(unittest.TestCase):
    def setUp(self):
        self.host = MacOSHost()

    def test_identity_and_scheduler(self):
        self.assertEqual(self.host.name(), "macos")
        self.assertEqual(self.host.scheduler_kind(), "launchd")
        self.assertTrue(str(self.host.service_unit_dir()).endswith("deploy/launchd"))

    def test_service_active_true_when_pid_present(self):
        with patch("subprocess.run", return_value=_completed(0, "1234\t0\tcom.lucyos.aion-work\n")):
            self.assertIs(self.host.service_active("com.lucyos.aion-work"), True)

    def test_service_active_false_when_loaded_but_no_pid(self):
        with patch("subprocess.run", return_value=_completed(0, "-\t0\tcom.lucyos.aion-work\n")):
            self.assertIs(self.host.service_active("com.lucyos.aion-work"), False)

    def test_service_active_false_when_not_loaded(self):
        # launchctl genuinely answered "no such job" -- a real, verified no.
        with patch("subprocess.run", return_value=_completed(113)):
            self.assertIs(self.host.service_active("com.lucyos.nope"), False)

    def test_service_active_none_when_launchctl_missing(self):
        with patch("subprocess.run", side_effect=OSError("no such binary")):
            self.assertIsNone(self.host.service_active("com.lucyos.aion-work"))

    def test_service_active_none_never_rendered_as_false(self):
        """The exact bug this whole layer exists to prevent (C1)."""
        with patch("subprocess.run", side_effect=OSError()):
            result = self.host.service_active("x")
        self.assertIsNone(result)
        self.assertIsNot(result, False)


if __name__ == "__main__":
    unittest.main()
