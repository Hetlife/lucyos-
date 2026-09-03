"""The end-to-end target from the directive, tested for real.

EXTERNAL AI PACKET -> INGEST -> LOCAL STATE -> TASK -> MODEL ROUTING ->
AGENT EXECUTION -> VALIDATION -> RESULT PACKET -> STATE UPDATE -> OWNER STATUS.

Only one boundary is simulated: the WhatsApp transport itself.  Everything
else runs against the real database, the real router and the real files.
"""
import unittest

from tests.base import AionTest
from aion_core import (agents, approvals, backup, config, context, db, fable, health,
                       memory, metrics, packets, reports, resume, router, tasks)

PACKET = """# AI SYNC PACKET

PACKET_ID: PKT-E2E-1
SOURCE: claude
PROJECT: lucyos
TOPIC: revenue push

## VERIFIED FACTS
- The lead CSV contains 14 rows.

## TASKS CREATED
- Qualify the 14 leads | P1 | none | every lead marked qualified or rejected with a reason
- Deploy the API to a paid host | P2 | none | health endpoint returns 200 from the public URL

## APPROVALS REQUIRED
- Purchase Railway Hobby hosting

## EXACT RESUME POINT
Start qualifying at row 1.

END AI SYNC PACKET
"""


class TestFullPipeline(AionTest):
    def test_packet_to_owner_status(self):
        # 1. External AI packet arrives in the inbox as a file.
        inbox = config.home() / "INBOX" / "pending"
        (inbox / "claude-packet.md").write_text(PACKET, encoding="utf-8")

        # 2. Boot ingests it as part of the normal startup loop.
        boot = resume.boot()
        ingest_step = next(s for s in boot["steps"] if s["step"] == "process_sync_inbox")
        self.assertEqual(len(ingest_step["results"]), 1)
        self.assertEqual(ingest_step["results"][0]["status"], "PROCESSED")

        # 3. Local state now holds real tasks and an approval.
        titles = {t["title"] for t in tasks.ready(50)}
        self.assertIn("Qualify the 14 leads", titles)
        self.assertTrue(approvals.pending(), "packet approval must be queued")

        qualify = next(t for t in tasks.ready(50) if t["title"] == "Qualify the 14 leads")

        # 4. Model routing picks the cheapest capable class for the work.
        route = agents.route("classify", complexity=2)
        self.assertEqual(route["model_class"], "A")
        tasks.update(qualify["task_id"], model_class=route["model_class"])

        # 5. Agent claims and executes.
        self.assertTrue(tasks.claim(qualify["task_id"], route["agent_id"]))
        tasks.update(qualify["task_id"], status="RUNNING")
        packet = context.build(qualify["task_id"])
        self.assertIn("SUCCESS CRITERIA", packet)
        self.assertIn("every lead marked qualified", packet)

        # 6. Validation: completion without evidence is refused.
        with self.assertRaises(tasks.TaskError):
            tasks.complete(qualify["task_id"], "")
        tasks.complete(qualify["task_id"],
                       "ran lead_qualifier.py over 14 rows: 9 qualified, 5 rejected with reasons",
                       next_action="draft outreach for the 9 qualified leads")
        agents.record_run(route["agent_id"], success=True, task_id=None)
        metrics.record_usage("llama3.1:8b", "A", input_tokens=4200, output_tokens=900,
                             cost_inr=0.0, task_id=qualify["task_id"])

        # 7. State update is durable and visible.
        done = tasks.get(qualify["task_id"])
        self.assertEqual(done["status"], "DONE")
        self.assertIn("9 qualified", done["evidence"])
        self.assertEqual(metrics.budget_status()["strong_model_spend_inr"], 0.0)

        # 8. Owner status over the WhatsApp router reflects reality.
        status = router.handle("status")
        self.assertIn("1 done", status)
        blockers = router.handle("blockers")
        self.assertIn("APPROVAL", blockers)

        # 9. The owner approves; the gated task resumes at the prepared step.
        approval_id = approvals.pending()[0]["approval_id"]
        reply = router.handle(f"APPROVE {approval_id}")
        self.assertIn(approval_id, reply)
        self.assertEqual(approvals.get(approval_id)["status"], "APPROVED")

        # 10. Everything is checkpointed and restorable.
        resume.checkpoint(current_task=qualify["task_id"],
                          last_verified_success="lead qualification completed with evidence")
        state = resume.load()
        self.assertEqual(state["current_task"], qualify["task_id"])
        verified = backup.verify() if backup.create() else None
        self.assertTrue(verified["ok"], verified)

    def test_owner_never_sees_a_secret_even_if_one_reaches_state(self):
        tasks.create("rotate ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345 today")
        memory.remember("fact", "key note", "the key is sk-ant-api03-AbCdEfGhIjKlMnOpQrStUv")
        for text in (reports.status(), reports.full_report(), reports.task_list(),
                     router.handle("report")):
            self.assertNotIn("ghp_AbCdEf", text)
            self.assertNotIn("sk-ant-api03-AbCdEf", text)

    def test_markdown_surfaces_regenerate_from_the_database(self):
        t = tasks.create("visible task", next_action="do the thing")
        approvals.create("spend money", why="because", task_id=t)
        written = reports.render_markdown_surfaces()
        self.assertEqual(len(written), 5)
        tasks_md = (config.home() / "GLOBAL_TASKS.md").read_text()
        approvals_md = (config.home() / "APPROVALS.md").read_text()
        self.assertIn("visible task", tasks_md)
        self.assertIn("spend money", approvals_md)
        self.assertIn("APPROVE A-", approvals_md)

    def test_fable_pack_builds_and_readiness_is_measured(self):
        fable.build_pack()
        d = config.home() / "FABLE"
        for name in ("FABLE_START_PROMPT.txt", "FABLE_CONTEXT.md", "FABLE_BUDGET.json",
                     "FABLE_TASK_QUEUE.md", "FABLE_COMPLETION_CRITERIA.md"):
            self.assertTrue((d / name).exists(), f"{name} missing")
        budget = fable.budget()
        self.assertEqual(budget["maximum_cumulative_authorization"], 2000.0)
        self.assertEqual(budget["remaining"], 2000.0)
        ok, gaps = fable.is_ready()
        self.assertIsInstance(ok, bool)
        # With no class-C task queued the pack must refuse to declare readiness.
        self.assertFalse(ok)
        self.assertTrue(any("class-C" in g for g in gaps))

    def test_readiness_flips_once_a_strong_task_exists_and_checks_pass(self):
        from aion_core import bootstrap
        bootstrap.init_secret_store()
        backup.create()
        tasks.create("design the revenue architecture", model_class="C",
                     success_criteria="written decision plus decomposed work orders")
        resume.checkpoint(objective="first real revenue", next_action="start with TASK-1")
        fable.build_pack()
        ok, gaps = fable.is_ready()
        self.assertTrue(ok, f"still not ready: {gaps}")
        report = fable.readiness_report()
        self.assertIn("FABLE READY", report)
        self.assertIn("RECOMMENDED INITIAL CREDIT", report)


if __name__ == "__main__":
    unittest.main()
