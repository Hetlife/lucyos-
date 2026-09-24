import unittest
from unittest.mock import patch

from tests.base import AionTest
from aion_core import completion, context, tasks, worker


class TestCompletionContract(AionTest):
    def test_substantial_model_work_without_any_gate_is_blocked(self):
        t = tasks.create("implement feature", model_class="B", kind="code")
        result = completion.preflight(tasks.get(t))
        self.assertFalse(result["ok"])
        self.assertIn("success criteria", result["detail"])

    def test_validation_command_is_a_valid_acceptance_gate(self):
        t = tasks.create("implement feature", model_class="B", kind="code",
                         validation_command="python3 -c 'raise SystemExit(0)'")
        self.assertTrue(completion.preflight(tasks.get(t))["ok"])

    def test_context_always_contains_machine_completion_contract(self):
        t = tasks.create("research current behavior", model_class="B", kind="research",
                         success_criteria="report cites measured current behavior")
        packet = context.build(t)
        self.assertIn("## COMPLETION CONTRACT", packet)
        self.assertIn("G4 REVERIFY", packet)
        self.assertIn("installed `unlazy` skill", packet)

    @patch("aion_core.worker._do_work")
    def test_worker_does_not_start_substantial_model_work_without_gate(self, do_work):
        t = tasks.create("vague coding task", model_class="B", kind="code")
        result = worker.work(max_tasks=1)
        self.assertEqual(result["results"][0]["status"], "NEEDS_REVIEW")
        self.assertEqual(tasks.get(t)["status"], "NEEDS_REVIEW")
        do_work.assert_not_called()


if __name__ == "__main__":
    unittest.main()
