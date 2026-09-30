import unittest

from tests.base import AionTest
from aion_core import approvals, db, router, tasks


class TestRouter(AionTest):
    def test_shortcuts_answer_without_a_model(self):
        for cmd in ["status", "today", "money", "tasks", "blockers", "errors", "agents",
                    "report", "help"]:
            reply = router.handle(cmd)
            self.assertTrue(reply and len(reply) > 5, f"{cmd} gave no answer")

    def test_natural_language_maps_to_commands(self):
        self.assertIn("AION STATUS", router.handle("hey, how are things looking?"))
        self.assertIn("MONEY", router.handle("what's our revenue so far"))
        self.assertIn("NEED", router.handle("anything you need from me?").upper())

    def test_secret_in_message_is_refused_and_not_stored(self):
        reply = router.handle("here is the key sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWx")
        self.assertIn("did not store", reply)
        rows = db.connect().execute("SELECT detail, subject FROM events").fetchall()
        blob = " ".join((r["detail"] or "") + (r["subject"] or "") for r in rows)
        self.assertNotIn("sk-ant-api03", blob)

    def test_casual_talk_never_approves(self):
        t = tasks.create("spend money")
        a = approvals.create("buy hosting", task_id=t)
        for text in ["yeah sounds good", "ok go for it", "sure why not", "approve"]:
            router.handle(text)
        self.assertEqual(approvals.get(a)["status"], "PENDING")

    def test_exact_form_approves(self):
        t = tasks.create("spend money")
        a = approvals.create("buy hosting", resumes="run deploy", task_id=t)
        reply = router.handle(f"APPROVE {a}")
        self.assertIn(a, reply)
        self.assertEqual(approvals.get(a)["status"], "APPROVED")

    def test_only_the_exact_form_decides_an_approval(self):
        # Every one of these once decided an approval through a loose pattern.
        loose = [
            "don't approve {a}", "not yet, will approve {a} tomorrow", "yes to {a}",
            "go ahead with {a}", "approved {a}", "should I approve {a}?",
            "I denied {a} last week?", "don't cancel {a}", "no to {a} for now",
            "approve {a} please",
        ]
        for template in loose:
            t = tasks.create("guarded step")
            a = approvals.create("guarded action", task_id=t)
            reply = router.handle(template.format(a=a))
            self.assertEqual(approvals.get(a)["status"], "PENDING", template)
            self.assertEqual(tasks.get(t)["status"], "NEEDS_APPROVAL", template)
            self.assertIn(f"APPROVE {a} or DENY {a}", reply, template)
            self.assertIn("Nothing was decided", reply, template)

    def test_strict_form_is_case_and_space_tolerant_and_still_decides(self):
        for text, expected in (("  approve {a}  ", "APPROVED"), ("Deny {a}", "DENIED"),
                               ("REJECT {a}", "DENIED")):
            a = approvals.create("x")
            router.handle(text.format(a=a))
            self.assertEqual(approvals.get(a)["status"], expected, text)

    def test_why_with_a_decision_word_explains_and_does_not_decide(self):
        a = approvals.create("buy hosting", why="needed for the site")
        reply = router.handle(f"why would I approve {a}?")
        self.assertEqual(approvals.get(a)["status"], "PENDING")
        self.assertNotIn("Nothing was decided", reply)

    def test_reject_is_accepted_as_deny(self):
        a = approvals.create("buy hosting")
        router.handle(f"reject {a}")
        self.assertEqual(approvals.get(a)["status"], "DENIED")

    def test_unknown_message_becomes_a_triage_task_not_a_guess(self):
        before = len(tasks.by_status("INBOX"))
        router.handle("remind me about the Sharma quotation next week")
        self.assertEqual(len(tasks.by_status("INBOX")), before + 1)

    def test_pause_resume_and_safe_mode_persist(self):
        router.handle("pause")
        self.assertTrue(router.is_paused())
        router.handle("resume")
        self.assertFalse(router.is_paused())
        router.handle("safe mode")
        self.assertTrue(router.is_safe_mode())
        router.handle("safe mode off")
        self.assertFalse(router.is_safe_mode())

    def test_why_explains_a_recorded_decision(self):
        from aion_core import memory
        d = memory.decide("hosting", "stay on the home PC", rationale="no revenue yet")
        self.assertIn("no revenue yet", router.handle(f"why {d}"))

    def test_deep_check_reports_every_check(self):
        reply = router.handle("deep check")
        self.assertIn("DEEP CHECK", reply)
        self.assertIn("database", reply)


if __name__ == "__main__":
    unittest.main()
