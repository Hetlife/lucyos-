import unittest

from aion_core import tasks
from aion_core.resource_governor import admission, flags, schema
from tests.base import AionTest


def _snap(claude_remaining=None, claude_confidence="UNKNOWN", local_available=False):
    claude = schema.empty_resource("claude", confidence=claude_confidence)
    if claude_remaining is not None:
        claude["quota"]["remaining_pct"] = claude_remaining
        claude["quota"]["used_pct"] = 100 - claude_remaining
        claude["state"] = None  # filled in below via observability normally; tests set state directly
    from aion_core.resource_governor import state as state_mod
    claude["state"] = state_mod.base_state(claude)
    return {
        "providers": {"claude": claude},
        "local": {"provider": "local", "available": local_available, "model": "llama3.1:8b"},
        "overall_state": claude["state"],
        "waiting_for_resource": [],
        "flags": flags.all_flags(),
    }


class TestAdmission(AionTest):
    def test_deterministic_task_always_runs_now(self):
        t = tasks.get(tasks.create("format a file", model_class="DET"))
        d = admission.evaluate(t, snap=_snap())
        self.assertEqual(d["decision"], "RUN_NOW")

    def test_owner_class_always_requires_owner_decision(self):
        t = tasks.get(tasks.create("spend money", model_class="D"))
        d = admission.evaluate(t, snap=_snap())
        self.assertEqual(d["decision"], "REQUIRE_OWNER_DECISION")

    def test_class_a_reroutes_to_local_when_available(self):
        t = tasks.get(tasks.create("classify a lead", model_class="A"))
        d = admission.evaluate(t, snap=_snap(local_available=True))
        self.assertEqual(d["decision"], "RUN_LOCAL")

    def test_normal_capacity_runs_now(self):
        t = tasks.get(tasks.create("write some code", model_class="B"))
        d = admission.evaluate(t, snap=_snap(70.0, "OFFICIAL_CURRENT"))
        self.assertEqual(d["decision"], "RUN_NOW")

    def test_exhausted_capacity_defers(self):
        t = tasks.get(tasks.create("write some code", model_class="B"))
        d = admission.evaluate(t, snap=_snap(2.0, "OFFICIAL_CURRENT"))
        self.assertEqual(d["decision"], "DEFER_UNTIL_RESET")

    def test_unknown_telemetry_never_blocks_a_task(self):
        t = tasks.get(tasks.create("write some code", model_class="B"))
        d = admission.evaluate(t, snap=_snap(None, "UNKNOWN"))
        self.assertEqual(d["decision"], "RUN_NOW")
        self.assertIn("telemetry unknown", " ".join(d["reasoning"]))

    def test_small_task_accepted_under_critical_capacity(self):
        t = tasks.get(tasks.create("tiny task", model_class="B"))
        d = admission.evaluate(t, snap=_snap(7.0, "OFFICIAL_CURRENT"))
        self.assertIn(d["task_size"], ("TINY", "SMALL"))
        self.assertEqual(d["decision"], "RUN_REDUCED_SCOPE")

    def test_large_task_rejected_under_constrained_capacity(self):
        long_desc = "x" * 60000
        t = tasks.get(tasks.create("large task", model_class="C", description=long_desc))
        d = admission.evaluate(t, snap=_snap(20.0, "OFFICIAL_CURRENT"))
        self.assertIn(d["task_size"], ("LARGE", "VERY_LARGE"))
        self.assertIn(d["decision"], ("CHECKPOINT_FIRST", "RUN_CHEAPER_MODEL"))

    def test_class_c_under_critical_requires_owner(self):
        t = tasks.get(tasks.create("hard debug", model_class="C", kind="hard_debug"))
        d = admission.evaluate(t, snap=_snap(7.0, "OFFICIAL_CURRENT"))
        self.assertEqual(d["decision"], "REQUIRE_OWNER_DECISION")

    def test_apply_run_now_lets_the_caller_proceed_unchanged(self):
        t = tasks.get(tasks.create("write some code", model_class="B"))
        decision = admission.evaluate(t, snap=_snap(70.0, "OFFICIAL_CURRENT"))
        outcome = admission.apply(t, decision)
        self.assertTrue(outcome["proceed"])
        self.assertIsNone(outcome["class_override"])

    def test_apply_run_cheaper_model_downgrades_for_this_run(self):
        t = tasks.get(tasks.create("architecture review", model_class="C", kind="architecture"))
        decision = admission.evaluate(t, snap=_snap(40.0, "OFFICIAL_CURRENT"))
        self.assertEqual(decision["decision"], "RUN_CHEAPER_MODEL")
        outcome = admission.apply(t, decision)
        self.assertTrue(outcome["proceed"])
        self.assertEqual(outcome["class_override"], "B")

    def test_apply_defer_with_auto_defer_off_only_records_the_decision(self):
        flags.set_flag("resource_governor.auto_defer", False)
        t = tasks.get(tasks.create("write some code", model_class="B"))
        decision = admission.evaluate(t, snap=_snap(2.0, "OFFICIAL_CURRENT"))
        outcome = admission.apply(t, decision)
        self.assertTrue(outcome["proceed"])  # not enforced
        row = tasks.get(t["task_id"])
        self.assertEqual(row["status"], "READY")

    def test_apply_defer_with_auto_defer_on_parks_the_task(self):
        flags.set_flag("resource_governor.auto_defer", True)
        t = tasks.get(tasks.create("write some code", model_class="B"))
        decision = admission.evaluate(t, snap=_snap(2.0, "OFFICIAL_CURRENT"))
        outcome = admission.apply(t, decision)
        self.assertFalse(outcome["proceed"])
        row = tasks.get(t["task_id"])
        self.assertEqual(row["status"], "WAITING")
        self.assertIn("resource governor:", row["blockers"])

    def test_apply_require_owner_decision_raises_an_approval(self):
        t = tasks.get(tasks.create("spend money", model_class="D"))
        decision = admission.evaluate(t, snap=_snap())
        outcome = admission.apply(t, decision)
        self.assertFalse(outcome["proceed"])
        row = tasks.get(t["task_id"])
        self.assertEqual(row["status"], "NEEDS_APPROVAL")


if __name__ == "__main__":
    unittest.main()
