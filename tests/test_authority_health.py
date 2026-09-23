"""Runtime health must stay separate from authority/deploy readiness (R-03).

A local runtime can be sound (database intact, no stale claims, no errors)
while protected-file hashes have drifted since the last freeze. The
authority check must surface that drift without ever landing in the
BLOCKING tier, and deploy readiness must stay an explicit, opt-in field
that never changes the ordinary READY/SETUP_REQUIRED/BROKEN verdict.
"""
import unittest
from unittest import mock

from aion_core import bootstrap, backup, health
from tests.base import AionTest


def _fake_authority(ok: bool, violations=None, extra=None):
    report = {"ok": ok, "violations": violations or []}
    if extra:
        report.update(extra)
    return report


class TestAuthorityCheckIsVisibleNotBlocking(AionTest):
    def test_authority_is_never_a_blocking_check(self):
        self.assertNotIn("authority", health.BLOCKING)
        self.assertNotIn("authority", health.SETUP_REQUIRED)

    def test_drift_is_reported_but_check_still_reachable(self):
        with mock.patch.object(health, "_run_authority",
                                return_value=_fake_authority(False, ["aion_core/db.py: hash drift"])):
            result = health.check_authority()
        self.assertEqual(result["name"], "authority")
        self.assertFalse(result["ok"])
        self.assertIn("hash drift", result["detail"])
        self.assertFalse(result.get("required", True))

    def test_clean_authority_reports_no_drift(self):
        with mock.patch.object(health, "_run_authority", return_value=_fake_authority(True)):
            result = health.check_authority()
        self.assertTrue(result["ok"])
        self.assertEqual(result["detail"], "no drift")

    def test_authority_drift_alone_does_not_break_an_otherwise_sound_machine(self):
        bootstrap.init_secret_store()
        backup.create()
        with mock.patch.object(health, "_run_authority",
                                return_value=_fake_authority(False, ["aion_core/db.py: hash drift"])):
            result = health.verify()
        self.assertEqual(result["verdict"], "READY")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("authority", {e["name"] for e in result["tiers"]["optional"]})

    def test_verifier_crash_or_bad_output_degrades_to_a_reported_failure(self):
        with mock.patch.object(health, "_run", return_value=(1, "not json")):
            result = health.check_authority()
        self.assertFalse(result["ok"])
        self.assertIn("not json", result["detail"]) or self.assertTrue(result["detail"])


class TestRunAllHonoursRequiredFalse(AionTest):
    """`run_all().healthy` must reflect required checks only (R-03).

    `check_authority` (and check_ollama/check_openclaw/check_drive_bridge)
    are `required: False` by design: they degrade gracefully. A non-required
    check failing is advisory and must not flip the overall runtime healthy
    flag to False, while a required check failing still must.
    """

    def test_authority_drift_alone_leaves_run_all_healthy(self):
        bootstrap.init_secret_store()
        backup.create()
        with mock.patch.object(health, "_run_authority",
                                return_value=_fake_authority(False, ["aion_core/db.py: hash drift"])):
            report = health.run_all()
        self.assertTrue(report["healthy"])
        self.assertIn("authority", report["failing"])
        self.assertNotIn("authority", report["required_failing"])
        names = {c["name"]: c for c in report["checks"]}
        self.assertFalse(names["authority"]["ok"])

    def test_a_required_check_failing_still_breaks_run_all(self):
        from collections import namedtuple
        Usage = namedtuple("Usage", "total used free")
        with mock.patch.object(health.shutil, "disk_usage", return_value=Usage(0, 0, 0)):
            report = health.run_all()
        self.assertFalse(report["healthy"])
        self.assertIn("disk", report["required_failing"])
        self.assertIn("disk", report["failing"])

    def test_ollama_failing_is_advisory_not_required(self):
        """Ollama (and OpenClaw/Drive) are advisory too: prove it explicitly
        rather than relying on it as a side effect of the authority fix."""
        bootstrap.init_secret_store()
        backup.create()
        with mock.patch.object(health, "_run", return_value=(0, "NAME\n")):
            report = health.run_all()
        names = {c["name"]: c for c in report["checks"]}
        self.assertFalse(names["ollama"]["ok"])  # header line only -> no models
        self.assertNotIn("ollama", report["required_failing"])
        self.assertIn("ollama", report["failing"])
        self.assertTrue(report["healthy"])


class TestDeployReadinessIsExplicitAndOptIn(AionTest):
    def test_verify_without_the_flag_has_no_deploy_readiness_field(self):
        result = health.verify()
        self.assertNotIn("deploy_readiness", result)

    def test_verify_with_the_flag_surfaces_drift_as_not_ready(self):
        with mock.patch.object(health, "deploy_readiness",
                                return_value={"ready": False, "fable_freeze_sha": "abc123",
                                              "violations": ["aion_core/db.py: hash drift"]}):
            result = health.verify(deploy_readiness_check=True)
        self.assertIn("deploy_readiness", result)
        self.assertFalse(result["deploy_readiness"]["ready"])
        self.assertIn("hash drift", result["deploy_readiness"]["violations"][0])

    def test_deploy_readiness_never_changes_the_runtime_verdict(self):
        bootstrap.init_secret_store()
        backup.create()
        with mock.patch.object(health, "deploy_readiness",
                                return_value={"ready": False, "fable_freeze_sha": "abc123",
                                              "violations": ["drift"]}):
            result = health.verify(deploy_readiness_check=True)
        self.assertEqual(result["verdict"], "READY")
        self.assertEqual(result["exit_code"], 0)

    def test_deploy_readiness_calls_the_existing_verifier_not_a_reimplementation(self):
        with mock.patch.object(health, "_run_authority", return_value=_fake_authority(
                False, ["x: hash drift"], {"fable_freeze_sha": "deadbeef"})) as m:
            result = health.deploy_readiness()
        m.assert_called_once_with(["deploy"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["fable_freeze_sha"], "deadbeef")

    def test_render_shows_deploy_readiness_only_when_present(self):
        result = health.verify()
        text = health.render_verify(result)
        self.assertNotIn("Deploy readiness", text)

        with mock.patch.object(health, "deploy_readiness",
                                return_value={"ready": False, "fable_freeze_sha": "abc",
                                              "violations": ["drift"]}):
            result2 = health.verify(deploy_readiness_check=True)
        text2 = health.render_verify(result2)
        self.assertIn("Deploy readiness", text2)
        self.assertIn("NOT READY", text2)


if __name__ == "__main__":
    unittest.main()
