"""Behavioural tests for the smallest-fix skill.

Weighted toward the two failure modes that would make this skill actively
harmful rather than merely unhelpful: flagging something that is not real
(false positive, wastes a reviewer's attention) and staying silent on
something that is real (false negative, defeats the point). The duplicate-
finding regression test exists because that exact bug was caught by manual
testing during development, not by code review -- it is recorded here so it
cannot come back silently.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "smallest-fix"
SCRIPT = SKILL_DIR / "scripts" / "check_reinvention.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_reinvention", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_reinvention"] = module
    spec.loader.exec_module(module)
    return module


checker = _load_module()


class TestSkillPackage(unittest.TestCase):
    def test_exactly_one_skill_md(self):
        found = [p for p in SKILL_DIR.rglob("SKILL.md") if "__pycache__" not in p.parts]
        self.assertEqual(len(found), 1)

    def test_frontmatter_declares_name_and_description(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        end = text.index("\n---", 4)
        front = text[4:end]
        fields = {}
        for line in front.splitlines():
            if ":" in line and not line.startswith(" "):
                key, _, value = line.partition(":")
                fields[key.strip()] = value.strip()
        self.assertEqual(fields.get("name"), "smallest-fix")
        self.assertEqual(fields.get("name"), SKILL_DIR.name)
        self.assertGreater(len(fields.get("description", "")), 150)

    def test_referenced_script_exists(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/check_reinvention.py", text)
        self.assertTrue(SCRIPT.exists())

    def test_script_compiles(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(SCRIPT)],
            shell=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_script_is_stdlib_only(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for needle in ("import requests", "import yaml", "from requests", "from yaml"):
            self.assertNotIn(needle, text)

    def test_no_unused_imports_at_module_level(self):
        """The skill preaches against dead code; its own script should have none."""
        import ast as ast_mod
        tree = ast_mod.parse(SCRIPT.read_text(encoding="utf-8"))
        imported = set()
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.Import):
                imported.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast_mod.ImportFrom):
                if node.module == "__future__":
                    continue  # a directive, never referenced by name elsewhere
                imported.update(alias.asname or alias.name for alias in node.names)
        source = SCRIPT.read_text(encoding="utf-8")
        for name in imported:
            uses = source.count(name)
            self.assertGreater(uses, 1, f"{name!r} is imported but appears to be unused")


class TestReinventionChecker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def scan(self, *paths):
        return checker.scan([str(p) for p in paths], root=self.root)

    def categories(self, result) -> list:
        return [f["category"] for f in result["findings"]]

    # --- true positives, one per rule -------------------------------------

    def test_detects_datetime_now_utc(self):
        f = self.write("a.py", "from datetime import datetime, timezone\n"
                                "x = datetime.now(timezone.utc)\n")
        result = self.scan(f)
        self.assertIn("timestamp", self.categories(result))

    def test_detects_datetime_utcnow(self):
        f = self.write("a.py", "import datetime\nx = datetime.utcnow()\n")
        result = self.scan(f)
        self.assertIn("timestamp", self.categories(result))

    def test_detects_uuid4(self):
        f = self.write("a.py", "import uuid\nx = uuid.uuid4().hex\n")
        result = self.scan(f)
        self.assertIn("id_generation", self.categories(result))

    def test_detects_sha256(self):
        f = self.write("a.py", "import hashlib\nx = hashlib.sha256(b'a').hexdigest()\n")
        result = self.scan(f)
        self.assertIn("hashing", self.categories(result))

    def test_detects_json_dump(self):
        f = self.write("a.py", "import json\n"
                                "with open('x', 'w') as fh:\n    json.dump({}, fh)\n")
        result = self.scan(f)
        self.assertIn("json_io", self.categories(result))

    def test_detects_json_load(self):
        f = self.write("a.py", "import json\n"
                                "with open('x') as fh:\n    json.load(fh)\n")
        result = self.scan(f)
        self.assertIn("json_io", self.categories(result))

    def test_detects_atomic_write_pattern(self):
        f = self.write("a.py",
                       "import tempfile, os\n"
                       "def w(path, text):\n"
                       "    fd, tmp = tempfile.mkstemp()\n"
                       "    os.write(fd, text.encode())\n"
                       "    os.replace(tmp, path)\n")
        result = self.scan(f)
        self.assertIn("atomic_write", self.categories(result))

    # --- the exact regression this skill's own development caught ---------

    def test_chained_call_reports_once_not_twice(self):
        """hashlib.sha256(x).hexdigest() is one reinvention, not two findings.

        The first implementation matched on the unparsed text of *every* Call
        node, including the outer .hexdigest() call, whose full source text
        also happens to start with 'hashlib.sha256(' as a substring. Caught
        by running the checker against a real fixture, not by inspection.
        """
        f = self.write("a.py", "import hashlib\n"
                                "x = hashlib.sha256(b'a').hexdigest()\n")
        result = self.scan(f)
        hashing_hits = [c for c in self.categories(result) if c == "hashing"]
        self.assertEqual(len(hashing_hits), 1, result["findings"])

    # --- false positives that must never happen ----------------------------

    def test_comment_mentioning_a_pattern_is_not_flagged(self):
        f = self.write("a.py", "# call hashlib.sha256(x) here later, and uuid.uuid4() too\n"
                                "def noop():\n    pass\n")
        self.assertEqual(self.scan(f)["findings"], [])

    def test_string_literal_mentioning_a_pattern_is_not_flagged(self):
        f = self.write("a.py", "MSG = 'use hashlib.sha256(data) to hash it'\n")
        self.assertEqual(self.scan(f)["findings"], [])

    def test_datetime_now_with_no_args_is_not_flagged(self):
        """Naive local time is a different bug; util.now() doesn't fix it."""
        f = self.write("a.py", "import datetime\nx = datetime.now()\n")
        self.assertEqual(self.scan(f)["findings"], [])

    def test_datetime_now_with_other_timezone_is_not_flagged(self):
        f = self.write("a.py", "import datetime, zoneinfo\n"
                                "tz = zoneinfo.ZoneInfo('Asia/Kolkata')\n"
                                "x = datetime.now(tz)\n")
        self.assertEqual(self.scan(f)["findings"], [])

    def test_json_dumps_is_not_confused_with_json_dump(self):
        """dumps (returns a string) is a different call from dump (writes a file)."""
        f = self.write("a.py", "import json\nx = json.dumps({})\n")
        self.assertEqual(self.scan(f)["findings"], [])

    def test_mkstemp_alone_without_os_replace_is_not_flagged(self):
        f = self.write("a.py", "import tempfile\nfd, path = tempfile.mkstemp()\n")
        self.assertEqual(self.scan(f)["findings"], [])

    def test_clean_file_produces_no_findings(self):
        f = self.write("a.py", "def add(a, b):\n    return a + b\n")
        self.assertEqual(self.scan(f)["findings"], [])

    # --- exemption and robustness -------------------------------------------

    def test_aion_core_util_is_always_exempt(self):
        f = self.write("aion_core/util.py",
                       "import datetime\nx = datetime.now(datetime.timezone.utc)\n")
        self.assertEqual(self.scan(f)["findings"], [])

    def test_custom_exempt_pattern_is_respected(self):
        f = self.write("legacy/frozen.py", "import uuid\nx = uuid.uuid4()\n")
        result = checker.scan([str(f)], exempt=checker.DEFAULT_EXEMPT + ("legacy/frozen.py",),
                              root=self.root)
        self.assertEqual(result["findings"], [])

    def test_syntax_error_is_reported_not_raised(self):
        f = self.write("broken.py", "def f(:\n")
        result = self.scan(f)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["category"], "parse_error")

    def test_scan_never_executes_the_file_it_reads(self):
        sentinel = self.root / "EXECUTED"
        self.write("evil.py", f"open({str(sentinel)!r}, 'w').write('x')\n")
        self.scan(self.root / "evil.py")
        self.assertFalse(sentinel.exists(), "check_reinvention executed the file it was scanning")

    def test_directory_scan_finds_files_recursively(self):
        self.write("a/b/c.py", "import uuid\nx = uuid.uuid4()\n")
        result = self.scan(self.root)
        self.assertGreaterEqual(result["files_scanned"], 1)
        self.assertIn("id_generation", self.categories(result))


class TestCliAndSelfConsistency(unittest.TestCase):
    """The checker run as a subprocess against the real repo, as a user would."""

    def test_cli_runs_clean_against_the_repo_and_exempts_util_py(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "aion_core", "--json"],
            shell=False, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertGreater(payload["files_scanned"], 10)
        util_hits = [f for f in payload["findings"] if f["file"].endswith("util.py")]
        self.assertEqual(util_hits, [], "aion_core/util.py must never flag itself")

    def test_cli_exits_zero_even_with_findings(self):
        """Advisory tool: findings are leads for a human, never a build failure."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "bridges", "--json"],
            shell=False, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
