from aion_core import bootstrap, db, model_gateway
from tests.base import AionTest


class TestModelGateway(AionTest):
    def setUp(self):
        super().setUp()
        bootstrap.set_secret("OPENROUTER_API_KEY", "test-owner-supplied-key")

    def test_public_small_task_provider_can_run_through_mock_transport(self):
        def transport(req, timeout):
            self.assertIn("Bearer ", req.headers["Authorization"])
            return {"choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
        result = model_gateway.complete("format this", data_class="PUBLIC", transport=transport)
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "openrouter_free")
        self.assertEqual(result["text"], "ok")

    def test_private_data_is_never_sent_to_free_pool(self):
        for cls in ("INTERNAL", "CONFIDENTIAL", "SECRET"):
            with self.assertRaises(PermissionError):
                model_gateway.complete("private", data_class=cls, transport=lambda *_: {})


    def test_trial_or_paid_provider_is_not_auto_eligible(self):
        bootstrap.set_secret("CEREBRAS_API_KEY", "test-owner-supplied-key")
        db.set_meta("provider.cerebras_free.model", "gpt-oss-120b")
        statuses = {row["provider"]: row for row in model_gateway.provider_status()}
        self.assertEqual(statuses["cerebras_free"]["cost_class"], "E1")
        self.assertNotIn("cerebras_free", model_gateway.eligible(data_class="PUBLIC"))

    def test_trial_or_paid_provider_cannot_bypass_free_only_gate(self):
        bootstrap.set_secret("CEREBRAS_API_KEY", "test-owner-supplied-key")
        db.set_meta("provider.cerebras_free.model", "gpt-oss-120b")
        called = []
        with self.assertRaises(PermissionError):
            model_gateway.complete(
                "public", data_class="PUBLIC", provider="cerebras_free",
                transport=lambda *args: called.append(args),
            )
        self.assertEqual(called, [])

    def test_no_key_means_no_external_call(self):
        bootstrap.set_secret("OPENROUTER_API_KEY", "")
        called = []
        result = model_gateway.complete("public", data_class="PUBLIC", transport=lambda *a: called.append(a))
        self.assertFalse(result["ok"])
        self.assertEqual(called, [])
