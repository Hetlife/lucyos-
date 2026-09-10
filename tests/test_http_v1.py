import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aion_core import metrics
from bridges import http_server
from tests.base import AionTest


class TestHttpV1(AionTest):
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

    def request(self, path, *, token=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        req = Request(self.base + path, headers=headers, method="GET")
        with urlopen(req, timeout=2) as response:
            return response, json.loads(response.read())

    def test_v1_endpoints_return_valid_json_with_a_token(self):
        for path in http_server.V1_ROUTES:
            response, payload = self.request(path, token=self.token)
            self.assertEqual(response.status, 200, path)
            self.assertTrue(payload["ok"], path)
            self.assertIn("data", payload, path)
            # Confirms it round-tripped through real JSON, not just a dict repr.
            json.dumps(payload)

    def test_v1_endpoints_reject_missing_and_wrong_tokens(self):
        for path in http_server.V1_ROUTES:
            for value in (None, "wrong"):
                with self.assertRaises(HTTPError) as caught:
                    self.request(path, token=value)
                self.assertEqual(caught.exception.code, 401, path)

    def test_v1_money_matches_the_underlying_split(self):
        metrics.record_money("revenue", 1500, stage="ACTUAL", evidence="pay_x")
        _, payload = self.request("/api/v1/money", token=self.token)
        self.assertEqual(payload["data"]["real"]["revenue_inr"], 1500.0)

    def test_existing_text_endpoint_is_unchanged(self):
        """No regression: an old route still returns its original text shape."""
        _, payload = self.request("/api/status", token=self.token)
        self.assertTrue(payload["ok"])
        self.assertIsInstance(payload["data"], str)


if __name__ == "__main__":
    unittest.main()
