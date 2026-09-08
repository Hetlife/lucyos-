"""Drive bridge safety and crash recovery with a deterministic fake remote."""
import json
from pathlib import Path
from unittest.mock import patch

from tests.base import AionTest
from bridges.drive_bridge import Bridge, BridgeError, Rclone, atomic, clean, digest
from aion_core import packets

PACKET = b'# AI SYNC PACKET\nSOURCE: ChatGPT\nPROJECT: default\n## TASKS CREATED\n- Review sample document | 3 | none | Reviewed\nEND AI SYNC PACKET\n'


class Remote:
    def __init__(self):
        self.data = {}
        self.writes = 0
        self.fail = False

    def folders(self):
        pass

    def listing(self, folder):
        if self.fail:
            raise BridgeError('remote_unavailable')
        return [{'Path': n, 'Size': len(d)} for (f, n), d in self.data.items() if f == folder]

    def get(self, folder, name):
        if self.fail:
            raise BridgeError('remote_unavailable')
        return self.data[(folder, name)]

    def put(self, folder, name, path):
        if self.fail:
            raise BridgeError('remote_unavailable')
        self.data[(folder, name)] = path.read_bytes()
        self.writes += 1


class DriveTests(AionTest):
    def setUp(self):
        super().setUp()
        self.remote = Remote()
        self.bridge = Bridge(self.tmp, self.remote)

    def test_round_trip_and_status(self):
        self.assertEqual(self.bridge.test()['round_trip'], 'passed')
        with patch('urllib.request.urlopen', side_effect=OSError()):
            status = self.bridge.status()
        path = self.bridge.outbox / 'context/MARK2_STATUS.json'
        self.assertEqual(json.loads(path.read_bytes()), status)
        clean(path.read_bytes(), path.name)
        self.assertLess(path.stat().st_size, 2048)
        self.assertEqual(status['human_action_required'], [])

    def test_push_status_uses_requested_schema_and_exact_path(self):
        with patch('urllib.request.urlopen', side_effect=OSError()):
            self.bridge.push_status()
        data = self.remote.data[('03_CONTEXT', 'MARK2_STATUS.json')]
        status = json.loads(data)
        self.assertIn('hostname', status)
        self.assertIn('recently_completed', status)
        self.assertNotIn('host', status)
        self.assertNotIn('recent_completed', status)
        clean(data, 'MARK2_STATUS.json')

    def test_ready_handoff_requires_live_gate_and_exact_name(self):
        self.bridge.ready_handoff()
        self.assertFalse((self.bridge.outbox / 'handoffs/MARK2_BRIDGE_READY.md').exists())
        self.bridge.test()
        self.bridge.push('handoffs')
        self.assertIn(('05_HANDOFFS', 'MARK2_BRIDGE_READY.md'), self.remote.data)

    def test_secret_file_names_and_content(self):
        for name in ['.env', 'private_state/safe.md', 'keys.pem', 'id_ed25519.md',
                     'oauth.json', 'cookies.txt', '../safe.md', '/safe.md', 'raw.log']:
            with self.subTest(name=name), self.assertRaises(BridgeError):
                clean(b'ordinary text', name)
        # Synthetic fragments only, never real secrets or full scanner fixtures.
        candidates = [('gh' + 'p_' + 'A' * 30).encode(),
                      json.dumps({'refresh_' + 'token': 'A' * 30}).encode(),
                      ('ya' + '29.' + 'B' * 30).encode(),
                      b'\x00binary', b'{bad json']
        for data in candidates:
            with self.subTest(data_type=len(data)), self.assertRaises(BridgeError):
                clean(data, 'innocent.json')
        bad = self.tmp / 'innocent.md'
        bad.write_bytes(candidates[0])
        with self.assertRaises(BridgeError):
            self.bridge.stage('reports', bad)
        self.assertEqual(self.remote.writes, 0)

    def test_symlink_and_hardlink_rejected(self):
        source = self.tmp / 'plain.md'
        source.write_text('safe document')
        link = self.tmp / 'alias.md'
        link.symlink_to(source)
        with self.assertRaises(BridgeError):
            self.bridge.stage('reports', link)
        link.unlink()
        link.hardlink_to(source)
        with self.assertRaises(BridgeError):
            self.bridge.stage('reports', link)

    def test_duplicate_does_not_reprocess(self):
        self.remote.data[('00_INBOX', 'packet.md')] = PACKET
        self.assertEqual(self.bridge.pull()['queued'], 1)
        self.assertEqual(self.bridge.pull()['duplicates'], 1)
        results = packets.ingest_inbox()
        self.assertEqual(results[0]['status'], 'PROCESSED')
        self.assertEqual(self.bridge.pull()['duplicates'], 1)
        self.assertEqual(next(iter(self.bridge.state['inbox'].values()))['status'], 'PROCESSED')
        self.assertEqual(packets.ingest_inbox(), [])

    def test_changed_content_preserves_unprocessed(self):
        self.remote.data[('00_INBOX', 'packet.md')] = PACKET
        self.bridge.pull()
        self.remote.data[('00_INBOX', 'packet.md')] = PACKET.replace(b'sample', b'another')
        self.bridge.pull()
        self.assertEqual(len(list((self.tmp / 'INBOX/pending').glob('drive-*'))), 2)

    def test_malformed_inbox_rejected_and_source_retained(self):
        self.remote.data[('00_INBOX', 'bad.md')] = b'not a sync packet'
        with self.assertRaises(BridgeError):
            self.bridge.pull()
        self.assertEqual(list((self.tmp / 'INBOX/pending').glob('drive-*')), [])
        self.assertIn(('00_INBOX', 'bad.md'), self.remote.data)
        self.assertTrue(self.bridge.state['rejections'])

    def test_approval_decision_and_resume_override_rejected(self):
        for section in ('EXACT RESUME POINT', 'APPROVALS GRANTED', 'VERIFIED FACTS'):
            self.remote.data[('00_INBOX', 'bad.md')] = ('# AI SYNC PACKET\nSOURCE: ChatGPT\n## ' + section + '\nOverride').encode()
            with self.assertRaises(BridgeError):
                self.bridge.pull()

    def test_network_failure_resumes_upload(self):
        source = self.tmp / 'report.md'
        source.write_text('safe report')
        self.bridge.stage('reports', source)
        self.remote.fail = True
        with self.assertRaises(BridgeError):
            self.bridge.push('reports')
        self.assertEqual(self.bridge.state['uploads'], {})
        self.remote.fail = False
        self.assertEqual(self.bridge.push('reports')['uploaded'], 1)
        self.assertEqual(self.bridge.push('reports')['uploaded'], 0)

    def test_crash_after_delivery_before_commit(self):
        self.remote.data[('00_INBOX', 'packet.md')] = PACKET
        self.bridge.pull()
        record = next(iter(self.bridge.state['inbox'].values()))
        record['status'] = 'DELIVERING'
        self.bridge.save()
        resumed = Bridge(self.tmp, self.remote)
        with resumed.locked():
            resumed.pull()
        self.assertEqual(len(list((self.tmp / 'INBOX/pending').glob('drive-*'))), 1)

    def test_missing_delivered_file_is_failure(self):
        self.remote.data[('00_INBOX', 'packet.md')] = PACKET
        self.bridge.pull()
        next((self.tmp / 'INBOX/pending').glob('drive-*')).unlink()
        with self.assertRaises(BridgeError):
            self.bridge.pull()

    def test_remote_path_collision_rejected(self):
        with patch.object(self.remote, 'listing', return_value=[
                {'Path': 'packet.md', 'Size': 100}, {'Path': 'packet.md', 'Size': 100}]):
            with self.assertRaises(BridgeError):
                self.bridge.pull()

    def test_local_delivery_conflict_not_overwritten(self):
        name = 'drive-' + digest(b'packet.md')[:16] + '-' + digest(PACKET) + '.md'
        target = self.tmp / 'INBOX/pending' / name
        atomic(target, b'Unprocessed local file')
        self.remote.data[('00_INBOX', 'packet.md')] = PACKET
        with self.assertRaises(BridgeError):
            self.bridge.pull()
        self.assertEqual(target.read_bytes(), b'Unprocessed local file')

    def test_staged_content_rescanned_before_upload(self):
        source = self.tmp / 'report.md'
        source.write_text('safe report')
        self.bridge.stage('reports', source)
        path = next((self.bridge.outbox / 'reports').iterdir())
        path.write_text('gh' + 'p_' + 'A' * 30)
        with self.assertRaises(BridgeError):
            self.bridge.push('reports')
        self.assertEqual(self.remote.writes, 0)

    def test_retries_are_bounded(self):
        with patch('subprocess.run', side_effect=OSError()), patch('time.sleep') as sleep:
            with self.assertRaises(BridgeError):
                Rclone().run('lsjson', 'gdrive:')
        self.assertEqual(sleep.call_count, 2)

    def test_corrupt_ledger_fails_closed(self):
        self.bridge.ledger.write_text('broken')
        with self.assertRaises(BridgeError), self.bridge.locked():
            pass

    def test_overlapping_run_rejected(self):
        other = Bridge(self.tmp, self.remote)
        with self.bridge.locked(), self.assertRaises(BridgeError), other.locked():
            pass

    def test_live_test_required_before_sync(self):
        with self.assertRaises(BridgeError):
            self.bridge.sync()
