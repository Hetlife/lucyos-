# 01 — Ground Truth Reconciliation

Source-of-truth order applied (master prompt §2): live `main` → live Mark-2 evidence (owner's Drive
baseline, 2026-09-18) → isolated worktree evidence → tests/CI → authority contracts → skills/manifests →
DEV plan → Executive Summary → historical reports → chat.

Classification vocabulary: **VERIFIED FACT** (observed this pass) · **MEASURED BUT MUST REVERIFY**
(measured by someone else, consistent, not re-run here) · **RESEARCH FINDING** · **WORKING HYPOTHESIS** ·
**STALE/CONTRADICTED** · **OWNER DECISION** · **UNKNOWN / NEEDS MEASUREMENT**.

## A. Canonical state

| Claim | Class | Evidence |
|---|---|---|
| Canonical `main` = `66e3a4ef1b8242123555af5a7c9d80115ab23d82` "owner: freeze governed MSOS candidate" | VERIFIED FACT | `git ls-remote`; Drive baseline agrees |
| CI green on that SHA | VERIFIED FACT | run 35279040189, `LucyOS CI`, conclusion success |
| `main` contains the full 2026-09-17 reconciliation (`a99beeb`: waves 1–5) | VERIFIED FACT | `git merge-base --is-ancestor a99beeb origin/main` → yes |
| Open items from the 2026-09-17 health audits (allowlist, `semantic_recall` ruling, promotion) | STALE — all resolved | `57f0e4c` (wave 2), `f2f1211` "owner: permit explicit rebuildable derived sqlite indexes", `2a70020` merge |
| `fable_freeze_sha` | VERIFIED FACT: `2a7002043ceca4ffff2da09bf59860708954370e` | `HIGH_MODEL_BASELINE.json` |
| `HIGH_MODEL_BASELINE.json.integration_branch` = `integration/consolidation-20260916` | STALE field — `main` is canonical; that branch is 30 commits behind and superseded | `CANONICAL_BRANCH.md` on `main` (itself stale: says frozen at `0720a92`) |
| `.lucy/planning/CANONICAL_BRANCH.md` | STALE — names `0720a920`, says 4 owner modules "not yet reached main" (they have) | file content vs `git log` |
| DC-1 deploy SHA | OWNER DECISION, still `<<FABLE_NAMES_SHA>>` — **not deployable** | `MARK2_DEPLOYMENT_CONTRACT.md` §0 |
| Branch protection on `main` | UNKNOWN (was `protected: false` on 2026-09-16 per FABLE_PROGRESS; not re-queried — needs owner/API check) | — |

## B. Repository size and hotspots

| Claim | Class | Evidence |
|---|---|---|
| 386 tracked files, 132 `.py`, 119 `.json`, 20,612 py LOC, 9,503 md LOC, 5,470 json LOC (DEV plan) | VERIFIED FACT — exact match on `66e3a4e` | `git ls-files` + `wc -l` in detached worktree |
| 58 test files (DEV plan) | VERIFIED FACT (58 entries in `tests/`, 57 `test_*.py` + `base.py`) | `ls tests` |
| 87 Markdown/docs files (DEV plan / Drive) | MEASURED BUT MUST REVERIFY — I count 79 tracked `*.md`; the 87 likely includes `.txt` directives/handoffs. Immaterial; agree on one counting command in S-40 | `git ls-files '*.md'` |
| 562 tests passing in ~52.5 s | VERIFIED FACT — 562 OK, 2 skipped, **46.1 s** here | fresh run on `66e3a4e` |
| "~150–200k LOC, hundreds of modules" (Executive Summary) | STALE/CONTRADICTED — off by ~8×; 67 production modules | AST scan |
| Hotspots `fable.py` 678, `learnrepo.py` 669, `worker.py` 615, `drive_bridge.py` 602, `cli.py` 601, `db.py` 569, `skills.py` 455 | VERIFIED FACT | `wc -l` |
| `cli.py::_main` is 564 lines | VERIFIED FACT (the only function >120 lines; five others 82–111) | AST scan |
| Import graph: 67 prod modules; fan-in leaders `db` 43, `util` 39, `security` 26, `config` 25, `tasks` 17; fan-out leaders `cli` 41, `worker` 16, `reports` 15, `fable` 14 | VERIFIED FACT (deterministic scan this pass; S-41 makes it reproducible) | AST scan |
| Import cycles | VERIFIED FACT: 14 small cycles, all through `resume↔tasks` (deliberate late import in `tasks.complete`) and `learnrepo↔skills`. Not pathological; a candidate boundary rule, not a bug | AST scan |
| `sqlite3.connect` sites: `db.py`, `backup.py`×2, `drive_bridge.py`, `semantic_recall.py`×2 (owner-allowed derived), `verify_authority.py` | VERIFIED FACT | grep |
| `global` keyword: 1 site (`db.py HAS_FTS`) | VERIFIED FACT | grep |
| Portability: 0 violations, 3 known exceptions (S-11, S-12); secret scan clean | VERIFIED FACT | ran both |
| Directory LOC concentration `aion_core` 10,055 / `tests` 6,556 / `.lucy` 4,992 / `skills` 4,795 / `.claude` 3,366 / `docs` 2,424 (Drive baseline) | MEASURED BUT MUST REVERIFY (owner's measurement, plausible, S-40 re-runs it) | Drive doc |

**Research finding worth stating plainly:** the "cognitive size" problem is dominated by non-code text.
`.lucy` + `skills` + `.claude` + `docs` + `directives` ≈ 15.6k lines vs 10k lines of `aion_core`. An agent
told to "read the authority docs first" reads more governance prose than kernel code.

## C. Node roles and runtime

| Claim | Class | Evidence |
|---|---|---|
| Mark-2 is canonical runtime/state/scheduler | OWNER DECISION (policy, binding) — and consistent with code: one SQLite via `db.py`, timer `aion-work.timer` (10 min) → `build_loop.sh` → `aion boot`/`work` | contracts; `systemd/` |
| Mark-2 checkout is canonical `main` | STALE/CONTRADICTED — Mark-2 is on `feature/resource-governor` @ `2cd3cc5` (136 behind `main`, 4 ahead) | Drive baseline |
| Lucy-den checkout | VERIFIED via owner: also `feature/resource-governor` @ `2cd3cc5` | Drive baseline |
| Mark-2 health: healthy; DB integrity ok; 0 ready / 0 running / 4 blocked-or-waiting / 13 done; 0 unresolved errors; 3 Ollama models; tree clean | MEASURED BUT MUST REVERIFY (owner-collected 2026-09-18) | Drive baseline |
| "Mark-2 timers paused / safe mode" (Executive Summary) | UNKNOWN — no repo evidence; Drive baseline says health OK but does not state timer state. Ask in S-40/OWNER-06 | — |
| Lucy-den has local models (Qwen/GGML) and Codex/Claude Code | MEASURED BUT MUST REVERIFY (owner statement); repo has `scripts/aion_codex_worker.sh` (Codex as class-B worker, `-s workspace-write --ephemeral`) | Drive baseline; script |
| "Lucy-den" appears nowhere in the repository | VERIFIED FACT (0 hits) — node roles exist only in owner docs; the repo knows `Mark-2` (45 files) and `agents` rows (`openclaw`, `ollama-local`, `cloud-sonnet`, `cloud-cheap`, `cloud-strong`, `owner`) | grep |
| Mark-2 deploys only a SHA literally written in the deployment contract | OWNER DECISION (binding; `deploy` mode of the verifier enforces) | contract §0 |
| `resource_governor` running on the nodes | WORKING HYPOTHESIS — the checkout has it; whether `enforce_admission` is on is UNKNOWN (contract says it must stay OFF) | — |

## D. Existing mechanisms the documents propose to build

| Proposed in documents | Exists on `main`? | Class / what to do |
|---|---|---|
| Task queue / scheduler | **Yes**: `tasks.py` (12 states, value ranking, deps, claim/stale-release, `MAX_TASK_RETRIES=3`), `worker.py`, `aion-work.timer` | VERIFIED — reuse; never add another |
| Approval system | **Yes**: `approvals.py` (`NEEDS_APPROVAL`, exact `APPROVE <ID>`), owner tier D | VERIFIED — reuse |
| Checkpoint / resume | **Yes**: `resume.py` (`checkpoint()`, `boot()`, `RESUME.json/.md`), `sessions.py` (per-session logs with resume point) | VERIFIED — reuse |
| Retry / escalation | **Yes**: `tasks.fail` → READY×2 then BLOCKED; `agents.escalate` one rung; `worker._fail` escalates at retry≥2 for DET/A/B | VERIFIED — reuse the numbers |
| Model routing | **Yes**: `agents.route(kind, complexity, stakes, ambiguity)` → DET/A/B/C/D; `governor.py` downshifts; `handoff.py` writes the cheap-worker prompt | VERIFIED — reuse |
| Context pack | **Partly**: `aion_core/context.py` → `aion context <TASK_ID>` builds a DB-driven work order (objective, state, files field, criteria, memory, failures, result-packet contract). It does **not** select source files/tests/manifests from the repo | VERIFIED — extend (S-45) |
| Context pack builder (delta/watermark) | **On a branch**: `feature/context-pack` adds `aion_core/context_pack.py` (git-delta packet since `last_high_model_reviewed_commit`, 30 KiB cap) — base is ~136 commits stale | VERIFIED — salvage the idea into `context.py`; do not merge the branch wholesale |
| `task_context_profiler` skill | **No** (nowhere on any branch) | Build as a deterministic script (S-43), not a skill |
| `context_pack_builder`, `context_cache`, `repo_metrics`, `codex_runner`, `claude_runner`, `code_inspector`, `learnrepo_fetch` skills "in LucyDB" | **No** — STALE/CONTRADICTED. Fresh-home registry has 9 skills; catalog has 104 manifests (inventory, `lifecycle_state: DISCOVERED`) | Do not build as skills |
| Architecture audit ("Lucy-architect-audit") | **Partly**: `architecture.py` + `aion architecture-check <proposal.json>` validates a *skill-integration proposal* against a duplicate-control-plane checklist (needs a registered `skill_id`); catalog entry `core.architecture-audit` is `enabled: false`; **not in CI**. The diff-based enforcement is `scripts/verify_authority.py anti-dup` (CI `authority-gate`, PR only) | VERIFIED — the "audit" is a gate composed of both plus high-model review (see 04) |
| Plugin infrastructure | **No dynamic loader**; **yes** manifests: `skills/manifest.schema.json`, `skills.py` (`register_manifest`, lifecycle, `activate`, catalog sync) | VERIFIED — Option B's mechanism already exists as metadata; do not add a loader |
| Memory / recall | **Yes**: `memory.py` (+FTS), `recall/` (lexical, unwired), `semantic_recall.py` (derived index, owner-allowed) | VERIFIED — reuse |
| Sync / cross-node packets | **Yes**: `packets.py` (AI SYNC PACKET ingest, idempotent by hash), `sync_outbox.py` (C2 PENDING_SYNC ledger), `intake.py` (C3 provenance) | VERIFIED — this is the node boundary |
| Authority / protected paths | **Yes**: `HIGH_MODEL_BASELINE.json`, `PROTECTED_PATHS.md`, `verify_authority.py strict|anti-dup|self|deploy|freeze`, CI `authority-gate` | VERIFIED — the controller scope must be added here (OWNER-08) |
| Deployment guardian (C5) | **Yes**: `guardian.py` 12-stage pipeline, `ENABLED=False` at module level | VERIFIED — unchanged |
| Usage/cost telemetry | **Yes**: `metrics.record_usage` → `model_usage`; `aion routing-report`; `usage_telemetry.py` (ccusage, read-only) | VERIFIED — use for context/cost metrics |
| Machine acceptance test `aion verify` | **On a branch only** (`2cd3cc5` on `feature/resource-governor`) | Salvage candidate (pilot task S-47) |

## E. Process claims

| Claim | Class |
|---|---|
| "Every executable change goes through Lucy-architect-audit" | OWNER DECISION — implemented here as the gate in 04 §3; today the deterministic half runs only on PRs (`authority-gate`), and `anti-dup` reads the baseline from the base branch |
| "Use existing `./aion context` before new context infra" (DEV plan) | VERIFIED as correct advice; see D |
| DEV plan's first three tasks (map → manifests+pilot → boundary experiment) | RESEARCH FINDING, **retained** with two amendments: M0 gains the node-divergence gate; Task 2's pilot uses two *real* salvage tasks from `2cd3cc5` so the pilot also shrinks the divergence (16) |
| Executive Summary's "recommend Option A" | RESEARCH FINDING, consistent with repo evidence; formalised in 02 with a discriminating experiment rather than taste |
| "Google Drive is the research archive" | OWNER DECISION — folder exists: `LucyOS/Architecture_Research/Codebase_Reduction_2026-09/` with `01_CURRENT_STATE_BASELINE` |
| Task-ID convention | VERIFIED FACT: the verifier only recognises `(S|FABLE|OWNER|CODEX)-\d{1,4}`; highest used `S-32`, `FABLE-04`, `OWNER-05` |

## F. Unknowns that block nothing in M0–M4 but must be measured

1. Mark-2 timer/pause/safe-mode state and whether `resource_governor.enforce_admission` is off.
2. Branch protection status on `main` (OWNER-01 from 2026-09-16).
3. Actual context tokens per task type — no telemetry exists yet for *files read by an agent*; S-43 builds the
   deterministic proxy (files/LOC of a task's touched set), and `model_usage` gives prompt tokens where
   the worker records them.
4. Whether `feature/lucyos-aion-handoff` carries unique content (open from the 2026-09-17 follow-up).
5. Which of the 104 catalog manifests correspond to any real capability (Fable's 2026-09-16 package already
   classifies the catalog as "design-grade inventory, not a promise").
