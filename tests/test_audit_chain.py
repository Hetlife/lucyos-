"""S-26: hash-chained audit export -- proves tampering of an exported
events log is detectable: modification, deletion, and insertion, each
proven separately, as the task's acceptance criterion demands."""
import copy
import unittest

from tests.base import AionTest
from aion_core import db, reports, tasks


class AuditChainTest(AionTest):
    def _populate_events(self):
        # task.create()/task.update() log real events through db.log_event().
        for i in range(5):
            tasks.create(f"audit chain seed task {i}")
        db.connect().commit()

    def test_empty_chain_verifies_trivially(self):
        result = reports.audit_verify([])
        self.assertTrue(result["ok"])
        self.assertEqual(result["records"], 0)

    def test_untouched_export_verifies(self):
        self._populate_events()
        chain = reports.audit_export()
        self.assertGreater(len(chain), 0)
        result = reports.audit_verify(chain)
        self.assertTrue(result["ok"], f"untouched export failed to verify: {result}")
        self.assertEqual(result["records"], len(chain))

    def test_chain_links_are_actually_connected(self):
        self._populate_events()
        chain = reports.audit_export()
        self.assertEqual(chain[0]["prev_hash"], reports.AUDIT_GENESIS_HASH)
        for i in range(1, len(chain)):
            self.assertEqual(chain[i]["prev_hash"], chain[i - 1]["hash"])

    def test_modifying_a_record_fails_verification(self):
        self._populate_events()
        chain = reports.audit_export()
        tampered = copy.deepcopy(chain)
        tampered[2]["detail"] = tampered[2]["detail"] + " (modified after export)"

        result = reports.audit_verify(tampered)
        self.assertFalse(result["ok"])
        self.assertEqual(result["broken_at"], 2)

    def test_deleting_a_record_fails_verification(self):
        self._populate_events()
        chain = reports.audit_export()
        self.assertGreater(len(chain), 3)
        tampered = copy.deepcopy(chain)
        del tampered[2]

        result = reports.audit_verify(tampered)
        self.assertFalse(result["ok"])
        # The gap surfaces at the record that now follows the deleted one.
        self.assertEqual(result["broken_at"], 2)

    def test_inserting_a_record_fails_verification(self):
        self._populate_events()
        chain = reports.audit_export()
        tampered = copy.deepcopy(chain)
        forged = {
            "id": 99999, "at": chain[0]["at"], "day": chain[0]["day"], "actor": "attacker",
            "kind": "forged.event", "subject": "", "detail": "never happened",
            "prev_hash": chain[1]["hash"] if len(chain) > 1 else reports.AUDIT_GENESIS_HASH,
        }
        forged["hash"] = "0" * 64  # attacker doesn't know the real derivation
        tampered.insert(2, forged)

        result = reports.audit_verify(tampered)
        self.assertFalse(result["ok"])
        self.assertEqual(result["broken_at"], 2)

    def test_export_is_read_only_never_touches_events_table(self):
        self._populate_events()
        before = db.connect().execute("SELECT COUNT(*) FROM events").fetchone()[0]
        reports.audit_export()
        after = db.connect().execute("SELECT COUNT(*) FROM events").fetchone()[0]
        self.assertEqual(before, after)

    def test_re_export_after_new_events_extends_the_chain_consistently(self):
        self._populate_events()
        first = reports.audit_export()
        tasks.create("one more task after the first export")
        db.connect().commit()
        second = reports.audit_export()

        self.assertGreater(len(second), len(first))
        # The prefix must be byte-for-byte identical -- appending new events
        # never rewrites history.
        self.assertEqual(second[:len(first)], first)
        result = reports.audit_verify(second)
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
