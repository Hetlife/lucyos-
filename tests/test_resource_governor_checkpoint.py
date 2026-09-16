import json
import subprocess
import unittest
from pathlib import Path

from aion_core import tasks
from aion_core.resource_governor import admission, checkpoint, flags, schema
from tests.base import AionTest


class TestCheckpointBasics(AionTest):
    def test_save_and_load_round_trips(self):
        t = tasks.create("do a thing", model_class="B")
        doc = checkpoint.save(t, GOAL="do a thing", CURRENT_STAGE="halfway",
                              COMPLETED_STEPS=["read files"], PENDING_STEPS=["write tests"])
        loaded = checkpoint.load(t)
        self.assertEqual(loaded["CURRENT_STAGE"], "halfway")
        self.assertEqual(loaded["COMPLETED_STEPS"], ["read files"])
        self.assertEqual(loaded["CHECKPOINT_VERSION"], checkpoint.CHECKPOINT_VERSION)
        self.assertEqual(doc["TASK_ID"], t)

    def test_unknown_field_is_rejected(self):
        t = tasks.create("do a thing")
        with self.assertRaises(ValueError):
            checkpoint.save(t, NOT_A_REAL_FIELD="x")

    def test_secrets_are_redacted_out_of_a_checkpoint(self):
        t = tasks.create("do a thing")
        checkpoint.save(t, IMPORTANT_FINDINGS="key is sk-ant-api03-AbCdEfGhIjKlMnOpQrStUv")
        loaded = checkpoint.load(t)
        self.assertNotIn("sk-ant-api03-AbCdEf", loaded["IMPORTANT_FINDINGS"])

    def test_corrupted_checkpoint_falls_back_to_last_known_good(self):
        t = tasks.create("do a thing")
        checkpoint.save(t, CURRENT_STAGE="good version")
        checkpoint.save(t, CURRENT_STAGE="second good version")  # first becomes .bak
        path = checkpoint._path(t)
        path.write_text("{not valid json at all", encoding="utf-8")
        loaded = checkpoint.load(t)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["CURRENT_STAGE"], "good version")  # the .bak, not garbage

    def test_missing_checkpoint_is_none_not_an_error(self):
        self.assertIsNone(checkpoint.load("TASK-DOES-NOT-EXIST"))


class TestDeferAndResume(AionTest):
    def setUp(self):
        super().setUp()
        flags.set_flag("resource_governor.auto_defer", True)
        flags.set_flag("resource_governor.auto_resume", True)

    def test_mark_waiting_for_resource_uses_the_existing_waiting_status(self):
        t = tasks.create("write some code", model_class="B")
        checkpoint.mark_waiting_for_resource(t, resource="claude", reasoning="capacity exhausted")
        row = tasks.get(t)
        self.assertEqual(row["status"], "WAITING")
        self.assertTrue(row["blockers"].startswith(checkpoint.MARKER_PREFIX))
        self.assertIn(t, [r["task_id"] for r in checkpoint.waiting_tasks()])

    def test_resume_eligible_when_capacity_is_back_to_normal(self):
        t = tasks.create("write some code", model_class="B")
        checkpoint.mark_waiting_for_resource(t, resource="claude", reasoning="was exhausted")

        good_snap = {
            "providers": {"claude": {**schema.empty_resource("claude", confidence="OFFICIAL_CURRENT"),
                                     "state": "NORMAL", "quota": {"remaining_pct": 70.0}}},
            "local": {"available": False},
        }
        import aion_core.resource_governor.observability as obs
        orig = obs.snapshot
        obs.snapshot = lambda persist=False: good_snap
        try:
            result = checkpoint.resume_all()
        finally:
            obs.snapshot = orig
        self.assertIn(t, result["resumed"])
        self.assertEqual(tasks.get(t)["status"], "READY")

    def test_does_not_blindly_resume_if_repo_head_changed(self):
        t = tasks.create("write some code", model_class="B")
        checkpoint.mark_waiting_for_resource(t, resource="claude", reasoning="was exhausted")
        doc = checkpoint.load(t)
        doc["_repo_signature"] = {"head": "deadbeef" * 5, "dirty": 0}
        from aion_core import util
        util.write_json(checkpoint._path(t), doc)

        result = checkpoint.resume_task(t)
        self.assertFalse(result["eligible"])
        self.assertIn("repository", result["reason"])
        self.assertEqual(tasks.get(t)["status"], "WAITING")

    def test_missing_checkpoint_is_not_silently_resumed(self):
        t = tasks.create("write some code", model_class="B")
        tasks.update(t, status="WAITING", blockers=f"{checkpoint.MARKER_PREFIX} claude constrained")
        result = checkpoint.resume_task(t)
        self.assertFalse(result["eligible"])
        self.assertIn("no valid checkpoint", result["reason"])

    def test_resume_all_handles_multiple_concurrent_waiting_tasks(self):
        ids = [tasks.create(f"task {i}", model_class="B") for i in range(3)]
        for tid in ids:
            checkpoint.mark_waiting_for_resource(tid, resource="claude", reasoning="exhausted")
        result = checkpoint.resume_eligible(force=True)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
