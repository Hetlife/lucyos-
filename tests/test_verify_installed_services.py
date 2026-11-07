"""Tests for rendered systemd deployment verification."""
from __future__ import annotations
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_installed_services", ROOT / "scripts" / "verify_installed_services.py"
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)

class VerifyInstalledServicesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.home = base / "brain"
        self.units = base / "units"
        (self.repo / "systemd").mkdir(parents=True)
        self.units.mkdir()
        template = "WorkingDirectory=@REPO@\nEnvironment=AION_HOME=@AION_HOME@\n"
        for name in mod.UNITS:
            (self.repo / "systemd" / name).write_text(template)
            rendered = mod.render(template, repo=self.repo, aion_home=self.home)
            (self.units / name).write_text(rendered)

    def test_rendered_units_match(self):
        report = mod.verify(self.repo, self.repo, self.home, self.units)
        self.assertTrue(report["ok"], report)
        self.assertTrue(all(item["status"] == "match" for item in report["results"]))

    def test_detached_template_checkout_can_verify_installed_repo_path(self):
        installed_repo = Path(self.tmp.name) / "installed-repo"
        template = (self.repo / "systemd" / mod.UNITS[0]).read_text()
        for name in mod.UNITS:
            rendered = mod.render(template, repo=installed_repo, aion_home=self.home)
            (self.units / name).write_text(rendered)
        report = mod.verify(self.repo, installed_repo, self.home, self.units)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["template_repo"], str(self.repo))
        self.assertEqual(report["render_repo"], str(installed_repo))

    def test_raw_template_or_changed_unit_is_detected(self):
        name = mod.UNITS[0]
        (self.units / name).write_text((self.repo / "systemd" / name).read_text())
        report = mod.verify(self.repo, self.repo, self.home, self.units)
        self.assertFalse(report["ok"])
        self.assertIn({"unit": name, "status": "different"}, report["results"])

    def test_missing_installed_unit_is_detected(self):
        name = mod.UNITS[-1]
        (self.units / name).unlink()
        report = mod.verify(self.repo, self.repo, self.home, self.units)
        self.assertFalse(report["ok"])
        self.assertIn({"unit": name, "status": "missing-installed"}, report["results"])

if __name__ == "__main__":
    unittest.main()
