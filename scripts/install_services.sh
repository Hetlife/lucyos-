#!/usr/bin/env bash
# Install the systemd --user units: the bridge plus a nightly maintenance timer.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"

if [[ "$(uname)" == "Darwin" ]]; then
  AGENTS="${HOME}/Library/LaunchAgents"
  mkdir -p "${AGENTS}" "${AION_HOME}/logs"

  for plist in com.lucyos.aion-work.plist com.lucyos.aion-maintenance.plist \
               com.lucyos.aion-bridge.plist com.lucyos.aion-interface.plist; do
    sed -e "s|@REPO@|${REPO}|g" -e "s|@AION_HOME@|${AION_HOME}|g" \
        "${REPO}/deploy/launchd/${plist}" > "${AGENTS}/${plist}"
    echo "wrote ${AGENTS}/${plist}"
  done

  UID_N="$(id -u)"
  for name in aion-maintenance aion-work; do
    launchctl bootstrap "gui/${UID_N}" "${AGENTS}/com.lucyos.${name}.plist" 2>/dev/null \
      || launchctl load "${AGENTS}/com.lucyos.${name}.plist"
  done
  echo "maintenance agent loaded (calendar: 03:15 daily)"
  echo "build loop agent loaded (runs at load; scripts/build_loop.sh owns its own internal loop)"
  echo
  echo "Start the bridge after its Cloud API settings are stored locally:"
  echo "  aion secrets set WHATSAPP_ACCESS_TOKEN"
  echo "  aion secrets set WHATSAPP_PHONE_NUMBER_ID"
  echo "  aion secrets set WHATSAPP_VERIFY_TOKEN"
  echo "  aion secrets set WHATSAPP_APP_SECRET"
  echo "  aion secrets set WHATSAPP_GRAPH_API_VERSION"
  echo "  launchctl bootstrap gui/${UID_N} ${AGENTS}/com.lucyos.aion-bridge.plist"
  echo "  launchctl list | grep com.lucyos.aion-bridge"
  echo
  echo "Start the private phone interface when its token is set:"
  echo "  aion secrets set AION_INTERFACE_TOKEN"
  echo "  launchctl bootstrap gui/${UID_N} ${AGENTS}/com.lucyos.aion-interface.plist"
  echo "  # From another machine: ssh -N -L 8787:127.0.0.1:8787 <mac>"
  echo "  # Then open http://127.0.0.1:8787 (use a private HTTPS tunnel for iPhone/PWA)"
  echo
  echo "launchd agents run only while logged in unless 'Login Items' background"
  echo "permission is granted in System Settings; see deploy/launchd/README.md"
  echo "for the scheduling and hardening differences from the Linux units."
  exit 0
fi

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
echo "Start the bridge after its Cloud API settings are stored locally:"
echo "  aion secrets set WHATSAPP_ACCESS_TOKEN"
echo "  aion secrets set WHATSAPP_PHONE_NUMBER_ID"
echo "  aion secrets set WHATSAPP_VERIFY_TOKEN"
echo "  aion secrets set WHATSAPP_APP_SECRET"
echo "  aion secrets set WHATSAPP_GRAPH_API_VERSION"
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
