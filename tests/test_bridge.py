import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer

from tests.base import AionTest
from aion_core import approvals, config, tasks, util
from bridges import whatsapp_bridge as bridge


class TestBridge(AionTest):
    def test_reply_is_redacted(self):
        tasks.create("rotate ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        self.assertNotIn("ghp_AbCdEf", bridge.reply_to("tasks"))

    def test_oversized_message_is_refused(self):
        self.assertIn("too long", bridge.reply_to("x" * 5000))

    def test_file_adapter_round_trip(self):
        inbox = config.home() / "INBOX" / "whatsapp"
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / "msg1.txt").write_text("status", encoding="utf-8")
        bridge.run_file(once=True)
        out = config.home() / "OUTBOX" / "whatsapp" / "msg1.reply.txt"
        self.assertTrue(out.exists())
        self.assertIn("AION STATUS", out.read_text())
        self.assertFalse((inbox / "msg1.txt").exists())

    def test_file_adapter_ignores_a_redelivered_message(self):
        inbox = config.home() / "INBOX" / "whatsapp"
        inbox.mkdir(parents=True, exist_ok=True)
        a = approvals.create("spend money")
        (inbox / "m.txt").write_text(f"APPROVE {a}", encoding="utf-8")
        bridge.run_file(once=True)
        first = (config.home() / "OUTBOX" / "whatsapp" / "m.reply.txt").read_text()
        self.assertIn(a, first)
        # Same file name and body delivered again must not be reprocessed.
        (inbox / "m.txt").write_text(f"APPROVE {a}", encoding="utf-8")
        bridge.run_file(once=True)
        self.assertFalse((inbox / "m.txt").exists())

    def test_router_crash_becomes_a_logged_error_not_a_dead_channel(self):
        original = bridge.router.handle
        bridge.router.handle = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            reply = bridge.reply_to("status")
        finally:
            bridge.router.handle = original
        self.assertIn("logged", reply)
        from aion_core import errors
        self.assertTrue(errors.open_errors())


if __name__ == "__main__":
    unittest.main()


class TestPhoneApi(AionTest):
    def setUp(self):
        super().setUp()
        bridge.Handler.phone_token = "phone-test-token-not-real"

    def tearDown(self):
        bridge.Handler.phone_token = ""
        super().tearDown()

    def _server(self):
        return _PhoneServer()

    def test_unauthenticated_get_is_refused(self):
        with self._server() as url:
            code, _ = _get(url, "/api/status", token=None)
        self.assertEqual(code, 401)

    def test_wrong_token_is_refused(self):
        with self._server() as url:
            code, _ = _get(url, "/api/status", token="not-the-real-token")
        self.assertEqual(code, 401)

    def test_authenticated_status_returns_dashboard(self):
        with self._server() as url:
            code, body = _get(url, "/api/status", token="phone-test-token-not-real")
        self.assertEqual(code, 200)
        self.assertIn("money", body)
        self.assertIn("needs_you", body)

    def test_tasks_money_blockers_errors_agents_report_all_respond(self):
        with self._server() as url:
            for path in ("/api/tasks", "/api/money", "/api/blockers", "/api/errors",
                        "/api/agents", "/api/report"):
                code, _ = _get(url, path, token="phone-test-token-not-real")
                self.assertEqual(code, 200, path)

    def test_command_routes_through_the_same_router_as_whatsapp(self):
        with self._server() as url:
            code, body = _post_json(url, "/api/command", {"message": "status"},
                                    token="phone-test-token-not-real")
        self.assertEqual(code, 200)
        self.assertIn("AION STATUS", body["reply"])

    def test_capture_creates_a_task(self):
        with self._server() as url:
            code, body = _post_json(url, "/api/capture", {"text": "phone idea", "kind": "idea"},
                                    token="phone-test-token-not-real")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "SAVED")

    def test_capture_refuses_a_credential(self):
        with self._server() as url:
            code, body = _post_json(
                url, "/api/capture",
                {"text": "key is ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345", "kind": "note"},
                token="phone-test-token-not-real")
        self.assertEqual(code, 400)

    def test_feedback_moves_a_task(self):
        from aion_core import tasks
        t = tasks.create("decide this", status="NEEDS_REVIEW")
        with self._server() as url:
            code, body = _post_json(url, "/api/feedback", {"task_id": t, "choice": "yes"},
                                    token="phone-test-token-not-real")
        self.assertEqual(code, 200)
        self.assertEqual(tasks.get(t)["status"], "READY")

    def test_phone_page_is_served_without_auth(self):
        with self._server() as url:
            code, _ = _get(url, "/app", token=None, expect_json=False)
        self.assertEqual(code, 200)

    def test_events_endpoint_still_works_alongside_phone_routes(self):
        # Regression: adding phone routes must not break S01's existing path.
        with self._server() as url:
            code, _ = _get(url, "/", token=None, expect_json=False)
        self.assertEqual(code, 200)


class _PhoneServer:
    def __enter__(self):
        self.srv = HTTPServer(("127.0.0.1", 0), bridge.Handler)
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()
        return f"http://127.0.0.1:{self.srv.server_port}"

    def __exit__(self, *a):
        self.srv.shutdown()
        self.srv.server_close()


def _get(url, path, token=None, expect_json=True):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url + path, headers=headers, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=5) as r:
            body = r.read()
            return r.status, (json.loads(body) if expect_json else body.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read()
        return e.code, (json.loads(body) if body and expect_json else {})


def _post_json(url, path, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url + path, data=body, headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        return e.code, (json.loads(body) if body else {})
