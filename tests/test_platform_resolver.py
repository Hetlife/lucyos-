from unittest import mock

from aion_core import platform_resolver, skills
from tests.base import AionTest


class TestPlatformResolver(AionTest):
    def test_mac_plan_uses_catalog_without_installing(self):
        skills.sync_catalog()
        before = len(skills.all_skills())
        result = platform_resolver.resolve(profile={"os": "macos", "arch": "arm64", "ram_gb": 32, "apple_silicon": True})
        after = len(skills.all_skills())
        items = {x["skill_id"]: x for x in result["items"]}
        self.assertTrue(items["ai.mlx"]["compatible"])
        self.assertTrue(items["ai.llama-cpp"]["compatible"])
        self.assertEqual(before, after)
        self.assertEqual(result["profile"]["apple_silicon"], True)
        self.assertEqual(result["scheduler"]["kind"], "launchd")
        self.assertEqual(result["scheduler"]["service_unit_dir"], "deploy/launchd")
        self.assertEqual(result["scheduler"]["install_mode"], "render_only")
        self.assertEqual(items["ai.mlx"]["approval_state"], "NOT_YET_APPLICABLE")
        self.assertIn("rollback_ready", items["ai.mlx"])
        self.assertEqual(items["ai.mlx"]["evidence"], [
            "https://github.com/ml-explore/mlx",
            "https://github.com/ml-explore/mlx-lm",
        ])

    def test_machine_profile_detects_apple_silicon(self):
        profile = platform_resolver.machine_profile(system="Darwin", machine="arm64", ram_gb=24)
        self.assertEqual(profile["os"], "macos")
        self.assertTrue(profile["apple_silicon"])

    def test_approval_and_rollback_state_are_explicit(self):
        self.assertEqual(platform_resolver._approval_state("ARCHITECTURE_APPROVED"),
                         "OWNER_APPROVAL_REQUIRED")
        self.assertEqual(platform_resolver._approval_state("OWNER_APPROVED"),
                         "SATISFIED_OR_PAST_GATE")
        self.assertEqual(platform_resolver._approval_state("DISCOVERED"),
                         "NOT_YET_APPLICABLE")

    def test_non_mac_scheduler_plan_is_conservative(self):
        linux = platform_resolver._scheduler_plan({"os": "linux"})
        unknown = platform_resolver._scheduler_plan({"os": "freebsd"})
        self.assertEqual(linux["kind"], "systemd")
        self.assertEqual(unknown["kind"], "native-timer")
        self.assertEqual(unknown["install_mode"], "manual_review")

    def test_manifest_approval_rollback_and_evidence_are_preserved(self):
        manifest = {
            "skill_id": "test.mac-safe", "name": "Mac Safe", "priority": "P0",
            "platforms": ["macos"], "lifecycle_state": "ARCHITECTURE_APPROVED",
            "cost_class": "F0", "risk_class": "R1",
            "approval_rule": "owner before install",
            "rollback": "disable feature and remove rendered agent",
            "feature_flag": "TEST_MAC_SAFE_ENABLED",
            "references": ["https://example.invalid/evidence"],
        }
        with mock.patch.object(skills, "catalog_manifests", return_value=["ignored"]), \
             mock.patch.object(skills, "load_manifest", return_value=manifest), \
             mock.patch.object(skills, "all_skills", return_value=[]):
            result = platform_resolver.resolve(profile={
                "os": "macos", "arch": "arm64", "ram_gb": 24, "apple_silicon": True,
            })
        item = result["items"][0]
        self.assertEqual(item["approval_state"], "OWNER_APPROVAL_REQUIRED")
        self.assertEqual(item["approval_rule"], "owner before install")
        self.assertTrue(item["rollback_ready"])
        self.assertIn("remove rendered agent", item["rollback"])
        self.assertEqual(item["feature_flag"], "TEST_MAC_SAFE_ENABLED")
        self.assertEqual(item["evidence"], ["https://example.invalid/evidence"])
