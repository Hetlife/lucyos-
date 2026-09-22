from unittest import mock

from tests.base import AionTest
from aion_core import health


class TestSupervisorState(AionTest):
    def test_state_priority_is_health_then_errors_then_work(self):
        healthy = {"healthy": True}
        degraded = {"healthy": False}
        self.assertEqual(health.supervisor_state(degraded, {}, [], []), "DEGRADED")
        self.assertEqual(health.supervisor_state(healthy, {}, [], [object()]), "REPAIR_REQUIRED")
        self.assertEqual(health.supervisor_state(healthy, {"READY": 1}, [], []), "ACTIVE")
        self.assertEqual(health.supervisor_state(healthy, {}, [object()], []), "OWNER_ACTION")
        self.assertEqual(health.supervisor_state(healthy, {"WAITING": 1}, [], []), "WAITING")
        self.assertEqual(health.supervisor_state(healthy, {}, [], []), "IDLE")

    def test_next_action_prefers_live_failures_over_queue(self):
        ready = {"task_id": "TASK-ABC123"}
        self.assertIn("health --deep", health.supervisor_next_action(
            {"healthy": False}, {"READY": 1}, [], [], ready))
        self.assertIn("aion errors", health.supervisor_next_action(
            {"healthy": True}, {"READY": 1}, [], [object()], ready))
        self.assertIn("aion work --max 1", health.supervisor_next_action(
            {"healthy": True}, {"READY": 1}, [], [], ready))


class TestSupervisorSnapshot(AionTest):
    @mock.patch("aion_core.health.worker.capability_report")
    @mock.patch("aion_core.health.machine")
    @mock.patch("aion_core.health.check_git")
    @mock.patch("aion_core.health.run_all")
    def test_snapshot_is_deterministic_and_persists_compact_surfaces(
            self, run_all, check_git, machine, capability_report):
        run_all.return_value = {"healthy": True, "failing": [], "checks": []}
        check_git.return_value = {"name": "git", "ok": True,
                                  "detail": "branch test, 0 uncommitted paths"}
        machine.return_value = {"hostname": "test", "repo_commit": "abc123"}
        capability_report.return_value = {
            "ollama": True, "ollama_model": "small-local", "cloud_worker": True,
            "allowlisted_prefixes": 3, "paused": False, "safe_mode": False,
            "governor": "NORMAL", "skills": []}

        result = health.supervisor_snapshot()

        self.assertEqual(result["mode"], "DETERMINISTIC_NO_LLM")
        self.assertEqual(result["state"], "IDLE")
        self.assertEqual(result["memory"]["canonical"], "sqlite_fts5")
        self.assertEqual(result["routing_policy"], ["DET", "LOCAL", "BOUNDED_CLOUD"])
        self.assertTrue((self.tmp / "state" / "SUPERVISOR.json").is_file())
        text = (self.tmp / "SUPERVISOR.md").read_text()
        self.assertIn("AION SUPERVISOR", text)
        self.assertIn("DET first", text)

    def test_waiting_work_gets_live_retriage_bottleneck(self):
        text = health.supervisor_bottleneck(
            {"healthy": True}, {"WAITING": 2}, [], [], None)
        self.assertIn("re-triage against live evidence", text)

    def test_running_work_outranks_waiting_work(self):
        counts = {"RUNNING": 1, "WAITING": 2}
        bottleneck = health.supervisor_bottleneck(
            {"healthy": True}, counts, [], [], None)
        action = health.supervisor_next_action(
            {"healthy": True}, counts, [], [], None)
        self.assertIn("1 task(s) running", bottleneck)
        self.assertIn("continue current RUNNING task", action)
