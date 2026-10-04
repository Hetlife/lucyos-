"""sync_outbox: the local-first PENDING_SYNC ledger (contract C2).

Local work must never block on Drive, and the same content queued twice must
never fan out into two rows -- these are the two properties this file exists
to prove, not just exercise.
"""
from pathlib import Path

from aion_core import db, sync_outbox
from tests.base import AionTest


class TestSyncOutbox(AionTest):
    def _file(self, name="doc.md", text="hello world"):
        path = self.tmp / name
        path.write_text(text)
        return path

    def test_queue_twice_with_identical_content_yields_one_row(self):
        path = self._file()
        first = sync_outbox.queue("document", str(path), project="alpha")
        second = sync_outbox.queue("document", str(path), project="alpha")
        self.assertEqual(first, second)
        rows = db.connect().execute("SELECT COUNT(*) AS n FROM sync_outbox").fetchone()
        self.assertEqual(rows["n"], 1)

    def test_queue_different_content_yields_different_rows(self):
        a = sync_outbox.queue("document", str(self._file("a.md", "one")))
        b = sync_outbox.queue("document", str(self._file("b.md", "two")))
        self.assertNotEqual(a, b)

    def test_full_local_cycle_completes_with_no_network_or_rclone(self):
        """The actual point of the contract: Drive is never a precondition."""
        path = self._file()
        sync_id = sync_outbox.queue("document", str(path), project="alpha",
                                    remote_target="MARK2_SHARED/04_REPORTS")
        self.assertEqual(db.connect().execute(
            "SELECT status FROM sync_outbox WHERE sync_id=?", (sync_id,)
        ).fetchone()["status"], "PENDING_SYNC")
        self.assertEqual([r["sync_id"] for r in sync_outbox.pending()], [sync_id])
        sync_outbox.claim(sync_id, "promoter-1")
        sync_outbox.mark_synced(sync_id)
        row = db.connect().execute(
            "SELECT * FROM sync_outbox WHERE sync_id=?", (sync_id,)).fetchone()
        self.assertEqual(row["status"], "SYNCED")
        self.assertEqual(row["promoted_by"], "promoter-1")
        self.assertTrue(row["synced_at"])

    def test_pending_survives_a_process_restart(self):
        path = self._file()
        sync_id = sync_outbox.queue("document", str(path))
        db.close()  # simulates a fresh process: no in-memory state exists
        db.connect()
        self.assertEqual([r["sync_id"] for r in sync_outbox.pending()], [sync_id])

    def test_illegal_transition_raises(self):
        path = self._file()
        sync_id = sync_outbox.queue("document", str(path))
        with self.assertRaises(sync_outbox.SyncOutboxError):
            sync_outbox.mark_synced(sync_id)  # PENDING_SYNC -> SYNCED skips CLAIMED
        sync_outbox.claim(sync_id, "promoter-1")
        with self.assertRaises(sync_outbox.SyncOutboxError):
            sync_outbox.claim(sync_id, "promoter-2")  # already CLAIMED
        sync_outbox.mark_synced(sync_id)
        with self.assertRaises(sync_outbox.SyncOutboxError):
            sync_outbox.mark_conflict(sync_id, "too late")  # SYNCED is terminal

    def test_conflict_is_recorded_not_silently_resolved(self):
        path = self._file()
        sync_id = sync_outbox.queue("document", str(path))
        sync_outbox.claim(sync_id, "promoter-1")
        sync_outbox.mark_conflict(sync_id, "remote copy diverged")
        row = db.connect().execute(
            "SELECT * FROM sync_outbox WHERE sync_id=?", (sync_id,)).fetchone()
        self.assertEqual(row["status"], "CONFLICT")
        self.assertIn("remote copy diverged", row["last_error"])

    def test_unknown_sync_id_raises(self):
        with self.assertRaises(sync_outbox.SyncOutboxError):
            sync_outbox.claim("SYN-DOESNOTEXIST", "promoter-1")

    def test_backlog_counts_by_status(self):
        a = sync_outbox.queue("document", str(self._file("a.md", "one")))
        sync_outbox.queue("document", str(self._file("b.md", "two")))
        sync_outbox.claim(a, "promoter-1")
        counts = sync_outbox.backlog()
        self.assertEqual(counts["PENDING_SYNC"], 1)
        self.assertEqual(counts["CLAIMED"], 1)
        self.assertEqual(counts["SYNCED"], 0)

    def test_local_path_column_stores_exactly_what_was_passed(self):
        # C2 forbids absolute paths in the ledger; queue() needs a readable
        # path to hash the content, so the relative-path discipline lives at
        # the call site, not here. This proves the stored value is exactly
        # the string given -- no silent normalization to an absolute path.
        path = self._file()
        sync_id = sync_outbox.queue("document", str(path))
        row = db.connect().execute(
            "SELECT local_path FROM sync_outbox WHERE sync_id=?", (sync_id,)).fetchone()
        self.assertEqual(row["local_path"], str(path))


if __name__ == "__main__":
    import unittest
    unittest.main()
