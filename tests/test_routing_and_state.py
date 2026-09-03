import unittest

from tests.base import AionTest
from aion_core import agents, errors, memory, metrics, resume, tasks


class TestModelRouting(AionTest):
    def test_mechanical_work_never_reaches_a_model(self):
        for kind in ("hash", "backup", "git", "health_check", "test_run"):
            self.assertEqual(agents.route(kind)["model_class"], "DET", kind)

    def test_routine_language_work_goes_local(self):
        for kind in ("classify", "extract", "summarize", "log_parse"):
            self.assertEqual(agents.route(kind)["model_class"], "A", kind)

    def test_hard_work_goes_strong(self):
        for kind in ("architecture", "security_review", "hard_debug", "finance_reason"):
            self.assertEqual(agents.route(kind)["model_class"], "C", kind)

    def test_complexity_and_stakes_escalate(self):
        self.assertEqual(agents.route("classify", complexity=4)["model_class"], "C")
        self.assertEqual(agents.route("code", stakes="high")["model_class"], "C")
        self.assertEqual(agents.route("classify", ambiguity="high")["model_class"], "B")

    def test_owner_boundary_routes_to_owner(self):
        for kind in ("spend", "contract", "credential", "account_change"):
            self.assertEqual(agents.route(kind)["model_class"], "D", kind)

    def test_escalation_is_one_step_and_stops_below_owner(self):
        self.assertEqual(agents.escalate("A", "two different failures")["model_class"], "B")
        self.assertEqual(agents.escalate("B", "low confidence")["model_class"], "C")
        self.assertEqual(agents.escalate("C", "still stuck")["model_class"], "C")

    def test_route_always_explains_itself(self):
        self.assertTrue(agents.route("classify")["reason"])

    def test_reliability_tracks_failures(self):
        agents.record_run("ollama-local", success=True)
        agents.record_run("ollama-local", success=False)
        self.assertEqual(agents.get("ollama-local")["reliability"], 0.5)


class TestBudgetGovernor(AionTest):
    def _gov(self):
        return metrics.budget_status()["governor"].split(" ")[0]

    def test_thresholds_move_with_spend(self):
        self.assertEqual(self._gov(), "NORMAL")
        metrics.record_usage("strong", "C", cost_inr=600)      # 30%
        self.assertEqual(self._gov(), "ARCHITECTURE-DONE")
        metrics.record_usage("strong", "C", cost_inr=500)      # 55%
        self.assertEqual(self._gov(), "SHIFT-DOWN")
        metrics.record_usage("strong", "C", cost_inr=400)      # 75%
        self.assertEqual(self._gov(), "RESERVE")
        metrics.record_usage("strong", "C", cost_inr=300)      # 90%
        self.assertEqual(self._gov(), "CRITICAL-ONLY")
        metrics.record_usage("strong", "C", cost_inr=200)      # 100%
        self.assertEqual(self._gov(), "STOP")

    def test_cheap_model_spend_does_not_consume_the_strong_budget(self):
        metrics.record_usage("local", "A", cost_inr=0)
        metrics.record_usage("cheap", "B", cost_inr=50)
        self.assertEqual(metrics.budget_status()["strong_model_spend_inr"], 0.0)

    def test_actual_money_requires_evidence(self):
        with self.assertRaises(ValueError):
            metrics.record_money("revenue", 5000, stage="ACTUAL")
        metrics.record_money("revenue", 5000, stage="ACTUAL", evidence="Razorpay pay_ABC123")
        self.assertEqual(metrics.money()["real_revenue_inr"], 5000.0)

    def test_forecast_is_kept_out_of_real_numbers(self):
        metrics.record_money("revenue", 100000, stage="FORECAST", description="pipeline")
        m = metrics.money()
        self.assertEqual(m["real_revenue_inr"], 0.0)
        self.assertIn("FORECAST", m["non_actual"])


class TestFailureLoop(AionTest):
    def test_classification(self):
        self.assertEqual(errors.classify("connection timeout to host"), "network")
        self.assertEqual(errors.classify("HTTP 429 too many requests"), "rate_limit")
        self.assertEqual(errors.classify("401 unauthorized"), "auth")
        self.assertEqual(errors.classify("something odd"), "unknown")

    def test_resolution_creates_a_reusable_lesson(self):
        e = errors.record("bridge", "HTTP 429 too many requests")
        errors.resolve(e, "no rate limiting on send", "added token bucket",
                       "Bridge provider rejects above 20 msg/min; throttle before dispatch.")
        self.assertTrue(memory.search("token bucket") or memory.search("throttle"))
        self.assertEqual(len(errors.open_errors()), 0)

    def test_runaway_detector(self):
        for _ in range(5):
            errors.record("bridge", "connection refused")
        self.assertTrue(errors.repeated("bridge"))


class TestResume(AionTest):
    def test_boot_is_idempotent_and_names_a_bottleneck(self):
        first = resume.boot()
        self.assertTrue(first["resume"]["bottleneck"])
        second = resume.boot()
        self.assertTrue(second["resume"]["at"])

    def test_checkpoint_survives_a_restart(self):
        tasks.create("resume me", next_action="continue at step 3")
        resume.checkpoint(objective="first revenue", current_task="TASK-X",
                          last_verified_success="39 tests passed")
        from aion_core import db
        db.close()
        state = resume.load()
        self.assertEqual(state["objective"], "first revenue")
        self.assertEqual(state["last_verified_success"], "39 tests passed")

    def test_boot_reports_the_previous_next_action_rather_than_rerunning_it(self):
        resume.checkpoint(next_action="deploy the thing")
        out = resume.boot()
        self.assertEqual(out["previous_next_action"], "deploy the thing")

    def test_bottleneck_ranks_health_then_errors_then_approvals(self):
        healthy = {"healthy": True, "failing": []}
        degraded = {"healthy": False, "failing": ["database"]}
        approval = [{"approval_id": "A-101"}]
        self.assertIn("health", resume.identify_bottleneck(degraded, [], [], None))
        self.assertIn("failure", resume.identify_bottleneck(healthy, [], [{"error_id": "E"}], None))
        self.assertIn("approval", resume.identify_bottleneck(healthy, approval, [], None))
        self.assertIn("empty ready queue", resume.identify_bottleneck(healthy, [], [], None))

    def test_bottleneck_names_approvals_end_to_end(self):
        from aion_core import approvals, backup, bootstrap
        bootstrap.init_secret_store()
        backup.create()
        t = tasks.create("only task")
        approvals.create("spend money", task_id=t)
        out = resume.boot()
        self.assertIn("approval", out["resume"]["bottleneck"].lower())


class TestMemory(AionTest):
    def test_search_finds_stored_facts(self):
        memory.remember("fact", "Razorpay", "Razorpay test keys work in sandbox only.",
                        confidence="VERIFIED_FACT")
        self.assertTrue(memory.search("Razorpay"))

    def test_duplicate_memory_is_not_stored_twice(self):
        a = memory.remember("fact", "same", "identical body")
        b = memory.remember("fact", "same", "identical body")
        self.assertEqual(a, b)

    def test_why_explains_task_approval_and_error(self):
        t = tasks.create("explain me", description="because it matters")
        self.assertIn("because it matters", memory.why(t))
        self.assertIn("No record found", memory.why("NOPE-1"))


if __name__ == "__main__":
    unittest.main()


class TestBottleneckFreshness(AionTest):
    def test_bottleneck_stops_naming_a_completed_task(self):
        done = tasks.create("finish me", impact=5)
        nxt = tasks.create("the next thing", impact=4)
        resume.checkpoint(bottleneck=f"execution capacity on {done}")
        tasks.complete(done, "evidence: it ran")
        state = resume.checkpoint()
        self.assertNotIn(done, state["bottleneck"])
        self.assertIn(nxt, state["bottleneck"])

    def test_a_live_bottleneck_is_left_alone(self):
        live = tasks.create("still going")
        resume.checkpoint(bottleneck=f"execution capacity on {live}")
        self.assertIn(live, resume.checkpoint()["bottleneck"])
