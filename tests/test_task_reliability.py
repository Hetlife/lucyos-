"""Reliability regressions against the canonical task ledger (no second queue)."""
import json
import subprocess
from unittest.mock import patch

from aion_core import approvals, config, db, packets, reports, tasks, util, worker
from tests.base import AionTest


class TestLifecycle(AionTest):
    def test_legacy_done_accepts_only_linked_pending_approval(self):
        task = tasks.create("prepared", status="RUNNING")
        tasks.complete(task, "preparation verified")
        for fields in ({"status": "NEEDS_APPROVAL"},
                       {"status": "NEEDS_APPROVAL", "approval_id": "missing"}):
            with self.assertRaises(tasks.TaskError):
                tasks.update(task, **fields)
        approval = approvals.create("execute prepared action", task_id=task)
        self.assertEqual(tasks.get(task)["status"], "NEEDS_APPROVAL")
        self.assertIsNone(tasks.get(task)["completed_at"])
        self.assertEqual(tasks.get(task)["evidence"], "preparation verified")
        approvals.decide(approval, "APPROVED")
        self.assertEqual(tasks.get(task)["status"], "READY")
        with self.assertRaises(tasks.TaskError):
            tasks.update(task, status="DONE", evidence="old preparation")

    def test_direct_ready_done_is_invalid_even_with_evidence(self):
        task = tasks.create("not executed")
        before = dict(tasks.get(task))
        with self.assertRaisesRegex(tasks.TaskError, "READY->DONE"):
            tasks.update(task, status="DONE", evidence="executor says done")
        self.assertEqual(dict(tasks.get(task)), before)

    def test_running_done_requires_evidence_and_terminal_is_immutable(self):
        task = tasks.create("executed", status="RUNNING")
        with self.assertRaises(tasks.TaskError):
            tasks.update(task, status="DONE")
        tasks.complete(task, "independent validation passed")
        before = dict(tasks.get(task))
        tasks.complete(task, "independent validation passed")
        self.assertEqual(dict(tasks.get(task)), before)
        for status in ("RUNNING", "READY"):
            with self.assertRaises(tasks.TaskError):
                tasks.update(task, status=status)
        with self.assertRaises(tasks.TaskError):
            tasks.create("unproved import", status="DONE")

    def test_legacy_completion_reconciles_atomically_and_moves_resume(self):
        task = tasks.create("already performed")
        tasks.complete(task, "independent observation")
        self.assertEqual(tasks.get(task)["status"], "DONE")
        event = db.connect().execute("SELECT detail FROM events WHERE kind='task.reconcile' AND subject=?",
                                     (task,)).fetchone()
        self.assertEqual(event[0], "READY->NEEDS_REVIEW->DONE")

    def test_failed_reconciliation_preserves_original_record(self):
        dep = tasks.create("unmet dependency")
        task = tasks.create("queued", dependencies=dep)
        before = dict(tasks.get(task))
        with self.assertRaises(tasks.TaskError):
            tasks.complete(task, "proof")
        self.assertEqual(dict(tasks.get(task)), before)
        self.assertEqual(db.connect().execute("SELECT count(*) FROM events WHERE kind='task.reconcile'").fetchone()[0], 0)

    def test_owner_hold_cannot_be_detached_or_completed(self):
        task = tasks.create("owner work")
        approval = approvals.create("owner boundary", task_id=task)
        with self.assertRaises(tasks.TaskError):
            tasks.update(task, approval_id=None)
        with self.assertRaises(tasks.TaskError):
            tasks.update(task, status="READY", approval_id=None)
        with self.assertRaises(tasks.TaskError):
            tasks.complete(task, "claims implementation exists")
        approvals.decide(approval, "APPROVED")
        self.assertTrue(tasks.claim(task, "worker"))

    def test_claim_cannot_bypass_dependencies_or_blockers(self):
        dep = tasks.create("first")
        task = tasks.create("second", dependencies=dep)
        self.assertFalse(tasks.claim(task, "worker"))
        tasks.complete(dep, "proof")
        tasks.update(task, blockers="architecture review required")
        self.assertFalse(tasks.claim(task, "worker"))

    def test_completion_packet_is_a_claim_not_runtime_done(self):
        task = tasks.create("implemented task")
        packet = f"SOURCE: test\nPACKET_ID: closure-packet\n## TASKS COMPLETED\n- {task}: done\n"
        self.assertEqual(packets.ingest(packet)["status"], "PROCESSED")
        self.assertEqual(packets.ingest(packet)["status"], "DUPLICATE")
        self.assertEqual(tasks.get(task)["status"], "READY")

    def test_old_evidence_cannot_silently_be_reused_for_done(self):
        task = tasks.create("new attempt", status="RUNNING", evidence="old attempt output")
        with self.assertRaises(tasks.TaskError):
            tasks.update(task, status="DONE")

    def test_complete_cannot_clear_architecture_hold(self):
        task = tasks.create("review needed", status="BLOCKED", blockers="architecture review required")
        with self.assertRaises(tasks.TaskError):
            tasks.complete(task, "tests pass")
        self.assertEqual(tasks.get(task)["status"], "BLOCKED")


class TestProgress(AionTest):
    def active(self):
        task = tasks.create("long-running")
        tasks.claim(task, "worker")
        tasks.update(task, status="RUNNING", started_at=util.ago(seconds=3600),
                     claimed_at=util.ago(seconds=3600))
        return task

    def test_heartbeat_without_evidence_stalls_but_does_not_release_live_owner(self):
        task = self.active()
        self.assertTrue(tasks.heartbeat(task, "worker"))
        self.assertFalse(tasks.heartbeat(task, "other"))
        self.assertTrue(tasks.progress(task, 60)["stalled"])
        self.assertIsNone(tasks.progress(task)["last_evidence_at"])
        self.assertEqual(tasks.release_stale(60), [])
        self.assertIn("Stalled without new evidence: 1", reports.status())

    def test_long_running_heartbeat_with_recent_measurement_is_not_stalled(self):
        task = self.active()
        tasks.record_evidence(task, "validation completed 100 of 1000 cases",
                              kind="validation", owner_agent="worker")
        self.assertTrue(tasks.heartbeat(task, "worker"))
        self.assertFalse(tasks.progress(task, 60)["stalled"])
        self.assertEqual(tasks.release_stale(60), [])

    def test_only_new_observations_reset_evidence_window(self):
        task = self.active()
        tasks.record_evidence(task, "artifact sha256 changed", kind="artifact", owner_agent="worker")
        self.assertFalse(tasks.progress(task, 60)["stalled"])
        conn = db.connect()
        conn.execute("UPDATE events SET at=? WHERE subject=? AND kind='task.evidence'",
                     (util.ago(seconds=600), task))
        conn.commit()
        tasks.record_evidence(task, "artifact sha256 changed", kind="artifact", owner_agent="worker")
        self.assertTrue(tasks.progress(task, 60)["stalled"])
        with self.assertRaises(tasks.TaskError):
            tasks.record_evidence(task, "alive", kind="heartbeat", owner_agent="worker")
        with self.assertRaises(tasks.TaskError):
            tasks.record_evidence(task, "test proof", kind="validation", owner_agent="other")

    def test_unverified_model_text_does_not_count_as_progress(self):
        task = self.active()
        tasks.update(task, evidence="model: still working")
        self.assertTrue(tasks.progress(task, 60)["stalled"])

    def test_repeated_dead_owners_are_bounded_and_new_claim_resets_start(self):
        task = tasks.create("abandoned")
        for attempt in range(config.MAX_TASK_RETRIES):
            self.assertTrue(tasks.claim(task, "worker"))
            self.assertIsNone(tasks.get(task)["started_at"])
            self.assertEqual(tasks.release_stale(-1), [task])
        self.assertEqual(tasks.get(task)["status"], "BLOCKED")
        self.assertFalse(tasks.claim(task, "worker"))


class TestRecovery(AionTest):
    def test_classification_and_mapping(self):
        cases = (
            ("provider schema validation error", "PROVIDER_SCHEMA_ERROR", "NEEDS_REVIEW"),
            ("worker process died", "WORKER_PROCESS_DIED", "READY"),
            ("heartbeat lost", "HEARTBEAT_LOST", "READY"),
            ("no route to eligible executor", "NO_ROUTE", "WAITING"),
            ("unrecognized failure", "UNKNOWN", "READY"),
            ("HTTP 429 quota exceeded", "MODEL_QUOTA_EXHAUSTED", "WAITING"),
            ("timed out after 300s", "PROVIDER_TIMEOUT", "READY"),
            ("context window exhausted", "CONTEXT_OVERFLOW", "NEEDS_REVIEW"),
            ("app-server connection reset", "APP_SERVER_CLOSED", "READY"),
            ("validation failed: tests failed", "TEST_FAILURE", "READY"),
            ("architecture gate denied after timeout", "ARCHITECTURE_GATE_FAILURE", "NEEDS_REVIEW"),
            ("owner approval required after quota failure", "OWNER_APPROVAL_REQUIRED", "NEEDS_APPROVAL"),
        )
        for message, kind, status in cases:
            with self.subTest(kind=kind):
                task = tasks.create(kind, status="RUNNING")
                self.assertEqual(tasks.classify_failure(message), kind)
                self.assertEqual(tasks.fail(task, message), status)
                row = tasks.get(task)
                self.assertEqual(row["retry_count"], int(tasks.RECOVERY[kind][2]))
                event = db.connect().execute("SELECT detail FROM events WHERE subject=? AND kind='task.failure'",
                                             (task,)).fetchone()
                self.assertEqual(json.loads(event[0])["kind"], kind)

    def test_bounded_retry_for_transient_and_test_failures(self):
        for message, policy in tasks.RECOVERY.items():
            self.assertEqual(tasks.classify_failure(message), message)
            self.assertTrue(policy[1])
            if not policy[2]:
                self.assertEqual(tasks.recovery_for(message, 100)["status"], policy[0])
                continue
            task = tasks.create(message)
            for _ in range(config.MAX_TASK_RETRIES - 1):
                self.assertEqual(tasks.fail(task, message), "READY")
            self.assertEqual(tasks.fail(task, message), "BLOCKED")
            self.assertNotIn(task, [r["task_id"] for r in tasks.ready()])
            self.assertEqual(tasks.fail(task, message), "BLOCKED")
            self.assertEqual(tasks.get(task)["retry_count"], config.MAX_TASK_RETRIES)

    def test_worker_consumes_mapping_without_new_execution_loop(self):
        task = tasks.create("quota limited", status="RUNNING")
        result = worker._fail(task, "B", "quota exceeded", None)
        self.assertEqual(result["status"], "WAITING")
        self.assertEqual(tasks.get(task)["retry_count"], 0)

    def test_owner_failure_resumes_only_after_recorded_approval(self):
        task = tasks.create("held execution", status="RUNNING")
        tasks.fail(task, "owner approval required")
        approval = approvals.create("authorize held execution", task_id=task)
        self.assertNotIn(task, [r["task_id"] for r in tasks.ready()])
        approvals.decide(approval, "APPROVED")
        self.assertIn(task, [r["task_id"] for r in tasks.ready()])
        self.assertTrue(tasks.claim(task, "worker"))

    def test_timeout_hold_does_not_masquerade_as_missing_executor(self):
        task = tasks.create("partial implementation", status="RUNNING", model_class="B")
        tasks.update(task, status="WAITING", blockers=tasks.EXECUTOR_WAIT_BLOCKERS["B"],
                     last_error="executor window ended (timed out after 900s)")
        self.assertEqual(tasks.requeue_available_executor_waits({"B"}), [])
        self.assertIn("reconcile", tasks.get(task)["blockers"])


class TestGitClosure(AionTest):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "implementation"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        (self.repo / "artifact").write_text("initial")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.task = tasks.create("already implemented", task_id="RELIABILITY-TEST",
                                 validation_command="test -f artifact", success_criteria="artifact exists")
        (self.repo / "artifact").write_text("implemented")
        self.git("add", ".")
        self.git("commit", "-qm", "Implement artifact\n\nTask-ID: RELIABILITY-TEST")
        self.commit = self.git("rev-parse", "HEAD")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                              text=True, check=True).stdout.strip()

    @staticmethod
    def passing(command, **kw):
        return {"ok": True, "code": 0, "cmd": command, "output": "independent checks passed"}

    @patch("aion_core.worker.run_command", side_effect=passing)
    def test_duplicate_closure_preserves_evidence_timestamp_and_events(self, run):
        self.assertTrue(tasks.close_implemented(self.task, self.commit, repo=self.repo))
        before = dict(tasks.get(self.task))
        count = db.connect().execute("SELECT count(*) FROM events").fetchone()[0]
        self.assertFalse(tasks.close_implemented(self.task, self.commit, repo=self.repo))
        self.assertEqual(dict(tasks.get(self.task)), before)
        self.assertEqual(db.connect().execute("SELECT count(*) FROM events").fetchone()[0], count)
        self.assertEqual(run.call_count, 5)
        evidence = json.loads(before["evidence"])
        self.assertEqual(evidence["commit"], self.commit)
        self.assertEqual(set(evidence["checks"]), {"validation", "scan", "portability", "authority", "anti_dup"})
        self.assertNotIn("exec_command", str(run.call_args_list))
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, "0" * 40, repo=self.repo)

    @patch("aion_core.worker.run_command", side_effect=passing)
    def test_waiting_implemented_task_reconciles_without_claim_or_reexecution(self, run):
        tasks.update(self.task, status="WAITING", blockers=tasks.EXECUTOR_WAIT_BLOCKERS["B"])
        self.assertTrue(tasks.close_implemented(self.task, self.commit, repo=self.repo))
        self.assertEqual(tasks.get(self.task)["status"], "DONE")
        self.assertIsNone(tasks.get(self.task)["claimed_at"])

    def test_missing_validation_dirty_tree_wrong_commit_and_active_owner_refused(self):
        tasks.update(self.task, validation_command="")
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)
        tasks.update(self.task, validation_command="test -f artifact")
        (self.repo / "untracked").write_text("not validated")
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)
        (self.repo / "untracked").unlink()
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, "0" * 40, repo=self.repo)
        tasks.claim(self.task, "worker")
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)

    @patch("aion_core.worker.run_command")
    def test_each_required_gate_failure_refuses_done(self, run):
        for failing in range(5):
            calls = [self.passing("check") for _ in range(5)]
            calls[failing] = {"ok": False, "code": 1, "output": "failed gate"}
            run.side_effect = calls
            before = dict(tasks.get(self.task))
            with self.assertRaises(tasks.TaskError):
                tasks.close_implemented(self.task, self.commit, repo=self.repo)
            self.assertEqual(dict(tasks.get(self.task)), before)

    @patch("aion_core.worker.run_command")
    def test_task_change_during_validation_cannot_overwrite_new_owner(self, run):
        def change(command, **kw):
            tasks.claim(self.task, "new-owner")
            return self.passing(command)
        run.side_effect = change
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)
        self.assertEqual(tasks.get(self.task)["owner_agent"], "new-owner")
        self.assertEqual(tasks.get(self.task)["status"], "CLAIMED")

    def test_architecture_and_owner_holds_cannot_be_closed(self):
        tasks.update(self.task, status="BLOCKED", blockers="architecture review required")
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)
        tasks.update(self.task, status="NEEDS_APPROVAL")
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)


    @patch("aion_core.worker.run_command")
    def test_real_independent_validation_failure_preserves_task(self, run):
        # Real local validator; gate success cannot rescue failed task proof.
        run.side_effect = lambda command, **kw: {
            "ok": False, "code": subprocess.run(["test", "-f", "missing-artifact"],
                                                cwd=self.repo).returncode,
            "output": "required artifact missing"}
        with self.assertRaises(tasks.TaskError):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)
        self.assertEqual(tasks.get(self.task)["status"], "READY")
        self.assertEqual(run.call_count, 1)

    @patch("aion_core.worker.run_command")
    def test_stale_process_commit_cannot_close_newer_committed_tree(self, run):
        self.git("commit", "--allow-empty", "-qm", "New work\n\nTask-ID: RELIABILITY-TEST")
        with self.assertRaisesRegex(tasks.TaskError, "exact clean committed tree"):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)
        run.assert_not_called()
        self.assertEqual(tasks.get(self.task)["status"], "READY")

    def test_commit_for_another_task_is_not_closure_proof(self):
        self.git("commit", "--allow-empty", "-qm", "unrelated change")
        commit = self.git("rev-parse", "HEAD")
        with self.assertRaisesRegex(tasks.TaskError, "does not identify"):
            tasks.close_implemented(self.task, commit, repo=self.repo)

    @patch("aion_core.worker.run_command")
    def test_tree_change_during_validation_refuses_closure(self, run):
        def dirty(command, **kw):
            (self.repo / "artifact").write_text("changed while checking")
            return self.passing(command)
        run.side_effect = dirty
        with self.assertRaisesRegex(tasks.TaskError, "tree changed"):
            tasks.close_implemented(self.task, self.commit, repo=self.repo)
        self.assertEqual(tasks.get(self.task)["status"], "READY")
