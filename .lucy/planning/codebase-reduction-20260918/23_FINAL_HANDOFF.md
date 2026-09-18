# 23 — Final Handoff: the 25 questions (master prompt §26)

1. **Actual problem?** Not size — 20.6k py LOC, 67 modules. It is (a) ~15.6k lines of governance/planning/
   skills/docs text that agents are told to read first, (b) implicit module boundaries every agent
   re-derives, (c) concentration (`cli._main` 564 lines, `db` fan-in 43, `cli` fan-out 41), (d) two nodes
   running a branch `main` does not contain. (01, 02 §1)
2. **Perceived vs measured bloat?** Perceived: "150–200k LOC, hundreds of modules, tasks exceed 128k
   tokens". Measured: 8× smaller; the kernel fits one context window; the text corpus and node drift are
   the real costs. (01 §B)
3. **Stale assumptions?** The Executive Summary's estimates and "to be written" skills; the DEV plan's
   "Mark-2 remains canonical runtime" as a fact; "Lucy-architect-audit" as a runnable for arbitrary code;
   `CANONICAL_BRANCH.md`, `HIGH_MODEL_BASELINE.json.integration_branch`, the 2026-09-17 audits' open items
   (all resolved on `main`). (01 §A, §D, §E)
4. **Existing capabilities that solve it without new systems?** `tasks/approvals/resume/sessions` (state,
   checkpoint), `agents.route/escalate` + `governor` + `handoff` (routing), `aion context` (packet),
   `architecture.py` + `verify_authority.py` + `check_portability.py` + `aion scan` (gate), `packets`/
   `sync_outbox` (node boundary), `metrics.model_usage` (telemetry), skill manifests (extension seam),
   `feature/context-pack`'s watermark idea (salvage). (01 §D)
5. **Recommended near-term architecture?** Hybrid modular monolith: one repo/SQLite/timer; eight logical
   modules as manifests; boundary ratchet in warning mode → CI; `aion context --module` packs; manifests
   as extension seam; business/planning text excluded from default context. Weighted 4.55 vs B 3.50 vs
   C 1.95. (02)
6. **Undecided?** Node checkout policy (OWNER-06); branch protection (OWNER-07); ratification of the module
   cut (M2); boundary-gate promotion (M4); archive list (M5); each M6 move; topology (M7). (02 §4, 04 §5)
7. **Authority structure?** OWNER → FABLE → CONTROLLER → WORKERS → VERIFIER, with the architect-audit as a
   gate (tools + high-model checklist) between every change and every merge; levels L0–L5 mapped to the
   baseline, approvals, task states and C5 bands. (04)
8. **What may ChatGPT do autonomously?** L0/L1 directly; dispatch/verify/merge L2 into the research branch;
   open PRs to `main`; checkpoint; escalate. (04 §4, 17)
9. **What must Fable review?** L3 plans, gate reports (FABLE-06/07/08/09), third-attempt failures,
   contradicted assumptions, any baseline/protected-path proposal. (04 §4, 05 §4)
10. **What requires owner approval?** The matrix in 04 §5: node policy, protection, ratification, `main`
    merges, CI promotion, archive list, M6 moves, topology, deletions, deploy/credentials/spend (never by this
    program).
11. **Codex does:** L2 implementation on Lucy-den (S-41, S-43, S-45, S-47, S-48, S-52, S-53) with the
    `aion_codex_worker.sh` sandbox semantics; verification of Claude-authored changes. (09 §1, 18)
12. **Claude Code does:** L2 implementation (S-42, S-44's test, S-49, S-50, S-55), independent
    verification of Codex-authored changes, `code-review`/`smallest-fix`/`learnrepo` skills. (18 §19)
13. **Local models do:** classify/summarise/cluster/draft inside a worker's task (manifest `purpose` drafts,
    duplicate-doc clustering, log labels); reviewed before commit; no decisions. (09 §1, 18 §20)
14. **Independent verification enforced how?** Card fields EXECUTOR ≠ INDEPENDENT_REVIEWER; verifier prompt
    re-runs gates and reads tests; PR body must link the verifier report; controller merges only PASS;
    CI from a fresh checkout; author cannot approve. (04 §1, 05 §2, 18 §21)
15. **First 10 tasks?** S-40, OWNER-06, S-41, S-42, S-43, FABLE-06, S-44, S-45, S-47, S-49 (with S-46 and
    S-48 immediately after). (16)
16. **Parallel?** S-41 ∥ S-42 ∥ S-43; S-47 ∥ S-49 ∥ S-48; S-50 ∥ S-52; S-53/S-55 ∥ S-54; owner decisions
    never block L0–L2. (06 `parallel_groups`)
17. **Milestone gates?** M0 lock → M1 maps → M2 contracts (owner ratifies) → M3 context pilot → M4 boundary
    pilot (owner promotes) → M5 cleanup → M6 decomposition → M7 topology → M8 operationalise → M9 value
    mode with six numeric entry criteria. (07)
18. **Avoid infinite rework?** 3 attempts, root-cause note before #2, class change before #3,
    `BLOCKED_TECHNICAL` + evidence packet + Fable after; assumption contradiction replans only the
    subtree. Same numbers as the kernel (`MAX_TASK_RETRIES=3`, `_fail` at 2). (05 §4)
19. **Resume after crash/reset?** `CHECKPOINT.md` top block → `06_TASK_GRAPH.json` → open PRs →
    `git status`; task branches are the state; research branch merges `main`, never rebases; no chat
    memory. (05 §5–6, 17 §6)
20. **Keep context bounded?** Standard packet (SHA, card, `aion context --module` ≤10 files/200 KiB, last
    diff, commands); exclusions for planning/archive/directives/internal docs; constraints carried as card
    fields not corpus reads; S-43 baseline and per-task metrics. (09)
21. **Stop bloat returning?** Warning-first budgets (function 120, file 700, fan-out 20, no new cycles,
    duplicate bodies, stale docs, manifest coverage test, anti-dup on new modules) promoted only after
    measured false-positive rates. (09 §6)
22. **ChatGPT executes first:** S-40 M0 canonical baseline lock, then dispatches S-41/S-42/S-43. (16, 17 §3)
23. **ChatGPT must NOT:** merge to `main`, deploy, touch nodes, delete branches, add dependencies, build a
    loader/cache/second queue, refactor `cli.py` before M6 evidence, merge `feature/context-pack` wholesale,
    let a worker self-verify, cite stale estimates, continue past M9 uncapped. (17 §5)
24. **Evidence the program works?** `14`: pack ≤10 files and ≤25% baseline volume on ≥4/6 task types;
    first-try-green ≥80%; `.lucy`+`docs` LOC −25%; 0 new cycles; `cli` fan-out <20 after move #1; CI green;
    nodes on a contract-named SHA; ≤3 owner-waiting PRs; 0 `BLOCKED_TECHNICAL` >7 d.
25. **When to stop optimising?** At M9 entry (all six criteria measured): cap architecture work at 20% of
    iterations, return capacity to the owner's value backlog; re-enter repair only on CI red >1 day, a
    boundary regression, a >25% context-cost regression, or owner instruction. (07 M9, 05 §8)

## Exact first task for ChatGPT

`S-40 — M0 canonical baseline lock` (L1). Acceptance in `16_FIRST_10_TASKS.md#S-40` and `17` §3. It needs no
owner decision, no code, no worker; it produces the file every later measurement is relative to and
raises the two owner questions that gate deployment-related milestones only.

## What this Fable pass did and did not do

Did: read all four inputs; reconciled against live `main`, CI, PRs, 49 branches, a sandboxed `./aion` run,
and the owner's Drive baseline; corrected the hierarchy where evidence required; produced the package.
Did not: change code, touch nodes, merge anything, decide owner questions, or upload secrets. The package
is committed on `claude/lucyos-health-audit-sonnet-repair-gfzowc` (based on `main` @ `66e3a4e`) and mirrored
to Drive; the controller's first `SYNC` should create `research/codebase-reduction-20260918` from `origin/main`
and copy this folder there (or the owner merges this branch — either is L1).
