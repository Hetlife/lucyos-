import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class TestUnlazyInstaller(unittest.TestCase):
    def test_install_check_drift_and_repair(self):
        repo = Path(__file__).resolve().parent.parent
        script = repo / "scripts" / "install_unlazy_skills.py"
        with tempfile.TemporaryDirectory(prefix="unlazy-home-") as tmp:
            env = dict(os.environ, HOME=tmp)
            install = subprocess.run(
                [sys.executable, str(script), "--install", "--target", "all", "--json"],
                cwd=repo, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(install.returncode, 0, install.stderr or install.stdout)
            data = json.loads(install.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(data["targets"]["claude"]["matches"])
            self.assertTrue(data["targets"]["codex"]["matches"])

            skill = Path(tmp) / ".codex" / "skills" / "unlazy" / "SKILL.md"
            skill.write_text(skill.read_text() + "\n# drift\n")
            check = subprocess.run(
                [sys.executable, str(script), "--check", "--target", "codex", "--json"],
                cwd=repo, env=env, capture_output=True, text=True, check=False)
            self.assertNotEqual(check.returncode, 0)
            self.assertFalse(json.loads(check.stdout)["ok"])

            repair = subprocess.run(
                [sys.executable, str(script), "--install", "--target", "codex", "--json"],
                cwd=repo, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(repair.returncode, 0, repair.stderr or repair.stdout)
            self.assertTrue(json.loads(repair.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
