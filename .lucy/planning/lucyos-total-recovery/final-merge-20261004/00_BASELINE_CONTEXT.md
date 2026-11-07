# LucyOS verified baseline — 2026-10-04
Audit base: e349bb03446452bace3a5225d990a73bae8160e1 (main, PR #104).
This is an evidence/context supplement to .lucy/planning/lucyos-total-recovery, NOT another plan, scheduler or operational database.
Read this + one work order + its named files. Runtime observations expire on deployment/service/config/state changes; code observations expire only when relevant file hashes change.

## Verified
- GitHub Hetlife/lucyos- is public. Push CI run 37209086211 at the base completed successfully.
- Isolated Lucy-den checkout: 813 tests, 153.249 seconds, OK (1 skipped), exit 0. This is not live E2E proof.
- Previous 864 test definitions became 813 after recent changes including skeleton removal. Both counts verified by AST. Review removed coverage with archived features; do not enforce an arbitrary never-decrease count.
- Boundary scan: 0 violations/known/stale. Portability: 0 violations, 3 documented exceptions. Secret scan clean. Anti-dup HEAD vs HEAD passed (self-comparison only, not a change review).
- Authority self: six hash drifts (CI workflow, config/db/router/security/worker). F1 override batch IS merged (#99); do not redo it.
- Remote inventory: 128 live heads including main. 127 non-main = 71 MERGED, 8 PATCH_EQUIVALENT, 48 unique-patch branches requiring semantic disposition. Seven cached refs no longer exist remotely.
- Only open PR observed: #102, secrets escrow. No merges/deletions/deployments performed.

## Runtime, observed directly
Lucy-den dev checkout: /home/scs-admin01/lucyos, feature/question-context-reduction, 8125fb847d477f7fe1d2d231b8543a40f5df6165, dirty.
Existing clean-runtime candidate: /home/scs-admin01/lucyos-main, 874a3f5f6e5cb011e064e16f6e58b06a55f0b37a.
Audit checkout: /home/scs-admin01/lucyos-audit-20261004 (isolated; never configured as runtime).
Lucy-den worker unit still targets dirty dev checkout. Worker/maintenance timers active; paused=0, safe_mode=0. Both codex and claude processes observed; do not assume idle ownership.
SQLite: ~/openclaw/shared_brain/state/aion.sqlite3, quick_check=ok, schema 12. 23 DONE, 9 NEEDS_REVIEW, 2 BLOCKED, 4 CANCELLED; no READY/RUNNING. No OPEN sessions. One OPEN error: ERR-D1585FFC, context compiler permission failure reading a foreign /root session-log path. Fix #95 is on main, not these runtime SHAs.
Approvals A-108/A-109 are APPROVED with openclaw-attributed principals (masked); this proves stored attribution, not fresh negative-message E2E.
Mark-2 root checkout: /root/lucyos, main at 33e4cedf18d79872bf45db80f5f04dd7a3e35ed9, dirty. Worker uses /root/lucyos-worktrees/main-current @ a5b792e. Worker/maintenance timers active; paused=0, safe_mode=0. Its separate SQLite quick_check=ok; schema 12; 22 DONE, 7 NEEDS_REVIEW, 2 BLOCKED, 3 CANCELLED, 1 WAITING; no OPEN sessions/errors. Cloud-command presence true on both hosts (values not exposed).
Two enabled worker hosts are a control-plane ownership risk; no duplicate execution or corruption was proven.
DigitalOcean Mark-2 active, 2 vCPU / 4GB / 80GB; provider lists four backup IDs. This does NOT prove an application restore.
Lucy-den OpenClaw gateway/node active. Mark-2 OpenClaw gateway active. LucyNest laptop bridge active. Camera sampler repeatedly fails “failed to start camera pipeline” (118+ restarts).
Pad reachable by existing SSH key. info => unreachable: control socket. Recorded socket and boot hook absent; no native client process found. Deployed hashes differ from September checkpoint. Physical touch not retested.
Latest observed Lucy-den local backup: 2026-10-02T21:52:54Z (~41h old at observation). Off-host freshness and restore NOT proven.

## Constraints
Use existing SQLite/task/session/approval mechanisms. No production DB changes during this audit. Work-order labels are planning IDs, not newly created canonical task IDs. Bind each before execution; reuse matching existing task.
Never reset/clean/stash others' dirty work; no deployments or protected merges without required concrete approval. Reuse TR orders. Main authority policy remains binding. Do not invoke local LLMs until the observed no-local-models timer/policy is reconciled.
