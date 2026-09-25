"""Context proxy boundary, accounting and determinism tests."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts import task_context_profiler as profiler


class ContextProfilerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = {
            "pkg/__init__.py": "",
            "pkg/a.py": "from . import b\n# é\n",
            "pkg/b.py": "from pkg import c\n",
            "pkg/c.py": "value = 1\n",
            "caller.py": "import pkg.a\n",
            "distant.py": "import caller\n",
            "tests/test_b.py": "from pkg import b\n",
            "tests/test_c.py": "import pkg.c\n",
            "START_HERE.md": "Read `docs/README.md` and `rules.json`.\n",
            "docs/README.md": "[Guide](GUIDE.md)\n",
            "docs/GUIDE.md": "A guide.\nDo not follow `unrelated.md`.\n",
            "docs/unrelated.md": "Not routed.\n",
            "rules.json": "{}\n",
        }
        for name, text in self.sources.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def test_hops_tests_routes_and_exact_accounting(self):
        result = profiler.profile(self.root, ["pkg/a.py"])
        expected = {"pkg/a.py", "pkg/b.py", "pkg/__init__.py", "caller.py",
                    "tests/test_b.py", "START_HERE.md", "docs/README.md",
                    "docs/GUIDE.md", "rules.json"}
        self.assertEqual(set(result["files"]), expected)
        self.assertEqual(result["file_count"], 9)
        self.assertEqual(result["source_loc"], 5)
        self.assertEqual(result["docs_loc"], 5)
        self.assertEqual(result["governance_loc"], 5)
        size = sum(len(self.sources[p].encode("utf-8")) for p in expected)
        self.assertEqual(result["bytes"], size)
        self.assertEqual(result["approx_tokens"], size / 4)

    def test_cli_is_deterministic_and_ignores_input_order_and_duplicates(self):
        outputs = []
        for paths in (["pkg/b.py", "pkg/a.py"], ["pkg/a.py", "pkg/b.py", "pkg/a.py"]):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(profiler.main(["--root", str(self.root), "--files", *paths]), 0)
            outputs.append(output.getvalue())
        self.assertEqual(*outputs)
        self.assertEqual(json.loads(outputs[0])["touched_files"], ["pkg/a.py", "pkg/b.py"])

    def test_unsafe_missing_and_symlink_inputs_rejected(self):
        (self.root / "link.py").symlink_to(self.root / "pkg/a.py")
        for path in ("../outside.py", "/etc/passwd", "missing.py", "link.py", "secrets/key.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                profiler.profile(self.root, [path])

    def test_private_directories_are_not_parsed(self):
        for folder in ("private_state", "secrets", ".ssh", "browser", "oauth"):
            path = self.root / folder
            path.mkdir()
            (path / "bad.py").write_text("this is not python!", encoding="utf-8")
        profiler.profile(self.root, ["pkg/a.py"])

    def test_nested_relative_and_absolute_submodule_imports(self):
        folder = self.root / "pkg/nested"
        folder.mkdir()
        (folder / "__init__.py").write_text("from ..a import value\n", encoding="utf-8")
        (folder / "client.py").write_text("from .. import b\nimport pkg.c\n", encoding="utf-8")
        graph = profiler.import_graph(self.root)
        self.assertIn("pkg/a.py", graph["pkg/nested/__init__.py"])
        self.assertTrue({"pkg/b.py", "pkg/c.py"} <= graph["pkg/nested/client.py"])


if __name__ == "__main__":
    unittest.main()
