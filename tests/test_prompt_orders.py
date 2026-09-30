import copy
import unittest
from unittest import mock

from aion_core import context as prompt_orders


def base(status="PENDING"):
    d = {
        "prompt_id": "PRM-20260924-HARMLESS-TEST",
        "title": "Harmless lifecycle proof",
        "created_at": "2026-09-24T12:00:00+00:00",
        "created_by": "owner",
        "project": "LucyOS",
        "objective": "Prove deterministic lifecycle",
        "source_context": [],
        "required_inputs": [],
        "execution_instructions": ["record a harmless deterministic marker"],
        "authority_limits": ["no main merge", "no secrets"],
        "success_criteria": ["receipt archived"],
        "expected_output": ["receipt"],
        "status": status,
        "linked_task_id": "",
        "linked_session_id": "",
        "starting_git_sha": "abc",
        "final_git_sha": "",
        "result_summary": "",
        "evidence": [],
        "archive_status": "NOT_ARCHIVED",
    }
    return d


class PromptOrderTests(unittest.TestCase):
    def test_startup_resumes_one_processing_and_does_not_pick_pending(self):
        s = prompt_orders.select_startup(
            [{"prompt_id": "PRM-OLD"}], [{"prompt_id": "PRM-NEW"}], requested_id="PRM-NEW"
        )
        self.assertEqual((s.action, s.prompt_id), ("RESUME", "PRM-OLD"))

    def test_multiple_processing_is_blocked(self):
        with self.assertRaises(prompt_orders.PromptOrderError):
            prompt_orders.select_startup(
                [{"prompt_id": "PRM-A"}, {"prompt_id": "PRM-B"}], []
            )

    @mock.patch("aion_core.context.sessions.summary", return_value={"session_id": "SES-1"})
    @mock.patch("aion_core.context.tasks.get", return_value={"task_id": "TASK-1"})
    def test_processing_requires_and_verifies_existing_links(self, _task, _session):
        out = prompt_orders.transition(base(), "PROCESSING", task_id="TASK-1", session_id="SES-1")
        self.assertEqual(out["status"], "PROCESSING")

    def test_completion_requires_evidence(self):
        d = base("PROCESSING")
        d.update(linked_task_id="TASK-1", linked_session_id="SES-1")
        with self.assertRaises(prompt_orders.PromptOrderError):
            prompt_orders.transition(d, "COMPLETED")

    def test_archive_requires_receipt_and_archived_cannot_rerun(self):
        d = base("COMPLETED")
        d.update(linked_task_id="TASK-1", linked_session_id="SES-1", result_summary="ok", evidence=["marker"])
        with self.assertRaises(prompt_orders.PromptOrderError):
            prompt_orders.transition(d, "ARCHIVED")
        receipt = prompt_orders.build_receipt(d, tests=["ok"], outputs=["marker"], unresolved_blockers=[], resume_pointer="none")
        archived = prompt_orders.transition(d, "ARCHIVED", receipt=receipt)
        self.assertEqual(archived["archive_status"], "ARCHIVED")
        with self.assertRaises(prompt_orders.PromptOrderError):
            prompt_orders.transition(archived, "PROCESSING", task_id="TASK-1", session_id="SES-1")

    def test_resume_is_stable_after_interruption(self):
        processing = [{"prompt_id": "PRM-20260924-HARMLESS-TEST"}]
        first = prompt_orders.select_startup(processing, [])
        second = prompt_orders.select_startup(copy.deepcopy(processing), [])
        self.assertEqual(first, second)

    def test_template_shape_is_valid(self):
        self.assertEqual(prompt_orders.validate_work_order(base()), [])


if __name__ == "__main__":
    unittest.main()
