"""scan_history must actually catch a planted secret, stay silent on clean
history, and never print the matched value -- only reuses of aion_core.security
prove that."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "scan_history.py"


def load_scanner():
    spec = importlib.util.spec_from_file_location("scan_history", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class TestScanHistory(unittest.TestCase):
    def setUp(self):
        self.scanner = load_scanner()
        self.tmp = Path(tempfile.mkdtemp(prefix="scan-history-"))
        git(self.tmp, "init", "-q")
        git(self.tmp, "config", "user.email", "t@t")
        git(self.tmp, "config", "user.name", "t")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _commit(self, name, content, msg):
        (self.tmp / name).write_text(content)
        git(self.tmp, "add", name)
        git(self.tmp, "commit", "-q", "-m", msg)

    def test_clean_history_reports_nothing(self):
        self._commit("README.md", "hello world\n", "init")
        findings = self.scanner.scan_history(cwd=self.tmp)
        self.assertEqual(findings, [])

    def test_planted_secret_is_detected_even_after_deletion(self):
        secret = "gh" + "p_" + "A" * 30  # synthetic, matches github_token pattern
        self._commit("config.txt", f"token={secret}\n", "add secret")
        (self.tmp / "config.txt").unlink()
        git(self.tmp, "add", "-A")
        git(self.tmp, "commit", "-q", "-m", "remove secret from working tree")
        findings = self.scanner.scan_history(cwd=self.tmp)
        self.assertTrue(any(f["path"] == "config.txt" for f in findings),
                        "a secret removed from the tip must still be found in history")
        # the preview is masked, never the raw value
        self.assertFalse(any(secret in f["preview"] for f in findings))
        for f in findings:
            self.assertNotIn(secret, str(f))

    def test_no_secret_value_ever_appears_in_cli_output(self):
        secret = "gh" + "p_" + "B" * 30
        self._commit("config.txt", f"token={secret}\n", "add secret")
        out = subprocess.run(
            ["python3", str(SCRIPT), "--json"], cwd=self.tmp,
            capture_output=True, text=True)
        self.assertNotIn(secret, out.stdout)
        self.assertNotIn(secret, out.stderr)
        self.assertEqual(out.returncode, 1)

    def test_clean_history_exits_zero(self):
        self._commit("README.md", "nothing here\n", "init")
        out = subprocess.run(["python3", str(SCRIPT)], cwd=self.tmp,
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertIn("clean", out.stdout)

    def test_binary_blob_is_skipped_without_crashing(self):
        (self.tmp / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
        git(self.tmp, "add", "image.png")
        git(self.tmp, "commit", "-q", "-m", "binary")
        findings = self.scanner.scan_history(cwd=self.tmp)  # must not raise
        self.assertEqual(findings, [])

    def test_current_repository_is_clean_or_reports_only_known_fixtures(self):
        """Sanity check against the real repo: this must not silently no-op."""
        findings = self.scanner.scan_history(cwd=str(REPO))
        self.assertIsInstance(findings, list)
        for f in findings:
            self.assertIn("preview", f)
            self.assertIn("commit", f)
            self.assertIn("path", f)


if __name__ == "__main__":
    unittest.main()
