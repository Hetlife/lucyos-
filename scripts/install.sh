#!/usr/bin/env bash
# Install AION on the Ubuntu PC.  Idempotent: safe to re-run.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${HOME}/.local/bin"
AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"

echo "repository:   ${REPO}"
echo "shared brain: ${AION_HOME}"

python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit(f"AION needs Python 3.9+, found {sys.version.split()[0]}")
print(f"python:       {sys.version.split()[0]} OK")
PY

mkdir -p "${BIN}"
ln -sf "${REPO}/aion" "${BIN}/aion"
echo "installed:    ${BIN}/aion -> ${REPO}/aion"

case ":${PATH}:" in
  *":${BIN}:"*) ;;
  *) echo "NOTE: add ${BIN} to PATH:  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc" ;;
esac

export AION_HOME
"${REPO}/aion" init
"${REPO}/aion" secrets init >/dev/null
"${REPO}/aion" backup >/dev/null
echo
"${REPO}/aion" health || true
echo
echo "Next:"
echo "  1. aion owner-setup          # what you still need to provide, batched"
echo "  2. aion boot                 # startup and resume loop"
echo "  3. python3 ${REPO}/bridges/whatsapp_bridge.py stdin   # try the commands"
echo "  4. scripts/install_services.sh   # run it continuously via systemd --user"
