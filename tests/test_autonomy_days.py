"""Hands-off days distinguish approvals from owner operation."""
from datetime import datetime, timedelta, timezone

from tests.base import AionTest


class TestAutonomyDays(AionTest):
    def _completion(self, day, owner="worker-b"):
        from aion_core import tasks
        task_id = tasks.create(f"work {day}")
        tasks.update(task_id, status="DONE", owner_agent=owner,
                     completed_at=day + "T12:00:00+00:00", evidence="test proof")

    def test_approval_does_not_break_hands_off_day(self):
        from aion_core import autonomy, db
        day = "2026-01-01"
        self._completion(day)
        conn = db.connect()
        conn.execute("INSERT INTO events(at,day,actor,kind) VALUES(?,?,?,?)",
                     (day + "T13:00:00+00:00", day, "owner", "approval.approve"))
        conn.commit()
        result = autonomy.evaluate_day(day)
        self.assertTrue(result["qualifies"])
        self.assertIn("1 owner approval", result["evidence"])

    def test_owner_operation_breaks_day_and_owner_completed_task_does_not_count(self):
        from aion_core import autonomy, db
        day = "2026-01-02"
        self._completion(day, owner="owner")
        db.log_event("owner", "control.pause")
        conn = db.connect()
        conn.execute("UPDATE events SET day=? WHERE actor='owner' AND kind='control.pause'", (day,))
        conn.commit()
        result = autonomy.evaluate_day(day)
        self.assertFalse(result["qualifies"])

    def test_m3_requires_thirty_adjacent_qualifying_records(self):
        from aion_core import autonomy, db, milestones
        start = datetime(2026, 1, 1, tzinfo=timezone.utc).date()
        for offset in list(range(29)) + [30]:
            day = (start + timedelta(days=offset)).isoformat()
            self._completion(day)
            autonomy.evaluate_day(day)
        self.assertEqual(autonomy.consecutive_days(), 29)
        self.assertFalse(milestones.check()["M3"]["reached"])
        day = (start + timedelta(days=29)).isoformat()
        self._completion(day)
        autonomy.evaluate_day(day)
        self.assertEqual(autonomy.consecutive_days(), 31)
        self.assertTrue(milestones.check()["M3"]["reached"])

    def test_today_cannot_be_evaluated(self):
        from aion_core import autonomy
        with self.assertRaises(ValueError):
            autonomy.evaluate_day(datetime.now(timezone.utc).date().isoformat())


if __name__ == "__main__":
    import unittest
    unittest.main()
