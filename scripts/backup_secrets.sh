#!/usr/bin/env bash
# Encrypted, off-machine-ready backup of private_state/ — the one thing
# `aion backup` deliberately excludes, on purpose, from every other archive.
#
# Design decision (recorded, not reopened without new evidence):
#   GPG symmetric encryption (AES256), passphrase-based. No new cloud
#   credential, no key pair to manage, no paid service. The passphrase must
#   live somewhere other than this disk (the owner's head or a password
#   manager) — that is the whole point of "survives a disk failure", so this
#   script is NOT wired into the unattended nightly timer. Run it yourself,
#   periodically, and copy the .gpg file off this machine (rsync/scp/cloud
#   sync of your choice — this script's job ends at producing a trustworthy
#   encrypted artifact, not choosing your cloud provider).
#
# Usage:
#   scripts/backup_secrets.sh            # prompts for a passphrase, hidden
#   SECRETS_BACKUP_PASSPHRASE=... scripts/backup_secrets.sh   # scripted use
#   scripts/backup_secrets.sh --verify-only   # restore-test the latest archive
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"
SRC="${AION_HOME}/private_state"
DEST_DIR="${AION_HOME}/BACKUPS/secrets"
KEEP=7
mkdir -p "${DEST_DIR}"

command -v gpg >/dev/null 2>&1 || { echo "gpg not installed — apt-get install gnupg" >&2; exit 1; }

_latest() { find "${DEST_DIR}" -maxdepth 1 -name 'secrets-*.tar.gz.gpg' | sort | tail -1; }

_get_passphrase() {
  if [ -n "${SECRETS_BACKUP_PASSPHRASE:-}" ]; then
    printf '%s' "${SECRETS_BACKUP_PASSPHRASE}"
    return
  fi
  read -rs -p "Passphrase for this encrypted secrets backup (not stored anywhere): " PASS >&2
  echo >&2
  printf '%s' "${PASS}"
}

# The passphrase must travel to gpg on its own file descriptor (3), never fd 0
# — stdin is already the tar data stream being encrypted/decrypted. Mixing
# them onto fd 0 silently feeds gpg the wrong bytes as the passphrase.

if [ "${1:-}" = "--verify-only" ]; then
  ARCHIVE="$(_latest)"
  [ -n "${ARCHIVE}" ] || { echo "no encrypted secrets backup exists yet"; exit 1; }
  PASS="$(_get_passphrase)"
  TMP="$(mktemp -d)"
  trap 'rm -rf "${TMP}"; unset PASS' EXIT
  if ! gpg --quiet --batch --yes --passphrase-fd 3 --decrypt "${ARCHIVE}" 3<<<"${PASS}" 2>/dev/null \
       | tar -tzf - > "${TMP}/listing.txt" 2>/dev/null; then
    echo "restore-test FAILED: wrong passphrase or corrupt archive"; exit 1
  fi
  grep -q "private_state/secrets.env" "${TMP}/listing.txt" || { echo "restore-test FAILED: secrets.env missing from archive"; exit 1; }
  echo "restore-test OK: $(basename "${ARCHIVE}") — $(wc -l < "${TMP}/listing.txt") files, secrets.env present"
  exit 0
fi

[ -d "${SRC}" ] || { echo "no ${SRC} yet — run 'aion secrets init' first"; exit 1; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${DEST_DIR}/secrets-${STAMP}.tar.gz.gpg"
PASS="$(_get_passphrase)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"; unset PASS' EXIT

tar -C "$(dirname "${SRC}")" -czf - "$(basename "${SRC}")" \
  | gpg --quiet --batch --yes --passphrase-fd 3 --symmetric --cipher-algo AES256 \
        --output "${DEST}" 3<<<"${PASS}"

# Restore-test immediately — an unverified encrypted backup is still just an
# assumption, the same principle as aion_core/backup.py's verify().
gpg --quiet --batch --yes --passphrase-fd 3 --decrypt "${DEST}" 3<<<"${PASS}" 2>/dev/null \
  | tar -tzf - | grep -q "private_state/secrets.env" \
  || { echo "restore-test FAILED immediately after writing — deleting bad archive"; rm -f "${DEST}"; exit 1; }

# Retention.
mapfile -t OLD < <(find "${DEST_DIR}" -maxdepth 1 -name 'secrets-*.tar.gz.gpg' | sort | head -n -"${KEEP}")
for f in "${OLD[@]:-}"; do [ -n "$f" ] && rm -f "$f"; done

echo "created and restore-verified: ${DEST}"
echo "NEXT: copy this file off this machine yourself (rsync/scp/cloud sync)."
echo "The passphrase was never written to disk — losing it means losing this backup."
