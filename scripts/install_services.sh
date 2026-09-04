#!/usr/bin/env bash
# Install the systemd --user units: the bridge plus a nightly maintenance timer.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"
UNITS="${HOME}/.config/systemd/user"
mkdir -p "${UNITS}"

UNIT_LIST=(aion-bridge.service aion-maintenance.service aion-maintenance.timer
           aion-work.service aion-work.timer)
command -v codex >/dev/null 2>&1 && UNIT_LIST+=(aion-codex.service aion-codex.timer)

for unit in "${UNIT_LIST[@]}"; do
  sed -e "s|@REPO@|${REPO}|g" -e "s|@AION_HOME@|${AION_HOME}|g" \
      "${REPO}/systemd/${unit}" > "${UNITS}/${unit}"
  echo "wrote ${UNITS}/${unit}"
done

systemctl --user daemon-reload
systemctl --user enable --now aion-maintenance.timer
systemctl --user enable --now aion-work.timer
echo "maintenance timer enabled (nightly)"
echo "build loop enabled (every 10 minutes, stops on a major milestone)"
if command -v codex >/dev/null 2>&1; then
  systemctl --user enable --now aion-codex.timer
  echo "codex worker loop enabled (every 15 minutes, claims one ranked task)"
fi
echo
echo "Start the bridge when its token is set:"
echo "  aion secrets set WHATSAPP_BRIDGE_TOKEN"
echo "  systemctl --user enable --now aion-bridge.service"
echo "  systemctl --user status aion-bridge.service"
echo
echo "To keep these running when you are logged out:  loginctl enable-linger \$USER"
