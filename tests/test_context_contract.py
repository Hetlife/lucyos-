"""S-30: keep every bounded worker on one compact result-packet contract."""
from pathlib import Path

from tests.base import AionTest
from aion_core import context, tasks


FIELDS = ("STATUS", "ACTIONS", "FILES_CHANGED", "TESTS", "RESULTS", "BLOCKERS", "NEXT_ACTION")
LEGACY = ("ACTIONS_TAKEN", "TESTS_RUN", "FAILURES / RISKS / ASSUMPTIONS", "NEXT_RECOMMENDED_ACTION", "EXACT_RESUME_POINT")


class ContextResultContractTest(AionTest):
    def test_context_packet_uses_only_canonical_worker_fields(self):
        task_id = tasks.create("contract smoke", success_criteria="packet names are stable")
        packet = context.build(task_id)
        contract_line = next(line for line in packet.splitlines() if line.startswith("STATUS / ACTIONS /"))
        self.assertEqual(contract_line.split(" / "), list(FIELDS))
        for legacy in LEGACY:
            self.assertNotIn(legacy, packet)

    def test_codex_wrapper_declares_same_contract(self):
        script = (Path(__file__).resolve().parents[1] / "scripts" / "aion_codex_worker.sh").read_text()
        expected = ", ".join(FIELDS)
        self.assertIn(f"Return a compact result packet with: {expected}.", script)


if __name__ == "__main__":
    import unittest
    unittest.main()
