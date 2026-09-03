#!/usr/bin/env bash
# Install the systemd --user units: the bridge plus a nightly maintenance timer.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"
UNITS="${HOME}/.config/systemd/user"
mkdir -p "${UNITS}"

for unit in aion-bridge.service aion-maintenance.service aion-maintenance.timer; do
  sed -e "s|@REPO@|${REPO}|g" -e "s|@AION_HOME@|${AION_HOME}|g" \
      "${REPO}/systemd/${unit}" > "${UNITS}/${unit}"
  echo "wrote ${UNITS}/${unit}"
done

systemctl --user daemon-reload
systemctl --user enable --now aion-maintenance.timer
echo "maintenance timer enabled"
echo
echo "Start the bridge when its token is set:"
echo "  aion secrets set WHATSAPP_BRIDGE_TOKEN"
echo "  systemctl --user enable --now aion-bridge.service"
echo "  systemctl --user status aion-bridge.service"
echo
echo "To keep these running when you are logged out:  loginctl enable-linger \$USER"
