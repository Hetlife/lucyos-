# LUCYOS_FABLE_ARCHITECT_EXECUTION_PACKAGE

Fable, highest-capability architect. Cycle 2026-09-16. Protected path.
Inputs: Opus brief @ `2f5f376`; owner decisions and Mark-2 runtime corrections (recorded in `.lucy/planning/FABLE_PROGRESS.md`); independent verification this session.
Companions: `HIGH_MODEL_BASELINE.json`, `PROTECTED_PATHS.md`, `../execution/SONNET_TASK_QUEUE.md`, `../deployment/MARK2_DEPLOYMENT_CONTRACT.md`.

## 1. Verified current state

Classifications merge Opus's repository evidence with the owner's Mark-2 evidence; where they differ, the stronger live evidence wins and is marked (M2).

| Capability | State | Basis |
|---|---|---|
| Canonical SQLite + FTS5, sessions, task transitions, checkpoint→restart→resume | LIVE_VERIFIED (M2) | Mark-2 rehearsals; also exercised on a clean home this session |
| Structured plan execution, approvals, validation gating, governor high→low handoff | LIVE_VERIFIED (M2) | Mark-2 isolated rehearsals |
| Local Ollama execution | LIVE_VERIFIED (M2) | Mark-2; absent in CI (degrades to class B by design) |
| Backup with real restore | TESTED | `backup.verify()` extracts and opens the DB; now a CI gate |
| Skill registry | DEGRADED (M2) | legacy lowercase policy classes; root cause `skills.py:163-164` vs `:203`; fix = S-01 |
| Drive reads | LIVE_VERIFIED (M2 + this session) | rclone-backed |
| Drive writes | BROKEN (M2) | rclone remotes cannot upload; diagnosable via S-07; remote scope is OWNER-04 |
| OpenClaw | DEGRADED (M2) | 2026.9.1 works transiently on loopback; no persistent gateway/channels/heartbeat |
| Resource governor | IMPLEMENTED, flag OFF | `feature/resource-governor` only; lands via S-03 |
| CI | **ABSENT → now DESIGNED+IMPLEMENTED on this branch** | `.github/workflows/lucyos-ci.yml`; becomes CI_VERIFIED on first green run |
| Authority enforcement | **ABSENT → now IMPLEMENTED+TESTED** | `scripts/verify_authority.py`, 8 tests |
| Branch protection | ABSENT | GitHub API `protected: false`; OWNER-01 |
| Repository visibility | PUBLIC | owner decision: PRIVATE (OWNER-02) |
| Mac portability | ABSENT | one darwin-aware line; S-05 + macOS CI job |

Test suite at this commit: **256 passing** (248 Q006 + 8 verifier).

## 2. Final architecture (this cycle)

Nothing about the AION kernel changes. The cycle adds one layer *around* it and removes duplication *inside* it.

```
OWNER ──────────────── merges, protects, decides visibility/money/exposure
  │
FABLE ──────────────── architecture + protected paths; lands via owner-merged PR
  │  (frozen contract: HIGH_MODEL_BASELINE.json, verified by scripts/verify_authority.py in CI)
OPUS ───────────────── adversarial audit; proposes only
  │
SONNET ─────────────── one task ⇒ one branch task/S-NN ⇒ one PR ⇒ authority-gate + anti-dup
  │
LOCAL MODEL ────────── mechanical drafts inside a Sonnet task
  │
CODEX/MARK-2 ───────── deploys an exact SHA per MARK2_DEPLOYMENT_CONTRACT.md; verify_authority.py deploy first
  │
DETERMINISTIC ──────── everything above prefers this: git, hashes, unit tests, health gate, secret scan
```

Runtime (unchanged in shape, consolidated in content):

```
systemd/launchd timer ─► aion work ─► worker._work_locked
                                        ├─ governor.enforce()            spend axis, demotes queue (runs first)
                                        ├─ _resource_governor_gate()     capacity axis, per-task admission (flag OFF; may only lower/skip — S-04)
                                        ├─ approvals / safe-mode / argv execution boundary (LQ-01, from S-02)
                                        └─ _execute(task, cls)  DET → A(ollama) → B(cloud cheap) → C(strong)
canonical state: aion_core/db.py (one SQLite; all tables; additive migrations)
health:          aion_core/health.py (14 checks + learnrepo + skill_registry; CI requires 8)
```

## 3. Trust boundaries

| Boundary | Enforced by |
|---|---|
| Model → repository | branch protection (OWNER-01) + `authority-gate` (strict, base-ref baseline) + `anti-dup` |
| Model → money | `governor.py` (protected) + `config.py` thresholds (protected); capacity gate can only lower (S-04) |
| Model → shell | `worker.py` argv allowlist + `HARD_DENY_BINARIES` + no-shell subprocess (protected; S-02 brings the hardened version) |
| Model → secrets | `.gitignore`, `security.redact`, `./aion scan` in CI, `.secretscanignore` protected |
| Model → production | Codex deploys only a SHA literally written in the deployment contract; `verify_authority.py deploy` gate |
| Model → owner | `approvals.py` (protected) state machine; tier-3 needs owner |
| Third-party code → LucyOS | `research_registry` stages + `.claude/skills/learnrepo` process; nothing reads the registry to execute code |

## 4. KEEP / REPAIR / SALVAGE / REBUILD / REPLACE / BUILD LATER / REJECT

| Subsystem | Decision | Why |
|---|---|---|
| AION kernel (db, tasks, sessions, resume, approvals, backup, health, memory, worker loop) | **KEEP** | LIVE_VERIFIED on Mark-2; exercised again here; the honest-health design is the best thing in the repo |
| `governor.py` (spend) | **KEEP** | works; protected |
| `resource_governor/` (capacity) | **SALVAGE** (S-03) with precedence rule (S-04) | disciplined, flag-gated, additive; but must land with the rename and the most-restrictive-wins clamp |
| Q006 `learnrepo.py` (evidence/health queue) | **KEEP, keeps the name** | largest, integrated with health/skills/architecture; running on Mark-2 |
| RG `learnrepo.py` (research registry) | **SALVAGE as `research_registry.py`** | different concept; same path was an accident |
| `.claude/skills/learnrepo` (acquisition skill) | **KEEP** | developer tooling, not runtime; different namespace |
| `architecture.py` declaration guard | **KEEP + supplement** | still useful as a checklist; the diff-based `anti-dup` mode is now the enforcement |
| Skill registry | **REPAIR** (S-01) | one migration + the migration-test policy |
| Skill catalog (104 manifests) | **KEEP as inventory** | design-grade; not a promise of capability |
| `recall/` (Phase-1 lexical retrieval) | **KEEP, unwired** | additive, tested, no integration until benchmark evidence |
| Drive bridge | **KEEP + diagnose** (S-07) | code fine; runtime is a remote-scope problem |
| OpenClaw | **BUILD LATER as bounded adapter** (S-09 probe only) | it is an executor/channel behind approvals, never a second orchestrator; persistence is a Mark-2 deployment decision |
| Mac support | **BUILD** (S-05 + macOS CI) | owner P1 |
| SEVAACONNECT (on `claude/fable-deploy-setup`) | **BUILD LATER** | owner: deferred until consolidation is stable |
| `docs/architect/*` planning surface | **REJECT as live surface; archive** (S-02) | duplicate control plane one level up |
| Any second scheduler / DB / memory / approval system | **REJECT** | anti-dup fails the PR |

## 5. Branch salvage decisions

Integration branch: `integration/consolidation-20260916`, created from the freeze commit on `planning/opus-fable-20260916` (= Q006 `2b59aea` + planning + substrate). All Sonnet PRs target it. Owner merges. Owner later opens the integration→main PR.

| Branch | Decision | Mechanism |
|---|---|---|
| `feature/skill-system-q006-architecture-guard` | base | already inside the integration branch |
| `claude/lucyos-architecture-audit-4o4q83` | salvage whole (clean merge) + archive docs | S-02 |
| `feature/resource-governor` | salvage with rename + conflict resolution | S-03 |
| `claude/fable-deploy-setup-mc5nr6` | hold; selective salvage later (SEVAACONNECT deferred) | future task once consolidation is stable; do not merge wholesale (31 behind) |
| Q000–Q005, `feature/learnrepo-queue-health` | delete after protection is on | OWNER-03 (all contained in Q006) |
| `claude/aion-whatsapp-control-1seild`, `arch/lucyos-interface-m-a`, `candidate/mark2-loop-v1.2-20260908`, `feature/lucyos-aion-handoff` | delete | OWNER-03 (zero unique value; verified) |
| `backup/pre-mark2-loop-v1.2-20260908` | tag then delete | OWNER-03 |

Trial-merge evidence: `git merge-tree --write-tree` — Q006+claude-audit clean; RG+claude-audit clean; Q006+RG conflicts only in `cli.py`, `db.py`, `health.py`, `learnrepo.py` (add/add). `worker.py` auto-merges in every pairing.

## 6. State / data model

One canonical store: `$AION_HOME/…sqlite3` via `aion_core/db.py`. Rules, now machine-checked:
- every table is created in `db.py` (`anti-dup`: CREATE TABLE elsewhere fails);
- no new `sqlite3.connect` outside `db.py`/`backup.py`/`drive_bridge.py` (read-only) (`anti-dup`);
- migrations are additive (`CREATE TABLE IF NOT EXISTS`, `_ADDED_COLUMNS` + `_migrate`) — a downgrade of code never needs a downgrade of data;
- **every schema/enum/policy migration ships with an upgrade-from-old-state test** in `tests/test_migrations.py` (owner rule; S-01 creates the file; CI job `upgrade-from-main-schema` proves the main-schema case on every PR).
- Drive is archive/collaboration, never transactional state. `shared_brain/`, `private_state/` never enter git.

Tables added this cycle (via S-03): `resource_snapshots`, `research_targets`. Both additive.

## 7. Scheduler / workflow / worker model

Unchanged: one timer (`aion-work.timer` / launchd `StartInterval`) → `aion work` → `_work_locked` (single-node lease, stale-claim release). Admission order inside the loop is now a contract:
1. `governor.enforce()` — spend axis, mutates the queue, never upgrades.
2. safe-mode / approvals — owner authority.
3. `_resource_governor_gate` — capacity axis, per task, **flag OFF**, may only lower class or skip (S-04).
4. `_execute` on the resulting class.

No second scheduler. LearnRepo maintenance (Q006) rides the same timer via `scripts/maintenance.sh`, makes zero model calls on schedule, and creates tasks only for evidence-backed failures.

## 8. Model hierarchy and escalation

Order: DETERMINISTIC → VERIFIED CACHE/DB → LOCAL (A) → CHEAP CLOUD (B) → SPECIALIST → HIGH (C/Fable) → OWNER. Routing lives in `agents.py` (protected). Downshift is automatic (`governor.py`); upshift is a deliberate act.

Executor scope and escalation are recorded in `HIGH_MODEL_BASELINE.json` (`allowed_executor_scope`, `escalation_rules`) and summarised in `PROTECTED_PATHS.md`. The one sentence that matters: **a lower model that cannot finish a task inside its allowed paths stops and reports; it does not widen, reinterpret, or edit the gate.**

## 9. Security / approval policy

- Repository treated as public until OWNER-02 flips it; nothing in `.lucy/` or the contract contains a secret, host name, or remote name.
- `./aion scan .` is a required CI step on every push and PR.
- `.secretscanignore` and `security.py` are protected; S-08 is the only sanctioned change and it narrows a false positive without widening exemptions.
- Approvals: `approvals.py` protected; tier-3 remains owner-gated; safe mode untouched.
- Money: `governor.py`, `config.py` protected; capacity gate cannot raise spend.
- Execution: argv allowlist + hard deny + no shell (S-02 brings LQ-01).
- Owner-only actions enumerated in the baseline (`owner_only_actions`).

## 10. CI acceptance gates (`.github/workflows/lucyos-ci.yml`)

| Job | Required | Proves |
|---|---|---|
| `code-and-test` (3.9/3.11/3.13) | yes | compile, secret scan, full suite |
| `clean-bootstrap-health` | yes | init→seed→required health→task/approval flow→backup→real restore→fresh-process boot→idempotent init→health again |
| `upgrade-from-main-schema` | yes | state created by `main`'s code, booted by the PR's code: integrity, registry clean, health |
| `authority-gate` | yes | strict protected-path check + anti-dup, verifier read from BASE |
| `authority-drift` | informational | hash/blob drift vs `fable_freeze_sha` (lags legitimately until FABLE-01) |
| `macos-readiness` | advisory → required after first green (FABLE-02) | compile, suite, init/boot on macOS |

Design notes: `./aion health` exits non-zero on any failing check, and `secret_store`/`backup` are legitimately absent on a fresh runner, so CI asserts the 8 required checks via `scripts/ci_health_gate.py` (protected) and prints the rest. The Drive draft's Python 3.14 matrix entry was replaced with 3.13 to avoid runner-availability flakes; nothing else from the draft was dropped.

## 11. Mac readiness contract

- Python 3.9+ standard library only (unchanged) — the macOS job proves the suite is platform-neutral.
- Services: `deploy/launchd/com.lucyos.*.plist` mirror `systemd/aion-*` (S-05); `mark2-*` units are host-specific and stay Linux-only.
- Paths: `$AION_HOME` everywhere; no `/home/...` literals (S-05 test asserts).
- Scheduler abstraction: `learnrepo.py:555` already names `launchd` for darwin; `scripts/install_services.sh` gains a darwin branch (S-05).
- Not in scope this cycle: MLX/Apple-silicon inference. The `recall/` design keeps it behind an adapter; no Mac-only dependency enters core.

## 12. Mark-2 deployment contract

See `.lucy/deployment/MARK2_DEPLOYMENT_CONTRACT.md`. Summary: snapshot → detached checkout of a SHA literally written in the contract → `verify_authority.py deploy` → suite + scan → `aion boot` (additive migrations) → required health → restart timers → one observed loop cycle → evidence. DC-1's SHA is named by Fable only after S-01..S-04 merge and FABLE-01 re-freezes.

## 13. Rollback / recovery

- Code: detached checkout of PREVIOUS_SHA; timers restarted. Additive schema means older code runs on newer data.
- Data: `./aion backup` before every deploy (contract §1); `backup.verify()` is a real restore.
- Authority: any drift is visible via `verify_authority.py self|deploy`; the frozen files can be restored with `git checkout <fable_freeze_sha> -- <path>`.
- Process: every Sonnet PR is one revertable unit tied to a task id.

## 14. WHAT NOT TO BUILD

- A third LearnRepo, a third governor, a second task queue, a second planning surface.
- A manifest-only authority checker (a manifest is editable by the model it constrains — that is why strict mode reads the baseline from BASE).
- A bespoke CI system; the workflow exists.
- Any orchestration framework (`anti-dup` fails the import).
- OpenClaw as an orchestrator. It is a channel/executor behind LucyOS approvals.
- Mac-only or cloud-only dependencies inside `aion_core`.
- A "fix" to the registry that handles one lowercase value (the Drive patch) instead of the class of bug.
- Wholesale merges of `claude/fable-deploy-setup-mc5nr6`.

## 15. Owner decisions — now / later

**Now (block the Sonnet phase until done):**
- OWNER-01 branch protection on `main` and the integration branch with the four required checks; direct pushes off; admin bypass is the Fable/owner landing path.
- OWNER-02 repository → PRIVATE (decided; needs the click).
- Approve creation/use of `integration/consolidation-20260916` as the single integration branch (created by Fable from the freeze commit; contains no code beyond Q006 + substrate).

**Later:**
- OWNER-03 branch deletions/tag (after protection).
- OWNER-04 rclone write scope on Mark-2 (after S-07 tells you what is missing).
- Turn on `resource_governor.enforce_admission` in production only after a Mark-2 rehearsal with S-04 in place.
- SEVAACONNECT salvage scope, once consolidation is stable.
- Name DC-1 (Fable does this; owner approves the deploy).
