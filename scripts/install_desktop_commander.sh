#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT="mark2-desktop-commander.service"

mkdir -p "${UNIT_DIR}"
install -m 0644 "${REPO}/systemd/${UNIT}" "${UNIT_DIR}/${UNIT}"
systemctl --user daemon-reload
systemctl --user enable --now "${UNIT}"
systemctl --user is-active --quiet "${UNIT}"
echo "${UNIT} enabled and active"
