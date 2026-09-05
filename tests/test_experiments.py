"""Revenue experiments: the verdict is computed from real rows, never claimed."""
import json
import os
import unittest
from datetime import date, timedelta
from pathlib import Path

from tests.base import AionTest
from aion_core import experiments, metrics, phone, reports


SPEC = {
    "experiment_id": "EXP-T",
    "project": "demo",
    "title": "demo offer",
    "offer_price_inr": 100,
    "funnel_log": "contacts.csv",
    "revenue_description_prefix": "EXP-T",
    "min_contacts": 4,
    "min_contacts_deadline_days": 3,
    "window_days": 10,
    "success": {"paid_min": 2},
    "failure": {"paid_max": 0},
    "ambiguous": {"extend_days": 5, "extend_contacts_to": 8, "then_paid_min": 2},
    "decisions": {
        "SUCCESS": "go public",
        "FAILURE_price": "retry cheaper",
        "FAILURE_offer": "change buyer",
        "AMBIGUOUS": "extend once",
        "BLOCKED": "owner time is the wall",
    },
}


class ExperimentTest(AionTest):
    def setUp(self):
        super().setUp()
        self.projects = self.tmp / "PROJECTS"
        self.folder = self.projects / "demo" / "experiments" / "EXP-T-demo"
        self.folder.mkdir(parents=True)
        (self.folder / "experiment.json").write_text(json.dumps(SPEC), encoding="utf-8")
        os.environ["AION_PROJECTS_DIR"] = str(self.projects)

    def tearDown(self):
        os.environ.pop("AION_PROJECTS_DIR", None)
        super().tearDown()

    def _csv(self, rows):
        lines = ["contact_code,sent_at,reply,reason_code,paid,payment_ref"] + rows
        (self.folder / "contacts.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _sent(self, n, day):
        return [f"C{i:02d},{day.isoformat()},,,0," for i in range(1, n + 1)]

    def test_not_started_without_a_sent_row(self):
        s = experiments.status("EXP-T")
        self.assertEqual(s["state"], "NOT_STARTED")
        self.assertEqual(s["sent"], 0)

    def test_running_inside_the_window(self):
        today = date(2026, 9, 10)
        self._csv(self._sent(4, today - timedelta(days=2)))
        s = experiments.status("EXP-T", today=today)
        self.assertEqual(s["state"], "RUNNING")
        self.assertEqual(s["day"], 3)

    def test_claimed_paid_in_csv_is_not_evidence(self):
        today = date(2026, 9, 10)
        self._csv(["C01,2026-09-09,interested,,1,razorpay:pay_x",
                   "C02,2026-09-09,interested,,1,razorpay:pay_y"])
        s = experiments.status("EXP-T", today=today)
        self.assertEqual(s["claimed_paid"], 2)
        self.assertEqual(s["paid"], 0)
        self.assertEqual(s["state"], "RUNNING")

    def test_success_comes_only_from_actual_revenue_rows(self):
        today = date(2026, 9, 10)
        self._csv(self._sent(4, today - timedelta(days=1)))
        metrics.record_money("revenue", 100, stage="ACTUAL", project="demo",
                             description="EXP-T payer C01", evidence="razorpay:pay_1")
        metrics.record_money("revenue", 100, stage="FORECAST", project="demo",
                             description="EXP-T payer C02")
        self.assertEqual(experiments.status("EXP-T", today=today)["state"], "RUNNING")
        metrics.record_money("revenue", 100, stage="ACTUAL", project="demo",
                             description="EXP-T payer C03", evidence="razorpay:pay_3")
        s = experiments.status("EXP-T", today=today)
        self.assertEqual(s["state"], "SUCCESS")
        self.assertEqual(s["revenue_inr"], 200)
        self.assertEqual(s["decision"], "go public")

    def test_failure_after_window_picks_the_reason_branch(self):
        start = date(2026, 9, 1)
        rows = [f"C{i:02d},{start.isoformat()},declined,price,0," for i in range(1, 6)]
        self._csv(rows)
        s = experiments.status("EXP-T", today=start + timedelta(days=11))
        self.assertEqual(s["state"], "FAILURE")
        self.assertEqual(s["decision"], "retry cheaper")
        # Fewer replies: the offer branch, not the price branch.
        self._csv(self._sent(5, start))
        s = experiments.status("EXP-T", today=start + timedelta(days=11))
        self.assertEqual(s["decision"], "change buyer")

    def test_ambiguous_extends_exactly_once(self):
        start = date(2026, 9, 1)
        self._csv(self._sent(4, start))
        metrics.record_money("revenue", 100, stage="ACTUAL", project="demo",
                             description="EXP-T payer C01", evidence="razorpay:pay_1")
        s = experiments.status("EXP-T", today=start + timedelta(days=11))
        self.assertEqual(s["state"], "EXTENDED")
        self.assertTrue(s["extended"])
        self.assertEqual(s["window_days"], 15)
        s = experiments.status("EXP-T", today=start + timedelta(days=16))
        self.assertEqual(s["state"], "FAILURE")

    def test_too_few_sent_past_the_deadline_is_blocked_not_failed(self):
        start = date(2026, 9, 1)
        self._csv(self._sent(2, start))
        s = experiments.status("EXP-T", today=start + timedelta(days=4))
        self.assertEqual(s["state"], "BLOCKED")
        self.assertEqual(s["decision"], "owner time is the wall")

    def test_decide_refuses_until_a_verdict_exists_then_writes_result(self):
        self._csv(self._sent(4, date.today()))
        with self.assertRaises(experiments.ExperimentError):
            experiments.decide("EXP-T")
        for i in (1, 2):
            metrics.record_money("revenue", 100, stage="ACTUAL", project="demo",
                                 description=f"EXP-T payer C0{i}", evidence=f"razorpay:pay_{i}")
        out = experiments.decide("EXP-T")
        self.assertEqual(out["state"], "SUCCESS")
        self.assertTrue(Path(out["result_file"]).exists())
        self.assertIn("go public", Path(out["result_file"]).read_text())

    def test_status_reply_and_phone_dashboard_carry_the_funnel(self):
        self._csv(self._sent(4, date.today()))
        self.assertIn("EXP-T: RUNNING", reports.status())
        dash = phone.dashboard()
        self.assertEqual(dash["experiments"][0]["experiment_id"], "EXP-T")
        self.assertEqual(dash["experiments"][0]["sent"], 4)

    def test_unknown_experiment_is_an_error(self):
        with self.assertRaises(experiments.ExperimentError):
            experiments.status("EXP-NOPE")


if __name__ == "__main__":
    unittest.main()
