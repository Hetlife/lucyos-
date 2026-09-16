from datetime import datetime, timedelta, timezone

from tests.base import AionTest
from aion_core import db, learnrepo, metrics

UTC = timezone.utc


class TestLearnRepoQueueHealth(AionTest):
    def setUp(self):
        super().setUp()
        learnrepo.ensure_defaults(datetime(2026, 9, 16, 1, 0, tzinfo=UTC))

    def test_task_schedule_run_are_separate(self):
        c = db.connect()
        self.assertEqual(c.execute("SELECT COUNT(*) FROM learnrepo_tasks").fetchone()[0], 3)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM learnrepo_schedules").fetchone()[0], 3)
        run_id = learnrepo.acquire("LR-SCHED-NIGHTLY", "worker-a", datetime(2026, 9, 16, 1, 0, tzinfo=UTC))
        self.assertTrue(run_id)
        self.assertEqual(c.execute("SELECT task_type FROM learnrepo_runs WHERE run_id=?", (run_id,)).fetchone()[0], "learnrepo.health.nightly")

    def test_schedule_calculation(self):
        t = datetime(2026, 9, 16, 4, 0, tzinfo=UTC)
        self.assertEqual(learnrepo.next_run("HOURLY", t), t + timedelta(hours=1))
        self.assertEqual(learnrepo.next_run("WEEKLY", t), t + timedelta(days=7))
        self.assertEqual(learnrepo.next_run("MONTHLY", t).month, 10)
        self.assertEqual(learnrepo.next_run("QUARTERLY", t).month, 10)
        self.assertIsNone(learnrepo.next_run("MANUAL", t))

    def test_grace_late_missed_and_timeout(self):
        t = datetime(2026, 9, 16, 1, 0, tzinfo=UTC)
        run_id = learnrepo.acquire("LR-SCHED-NIGHTLY", "worker-a", t)
        self.assertEqual(learnrepo.classify_timing(run_id, t + timedelta(minutes=5)), "LATE")
        self.assertEqual(learnrepo.classify_timing(run_id, t + timedelta(minutes=21)), "MISSED")
        db.connect().execute("UPDATE learnrepo_runs SET started_at=?, status='STARTED' WHERE run_id=?", (t.isoformat(), run_id)); db.connect().commit()
        self.assertEqual(learnrepo.classify_timing(run_id, t + timedelta(minutes=21)), "FAIL")

    def test_duplicate_run_prevention_and_stale_recovery(self):
        t = datetime(2026, 9, 16, 1, 0, tzinfo=UTC)
        first = learnrepo.acquire("LR-SCHED-NIGHTLY", "worker-a", t, lease_seconds=60)
        self.assertTrue(first)
        self.assertIsNone(learnrepo.acquire("LR-SCHED-NIGHTLY", "worker-b", t + timedelta(seconds=30)))
        recovered = learnrepo.recover_stale_leases(t + timedelta(seconds=61))
        self.assertIn(first, recovered)
        self.assertTrue(learnrepo.acquire("LR-SCHED-NIGHTLY", "worker-b", t + timedelta(seconds=61)))

    def test_healthy_overnight_makes_zero_ai_calls(self):
        t = datetime(2026, 9, 16, 1, 0, tzinfo=UTC)
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        result = learnrepo.run_due(mode="nightly", now=t)
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        self.assertEqual(result["ai_calls"], 0)
        self.assertEqual(before, after)
        self.assertEqual(result["api_escalations"], 0)
        self.assertEqual(result["success"], 1)

    def test_broken_contract_creates_one_deduplicated_api_work_required(self):
        c = db.connect()
        c.execute("UPDATE learnrepo_contracts SET validation_command='python3 -c raise SystemExit(2)' WHERE contract_id='LR-CONTRACT-MODULE'")
        c.commit()
        t = datetime(2026, 9, 16, 1, 0, tzinfo=UTC)
        run_id = learnrepo.acquire("LR-SCHED-NIGHTLY", "worker", t)
        r1 = learnrepo.execute_run(run_id, now=t)
        self.assertEqual(r1["api_escalations"], 1)
        esc = c.execute("SELECT * FROM learnrepo_escalations").fetchone()
        task = c.execute("SELECT * FROM tasks WHERE task_id=?", (esc["task_id"],)).fetchone()
        self.assertEqual(task["kind"], "learnrepo_api_work_required")
        self.assertEqual(task["model_class"], "C")
        check = {"level": 3, "name": "LR-CONTRACT-MODULE", "detail": "", "severity": "HIGH", "ok": False}
        # Same fingerprint updates occurrence count instead of duplicating task.
        eid = learnrepo.escalate(run_id, check)
        learnrepo.escalate(run_id, check)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM learnrepo_escalations WHERE escalation_id=?", (eid,)).fetchone()[0], 1)

    def test_offline_external_probe_is_degraded_not_api_work(self):
        def offline(_):
            raise OSError("network offline")
        checks = learnrepo.level4_external(offline)
        self.assertTrue(all(c["degraded"] for c in checks))
        self.assertTrue(all(not learnrepo._needs_reasoning(c) for c in checks))

    def test_forbidden_repair_is_refused(self):
        r = learnrepo.safe_repair("rewrite_production_logic")
        self.assertFalse(r["ok"])
        self.assertIn("not allowlisted", r["detail"])

    def test_persistence_after_reconnect(self):
        db.close()
        learnrepo.ensure_defaults()
        self.assertEqual(db.connect().execute("SELECT COUNT(*) FROM learnrepo_schedules").fetchone()[0], 3)


    def test_on_change_schedule_wakes_only_after_revision_change(self):
        c = db.connect()
        db.set_meta("learnrepo.last_git_head", "old-head")
        original = learnrepo._git_head
        try:
            learnrepo._git_head = lambda: "new-head"
            self.assertTrue(learnrepo.trigger_on_change_if_needed(datetime(2026, 9, 16, 2, 0, tzinfo=UTC)))
            row = c.execute("SELECT next_run_at FROM learnrepo_schedules WHERE schedule_id='LR-SCHED-ONCHANGE'").fetchone()
            self.assertIsNotNone(row[0])
            self.assertFalse(learnrepo.trigger_on_change_if_needed(datetime(2026, 9, 16, 2, 1, tzinfo=UTC)))
        finally:
            learnrepo._git_head = original

    def test_future_macos_adapter_and_quarantine_marker(self):
        self.assertEqual(learnrepo.os_adapter_name("Darwin"), "launchd")
        learnrepo.quarantine("candidate-x", "security evidence")
        self.assertIn("security", db.get_meta("learnrepo.quarantine.candidate-x"))
