#!/usr/bin/env bash
# S04 branch hygiene for het-life/sevaaconnect-realestate.
# Prepared by an agent without push access to this repo -- verified locally,
# not executed. Run this from a clone with push rights, after reviewing it.
#
# Method: a branch is "merged" here only if its tree hash matches EXACTLY one
# commit tree already in main's history (a real squash-merge check, not a
# guess from branch names or dates). Verified against main = a85a8cc on 2026-09-04.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git fetch origin --prune

echo "== verifying tree hashes against current main before touching anything =="
MAIN_TREE=$(git rev-parse origin/main^{tree})
for b in agent/monetization-mvp chore/record-agent-control-plane-state \
         chore/sync-hosting-gate-v2 feat/agent-control-plane \
         feat/privacy-pilot-hardening feat/sevaa-sales-os-mvp \
         privacy-prospecting-policy; do
  T=$(git rev-parse "origin/$b^{tree}")
  if ! git log origin/main --format=%T | grep -q "^$T$"; then
    echo "REFUSING: $b tree $T is not in main's history -- main may have moved. Stop and re-verify." >&2
    exit 1
  fi
done
echo "all seven confirmed merged (tree-exact) -- safe to delete"

# Deferred, not merged: T300 in TODO.md explicitly defers PostgreSQL until a
# measured trigger. Tag before deleting so the work is recoverable, not lost.
git tag deferred/postgres-path-2026-08-30 origin/feat/sevaa-postgres-path
git tag deferred/postgres-portable-2026-08-30 origin/feat/sevaa-postgres-portable
git push origin deferred/postgres-path-2026-08-30 deferred/postgres-portable-2026-08-30

# Delete: seven merged branches + the two now-tagged deferred branches.
git push origin --delete \
  agent/monetization-mvp \
  chore/record-agent-control-plane-state \
  chore/sync-hosting-gate-v2 \
  feat/agent-control-plane \
  feat/privacy-pilot-hardening \
  feat/sevaa-sales-os-mvp \
  privacy-prospecting-policy \
  feat/sevaa-postgres-path \
  feat/sevaa-postgres-portable

cat >> CHANGELOG.md <<'EOF'

## Branch hygiene (S04, 2026-09-04)

Deleted seven branches whose tree hash exactly matched a commit already in
`main`'s history (agent/monetization-mvp, chore/record-agent-control-plane-state,
chore/sync-hosting-gate-v2, feat/agent-control-plane, feat/privacy-pilot-hardening,
feat/sevaa-sales-os-mvp, privacy-prospecting-policy) -- genuinely merged, not
guessed from name or date.

Tagged and deleted two branches with unmerged PostgreSQL work, deferred by
T300 in TODO.md (no trigger measured -- single-instance SQLite remains
simpler): `deferred/postgres-path-2026-08-30`, `deferred/postgres-portable-2026-08-30`.

Left alone (unmerged, not deferred by any TODO.md entry -- a human decision,
not an agent's to make):
- `agent/reconcile-deployment-gate` (3 commits ahead of main)
- `chore/sync-hosting-gate` (5 commits ahead of main, distinct from the
  merged -v2 branch)
- `codex/create-landscout-roi-real-estate-app` (1 commit, 2025-10-23 -- a
  different, unrelated SwiftUI experiment predating the SEVAA pivot)
EOF
git add CHANGELOG.md
git commit -m "S04: branch hygiene -- delete merged branches, tag and delete deferred Postgres work

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git push origin main
echo "S04 complete"
