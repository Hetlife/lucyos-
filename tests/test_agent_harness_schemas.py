"""Ensure all three provider-neutral JSON Schemas are valid and fail closed."""
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver
from tests.test_agent_harness import envelope


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "docs" / "agent-harness" / "schemas"


class HarnessSchemaTest(unittest.TestCase):
    def test_schema_documents_are_draft_2020_12_valid(self):
        for name in ("agent-message", "work-order", "result"):
            schema = json.loads((SCHEMA_DIR / (name + ".schema.json")).read_text())
            with self.subTest(name=name):
                Draft202012Validator.check_schema(schema)

    def test_work_order_uses_canonical_task_and_owner_gate(self):
        schema = json.loads((SCHEMA_DIR / "work-order.schema.json").read_text())
        valid = {
            "schema": "lucy-work-order/1", "canonical_task_id": "TASK-12345678",
            "revision": 1, "source_sha": "e" * 40,
            "objective": "Bounded deterministic validator test", "project_id": "lucyos",
            "dependencies": [], "executor_class": "R0", "allowed_paths": ["tests/"],
            "do_not_touch": ["aion_core/db.py"], "risk": "LOW", "max_tokens": 0,
            "steps": ["Run tests"], "acceptance_tests": ["all tests pass"],
            "rollback": "Discard branch worktree", "evidence_required": ["test run"],
            "owner_gate": False,
        }
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(valid))
        del valid["owner_gate"]
        self.assertFalse(validator.is_valid(valid))

    def test_result_schema_references_real_envelope_contract(self):
        path = SCHEMA_DIR / "result.schema.json"
        schema = json.loads(path.read_text())
        resolver = RefResolver(base_uri=path.as_uri(), referrer=schema)
        validator = Draft202012Validator(schema, resolver=resolver)
        valid = {"schema": "lucy-result/1", "verification_state": "PROPOSED",
                 "envelope": envelope(), "artifact_hashes": {}}
        self.assertTrue(validator.is_valid(valid), list(validator.iter_errors(valid)))
        valid["envelope"]["status"] = "PASS"
        self.assertFalse(validator.is_valid(valid))  # missing verifier reference


if __name__ == "__main__":
    unittest.main()
