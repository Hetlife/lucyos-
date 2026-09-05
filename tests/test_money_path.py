"""The money path: steps are DONE when their checks pass, never when claimed."""
import json
import os
import unittest

from tests.base import AionTest
from aion_core import bootstrap, metrics, money_path, phone, reports


PATH = {
    "project": "demo",
    "goal": "first rupee",
    "steps": [
        {"id": "s1", "title": "designed", "you": "", "how": "",
         "checks": [{"file": "PROJECTS/demo/experiments/EXP-T-demo/experiment.json"}]},
        {"id": "s2", "title": "owner pays link", "you": "make the link", "how": "dashboard",
         "checks": [{"file_contains": ["PROJECTS/demo/LINK.md", "https://"]}]},
        {"id": "s3", "title": "first rupee", "you": "record it", "how": "aion money-add",
         "checks": [{"milestone": "M0"}]},
        {"id": "s4", "title": "secret present", "you": "set it", "how": "aion secrets set",
         "checks": [{"secret": "DEMO_TOKEN"}]},
    ],
}

SPEC = {"experiment_id": "EXP-T", "project": "demo", "title": "t", "funnel_log": "contacts.csv",
        "revenue_description_prefix": "EXP-T", "window_days": 5, "success": {"paid_min": 1},
        "failure": {"paid_max": 0}}


class MoneyPathTest(AionTest):
    def setUp(self):
        super().setUp()
        self.projects = self.tmp / "PROJECTS"
        exp = self.projects / "demo" / "experiments" / "EXP-T-demo"
        exp.mkdir(parents=True)
        (exp / "experiment.json").write_text(json.dumps(SPEC), encoding="utf-8")
        (self.projects / "demo" / "money_path.json").write_text(json.dumps(PATH), encoding="utf-8")
        os.environ["AION_PROJECTS_DIR"] = str(self.projects)

    def tearDown(self):
        os.environ.pop("AION_PROJECTS_DIR", None)
        super().tearDown()

    def test_first_undone_step_is_next_and_owner_step_is_surfaced(self):
        [p] = money_path.all_status()
        self.assertEqual([s["status"] for s in p["steps"]], ["DONE", "NEXT", "LATER", "LATER"])
        self.assertEqual(p["owner_next"]["id"], "s2")
        self.assertIn("make the link", money_path.owner_line())
        self.assertIn("Needs you (demo): make the link", reports.status())

    def test_steps_close_only_on_real_state(self):
        (self.projects / "demo" / "LINK.md").write_text("link: https://x", encoding="utf-8")
        [p] = money_path.all_status()
        self.assertEqual(p["steps"][1]["status"], "DONE")
        self.assertEqual(p["next"]["id"], "s3")
        metrics.record_money("revenue", 100, stage="FORECAST", project="demo",
                             description="EXP-T payer C01")
        self.assertEqual(money_path.all_status()[0]["steps"][2]["status"], "NEXT")
        metrics.record_money("revenue", 100, stage="ACTUAL", project="demo",
                             description="EXP-T payer C01", evidence="razorpay:pay_1")
        self.assertEqual(money_path.all_status()[0]["steps"][2]["status"], "DONE")
        bootstrap.set_secret("DEMO_TOKEN", "not-a-real-value-just-a-fixture")
        p = money_path.all_status()[0]
        self.assertEqual(p["done"], 4)
        self.assertIsNone(p["owner_next"])

    def test_a_broken_check_reads_as_not_done_not_a_crash(self):
        ok, detail = money_path.check({"experiment": ["EXP-NOPE", "sent", ">=", 1]})
        self.assertFalse(ok)
        self.assertIn("check failed", detail)
        ok, detail = money_path.check({"nonsense": 1})
        self.assertFalse(ok)

    def test_phone_dashboard_carries_the_path(self):
        dash = phone.dashboard()
        self.assertEqual(dash["money_path"][0]["project"], "demo")
        self.assertEqual(dash["money_path"][0]["next"]["id"], "s2")

    def test_report_marks_you_and_system(self):
        text = money_path.report("demo")
        self.assertIn("[x] s1 (system)", text)
        self.assertIn("[>] s2 (YOU)", text)
        self.assertIn("do: make the link", text)


if __name__ == "__main__":
    unittest.main()
