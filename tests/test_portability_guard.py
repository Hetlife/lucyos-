"""The portability guard must catch what the invariant forbids -- and stay a ratchet.

A guard that only ever passes proves nothing, so these tests drive the real
scanner over synthetic files and assert both directions: new coupling fails,
portable code passes, and a stale exception fails so the excuse list cannot rot.
"""
import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "scripts" / "check_portability.py"


def load_guard():
    spec = importlib.util.spec_from_file_location("check_portability", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPortabilityGuard(unittest.TestCase):
    def setUp(self):
        self.guard = load_guard()

    def _findings(self, source: str, name: str = "sample.py"):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_text(source, encoding="utf-8")
            # findings_for() reports paths relative to REPO; for a temp file that
            # is not under REPO we only care about the rules that matched.
            original = self.guard.REPO
            self.guard.REPO = Path(tmp)
            try:
                return [f["rule"] for f in self.guard.findings_for(path)]
            finally:
                self.guard.REPO = original

    def test_repository_is_currently_portable(self):
        """The live tree must pass, or the ratchet is already broken."""
        self.assertEqual(self.guard.main(["--json"]), 0)

    def test_init_system_reference_is_caught(self):
        self.assertIn("init_system", self._findings(
            "import subprocess\nsubprocess.run(['systemctl', 'status', 'x'])\n"))

    def test_launchctl_is_caught_too(self):
        self.assertIn("init_system", self._findings(
            "import subprocess\nsubprocess.run(['launchctl', 'list'])\n"))

    def test_os_branching_is_caught(self):
        self.assertIn("os_branch", self._findings(
            "import sys\nif sys.platform == 'darwin':\n    pass\n"))
        self.assertIn("os_branch", self._findings(
            "import platform\nkind = platform.system().lower()\n"))

    def test_os_specific_absolute_path_is_caught(self):
        self.assertIn("os_path", self._findings("CONF = '/etc/lucyos.conf'\n"))
        self.assertIn("os_path", self._findings("LIB = '/Library/Application Support'\n"))

    def test_package_manager_is_caught(self):
        self.assertIn("pkg_manager", self._findings(
            "import subprocess\nsubprocess.run(['brew', 'install', 'x'])\n"))

    def test_defensive_denylist_literals_are_not_coupling(self):
        source = (
            'FORBIDDEN_COMMANDS = ["systemctl ", "launchctl ", "brew", "apt-get"]\n'
            'def blocked(command):\n'
            '    return any(marker in command for marker in FORBIDDEN_COMMANDS)\n'
        )
        self.assertEqual(self._findings(source), [])

    def test_real_command_variable_still_fails(self):
        source = (
            'import subprocess\n'
            'command = "systemctl status lucyos"\n'
            'subprocess.run(command, shell=True)\n'
        )
        self.assertIn("init_system", self._findings(source))

    def test_scheduler_mapping_string_still_fails(self):
        source = 'scheduler = "systemd" if kind == "linux" else "launchd"\n'
        self.assertIn("init_system", self._findings(source))

    def test_masking_denylist_does_not_hide_real_call_on_same_line(self):
        source = (
            'import subprocess\n'
            'FORBIDDEN = ["systemctl"]; subprocess.run(["launchctl", "list"])\n'
        )
        self.assertIn("init_system", self._findings(source))

    def test_policy_name_cannot_hide_indexed_execution(self):
        source = (
            'import subprocess\n'
            'FORBIDDEN = ["systemctl"]\n'
            'subprocess.run([FORBIDDEN[0], "status", "x"])\n'
        )
        self.assertIn("init_system", self._findings(source))

    def test_policy_name_cannot_hide_looped_execution(self):
        source = (
            'import subprocess\n'
            'FORBIDDEN = ["systemctl"]\n'
            'for command in FORBIDDEN:\n'
            '    subprocess.run([command, "status", "x"])\n'
        )
        self.assertIn("init_system", self._findings(source))

    def test_real_package_manager_variable_still_fails(self):
        source = (
            'import subprocess\n'
            'installer = "apt-get install x"\n'
            'subprocess.run(installer, shell=True)\n'
        )
        self.assertIn("pkg_manager", self._findings(source))

    def test_portable_code_passes(self):
        portable = (
            "import os\n"
            "from pathlib import Path\n"
            "import tempfile\n"
            "def home():\n"
            "    return Path(os.environ.get('AION_HOME', Path.home() / 'x'))\n"
            "def scratch():\n"
            "    return tempfile.mkdtemp()\n"
        )
        self.assertEqual(self._findings(portable), [])

    def test_hostname_identity_is_not_an_os_branch(self):
        """platform.node() is identity, not an OS decision -- must stay allowed."""
        self.assertEqual(self._findings(
            "import platform\nworker = platform.node() or 'local'\n"), [])

    def test_api_route_string_is_not_an_os_path(self):
        self.assertEqual(self._findings("ROUTES = '/api/money, /api/errors'\n"), [])

    def test_docstring_discussion_is_not_a_violation(self):
        """Documenting the invariant must not trip it."""
        source = (
            '"""This module must not call systemctl or branch on sys.platform."""\n'
            "VALUE = 1\n"
        )
        self.assertEqual(self._findings(source), [])

    def test_comment_is_not_a_violation(self):
        self.assertEqual(self._findings("VALUE = 1  # never call launchctl here\n"), [])

    def test_stale_exception_fails_the_guard(self):
        """An exception whose coupling is gone must fail, so the list only shrinks."""
        self.guard.KNOWN_EXCEPTIONS = dict(self.guard.KNOWN_EXCEPTIONS)
        self.guard.KNOWN_EXCEPTIONS["aion_core/does_not_exist.py::init_system"] = "S-99"
        self.assertEqual(self.guard.main(["--json"]), 1)

    def test_every_known_exception_names_a_task(self):
        for key, task in self.guard.KNOWN_EXCEPTIONS.items():
            self.assertRegex(task, r"^(S|FABLE|OWNER)-\d+$",
                             f"exception {key!r} must name the task that removes it")


if __name__ == "__main__":
    unittest.main()
