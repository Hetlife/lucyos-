from tests.base import AionTest
from aion_core import db, health, skills, worker


class TestSkillRegistry(AionTest):
    def test_defaults_live_in_canonical_sqlite(self):
        rows = skills.all_skills()
        self.assertGreaterEqual(len(rows), 9)
        self.assertEqual(db.connect().execute("SELECT COUNT(*) FROM skills").fetchone()[0], len(rows))
        self.assertIsNotNone(skills.get("core.state"))

    def test_registration_is_idempotent_and_strict(self):
        skills.register(skill_id="test.echo", name="Echo", capabilities="echo,echo",
                        executor_classes="DET", platforms="linux,linux")
        skills.register(skill_id="test.echo", name="Echo v2", capabilities="echo",
                        executor_classes="DET")
        self.assertEqual(skills.get("test.echo")["name"], "Echo v2")
        with self.assertRaises(skills.SkillError):
            skills.register(skill_id="BAD ID", name="bad")
        with self.assertRaises(skills.SkillError):
            skills.register(skill_id="test.badclass", name="bad", executor_classes="Z")

    def test_owner_disable_survives_default_seed(self):
        skills.set_enabled("ai.cloud", False)
        skills.ensure_defaults()
        self.assertEqual(skills.get("ai.cloud")["enabled"], 0)

    def test_availability_reuses_measured_executor_facts(self):
        report = {r["skill_id"]: r for r in skills.report({"ollama": False, "cloud_worker": False})}
        self.assertTrue(report["core.state"]["available"])
        self.assertFalse(report["ai.local"]["available"])
        self.assertFalse(report["ai.cloud"]["available"])
        report = {r["skill_id"]: r for r in skills.report({"ollama": True, "cloud_worker": True})}
        self.assertTrue(report["ai.local"]["available"])
        self.assertTrue(report["ai.cloud"]["available"])

    def test_capability_report_adds_skills_without_model_usage(self):
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        report = worker.capability_report()
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        self.assertIn("skills", report)
        self.assertGreaterEqual(len(report["skills"]), 9)
        self.assertEqual(before, after)

    def test_registry_health_is_deterministic(self):
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        result = health.check_skill_registry()
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        self.assertTrue(result["ok"], result)
        self.assertEqual(before, after)

    def test_network_skill_may_still_have_offline_subcapabilities(self):
        skills.register(skill_id="test.hybrid", name="Hybrid", network_required=1,
                        offline_supported=1, executor_classes="DET")
        self.assertEqual(skills.validate_registry(), [])
