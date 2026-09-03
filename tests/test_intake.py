import unittest

from tests.base import AionTest
from aion_core import config, intake, memory, metrics, security, tasks


class TestCapture(AionTest):
    def test_idea_becomes_a_triage_task(self):
        r = intake.capture("subscription box for architects", "idea")
        self.assertEqual(r["status"], "SAVED")
        self.assertEqual(tasks.get(r["task_id"])["status"], "INBOX")

    def test_company_gets_its_own_project_and_folder(self):
        r = intake.capture("Sevaa Prefab Homes", "company")
        self.assertEqual(r["project"], "sevaa-prefab-homes")
        self.assertTrue((config.home() / "PROJECTS" / "sevaa-prefab-homes" / "README.md").exists())

    def test_same_capture_twice_is_a_duplicate(self):
        intake.capture("one idea", "idea")
        self.assertEqual(intake.capture("one idea", "idea")["status"], "DUPLICATE")

    def test_credential_is_refused_and_not_stored(self):
        with self.assertRaises(security.SecretLeak):
            intake.capture("razorpay key rzp_live_9KpQm2XvT7aBcD", "note")
        self.assertEqual(memory.search("razorpay"), [])

    def test_note_goes_to_memory_not_the_queue(self):
        before = len(tasks.ready(50))
        r = intake.capture("prefer WhatsApp over email for approvals", "note")
        self.assertIn("memory_id", r)
        self.assertEqual(len(tasks.ready(50)), before)


class TestFeedback(AionTest):
    def test_yes_unblocks_and_records_a_decision(self):
        t = tasks.create("proposed outreach template", status="NEEDS_REVIEW", human_dependence=3)
        r = intake.feedback(t, "yes", "go with the shorter one")
        self.assertEqual(tasks.get(t)["status"], "READY")
        self.assertEqual(tasks.get(t)["next_action"], "go with the shorter one")
        self.assertIn("shorter one", memory.why(r["decision_id"]))

    def test_no_cancels_with_the_reason(self):
        t = tasks.create("buy ads", status="NEEDS_REVIEW")
        intake.feedback(t, "no", "too early")
        row = tasks.get(t)
        self.assertEqual(row["status"], "CANCELLED")
        self.assertIn("too early", row["last_error"])

    def test_later_defers(self):
        t = tasks.create("hire a designer", status="NEEDS_REVIEW")
        intake.feedback(t, "later")
        self.assertEqual(tasks.get(t)["status"], "WAITING")

    def test_bad_choice_and_unknown_task_fail_loudly(self):
        with self.assertRaises(ValueError):
            intake.feedback("TASK-NOPE", "yes")
        t = tasks.create("x")
        with self.assertRaises(ValueError):
            intake.feedback(t, "maybe")


class TestFeedAndMoney(AionTest):
    def test_feed_shows_real_changes_newest_first(self):
        t = tasks.create("done thing")
        tasks.complete(t, "ran it: worked")
        metrics.record_money("revenue", 500, stage="ACTUAL", evidence="pay_1", description="first sale")
        items = intake.feed(10)
        types = {i["type"] for i in items}
        self.assertIn("done", types)
        self.assertIn("money", types)
        self.assertEqual(items, sorted(items, key=lambda i: i["at"], reverse=True))

    def test_money_by_project_keeps_forecast_separate(self):
        metrics.record_money("revenue", 1000, stage="ACTUAL", evidence="pay_1", project="alpha")
        metrics.record_money("cost", 200, stage="ACTUAL", evidence="inv_1", project="alpha")
        metrics.record_money("revenue", 90000, stage="FORECAST", project="alpha")
        row = metrics.by_project()[0]
        self.assertEqual(row["net"], 800.0)
        self.assertEqual(row["forecast"], 90000.0)


if __name__ == "__main__":
    unittest.main()
