# 16 — First 10 Executable Tasks (with acceptance criteria)

Order = execution order. Fields follow `08_TASK_CARD_TEMPLATE.md`; fields identical for every card are
stated once here and inherited:

- `CANONICAL_SHA`: `66e3a4ef1b8242123555af5a7c9d80115ab23d82` (re-read `origin/main` at SELECT; if moved,
  update the card's SHA and re-check START STATE before dispatch)
- `WORKTREE`: detached worktree of the base ref under `~/lucyos-worktrees/<TASK_ID>/`; never the node's
  live checkout
- `FILES_FORBIDDEN` (always, in addition to the card's list): every path in
  `HIGH_MODEL_BASELINE.json.protected_paths`; `.lucy/planning/**` other than this folder; `tests/base.py`
  unless named
- `REGRESSION_TESTS`: `python3 -m compileall -q aion_core bridges tests scripts` ·
  `python3 -m unittest discover -s tests -t . -q` · `./aion scan .` · `python3 scripts/check_portability.py` ·
  `python3 scripts/verify_authority.py anti-dup --base origin/main` ·
  `python3 scripts/verify_authority.py strict --base origin/main --branch "$(git branch --show-current)"`
- `SECURITY_CHECKS`: scan clean; no new `subprocess`/network/`shell=True`; nothing under `private_state`,
  `secrets`, `~/.ssh`, browser or OAuth paths read
- `REQUIRED_LUCY_SKILLS`: `smallest-fix` before any code; `learnrepo` only where the card says
- `MAX_ATTEMPTS`: 3
- `STOP_CONDITIONS` (always): start state drifted · needs a protected path · needs a non-stdlib dependency ·
  needs a public CLI/API/schema change · a test must be weakened to pass · scope leaves `FILES_ALLOWED`

---

## S-40 — M0 canonical baseline lock
- MILESTONE M0 · LEVEL **L1** · PRIORITY P1 · EXECUTOR controller · REVIEWER ci+controller
- OBJECTIVE: one file states what `main`, CI, the branches, the PRs and (as reported) the nodes are, with
  the commands that produced each number.
- WHY: `01` §A–§C has three "MEASURED BUT MUST REVERIFY" and two UNKNOWN rows; every later metric is
  relative to this file.
- WORK_BRANCH `research/codebase-reduction-20260918` (create from `origin/main` if absent)
- PREREQUISITES: FABLE-05 (this package) on the branch.
- CONTEXT_PACK: none needed beyond `git`, GitHub Actions API, the Drive baseline doc.
- LEARNREPO: no (internal).
- ARCHITECTURE_AUDIT: n/a (no code). Post: `./aion scan .`.
- FILES_ALLOWED: `.lucy/planning/codebase-reduction-20260918/evidence/M0_BASELINE.md`, `CHECKPOINT.md`,
  `06_TASK_GRAPH.json` (status fields only).
- STEPS: (1) `git fetch --prune`; record `origin/main` SHA, latest `LucyOS CI` run id/conclusion for it.
  (2) In a detached worktree of that SHA run the exact counting commands from `14` §A and the full suite;
  record counts and times. (3) `git for-each-ref` all remote branches with ahead/behind vs `main`; mark
  each as contained / unique / superseded (use `git merge-base --is-ancestor`). (4) List open PRs (16 today)
  with base/head/state. (5) Copy node facts from the Drive baseline verbatim with its link and date; do not
  infer more. (6) Dry-run the strict gate: create `task/S-40-baseline` from `origin/main`, empty commit with
  `Task-ID: S-40`, run strict — expect `ok: true` with `changed: 0`; delete the branch. (7) Write the two
  owner questions (OWNER-06, OWNER-07) as one paragraph each with the evidence lines they need.
- SUCCESS_CRITERIA: file exists; every number has its command; the 87-vs-79 markdown count is resolved by
  naming one command; strict dry-run recorded; `TASK_GRAPH.json` shows S-40 DONE and OWNER-06/07 NEW→
  BLOCKED_OWNER; checkpoint block written.
- BEFORE/AFTER METRICS: this *is* the baseline (14 §A, §C, §D).
- ROLLBACK: delete the file (nothing depends on it yet).
- OWNER_APPROVAL: none to execute; raises OWNER-06/07.
- NEXT_UNLOCKED: S-41, S-42, S-43.

## OWNER-06 — Node checkout policy
- MILESTONE M0 · LEVEL **L4** · owner decides · see `11` §2 for the two options and their costs.
- ACCEPTANCE: the decision text in `CHECKPOINT.md`; if option (a), Fable opens the deployment-contract PR
  naming the SHA (authority-gate fails by design; owner merges); if (b), S-03/S-04 cards are re-issued
  under Fable with `task_overrides` before any worker starts.
- Blocks only M6/M8/M9; M1–M5 proceed.

## S-41 — `scripts/complexity_map.py`
- MILESTONE M1 · LEVEL **L2** · P3 · EXECUTOR codex · REVIEWER claude-code · PARALLEL with S-42, S-43
- OBJECTIVE: a stdlib-only script that, for a given tree, writes `complexity_map.json` (per module: path,
  LOC, functions>120, classes, imports out, importers in), `dependency_graph.json` (edges), `hotspots.md`
  (top-12 by LOC, fan-in, fan-out, function length; cycles list) — byte-stable for a fixed SHA.
- WHY: `01` §B numbers were produced ad hoc this pass; M2/M4/M6 need them reproducible.
- WORK_BRANCH `task/S-41-complexity-map` from `origin/main`; PR → research branch.
- RELEVANT_MODULE governance · CONTEXT_PACK: card + `scripts/check_portability.py` (as the style/
  ratchet precedent) + `scripts/runtime_inventory.py` + `tests/test_portability_guard.py`; ≤ 6 files.
- LEARNREPO: no — `ast` + a DFS is 150 lines; no external graph library (stdlib rule; `networkx` refused).
- ARCHITECTURE_AUDIT pre: strict/anti-dup on the empty branch; checklist: new file under `scripts/` (not
  `aion_core`), no state, no network. Post: same + full regression.
- FILES_ALLOWED: `scripts/complexity_map.py`, `tests/test_complexity_map.py`,
  `.lucy/planning/codebase-reduction-20260918/evidence/{complexity_map.json,dependency_graph.json,hotspots.md}`.
- TARGETED_TESTS: `tests/test_complexity_map.py` — fixture tree with a known cycle, a >120-line function, a
  relative import; asserts JSON keys, cycle detection, determinism (two runs identical), CLI exit 0.
- SUCCESS_CRITERIA: `python3 scripts/complexity_map.py --root . --out <dir>` runs in < 10 s; reports 67±2
  production modules, `cli._main` as the only >120-line function, fan-in `db` ≥ 40, 14 cycles (or an
  explained difference); no third-party import; anti-dup clean.
- ROLLBACK: delete the two files.
- NEXT_UNLOCKED: FABLE-06 (with S-42, S-43).

## S-42 — `scripts/duplication_scan.py`
- MILESTONE M1 · LEVEL **L2** · P3 · EXECUTOR claude-code · REVIEWER codex · PARALLEL
- OBJECTIVE: stdlib-only scan writing `duplication_report.md` (function bodies with identical normalised
  AST hash and > 15 lines; repeated retry/backoff, health-check and validation shapes by name pattern) and
  `dead_weight_candidates.md` (modules with zero importers *and* no CLI wiring in `cli.py` *and* no test
  importing them *and* no manifest/`.lucy`/`docs` reference; `.md` files referencing paths that do not
  exist; planning docs whose header says superseded). **Reports only; deletes nothing.**
- WHY: M5 may remove only evidence-confirmed dead weight (DEV plan Phase 6).
- WORK_BRANCH `task/S-42-duplication-scan` · CONTEXT_PACK: card + `scripts/scan_history.py` (grep-style
  precedent) + `aion_core/cli.py` (wiring source) ≤ 5 files.
- LEARNREPO: no.
- FILES_ALLOWED: `scripts/duplication_scan.py`, `tests/test_duplication_scan.py`, the two evidence files.
- TARGETED_TESTS: fixture with a duplicated function, an orphan module, a doc with a dead link; asserts each
  is found and a wired module is *not* reported.
- SUCCESS_CRITERIA: runs < 15 s; every candidate line carries the four negative checks it passed; the report
  lists `INTEGRATION_ROADMAP_20260917.md`, `INTEGRATION_ROADMAP_V2_20260917.md`, `OPUS_ROADMAP_REVISION_PROMPT_20260917.md`,
  `CANONICAL_BRANCH.md` as superseded/stale (known ground truth); anti-dup clean.
- NEXT_UNLOCKED: FABLE-06, S-50, S-52.

## S-43 — `scripts/task_context_profiler.py` + six-task baseline
- MILESTONE M1 · LEVEL **L2** · P3 · EXECUTOR codex · REVIEWER claude-code · PARALLEL
- OBJECTIVE: given a reference commit (or a file list), compute the *deterministic context proxy* an agent
  would read: touched files + one import hop (both directions) + tests importing them + the docs
  `START_HERE.md` routes to; output files, source LOC, docs LOC, approx tokens (bytes/4, labelled
  "approx"). Run it for the six reference commits in `14` §B and write `context_cost_baseline.md`.
- WHY: no telemetry of files-read exists; M3 needs a baseline that is measured, not the Executive Summary's
  estimates.
- WORK_BRANCH `task/S-43-context-profiler` · CONTEXT_PACK: card + `aion_core/context.py` + `scripts/complexity_map.py`
  if S-41 is merged (else standalone) ≤ 5 files.
- LEARNREPO: no.
- FILES_ALLOWED: `scripts/task_context_profiler.py`, `tests/test_task_context_profiler.py`,
  `evidence/context_cost_baseline.md`.
- TARGETED_TESTS: fixture repo with two modules and a test; asserts hop expansion and LOC sums; determinism.
- SUCCESS_CRITERIA: six rows, each with commit, files, source LOC, docs LOC, approx tokens; "governance LOC an
  agent following START_HERE reads" computed once and stated; runs offline; anti-dup clean.
- NEXT_UNLOCKED: FABLE-06, S-45.

## FABLE-06 — Review M1 maps
- LEVEL L1 · Fable reads the three evidence sets, confirms or amends the 8-module cut in `02` §3, writes
  `evidence/M1_GATE.md` (≤ 1 page). ACCEPTANCE: S-44 has an unambiguous file→module table to implement.

## S-44 — Module manifests + schema + coverage test
- MILESTONE M2 · LEVEL **L1** (metadata) · P3 · EXECUTOR claude-code · REVIEWER codex
- OBJECTIVE: `.lucy/architecture/module.schema.json` (fields: `module`, `purpose`, `public_api[]`,
  `owned_files[]` (globs allowed), `allowed_dependencies[]`, `forbidden_dependencies[]`, `state_touched[]`,
  `side_effects[]`, `tests[]`, `invariants[]`, `adrs[]`, `risk_level`, `protected_paths[]`), eight
  manifests per FABLE-06, `README.md` (one page), and `tests/test_module_manifests.py` asserting every
  tracked `.py` under `aion_core/`, `bridges/`, `scripts/`, `integrations/` is owned by exactly one manifest,
  all listed files exist, and `allowed_dependencies` ⊆ the S-41 graph's actual edges (no manifest may
  *permit* an edge that does not exist — keeps manifests honest).
- WHY: the missing contract layer (`02` §1).
- WORK_BRANCH research branch directly (metadata) **but** the test file goes via `task/S-44-module-manifests`
  PR → research branch, because `tests/` is code.
- CONTEXT_PACK: card + `evidence/complexity_map.json` + `skills/manifest.schema.json` (style precedent only)
  ≤ 4 files; local model may draft `purpose` lines from module docstrings, reviewed by the executor.
- LEARNREPO: no.
- FILES_ALLOWED: `.lucy/architecture/**`, `tests/test_module_manifests.py`.
- SUCCESS_CRITERIA: coverage 100%; each manifest ≤ 60 lines; test passes; a deliberately unowned fixture
  file makes the test fail (negative test).
- OWNER_APPROVAL: ratification of the cut at M2 exit (needed before S-45's `main` PR, not before starting it).
- NEXT_UNLOCKED: S-45, S-48.

## S-45 — Extend `aion context` (repo-aware, budgeted, watermark)
- MILESTONE M3 · LEVEL **L2** · P3 · EXECUTOR codex · REVIEWER claude-code · PR → **main** (owner merge)
- OBJECTIVE: `aion context <TASK_ID> [--module <name>] [--budget-bytes N] [--since <sha>] [--json]`
  per `09` §2; default output unchanged byte-for-byte (assert in test); reads manifests from
  `.lucy/architecture/modules/`; ports `context_pack.py`'s changed-files-since-watermark and sha listing;
  `security.redact` on everything; never inlines file contents beyond budget.
- WHY: the only missing piece between the kernel's work order and a bounded coding pack.
- WORK_BRANCH `task/S-45-context-module` from `origin/main`.
- CONTEXT_PACK: card + `aion_core/context.py` + `git show origin/feature/context-pack:aion_core/context_pack.py`
  + `aion_core/cli.py` lines for the `context` parser + `tests/test_context_contract.py` + one manifest ≤ 6 files.
- LEARNREPO: no (an internal port).
- ARCHITECTURE_AUDIT pre: checklist — extends an existing seam; no new store (no cache); no new `aion_core`
  module; `cli.py` and `context.py` unprotected. Post: full regression.
- FILES_ALLOWED: `aion_core/context.py`, `aion_core/cli.py` (the `context` subparser + dispatch lines only),
  `tests/test_context_contract.py`.
- TARGETED_TESTS: existing `test_context_contract.py` unchanged behaviour + new cases: `--module` adds the
  sections in order; budget truncation lists paths without content and says so; `--since` lists changed
  owned files; `--json` round-trips; redaction still applied.
- SUCCESS_CRITERIA: all above; `aion context TASK --module kernel.tasks` on a fresh home lists ≤ 10 files;
  strict/anti-dup clean (no protected path touched); suite count rises.
- ROLLBACK: revert the merge; default output was unchanged so callers are unaffected.
- NEXT_UNLOCKED: S-47, S-49, S-53.

## S-47 — Pilot A: salvage `aion verify` from `2cd3cc5` (pack-only execution)
- MILESTONE M3 · LEVEL **L2** · P3 · EXECUTOR codex · REVIEWER claude-code · PR → **main**
- OBJECTIVE: bring commit `2cd3cc5391a8b240baf018d8495b803356f78984` ("Add `aion verify`: one-command
  machine acceptance test") onto `main` as a task-scoped change, using **only** the S-45 pack for
  `interfaces`/`governance`; record every file the worker opened.
- WHY: (a) a real, wanted, bounded change; (b) it is one of the four commits the nodes run and `main` lacks
  (`11` §2), so landing it shrinks the divergence; (c) it becomes the operations-metrics source for `14` §D.
- START STATE: `git cherry-pick -n 2cd3cc5` on a fresh branch from `origin/main` — record conflicts; if the
  commit depends on `resource_governor` code absent from `main`, **stop**: the card becomes L3 under
  OWNER-06(b) and the pilot uses the fallback below.
- FALLBACK pilot task if stopped: `S-47b` — add `--json` output to `aion routing-report` (bounded,
  `reports.py`/`cli.py`, unprotected).
- FILES_ALLOWED: whatever the cherry-pick touches, minus protected paths; if it touches `cli.py` only for a
  subparser, allowed; if it touches `worker.py`/`health.py` protected semantics → stop.
- SUCCESS_CRITERIA: `./aion verify` exits 0 on a fresh home and non-zero when a required health check is
  forced to fail (test); suite count rises; pack metrics recorded (files listed/opened, LOC, attempts).
- NEXT_UNLOCKED: S-46.

## S-49 — Pilot B: salvage hermetic test environment from `10c8d79` (pack-only execution)
- MILESTONE M3 · LEVEL **L2** · P3 · EXECUTOR claude-code · REVIEWER codex · PR → **main** · PARALLEL with S-47
- OBJECTIVE: bring `10c8d79e12de5a519ae0d51ca9eeab89c557a5d1` ("Make the test suite hermetic: stop
  inheriting host environment") onto `main`: `tests/base.py` (and only tests) stop inheriting
  `AION_*`/`PATH`-dependent host state; every existing test still passes; CI unchanged.
- WHY: real, bounded, node-divergence-shrinking; directly improves M3/M4 measurement determinism.
- START STATE: `git cherry-pick -n 10c8d79`; conflicts in `tests/base.py` expected to be small; if the
  commit touches non-test files → stop and report.
- FILES_ALLOWED: `tests/**` only (the card's own exception to the `tests/base.py` default forbid).
- SUCCESS_CRITERIA: with `AION_HOME`, `AION_DB`, `AION_CCUSAGE_CMD`, `OLLAMA_HOST` deliberately set to junk
  in the environment, the full suite still passes; count ≥ 562; pack metrics recorded.
- NEXT_UNLOCKED: S-46.

## S-46 — Context pilot measurement + M3 gate report
- MILESTONE M3 · LEVEL **L1** · EXECUTOR controller · REVIEWER fable
- OBJECTIVE: `evidence/context_pilot_results.md` — for S-47 and S-49: files listed vs opened, source/docs
  LOC, tokens where reported, calls, attempts, first-try-green, rework, wall time, verifier verdict —
  against the S-43 baseline for their task types; plus the `02` §5 discriminating check (exclusion set size);
  `evidence/M3_GATE.md` with PASS/FAIL per target.
- SUCCESS_CRITERIA: both pilots landed (or one landed + fallback landed); targets evaluated with numbers;
  any "worker needed an excluded file" event listed with the manifest fix applied.
- NEXT_UNLOCKED: FABLE-07, FABLE-10 (partial).

## S-48 — `scripts/check_boundaries.py` (warning mode)
- MILESTONE M4 · LEVEL **L2** · P3 · EXECUTOR codex · REVIEWER claude-code · PARALLEL with M3 pilots
- OBJECTIVE: stdlib script reading `.lucy/architecture/modules/*.json`; whole-tree import scan; rules (a)
  only `aion_core/host/__init__.py` may import `host.linux`/`host.macos`; (b) any import edge not in the
  importing module's `allowed_dependencies` is a violation; (c) `import sqlite3` only in files listed in the
  baseline's `sqlite_connect_allowed` + `derived_sqlite_allowed`; `KNOWN_EXCEPTIONS = {path::rule: task}`
  exactly like `check_portability.py`; stale exception fails; exit 0 in warning mode, `--strict` flag for
  the future CI promotion; writes `evidence/boundary_report.md`.
- WHY: DEV plan Phase 5, one boundary, reversible, ratchet pattern already proven by C1.
- LEARNREPO: no — the pattern is in-repo.
- FILES_ALLOWED: `scripts/check_boundaries.py`, `tests/test_check_boundaries.py`, `evidence/boundary_report.md`.
- TARGETED_TESTS: mirror `tests/test_portability_guard.py` (both directions: violation found; exception
  honoured; stale exception fails; `--strict` non-zero).
- SUCCESS_CRITERIA: runs < 10 s; on `main` reports N violations each mapped to a task or an exception;
  5 consecutive daily runs with 0 false positives logged in the report before FABLE-07 may recommend
  promotion; **no CI workflow change in this task** (that is L4/owner).
- NEXT_UNLOCKED: FABLE-07, S-55.

---

Tasks 11+ (S-50…S-55, FABLE-07…09, OWNER-08/09, FABLE-10) are specified at card level in
`06_TASK_GRAPH.json` and `07_MILESTONE_GATES.md`; the controller writes their full cards into
`tasks/<ID>.md` when their prerequisites are DONE, using `08_TASK_CARD_TEMPLATE.md`, and Fable reviews any
card at L3+ before it becomes READY.
