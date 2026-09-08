#!/bin/sh
# Separate opt-in installer; never touches the canonical AION loop units.
set -eu
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export REPO
python3 - <<'PY'
import os
from pathlib import Path
repo = Path(os.environ['REPO'])
brain = Path(os.environ.get('AION_HOME', '/root/openclaw/shared_brain'))
units = Path.home() / '.config/systemd/user'
units.mkdir(parents=True, exist_ok=True)
for name in ('mark2-drive.service', 'mark2-drive.timer'):
    text = (repo / 'systemd' / name).read_text()
    (units / name).write_text(text.replace('@REPO@', str(repo)).replace('@AION_HOME@', str(brain)))
for sub in ('state/drive_bridge', 'INBOX/pending', 'OUTBOX/drive'):
    (brain / sub).mkdir(parents=True, exist_ok=True, mode=0o700)
link = Path.home() / '.local/bin/mark2-drive'
if not link.exists() and not link.is_symlink():
    link.symlink_to(repo / 'scripts/mark2-drive')
elif not link.is_symlink() or link.resolve() != repo / 'scripts/mark2-drive':
    raise SystemExit('Existing command conflict; installer stopped')
PY
systemctl --user daemon-reload
if [ "${1:-}" = '--enable' ]; then
    # Real authentication, folder writes, verified download, and manual sync first.
    "$REPO/scripts/mark2-drive" test
    "$REPO/scripts/mark2-drive" sync
    systemctl --user enable --now mark2-drive.timer
else
    echo 'Drive units installed but not enabled; live authentication/test required.'
fi
