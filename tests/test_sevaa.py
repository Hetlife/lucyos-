"""S07 — SEVAA daily-brief figures inside AION status/today.

Only counts ever cross the boundary; no lead identity, no token, ever leaks
into a report.
"""
import json
import unittest
import urllib.error

from tests.base import AionTest
from aion_core import bootstrap, reports, sevaa

TOKEN = "automation-test-token-not-real"


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TestSevaaBrief(AionTest):
    def setUp(self):
        super().setUp()
        bootstrap.set_secret(sevaa.AUTOMATION_TOKEN_NAME, TOKEN)
        sevaa._cache.update(at=0.0, brief=None, error=None)

    def _mock_open(self, body=None, exc=None):
        def opener_factory(*a, **k):
            class _Opener:
                def open(self, req, timeout=5.0):
                    if exc:
                        raise exc
                    self.last_headers = dict(req.headers)
                    return _FakeResponse(body)
            return _Opener()
        return opener_factory

    def test_no_token_is_a_quiet_not_configured_state(self):
        # Fresh brain: undo the setUp token to test the truly unconfigured case.
        import os
        from aion_core import config
        (config.secrets_file()).write_text("")
        os.environ.pop(sevaa.AUTOMATION_TOKEN_NAME, None)
        brief = sevaa.daily_brief(force=True)
        self.assertFalse(brief["ok"])
        self.assertIn("status" if False else sevaa.AUTOMATION_TOKEN_NAME, brief["error"])
        # And status() must not mention SEVAA at all when it was never configured.
        self.assertNotIn("SEVAA", reports.status())

    def test_successful_brief_surfaces_only_counts(self):
        body = {"new_leads": 3, "proposals_awaiting_approval": 2, "overdue_followups": 1,
                "actor": {"role": "automation"}}
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_open(body=body)
        try:
            brief = sevaa.daily_brief(force=True)
        finally:
            urllib.request.build_opener = original
        self.assertTrue(brief["ok"])
        self.assertEqual(brief["new_leads"], 3)
        self.assertEqual(brief["proposals_awaiting_approval"], 2)
        self.assertEqual(brief["overdue_followups"], 1)
        self.assertNotIn("lead_name", brief)
        self.assertNotIn("actor", brief)

    def test_status_line_reflects_counts(self):
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_open(
            body={"new_leads": 5, "proposals_awaiting_approval": 0, "overdue_followups": 2})
        try:
            line = sevaa.status_line()
        finally:
            urllib.request.build_opener = original
        self.assertEqual(line, "SEVAA: 5 new enquiries, 0 approvals pending, 2 follow-ups overdue")

    def test_unreachable_is_never_silently_omitted(self):
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_open(exc=urllib.error.URLError("refused"))
        try:
            line = sevaa.status_line()
        finally:
            urllib.request.build_opener = original
        self.assertIn("SEVAA: unreachable", line)

    def test_status_includes_the_line_once_configured(self):
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_open(
            body={"new_leads": 1, "proposals_awaiting_approval": 0, "overdue_followups": 0})
        try:
            text = reports.status()
        finally:
            urllib.request.build_opener = original
        self.assertIn("SEVAA: 1 new enquiries", text)

    def test_result_is_cached_within_the_window(self):
        import urllib.request
        original = urllib.request.build_opener
        calls = {"n": 0}

        def counting_opener(*a, **k):
            calls["n"] += 1
            return self._mock_open(body={"new_leads": 0, "proposals_awaiting_approval": 0,
                                         "overdue_followups": 0})()
        urllib.request.build_opener = counting_opener
        try:
            sevaa.daily_brief()
            sevaa.daily_brief()
        finally:
            urllib.request.build_opener = original
        self.assertEqual(calls["n"], 1)

    def test_token_never_appears_in_any_report_or_log(self):
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_open(
            body={"new_leads": 1, "proposals_awaiting_approval": 0, "overdue_followups": 0})
        try:
            text = reports.status() + reports.today() + reports.full_report()
        finally:
            urllib.request.build_opener = original
        self.assertNotIn(TOKEN, text)
        from aion_core import db
        blob = " ".join((r["detail"] or "") + (r["subject"] or "") for r in
                        db.connect().execute("SELECT detail, subject FROM events"))
        self.assertNotIn(TOKEN, blob)


if __name__ == "__main__":
    unittest.main()


class TestPaymentReconciliation(AionTest):
    def setUp(self):
        super().setUp()
        bootstrap.set_secret(sevaa.AUTOMATION_TOKEN_NAME, TOKEN)
        sevaa._cache.update(at=0.0, brief=None, error=None)

    def _mock_links(self, rows):
        def opener_factory(*a, **k):
            class _Opener:
                def open(self, req, timeout=5.0):
                    return _FakeResponse(rows)
            return _Opener()
        return opener_factory

    def test_paid_link_becomes_actual_revenue(self):
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_links([
            {"id": 9, "provider": "razorpay", "provider_payment_id": "pay_ABC123",
             "provider_payment_link_id": "plink_XYZ", "paid_amount": 15000, "status": "paid",
             "lead_name": "Real Buyer", "lead_company": "Real Co"},
        ])
        try:
            result = sevaa.reconcile_payments()
        finally:
            urllib.request.build_opener = original
        self.assertTrue(result["ok"])
        self.assertEqual(result["recorded"], [{"link_id": 9, "amount_inr": 15000}])
        from aion_core import metrics, milestones
        self.assertEqual(metrics.money()["real_revenue_inr"], 15000.0)
        self.assertTrue(milestones.check()["M0"]["reached"])

    def test_non_paid_statuses_are_never_recorded(self):
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_links([
            {"id": 1, "provider": "razorpay", "paid_amount": 0, "status": "created"},
            {"id": 2, "provider": "razorpay", "paid_amount": 500, "status": "cancelled"},
            {"id": 3, "provider": "razorpay", "paid_amount": 0, "status": "expired"},
        ])
        try:
            result = sevaa.reconcile_payments()
        finally:
            urllib.request.build_opener = original
        self.assertEqual(result["recorded"], [])
        from aion_core import metrics
        self.assertEqual(metrics.money()["real_revenue_inr"], 0.0)

    def test_replay_records_each_link_once(self):
        import urllib.request
        original = urllib.request.build_opener
        rows = [{"id": 5, "provider": "razorpay", "provider_payment_id": "pay_1",
                 "paid_amount": 2000, "status": "paid"}]
        urllib.request.build_opener = self._mock_links(rows)
        try:
            sevaa.reconcile_payments()
            second = sevaa.reconcile_payments()
        finally:
            urllib.request.build_opener = original
        self.assertEqual(second["recorded"], [])
        from aion_core import metrics
        self.assertEqual(metrics.money()["real_revenue_inr"], 2000.0)

    def test_lead_identity_is_never_forwarded_into_aion_state(self):
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_links([
            {"id": 11, "provider": "razorpay", "provider_payment_id": "pay_secret",
             "paid_amount": 3000, "status": "paid",
             "lead_name": "Sensitive Person", "lead_company": "Sensitive Co Pvt Ltd"},
        ])
        try:
            sevaa.reconcile_payments()
        finally:
            urllib.request.build_opener = original
        from aion_core import db
        blob = " ".join((r["description"] or "") + (r["evidence"] or "") for r in
                        db.connect().execute("SELECT description, evidence FROM finance"))
        self.assertNotIn("Sensitive Person", blob)
        self.assertNotIn("Sensitive Co", blob)
        self.assertIn("pay_secret", blob)

    def test_unreachable_reconciliation_does_not_raise(self):
        import urllib.request
        original = urllib.request.build_opener

        def boom(*a, **k):
            class _Opener:
                def open(self, req, timeout=5.0):
                    raise urllib.error.URLError("refused")
            return _Opener()
        urllib.request.build_opener = boom
        try:
            result = sevaa.reconcile_payments()
        finally:
            urllib.request.build_opener = original
        self.assertFalse(result["ok"])
        self.assertEqual(result["recorded"], [])

    def test_boot_reconciles_when_configured(self):
        import urllib.request
        original = urllib.request.build_opener
        urllib.request.build_opener = self._mock_links([
            {"id": 21, "provider": "razorpay", "provider_payment_id": "pay_boot",
             "paid_amount": 4200, "status": "paid"},
        ])
        try:
            from aion_core import resume
            out = resume.boot()
        finally:
            urllib.request.build_opener = original
        step = next(s for s in out["steps"] if s["step"] == "sevaa_reconcile")
        self.assertIn("1 payment(s) recorded", step["detail"])
