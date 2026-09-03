import unittest

from tests.base import AionTest
from aion_core import tasks


class TestTasks(AionTest):
    def test_create_and_rank_by_value(self):
        low = tasks.create("low value", impact=1, cost=5, risk=2)
        high = tasks.create("high value", impact=5, cost=1, risk=1)
        order = [r["task_id"] for r in tasks.ready(10)]
        self.assertLess(order.index(high), order.index(low))

    def test_done_requires_evidence(self):
        t = tasks.create("prove it")
        with self.assertRaises(tasks.TaskError):
            tasks.complete(t, "")
        tasks.complete(t, "ran `python3 -m unittest`: 24 passed")
        self.assertEqual(tasks.get(t)["status"], "DONE")

    def test_claim_is_exclusive(self):
        t = tasks.create("one owner only")
        self.assertTrue(tasks.claim(t, "agent-a"))
        self.assertFalse(tasks.claim(t, "agent-b"))
        self.assertEqual(tasks.get(t)["owner_agent"], "agent-a")

    def test_dependencies_gate_readiness(self):
        first = tasks.create("first")
        second = tasks.create("second", dependencies=first)
        self.assertNotIn(second, [r["task_id"] for r in tasks.ready(10)])
        tasks.complete(first, "evidence: done")
        self.assertIn(second, [r["task_id"] for r in tasks.ready(10)])

    def test_failure_retries_then_blocks(self):
        t = tasks.create("flaky")
        self.assertEqual(tasks.fail(t, "boom 1"), "READY")
        self.assertEqual(tasks.fail(t, "boom 2"), "READY")
        self.assertEqual(tasks.fail(t, "boom 3"), "BLOCKED")

    def test_stale_claim_is_released(self):
        t = tasks.create("abandoned")
        tasks.claim(t, "agent-gone")
        self.assertEqual(tasks.release_stale(max_age_s=-1), [t])
        self.assertEqual(tasks.get(t)["status"], "READY")

    def test_secrets_never_enter_task_titles(self):
        t = tasks.create("deploy with ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        self.assertNotIn("ghp_", tasks.get(t)["title"])


if __name__ == "__main__":
    unittest.main()


class TestCompletionRefreshesResume(AionTest):
    def test_resume_point_moves_on_after_a_completion(self):
        from aion_core import resume
        first = tasks.create("first job", impact=5, cost=1)
        second = tasks.create("second job", impact=4, cost=1, next_action="do the second thing")
        resume.checkpoint(next_action=f"work {first} : first job")
        tasks.complete(first, "ran the thing: it worked")
        state = resume.load()
        self.assertIn(second, state["next_action"])
        self.assertIn("it worked", state["last_verified_success"])

    def test_empty_queue_after_completion_says_so(self):
        from aion_core import resume
        only = tasks.create("the only job")
        tasks.complete(only, "evidence recorded")
        self.assertIn("queue empty", resume.load()["next_action"])
