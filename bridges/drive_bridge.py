"""Bounded Google Drive exchange; never a live database or execution channel."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
import urllib.request

from aion_core import config, packets, security

REPO = Path(__file__).resolve().parents[1]
FOLDERS = ['00_INBOX', '01_LUCYOS', '02_STRATEGY_FACTORY', '03_CONTEXT',
           '04_REPORTS', '05_HANDOFFS', '06_APPROVALS', '99_ARCHIVE']
KINDS = {'handoffs': '05_HANDOFFS', 'reports': '04_REPORTS', 'context': '03_CONTEXT'}
LIMIT = 256 * 1024
BLOCK = re.compile(r'(?i)(private_state|secrets?\.env|^\.env|\.pem$|\.key$|id_(?:ed25519|rsa)|'
                   r'credential|cookie|oauth|rclone\.conf|token|api.?key|password|browser|'
                   r'banking|trading|session|^logs?$|\.log$|\.ssh|\.sqlite|\.db$)')
SENSITIVE = re.compile(r'(?i)(password|passwd|secret|token|credential|cookie|authorization|'
                       r'api.?key|private.?key|client.?secret|recovery.?code)')
EXTRA = re.compile(r'(?i)(ya29\.[\w.-]+|1//[\w-]{16,}|GOCSPX-[\w-]+|'
                   r'-----BEGIN [A-Z ]*PRIVATE KEY-----|https?://[^\s/]+:[^\s/]+@)')


class BridgeError(Exception):
    """Only fixed, non-sensitive error codes cross the CLI/log boundary."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.drive-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode()


def safe_path(name):
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or '\\' in name or len(name) > 240
            or any(x in ('', '.', '..') or x.startswith('.') or BLOCK.search(x)
                   for x in name.split('/'))
            or p.suffix.lower() not in ('.md', '.txt', '.json')
            or any(ord(c) < 32 for c in name) or security.scan_text(name)):
        raise BridgeError('rejected_path')
    return p


def check_json(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if SENSITIVE.search(k) and v not in (None, '', '[REDACTED]'):
                raise BridgeError('rejected_sensitive_field')
            check_json(v)
    elif isinstance(value, list):
        for v in value:
            check_json(v)


def clean(data, name):
    safe_path(name)
    if not data or len(data) > LIMIT:
        raise BridgeError('rejected_size')
    try:
        text = data.decode('utf-8')
    except UnicodeError:
        raise BridgeError('rejected_encoding') from None
    if any(ord(c) < 32 and c not in '\n\r\t' for c in text):
        raise BridgeError('rejected_binary')
    if security.scan_text(text) or EXTRA.search(text):
        raise BridgeError('rejected_secret')
    # Supplement AION's scanner for quoted JSON keys and opaque encoded payloads.
    if re.search(r'(?i)["\']?(?:password|secret|access_token|refresh_token|cookie|api_key)'
                 r'["\']?\s*[:=]\s*["\']?[^\s"\']{4,}', text):
        raise BridgeError('rejected_secret')
    for word in re.findall(r'[A-Za-z0-9+/=_-]{32,}', text):
        counts = Counter(word)
        entropy = -sum((n / len(word)) * math.log2(n / len(word)) for n in counts.values())
        if entropy > 4.3:
            raise BridgeError('rejected_opaque_content')
    if Path(name).suffix == '.json':
        try:
            check_json(json.loads(text))
        except (ValueError, RecursionError):
            raise BridgeError('rejected_json') from None
    return text


def read_safe(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or BLOCK.search(part.name):
            raise BridgeError('rejected_source')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > LIMIT:
            raise BridgeError('rejected_source')
        with os.fdopen(fd, 'rb', closefd=False) as f:
            data = f.read(LIMIT + 1)
    finally:
        os.close(fd)
    clean(data, path.name)
    return data


class Rclone:
    def __init__(self):
        self.binary = shutil.which('rclone') or str(Path.home() / '.local/bin/rclone')

    def run(self, *args):
        for attempt in range(3):
            try:
                # Never print rclone stderr: it may contain private paths or OAuth material.
                result = subprocess.run([self.binary, *args, '--retries', '1',
                    '--low-level-retries', '1', '--contimeout', '10s', '--timeout', '20s',
                    '--log-level', 'ERROR'], stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, timeout=45, check=False)
                if result.returncode == 0:
                    if len(result.stdout) > 4 * 1024 * 1024:
                        raise BridgeError('remote_listing_too_large')
                    return result.stdout
            except (subprocess.TimeoutExpired, OSError):
                pass
            if attempt < 2:
                time.sleep(2 ** attempt)
        raise BridgeError('remote_unavailable')

    def folders(self):
        for folder in FOLDERS:
            self.run('mkdir', 'gdrive:MARK2_SHARED/' + folder)

    def listing(self, folder):
        try:
            result = json.loads(self.run('lsjson', 'gdrive:MARK2_SHARED/' + folder,
                                        '--files-only', '--recursive', '--hash'))
            if not isinstance(result, list) or len(result) > 1000:
                raise ValueError()
            return result
        except (ValueError, TypeError):
            raise BridgeError('invalid_remote_listing') from None

    def get(self, folder, name):
        return self.run('cat', 'gdrive:MARK2_SHARED/' + folder + '/' + name,
                        '--head', str(LIMIT + 1))

    def put(self, folder, name, path):
        self.run('copyto', str(path), 'gdrive:MARK2_SHARED/' + folder + '/' + name,
                 '--no-traverse')


class Bridge:
    def __init__(self, root=None, remote=None):
        self.home = Path(root) if root else config.home()
        self.root = self.home / 'state/drive_bridge'
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        self.outbox = self.home / 'OUTBOX/drive'
        self.remote = remote or Rclone()
        self.ledger = self.root / 'ledger.json'
        self.state = {'version': 1, 'inbox': {}, 'uploads': {}, 'last_sync': None}

    @contextmanager
    def locked(self):
        with (self.root / 'bridge.lock').open('a') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise BridgeError('already_running') from None
            if self.ledger.exists():
                try:
                    self.state = json.loads(self.ledger.read_text())
                    if self.state['version'] != 1 or not all(
                            isinstance(self.state[k], dict) for k in ('inbox', 'uploads')):
                        raise ValueError()
                except (ValueError, KeyError):
                    raise BridgeError('invalid_ledger_restore_checkpoint') from None
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def save(self):
        atomic(self.ledger, json_bytes(self.state))

    def stage(self, kind, path):
        data = read_safe(path)
        h = digest(data)
        name = f'{Path(path).stem}-{h[:16]}{Path(path).suffix.lower()}'
        clean(data, name)
        atomic(self.outbox / kind / name, data)
        return {'staged': True, 'kind': kind}

    def pull(self):
        entries = self.remote.listing('00_INBOX')
        paths = Counter(e.get('Path') for e in entries)
        results = Counter()
        failures = False
        for e in entries:
            name = e.get('Path', '')
            # Never persist private remote names or rejection bodies in logs/ledger.
            identity = digest(str(name).encode())
            try:
                safe_path(name)
                if paths[name] != 1:
                    raise BridgeError('duplicate_remote_path')
                if e.get('Size', -1) < 0 or e['Size'] > LIMIT:
                    raise BridgeError('rejected_size_or_native_document')
                data = self.remote.get('00_INBOX', name)
                h = digest(data)
                key = identity + ':' + h
                existing = self.state['inbox'].get(key)
                if existing and existing['status'] in ('QUEUED', 'PROCESSED', 'FAILED'):
                    for folder in ('processed', 'failed'):
                        if (self.home / 'INBOX' / folder / existing['local']).exists():
                            existing['status'] = folder.upper()
                    if existing['status'] == 'QUEUED' and not (
                            self.home / 'INBOX/pending' / existing['local']).exists():
                        raise BridgeError('missing_local_delivery')
                    results['duplicates'] += 1
                    continue
                text = clean(data, name)
                if not text.startswith('# AI SYNC PACKET'):
                    raise BridgeError('malformed_packet')
                try:
                    parsed = packets.parse(text)
                except packets.PacketError:
                    raise BridgeError('malformed_packet') from None
                # Requests enter TRIAGE through the existing parser. No Drive approval
                # decisions, commands, canonical resume overrides, or asserted facts.
                allowed = {'TASKS CREATED', 'RESEARCH FINDINGS', 'RISKS', 'APPROVALS REQUIRED'}
                if not parsed['sections'] or set(parsed['sections']) - allowed:
                    raise BridgeError('unsupported_packet_section')
                if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',
                                    parsed['headers'].get('PROJECT', 'default')):
                    raise BridgeError('invalid_project')
                local = f'drive-{identity[:16]}-{h}.md'
                target = self.home / 'INBOX/pending' / local
                # Persist intent first; crash recovery uses the same immutable filename.
                self.state['inbox'][key] = {'status': 'DELIVERING', 'local': local,
                                            'updated_at': now()}
                self.save()
                found = False
                for folder in ('pending', 'processed', 'failed'):
                    candidate = self.home / 'INBOX' / folder / local
                    if candidate.exists():
                        if candidate.is_symlink() or digest(candidate.read_bytes()) != h:
                            raise BridgeError('local_conflict')
                        found = True
                        self.state['inbox'][key]['status'] = (
                            'QUEUED' if folder == 'pending' else folder.upper())
                        break
                if not found:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # Atomic link publishes complete bytes without replacing any file.
                    tmp = self.root / ('delivery-' + h)
                    atomic(tmp, data)
                    try:
                        os.link(tmp, target)
                    except FileExistsError:
                        raise BridgeError('local_conflict') from None
                    finally:
                        tmp.unlink(missing_ok=True)
                    dfd = os.open(target.parent, os.O_DIRECTORY)
                    try:
                        os.fsync(dfd)
                    finally:
                        os.close(dfd)
                    self.state['inbox'][key]['status'] = 'QUEUED'
                results['queued'] += 1
                self.save()
            except BridgeError as exc:
                self.state.setdefault('rejections', {})[identity] = {
                    'code': str(exc), 'updated_at': now()}
                self.save()
                failures = True
                results['rejected'] += 1
        self.save()
        if failures:
            raise BridgeError('inbox_items_rejected')
        return dict(results)

    def push(self, kind, only=None):
        folder = self.outbox / kind
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        count = 0
        for path in sorted(folder.iterdir()):
            if only is not None and path.name != only:
                continue
            data = read_safe(path)
            h = digest(data)
            name = path.name
            if name not in ('MARK2_STATUS.json', 'MARK2_BRIDGE_READY.md'):
                suffix = '-' + h[:16]
                if not path.stem.endswith(suffix):
                    name = path.stem + suffix + path.suffix
            key = kind + '/' + name
            if self.state['uploads'].get(key, {}).get('hash') == h:
                continue
            # A private snapshot prevents a concurrent producer swapping bytes after scan.
            with tempfile.TemporaryDirectory(dir=self.root) as tmp:
                snapshot = Path(tmp) / 'payload'
                atomic(snapshot, data)
                self.remote.put(KINDS[kind], name, snapshot)
                received = self.remote.get(KINDS[kind], name)
                if digest(received) != h:
                    raise BridgeError('upload_verification_failed')
            self.state['uploads'][key] = {'hash': h, 'updated_at': now()}
            self.save()
            count += 1
        return {'uploaded': count}

    def status(self):
        result = {'updated_at': now(), 'hostname': 'Mark-2', 'system_health': 'unknown',
                  'active_project': None, 'active_task': None, 'current_bottleneck': None,
                  'recently_completed': [], 'recent_failures': [], 'pending_approvals': 0,
                  'human_action_required': [], 'next_action': 'review_local_resume',
                  'ollama_status': 'unknown', 'git_status_summary': 'unknown',
                  'last_sync': self.state.get('last_sync'),
                  'resume_pointer': 'local:RESUME.md; local:state/drive_bridge/ledger.json'}
        dbfile = self.home / 'state/aion.sqlite3'
        try:
            with sqlite3.connect(dbfile.as_uri() + '?mode=ro', uri=True, timeout=2) as c:
                result['pending_approvals'] = c.execute(
                    "SELECT count(*) FROM approvals WHERE status='PENDING'").fetchone()[0]
                for field, query, pattern in [
                    ('recently_completed', "SELECT task_id FROM tasks WHERE status='DONE' ORDER BY completed_at DESC LIMIT 5", r'TASK-[A-F0-9]{8}'),
                    ('recent_failures', "SELECT error_id FROM errors WHERE status='OPEN' ORDER BY created_at DESC LIMIT 5", r'ERR-[A-F0-9]{8}')]:
                    result[field] = [r[0] for r in c.execute(query) if re.fullmatch(pattern, r[0])]
                row = c.execute("SELECT task_id, project FROM tasks WHERE status='IN_PROGRESS' LIMIT 1").fetchone()
                if row:
                    result['active_task'] = row[0] if re.fullmatch(r'TASK-[A-F0-9]{8}', row[0]) else None
                    result['active_project'] = row[1] if row[1] in ('default', 'lucyos', 'strategy-factory') else 'other'
                if not row:
                    resume_path = self.home / 'state/RESUME.json'
                    try:
                        current = json.loads(resume_path.read_text()).get('current_task', '')
                    except (OSError, ValueError):
                        current = ''
                    if isinstance(current, str) and re.fullmatch(r'TASK-[A-F0-9]{8}', current):
                        result['active_task'] = current
                        project = c.execute('SELECT project FROM tasks WHERE task_id=?', (current,)).fetchone()
                        if project:
                            result['active_project'] = project[0] if project[0] in ('default', 'lucyos', 'strategy-factory') else 'other'
                result['system_health'] = 'degraded' if result['recent_failures'] else 'database_ok'
        except (sqlite3.Error, ValueError):
            result['system_health'] = 'database_unavailable'
        if not (self.root / 'AUTH_VERIFIED').exists():
            result['human_action_required'] = ['GOOGLE_OAUTH']
            result['current_bottleneck'] = 'drive_authorization_pending'
            result['next_action'] = 'complete_google_authorization'
        elif result['recent_failures']:
            result['current_bottleneck'] = 'local_errors_require_review'
        try:
            with urllib.request.urlopen('http://127.0.0.1:11434/api/version', timeout=2) as r:
                result['ollama_status'] = 'running' if r.status == 200 else 'unavailable'
        except OSError:
            result['ollama_status'] = 'unavailable'
        try:
            p = subprocess.run(['git', '-C', str(REPO), 'status', '--porcelain'],
                               capture_output=True, timeout=5)
            if p.returncode == 0:
                result['git_status_summary'] = 'clean' if not p.stdout else 'modified'
        except (OSError, subprocess.TimeoutExpired):
            pass
        data = json_bytes(result)
        clean(data, 'MARK2_STATUS.json')
        atomic(self.outbox / 'context/MARK2_STATUS.json', data)
        return result

    def ready_handoff(self):
        if not (self.root / 'AUTH_VERIFIED').exists():
            return
        try:
            active = subprocess.run(['systemctl', '--user', 'is-active', '--quiet',
                                     'mark2-drive.timer'], capture_output=True, timeout=5).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            active = False
        data = ('# Mark-2 Drive bridge readiness\n\n'
                'Live Drive read/write and safe round-trip: verified.\n'
                'Automatic exchange timer: ' + ('active' if active else 'not active') + '.\n'
                'Canonical code: GitHub Hetlife/lucyos-.\n'
                'Canonical state: local AION shared brain; never stored on Drive.\n'
                'Transport: explicit scanned text packets; no approvals granted by Drive.\n'
                'Status: MARK2_SHARED/03_CONTEXT/MARK2_STATUS.json.\n'
                'Inbox: MARK2_SHARED/00_INBOX; AI SYNC PACKET text files enter local TRIAGE.\n'
                'Recovery: local state/drive_bridge/ledger.json and docs/DRIVE_BRIDGE.md.\n').encode()
        clean(data, 'MARK2_BRIDGE_READY.md')
        atomic(self.outbox / 'handoffs/MARK2_BRIDGE_READY.md', data)

    def push_status(self):
        self.status()
        return self.push('context', only='MARK2_STATUS.json')

    def test(self):
        self.remote.folders()
        data = b'Mark-2 safe Drive bridge round-trip test.\n'
        clean(data, 'MARK2_BRIDGE_TEST.txt')
        with tempfile.TemporaryDirectory(dir=self.root) as tmp:
            path = Path(tmp) / 'test.txt'
            atomic(path, data)
            self.remote.put('99_ARCHIVE', 'MARK2_BRIDGE_TEST.txt', path)
            if self.remote.get('99_ARCHIVE', 'MARK2_BRIDGE_TEST.txt') != data:
                raise BridgeError('round_trip_failed')
        atomic(self.root / 'AUTH_VERIFIED', json_bytes({'verified_at': now()}))
        self.ready_handoff()
        return {'round_trip': 'passed', 'folders': 'verified'}

    def sync(self):
        if not (self.root / 'AUTH_VERIFIED').exists():
            raise BridgeError('live_test_required')
        self.ready_handoff()
        failures = []
        # One blocked direction must not prevent independent safe exports.
        for action in [self.pull, lambda: self.push('handoffs'), lambda: self.push('reports'),
                       self.status, lambda: self.push('context')]:
            try:
                action()
            except BridgeError as exc:
                failures.append(str(exc))
        self.state['last_attempt'] = now()
        self.state['failures'] = failures
        if not failures:
            self.state['last_sync'] = now()
        self.save()
        if failures:
            raise BridgeError('sync_incomplete')
        return {'sync': 'ok'}


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['pull-inbox', 'push-handoffs', 'push-reports',
                   'push-context', 'push-status', 'status', 'test', 'sync', 'stage'])
    p.add_argument('--kind', choices=KINDS)
    p.add_argument('--file', type=Path)
    args = p.parse_args()
    try:
        bridge = Bridge()
        with bridge.locked():
            if args.operation == 'stage':
                if not args.kind or not args.file:
                    p.error('stage requires --kind and --file')
                result = bridge.stage(args.kind, args.file)
            elif args.operation == 'push-status':
                result = bridge.push_status()
            elif args.operation == 'push-handoffs':
                bridge.ready_handoff()
                result = bridge.push('handoffs')
            elif args.operation.startswith('push-'):
                result = bridge.push(args.operation[5:])
            elif args.operation == 'pull-inbox':
                result = bridge.pull()
            else:
                result = getattr(bridge, args.operation)()
        print(json.dumps(result, sort_keys=True))
        return 0
    except BridgeError as exc:
        print(json.dumps({'ok': False, 'code': str(exc)}))
        return 1
    except Exception:
        # No traceback or raw exception containing file contents/credentials.
        print(json.dumps({'ok': False, 'code': 'local_failure'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
