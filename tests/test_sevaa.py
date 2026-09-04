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
