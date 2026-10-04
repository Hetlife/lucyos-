"""S-16: temporary-worker scope narrowing and TTL -- guard rails only.

Proves the primitives contract C6 needs before anything can spawn a bounded
temporary worker. This module never spawns one; these tests never spawn one
either -- fixtures that need a live agents row insert it directly via SQL,
exactly the way a future (not-yet-written) spawn path would.
"""
import unittest
from datetime import datetime, timedelta, timezone

from tests.base import AionTest
from aion_core import db, tempworker


class DeriveTest(unittest.TestCase):
    def test_granted_scope_is_the_intersection_never_a_superset(self):
        w = tempworker.derive(
            parent_scope={"code", "research", "debug", "write"},
            requested_scope={"code", "debug", "deploy"},
            ttl_seconds=3600,
        )
        self.assertEqual(set(w["scope"]), {"code", "debug"})
        self.assertNotIn("deploy", w["scope"])  # parent never held it
        self.assertNotIn("write", w["scope"])  # not requested

    def test_child_requesting_capability_parent_lacks_gets_narrower_not_requested(self):
        parent_scope = {"code", "research"}
        requested_scope = {"code", "research", "approve", "pay"}
        w = tempworker.derive(parent_scope, requested_scope, ttl_seconds=60)
        self.assertEqual(set(w["scope"]), {"code", "research"})
        self.assertNotEqual(set(w["scope"]), requested_scope)

    def test_scope_narrowing_is_transitive_across_three_generations(self):
        gen1_scope = {"code", "research", "debug", "write", "deploy"}
        gen2 = tempworker.derive(gen1_scope, {"code", "research", "debug"}, ttl_seconds=3600)
        self.assertEqual(set(gen2["scope"]), {"code", "research", "debug"})

        gen3 = tempworker.derive(gen2["scope"], {"code", "research", "approve"}, ttl_seconds=3600)
        self.assertEqual(set(gen3["scope"]), {"code", "research"})
        self.assertTrue(set(gen3["scope"]).issubset(set(gen2["scope"])))

        gen4 = tempworker.derive(gen3["scope"], {"code", "write"}, ttl_seconds=3600)
        self.assertEqual(set(gen4["scope"]), {"code"})
        self.assertTrue(set(gen4["scope"]).issubset(set(gen3["scope"])))
        self.assertTrue(set(gen4["scope"]).issubset(set(gen1_scope)))

    def test_accepts_comma_separated_string_scopes_matching_agents_table_convention(self):
        w = tempworker.derive("code,research,debug", "code,debug,deploy", ttl_seconds=60)
        self.assertEqual(set(w["scope"]), {"code", "debug"})

    def test_rejects_non_positive_ttl(self):
        with self.assertRaises(tempworker.TempWorkerError):
            tempworker.derive({"code"}, {"code"}, ttl_seconds=0)
        with self.assertRaises(tempworker.TempWorkerError):
            tempworker.derive({"code"}, {"code"}, ttl_seconds=-5)


class IsExpiredTest(unittest.TestCase):
    def test_worker_with_no_expiry_never_expires(self):
        w = {"scope": ["code"], "expires_at": None}
        self.assertFalse(tempworker.is_expired(w))

    def test_worker_past_its_ttl_is_expired(self):
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        w = {"scope": ["code"], "expires_at": past}
        self.assertTrue(tempworker.is_expired(w))

    def test_worker_within_its_ttl_is_not_expired(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        w = {"scope": ["code"], "expires_at": future}
        self.assertFalse(tempworker.is_expired(w))

    def test_derive_output_is_not_expired_immediately(self):
        w = tempworker.derive({"code"}, {"code"}, ttl_seconds=3600)
        self.assertFalse(tempworker.is_expired(w))

    def test_explicit_now_parameter_lets_ttl_be_checked_without_sleeping(self):
        w = tempworker.derive({"code"}, {"code"}, ttl_seconds=10)
        just_after_expiry = datetime.now(timezone.utc) + timedelta(seconds=11)
        self.assertTrue(tempworker.is_expired(w, now=just_after_expiry))


class AssertCanClaimTest(unittest.TestCase):
    def test_in_scope_unexpired_claim_succeeds(self):
        w = tempworker.derive({"code", "research"}, {"code", "research"}, ttl_seconds=3600)
        tempworker.assert_can_claim(w, "code")  # must not raise

    def test_out_of_scope_claim_is_refused(self):
        w = tempworker.derive({"code", "research"}, {"code"}, ttl_seconds=3600)
        with self.assertRaises(tempworker.TempWorkerError):
            tempworker.assert_can_claim(w, "research")

    def test_expired_worker_cannot_claim_a_task(self):
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        w = {"scope": ["code"], "expires_at": past}
        with self.assertRaises(tempworker.TempWorkerError):
            tempworker.assert_can_claim(w, "code")

    def test_expiry_is_checked_before_scope_for_a_clear_error(self):
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        w = {"scope": [], "expires_at": past}
        with self.assertRaises(tempworker.TempWorkerError) as ctx:
            tempworker.assert_can_claim(w, "code")
        self.assertIn("expired", str(ctx.exception))


class LiveAgentRowTest(AionTest):
    """TTL/scope enforcement reads a live agents row fresh every time -- no
    caching, no background sweeper. The row is inserted directly via SQL,
    the way a future spawn path would, since this module provides no
    insert/spawn function of its own."""

    def _insert_agent(self, agent_id, capabilities, expires_at=None, parent_agent_id=None):
        conn = db.connect()
        conn.execute(
            "INSERT INTO agents(agent_id, role, model, model_class, capabilities, "
            "parent_agent_id, expires_at) VALUES (?, 'temp', 'none', 'B', ?, ?, ?)",
            (agent_id, capabilities, parent_agent_id, expires_at),
        )
        conn.commit()

    def test_is_expired_reads_the_live_row(self):
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self._insert_agent("WORKER-1", "code,research", expires_at=past)
        self.assertTrue(tempworker.is_expired("WORKER-1"))

    def test_unexpired_live_row_is_not_expired(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self._insert_agent("WORKER-2", "code", expires_at=future)
        self.assertFalse(tempworker.is_expired("WORKER-2"))

    def test_permanent_agent_with_no_expiry_never_expires(self):
        self._insert_agent("WORKER-3", "code,research", expires_at=None)
        self.assertFalse(tempworker.is_expired("WORKER-3"))

    def test_assert_can_claim_against_a_live_expired_row_refuses(self):
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self._insert_agent("WORKER-4", "code", expires_at=past)
        with self.assertRaises(tempworker.TempWorkerError):
            tempworker.assert_can_claim("WORKER-4", "code")

    def test_assert_can_claim_against_live_row_out_of_scope_refuses(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self._insert_agent("WORKER-5", "code", expires_at=future)
        with self.assertRaises(tempworker.TempWorkerError):
            tempworker.assert_can_claim("WORKER-5", "deploy")

    def test_assert_can_claim_against_live_row_in_scope_succeeds(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self._insert_agent("WORKER-6", "code,deploy", expires_at=future)
        tempworker.assert_can_claim("WORKER-6", "deploy")  # must not raise

    def test_unknown_agent_id_raises(self):
        with self.assertRaises(tempworker.TempWorkerError):
            tempworker.is_expired("NO-SUCH-AGENT")

    def test_ttl_is_reread_live_not_cached(self):
        # Insert expired, confirm expired; update to unexpired directly in
        # the DB; confirm the next call reflects the new state -- proving
        # there is no cache and no sweeper standing between reads.
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self._insert_agent("WORKER-7", "code", expires_at=past)
        self.assertTrue(tempworker.is_expired("WORKER-7"))

        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        conn = db.connect()
        conn.execute("UPDATE agents SET expires_at=? WHERE agent_id=?", (future, "WORKER-7"))
        conn.commit()
        self.assertFalse(tempworker.is_expired("WORKER-7"))

    def test_parent_agent_id_column_is_additive_and_nullable(self):
        self._insert_agent("WORKER-8", "code", parent_agent_id="PARENT-1")
        row = db.connect().execute(
            "SELECT parent_agent_id FROM agents WHERE agent_id=?", ("WORKER-8",)
        ).fetchone()
        self.assertEqual(row["parent_agent_id"], "PARENT-1")

    def test_no_insert_or_spawn_function_exists_in_this_module(self):
        # Guard-rails only: this task must never provide a way to create a
        # worker row, only to check one that some future path created.
        public_names = [n for n in dir(tempworker) if not n.startswith("_")]
        for name in public_names:
            self.assertNotIn("spawn", name.lower())
            self.assertNotIn("create", name.lower())
            self.assertNotIn("insert", name.lower())


if __name__ == "__main__":
    unittest.main()
