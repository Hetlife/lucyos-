# Sonnet execution plan — fix red main, finish merges, close out branches
Author: Opus planning pass, 2026-09-25. Executor: Sonnet (Claude Code on Lucy-den).
Read this whole file once, then work phase by phase. Stop at every **OWNER** step.

## 0. Ground truth at hand-off (re-verify before acting)
- `origin/main` = `760973e` (PR #71 SEVAA merge). Merged since `64e221b`: PRs #64–#71
  (S-44, S-45, cerebras-e0, mac-resolver, S-48, taskcheck-owner-value, reference docs, SEVAA).
- **main is RED**: `code-and-test` fails on py3.9/3.11/3.13. `macos-readiness` is also red but is
  advisory by design — ignore it.
- **Root cause (reproduced locally):** `tests/test_module_manifests.py` fails with
  `Expected exactly one owner: aion_core/sevaa.py` (2 failures). S-44's manifest test requires every
  `aion_core` file to have exactly one owner. SEVAA branched before S-44 merged, so `sevaa.py` has no owner, and the
  S-41 evidence (`dependency_graph.json`) has no edges for `sevaa`. Neither branch is wrong on its own.
  They only fail together, because of the order they were merged in.
- Re-verify: `git fetch origin && git log --oneline -3 origin/main` and
  `curl -s https://api.github.com/repos/Hetlife/lucyos-/commits/<sha>/check-runs` (anonymous read works;
  `gh` is NOT authenticated on this box).

## Operating rules (apply to every phase)
1. Never push to `main`, never self-merge, never force-push. Push a branch and give the owner the
   `https://github.com/Hetlife/lucyos-/pull/new/<branch>` link. (Direct pushes to main are blocked by the
   Claude Code classifier by design — do not route around it.)
2. Never edit protected paths (`.lucy/authority/**`, `.lucy/deployment/**`, `.github/workflows/lucyos-ci.yml`,
   `aion_core/{worker,router,resume,db,config,security,approvals,governor,architecture,agents}.py`,
   `scripts/verify_authority.py`, `scripts/check_portability.py`, …). Check with
   `python3 scripts/verify_authority.py strict --base origin/main --branch <b>` → `protected_touched: []`.
3. Gates per branch, on the final committed SHA: targeted tests → full suite → `./aion scan .` →
   `python3 scripts/check_portability.py` → `git diff --check origin/main...HEAD` → authority strict + anti-dup.
4. Full suite takes ~4 min. Run it detached and poll without sleep chains:
   `nohup python3 -m unittest discover -s tests -t . -q > /tmp/<name>.log 2>&1 & disown; P=$!` then
   `while ps -p $P >/dev/null; do sleep 5; done; grep -n '^Ran\|^OK\|^FAILED' /tmp/<name>.log`.
   (Do not wrap `&` inside a `run_in_background` call — the notification fires early.)
5. **New merge rule (this incident):** before the owner merges any PR, rebase-check it against the *current*
   `origin/main` (`git merge-tree --write-tree origin/main origin/<b>`) and re-run
   `tests.test_module_manifests` on the merge result. Any PR adding an `aion_core/*.py` or `scripts/*.py`
   file must also add it to a module manifest in `.lucy/architecture/modules/*.json`.
6. After every owner merge: re-check CI on the new main SHA via the API. The three `code-and-test` jobs must be
   `success` before the next merge.
7. Work in isolated worktrees under `~/lucyos-worktrees/`. Never touch the base checkout at
   `~/GitHub/Hetlife/lucyos-` (dirty, preserved owner work on `feature/little-lucy-nebula-prep-20260920`).

## Phase 1 — Make main green (do first, nothing else until done)
Branch: `task/fix-sevaa-manifest-ownership-20260925` from `origin/main`.
1. `.lucy/architecture/modules/business.json`: add `"aion_core/sevaa.py"` to `owned_files` and
   `"tests/test_sevaa.py"` to `tests`. (Business owns money_path/experiments/owner_setup; SEVAA revenue fits there.
   `sevaa.py` imports only `config`, `db` (and lazily `metrics`) → `kernel.state` + `governance`, both already in
   business's `allowed_dependencies`.)
2. Regenerate S-41 evidence against current main:
   `python3 scripts/complexity_map.py --out .lucy/planning/codebase-reduction-20260918/evidence`
   (default `--root .`; do NOT pass `--root aion_core`, and `--out` is a directory).
   Expect exactly 3 changed files: `complexity_map.json`, `dependency_graph.json`, `hotspots.md`.
3. `python3 -m unittest tests.test_module_manifests tests.test_sevaa -v` → all pass (6 + 18).
4. Full gates (rule 3). Commit `fix: give sevaa.py a module owner and refresh S-41 evidence` with
   `Task-ID: FIX-SEVAA-MANIFEST`. Push. Hand the owner the PR link.
5. **OWNER** merges. Then verify CI on the new main SHA (rule 6). Done when all three `code-and-test` are green.

## Phase 2 — Owner-only authority items (Sonnet prepares; owner executes)
2a. **M-CONTEXT-02** (`task/M-CONTEXT-02-worker-integration-20260925`, owner's own ratified commits):
   - Branched from `64e221b`; main has moved 8+ merges. Dry-run: `git merge-tree --write-tree origin/main
     origin/task/M-CONTEXT-02-worker-integration-20260925` → report conflicts, if any.
   - In a scratch worktree at the merge result: run `tests.test_context_compiler`,
     `tests.test_context_worker_integration`, `tests.test_module_manifests` (new file
     `aion_core/recall/context_compiler.py` is owned by `memory` via `aion_core/recall/**/*.py` — confirm), and the full suite.
     If it no longer applies cleanly, rebuild the branch by cherry-picking the same 5 commits
     (`15bb92b 91eb819 1281f3e 3bf08ea 3b10118`) onto current main into a new `-rebased` branch. Keep the
     authorship unchanged and don't edit their content.
   - Authority strict will ALWAYS fail on this branch (it carries the FABLE-10 override for `worker.py` and edits the
     constitutional baseline). That is by design. **OWNER** opens the PR and merges it directly.
2b. **SEVAA allowlist** — `aion_core_modules` in `.lucy/authority/HIGH_MODEL_BASELINE.json` lacks `"sevaa"`.
   `sevaa.py` is already on main, so this is baseline bookkeeping: future anti-dup diffs won't flag it, but the
   baseline should reflect reality. Both 2a and 2b edit the baseline. **OWNER** should merge 2a first, then add `sevaa`
   (or do both in one owner commit). Sonnet prepares nothing in that file.
2c. Still owner-only, unchanged: A-103 passphrase (`./aion secrets set BACKUP_PASSPHRASE`, real terminal, never chat),
   authority re-freeze at a chosen SHA (`deploy_readiness.ready` is still false on the 4 pre-existing drifted files),
   naming the Mark-2 DC-1 deploy SHA, A-104 (owner deferred until the Mac is set up).

## Phase 3 — Record-keeping
- Push the local, unpushed commit `46c80fd` (Opus consolidation plan) and this file on
  `docs/opus-planning-brief-20260924`; push/refresh `docs/progress-postmerge-20260924` so `PROGRESS.md` reflects
  merges #64–#71. Owner merges docs.
- AION: once M-CONTEXT-02 is on main, its DONE records (`TASK-M-CONTEXT-01/02`) become true. If the owner declines 2a,
  correct those two records via `./aion task-update` with the reason. Record the red-main incident as a lesson:
  `./aion error-add` then `./aion error-resolve` with root cause = merge-order manifest coverage, fix = Phase 1,
  lesson = rule 5.

## Phase 4 — Remaining branch investigations (one at a time, verdict each)
For each branch: isolate its own commits (`git log origin/main..origin/<b>` and `git show --stat <sha>`, not the
branch-vs-main diff, which is misleading because the branches are stale). Then check whether the content is
already on main (`git cat-file -e origin/main:<path>`, grep the function names). Check it for protected paths,
third-party imports, and manifest ownership. Give the owner a verdict: MERGE / SUPERSEDED / HOLD.
1. `feature/context-pack` — `aion_core/context_pack.py`. Check overlap with S-45's `./aion context --module/--budget-bytes`
   (possible duplicate). If unique: stdlib? a manifest owner (memory)? then salvage the module + test only.
2. `feature/lucy-taskcheck-20260922` — isolate `460e64c` (TaskCheck completion via OpenClaw) and `c15379f`
   (shareable completion report). Grep main for their functions. If missing and they don't touch protected
   `router.py`, cherry-pick them onto a fresh branch. Ignore the ~15 unrelated checkpoint commits.
3. `feature/taskcheck-mvp-20260922` — confirm it's superseded by main's `taskcheck.py` (compare its commits' patch-ids).
4. `task/prompt-work-order-20260924` (open PR #62) and `review/code-review-20260924` — trace what they are and
   whether AION's DONE "Prompt Work-Order lifecycle" tasks match their code.
5. `claude/fable-deploy-setup-mc5nr6` remainder — SEVAA WhatsApp approval commands and the phone interface. The
   source `router.py` predates `owner_actions`. `router.py` is protected, so this is HOLD and needs an owner override;
   write a scoped proposal, don't port it.
6. `feature/resource-governor` — build the evidence package for the owner: the smallest per-file override needed
   (`resume.py`, `router.py`, `worker.py`), the invariants touched, the rollback, and the test results on a rebased
   scratch branch. Don't merge.
7. LucyNest/SCG cluster (7 branches) — waiting on the owner's answer to the comment in the "Branch Reconciliation
   Audit" doc. Do nothing until then.
8. `candidate/deployment-preflight-rendered-units-20260918` — HOLD (touches the protected deploy contract; only
   relevant once DC-1 is named).

## Phase 5 — PR and branch hygiene (owner executes deletions)
- 22 open PRs exist. Several (#4–#10 skill-system, #24/#27/#29/#30/#33/#34 S-tasks, #50/#51/#52/#56 superseded
  originals, #2 whatsapp-control, #11 authority-probe) have their content already on main or are superseded.
  For each: check `base.ref` and whether the head is an ancestor of main. Then give the owner a close-list with a
  one-line evidence note per PR. The owner closes them (or authenticates `gh` via `gh auth login --web` and
  approves a scripted close).
- Branch deletion: use the 70-branch safe list from the audit doc, plus the head branches of merged PRs #64–#71.
  Keep the audit-trail branches (R-04..R-07, review/*, docs/*) as ARCHIVE. Bulk delete is blocked by the classifier
  for Sonnet, so the owner runs it.

## Done criteria
Main green on all three `code-and-test` jobs. M-CONTEXT-02 decided and on main (or its records corrected). Every
remaining branch has a written verdict. Open PRs are reduced to genuinely active work. Every step's evidence
(SHA, commands, exit codes) is recorded in the PR body or `PROGRESS.md`.
