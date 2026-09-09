"""Truthful calendar closes and portfolio milestone coverage."""
from unittest.mock import patch

from tests.base import AionTest


class TestMonthlyClose(AionTest):
    def _month(self, month, project="one", revenue=30000, cost=1000, linked=True):
        from aion_core import db, deliveries
        delivery_id = deliveries.record(project=project, evidence=f"delivery-{month}-{project}")
        conn = db.connect()
        for kind, amount in (("revenue", revenue), ("cost", cost)):
            conn.execute(
                "INSERT INTO finance(at,day,kind,stage,amount_inr,project,delivery_id,description,evidence) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (month + "-20T00:00:00+00:00", month + "-20", kind, "ACTUAL", amount,
                 project, delivery_id if linked else None, "", "proof"))
        conn.commit()
        return delivery_id

    @patch("aion_core.deliveries.date")
    def test_close_requires_finished_month_complete_costs_and_evidence(self, mocked_date):
        from aion_core import deliveries
        mocked_date.today.return_value.strftime.return_value = "2026-09"
        with self.assertRaises(ValueError):
            deliveries.close_month("one", "2026-09", costs_complete=True, evidence="proof")
        with self.assertRaises(ValueError):
            deliveries.close_month("one", "2026-08", costs_complete=False, evidence="proof")
        with self.assertRaises(ValueError):
            deliveries.close_month("one", "2026-08", costs_complete=True, evidence="")

    def test_unlinked_actual_money_disqualifies_month(self):
        from aion_core import deliveries
        self._month("2026-01", linked=False)
        deliveries.close_month("one", "2026-01", costs_complete=True, evidence="close-proof")
        self.assertEqual(deliveries.closed_portfolio_months(), [])

    def test_consecutive_means_adjacent_closed_calendar_months(self):
        from aion_core import deliveries, milestones
        for month in ("2026-01", "2026-02", "2026-04"):
            self._month(month)
            deliveries.close_month("one", month, costs_complete=True, evidence="close-proof")
        self.assertEqual(milestones._consecutive_months_at(25000), 2)
        self.assertFalse(milestones.check()["M4"]["reached"])

    def test_three_closed_profitable_months_reach_m4_and_report_concentration(self):
        from aion_core import deliveries, milestones
        for month in ("2026-01", "2026-02", "2026-03"):
            self._month(month, project="one", revenue=30000, cost=1000)
            self._month(month, project="two", revenue=10000, cost=1000)
            deliveries.close_month("one", month, costs_complete=True, evidence="close-one")
            deliveries.close_month("two", month, costs_complete=True, evidence="close-two")
        self.assertTrue(milestones.check()["M4"]["reached"])
        latest = deliveries.closed_portfolio_months()[-1]
        self.assertEqual(latest["contribution_inr"], 38000)
        self.assertEqual(latest["largest_revenue_share_pct"], 75.0)

    def test_cli_records_explicit_close_attestation(self):
        from aion_core import cli, db
        self.assertEqual(cli.main([
            "month-close", "one", "2026-01", "--costs-complete",
            "--evidence", "reconciled-ledger-ref"]), 0)
        row = db.connect().execute(
            "SELECT costs_complete,evidence FROM monthly_closes WHERE project='one'"
        ).fetchone()
        self.assertEqual(row["costs_complete"], 1)
        self.assertEqual(row["evidence"], "reconciled-ledger-ref")


if __name__ == "__main__":
    import unittest
    unittest.main()
