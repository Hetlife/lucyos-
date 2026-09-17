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
