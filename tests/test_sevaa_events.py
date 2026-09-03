"""S01 — signed enquiry events from SEVAA into AION.  PII can never enter."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer

from tests.base import AionTest
from aion_core import db, governor, intake, reports, sevaa, tasks
from bridges import whatsapp_bridge as bridge

SECRET = "test-shared-secret-not-real"


def good_event(**over):
    e = {"type": "enquiry.created", "lead_id": 42, "score": 71, "stage": "new", "city": "Surat",
         "source": "public-quote", "requirement_summary": "20ft modular sales office",
         "created_at": "2026-09-03T21:00:00+00:00"}
    e.update(over)
    return e


class TestContract(AionTest):
    def test_forbidden_keys_are_rejected(self):
        for key in sevaa.EVENT_FORBIDDEN_KEYS:
            problems = sevaa.validate_event(good_event(**{key: "x"}))
            self.assertTrue(any("forbidden PII" in p for p in problems), key)

    def test_unknown_keys_and_bad_types_are_rejected(self):
        self.assertTrue(sevaa.validate_event(good_event(extra="x")))
        self.assertTrue(sevaa.validate_event(good_event(lead_id="42")))
        self.assertTrue(sevaa.validate_event(good_event(type="lead.won")))
        self.assertTrue(sevaa.validate_event(good_event(requirement_summary="x" * 81)))
        self.assertEqual(sevaa.validate_event(good_event()), [])

    def test_signature_roundtrip_and_constant_time_reject(self):
        body = json.dumps(good_event()).encode()
        sig = sevaa.sign(body, SECRET)
        self.assertTrue(sevaa.verify(body, sig, SECRET))
        self.assertFalse(sevaa.verify(body + b" ", sig, SECRET))
        self.assertFalse(sevaa.verify(body, sig, "other"))
        self.assertFalse(sevaa.verify(body, sig, None))
        self.assertFalse(sevaa.verify(body, None, SECRET))


class TestIntake(AionTest):
    def test_event_becomes_triage_task_and_alert(self):
        r = intake.external_event(good_event())
        self.assertEqual(r["status"], "SAVED")
        row = tasks.get(r["task_id"])
        self.assertEqual(row["status"], "TRIAGE")
        self.assertEqual(row["project"], "sevaa-sales-os")
        self.assertIn("Enquiry #42", row["title"])
        self.assertIn("Surat", row["title"])
        self.assertIn("New enquiry #42", governor.pending_alert())

    def test_replay_creates_nothing(self):
        intake.external_event(good_event())
        again = intake.external_event(good_event())
        self.assertEqual(again["status"], "DUPLICATE")
        self.assertEqual(len([t for t in tasks.by_status("TRIAGE")]), 1)

    def test_pii_event_is_refused_and_nothing_stored(self):
        with self.assertRaises(ValueError):
            intake.external_event(good_event(phone="+91 99999 11111"))
        self.assertEqual(tasks.by_status("TRIAGE"), [])
        blob = " ".join((r["detail"] or "") for r in db.connect().execute("SELECT detail FROM events"))
        self.assertNotIn("99999", blob)

    def test_status_shows_the_alert_without_contact_details(self):
        intake.external_event(good_event())
        text = reports.status()
        self.assertIn("New enquiry #42", text)
        for word in ("phone", "@", "+91"):
            self.assertNotIn(word, text)


class _Server:
    def __enter__(self):
        self.srv = HTTPServer(("127.0.0.1", 0), bridge.Handler)
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()
        return f"http://127.0.0.1:{self.srv.server_port}"

    def __exit__(self, *a):
        self.srv.shutdown()
        self.srv.server_close()


# Loopback must never go through an HTTP(S)_PROXY from the environment.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _post(url, body: bytes, sig: str | None):
    headers = {"Content-Type": "application/json"}
    if sig:
        headers[sevaa.SIGNATURE_HEADER] = sig
    req = urllib.request.Request(url + "/api/events", data=body, headers=headers, method="POST")
    try:
        with _OPENER.open(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


class TestBridgeEndpoint(AionTest):
    def setUp(self):
        super().setUp()
        import os
        os.environ[sevaa.SECRET_NAME] = SECRET

    def tearDown(self):
        import os
        os.environ.pop(sevaa.SECRET_NAME, None)
        super().tearDown()

    def test_bad_signature_is_401_and_stores_nothing(self):
        body = json.dumps(good_event()).encode()
        with _Server() as url:
            code, _ = _post(url, body, "sha256=deadbeef")
            code2, _ = _post(url, body, None)
        self.assertEqual((code, code2), (401, 401))
        self.assertEqual(tasks.by_status("TRIAGE"), [])

    def test_valid_event_then_replay(self):
        body = json.dumps(good_event()).encode()
        sig = sevaa.sign(body, SECRET)
        with _Server() as url:
            code, r1 = _post(url, body, sig)
            code2, r2 = _post(url, body, sig)
        self.assertEqual(code, 200)
        self.assertEqual(r1["status"], "SAVED")
        self.assertEqual(r2["status"], "DUPLICATE")
        self.assertEqual(len(tasks.by_status("TRIAGE")), 1)

    def test_pii_event_is_400(self):
        body = json.dumps(good_event(email="a@b.c")).encode()
        with _Server() as url:
            code, r = _post(url, body, sevaa.sign(body, SECRET))
        self.assertEqual(code, 400)
        self.assertIn("forbidden PII", r["error"])

    def test_unconfigured_secret_refuses_everything(self):
        import os
        os.environ.pop(sevaa.SECRET_NAME, None)
        body = json.dumps(good_event()).encode()
        with _Server() as url:
            code, _ = _post(url, body, sevaa.sign(body, SECRET))
        self.assertEqual(code, 503)


if __name__ == "__main__":
    unittest.main()
