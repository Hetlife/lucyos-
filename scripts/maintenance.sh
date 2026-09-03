#!/usr/bin/env bash
# Nightly maintenance: boot loop, backup with restore test, docs, health.
# Exits non-zero if health fails, so the timer surfaces a real problem.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"
AION="${REPO}/aion"

SESSION="$("${AION}" session start --actor openclaw --model-class DET \
           --objective "nightly maintenance")"
log() { "${AION}" session log "${SESSION}" --kind "$1" --text "$2" >/dev/null; }

"${AION}" boot           >/dev/null && log action "boot loop completed"
"${AION}" notebook sync  >/dev/null && log action "notebook synced"
"${AION}" backup         >/dev/null && log action "backup created and restore-tested"
"${AION}" sync-docs      >/dev/null && log action "markdown surfaces regenerated"
"${AION}" owner-setup    >/dev/null && log action "owner setup list refreshed"
if "${AION}" scan "${REPO}" >/dev/null; then
  log test "secret scan clean"
else
  log failure "secret scan found credential-shaped content"
fi

if "${AION}" health --deep >/dev/null; then
  log test "health check passed"
  "${AION}" session end "${SESSION}" --outcome "nightly maintenance clean" \
      --resume-point "nothing pending" >/dev/null
  exit 0
fi

log failure "health check failed"
"${AION}" session end "${SESSION}" --outcome "health check failing" \
    --resume-point "run: aion health --deep" >/dev/null
"${AION}" health
exit 1
