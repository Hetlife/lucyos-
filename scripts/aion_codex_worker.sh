#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="${1:?usage: aion_codex_worker.sh <prompt-file>}"
REPO="${AION_REPO:-/root/lucyos}"
CODEX_BIN="${CODEX_BIN:-/root/.openclaw/tools/node/bin/codex}"

[ -f "$PROMPT_FILE" ] || { echo "prompt file missing" >&2; exit 2; }
[ -x "$CODEX_BIN" ] || { echo "codex executable unavailable" >&2; exit 3; }

{
  cat <<'EOF'
You are AION's class-B implementation worker on Mark-2.
Execute the supplied work order; do not merely explain what could be done.
Work only inside the provided repository workspace unless the work order explicitly names another safe local output.
Do not read or expose secrets, private_state, browser data, OAuth tokens, credentials, or unrelated personal files.
Do not spend money, change accounts, make external commitments, use real capital, or bypass owner approval boundaries.
Do not commit, push, force-push, or alter canonical operating-loop semantics.
Prefer targeted reads and existing tests. Make the smallest robust change that satisfies the objective.
Run relevant tests and git diff --check before finishing when code changes are made.
If blocked, state the blocker precisely and leave recoverable state. Never claim success without evidence.
Return a compact result packet with: STATUS, ACTIONS, FILES_CHANGED, TESTS, RESULTS, BLOCKERS, NEXT_ACTION.
EOF
  cat "$PROMPT_FILE"
} | "$CODEX_BIN" exec -s workspace-write --ephemeral --color never -C "$REPO" -
