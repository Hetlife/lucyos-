import unittest

from tests.base import AionTest
from aion_core import config, db, memory, packets, tasks

PACKET = """# AI SYNC PACKET

PACKET_ID: PKT-TEST-001
SOURCE: chatgpt
SOURCE_SESSION: session-abc
TIMESTAMP: 2026-09-03T10:00:00Z
PROJECT: lucyos
TOPIC: lead qualification

## OWNER INTENT
Get to first real revenue.

## VERIFIED FACTS
- Apollo integration is disabled.
- 14 leads exist in the local CSV.

## INFERENCES / ASSUMPTIONS
- Roughly half the leads are likely to be reachable.

## DECISIONS
- Qualify leads manually before any outbound automation.

## TASKS CREATED
- Qualify the 14 existing leads | P1 | none | 14 leads each marked qualified or rejected with a reason
- Draft the outreach template | P2 | none | one template reviewed against platform rules

## TASKS COMPLETED
- Exported the lead list from the CRM

## RESEARCH FINDINGS
- WhatsApp Business API requires template pre-approval (checked 2026-09-01).

## RISKS
- Outbound messaging without approval risks an account ban.

## BLOCKERS
- No payment gateway configured.

## APPROVALS REQUIRED
- Purchase a paid outreach tool subscription

## CURRENT STATE
Leads exist, nothing sent, no revenue.

## NEXT HIGHEST-VALUE ACTIONS
1. Qualify leads.

## EXACT RESUME POINT
Open the lead CSV and start qualifying at row 1.

END AI SYNC PACKET
"""


class TestPackets(AionTest):
    def test_ingest_creates_tasks_memory_and_approvals(self):
        result = packets.ingest(PACKET)
        self.assertEqual(result["status"], "PROCESSED")
        self.assertEqual(len(result["tasks"]), 2)
        self.assertEqual(len(result["approvals"]), 1)
        self.assertGreaterEqual(result["facts"], 5)
        titles = [tasks.get(t)["title"] for t in result["tasks"]]
        self.assertIn("Qualify the 14 existing leads", titles)

    def test_resume_point_is_stored(self):
        packets.ingest(PACKET)
        self.assertIn("row 1", db.get_meta("packet_resume_point"))

    def test_duplicate_packet_is_not_reprocessed(self):
        packets.ingest(PACKET)
        before = len(tasks.ready(50))
        second = packets.ingest(PACKET)
        self.assertEqual(second["status"], "DUPLICATE")
        self.assertEqual(len(tasks.ready(50)), before)

    def test_same_content_different_id_is_still_a_duplicate(self):
        packets.ingest(PACKET)
        again = packets.ingest(PACKET.replace("PKT-TEST-001", "PKT-TEST-999"))
        self.assertEqual(again["status"], "DUPLICATE")

    def test_missing_source_header_is_rejected(self):
        with self.assertRaises(packets.PacketError):
            packets.ingest("# AI SYNC PACKET\n\nPACKET_ID: X\n\n## VERIFIED FACTS\n- nothing\n")

    def test_secrets_in_a_packet_are_redacted_before_storage(self):
        dirty = PACKET.replace("Apollo integration is disabled.",
                               "Apollo key is ghp_AbCdEfGhIjKlMnOpQrStUvWxYz012345")
        result = packets.ingest(dirty)
        self.assertTrue(result["redacted"])
        rows = db.connect().execute("SELECT body FROM memory").fetchall()
        self.assertFalse(any("ghp_AbCdEf" in r["body"] for r in rows))

    def test_inbox_files_move_to_processed(self):
        pending = config.home() / "INBOX" / "pending"
        (pending / "packet1.md").write_text(PACKET, encoding="utf-8")
        results = packets.ingest_inbox()
        self.assertEqual(results[0]["status"], "PROCESSED")
        self.assertFalse((pending / "packet1.md").exists())
        self.assertTrue((config.home() / "INBOX" / "processed" / "packet1.md").exists())

    def test_unparseable_file_goes_to_failed(self):
        pending = config.home() / "INBOX" / "pending"
        (pending / "junk.md").write_text("not a packet at all", encoding="utf-8")
        packets.ingest_inbox()
        self.assertTrue((config.home() / "INBOX" / "failed" / "junk.md").exists())

    def test_conflicting_fact_is_flagged_not_overwritten(self):
        memory.remember("fact", "Apollo integration", "Apollo integration is enabled.",
                        confidence="VERIFIED_FACT")
        result = packets.ingest(PACKET)
        rows = db.connect().execute(
            "SELECT body FROM memory WHERE body LIKE 'Apollo integration is%'").fetchall()
        self.assertEqual(len(rows), 2, "both versions must survive for review")


if __name__ == "__main__":
    unittest.main()
