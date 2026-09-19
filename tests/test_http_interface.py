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
            if path == http_server.SCS_RESULT_PATH:
                payload = dict(payload)
                payload.setdefault("claim_id", tasks.claim_id(payload["task_id"]))
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

    def _scs_claim(self, title="handoff task"):
        task_id = tasks.create(title, model_class="DET")
        _, body = self.request(http_server.SCS_TASK_PATH, token=self.token)
        self.assertEqual(body["data"]["task_id"], task_id)
        return task_id, body["data"]

    @staticmethod
    def _scs_packet(claim, key, status="DONE", **updates):
        packet = {
            "task_id": claim["task_id"],
            "claim_id": claim["claim_id"],
            "idempotency_key": key,
            "STATUS": status,
            "ACTIONS": "worker claims bounded work completed",
            "FILES_CHANGED": "artifact.txt",
            "TESTS": "focused validation exited 0",
            "RESULTS": "artifact measurement matched",
            "BLOCKERS": "",
            "NEXT_ACTION": "independent review",
        }
        packet.update(updates)
        return packet

    def test_scs_handoff_is_off_by_default(self):
        task_id = tasks.create("stay ready while handoff disabled")
        with self.assertRaises(HTTPError) as caught:
            self.request(http_server.SCS_TASK_PATH, token=self.token)
        self.assertEqual(caught.exception.code, 404)
        packet = {field: "" for field in http_server.SCS_RESULT_FIELDS}
        with self.assertRaises(HTTPError) as caught:
            self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)
        self.assertEqual(caught.exception.code, 404)
        self.assertEqual(tasks.get(task_id)["status"], "READY")

    def test_scs_duplicate_claim_and_delivery_do_not_repeat_work_or_events(self):
        secret_task = tasks.create("secret task", data_class="SECRET")
        task_id = tasks.create("safe local task", model_class="DET")
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            def fetch():
                return self.request(http_server.SCS_TASK_PATH, token=self.token)[1]["data"]
            with ThreadPoolExecutor(max_workers=4) as pool:
                claims = list(pool.map(lambda _: fetch(), range(4)))
            claimed = [item for item in claims if item is not None]
            self.assertEqual(len(claimed), 1, claims)
            claim = claimed[0]
            self.assertEqual(claim["task_id"], task_id)
            self.assertEqual(claim["owner_agent"], "scs-admin01")
            self.assertEqual(set(claim), set(http_server.SCS_TASK_FIELDS))
            packet = self._scs_packet(claim, "delivery-1")
            first = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)[1]
            replay = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)[1]
        self.assertFalse(first["data"]["replayed"])
        self.assertTrue(replay["data"]["replayed"])
        self.assertEqual(tasks.get(task_id)["status"], "NEEDS_REVIEW")
        self.assertEqual(tasks.get(secret_task)["status"], "READY")
        counts = dict(db.connect().execute(
            "SELECT kind,COUNT(*) FROM events WHERE subject=? GROUP BY kind", (task_id,)).fetchall())
        self.assertEqual(counts["task.claim"], 1)
        self.assertEqual(counts["task.worker_result"], 1)
        self.assertEqual(counts["task.evidence"], 1)

    def test_scs_heartbeat_is_contact_without_evidence(self):
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            task_id, claim = self._scs_claim("heartbeat only")
            before = tasks.get(task_id)["updated_at"]
            packet = self._scs_packet(
                claim, "heartbeat-1", "HEARTBEAT", ACTIONS="", FILES_CHANGED="",
                TESTS="", RESULTS="", BLOCKERS="", NEXT_ACTION="")
            body = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)[1]
        row = tasks.get(task_id)
        self.assertEqual(body["data"]["status"], "CLAIMED")
        self.assertEqual(row["status"], "CLAIMED")
        self.assertGreaterEqual(row["updated_at"], before)
        self.assertEqual(row["evidence"], "")
        count = db.connect().execute(
            "SELECT COUNT(*) FROM events WHERE subject=? AND kind='task.evidence'", (task_id,)).fetchone()[0]
        self.assertEqual(count, 0)

    def test_scs_meaningful_validation_uses_existing_evidence_api(self):
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            task_id, claim = self._scs_claim("measured progress")
            packet = self._scs_packet(claim, "progress-1", "PROGRESS")
            body = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)[1]
        self.assertEqual(body["data"]["status"], "CLAIMED")
        self.assertIn("focused validation exited 0", tasks.get(task_id)["evidence"])
        detail = db.connect().execute(
            "SELECT detail FROM events WHERE subject=? AND kind='task.evidence'", (task_id,)).fetchone()[0]
        self.assertEqual(json.loads(detail)["kind"], "validation")
        self.assertNotIn(packet["ACTIONS"], tasks.get(task_id)["evidence"])

    def test_scs_done_is_a_review_claim_and_never_closes_task(self):
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            task_id, claim = self._scs_claim("claimed complete")
            packet = self._scs_packet(claim, "done-claim")
            body = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)[1]
        self.assertEqual(body["data"]["status"], "NEEDS_REVIEW")
        row = tasks.get(task_id)
        self.assertEqual(row["status"], "NEEDS_REVIEW")
        self.assertIsNone(row["completed_at"])
        self.assertNotEqual(row["status"], "DONE")

    def test_scs_failed_uses_deterministic_failure_recovery(self):
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            task_id, claim = self._scs_claim("schema failure")
            packet = self._scs_packet(
                claim, "failure-1", "FAILED", TESTS="", FILES_CHANGED="",
                RESULTS="provider schema validation error", BLOCKERS="invalid schema")
            body = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)[1]
        row = tasks.get(task_id)
        self.assertEqual(body["data"]["status"], "NEEDS_REVIEW")
        self.assertEqual(row["status"], "NEEDS_REVIEW")
        self.assertEqual(row["retry_count"], 0)
        self.assertIn("PROVIDER_SCHEMA_ERROR", row["blockers"])

    def test_scs_replay_conflict_and_old_claim_are_rejected(self):
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            task_id, first_claim = self._scs_claim("retry fence")
            failed = self._scs_packet(
                first_claim, "attempt-1", "FAILED", TESTS="", FILES_CHANGED="",
                RESULTS="worker process died", BLOCKERS="")
            self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=failed)
            self.assertEqual(tasks.get(task_id)["status"], "READY")
            _, second_claim = self.request(http_server.SCS_TASK_PATH, token=self.token)
            second_claim = second_claim["data"]
            self.assertNotEqual(first_claim["claim_id"], second_claim["claim_id"])
            stale = self._scs_packet(first_claim, "stale-attempt")
            with self.assertRaises(HTTPError) as caught:
                self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=stale)
            self.assertEqual(caught.exception.code, 409)
            replay = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=failed)[1]
            self.assertTrue(replay["data"]["replayed"])
            conflict = dict(failed, RESULTS="different failure")
            with self.assertRaises(HTTPError) as caught:
                self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=conflict)
        self.assertEqual(caught.exception.code, 409)
        self.assertEqual(tasks.get(task_id)["retry_count"], 1)
        self.assertEqual(tasks.get(task_id)["owner_agent"], "scs-admin01")

    def test_scs_result_return_failure_retries_saved_receipt(self):
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            task_id, claim = self._scs_claim("lost response")
            packet = self._scs_packet(claim, "lost-return")
            original = self.server.RequestHandlerClass._json
            def lose_success(handler, code, payload):
                if code == 200 and payload.get("data", {}).get("task_id") == task_id:
                    raise ConnectionResetError("client disappeared")
                return original(handler, code, payload)
            with mock.patch.object(self.server.RequestHandlerClass, "_json", lose_success):
                with self.assertRaises(Exception):
                    self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)
            replay = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)[1]
        self.assertTrue(replay["data"]["replayed"])
        self.assertEqual(tasks.get(task_id)["status"], "NEEDS_REVIEW")
        count = db.connect().execute(
            "SELECT COUNT(*) FROM events WHERE subject=? AND kind='task.worker_result'", (task_id,)).fetchone()[0]
        self.assertEqual(count, 1)

    def test_scs_auth_and_redaction_cover_claims_receipts_and_events(self):
        with mock.patch.dict(os.environ, {"AION_SCS_HANDOFF_ENABLED": "1"}, clear=False):
            for token in (None, "wrong"):
                with self.assertRaises(HTTPError) as caught:
                    self.request(http_server.SCS_TASK_PATH, token=token)
                self.assertEqual(caught.exception.code, 401)
            task_id, claim = self._scs_claim("redacted result")
            packet = self._scs_packet(
                claim, "redacted-1", RESULTS="token=ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345")
            body = self.request(http_server.SCS_RESULT_PATH, token=self.token, payload=packet)[1]
        self.assertNotIn("ghp_AbCdEf", json.dumps(body))
        self.assertNotIn("ghp_AbCdEf", tasks.get(task_id)["evidence"])
        stored = "\n".join(row[0] for row in db.connect().execute(
            "SELECT result FROM idempotency WHERE scope=? UNION ALL SELECT detail FROM events WHERE subject=?",
            (http_server.SCS_IDEMPOTENCY_SCOPE, task_id)).fetchall())
        self.assertNotIn("ghp_AbCdEf", stored)
        key = db.connect().execute(
            "SELECT key FROM idempotency WHERE scope=?", (http_server.SCS_IDEMPOTENCY_SCOPE,)).fetchone()[0]
        self.assertNotIn("redacted-1", key)

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
