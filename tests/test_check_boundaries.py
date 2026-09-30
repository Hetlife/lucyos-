import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_boundaries.py"


def load_guard():
    spec = importlib.util.spec_from_file_location("check_boundaries", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBoundaryGuard(unittest.TestCase):
    def test_warning_mode_reports_and_passes(self):
        guard = load_guard()
        self.assertEqual(guard.main([]), 0)
        report = json.loads((ROOT / "evidence/boundary_report.md").read_text().split("\n", 2)[2])
        self.assertIn("violations", report)

    def test_strict_mode_fails_for_unmapped_violation(self):
        guard = load_guard()
        original_findings = guard.findings
        original_exceptions = guard.KNOWN_EXCEPTIONS
        try:
            # Direct unit-level contract for the strict exit rule.
            guard.findings = lambda: [{"path": "bad.py", "line": 1,
                                       "rule": "sqlite_import", "detail": "bad"}]
            guard.KNOWN_EXCEPTIONS = {"bad.py::sqlite_import": "S-99"}
            self.assertEqual(guard.main(["--strict"]), 0)
            guard.KNOWN_EXCEPTIONS = {}
            self.assertEqual(guard.main(["--strict"]), 1)
        finally:
            guard.findings = original_findings
            guard.KNOWN_EXCEPTIONS = original_exceptions

    def test_known_exception_and_stale_exception_are_ratchets(self):
        guard = load_guard()
        original = guard.KNOWN_EXCEPTIONS
        guard.KNOWN_EXCEPTIONS = {"aion_core/nope.py::dependency": "S-99"}
        try:
            self.assertEqual(guard.main(["--strict"]), 1)
        finally:
            guard.KNOWN_EXCEPTIONS = original


if __name__ == "__main__":
    unittest.main()
