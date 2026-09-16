from tests.base import AionTest
from aion_core import architecture, db, learnrepo, skills


class TestArchitectureGuard(AionTest):
    def setUp(self):
        super().setUp()
        skills.sync_catalog()

    def _proposal(self):
        return {
            "skill_id": "web.browser-kernel", "candidate_id": "playwright",
            "reuse_canonical_sqlite": True, "reuse_task_queue": True,
            "reuse_approval_engine": True, "reuse_health": True,
            "reuse_resource_governor": True, "feature_flagged": True,
            "rollback_defined": True, "evidence_defined": True,
            "new_canonical_state": False, "new_global_queue": False,
            "new_scheduler": False, "new_approval_system": False,
            "new_secret_store": False, "always_on_llm_health": False,
            "mandatory_cloud_dependency": False, "direct_saas_core_coupling": False,
            "broad_autonomous_installer": False, "new_daemon": False,
            "new_recurring_cost": False, "new_privilege": False,
            "notes": "test", "evidence": {"checked": True},
        }

    def test_clean_adapter_passes(self):
        self.assertEqual(architecture.audit(self._proposal())["status"], "PASS")

    def test_duplicate_control_plane_is_blocked(self):
        p = self._proposal(); p["new_global_queue"] = True
        r = architecture.audit(p)
        self.assertEqual(r["status"], "BLOCK")
        self.assertTrue(any("queue" in x for x in r["blockers"]))

    def test_new_daemon_or_cost_needs_review(self):
        p = self._proposal(); p["new_daemon"] = True; p["new_recurring_cost"] = True
        self.assertEqual(architecture.audit(p)["status"], "NEEDS_REVIEW")

    def test_missing_reuse_invariant_is_blocked(self):
        p = self._proposal(); p["reuse_canonical_sqlite"] = False
        self.assertEqual(architecture.audit(p)["status"], "BLOCK")

    def test_pass_can_record_architecture_evidence_without_ai(self):
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        r = architecture.audit_and_record(self._proposal())
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(before, after)
        self.assertIn("ARCHITECTURE", learnrepo.skill_review_status("web.browser-kernel")["stages"])

    def test_block_does_not_record_pass(self):
        p = self._proposal(); p["new_scheduler"] = True
        r = architecture.audit_and_record(p)
        self.assertEqual(r["status"], "BLOCK")
        st = learnrepo.skill_review_status("web.browser-kernel")["stages"]
        self.assertTrue(all(x["verdict"] != "PASS" for x in st.get("ARCHITECTURE", [])))
