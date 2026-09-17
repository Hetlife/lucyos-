"""S-05: macOS launchd units mirroring systemd -- validated with plistlib
(stdlib) so this runs on Linux too, not just macOS."""
import plistlib
import unittest
from pathlib import Path

LAUNCHD_DIR = Path(__file__).resolve().parent.parent / "deploy" / "launchd"

EXPECTED_UNITS = {
    "com.lucyos.aion-work.plist",
    "com.lucyos.aion-maintenance.plist",
    "com.lucyos.aion-bridge.plist",
    "com.lucyos.aion-interface.plist",
}

_KNOWN_SYSTEM_BINARIES = ("/bin/bash", "/usr/bin/python3")


def _load(name: str) -> dict:
    with open(LAUNCHD_DIR / name, "rb") as f:
        return plistlib.load(f)


def _path_bearing_strings(d: dict):
    """Yield only the plist fields that are meant to hold filesystem paths --
    not Label (a reverse-DNS name) or PATH (a system search list of standard
    bin directories, not a reference to this checkout or AION_HOME)."""
    yield from d.get("ProgramArguments", [])
    if "WorkingDirectory" in d:
        yield d["WorkingDirectory"]
    if "StandardOutPath" in d:
        yield d["StandardOutPath"]
    if "StandardErrorPath" in d:
        yield d["StandardErrorPath"]
    env = d.get("EnvironmentVariables", {})
    if "AION_HOME" in env:
        yield env["AION_HOME"]


class LaunchdUnitsTest(unittest.TestCase):
    def test_all_four_units_have_a_plist_counterpart(self):
        present = {p.name for p in LAUNCHD_DIR.glob("*.plist")}
        self.assertEqual(present, EXPECTED_UNITS)

    def test_every_plist_parses_with_plistlib(self):
        for name in EXPECTED_UNITS:
            with self.subTest(name=name):
                d = _load(name)
                self.assertIsInstance(d, dict)
                self.assertIn("Label", d)
                self.assertEqual(d["Label"], name.removesuffix(".plist"))

    def test_program_arguments_zero_is_non_empty(self):
        for name in EXPECTED_UNITS:
            with self.subTest(name=name):
                d = _load(name)
                args = d.get("ProgramArguments")
                self.assertIsInstance(args, list)
                self.assertTrue(args)
                self.assertTrue(args[0], f"{name}: ProgramArguments[0] is empty")

    def test_program_arguments_are_placeholder_substitutable(self):
        """After a sed-style substitution of @REPO@/@AION_HOME@, no leftover
        placeholder token or empty argv[0] should remain -- proves the
        install script's substitution actually resolves every argument."""
        repo, home = "/opt/lucyos-checkout", "/home/owner/openclaw/shared_brain"
        for name in EXPECTED_UNITS:
            with self.subTest(name=name):
                d = _load(name)
                args = d["ProgramArguments"]
                substituted = [a.replace("@REPO@", repo).replace("@AION_HOME@", home) for a in args]
                self.assertTrue(substituted[0])
                for a in substituted:
                    self.assertNotIn("@REPO@", a)
                    self.assertNotIn("@AION_HOME@", a)

    def test_no_path_outside_the_placeholder_convention(self):
        """Every absolute path in the plist is either a known system binary
        or carries an @REPO@/@AION_HOME@ placeholder -- never a baked-in
        host-specific path."""
        for name in EXPECTED_UNITS:
            with self.subTest(name=name):
                d = _load(name)
                for s in _path_bearing_strings(d):
                    if not s.startswith("/"):
                        continue
                    if s in _KNOWN_SYSTEM_BINARIES:
                        continue
                    self.assertTrue(
                        "@REPO@" in s or "@AION_HOME@" in s,
                        f"{name}: hard-coded absolute path with no placeholder: {s!r}",
                    )

    def test_scheduling_keys_match_the_translation_table(self):
        work = _load("com.lucyos.aion-work.plist")
        self.assertTrue(work.get("RunAtLoad"))
        self.assertNotIn("StartCalendarInterval", work)

        maint = _load("com.lucyos.aion-maintenance.plist")
        self.assertEqual(maint.get("StartCalendarInterval"), {"Hour": 3, "Minute": 15})

        for name in ("com.lucyos.aion-bridge.plist", "com.lucyos.aion-interface.plist"):
            d = _load(name)
            self.assertTrue(d.get("RunAtLoad"))
            self.assertTrue(d.get("KeepAlive"))

    def test_logs_go_under_aion_home_placeholder(self):
        for name in EXPECTED_UNITS:
            with self.subTest(name=name):
                d = _load(name)
                for key in ("StandardOutPath", "StandardErrorPath"):
                    self.assertIn(key, d)
                    self.assertTrue(d[key].startswith("@AION_HOME@/logs/"))

    def test_no_mark2_units_present(self):
        for p in LAUNCHD_DIR.glob("*.plist"):
            self.assertNotIn("mark2", p.name)


class InstallServicesScriptTest(unittest.TestCase):
    def test_darwin_branch_present_and_linux_branch_unchanged(self):
        script = (Path(__file__).resolve().parent.parent / "scripts" / "install_services.sh").read_text()
        self.assertIn('uname)" == "Darwin"', script)
        self.assertIn("deploy/launchd/${plist}", script)
        # The pre-existing Linux install path must still be intact, byte for byte.
        self.assertIn(
            'for unit in aion-bridge.service aion-interface.service aion-maintenance.service '
            'aion-maintenance.timer \\\n            aion-work.service aion-work.timer; do',
            script,
        )
        self.assertIn("systemctl --user daemon-reload", script)
        self.assertIn("loginctl enable-linger", script)


if __name__ == "__main__":
    unittest.main()
