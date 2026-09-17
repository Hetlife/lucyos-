"""S-28: sanitized runtime inventory -- proves nothing sensitive leaks and
the output is safe to hand to another human for a migration."""
import getpass
import json
import socket
import unittest
from pathlib import Path

from scripts.runtime_inventory import collect, render
from aion_core import security


class RuntimeInventoryTest(unittest.TestCase):
    def test_output_passes_security_redact_unchanged(self):
        text = render(collect())
        self.assertEqual(security.redact(text), text)
        self.assertEqual(security.scan_text(text), [])

    def test_no_username_leaks(self):
        text = render(collect())
        try:
            user = getpass.getuser()
        except Exception:
            user = None
        if user:
            self.assertNotIn(user, text)

    def test_no_home_path_leaks(self):
        text = render(collect())
        home = str(Path.home())
        self.assertNotIn(home, text)

    def test_no_hostname_leaks(self):
        text = render(collect())
        hostname = socket.gethostname()
        if hostname and len(hostname) > 2:  # skip trivially short/common hostnames
            self.assertNotIn(hostname, text)

    def test_no_env_values_present(self):
        # A sanitized inventory must never dump os.environ or any of its
        # values -- only fixed, known-safe facts this script computes itself.
        import inspect
        import scripts.runtime_inventory as mod
        src = inspect.getsource(mod)
        self.assertNotIn("os.environ", src)
        self.assertNotIn("getenv", src)

    def test_tooling_reports_booleans_never_paths(self):
        inv = collect()
        self.assertIn("tooling", inv)
        for tool, present in inv["tooling"].items():
            self.assertIsInstance(present, bool, f"{tool} should report a boolean, not a path")

    def test_no_network_call_anywhere_in_the_script(self):
        import inspect
        import scripts.runtime_inventory as mod
        src = inspect.getsource(mod)
        for forbidden in ("socket.create_connection", "urllib.request", "requests.",
                          "http.client", "subprocess.run"):
            self.assertNotIn(forbidden, src, f"found forbidden call pattern: {forbidden}")

    def test_expected_fields_present(self):
        inv = collect()
        for field in ("python_version", "platform_system", "platform_machine",
                      "cpu_count", "disk_free_gb", "sqlite_version", "tooling"):
            self.assertIn(field, inv)

    def test_output_is_valid_json(self):
        text = render(collect())
        parsed = json.loads(text)
        self.assertIsInstance(parsed, dict)

    def test_host_adapter_fields_are_optional_never_crash_when_absent(self):
        # Whether or not aion_core.host (S-10) is present on this checkout,
        # collect() must never raise -- host facts are best-effort only.
        inv = collect()
        self.assertIsInstance(inv, dict)


if __name__ == "__main__":
    unittest.main()
