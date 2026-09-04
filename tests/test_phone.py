"""Phone interface backend: structured JSON for the mobile page."""
import unittest

from tests.base import AionTest
from aion_core import approvals, intake, metrics, phone, security, tasks


class TestDashboard(AionTest):
    def test_dashboard_has_all_sections(self):
        d = phone.dashboard()
        for key in ("as_of", "money", "feed", "needs_you", "mission_target_inr"):
            self.assertIn(key, d)
        self.assertIn("by_project", d["money"])
        self.assertIn("trend_7d", d["money"])

    def test_money_first_real_and_forecast_are_separated(self):
        metrics.record_money("revenue", 1000, stage="ACTUAL", evidence="pay_1")
        metrics.record_money("revenue", 500000, stage="FORECAST")
        d = phone.dashboard()
        self.assertEqual(d["money"]["real_revenue_inr"], 1000.0)
        self.assertIn("FORECAST", d["money"]["non_actual"])

    def test_pending_approval_appears_in_needs_you(self):
        aid = approvals.create("spend money", why="test")
        d = phone.dashboard()
        ids = [a["approval_id"] for a in d["needs_you"]["approvals"]]
        self.assertIn(aid, ids)

    def test_feedback_needed_surfaces_review_tasks(self):
        t = tasks.create("proposed direction", status="NEEDS_REVIEW",
                         description="because reasons")
        d = phone.dashboard()
        ids = [x["task_id"] for x in d["needs_you"]["feedback_needed"]]
        self.assertIn(t, ids)

    def test_secret_never_survives_into_dashboard_json(self):
        tasks.create("rotate ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        import json
        blob = json.dumps(phone.dashboard())
        self.assertNotIn("ghp_AbCdEf", blob)


class TestOtherEndpointsBackend(AionTest):
    def test_task_list_ranked(self):
        tasks.create("low", impact=1, cost=5)
        high = tasks.create("high", impact=5, cost=1)
        rows = phone.task_list(10)
        self.assertEqual(rows[0]["task_id"], high)

    def test_blockers_matches_dashboard_needs_you(self):
        approvals.create("x")
        self.assertEqual(len(phone.blockers()["approvals"]), 1)

    def test_money_endpoint_has_budget_governor(self):
        m = phone.money()
        self.assertIn("governor", m["budget"])

    def test_run_command_goes_through_the_same_router(self):
        result = phone.run_command("status")
        self.assertIn("AION STATUS", result["reply"])

    def test_capture_and_feedback_delegate_to_intake(self):
        r = phone.capture("a phone idea", "idea")
        self.assertEqual(r["status"], "SAVED")
        t = tasks.create("needs a decision")
        fb = phone.feedback(t, "yes", "go ahead")
        self.assertEqual(fb["task_status"], "READY")


if __name__ == "__main__":
    unittest.main()
