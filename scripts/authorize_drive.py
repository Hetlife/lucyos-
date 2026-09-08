#!/usr/bin/env python3
"""Import a locally supplied Desktop OAuth client and start private browser authorization.
Run only with a browser connection/tunnel to Mark-2 localhost port 53682 ready.
Never prints client material or authentication output other than the local login URL.
"""
import argparse
import configparser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridges.drive_bridge import atomic


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--client-file', type=Path, required=True)
    args = p.parse_args()
    source = args.client_file
    if source.is_symlink() or source.stat().st_mode & 0o077 or source.stat().st_size > 16384:
        raise ValueError()
    client = json.loads(source.read_bytes())['installed']
    if not client['client_id'].endswith('.apps.googleusercontent.com') or not client['client_secret']:
        raise ValueError()
    path = Path.home() / '.config/rclone/rclone.conf'
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(path)
    if not cfg.has_section('gdrive'):
        cfg.add_section('gdrive')
    if cfg.get('gdrive', 'token', fallback=''):
        print('Existing authorization found; verify with mark2-drive test.')
        return 0
    cfg['gdrive'].update(type='drive', scope='drive', client_id=client['client_id'],
                         client_secret=client['client_secret'])
    import io
    content = io.StringIO()
    cfg.write(content)
    atomic(path, content.getvalue().encode())
    # Suppress output: rclone can otherwise dump configuration after authorization.
    command = [str(Path.home() / '.local/bin/rclone'), 'config', 'update', 'gdrive',
               'config_is_local', 'true', 'config_auth_no_browser', 'true', '--no-output']
    print('Waiting for Google browser authorization on Mark-2 localhost:53682.', flush=True)
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True) as proc:
        deadline = threading.Timer(600, proc.terminate)
        deadline.start()
        for line in proc.stdout:
            match = re.search(r'http://(?:127\.0\.0\.1|localhost):53682/auth\?state=[A-Za-z0-9_-]+', line)
            if match:
                print(match.group(0), flush=True)
        code = proc.wait()
        deadline.cancel()
    path.chmod(0o600)
    print('Authorization command completed; live verification still required.' if code == 0
          else 'Authorization failed; no credentials printed.')
    return code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('Authorization setup failed; check protected Desktop client file locally.')
        raise SystemExit(1)
