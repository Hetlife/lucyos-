# R-Series Repair Tasks

Use this file for daily execution. Read the full master plan only when a task needs context not present here.

## R-01 — Harden executable task contract
STATUS: READY · MODEL: Sonnet/B · RISK: low
OBJECTIVE: prevent explicit DET tasks without `exec_command` from reaching normal execution or consuming retries.
PREFERRED FILES: `aion_core/tasks.py`, `tests/test_tasks.py`, `tests/test_task_reliability.py`, `tests/test_plan_worker.py`.
AVOID: protected `aion_core/worker.py` unless evidence proves no non-protected seam exists.
ACCEPTANCE:
- malformed DET READY work cannot become RUNNING;
- legacy malformed row is quarantined safely;
- static contract defect consumes no retry;
- valid DET and A/B behavior unchanged;
- focused tests + full suite + scan + portability + diff-check pass.
ESCALATE: protected-file change is actually required.

## R-02 — Prove autonomous lifecycle and resolve current error
STATUS: WAITING R-01 · MODEL: DET first, Sonnet only for repair
OBJECTIVE: make `TASK-AA93D718` complete through READY→CLAIMED→RUNNING→validated DONE→checkpoint and resolve `ERR-A62774E4` with root cause/fix/lesson.
PREFERRED: supported AION task/error APIs and reversible marker workload.
FORBIDDEN: raw SQLite editing.
ACCEPTANCE: independent validation evidence, no stale claim, no unresolved task error, resume state correct.

## R-03 — Authority-aware health
STATUS: WAITING R-02 · MODEL: Sonnet/B
OBJECTIVE: report runtime health separately from authority/deploy readiness.
PREFERRED FILES: non-protected health/verification surfaces and tests.
FORBIDDEN: `.lucy/authority/**`, `scripts/verify_authority.py`.
ACCEPTANCE: current authority drift is visible and deployment readiness is false without falsely declaring local runtime corrupt.
## R-04 — Reconcile generated state surfaces
STATUS: WAITING R-03 · MODEL: Sonnet/B
OBJECTIVE: regenerate owner/shared-brain docs from measured capabilities and remove stale setup claims through supported generators.
PREFERRED: owner-setup/capability generator logic plus tests only if live generation is wrong.
ACCEPTANCE: Ollama/cloud/GitHub/OpenClaw wording matches measured state; no secret values exposed.

## R-05 — OpenClaw ↔ AION owner-control path
STATUS: WAITING R-04 · MODEL: Sonnet/B
OBJECTIVE: reconcile existing loopback OpenClaw health/config and prove channel→AION→safe action/approval→response.
PREFERRED: existing `bridges/openclaw_check.py`, integrations/openclaw/lucyos, bridge tests, supported AION metadata.
FORBIDDEN: new transport queue/state store/daemon; non-loopback exposure; credentials in repo/chat.
ACCEPTANCE: existing integration works; LucyOS remains canonical.

## R-06 — Unattended reliability proof
STATUS: WAITING R-05 · MODEL: DET first
OBJECTIVE: prove singleton, crash recovery, stale-claim handling, timeout preservation, validation gate, restart/resume, backup/restore, timer persistence, budget and approvals.
PREFERRED: existing tests and fault-injection seams; add only missing regression tests.
ACCEPTANCE: zero false completion, zero stale claim, zero new unresolved error.

## R-07 — Final integration + protected evidence package
STATUS: WAITING R-06 · MODEL: Sonnet/B read-only where protected
OBJECTIVE: run final regression/security/architecture audit and prepare exact evidence for authority re-freeze + exact-SHA deployment.
FORBIDDEN: editing protected authority/deployment/CI/verifier files.
ACCEPTANCE: controller gets current SHA, verifier output, drift history, test/scan results, rollback, and exact remaining owner/high-model action.

## Standard result
Return exactly: STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS / BLOCKERS / NEXT_ACTION.