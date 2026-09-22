from tests.base import AionTest
from aion_core import db, owner_actions, taskcheck


class TestOwnerActions(AionTest):
    def setUp(self):
        super().setUp(); taskcheck.load_builtin_templates()

    def make(self):
        return owner_actions.request(
            title="Plug in test device",
            instructions="Connect the test device and confirm power.",
            public_base_url="https://task.example.test",
            expires_hours=12,
            action_type="physical",
        )

    def test_digest_contains_only_explicit_owner_actions(self):
        made=self.make(); digest=owner_actions.daily_digest()
        self.assertIn("Plug in test device",digest)
        self.assertIn(made["taskcheck_id"],digest)
        self.assertNotIn("engineering blocker",digest.lower())

    def test_reissue_rotates_bearer_token(self):
        made=self.make(); old=made["access_token"]
        runtime=self.tmp/"TASKCHECK"/"runtime"; runtime.mkdir(parents=True)
        (runtime/"public_url").write_text("https://task.example.test\n")
        link=owner_actions.reissue_link(made["taskcheck_id"])
        self.assertIn("https://task.example.test/t/",link)
        with self.assertRaises(ValueError): taskcheck.public_task(old,mark_opened=False)
