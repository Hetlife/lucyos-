import unittest

from tests.base import AionTest
from aion_core import approvals, tasks


class TestApprovals(AionTest):
    def _make(self):
        t = tasks.create("deploy paid instance", model_class="B")
        a = approvals.create("Purchase Railway Hobby plan", why="free tier insufficient",
                             cost="INR 500/month", max_downside="INR 500 wasted, cancel anytime",
                             reversibility="reversible — cancel in console",
                             prepared="config, deploy file, rollback plan",
                             resumes="run the prepared deploy", task_id=t)
        return t, a

    def test_holds_only_its_own_task(self):
        other = tasks.create("independent work")
        t, a = self._make()
        self.assertEqual(tasks.get(t)["status"], "NEEDS_APPROVAL")
        self.assertEqual(tasks.get(other)["status"], "READY")
        self.assertIn(other, [r["task_id"] for r in tasks.ready(10)])

    def test_approve_resumes_the_prepared_step(self):
        t, a = self._make()
        result = approvals.decide(a, "APPROVED")
        self.assertTrue(result["changed"])
        row = tasks.get(t)
        self.assertEqual(row["status"], "READY")
        self.assertEqual(row["next_action"], "run the prepared deploy")

    def test_deny_cancels_only_that_task(self):
        t, a = self._make()
        approvals.decide(a, "DENIED")
        self.assertEqual(tasks.get(t)["status"], "CANCELLED")

    def test_duplicate_reply_is_not_reapplied(self):
        t, a = self._make()
        approvals.decide(a, "APPROVED")
        again = approvals.decide(a, "DENIED")
        self.assertFalse(again["changed"])
        self.assertEqual(approvals.get(a)["status"], "APPROVED")

    def test_ids_are_sequential_and_unique(self):
        first = approvals.create("one")
        second = approvals.create("two")
        self.assertNotEqual(first, second)
        self.assertEqual(int(second[2:]), int(first[2:]) + 1)

    def test_render_contains_reply_instructions(self):
        _, a = self._make()
        card = approvals.render(approvals.get(a))
        self.assertIn(f"APPROVE {a}", card)
        self.assertIn(f"DENY {a}", card)


if __name__ == "__main__":
    unittest.main()
