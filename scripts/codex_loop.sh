#!/usr/bin/env bash
# The Codex worker loop: claim one ranked task, hand it to `codex exec` with a
# bounded, evidence-required brief, then verify — never trust — the result.
# Same pause rule as build_loop.sh: a real milestone stops new claims.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AION_HOME="${AION_HOME:-${HOME}/openclaw/shared_brain}"
AION="${REPO}/aion"
AGENT_ID="codex-mark2"
LOG="${AION_HOME}/logs/codex_loop.log"
mkdir -p "$(dirname "${LOG}")"
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "${LOG}"; }

command -v codex >/dev/null 2>&1 || { log "codex not installed — skipping"; exit 0; }

REACHED="$("${AION}" milestones --new 2>/dev/null | tr -d '[:space:]')"
if [ -n "${REACHED}" ] && [ "${REACHED}" != "none" ]; then
  log "major milestone reached: ${REACHED} — not claiming new work"
  exit 0
fi

TASK_ID="$("${AION}" tasks --limit 1 2>/dev/null | grep -oE 'TASK-[0-9A-F]{8}' | head -1)"
if [ -z "${TASK_ID}" ]; then
  log "no ready task — nothing to do"
  exit 0
fi

TITLE="$("${AION}" tasks --limit 1 2>/dev/null | grep "${TASK_ID}" | sed 's/.*· //')"
log "claiming ${TASK_ID}: ${TITLE}"

BRIEF="Task ${TASK_ID}: ${TITLE}
Read it in full first: ${AION} task-update ${TASK_ID} --status RUNNING; then read directives/03_AGENT_UNLAZY_EXECUTION_STANDARD.txt.
Rules: INR 0 spend. Never push to main. Never write a secret anywhere. Run the
real test suite and paste real output before claiming done. When finished, run
exactly: ${AION} task-done ${TASK_ID} --evidence \"<the real command+output>\"
If you cannot finish, run: ${AION} task-fail ${TASK_ID} --error \"<what happened>\"
Do not report success without having run task-done yourself — nothing else
marks this complete."

cd "${REPO}"
codex exec --full-auto "${BRIEF}" >> "${LOG}" 2>&1
STATUS="$("${AION}" task-update "${TASK_ID}" 2>/dev/null | grep -oE '"status": *"[A-Z_]+"')"
log "${TASK_ID} finished this pass, status now: ${STATUS:-unknown}"

# Only push if the task actually reports DONE — never push a half-finished
# claim, and never touch main.
if echo "${STATUS}" | grep -q DONE; then
  git add -A
  git diff --cached --quiet || git commit -q -m "codex: ${TASK_ID} ${TITLE}"
  git push -q origin claude/aion-whatsapp-control-1seild 2>>"${LOG}" || log "push failed, left local"
fi
