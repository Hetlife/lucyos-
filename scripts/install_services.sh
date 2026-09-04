#!/usr/bin/env bash
# Install the systemd --user units: the bridge plus a nightly maintenance timer.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"
UNITS="${HOME}/.config/systemd/user"
mkdir -p "${UNITS}"

for unit in aion-bridge.service aion-interface.service aion-maintenance.service aion-maintenance.timer \
            aion-work.service aion-work.timer; do
  sed -e "s|@REPO@|${REPO}|g" -e "s|@AION_HOME@|${AION_HOME}|g" \
      "${REPO}/systemd/${unit}" > "${UNITS}/${unit}"
  echo "wrote ${UNITS}/${unit}"
done

systemctl --user daemon-reload
systemctl --user enable --now aion-maintenance.timer
systemctl --user enable --now aion-work.timer
echo "maintenance timer enabled (nightly)"
echo "build loop enabled (every 10 minutes, stops on a major milestone)"
echo
echo "Start the bridge when its token is set:"
echo "  aion secrets set WHATSAPP_BRIDGE_TOKEN"
echo "  systemctl --user enable --now aion-bridge.service"
echo "  systemctl --user status aion-bridge.service"
echo
echo "Start the private phone interface when its token is set:"
echo "  aion secrets set AION_INTERFACE_TOKEN"
echo "  systemctl --user enable --now aion-interface.service"
echo "  # From another machine: ssh -N -L 8787:127.0.0.1:8787 <ubuntu-pc>"
echo "  # Then open http://127.0.0.1:8787 (use a private HTTPS tunnel for iPhone/PWA)"
echo
echo "To keep these running when you are logged out:  loginctl enable-linger \$USER"
