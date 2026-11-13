import json
from unittest.mock import patch

from tests.base import AionTest
from aion_core import approvals, db, security, tasks, worker
from aion_core.recall import context_compiler


class ContextWorkerIntegrationTest(AionTest):
    def _task(self, *, project="LucyOS", title="Compile worker context"):
        return tasks.create(
            title, project=project, status="READY", model_class="A", kind="code",
            description="Use bounded local evidence before execution",
            validation_command="test -d .", success_criteria="context reaches worker")

    def test_fresh_task_receives_context_automatically(self):
        task_id = self._task()
        captured = {}

        def fake_ollama(prompt, model=None):
            captured["prompt"] = prompt
            return {"ok": True, "output": "implemented", "model": "fixture"}

        with patch("aion_core.worker.ollama_available", return_value=True), \
                patch("aion_core.worker.run_ollama", side_effect=fake_ollama):
            result = worker.work(max_tasks=1)

        self.assertEqual(result["done"], 1)
        self.assertIn("# VERIFIED TASK-SPECIFIC CONTEXT", captured["prompt"])
        self.assertIn(task_id, captured["prompt"])
        packet = json.loads((self.tmp / "context/current/CURRENT_CONTEXT.json").read_text())
        self.assertEqual(packet["task_id"], task_id)

    def test_deterministic_task_runs_command_without_compiling_context(self):
        task_id = tasks.create(
            "Run bounded local check", project="LucyOS", status="READY",
            model_class="DET", kind="verify", exec_command="echo checked",
            validation_command="test -d .", success_criteria="command is verified")

        result = worker.work(max_tasks=1)

        self.assertEqual(result["done"], 1)
        self.assertFalse((self.tmp / "context/current/CURRENT_CONTEXT.json").exists())
        self.assertIn("ran `echo checked`", tasks.get(task_id)["evidence"])

    def test_cached_task_reuses_context_and_state_change_refreshes_it(self):
        task_id = self._task()
        task = tasks.get(task_id)
        first = worker.prepare_task_context(task)
        second = worker.prepare_task_context(task)
        self.assertEqual(first["status"], "BUILT")
        self.assertEqual(second["status"], "CACHE_HIT")
        tasks.update(task_id, blockers="owner decision pending", status="BLOCKED")
        refreshed = worker.prepare_task_context(tasks.get(task_id))
        self.assertEqual(refreshed["status"], "BUILT")
        self.assertNotEqual(first["source_revision"], refreshed["source_revision"])
        self.assertIn("owner decision pending", refreshed["markdown"])

    def test_owner_gate_is_visible_and_unrelated_project_is_excluded(self):
        task_id = self._task()
        approvals.create("Approve protected merge", project="LucyOS",
                         why="Main is protected", owner_action="Review exact SHA")
        tasks.create("Private unrelated roadmap", project="OtherProject", status="BLOCKED",
                     blockers="unrelated blocker")
        prepared = worker.prepare_task_context(tasks.get(task_id))
        self.assertIn("Approve protected merge", prepared["markdown"])
        self.assertNotIn("Private unrelated roadmap", prepared["markdown"])

    @patch("aion_core.worker._do_work")
    @patch("aion_core.worker.prepare_task_context")
    def test_compilation_failure_blocks_before_worker_start(self, prepare, do_work):
        prepare.side_effect = context_compiler.ContextCompilerError("fixture corruption")
        task_id = self._task()

        result = worker.work(max_tasks=1)

        row = tasks.get(task_id)
        self.assertEqual(result["results"][0]["status"], "BLOCKED")
        self.assertFalse(result["results"][0]["worker_started"])
        self.assertEqual(row["status"], "BLOCKED")
        self.assertIsNone(row["owner_agent"])
        self.assertIn("CONTEXT_COMPILATION_FAILED", row["blockers"])
        do_work.assert_not_called()

    def test_disabled_feature_flag_holds_execution_fail_closed(self):
        task_id = self._task()
        db.set_meta(worker.CONTEXT_COMPILER_FLAG, "0")

        result = worker.work(max_tasks=1)

        self.assertEqual(result["results"][0]["status"], "BLOCKED")
        self.assertEqual(tasks.get(task_id)["status"], "BLOCKED")
        self.assertIn("disabled", tasks.get(task_id)["last_error"])

    def test_det_task_runs_with_compiler_disabled(self):
        # TR-1-06: deterministic steps never need the model-context compiler.
        task_id = tasks.create("echo", project="LucyOS", status="READY", model_class="DET",
                               kind="verify", exec_command="echo checked", validation_command="test -d .",
                               success_criteria="command is verified")
        db.set_meta(worker.CONTEXT_COMPILER_FLAG, "0")
        with patch("aion_core.worker.prepare_task_context") as prep:
            result = worker.work(max_tasks=1)
        prep.assert_not_called()
        self.assertEqual(result["results"][0]["status"], "DONE", result)
        self.assertEqual(tasks.get(task_id)["status"], "DONE")

    def test_model_task_still_blocked_with_compiler_disabled(self):
        task_id = self._task()
        db.set_meta(worker.CONTEXT_COMPILER_FLAG, "0")
        result = worker.work(max_tasks=1)
        self.assertFalse(result["results"][0]["worker_started"])
        self.assertEqual(tasks.get(task_id)["status"], "BLOCKED")

    def test_empty_queue_opens_no_session(self):
        # The timer fires every 10 minutes; an idle run must leave no trace.
        count = lambda: db.connect().execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        before = count()
        result = worker.work(max_tasks=1)
        self.assertEqual(result["stopped"], "no ready task")
        self.assertEqual(result["attempted"], 0)
        self.assertEqual(count(), before)

    def test_prompt_security_is_checked_again_at_worker_boundary(self):
        task_id = self._task()
        prepared = worker.prepare_task_context(tasks.get(task_id))
        prepared["markdown"] += "\nsecret_key=" + "A" * 30
        with self.assertRaises(security.SecretLeak):
            worker._worker_prompt(tasks.get(task_id), prepared)


if __name__ == "__main__":
    import unittest
    unittest.main()
