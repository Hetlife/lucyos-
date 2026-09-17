import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aion_core import approvals, bootstrap, db, tasks
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

    def test_scs_handoff_is_off_by_default(self):
        task_id = tasks.create("stay ready while handoff disabled")
        with self.assertRaises(HTTPError) as caught:
            self.request(http_server.SCS_TASK_PATH, token=self.token)
        self.assertEqual(caught.exception.code, 404)
        self.assertEqual(tasks.get(task_id)["status"], "READY")

    def test_scs_get_claims_atomically_and_exposes_only_allowlisted_fields(self):
        secret_task = tasks.create("secret task", data_class="SECRET")
        task_id = tasks.create(
            "safe local task",
            description="bounded work",
            success_criteria="verified output",
            validation_method="unit test",
            next_action="execute",
            model_class="B",
            data_class="INTERNAL",
        )
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            def fetch():
                _, payload = self.request(http_server.SCS_TASK_PATH, token=self.token)
                return payload["data"]
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: fetch(), range(4)))
        claimed = [item for item in results if item is not None]
        self.assertEqual(len(claimed), 1, results)
        self.assertEqual(claimed[0]["task_id"], task_id)
        self.assertEqual(set(claimed[0]), set(http_server.SCS_TASK_FIELDS))
        self.assertEqual(tasks.get(task_id)["status"], "CLAIMED")
        self.assertEqual(tasks.get(task_id)["owner_agent"], "scs-admin01")
        self.assertEqual(tasks.get(secret_task)["status"], "READY")

    def test_scs_claim_respects_pause_and_safe_mode(self):
        task_id = tasks.create("paid handoff task", model_class="B")
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            db.set_meta("paused", "1")
            _, paused = self.request(http_server.SCS_TASK_PATH, token=self.token)
            self.assertIsNone(paused["data"])
            self.assertEqual(tasks.get(task_id)["status"], "READY")
            db.set_meta("paused", "0")
            db.set_meta("safe_mode", "1")
            _, safe = self.request(http_server.SCS_TASK_PATH, token=self.token)
            self.assertIsNone(safe["data"])
            self.assertEqual(tasks.get(task_id)["status"], "READY")

    def test_scs_claim_respects_model_authority_and_budget_governor(self):
        c_task = tasks.create("class c", model_class="C")
        d_task = tasks.create("class d", model_class="D")
        b_task = tasks.create("class b", model_class="B")
        budget = {
            "day_over": False,
            "month_over": False,
            "governor": "RESERVE",
        }
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False),              mock.patch("bridges.http_server.governor.state", return_value="RESERVE"),              mock.patch("bridges.http_server.metrics.budget_status", return_value=budget):
            _, held = self.request(http_server.SCS_TASK_PATH, token=self.token)
        self.assertIsNone(held["data"])
        for task_id in (c_task, d_task, b_task):
            self.assertEqual(tasks.get(task_id)["status"], "READY")

        a_task = tasks.create("class a", model_class="A")
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False),              mock.patch("bridges.http_server.governor.state", return_value="RESERVE"),              mock.patch("bridges.http_server.metrics.budget_status", return_value=budget):
            _, allowed = self.request(http_server.SCS_TASK_PATH, token=self.token)
        self.assertEqual(allowed["data"]["task_id"], a_task)
        self.assertEqual(tasks.get(c_task)["status"], "READY")
        self.assertEqual(tasks.get(d_task)["status"], "READY")
        self.assertEqual(tasks.get(b_task)["status"], "READY")

    def test_scs_result_is_replay_safe_conflict_safe_and_redacted(self):
        task_id = tasks.create("handoff result")
        packet = {
            "task_id": task_id,
            "idempotency_key": "result-001",
            "STATUS": "DONE",
            "ACTIONS": "implemented adapter",
            "FILES_CHANGED": "bridges/http_server.py",
            "TESTS": "focused tests passed",
            "RESULTS": "verified ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345",
            "BLOCKERS": "",
            "NEXT_ACTION": "continue",
        }
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            self.request(http_server.SCS_TASK_PATH, token=self.token)
            _, first = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)
            _, replay = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)
            conflict = dict(packet)
            conflict["RESULTS"] = "different result"
            with self.assertRaises(HTTPError) as caught:
                self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=conflict)
        self.assertEqual(caught.exception.code, 409)
        self.assertFalse(first["data"]["replayed"])
        self.assertTrue(replay["data"]["replayed"])
        row = tasks.get(task_id)
        self.assertEqual(row["status"], "DONE")
        self.assertNotIn("ghp_AbCdEf", row["evidence"])
        stored_row = db.connect().execute(
            "SELECT key,result FROM idempotency WHERE scope=?",
            (http_server.SCS_IDEMPOTENCY_SCOPE,),
        ).fetchone()
        self.assertNotIn("result-001", stored_row["key"])
        self.assertNotIn("ghp_AbCdEf", stored_row["result"])

    def test_scs_post_commit_failure_keeps_idempotency_pending(self):
        from aion_core import resume

        task_id = tasks.create("post-commit failure")
        packet = {
            "task_id": task_id,
            "idempotency_key": "result-post-commit",
            "STATUS": "DONE",
            "ACTIONS": "completed bounded work",
            "FILES_CHANGED": "artifact.txt",
            "TESTS": "validation passed",
            "RESULTS": "artifact verified",
            "BLOCKERS": "",
            "NEXT_ACTION": "continue",
        }
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            self.request(http_server.SCS_TASK_PATH, token=self.token)
            with mock.patch.object(resume, "checkpoint", side_effect=RuntimeError("checkpoint unavailable")):
                with self.assertRaises(HTTPError) as caught:
                    self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)
            self.assertEqual(caught.exception.code, 500)
            self.assertEqual(tasks.get(task_id)["status"], "DONE")
            pending = db.connect().execute(
                "SELECT key,result FROM idempotency WHERE scope=?",
                (http_server.SCS_IDEMPOTENCY_SCOPE,),
            ).fetchone()
            self.assertIsNotNone(pending)
            self.assertNotIn("result-post-commit", pending["key"])
            self.assertEqual(json.loads(pending["result"])["state"], "pending")
            with self.assertRaises(HTTPError) as retry:
                self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)
        self.assertEqual(retry.exception.code, 409)

    def test_scs_done_requires_evidence_and_non_done_stays_non_done(self):
        task_id = tasks.create("handoff evidence gate")
        base = {
            "task_id": task_id,
            "idempotency_key": "result-002",
            "STATUS": "DONE",
            "ACTIONS": "attempted",
            "FILES_CHANGED": "",
            "TESTS": "",
            "RESULTS": "result exists",
            "BLOCKERS": "",
            "NEXT_ACTION": "",
        }
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            self.request(http_server.SCS_TASK_PATH, token=self.token)
            with self.assertRaises(HTTPError) as caught:
                self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=base)
            self.assertEqual(caught.exception.code, 400)
            self.assertEqual(tasks.get(task_id)["status"], "CLAIMED")
            review = dict(base)
            review["idempotency_key"] = "result-003"
            review["STATUS"] = "NEEDS_REVIEW"
            review["BLOCKERS"] = "human review needed"
            _, payload = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=review)
        self.assertEqual(payload["data"]["status"], "NEEDS_REVIEW")
        self.assertEqual(tasks.get(task_id)["status"], "NEEDS_REVIEW")
        self.assertNotEqual(tasks.get(task_id)["status"], "DONE")

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
