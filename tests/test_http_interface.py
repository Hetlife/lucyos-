import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aion_core import approvals, bootstrap, tasks
from bridges import http_server
from tests.base import AionTest


class TestPhoneInterface(AionTest):
    def setUp(self):
        super().setUp()
        self.token = "test-interface-value"
        self.server = http_server.build_server("127.0.0.1", 0, token=self.token)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        super().tearDown()

    def request(self, path, *, token=None, payload=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, data=data, headers=headers,
                      method="POST" if payload is not None else "GET")
        with urlopen(req, timeout=2) as response:
            return response, json.loads(response.read()) if path.startswith("/api/") else response.read()

    def test_api_rejects_missing_and_wrong_bearer_tokens(self):
        for value in (None, "wrong"):
            with self.assertRaises(HTTPError) as caught:
                self.request("/api/status", token=value)
            self.assertEqual(caught.exception.code, 401)

    def test_every_read_endpoint_is_authenticated_and_redacted(self):
        tasks.create("rotate ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        for path in http_server.API_COMMANDS:
            response, payload = self.request(path, token=self.token)
            self.assertEqual(response.status, 200, path)
            self.assertTrue(payload["ok"], path)
            self.assertNotIn("ghp_AbCdEf", json.dumps(payload), path)
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_approval_round_trip_uses_the_shared_router(self):
        task_id = tasks.create("await interface approval")
        approval_id = approvals.create("continue prepared action", task_id=task_id,
                                       resumes="run validated step")
        _, listing = self.request("/api/approvals", token=self.token)
        self.assertEqual(listing["data"][0]["approval_id"], approval_id)
        _, blockers = self.request("/api/blockers", token=self.token)
        self.assertIn(approval_id, blockers["data"])
        _, result = self.request("/api/command", token=self.token,
                                 payload={"message": f"APPROVE {approval_id}"})
        self.assertIn("approved", result["data"])
        self.assertEqual(approvals.get(approval_id)["status"], "APPROVED")
        self.assertEqual(tasks.get(task_id)["status"], "READY")

    def test_public_app_shell_has_strict_security_headers(self):
        response, body = self.request("/")
        self.assertIn(b"AION Control", body)
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_token_loads_from_protected_secret_store(self):
        bootstrap.set_secret("AION_INTERFACE_TOKEN", "stored-test-value")
        self.assertEqual(http_server.read_secret(), "stored-test-value")


if __name__ == "__main__":
    unittest.main()
