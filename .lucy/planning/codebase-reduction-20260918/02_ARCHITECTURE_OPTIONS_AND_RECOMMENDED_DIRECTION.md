# 02/03 — Architecture Options and Recommended Direction

## 1. What the problem actually is (measured, not perceived)

- **Not raw size.** 20.6k py LOC / 67 production modules fits in one strong-model context window. The
  Executive Summary's premise ("beyond even a 64k window") is false for the kernel.
- **Text-to-code ratio.** ~15.6k lines of governance/planning/skills/docs text vs 10k lines of kernel. Agents
  are instructed to read the text first. This is the measurable context burden.
- **Concentration.** `cli.py::_main` (564 lines) dispatches 70+ subcommands and imports 41 modules; `db.py`
  is imported by 43 modules; `worker.py`/`fable.py`/`learnrepo.py` are 600–680 lines each.
- **Ambiguous boundaries, not missing ones.** The repo has *implicit* domains (state, tasks/approvals,
  execution, memory, skills/learnrepo, interfaces, health/governance, business) but no manifest says which
  files belong to which, what may import what, or which tests prove which module. Every agent re-derives it.
- **Runtime drift.** The nodes run a branch that `main` does not contain (`aion verify`, hermetic tests,
  resource governor). Reasoning from `main` about behaviour on Mark-2 is currently wrong by construction.
- **Duplicate planning surfaces.** `.lucy/planning/` holds six 2026-09-17 documents, two of which are
  explicitly superseded by a third; `docs/internal/health-audit/` holds two audit generations; `START_HERE.md`
  and `docs/README.md` and `directives/README.md` are three routers.

## 2. Options compared with weighted evidence

Weights (master prompt §25). Scores 1–5, 5 = best for LucyOS *now*.

| Criterion (weight) | A. Modular monolith | B. Thin core + plugin loader | C. Hybrid core + service/repo split |
|---|---|---|---|
| Context reduction (0.20) | 4 — manifests + `aion context` bound reads | 4 — same, plus code exclusion; gain over A unproven | 3 — service boundaries help, but cross-repo reads add back |
| Correctness / regression risk (0.15) | 5 — no code moves in M0–M4 | 3 — a loader touches `skills.py`/`worker.py` (protected) | 2 — network + state consistency |
| Migration risk (0.10) | 5 | 3 | 1 |
| State-consistency risk (0.15) | 5 — one SQLite unchanged | 4 | 1 — violates "one canonical store" unless very carefully bounded |
| Debug complexity (0.10) | 4 | 3 | 2 |
| Testability (0.10) | 4 — module→test map | 3 | 3 |
| Deployment complexity (0.05) | 5 — unchanged systemd/launchd | 4 | 1 — DC-1 not even named yet |
| Security (0.05) | 5 — anti-dup, argv allowlist untouched | 3 — dynamic loading is an attack surface | 2 |
| Rollback (0.05) | 5 | 3 | 2 |
| Existing Lucy mechanisms (0.05) | 5 — everything exists | 4 — manifests exist, loader does not | 2 |
| **Weighted total** | **4.55** | **3.50** | **1.95** |

Reading: B is not an alternative to A; it is A plus a loader. Everything B promises for context is
obtainable in A by *excluding* files via manifests and `aion context` without loading code dynamically.
C is a later option that only earns consideration if, after M4, a measured boundary still leaks (e.g.
recall/embedding compute that must live off-node).

## 3. Recommended near-term direction (for owner ratification at M2 gate)

**Hybrid modular monolith, exactly as the DEV plan hypothesised, made concrete:**

1. **One repo, one canonical SQLite, one timer/loop.** Unchanged.
2. **Eight logical modules** with manifests under `.lucy/architecture/modules/` (S-44). Proposed cut, from
   fan-in/fan-out evidence:

| Module | Owned files (initial) | Public seam | Protected? |
|---|---|---|---|
| `kernel.state` | `db.py`, `config.py`, `util.py`, `security.py`, `bootstrap.py`, `backup.py` | `db.connect/get_meta/set_meta/log_event`, `security.redact/scan_text` | db, config, security: yes |
| `kernel.tasks` | `tasks.py`, `approvals.py`, `errors.py`, `resume.py`, `sessions.py`, `packets.py`, `notebook.py` | `tasks.create/claim/complete/fail/ready`, `approvals.request/decide`, `resume.checkpoint/boot` | approvals, resume: yes |
| `execution` | `worker.py`, `agents.py`, `plan.py`, `governor.py`, `tempworker.py`, `handoff.py`, `model_gateway.py`, `platform_resolver.py`, `host/` | `agents.route/escalate`, `plan.apply`, `worker.work/run_command` | worker, agents, governor: yes |
| `memory` | `memory.py`, `recall/`, `semantic_recall.py`, `context.py` | `memory.search/remember/decide/why`, `context.build` | no |
| `skills` | `skills.py`, `learnrepo.py`, `architecture.py`, `skills/catalog/**`, `.claude/skills/**` | `skills.register_manifest/validate_registry`, `architecture.audit` | architecture: yes |
| `interfaces` | `router.py`, `api.py`, `reports.py`, `cli.py`, `bridges/*`, `web/*`, `integrations/openclaw/**` | CLI, HTTP v1, WhatsApp router | router: yes |
| `governance` | `health.py`, `metrics.py`, `milestones.py`, `autonomy.py`, `guardian.py`, `portability.py`, `usage_telemetry.py`, `scripts/verify_authority.py`, `scripts/check_portability.py`, `scripts/ci_health_gate.py` | `health.run_all`, `metrics.budget_status` | verifier, gates: constitutional |
| `business` | `fable.py`, `experiments.py`, `money_path.py`, `deliveries.py`, `intake.py`, `sync_outbox.py`, `seed.py`, `owner_setup.py` | `aion money*`, `aion experiment-*` | no |

   Manifests are metadata; **no file moves** are required to create or enforce them.
3. **Boundaries as a ratchet** (S-48): `scripts/check_boundaries.py` reads the manifests' `allowed_dependencies`
   and reports violations; warning-only until the false-positive rate is measured, then a required CI step,
   following the exact `check_portability.py` pattern (`KNOWN_EXCEPTIONS` naming the task that removes each).
4. **Skill manifests remain the extension seam.** New optional capability = manifest + module behind a
   feature flag; no plugin loader. The `architecture-check` proposal JSON remains the pre-flight for any new
   *skill integration*.
5. **Context by contract.** `aion context <TASK_ID> --module <name>` returns the work order plus the module
   manifest's owned files, public seam, tests, ADRs, neighbours, exclusions, SHA, and a size budget (S-45).
6. **Business/project code loads last.** `business` and `integrations/**` are excluded from default context
   for kernel tasks; `.lucy/planning/**`, `.lucy/archive/**`, `directives/**`, `docs/internal/**` are excluded
   from *every* context pack unless the task names them.

## 4. What remains undecided (owner decisions, with the evidence that decides them)

| Decision | Decided by | Evidence needed |
|---|---|---|
| Ratify the 8-module cut and the direction above | OWNER at M2 gate | S-41/S-42 maps + S-44 manifests |
| Node checkout policy (name DC-1 = `main`, or fast-track `resource-governor` salvage) | OWNER-06 at M0 | S-40 baseline |
| Whether `check_boundaries.py` becomes a required CI step | OWNER at M4 gate (constitutional path: CI workflow) | ≥2 weeks warning-mode false-positive rate |
| Repository topology (stay A / consider C for recall) | OWNER at M7 | M3+M4+M6 measurements |
| Whether the `governance` text corpus is pruned/archived (biggest measured context lever) | OWNER at M5 | S-42 stale-doc report |

## 5. Discriminating experiment (if the owner wants proof before ratifying A)

Run S-46's pilot twice on the same two tasks: once with `aion context --module` packs (A), once with the
same packs plus *only* the files a hypothetical loader would exclude (simulating B). If B's exclusion set is
empty or <10% of pack bytes, B adds nothing and is closed. Cost: zero extra code.
