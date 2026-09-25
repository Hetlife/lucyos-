"""Exercise the standalone complexity reporter on known source graphs."""
import importlib.util
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "complexity_map.py"
spec = importlib.util.spec_from_file_location("complexity_map", SCRIPT)
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


class TestComplexityMap(unittest.TestCase):
    def test_reports_and_cli_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "aion_core"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "a.py").write_text(
                "from . import b\nfrom .b import Thing\nimport os\n"
                "def long():\n" + "    pass\n" * 120 +
                "async def short():\n    pass\n", encoding="utf-8")
            (package / "b.py").write_text(
                "import aion_core.a\nclass Thing:\n    pass\n", encoding="utf-8")
            nested = package / "nested"
            nested.mkdir()
            (nested / "__init__.py").write_text("from .. import a\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "ignored.py").write_text("invalid python!", encoding="utf-8")
            outputs = [root / "first", root / "second"]
            for out in outputs:
                with patch.object(sys, "argv", [str(SCRIPT), "--root", str(root), "--out", str(out)]):
                    with self.assertRaises(SystemExit) as caught:
                        runpy.run_path(str(SCRIPT), run_name="__main__")
                    self.assertEqual(caught.exception.code, 0)
            for filename in ("complexity_map.json", "dependency_graph.json", "hotspots.md"):
                self.assertEqual((outputs[0] / filename).read_bytes(),
                                 (outputs[1] / filename).read_bytes())
            modules = json.loads((outputs[0] / "complexity_map.json").read_text())["modules"]
            self.assertEqual(len(modules), 4)
            row = modules["aion_core.a"]
            self.assertEqual(set(row), {"path", "loc", "classes", "functions",
                                       "functions_over_120", "imports_out", "importers_in"})
            self.assertEqual(row["path"], "aion_core/a.py")
            self.assertEqual(row["loc"], 126)
            self.assertEqual(row["functions_over_120"], [{"name": "long", "line": 4, "loc": 121}])
            self.assertEqual(row["imports_out"], ["aion_core.b"])
            self.assertEqual(row["importers_in"], ["aion_core.b", "aion_core.nested"])
            self.assertEqual(modules["aion_core.b"]["classes"], 1)
            graph = json.loads((outputs[0] / "dependency_graph.json").read_text())
            self.assertEqual(graph["cycles"], [["aion_core.a", "aion_core.b", "aion_core.a"]])
            self.assertEqual(len(graph["edges"]), 3)

    def test_cycle_shapes(self):
        self.assertEqual(reporter.cycles_for({"a": {"b"}, "b": set()}), [])
        self.assertEqual(reporter.cycles_for({"a": {"a"}, "b": {"c"}, "c": {"b"}}),
                         [["a", "a"], ["b", "c", "b"]])

    def test_function_boundary_and_qualified_names(self):
        tree = reporter.ast.parse("class Thing:\n    def exact(self):\n" + "        pass\n" * 119)
        self.assertEqual(reporter.functions_for(tree), [{"name": "Thing.exact", "line": 2, "loc": 120}])

    def test_invalid_source_fails_without_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "bad.py").write_text("def broken(", encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                reporter.main(["--root", str(root), "--out", str(root / "out")])
            self.assertEqual(caught.exception.code, 1)
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
