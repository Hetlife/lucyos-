"""S-09: `aion openclaw-check` -- loopback reachability probe for an
optional OpenClaw gateway. Never touches anything but 127.0.0.1."""
import http.server
import threading
import unittest

from tests.base import AionTest
from bridges import openclaw_check
from aion_core import db, health


class OpenClawCheckTest(unittest.TestCase):
    def test_not_configured_when_no_port_set(self):
        result = openclaw_check.check("")
        self.assertEqual(result["state"], openclaw_check.NOT_CONFIGURED)

    def test_not_configured_when_port_is_garbage(self):
        result = openclaw_check.check("not-a-port")
        self.assertEqual(result["state"], openclaw_check.NOT_CONFIGURED)

    def test_not_configured_when_port_out_of_range(self):
        result = openclaw_check.check("999999")
        self.assertEqual(result["state"], openclaw_check.NOT_CONFIGURED)

    def test_unreachable_when_nothing_listening(self):
        # Port 1 is a privileged port almost never bound in a test sandbox;
        # a closed-connection probe against loopback proves "unreachable"
        # without needing a real server to *not* exist elsewhere.
        result = openclaw_check.check("1")
        self.assertEqual(result["state"], openclaw_check.UNREACHABLE)

    def test_reachable_against_a_real_loopback_server(self):
        server = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        try:
            result = openclaw_check.check(str(port))
            self.assertEqual(result["state"], openclaw_check.REACHABLE)
        finally:
            thread.join(timeout=3)
            server.server_close()

    def test_never_targets_anything_but_loopback(self):
        # There is no host parameter at all -- the only string this module
        # ever builds a URL from is a hard-coded "127.0.0.1" plus a
        # caller-supplied *port*, never a caller-supplied host.
        import inspect
        src = inspect.getsource(openclaw_check)
        self.assertIn('"http://127.0.0.1:', src)
        self.assertNotIn("requested_host", src)


class OpenClawCheckIntegrationTest(AionTest):
    def test_check_reads_port_from_db_meta_when_not_passed_explicitly(self):
        db.set_meta("openclaw_port", "1")
        result = openclaw_check.check()
        self.assertEqual(result["state"], openclaw_check.UNREACHABLE)

    def test_health_check_is_non_required_and_always_ok(self):
        db.set_meta("openclaw_port", "")
        report = health.check_openclaw()
        self.assertTrue(report["ok"])
        self.assertFalse(report.get("required", True))
        self.assertIn("not-configured", report["detail"])

        db.set_meta("openclaw_port", "1")
        report = health.check_openclaw()
        self.assertTrue(report["ok"])
        self.assertIn("unreachable", report["detail"])

    def test_openclaw_check_appears_in_full_health_report(self):
        report = health.run_all()
        names = [r["name"] for r in report["checks"]]
        self.assertIn("openclaw", names)


if __name__ == "__main__":
    unittest.main()
