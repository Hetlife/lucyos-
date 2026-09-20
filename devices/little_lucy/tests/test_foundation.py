import tempfile
import time
import unittest
from pathlib import Path
from devices.little_lucy.emulator.server import STATIC
from devices.little_lucy.protocol.state import decode, encode
from devices.little_lucy.updater.releases import rollback, stage, status

class FoundationTests(unittest.TestCase):
    def test_protocol(self):
        value = dict(version=1, sequence=2, timestamp=time.time(), state='WORK', status='Working')
        self.assertEqual(decode(encode(value)), value)
        for bad in ({**value, 'secret':'hidden'}, {**value, 'status':'key=abc_123'}, {**value, 'timestamp':time.time()-30}):
            with self.assertRaises(ValueError): encode(bad)
    def test_emulator(self):
        html = (STATIC/'index.html').read_text()
        for item in ('width:480px;height:272px', 'RECONNECTING', 'OFFLINE'):
            self.assertIn(item, html)
    def test_release_and_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            root, source = Path(d)/'endpoint', Path(d)/'source'
            (source/'release').mkdir(parents=True)
            health = source/'release/health.py'
            health.write_text("print('healthy')\n")
            stage(root, source, 'v1')
            stage(root, source, 'v2')
            self.assertEqual(Path(status(root)['current']).name, 'v2')
            rollback(root)
            self.assertEqual(Path(status(root)['current']).name, 'v1')
            health.write_text('raise SystemExit(1)\n')
            with self.assertRaises(Exception): stage(root, source, 'bad')
            self.assertEqual(Path(status(root)['current']).name, 'v1')
            with self.assertRaises(ValueError): stage(root, source, '../escape')
