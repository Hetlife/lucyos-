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

class TestSkillManifest(AionTest):
    def _manifest(self):
        return {
            "schema_version": 1, "skill_id": "test.manifest", "name": "Manifest",
            "version": "1.0.0", "capabilities": ["read", "write"],
            "executor_classes": ["DET"], "platforms": ["linux", "darwin"],
            "requirements": {"network": False, "ai": False, "offline_supported": True},
            "cost_class": "F0", "risk_class": "R0", "data_class": "INTERNAL", "priority": "P2",
            "enabled": True, "actions": ["read"], "permissions": ["workspace:read"],
        }

    def test_valid_manifest_registers_into_existing_registry(self):
        data = self._manifest()
        self.assertEqual(skills.validate_manifest(data), [])
        sid = skills.register_manifest(data)
        self.assertEqual(sid, "test.manifest")
        row = skills.get(sid)
        self.assertEqual(row["executor_classes"], "DET")
        self.assertEqual(row["platforms"], "linux,darwin")

    def test_manifest_rejects_unknown_fields_and_bad_executor(self):
        data = self._manifest()
        data["surprise_install_hook"] = "curl bad | sh"
        data["executor_classes"] = ["ROOT"]
        errors = skills.validate_manifest(data)
        self.assertTrue(any("unknown" in e for e in errors))
        self.assertIn("manifest:invalid-executor-class", errors)
        with self.assertRaises(skills.SkillError):
            skills.register_manifest(data)

    def test_manifest_requires_explicit_network_ai_offline_flags(self):
        data = self._manifest()
        del data["requirements"]["offline_supported"]
        self.assertTrue(any("missing-requirements" in e for e in skills.validate_manifest(data)))

    def test_loading_manifest_is_data_only(self):
        import json
        from pathlib import Path
        path = Path(self.tmp) / "manifest.json"
        path.write_text(json.dumps(self._manifest()), encoding="utf-8")
        loaded = skills.load_manifest(path)
        self.assertEqual(loaded["skill_id"], "test.manifest")
        self.assertEqual(db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0], 0)

    def test_repo_example_matches_runtime_validator(self):
        from pathlib import Path
        repo = Path(__file__).resolve().parent.parent
        data = skills.load_manifest(repo / "skills" / "example.manifest.json")
        self.assertEqual(skills.validate_manifest(data), [])


class TestSkillCatalogLifecycle(AionTest):
    def test_catalog_valid_and_complete(self):
        self.assertEqual(skills.validate_catalog(), [])
        self.assertGreaterEqual(len(skills.catalog_manifests()), 100)

    def test_catalog_sync_learns_candidates_disabled(self):
        skills.sync_catalog()
        row = skills.get("web.browser-kernel")
        self.assertIsNotNone(row)
        self.assertEqual(row["lifecycle_state"], "DISCOVERED")
        self.assertEqual(row["enabled"], 0)
        self.assertTrue(row["source_manifest"].endswith("web/browser-kernel.manifest.json"))

    def test_catalog_sync_is_idempotent_and_does_not_disable_existing_core(self):
        first = skills.sync_catalog()
        before = db.connect().execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        result = skills.sync_catalog()
        after = db.connect().execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        self.assertGreater(first["added"], 0)
        self.assertEqual(before, after)
        self.assertEqual(result["added"], 0)
        self.assertEqual(skills.get("core.learnrepo")["enabled"], 1)

    def test_discovered_skill_cannot_be_enabled_directly(self):
        skills.sync_catalog()
        with self.assertRaises(skills.SkillError):
            skills.set_enabled("web.browser-kernel", True)

    def test_lifecycle_cannot_skip_security_pipeline(self):
        skills.sync_catalog()
        with self.assertRaises(skills.SkillError):
            skills.set_lifecycle("web.browser-kernel", "ACTIVE")
        from aion_core import learnrepo
        learnrepo.record_skill_review("web.browser-kernel", "playwright", "RESEARCH", {"official_repo": "checked"})
        skills.set_lifecycle("web.browser-kernel", "RESEARCHED")
        self.assertEqual(skills.get("web.browser-kernel")["lifecycle_state"], "RESEARCHED")

    def test_activation_requires_tested_state(self):
        sid = "test.lifecycle"
        skills.register(skill_id=sid, name="Lifecycle", enabled=0, lifecycle_state="INSTALLED_DISABLED")
        with self.assertRaises(skills.SkillError):
            skills.activate(sid)
        skills.set_lifecycle(sid, "TESTED")
        skills.activate(sid)
        row = skills.get(sid)
        self.assertEqual(row["lifecycle_state"], "ACTIVE")
        self.assertEqual(row["enabled"], 1)

    def test_catalog_learning_makes_zero_model_calls(self):
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        skills.sync_catalog()
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        self.assertEqual(before, after)


class TestLearnRepoSkillContract(AionTest):
    def setUp(self):
        super().setUp()
        skills.sync_catalog()

    def test_catalog_transition_requires_learnrepo_evidence(self):
        with self.assertRaises(skills.SkillError):
            skills.set_lifecycle("web.browser-kernel", "RESEARCHED")
        from aion_core import learnrepo
        learnrepo.record_skill_review(
            "web.browser-kernel", "playwright", "RESEARCH",
            {"official_repo": "https://github.com/microsoft/playwright", "checked": True},
            candidate_url="https://github.com/microsoft/playwright")
        skills.set_lifecycle("web.browser-kernel", "RESEARCHED")
        self.assertEqual(skills.get("web.browser-kernel")["lifecycle_state"], "RESEARCHED")

    def test_stage_progression_requires_matching_pass(self):
        from aion_core import learnrepo
        sid = "web.browser-kernel"
        learnrepo.record_skill_review(sid, "playwright", "RESEARCH", {"docs": "checked"})
        skills.set_lifecycle(sid, "RESEARCHED")
        learnrepo.record_skill_review(sid, "playwright", "LICENSE", {"license": "Apache-2.0"}, verdict="NEEDS_REVIEW")
        with self.assertRaises(skills.SkillError):
            skills.set_lifecycle(sid, "LICENSE_OK")
        learnrepo.record_skill_review(sid, "playwright", "LICENSE", {"license": "Apache-2.0", "commercial": "checked"})
        skills.set_lifecycle(sid, "LICENSE_OK")

    def test_candidate_limit_two_primary_one_fallback(self):
        from aion_core import learnrepo
        sid = "web.browser-agent"
        for cid in ("one", "two"):
            learnrepo.record_skill_review(sid, cid, "RESEARCH", {"checked": cid})
        with self.assertRaises(ValueError):
            learnrepo.record_skill_review(sid, "three", "RESEARCH", {"checked": 3})
        learnrepo.record_skill_review(sid, "fallback", "RESEARCH", {"checked": "fallback"}, role="fallback")
        with self.assertRaises(ValueError):
            learnrepo.record_skill_review(sid, "fallback2", "RESEARCH", {"checked": "fallback2"}, role="fallback")

    def test_review_recording_is_deterministic_zero_ai(self):
        from aion_core import learnrepo
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        learnrepo.record_skill_review("docs.pdf-read", "pypdf", "RESEARCH", {"official_repo": "checked"})
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        self.assertEqual(before, after)
        self.assertIn("RESEARCH", learnrepo.skill_review_status("docs.pdf-read")["stages"])


class TestSkillPolicyClasses(AionTest):
    def test_policy_enums_are_strict(self):
        with self.assertRaises(skills.SkillError):
            skills.register(skill_id="test.badpolicy", name="bad", cost_class="FREE")
        with self.assertRaises(skills.SkillError):
            skills.register(skill_id="test.badpolicy2", name="bad", risk_class="HIGH")
        with self.assertRaises(skills.SkillError):
            skills.register(skill_id="test.badpolicy3", name="bad", data_class="PRIVATE")

    def test_catalog_has_explicit_cost_risk_data_priority(self):
        for path in skills.catalog_manifests():
            data = skills.load_manifest(path)
            self.assertIn(data["cost_class"], skills.COST_CLASSES, path)
            self.assertIn(data["risk_class"], skills.RISK_CLASSES, path)
            self.assertIn(data["data_class"], skills.DATA_CLASSES, path)
            self.assertIn(data["priority"], skills.PRIORITY_CLASSES, path)

    def test_capability_report_exposes_policy_without_model_call(self):
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        report = worker.capability_report()
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        row = next(x for x in report["skills"] if x["skill_id"] == "core.state")
        self.assertIn(row["cost_class"], skills.COST_CLASSES)
        self.assertIn(row["risk_class"], skills.RISK_CLASSES)
        self.assertIn(row["data_class"], skills.DATA_CLASSES)
        self.assertEqual(before, after)
