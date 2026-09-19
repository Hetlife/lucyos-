import os
import unittest

from aion_core import backup, bootstrap, health, verify
from tests.base import AionTest


class TestMachineIdentity(AionTest):
    def test_machine_reports_measurable_identity(self):
        m = verify.machine()
        for field in ("hostname", "platform", "arch", "python", "repo_path", "aion_home"):
            self.assertTrue(m[field], f"{field} must be measured, not blank")
        self.assertEqual(m["aion_home"], str(self.tmp))

    def test_label_defaults_to_unlabelled_rather_than_a_guess(self):
        os.environ.pop("AION_MACHINE", None)
        self.assertEqual(verify.machine()["label"], "unlabelled")

    def test_label_is_read_from_the_environment(self):
        os.environ["AION_MACHINE"] = "lucy-den"
        try:
            self.assertEqual(verify.machine()["label"], "lucy-den")
        finally:
            os.environ.pop("AION_MACHINE", None)


class TestOpenClawDetection(AionTest):
    def test_shared_brain_alone_is_not_evidence_of_openclaw(self):
        # AION's own state lives in <openclaw home>/shared_brain. Its presence
        # says nothing about whether OpenClaw itself is installed.
        home = self.tmp / "openclaw_home"
        (home / "shared_brain").mkdir(parents=True)
        os.environ["OPENCLAW_HOME"] = str(home)
        original_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(self.tmp / "empty-bin")
        try:
            result = verify.openclaw()
            self.assertFalse(result["present"])
            self.assertEqual(result["home_contents"], [])
        finally:
            os.environ["PATH"] = original_path
            os.environ.pop("OPENCLAW_HOME", None)

    def test_other_contents_do_count_as_evidence(self):
        home = self.tmp / "openclaw_home2"
        (home / "shared_brain").mkdir(parents=True)
        (home / "agent").mkdir()
        os.environ["OPENCLAW_HOME"] = str(home)
        try:
            result = verify.openclaw()
            self.assertTrue(result["present"])
            self.assertIn("agent", result["home_contents"])
        finally:
            os.environ.pop("OPENCLAW_HOME", None)


class TestClassification(AionTest):
    def test_blocking_setup_and_optional_are_separated(self):
        report = {"checks": [
            {"name": "database", "ok": False, "detail": "corrupt"},
            {"name": "secret_store", "ok": False, "detail": "missing"},
            {"name": "ollama", "ok": False, "detail": "not installed"},
            {"name": "disk", "ok": True, "detail": "fine"},
        ]}
        tiers = verify.classify(report)
        self.assertEqual([e["name"] for e in tiers["blocking"]], ["database"])
        self.assertEqual([e["name"] for e in tiers["setup_required"]], ["secret_store"])
        self.assertEqual([e["name"] for e in tiers["optional"]], ["ollama"])

    def test_setup_required_entries_carry_the_exact_fix_command(self):
        report = {"checks": [{"name": "secret_store", "ok": False, "detail": "missing"}]}
        tiers = verify.classify(report)
        self.assertEqual(tiers["setup_required"][0]["fix"], "aion secrets init")

    def test_passing_checks_are_not_reported_as_problems(self):
        report = {"checks": [{"name": "database", "ok": True, "detail": "fine"}]}
        tiers = verify.classify(report)
        self.assertEqual(tiers["blocking"], [])


class TestVerdicts(AionTest):
    def test_fresh_install_is_setup_required_not_broken(self):
        """A brand new machine is sound; it just has owner steps outstanding."""
        result = verify.run()
        self.assertEqual(result["verdict"], "SETUP_REQUIRED")
        self.assertEqual(result["exit_code"], 1)
        fixes = {e["fix"] for e in result["tiers"]["setup_required"]}
        self.assertIn("aion secrets init", fixes)
        self.assertIn("aion backup", fixes)

    def test_machine_becomes_ready_once_owner_setup_is_done(self):
        bootstrap.init_secret_store()
        backup.create()
        result = verify.run()
        self.assertEqual(result["verdict"], "READY")
        self.assertEqual(result["exit_code"], 0)

    def test_blocking_failure_is_broken(self):
        original = health.run_all
        health.run_all = lambda deep=False: {
            "healthy": False, "failing": ["database"],
            "checks": [{"name": "database", "ok": False, "detail": "integrity_check failed"}]}
        try:
            result = verify.run()
        finally:
            health.run_all = original
        self.assertEqual(result["verdict"], "BROKEN")
        self.assertEqual(result["exit_code"], 2)

    def test_verify_never_raises_even_if_health_itself_crashes(self):
        """This is the diagnostic of last resort: a broken machine must still
        get a readable verdict rather than a traceback."""
        original = health.run_all

        def explode(deep=False):
            raise RuntimeError("file is not a database")

        health.run_all = explode
        try:
            result = verify.run()
        finally:
            health.run_all = original
        self.assertEqual(result["verdict"], "BROKEN")
        self.assertIn("file is not a database", result["tiers"]["blocking"][0]["detail"])

    def test_failing_tests_make_an_otherwise_ready_machine_broken(self):
        bootstrap.init_secret_store()
        backup.create()
        original = verify.run_tests
        verify.run_tests = lambda repo: {"ran": True, "ok": False,
                                         "detail": "FAILED (failures=3)", "count": 258}
        try:
            result = verify.run(deep=True)
        finally:
            verify.run_tests = original
        self.assertEqual(result["verdict"], "BROKEN")


class TestTestSummaryParsing(AionTest):
    def test_summary_prefers_unittest_verdict_over_stray_output(self):
        output = "Ran 258 tests in 17.5s\n\nOK\n"
        self.assertEqual(verify._summary_line(output), "OK")

    def test_summary_finds_failure_line(self):
        output = "Ran 258 tests in 17.5s\n\nFAILED (failures=2)\n"
        self.assertEqual(verify._summary_line(output), "FAILED (failures=2)")

    def test_stray_test_stdout_is_not_mistaken_for_a_verdict(self):
        output = "Ran 5 tests\n\nOK\nStrong-model build spend: INR 0.0\n"
        self.assertEqual(verify._summary_line(output), "OK")

    def test_count_is_extracted(self):
        self.assertEqual(verify._test_count("Ran 258 tests in 17.5s"), 258)

    def test_missing_summary_says_so_rather_than_inventing_one(self):
        self.assertEqual(verify._summary_line("no useful output"),
                         "no unittest summary found")


class TestRender(AionTest):
    def test_render_names_the_verdict_and_the_fixes(self):
        text = verify.render(verify.run())
        self.assertIn("SETUP_REQUIRED", text)
        self.assertIn("aion secrets init", text)
        self.assertIn("Test suite: not run", text)


if __name__ == "__main__":
    unittest.main()
