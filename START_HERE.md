# LucyOS — START HERE

This file is a **router, not a second brain**. Do not copy state into it.
Live AION/SQLite state wins over prose; authority files win over ordinary docs.

## Read the minimum necessary

1. Run `./aion boot`, then `./aion status` and `./aion health --deep`.
2. For one task, use `./aion context <TASK_ID>` instead of loading the whole repo.
3. Use `./aion search "<query>"` for durable memory and `./aion why <ID>` for provenance.
4. Read `$AION_HOME/RESUME.md` for the current checkpoint/resume pointer.
5. Read `.lucy/authority/HIGH_MODEL_BASELINE.json` before architecture, policy, protected-path, or executor-scope changes.
6. Read `.lucy/execution/SONNET_TASK_QUEUE.md` only as a planning/execution view; re-check live task state before acting.
7. For architecture changes, follow `docs/skill-system/Q000_ARCHITECTURE_AUDIT.txt` and `docs/skill-system/Q006_ARCHITECTURE_ANTI_DUPLICATION.txt`; use `./aion architecture-check <proposal.json>` when the change is a skill/integration proposal.
8. Use `docs/README.md` to route to architecture/operations docs. Dated handoffs are historical until reverified against live state.

## Existing seams — reuse, do not rebuild

- State/tasks/approvals/errors: `aion_core/db.py`, `tasks.py`, `approvals.py`, `errors.py`
- Memory/retrieval: `aion_core/memory.py` and `./aion search`
- Task-specific token-efficient context: `aion_core/context.py` and `./aion context`
- Resume/handoff: `aion_core/resume.py`, `sessions.py`, `$AION_HOME/RESUME.md`
- Executor routing/evidence: `aion_core/worker.py`; never replace `_validate` evidence semantics
- Health/cost: `aion_core/health.py`, `governor.py`, `metrics.py`
- External dependency research: `aion_core/learnrepo.py`
- Architecture audit: `aion_core/architecture.py` plus the Q000/Q006 rules above

## Multi-model rule

High-capability models decide architecture and bounded plans; deterministic/local workers do routine execution first; cloud/Codex is bounded and evidence-gated. No model may silently create a second state store, queue, scheduler, approval system, memory system, secret store, or governance layer.

Before claiming DONE: run the task's own validation, relevant repo gates, secret scan, and record independent evidence/checkpoint. Never treat an executor's success text or exit code alone as proof.
