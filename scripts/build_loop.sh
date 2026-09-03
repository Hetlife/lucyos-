#!/usr/bin/env bash
# The continuous build loop: keep executing the queue until a major milestone
# lands, the owner pauses, or there is genuinely nothing left to do.
#
# Run under systemd (aion-work.timer) or directly: scripts/build_loop.sh
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"
AION="${REPO}/aion"
MAX_TASKS="${AION_LOOP_MAX_TASKS:-10}"

"${AION}" boot >/dev/null 2>&1

# A major milestone is a decision point for the owner, not a checkpoint to
# drive past. Stop and let them look.
REACHED="$("${AION}" milestones --new 2>/dev/null | tr -d '[:space:]')"
if [ -n "${REACHED}" ] && [ "${REACHED}" != "none" ]; then
  echo "major milestone reached: ${REACHED} — pausing the build loop"
  "${AION}" whatsapp pause >/dev/null 2>&1
  exit 0
fi

"${AION}" work --max "${MAX_TASKS}"
"${AION}" sync-docs >/dev/null 2>&1
exit 0
