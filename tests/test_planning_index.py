"""scripts/planning_index.py classifies planning documents deterministically."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SPEC = importlib.util.spec_from_file_location("planning_index", REPO / "scripts" / "planning_index.py")
planning_index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planning_index)


class PlanningIndexTest(unittest.TestCase):
    def test_status_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cur = root / ".lucy/planning/lucyos-total-recovery"
            cur.mkdir(parents=True)
            (cur / "00.md").write_text("# anything\n")
            old = root / ".lucy/execution"
            old.mkdir(parents=True)
            (old / "a.md").write_text("> STATUS: HISTORICAL — superseded\n# old\n")
            (old / "b.md").write_text("\n# no marker\n")
            (old / "c.md").write_text("STATUS: current\n")
            rows = dict(planning_index.collect(root))
            self.assertEqual(rows[".lucy/planning/lucyos-total-recovery/00.md"], "CURRENT")
            self.assertEqual(rows[".lucy/execution/a.md"], "HISTORICAL")
            self.assertEqual(rows[".lucy/execution/b.md"], "UNMARKED")
            self.assertEqual(rows[".lucy/execution/c.md"], "CURRENT")
            text = planning_index.render(planning_index.collect(root))
            self.assertIn("CURRENT=2", text)
            self.assertIn("| CURRENT | `.lucy/execution/c.md` |", text)

    def test_repo_has_exactly_one_current_package(self):
        rows = planning_index.collect(REPO)
        current = {p for p, s in rows if s == "CURRENT"}
        self.assertTrue(all(p.startswith(".lucy/planning/lucyos-total-recovery/") for p in current), current)
        self.assertTrue(current)


if __name__ == "__main__":
    unittest.main()
