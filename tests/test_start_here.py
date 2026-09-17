"""Keep the thin multi-model entrypoint from drifting into stale pointers."""
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class TestStartHere(unittest.TestCase):
    def test_stable_repo_pointers_exist(self):
        paths = [
            "START_HERE.md",
            ".lucy/authority/HIGH_MODEL_BASELINE.json",
            ".lucy/execution/SONNET_TASK_QUEUE.md",
            "docs/README.md",
            "docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt",
            "docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt",
            "aion_core/db.py", "aion_core/tasks.py", "aion_core/approvals.py",
            "aion_core/errors.py", "aion_core/memory.py", "aion_core/context.py",
            "aion_core/resume.py", "aion_core/sessions.py", "aion_core/worker.py",
            "aion_core/health.py", "aion_core/governor.py", "aion_core/metrics.py",
            "aion_core/learnrepo.py", "aion_core/architecture.py",
        ]
        missing = [path for path in paths if not (REPO / path).exists()]
        self.assertEqual(missing, [], f"START_HERE pointer(s) stale: {missing}")

    def test_entrypoint_routes_instead_of_duplicating_state(self):
        text = (REPO / "START_HERE.md").read_text(encoding="utf-8")
        self.assertIn("router, not a second brain", text)
        self.assertIn("./aion context <TASK_ID>", text)
        self.assertIn("./aion search", text)
        self.assertIn("$AION_HOME/RESUME.md", text)
        self.assertIn("HIGH_MODEL_BASELINE.json", text)
        self.assertIn("architecture-check", text)


if __name__ == "__main__":
    unittest.main()
