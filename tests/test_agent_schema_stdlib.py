"""Hermetic JSON Schema validation on Python without optional jsonschema."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest import TestCase
from unittest.mock import patch

from aion_core import packets
from tests.test_agent_harness import envelope
from tests.test_agent_collaboration import review


class StdlibSchemaTest(TestCase):
    def validate_without_optional_library(self, value):
        with patch.dict(sys.modules, {"jsonschema": None}):
            return packets.validate_agent_envelope(value)

    def test_valid_result_without_dependency(self):
        self.assertEqual(self.validate_without_optional_library(envelope())["status"],
                         "VERIFYING")

    def test_known_attacks_fail_closed_without_dependency(self):
        invalid = [
            {"nonsense": "authorize"}, {"redacted": 1},
            {"sender": 88}, {"type": "SUPERUSER"}, {"status": "DONE"},
            {"created_at": "tomorrow"}, {"created_at": "2026-10-16T10:00:00"},
            {"summary": ""}, {"summary": "x" * 601}, {"evidence_refs": "not-list"},
            {"tests": [{}]}, {"tests": [{"command": "x", "status": "PASS"}]},
            {"limits": {"max_retries": 900}},
        ]
        for changes in invalid:
            candidate = envelope()
            candidate.update(changes)
            with self.subTest(changes=list(changes)):
                with self.assertRaises(packets.PacketError):
                    self.validate_without_optional_library(candidate)

    def test_review_requires_exact_machine_fields(self):
        good = review(position="CHALLENGE")
        self.assertEqual(self.validate_without_optional_library(good)["type"], "REVIEW")
        invalid = deepcopy(good)
        del invalid["review_target"]
        with self.assertRaises(packets.PacketError):
            self.validate_without_optional_library(invalid)
        invalid = deepcopy(good)
        del invalid["review_issue"]
        with self.assertRaises(packets.PacketError):
            self.validate_without_optional_library(invalid)

    def test_cross_document_workorder_and_result(self):
        root = packets.AGENT_ENVELOPE_SCHEMA.parent
        wo = json.loads((root / "work-order.schema.json").read_text())
        order = {
            "schema":"lucy-work-order/1","canonical_task_id":"TASK-12345678",
            "revision":1,"source_sha":"e"*40,"objective":"Prove true AION task",
            "project_id":"lucyos","dependencies":[],"executor_class":"R0",
            "allowed_paths":["tests/"],"do_not_touch":["aion_core/db.py"],
            "risk":"LOW","max_tokens":0,"steps":["Run exact test"],
            "acceptance_tests":["test passes"],"rollback":"Discard worktree",
            "evidence_required":["test log"],"owner_gate":False,
        }
        packets._schema_subset_check(order,wo,root=root)
        bad=dict(order)
        bad["owner_gate"]=None
        with self.assertRaises(ValueError):
            packets._schema_subset_check(bad,wo,root=root)
        result_schema=json.loads((root / "result.schema.json").read_text())
        result={"schema":"lucy-result/1","envelope":envelope(),
                "artifact_hashes":{},"verification_state":"PROPOSED"}
        packets._schema_subset_check(result,result_schema,root=root)
        result["envelope"]["extra_permission"]="owner"
        with self.assertRaises(ValueError):
            packets._schema_subset_check(result,result_schema,root=root)

    def test_unsupported_keywords_or_external_refs_never_ignored(self):
        for schema in ({"allOf":[{"not":{"status":"FAIL"}}]},
                       {"$ref":"https://example.invalid/dangerous.json"},
                       {"type":"string","if":{"const":"x"}},
                       {"if":{"not":{"const":"x"}},"then":{"const":"x"}},
                       {"properties":{"allowed":{"oneOf":[{"type":"string"}]}}}):
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                packets._schema_subset_check("x",schema,root=packets.AGENT_ENVELOPE_SCHEMA.parent)
