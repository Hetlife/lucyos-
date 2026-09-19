"""The test suite must give the same answer on every machine.

`aion verify --deep` runs this suite as a machine acceptance gate, so a test
that silently inherits the developer's shell environment turns that gate into
a coin flip: the same commit passes on one box and fails on another for
reasons that have nothing to do with LucyOS being sound.  These tests fail
loudly if that isolation is ever weakened.
"""
import os
import unittest
from unittest.mock import patch

from aion_core import config, worker
from tests.base import ISOLATED_ENV, AionTest


class TestHermeticEnvironment(AionTest):
    def test_cloud_worker_env_var_does_not_leak_into_tests(self):
        """The regression this guards: a machine with AION_CLOUD_CMD exported
        handed the worker loop an executor that tests had set up to be absent."""
        self.assertEqual(worker.cloud_command(), "",
                         "AION_CLOUD_CMD leaked in from the host environment")

    def test_every_isolated_var_is_actually_cleared(self):
        for key in ISOLATED_ENV:
            if key == "AION_HOME":
                continue  # deliberately set to the throwaway brain
            self.assertIsNone(os.environ.get(key),
                              f"{key} leaked in from the host environment")

    def test_aion_home_points_at_the_throwaway_brain(self):
        self.assertEqual(os.environ["AION_HOME"], str(self.tmp))
        self.assertEqual(config.home(), self.tmp)


class TestEnvironmentIsRestored(unittest.TestCase):
    """Isolation must not damage the caller's environment either."""

    def test_pre_existing_values_are_restored_after_a_test(self):
        original = {key: "host-setting-" + key for key in ISOLATED_ENV}
        with patch.dict(os.environ, original):
            case = _Probe("test_noop")
            result = unittest.TestResult()
            case.run(result)
            self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
            self.assertEqual({key: os.environ.get(key) for key in ISOLATED_ENV}, original)

    def test_absent_values_stay_absent_after_a_test(self):
        with patch.dict(os.environ):
            for key in ISOLATED_ENV:
                os.environ.pop(key, None)
            case = _Probe("test_noop")
            result = unittest.TestResult()
            case.run(result)
            self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
            for key in ISOLATED_ENV:
                self.assertNotIn(key, os.environ)

    def test_setup_failure_restores_environment_and_removes_temporary_home(self):
        original = {key: "host-setting-" + key for key in ISOLATED_ENV}
        with patch.dict(os.environ, original), patch(
                "aion_core.bootstrap.ensure", side_effect=RuntimeError("setup failed")):
            case = _Probe("test_noop")
            result = unittest.TestResult()
            case.run(result)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("setup failed", result.errors[0][1])
            self.assertFalse(case.tmp.exists())
            self.assertEqual({key: os.environ.get(key) for key in ISOLATED_ENV}, original)


class _Probe(AionTest):
    def test_noop(self):
        for key in ISOLATED_ENV:
            if key != "AION_HOME":
                self.assertNotIn(key, os.environ)
        self.assertEqual(config.home(), self.tmp)


if __name__ == "__main__":
    unittest.main()
