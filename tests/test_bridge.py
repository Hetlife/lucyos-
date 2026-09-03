import json
import unittest

from tests.base import AionTest
from aion_core import approvals, config, tasks, util
from bridges import whatsapp_bridge as bridge


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


if __name__ == "__main__":
    unittest.main()
