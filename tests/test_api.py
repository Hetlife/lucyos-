import json
import unittest

from tests.base import AionTest
from aion_core import api, metrics, tasks


class TestSystemSnapshot(AionTest):
    def test_snapshot_is_json_serialisable_and_shaped(self):
        snap = api.system_snapshot()
        json.dumps(snap)  # must not raise
        for key in ("as_of", "healthy", "checks", "bottleneck", "next_action",
                    "task_counts", "governor", "paused", "safe_mode",
                    "pending_approvals"):
            self.assertIn(key, snap)
        self.assertIsInstance(snap["checks"], list)
        self.assertIsInstance(snap["task_counts"], dict)


class TestMoneySplit(AionTest):
    def test_actual_is_real_forecast_is_simulated_never_combined(self):
        metrics.record_money("revenue", 1000, stage="ACTUAL", evidence="pay_1")
        metrics.record_money("revenue", 50000, stage="FORECAST", description="pipeline")
        split = api.money_split()
        json.dumps(split)
        self.assertEqual(split["real"]["revenue_inr"], 1000.0)
        self.assertEqual(split["simulated"]["revenue_inr"], 50000.0)
        # The forecast amount must never leak into the real figure.
        self.assertNotEqual(split["real"]["revenue_inr"], 51000.0)
        self.assertIn("FORECAST", split["simulated"]["by_stage"])
        self.assertNotIn("FORECAST", split["real"])

    def test_mission_pct_uses_real_net_only(self):
        metrics.record_money("revenue", 500000, stage="SIMULATION", description="test")
        split = api.money_split()
        self.assertEqual(split["mission_pct"], 0.0)

    def test_milestones_present(self):
        split = api.money_split()
        self.assertIn("M0", split["milestones"])


class TestProjects(AionTest):
    def test_two_projects_stay_separate(self):
        tasks.create("alpha work", project="alpha")
        tasks.create("beta work", project="beta")
        metrics.record_money("revenue", 100, stage="ACTUAL", project="alpha", evidence="pay_a")
        metrics.record_money("revenue", 999, stage="FORECAST", project="beta")

        rows = api.projects()
        json.dumps(rows)
        by_name = {r["project"]: r for r in rows}
        self.assertIn("alpha", by_name)
        self.assertIn("beta", by_name)
        self.assertEqual(by_name["alpha"]["real_net_inr"], 100.0)
        self.assertEqual(by_name["alpha"]["simulated_net_inr"], 0.0)
        self.assertEqual(by_name["beta"]["real_net_inr"], 0.0)
        self.assertEqual(by_name["beta"]["simulated_net_inr"], 999.0)
        self.assertGreaterEqual(by_name["alpha"]["open_tasks"], 1)


class TestCosts(AionTest):
    def test_costs_sum_only_recorded_usage(self):
        metrics.record_usage("claude-sonnet-5", "B", cost_inr=42.5)
        metrics.record_usage("claude-opus-5", "C", cost_inr=100.0)
        c = api.costs()
        json.dumps(c)
        self.assertEqual(c["month_inr"], 142.5)
        classes = {row["model_class"]: row["cost_inr"] for row in c["by_class"]}
        self.assertEqual(classes["B"], 42.5)
        self.assertEqual(classes["C"], 100.0)
        self.assertIn("governor", c)

    def test_no_usage_is_zero_not_missing(self):
        c = api.costs()
        self.assertEqual(c["today_inr"], 0.0)
        self.assertEqual(c["by_model"], [])


if __name__ == "__main__":
    unittest.main()
