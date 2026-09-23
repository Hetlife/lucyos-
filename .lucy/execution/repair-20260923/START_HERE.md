# LucyOS Repair Mission — START HERE

Mission ID: PRM-LUCYOS-REPAIR-SCALE-20260923
Owner authorization date: 2026-09-23
Canonical base observed when packaged: origin/main @ a6f214d0bb3542873c2b66a972abfd7aeeeb3c63

## Goal
Repair, debug, integrate, and prove the LucyOS autonomous execution path end-to-end, then prepare clean PRs for controller merge. Preserve current architecture and future scaling contracts.

## Read in this order
1. `START_HERE.md`
2. `OWNER_AUTHORIZATION.md`
3. `LOW_TOKEN_REPAIR_PLAN.txt`
4. `AION_PLAN_BLUEPRINT.json`
5. `MERGE_PROTOCOL.md`
6. `PROGRESS.md`
7. Repository `START_HERE.md`
8. `integrations/openclaw/lucyos/SKILL.md`
9. `.lucy/authority/HIGH_MODEL_BASELINE.json`

## Worker mode
- Model: Sonnet / class B.
- Work one bounded task at a time.
- Before editing: inspect live repo state, current task/error state, and invoke LucyOS architecture audit.
- Prefer deterministic work first. Use local tests/tools before model reasoning.
- Smallest robust fix; no broad refactor.
- No third-party dependency in `aion_core`.
- No direct SQLite edits.
- No second queue, scheduler, canonical database, approval system, secret store, or always-on LLM loop.- Never expose secrets or read unrelated private files.
- Maximum two materially different attempts per task; then record evidence and escalate.
- Never claim DONE without independent validation evidence.

## Branch / PR rule
For each repair task:
- Refresh `origin/main`.
- Create `task/R-XX-<slug>` from the current `origin/main`.
- Change only files needed by that task.
- Run focused tests, full suite, secret scan, portability, and authority/anti-dup checks as applicable.
- Commit with `R-XX: <summary>` and trailer `Task-ID: R-XX`.
- Push and open a PR to `main`.
- Never merge the PR yourself.
- Move to the next independent safe task only after the current branch is safely pushed and recorded.

If existing authority text conflicts with this owner-issued post-consolidation mission, do not modify protected authority files. Record `AUTHORITY_SCOPE_STALE` with exact evidence and continue only work that does not cross a protected path or owner boundary.

## Hard stop boundaries
Do not modify `.lucy/authority/**`, `.github/workflows/lucyos-ci.yml`, `scripts/verify_authority.py`, or other constitutional paths.
Do not spend money, create external accounts, change credentials/security, deploy production exposure, use real capital, or make legal commitments.
Do not merge.

## Required result packet after every task
STATUS:
ACTIONS:
FILES_CHANGED:
TESTS:
RESULTS:
BLOCKERS:
NEXT_ACTION:

## Low-token daily execution
After the initial full read, use `TASKS.md` + the current AION context packet for each R-series task. Re-read the master plan only when `TASKS.md` explicitly lacks required context.