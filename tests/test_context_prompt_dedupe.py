"""Regression: AION worker must not paste the same owner instruction twice."""
from tests.base import AionTest
from aion_core import context, tasks, worker


class PromptDedupTest(AionTest):
    def setUp(self):
        super().setUp()
        self.distinct_instruction = "KEEP_THIS_OWNER_DIRECTIVE_" + "z" * 9000
        self.task_id = tasks.create(
            "Scoped context regression", project="lucyos",
            description="Business context: scoped test.\n\nPROMPT FOR THE EXECUTING MODEL:\n"
                        + self.distinct_instruction,
            success_criteria="one instruction copy; no authority change",
            validation_method="test_context_prompt_dedupe")
        self.prepared = {"status":"NEW", "source_revision":"a" * 40,
                         "json_path":"/tmp/context-pointer.json", "markdown":"# context\n"}

    def test_work_order_keeps_business_context_and_pointer(self):
        packet = context.build(self.task_id)
        self.assertIn("Business context: scoped test.", packet)
        self.assertNotIn(self.distinct_instruction, packet)
        self.assertIn("supplied separately", packet.lower())

    def test_worker_prompt_contains_one_complete_owner_instruction(self):
        prompt = worker._worker_prompt(tasks.get(self.task_id), self.prepared)
        self.assertEqual(prompt.count(self.distinct_instruction), 1)
        self.assertIn("## SUCCESS CRITERIA", prompt)
        self.assertIn("Business context: scoped test.", prompt)

    def test_compact_instruction_reduces_byte_usage_without_dropping_it(self):
        prompt = worker._worker_prompt(tasks.get(self.task_id), self.prepared)
        self.assertLess(len(prompt.encode("utf-8")), 11000)

    def test_plain_description_preserves_old_behavior(self):
        task_id = tasks.create("Ordinary", description="Unmarked owner intent 777")
        self.assertIn("Unmarked owner intent 777", context.build(task_id))
