# 07 — Milestone Gates M0–M9

Each milestone: purpose · prerequisites · tasks · authority ceiling · tools/skills · outputs · tests ·
success metrics · rollback · stop conditions · owner decision · parallelism. Task IDs resolve in
`06_TASK_GRAPH.json` / `16_FIRST_10_TASKS.md`. "Gate report" = `evidence/M<n>_GATE.md` written by the
controller, reviewed by Fable, decided by the owner where noted.

## M0 — CANONICAL BASELINE LOCK
- Purpose: one agreed description of reality before anything is measured or changed.
- Prerequisites: this package on the research branch.
- Tasks: **S-40** baseline lock · **OWNER-06** node checkout policy · **OWNER-07** branch-protection state.
- Authority ceiling: L1 (S-40); L4 decisions are the owner's.
- Tools: `git`, `python3 -m unittest`, `./aion scan`, `check_portability.py`, GitHub Actions API, Drive read.
- Outputs: `evidence/M0_BASELINE.md` (SHA, CI run id, counts by one fixed command set, branch inventory with
  ahead/behind, open PRs, node checkouts as reported by the owner, Mark-2 health as reported).
- Success: every number in `01` §A/§B/§C is either confirmed or corrected in the file; owner questions
  posed as exactly two decisions.
- Stop: `main` CI red, or `main` moved during the task (re-run once, then record the new SHA).
- Owner decision: OWNER-06, OWNER-07 (do not block M1).
- Parallel: none (it is one task).

## M1 — COMPLEXITY + CONTEXT MAP
- Purpose: deterministic, reproducible maps that replace every agent's private re-derivation.
- Prerequisites: M0 report exists.
- Tasks: **S-41** `scripts/complexity_map.py` · **S-42** `scripts/duplication_scan.py` · **S-43**
  `scripts/task_context_profiler.py` + baseline of six task types.
- Authority ceiling: L2 (new deterministic scripts under `scripts/`, stdlib only, tests under `tests/`).
- Gate: pre/post architecture audit (04 §3); anti-dup must stay clean (scripts are not `aion_core`); no
  third-party import (`networkx` in the Executive Summary sketch is **not** allowed — stdlib `ast` only).
- Outputs: `evidence/complexity_map.json`, `dependency_graph.json`, `hotspots.md`, `duplication_report.md`,
  `dead_weight_candidates.md`, `context_cost_baseline.md`.
- Tests: each script has a unit test on a fixture tree; output is byte-stable for a fixed SHA.
- Success metrics: maps regenerate identically twice; every hotspot in `01` §B appears; cycles list matches
  the 14 found here or explains the difference.
- Rollback: delete the scripts; nothing depends on them yet.
- Stop: a script needs anything outside stdlib; a scan needs to *execute* repo code.
- Owner decision: none. Fable review **FABLE-06** of the maps before M2.
- Parallel: S-41 ∥ S-42 ∥ S-43 (three independent scripts; different workers).

## M2 — LOGICAL MODULE CONTRACTS
- Purpose: name the eight modules, their owned files, seams, allowed/forbidden deps, state, tests,
  invariants, ADRs, risk — without moving a file.
- Prerequisites: FABLE-06 accepted M1 maps.
- Tasks: **S-44** manifests + schema + `aion context`-readable index.
- Authority ceiling: L1 (metadata) — the schema is a JSON file under `.lucy/architecture/`, not code.
- Outputs: `.lucy/architecture/modules/<module>.json` ×8, `.lucy/architecture/module.schema.json`,
  `.lucy/architecture/README.md` (one page).
- Tests: a unit test asserts every tracked `.py` under `aion_core/`, `bridges/`, `scripts/` is owned by
  exactly one manifest and every manifest's files exist (added in S-44, allowed because it is a test).
- Success: 100% file ownership coverage; each manifest ≤ 60 lines; `allowed_dependencies` derived from the
  M1 graph, `forbidden_dependencies` explicit.
- Stop: two modules genuinely need the same file (report, do not split the file).
- Owner decision: **ratify direction + module cut** (04 §5). M3 may start on the research branch before
  ratification; nothing merges to `main` before it.
- Parallel: none.

## M3 — BOUNDED CONTEXT PILOT
- Purpose: prove `aion context` + manifests give a worker what it needs with ≤ 25% of baseline source volume.
- Prerequisites: S-44 manifests; S-43 profiler; owner ratification for the `main` PR of S-45.
- Tasks: **S-45** extend `aion context` (`--module`, repo section, budget, delta/watermark salvage) ·
  **S-46** pilot: two real bounded tasks (**S-47** salvage `aion verify` from `2cd3cc5`; **S-49** salvage
  hermetic test env from `10c8d79`) executed by Codex and Claude *using only the pack*, measured.
- Authority ceiling: L2 (`context.py` is deliberately unprotected; `cli.py` arg addition).
- Gate: S-45 PR targets `main` (owner merge) because Mark-2 workers must eventually get the same pack; until
  merged, pilot runs from the task branch.
- Outputs: `evidence/context_pilot_results.md` with per-task: files read, LOC read, tokens (from
  `model_usage` where recorded), calls, retries, wall time, correctness (tests pass first try? rework count).
- Success (targets from the DEV plan, not guarantees): ≤ 10 source files per pack; ≤ 25% of the S-43 baseline
  volume; both pilot tasks land green with ≤ 1 rework; no correctness loss vs baseline.
- Stop: a worker needed a file the pack excluded **three times** → the manifest, not the worker, is wrong;
  fix manifest, rerun. Pack cannot fit budget for a kernel task → escalate to Fable (module cut too coarse).
- Owner decision: merge S-45 to `main`; merge S-47/S-49 to `main` (they shrink node divergence).
- Parallel: S-47 ∥ S-49 (different workers, disjoint files) after S-45.

## M4 — DEPENDENCY-BOUNDARY PILOT
- Purpose: one enforced boundary, warning-mode first, with a ratchet.
- Prerequisites: S-44; M3 results.
- Tasks: **S-48** `scripts/check_boundaries.py` reading manifests (`allowed_dependencies`), whole-tree,
  `KNOWN_EXCEPTIONS` naming the task that removes each; first rule set = (a) core never imports
  `host.linux`/`host.macos` directly, (b) `business` and `interfaces` may not import `kernel.state` private
  helpers beyond the seam list, (c) nothing outside `kernel.state`/`backup`/`drive_bridge`/`semantic_recall`
  imports `sqlite3`.
- Authority ceiling: L2 while warning-only; promotion to a required CI step is L4 (CI workflow is
  constitutional) → owner.
- Outputs: `evidence/boundary_report.md` (violations, exceptions, false positives over ≥ 5 runs).
- Success: 0 false positives on `main` across 5 consecutive days of runs; every true violation is either an
  exception with a task or fixed by an L2 task.
- Rollback: delete the script; no CI change until promoted.
- Stop: a rule needs a protected-path change to satisfy → task card for L3, not a silent exception.
- Owner decision: promote to required CI (M4 exit).
- Parallel: S-48 ∥ M3's S-47/S-49.

## M5 — LOW-RISK CLEANUP
- Purpose: remove measured dead weight; nothing speculative.
- Prerequisites: S-42 report; owner has seen the stale-doc list.
- Tasks: **S-50** archive superseded planning docs (`INTEGRATION_ROADMAP*`, `OPUS_ROADMAP_REVISION_PROMPT`,
  `CODEX_INTEGRATION_EXECUTION_PLAN` once its S-31/S-32 items are re-homed, stale `CANONICAL_BRANCH.md`
  text) into `.lucy/archive/planning-20260917/` with a 3-line README; collapse the three routers
  (`START_HERE.md`, `docs/README.md`, `directives/README.md`) into one router + two pointers · **S-51**
  fix `HIGH_MODEL_BASELINE.json.integration_branch` (Fable PR, L4) · **S-52+** dead-code removals only where
  S-42 shows no importer, no CLI wiring, no test, no manifest reference, and a grep of `.lucy`/`docs` finds
  no live pointer — one module per PR, with the evidence in the PR body.
- Authority ceiling: L1 for archiving; L2 per dead-code PR; L3 if anything protected.
- Success: `.lucy` + `docs` LOC reduced by a measured amount; `START_HERE.md` ≤ 60 lines; zero broken
  internal links (a test greps for referenced paths).
- Rollback: `git revert`; archives are moves, not deletions.
- Stop: any candidate is referenced by a manifest, directive or the deployment contract.
- Owner decision: the archive list (L1 but owner-visible); OWNER-03 deletions remain L5 and separate.
- Parallel: S-50 ∥ S-52+ (disjoint files).

## M6 — PROGRESSIVE DECOMPOSITION
- Purpose: move one subsystem at a time only where M3/M4 metrics show a boundary that still costs context.
- Prerequisites: M3, M4, M5 exits; owner-ratified direction.
- Candidate order (DEV plan, confirmed by fan-out data): (1) `cli.py::_main` → per-module `register(sub)` +
  `handle(args)` tables (no behaviour change; first seam: the `learnrepo-*`/`skills`/`architecture-check`
  group), (2) one bridge/adapter boundary (`bridges/drive_bridge.py` `Bridge` class 291 lines), (3) one
  optional skill subsystem, (4) one project-specific subsystem (`business`).
- Authority ceiling: L3 (Fable plan per move; `task_overrides` for `worker.py`/`db.py` if touched; owner
  merge).
- Per move: architecture audit → compatibility shim if an import path changes → focused tests → full
  regression → context-cost benchmark → `pre/<TASK_ID>` tag → PR to `main`.
- Success: the moved module's pack shrinks measurably; no test count drop; no public CLI/API change.
- Stop: a move requires a schema change, a protected-path change without override, or a public contract
  change → Fable/owner.
- Owner decision: each move's merge.
- Parallel: never two moves touching the same module; otherwise one code move ∥ one docs task.

## M7 — REPOSITORY TOPOLOGY DECISION
- Purpose: owner chooses A / B / C on measured evidence.
- Prerequisites: M3, M4, M6 (≥ 1 move) reports; `02` §2 table refreshed with measured numbers.
- Tasks: **FABLE-08** refreshed comparison; **OWNER-09** decision.
- Authority: L4.
- Success: decision recorded in `.lucy/authority/` via owner-merged PR (Fable writes the ADR).
- Default if undecided: remain A.

## M8 — OPERATIONALIZATION
- Purpose: make packs, manifests, boundaries and the gate the *normal* Codex/Claude workflow.
- Prerequisites: M4 promoted or explicitly deferred; S-45 on `main`.
- Tasks: **S-53** `handoff.build_prompt` and `scripts/aion_codex_worker.sh` reference `aion context
  <ID> --module` and the manifests (L2; `handoff.py` is unprotected) · **S-54** `START_HERE.md` says
  "run `aion context`" first and lists the module index (L1) · **S-55** `aion health` non-required check
  `module_manifests` (manifest coverage = 100%, boundary warnings count) (L2; `health.py` unprotected) ·
  **FABLE-09** update the Sonnet/Codex prompts under `.lucy/handoffs/` (L4, owner merge).
- Success: a new Codex task on Lucy-den reads ≤ 10 files by default; `aion health` shows the two new
  informational lines; the night-loop prompt no longer says "do not scan the repository" without saying
  what to read instead.
- Owner decision: merge FABLE-09.

## M9 — VALUE MODE (hard exit gate)
- Entry criteria (all measured, all in `14`): (1) M3 targets met on ≥ 4 of the 6 task types; (2) boundary
  check promoted or owner-deferred with reason; (3) M5 text-corpus reduction ≥ 25% of `.lucy`+`docs` lines or
  owner-accepted lower number; (4) no P0/P1 open in the graph; (5) nodes on a SHA named in the deployment
  contract **or** OWNER-06 explicitly accepted the divergence; (6) two consecutive weeks without a
  `BLOCKED_TECHNICAL` in this program.
- Behaviour after entry: the controller caps P4/P5 (architecture/efficiency/cleanup) at ≤ 20% of iterations;
  ≥ 80% go to the owner's value backlog (Mark-2 `aion tasks` top items, delivered through the same authority
  model). Any new architecture work needs a Fable card with a measured regression as its `WHY_THIS_EXISTS`.
- Exit from VALUE MODE (back to repair) only on: `main` CI red for > 1 day, a boundary regression, a
  measured context-cost regression > 25%, or an owner instruction.
