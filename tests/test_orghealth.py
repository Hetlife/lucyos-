"""Org-wide health generalization (TASK-89B0270A stage M1).

Contract under test:
- default (flag off): the LearnRepo pilot is byte-for-byte unchanged;
- flag on: LucyOS org schedules/contracts seed and run deterministically with
  zero model calls, reusing the pilot tables and escalation path;
- optional components degrade instead of escalating;
- required-component failures escalate exactly once per fingerprint;
- rollback ("orghealth off") disables org schedules and nothing else.
"""
import json
from datetime import datetime, timezone

from tests.base import AionTest
from aion_core import db, learnrepo

UTC = timezone.utc
T0 = datetime(2026, 9, 26, 1, 0, tzinfo=UTC)


class TestOrgHealthDisabledByDefault(AionTest):
    def test_no_org_rows_until_flag_on(self):
        learnrepo.ensure_defaults(T0)
        c = db.connect()
        self.assertEqual(
            c.execute("SELECT COUNT(*) FROM learnrepo_tasks WHERE component='LucyOS'").fetchone()[0], 0)
        self.assertEqual(
            c.execute("SELECT COUNT(*) FROM learnrepo_schedules WHERE component='LucyOS'").fetchone()[0], 0)
        self.assertFalse(learnrepo.org_enabled())
        # pilot unchanged
        self.assertEqual(c.execute("SELECT COUNT(*) FROM learnrepo_tasks").fetchone()[0], 3)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM learnrepo_schedules").fetchone()[0], 3)

    def test_component_columns_default_to_pilot(self):
        learnrepo.ensure_defaults(T0)
        c = db.connect()
        for table in ("learnrepo_tasks", "learnrepo_schedules", "learnrepo_contracts"):
            rows = c.execute(f"SELECT DISTINCT component FROM {table}").fetchall()
            self.assertEqual([r[0] for r in rows], ["LearnRepo"], table)


class TestOrgHealthEnabled(AionTest):
    def setUp(self):
        super().setUp()
        # a healthy temp brain: backup archive present, secrets file 0600
        backups = learnrepo.config.home() / "BACKUPS"
        backups.mkdir(parents=True, exist_ok=True)
        (backups / "aion-backup-20260926T000000+0000.tar.gz").write_bytes(b"")
        secrets = learnrepo.config.home() / "private_state" / "secrets.env"
        secrets.parent.mkdir(parents=True, exist_ok=True)
        secrets.write_text("")
        secrets.chmod(0o600)
        self.result = learnrepo.set_org_enabled(True, T0)
        self.assertTrue(self.result["ok"])

    def test_flag_and_seeds(self):
        self.assertTrue(learnrepo.org_enabled())
        c = db.connect()
        task_types = [r[0] for r in c.execute(
            "SELECT task_type FROM learnrepo_tasks WHERE component='LucyOS' ORDER BY task_type")]
        self.assertEqual(task_types, ["lucyos.health.nightly", "lucyos.health.on_change"])
        schedules = [r[0] for r in c.execute(
            "SELECT schedule_id FROM learnrepo_schedules WHERE component='LucyOS' ORDER BY schedule_id")]
        self.assertEqual(schedules, ["LH-SCHED-NIGHTLY", "LH-SCHED-ONCHANGE"])
        contracts = c.execute(
            "SELECT COUNT(*) FROM learnrepo_contracts WHERE component='LucyOS'").fetchone()[0]
        self.assertGreaterEqual(contracts, 3)

    def test_org_run_is_deterministic_and_zero_ai(self):
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        result = learnrepo.run_due(mode="nightly", now=T0)
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        self.assertEqual(result["ai_calls"], 0)
        self.assertEqual(before, after)
        org_runs = [r for r in result["runs"] if r["component"] == "LucyOS"]
        self.assertEqual(len(org_runs), 1)
        run = org_runs[0]
        names = [c["name"] for c in run["checks"]]
        self.assertIn("org:database", names)
        self.assertIn("org:openclaw", names)
        self.assertIn("org:ollama", names)
        # optional components must degrade, never escalate
        for check in run["checks"]:
            if check["name"] in ("org:openclaw", "org:ollama") and not check["ok"]:
                self.assertTrue(check.get("degraded"), check)
        self.assertEqual(run["api_escalations"], 0)

    def test_required_failure_escalates_once_per_fingerprint(self):
        # simulate a hard failure of a required component check
        from aion_core import health
        original = health.check_backup
        health.check_backup = lambda: {"name": "backup", "ok": False,
                                       "detail": "simulated: no backup taken yet"}
        try:
            first = learnrepo.run_due(mode="nightly", now=T0)
            second = learnrepo.run_due(mode="nightly", now=T0)
        finally:
            health.check_backup = original
        self.assertGreaterEqual(first["api_escalations"], 1)
        self.assertEqual(second["api_escalations"], 0)  # deduplicated
        titles = [r[0] for r in db.connect().execute(
            "SELECT title FROM tasks WHERE kind='learnrepo_api_work_required'")]
        self.assertTrue(any(t.startswith("API_WORK_REQUIRED LucyOS:") for t in titles), titles)
        sources = [r[0] for r in db.connect().execute(
            "SELECT DISTINCT source FROM learnrepo_escalations")]
        self.assertIn("LucyOS", sources)

    def test_org_summary_file_written(self):
        learnrepo.run_due(mode="nightly", now=T0)
        path = learnrepo.config.home() / "state" / "LUCYOS_HEALTH.json"
        self.assertTrue(path.exists())
        summary = json.loads(path.read_text())
        self.assertEqual(summary["component"], "LucyOS")


class TestOrgHealthRollback(AionTest):
    def test_off_disables_only_org(self):
        learnrepo.set_org_enabled(True, T0)
        learnrepo.run_due(mode="nightly", now=T0)
        result = learnrepo.set_org_enabled(False, T0)
        self.assertTrue(result["ok"])
        self.assertFalse(learnrepo.org_enabled())
        c = db.connect()
        enabled = [r[0] for r in c.execute(
            "SELECT schedule_id FROM learnrepo_schedules WHERE enabled=1 ORDER BY schedule_id")]
        self.assertEqual(
            enabled, ["LR-SCHED-NIGHTLY", "LR-SCHED-ONCHANGE", "LR-SCHED-WEEKLY"])
        # pilot rows untouched, org rows retained but disabled
        pilot = c.execute(
            "SELECT COUNT(*) FROM learnrepo_schedules WHERE component='LearnRepo' AND enabled=1").fetchone()[0]
        self.assertEqual(pilot, 3)
        org_disabled = c.execute(
            "SELECT COUNT(*) FROM learnrepo_schedules WHERE component='LucyOS' AND enabled=0").fetchone()[0]
        self.assertEqual(org_disabled, 2)

    def test_status_includes_component_breakdown(self):
        learnrepo.set_org_enabled(True, T0)
        s = learnrepo.status()
        self.assertIn("components", s)
        self.assertIn("LucyOS", s["components"])
        self.assertIn("LearnRepo", s["components"])
        self.assertTrue(s["org_enabled"])
