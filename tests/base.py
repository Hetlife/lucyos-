"""Test base: every test runs against a throwaway shared brain."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Environment variables that change AION's behaviour when read at call time.
# A test must never inherit these from whatever shell it happens to run in:
# otherwise the same commit passes on one machine and fails on another for
# reasons that have nothing to do with the code — which is exactly what
# `aion verify --deep` exists to rule out.  A developer machine with
# AION_CLOUD_CMD exported, for instance, gives the worker loop an executor
# the test explicitly set up to be absent.
ISOLATED_ENV = (
    "AION_HOME",
    "AION_DB",
    "AION_SECRETS",
    "AION_CLOUD_CMD",
    "AION_MACHINE",
    "OPENCLAW_HOME",
    "AION_CLAUDE_TELEMETRY_FILE",
    "AION_CODEX_TELEMETRY_FILE",
)


class AionTest(unittest.TestCase):
    def setUp(self):
        self._saved_env = {key: os.environ.get(key) for key in ISOLATED_ENV}
        for key in ISOLATED_ENV:
            os.environ.pop(key, None)
        self.tmp = Path(tempfile.mkdtemp(prefix="aion-test-"))
        os.environ["AION_HOME"] = str(self.tmp)
        from aion_core import db
        db.close()
        from aion_core import bootstrap
        bootstrap.ensure()

    def tearDown(self):
        from aion_core import db
        db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        # Restore, rather than just unset: the caller's environment is theirs.
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
