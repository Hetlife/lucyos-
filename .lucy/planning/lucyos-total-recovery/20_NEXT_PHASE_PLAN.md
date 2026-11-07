# 20 — Next phase: make it correct, then let it improve itself (2026-11-07)

Basis: `main` @ `a6daea3`: 843 tests OK, boundary scan 0, authority self still **6 drift**, open PRs #109 (service verifier extract) and #111 (agent harness / disputes). Wave 1 and the F1 override batch are merged. Companion docs: `18_` (audit), `19_` (roles, session loop), `17_` (critical path).

## 1. Principle
Self-improvement is only safe on a core that is **provably correct, observable and reversible**. So the order is fixed: **prove → stabilize → one governed loop → measured autonomy → ship**. A later stage never starts before the earlier stage's gate is recorded in `evidence/EVIDENCE_INDEX.md`.

## 2. Stage A — Prove what exists (owner + Fable, about 1 day; no new features)
| # | Action | Gate (observable) |
|---|---|---|
| A1 | Lucy-den: refresh `~/lucyos-main`, `./aion errors`, `./aion boot` | `errors` check green or each error filed as an issue (ISSUE-044) |
| A2 | TR-1-08 live: `./aion work --max 1` on a READY test task | task reaches DONE with evidence, no `CONTEXT_COMPILATION_FAILED` |
| A3 | TR-1-05 probe 3 + masked audit-export block | loose message leaves a PENDING approval pending; `decided_by` = `openclaw:<masked>` → **L2 recorded** |
| A4 | Fable review + merge of #102 (secret handling) and #111 (harness) | reviews recorded on the PRs |
| A5 | TR-3-04 churn: add `"TR-3-04": ["aion_core/worker.py"]` (or fold into TR-1-06), land `71c8324` + test | empty queue opens no session |
| A6 | TR-0-06: tag then delete merged branches (dry-run script, owner `--yes`) | `branch_ledger.py`: only UNIQUE/UNRELATED remain |
| A7 | **F2 re-freeze (TR-0-03)** after A5 and TR-1-06 | `verify_authority.py self` = 0 drift → **L1 recorded** |

## 3. Stage B — Make it logical and bug-resistant (Sonnet, parallel lanes)
Bug classes seen so far and the guard that closes each, so the same class cannot return:
| Seen | Guard to add | Order |
|---|---|---|
| Loose text decided approvals (ISSUE-035) | table-driven router test: every ordinary sentence is a no-op; only the exact grammar decides | TR-B-01 |
| Foreign paths / host assumptions (036, 040) | clean-machine proof in CI-lite: install → seed → export → fresh home → import → run one task | TR-2-01 |
| Plaintext written before encryption (048) | secret-hygiene test: no secret canary in any file under `AION_HOME` except `private_state` | TR-B-02 |
| Empty-session churn, stale status, generated files in repo (029, 045) | invariants test: idle worker creates 0 rows; `evidence/` never tracked; INDEX matches `git log` (script) | TR-B-03 |
| Schema drift between versions | upgrade-from-main-schema test already in CI: add one per migration (required for TR-4-02/4-05/5-02) | with each order |
| Flaky/concurrent test runs (029) | isolate test homes; run suite twice in CI, fail on any diff | TR-B-04 |
Also: turn `check_boundaries.py --strict` on in CI (Fable, workflow is constitutional) so the zero cannot regress.
Then the remaining Wave-1 leftovers: TR-2-05 (cost per verified task), TR-2-01, TR-C-03.

## 4. Stage C — One governed execution loop (L3; needs overrides already merged)
Order is forced by `db.py` (one migration at a time): **TR-1-06 → TR-4-02 → TR-4-05 → TR-4-06**, then TR-4-03 (live on one B task) and the 3-step PLAN proof.
Definition of a **verified task** (the unit everything measures): executor result + independent check (TR-4-05) + evidence row + owner-visible status. Nothing counts as DONE without it.
Collaboration: adopt #111's harness as the single dispatch/review/dispute record (no parallel truth); one writer per worktree, reviewer checks the exact SHA, max 2 revision cycles, 30-minute checkpoint (from the Lucy-den master prompt).

## 5. Stage D — Adaptive, self-programming, but bounded (the product's core idea)
The loop, all through existing AION records, never a new daemon:
```
OBSERVE  errors table, failed/blocked tasks, cost per verified task (TR-2-05/4-04), health checks, owner feedback
   -> PROPOSE  files an INBOX task with evidence + class (DET/A/B/C) + acceptance test; dedup against open tasks
   -> IMPLEMENT  executor registry picks the cheapest capable executor; isolated worktree; tests first
   -> VERIFY  independent reviewer on the exact SHA + all gates (tests, scan, portability, boundaries, authority)
   -> LAND  GREEN: auto-PR, owner merges; AMBER: PR + approval; RED: owner only (protected paths, money, secrets, exposure)
   -> LEARN  every fixed bug adds a regression test; every failure adds a memory row (kind=lesson) retrievable by the compiler
```
Hard limits (the safety case for self-modification):
1. It may **never** edit `.lucy/authority/**`, the verifier, the CI workflow, the router's decision grammar, approvals, or secrets handling; those stay Fable + owner (contract C5 bands).
2. Budget per cycle: tokens/INR (governor), 1 task, 2 revisions, 30 min; stop on repeated identical failure, auth loss, merge conflict or budget exhaustion; mark BLOCKED with the real reason.
3. A change lands only with a failing-then-passing test and a rollback command in the PR.
4. Kill switch: `pause` (router) and `safe mode` stop dispatch; verified before first unattended run.
5. Promotion by evidence: start with **read-only proposals only**, then DET/class-A fixes, then class B; each step needs 10 consecutive verified tasks at ≥90% first-pass with 0 policy violations.
LearnRepo (capability intake) stays gated: provenance + licence + quarantine; learned code never auto-activates.
Orders to write (Fable) before building: TR-D-01 proposal generator (reads errors/failed tasks, files INBOX tasks), TR-D-02 eval harness (a fixed set of golden tasks run on every release; a regression blocks promotion), TR-D-03 autonomy ladder config + metrics (`aion autonomy status`), TR-D-04 lesson memory feeding the context compiler.

## 6. Stage E — Projects, then ship
- Projects (L4/L5): TR-5-01 ratify → TR-5-02 migration v13 → {5-03, 5-04, 5-06, 5-07} → 5-05 SEVAA manifest → TR-8-04 strategy-factory registered. Project policy (max model class, budget, allowed actions) enforced in routing/governor/worker before any project runs unattended.
- Reach: TR-1-04 bridge restart policy (needs D-5); control-center views TR-I-01/02.
- Ship (L6/L7): TR-2-02/2-03 off-host backup + restore drill, TR-6-04 update.sh with rollback, TR-7-01..03 Mac primary, TR-8-01..03 SEVAA token + 14 days of nightly reconcile and morning brief.

## 7. "Shippable" checklist (all must be true)
1. Fresh machine: one command installs, seeds, passes `aion verify`, and runs a task (clean-machine proof).
2. 0 authority drift; 0 boundary findings; suite green twice in a row; CI never cancelled on main.
3. Phone: status, approve, deny, pause work through OpenClaw with attribution proven in the audit export.
4. Backup nightly off-host, restore drill passed, secrets escrow done.
5. Update and rollback in one command each, tested.
6. 14 days unattended on the Mac: ≥90% verified-task rate, 0 policy violations, owner morning brief delivered.
7. Autonomy at least at "DET/class-A auto-PR" with the eval harness passing.

## 8. Who does what, now
| Who | Next 3 actions |
|---|---|
| Owner | A1–A3 on Lucy-den; merge #102/#111/#109 after Fable review; run TR-0-06 delete script |
| Fable | A5 override + A7 re-freeze; write TR-D-01..04; enable `--strict` boundaries in CI |
| Sonnet | TR-B-01..04, TR-2-05, TR-2-01, TR-C-03, then TR-1-06 → TR-4-02 (one `db.py` change at a time) |
| Codex | TR-0-04 census refresh, TR-4-03 live proof, restore drill |
