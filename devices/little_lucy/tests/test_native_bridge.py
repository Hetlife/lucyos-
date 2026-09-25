import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import HTTPServer
import urllib.error
import urllib.request

from devices.little_lucy import bridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = os.environ.get("AION_DB")
        self.old_home = os.environ.get("AION_HOME")
        os.environ["AION_DB"] = str(Path(self.tmp.name) / "test.sqlite3")
        os.environ["AION_HOME"] = self.tmp.name
        bridge.db.connect()

    def tearDown(self):
        for name, value in (("AION_DB", self.old_db), ("AION_HOME", self.old_home)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.tmp.cleanup()

    def test_real_engine_decision_and_replay(self):
        approval_id = bridge.approvals.create("Isolated test action")
        card = bridge.snapshot()["approvals"][0]
        with self.assertRaises(ValueError):
            bridge.decide({"approval_id": approval_id, "revision": "wrong", "decision": "APPROVED"})
        payload = {"approval_id": approval_id, "revision": card["revision"], "decision": "APPROVED"}
        result = bridge.decide(payload)
        self.assertEqual(result["status"], "APPROVED")
        with self.assertRaises(ValueError):
            bridge.decide(payload)
        self.assertEqual(bridge.snapshot()["approvals"], [])

    def test_empty_source_is_not_fake_progress(self):
        snapshot = bridge.snapshot()
        self.assertEqual(snapshot["counts"], {})
        self.assertEqual(snapshot["active"], [])

    def test_http_auth_and_narrow_routes(self):
        server = HTTPServer(("127.0.0.1", 0), bridge.Handler)
        server.auth_value = "isolated-test-value"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        cases = [
            ("/status", "wrong", None, 401),
            ("/decision", "wrong", b"{}", 401),
            ("/command", server.auth_value, b"{}", 404),
            ("/decision", server.auth_value, b"{bad", 409),
        ]
        try:
            for path, token, body, expected in cases:
                request = urllib.request.Request(
                    base + path,
                    data=body,
                    headers={"Authorization": "Bearer " + token},
                )
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(request, timeout=2)
                self.assertEqual(context.exception.code, expected)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
