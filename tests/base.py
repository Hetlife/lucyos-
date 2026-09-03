"""Test base: every test runs against a throwaway shared brain."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path


class AionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aion-test-"))
        os.environ["AION_HOME"] = str(self.tmp)
        os.environ.pop("AION_DB", None)
        from aion_core import db
        db.close()
        from aion_core import bootstrap
        bootstrap.ensure()

    def tearDown(self):
        from aion_core import db
        db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("AION_HOME", None)
