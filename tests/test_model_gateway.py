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

    def test_no_key_means_no_external_call(self):
        bootstrap.set_secret("OPENROUTER_API_KEY", "")
        called = []
        result = model_gateway.complete("public", data_class="PUBLIC", transport=lambda *a: called.append(a))
        self.assertFalse(result["ok"])
        self.assertEqual(called, [])
