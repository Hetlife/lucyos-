"""The test suite must give the same answer on every machine.

`aion verify --deep` runs this suite as a machine acceptance gate, so a test
that silently inherits the developer's shell environment turns that gate into
a coin flip: the same commit passes on one box and fails on another for
reasons that have nothing to do with LucyOS being sound.  These tests fail
loudly if that isolation is ever weakened.
"""
import os
import unittest

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

    def test_pre_existing_value_is_restored_after_a_test(self):
        os.environ["AION_CLOUD_CMD"] = "owner's real setting"
        try:
            case = _Probe("test_noop")
            case.setUp()
            leaked = os.environ.get("AION_CLOUD_CMD")
            case.tearDown()
            self.assertIsNone(leaked, "must be cleared during the test")
            self.assertEqual(os.environ.get("AION_CLOUD_CMD"), "owner's real setting",
                             "must be restored afterwards")
        finally:
            os.environ.pop("AION_CLOUD_CMD", None)

    def test_absent_value_stays_absent_after_a_test(self):
        os.environ.pop("AION_CLOUD_CMD", None)
        case = _Probe("test_noop")
        case.setUp()
        case.tearDown()
        self.assertNotIn("AION_CLOUD_CMD", os.environ)


class _Probe(AionTest):
    def test_noop(self):
        pass


if __name__ == "__main__":
    unittest.main()
