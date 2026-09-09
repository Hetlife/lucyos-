import json
import os
import unittest
from unittest import mock

from tests.base import AionTest
from aion_core import approvals, config, tasks, util
from bridges import whatsapp_bridge as bridge


class TestCloudSenderAuthorization(unittest.TestCase):
    def test_only_configured_owner_sender_is_authorized(self):
        from bridges.whatsapp_bridge import cloud_sender_allowed
        self.assertTrue(cloud_sender_allowed("15551234567", "15551234567"))
        self.assertFalse(cloud_sender_allowed("15557654321", "15551234567"))
        self.assertFalse(cloud_sender_allowed("", "15551234567"))


class TestBridge(AionTest):
    def test_reply_is_redacted(self):
        tasks.create("rotate ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        self.assertNotIn("ghp_AbCdEf", bridge.reply_to("tasks"))

    def test_oversized_message_is_refused(self):
        self.assertIn("too long", bridge.reply_to("x" * 5000))

    def test_file_adapter_round_trip(self):
        inbox = config.home() / "INBOX" / "whatsapp"
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / "msg1.txt").write_text("status", encoding="utf-8")
        bridge.run_file(once=True)
        out = config.home() / "OUTBOX" / "whatsapp" / "msg1.reply.txt"
        self.assertTrue(out.exists())
        self.assertIn("AION STATUS", out.read_text())
        self.assertFalse((inbox / "msg1.txt").exists())

    def test_file_adapter_ignores_a_redelivered_message(self):
        inbox = config.home() / "INBOX" / "whatsapp"
        inbox.mkdir(parents=True, exist_ok=True)
        a = approvals.create("spend money")
        (inbox / "m.txt").write_text(f"APPROVE {a}", encoding="utf-8")
        bridge.run_file(once=True)
        first = (config.home() / "OUTBOX" / "whatsapp" / "m.reply.txt").read_text()
        self.assertIn(a, first)
        # Same file name and body delivered again must not be reprocessed.
        (inbox / "m.txt").write_text(f"APPROVE {a}", encoding="utf-8")
        bridge.run_file(once=True)
        self.assertFalse((inbox / "m.txt").exists())

    def test_router_crash_becomes_a_logged_error_not_a_dead_channel(self):
        original = bridge.router.handle
        bridge.router.handle = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            reply = bridge.reply_to("status")
        finally:
            bridge.router.handle = original
        self.assertIn("logged", reply)
        from aion_core import errors
        self.assertTrue(errors.open_errors())

    def test_cloud_payload_extracts_only_text_messages(self):
        payload = {"entry": [{"changes": [{"value": {"messages": [
            {"id": "wamid.1", "from": "15551234567", "type": "text",
             "text": {"body": " status "}},
            {"id": "wamid.2", "from": "15551234567", "type": "image"},
        ]}}]}]}
        self.assertEqual(bridge.cloud_messages(payload),
                         [("wamid.1", "15551234567", "status")])

    def test_cloud_client_sends_whatsapp_text_request(self):
        response = mock.MagicMock(status=200)
        response.__enter__.return_value = response
        client = bridge.CloudAPI("token-not-real", "123", "v99.0")
        with mock.patch.object(bridge.urlrequest, "urlopen", return_value=response) as send:
            client.send_text("15551234567", "AION STATUS")
        request = send.call_args.args[0]
        self.assertEqual(request.full_url,
                         "https://graph.facebook.com/v99.0/123/messages")
        self.assertEqual(json.loads(request.data)["text"]["body"], "AION STATUS")
        self.assertEqual(request.get_header("Authorization"), "Bearer token-not-real")

    def test_cloud_adapter_refuses_to_start_without_credentials(self):
        names = ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID",
                 "WHATSAPP_VERIFY_TOKEN", "WHATSAPP_APP_SECRET",
                 "WHATSAPP_GRAPH_API_VERSION")
        with mock.patch.dict(os.environ, {name: "" for name in names}):
            self.assertEqual(bridge.run_cloud("127.0.0.1", 0), 2)


if __name__ == "__main__":
    unittest.main()
