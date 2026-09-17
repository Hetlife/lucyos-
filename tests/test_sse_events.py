import json
import threading
from urllib.request import Request, urlopen

from aion_core import db
from bridges import http_server
from tests.base import AionTest


class TestSSEEvents(AionTest):
    def setUp(self):
        super().setUp()
        self.auth_value = "test-interface-value"
        self.server = http_server.build_server("127.0.0.1", 0, token=self.auth_value)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
        super().tearDown()

    def _get(self, path):
        req = Request(self.base + path, headers={"Authorization": f"Bearer {self.auth_value}"})
        return urlopen(req, timeout=3)

    def test_event_json_and_one_shot_sse_use_existing_event_bus(self):
        db.log_event("test", "skill.progress", "S-1", "sandbox passed")
        with self._get("/api/v1/events?after=0&limit=20") as r:
            payload = json.loads(r.read())
        self.assertTrue(payload["ok"])
        self.assertTrue(any(e["kind"] == "skill.progress" for e in payload["data"]))
        with self._get("/api/v1/events/stream?after=0&once=1") as r:
            body = r.read().decode("utf-8")
            self.assertEqual(r.headers["Content-Type"], "text/event-stream; charset=utf-8")
        self.assertIn("event: lucyos", body)
        self.assertIn("skill.progress", body)
