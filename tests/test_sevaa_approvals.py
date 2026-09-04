"""S02 — SEVAA proposal approvals become AION WhatsApp cards; APPROVE/DENY
calls the SEVAA decision API with the founder token.

The founder token is the one truly consequential credential in this whole
integration. Every test here checks not just that the feature works, but that
the token and the lead's identity never leak anywhere they should not.
"""
import json
import unittest
import urllib.error

from tests.base import AionTest
from aion_core import approvals, bootstrap, db, resume, router, sevaa

AUTOMATION_TOKEN = "automation-approvals-test"
FOUNDER_TOKEN = "founder-secret-token-not-real"


class _FakeResponse:
    def __init__(self, body):
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(body=None, exc=None, capture=None):
    def factory(*a, **k):
        class _Opener:
            def open(self, req, timeout=5.0):
                if capture is not None:
                    capture.append({"url": req.full_url, "method": req.get_method(),
                                    "headers": dict(req.headers),
                                    "body": req.data.decode("utf-8") if req.data else None})
                if exc:
                    raise exc
                return _FakeResponse(body)
        return _Opener()
    return factory


class TestSyncPendingApprovals(AionTest):
    def setUp(self):
        super().setUp()
        bootstrap.set_secret(sevaa.AUTOMATION_TOKEN_NAME, AUTOMATION_TOKEN)
        bootstrap.set_secret(sevaa.FOUNDER_TOKEN_NAME, FOUNDER_TOKEN)
        sevaa._cache.update(at=0.0, brief=None, error=None)

    def _mock_pending(self, rows):
        import urllib.request
        urllib.request.build_opener = _opener(body=rows)

    def test_pending_proposal_becomes_a_card(self):
        self._mock_pending([
            {"id": 5, "object_type": "proposal", "object_id": 5, "status": "pending",
             "amount": 25000, "scope_summary": "20ft modular office, delivery in 30 days",
             "lead_name": "Real Buyer", "lead_company": "Real Buyer Co"},
        ])
        out = resume.boot()
        step = next(s for s in out["steps"] if s["step"] == "sevaa_approvals")
        self.assertIn("1 new card", step["detail"])
        card = approvals.pending()[0]
        self.assertEqual(card["external_ref"], "sevaa:approval:5")
        self.assertIn("25000", card["cost"])
        self.assertNotIn("Real Buyer", card["action"])
        self.assertNotIn("Real Buyer Co", card["why"])

    def test_resync_does_not_duplicate_the_card(self):
        rows = [{"id": 7, "amount": 1000, "scope_summary": "x"}]
        self._mock_pending(rows)
        resume.boot()
        self._mock_pending(rows)
        resume.boot()
        matching = [a for a in db.connect().execute(
            "SELECT * FROM approvals WHERE external_ref='sevaa:approval:7'")]
        self.assertEqual(len(matching), 1)


class TestApproveDenyRoundTrip(AionTest):
    def setUp(self):
        super().setUp()
        # Only the founder token: status()/today() would otherwise also poll
        # SEVAA's daily-brief through the same mocked opener and pollute the
        # call count these tests check.
        bootstrap.set_secret(sevaa.FOUNDER_TOKEN_NAME, FOUNDER_TOKEN)

    def _card(self):
        return approvals.create("Approve SEVAA proposal — test", cost="₹5000",
                                resumes="proceeds in SEVAA", external_ref="sevaa:approval:42")

    def test_approve_calls_sevaa_with_the_founder_token_and_updates_local_state(self):
        captured = []
        import urllib.request
        urllib.request.build_opener = _opener(
            body={"id": 42, "status": "approved"}, capture=captured)
        aid = self._card()
        result = router.handle(f"APPROVE {aid}")
        self.assertIn(aid, result)
        self.assertEqual(approvals.get(aid)["status"], "APPROVED")
        self.assertEqual(len(captured), 1)
        call = captured[0]
        self.assertEqual(call["method"], "POST")
        self.assertIn("/api/v2/approvals/42/decision", call["url"])
        self.assertEqual(call["headers"]["Authorization"], f"Bearer {FOUNDER_TOKEN}")
        self.assertEqual(json.loads(call["body"])["decision"], "approved")

    def test_deny_sends_rejected(self):
        captured = []
        import urllib.request
        urllib.request.build_opener = _opener(
            body={"id": 42, "status": "rejected"}, capture=captured)
        aid = self._card()
        router.handle(f"DENY {aid}")
        self.assertEqual(json.loads(captured[0]["body"])["decision"], "rejected")
        self.assertEqual(approvals.get(aid)["status"], "DENIED")

    def test_replay_hits_sevaa_exactly_once(self):
        captured = []
        import urllib.request
        urllib.request.build_opener = _opener(
            body={"id": 42, "status": "approved"}, capture=captured)
        aid = self._card()
        router.handle(f"APPROVE {aid}")
        router.handle(f"APPROVE {aid}")
        router.handle(f"APPROVE {aid}")
        self.assertEqual(len(captured), 1)

    def test_non_2xx_keeps_the_card_pending(self):
        import urllib.request
        urllib.request.build_opener = _opener(
            exc=urllib.error.HTTPError("url", 409, "already resolved", None, None))
        aid = self._card()
        reply = router.handle(f"APPROVE {aid}")
        self.assertEqual(approvals.get(aid)["status"], "PENDING")
        self.assertIn("PENDING", reply)

    def test_unreachable_sevaa_keeps_the_card_pending_and_a_retry_can_still_succeed(self):
        import urllib.request
        urllib.request.build_opener = _opener(exc=urllib.error.URLError("refused"))
        aid = self._card()
        router.handle(f"APPROVE {aid}")
        self.assertEqual(approvals.get(aid)["status"], "PENDING")

        captured = []
        urllib.request.build_opener = _opener(body={"id": 42, "status": "approved"}, capture=captured)
        router.handle(f"APPROVE {aid}")
        self.assertEqual(approvals.get(aid)["status"], "APPROVED")
        self.assertEqual(len(captured), 1)

    def test_ordinary_aion_approvals_never_call_sevaa(self):
        captured = []
        import urllib.request
        urllib.request.build_opener = _opener(body={}, capture=captured)
        aid = approvals.create("buy hosting")  # no external_ref
        router.handle(f"APPROVE {aid}")
        self.assertEqual(captured, [])
        self.assertEqual(approvals.get(aid)["status"], "APPROVED")

    def test_founder_token_never_appears_in_any_log_or_reply(self):
        import urllib.request
        urllib.request.build_opener = _opener(body={"id": 42, "status": "approved"})
        aid = self._card()
        reply = router.handle(f"APPROVE {aid}")
        self.assertNotIn(FOUNDER_TOKEN, reply)
        blob = " ".join((r["detail"] or "") + (r["subject"] or "") for r in
                        db.connect().execute("SELECT detail, subject FROM events"))
        self.assertNotIn(FOUNDER_TOKEN, blob)

    def test_forged_decision_value_is_rejected_before_any_network_call(self):
        captured = []
        import urllib.request
        urllib.request.build_opener = _opener(body={}, capture=captured)
        with self.assertRaises(sevaa.SevaaError):
            sevaa.decide_approval(42, "banana")
        self.assertEqual(captured, [])


if __name__ == "__main__":
    unittest.main()
