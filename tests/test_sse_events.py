import json
import threading
from urllib.request import Request, urlopen

from aion_core import api, approvals, db, tasks
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

    def test_live_activity_is_canonical_and_token_free(self):
        task_id = tasks.create("background proof", status="READY", model_class="DET")
        snap = api.live_activity()
        self.assertEqual(snap["source"], "canonical-sqlite")
        self.assertEqual(snap["ai_calls"], 0)
        self.assertEqual(snap["mode"], "ready")
        self.assertTrue(any(row["task_id"] == task_id for row in snap["ready"]))

    def test_live_activity_surfaces_owner_approval(self):
        task_id = tasks.create("owner gate", status="BLOCKED", blockers="OWNER_APPROVAL_REQUIRED")
        approvals.create("approve test", why="owner boundary", cost="zero", max_downside="none", reversibility="yes", resumes="resume", task_id=task_id)
        snap = api.live_activity()
        self.assertTrue(snap["warning"])
        self.assertTrue(snap["needs_owner"])
        self.assertEqual(snap["mode"], "needs-you")

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
