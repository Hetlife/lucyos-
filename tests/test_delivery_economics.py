"""Focused coverage for evidence-backed delivery unit economics."""
import os
import sqlite3

from tests.base import AionTest


class TestDeliveryEconomics(AionTest):
    def _completed(self, number=1, project="default"):
        from aion_core import deliveries
        return [deliveries.record(
            delivery_id=f"DEL-{project}-{i}", project=project,
            payer_id=f"payer-{i}", customer_id=f"customer-{i}",
            evidence=f"delivery-proof-{i}") for i in range(number)]

    def test_legacy_finance_migration_preserves_unknown_attribution(self):
        from aion_core import db
        db.close()
        legacy = self.tmp / "legacy-delivery.db"
        conn = sqlite3.connect(legacy)
        conn.execute(
            "CREATE TABLE finance (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, "
            "day TEXT NOT NULL, kind TEXT NOT NULL, stage TEXT NOT NULL DEFAULT 'ACTUAL', "
            "amount_inr REAL NOT NULL, project TEXT NOT NULL DEFAULT 'default', payer_id TEXT, "
            "description TEXT NOT NULL DEFAULT '', evidence TEXT NOT NULL DEFAULT '')")
        conn.execute(
            "INSERT INTO finance(at, day, kind, amount_inr, description, evidence) "
            "VALUES('2026-01-01T00:00:00+00:00','2026-01-01','revenue',100,'old','proof')")
        conn.commit()
        conn.close()
        os.environ["AION_DB"] = str(legacy)

        migrated = db.connect()
        columns = {r["name"] for r in migrated.execute("PRAGMA table_info(finance)")}
        self.assertTrue({"delivery_id", "cost_category"}.issubset(columns))
        row = migrated.execute("SELECT delivery_id, cost_category FROM finance").fetchone()
        self.assertIsNone(row["delivery_id"])
        self.assertIsNone(row["cost_category"])
        self.assertEqual(migrated.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0], 0)

    def test_only_explicitly_linked_actual_money_is_attributable(self):
        from aion_core import deliveries, metrics
        delivery_id = self._completed()[0]
        metrics.record_money("revenue", 1000, evidence="pay-linked", delivery_id=delivery_id)
        metrics.record_money("revenue", 9000, evidence="pay-unlinked")
        for category in deliveries.COST_CATEGORIES:
            metrics.record_money("cost", 10, evidence=f"cost-{category}",
                                 delivery_id=delivery_id, cost_category=category)
        metrics.record_money("cost", 500, stage="FORECAST", delivery_id=delivery_id,
                             cost_category="direct")
        metrics.record_money("revenue", 500, stage="SIMULATION", delivery_id=delivery_id)

        result = deliveries.economics()
        self.assertEqual(result["completed_deliveries"], 1)
        self.assertEqual(result["revenue_inr"], 1000)
        self.assertEqual(result["cost_inr"], 60)
        self.assertEqual(result["contribution_inr"], 940)

    def test_existing_finance_row_can_be_linked_without_identity_inference(self):
        from aion_core import db, deliveries, metrics
        delivery_id = deliveries.record(payer_id="payer-known", evidence="proof")
        metrics.record_money("revenue", 250, evidence="pay-old")
        row = db.connect().execute("SELECT id FROM finance").fetchone()
        deliveries.attribute_finance(row["id"], delivery_id)
        linked = db.connect().execute(
            "SELECT payer_id, delivery_id FROM finance WHERE id=?", (row["id"],)).fetchone()
        self.assertIsNone(linked["payer_id"])
        self.assertEqual(linked["delivery_id"], delivery_id)
        self.assertEqual(deliveries.economics()["contribution_inr"], 250)

    def test_m2_requires_ten_evidenced_completed_deliveries(self):
        from aion_core import db, deliveries, metrics, milestones
        ids = self._completed(9)
        metrics.record_money("revenue", 100, evidence="pay", delivery_id=ids[0])
        self.assertFalse(milestones.check()["M2"]["reached"])

        tenth = deliveries.record(delivery_id="DEL-tenth", status="IN_PROGRESS")
        self.assertFalse(milestones.check()["M2"]["reached"])
        # A revenue row is not a delivery and cannot make the count ten.
        metrics.record_money("revenue", 10000, evidence="unlinked-pay")
        self.assertFalse(milestones.check()["M2"]["reached"])
        db.connect().execute(
            "UPDATE deliveries SET status='COMPLETED', evidence='proof-10', completed_at=? "
            "WHERE delivery_id=?", ("2026-01-01T00:00:00+00:00", tenth))
        db.connect().commit()
        self.assertTrue(milestones.check()["M2"]["reached"])

    def test_m2_rejects_negative_attributable_contribution(self):
        from aion_core import metrics, milestones
        ids = self._completed(10)
        metrics.record_money("revenue", 100, evidence="pay", delivery_id=ids[0])
        metrics.record_money("cost", 101, evidence="refund", delivery_id=ids[0],
                             cost_category="refund")
        result = milestones.check()["M2"]
        self.assertFalse(result["reached"])
        self.assertIn("-1.0", result["evidence"])

    def test_cli_records_delivery_and_attributed_money(self):
        from aion_core import cli, db
        self.assertEqual(cli.main([
            "delivery-add", "--delivery-id", "DEL-cli", "--customer-id", "customer-cli",
            "--evidence", "signed-acceptance"]), 0)
        self.assertEqual(cli.main([
            "money-add", "revenue", "75", "--delivery-id", "DEL-cli",
            "--evidence", "payment-cli"]), 0)
        row = db.connect().execute("SELECT delivery_id FROM finance").fetchone()
        self.assertEqual(row["delivery_id"], "DEL-cli")


if __name__ == "__main__":
    import unittest
    unittest.main()
