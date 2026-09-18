# M0 Canonical Baseline — S-40

Measured 2026-09-18 on canonical `origin/main` and live connected nodes. Commands are recorded with each number.

## Canonical source and CI
- `origin/main`: `66e3a4ef1b8242123555af5a7c9d80115ab23d82` (`git rev-parse origin/main`).
- Latest `LucyOS CI` run for this SHA: `35279040189`, conclusion `success` (GitHub Actions API, `head_sha=66e3a4e...`).
- Fable planning branch: `claude/lucyos-health-audit-sonnet-repair-gfzowc` @ `332d3a77c9d74ed60681654ce3c7dd56ca440857`; planning commit `332d3a7` is the branch tip.
- Planning-package discrepancy: the start prompt names `21_VERIFIER_PROMPT.txt`; the live branch has verifier §21 inside `18_WORKER_AND_VERIFIER_PROMPTS.md` and no standalone `21_VERIFIER_PROMPT.txt`.

## Canonical-main repository counts
Detached worktree of `origin/main`:
- tracked files: **386** — `git ls-files | wc -l`
- Python files: **132** — `git ls-files '*.py' | wc -l`
- Markdown files: **79** — `git ls-files '*.md' | wc -l`
- JSON files: **119** — `git ls-files '*.json' | wc -l`
- Python LOC: **20,612** — `git ls-files '*.py' | xargs wc -l | tail -1`
- Markdown LOC: **9,503** — `git ls-files '*.md' | xargs wc -l | tail -1`
- JSON LOC: **5,470** — `git ls-files '*.json' | xargs wc -l | tail -1`
- test files under `tests/`: **58** — `find tests -maxdepth 1 -type f | wc -l`

The prior “87 Markdown/docs files” used a broader docs/text count. For this program the canonical file-count command is `git ls-files '*.md' | wc -l`, therefore **79 tracked Markdown files**.

## Test and safety baseline
- Full suite: PASS on canonical main; wall **57.56 s** — `/usr/bin/time -f 'WALL=%e' python3 -m unittest discover -s tests -t . -q`. Existing environment emitted missing WhatsApp-variable notices but suite completed successfully.
- Secret scan: clean — `./aion scan .`.
- Portability: 0 violations, 3 known exceptions, 0 stale — `python3 scripts/check_portability.py`.
- Strict dry-run on temporary `task/S-40-baseline` with empty `Task-ID: S-40` commit: `ok: true`, `changed: 0`, no protected paths; branch deleted after run.
- Anti-dup dry-run: `ok: true`, zero violations.

## Live node reality
Drive baseline source: `01_CURRENT_STATE_BASELINE`, 2026-09-18.

Drive facts copied verbatim:
- “Lucy-den working checkout is currently on feature/resource-governor at 2cd3cc5391a8b240baf018d8495b803356f78984, while origin/main is 66e3a4e.”
- “Mark-2 working checkout is also on feature/resource-governor at 2cd3cc5; origin/main is 66e3a4e.”
- “AION health reports healthy.”
- “Canonical state database integrity: OK.”
- “Tasks: 0 ready, 0 running, 4 blocked/waiting, 13 done.”
- “Unresolved errors: 0.”
- “Ollama: 3 local models detected.”
- “Git working tree: clean on feature/resource-governor.”

Live verification this session confirms both connected nodes are still on `feature/resource-governor` @ `2cd3cc5391a8b240baf018d8495b803356f78984`; both see `origin/main` @ `66e3a4e`. Mark-2 is an active DigitalOcean droplet in `blr1`, size `s-2vcpu-4gb`; no runtime/state mutation was performed.

## Remote branches
Command: `git branch -r` plus `git rev-list --left-right --count origin/main...<ref>` and `git merge-base --is-ancestor <ref> origin/main`.
63 non-main remote branches were measured. Full inventory is appended below from `/tmp/s40_branches.tsv`; `contained` means the branch tip is reachable from `main`; `unique` means it has commits not contained in main.

## Open pull requests
GitHub open-state search on 2026-09-18 returned 16 open PRs: #41, #34, #33, #30, #29, #27, #24, #11, #10, #9, #8, #7, #6, #5, #4, #2. Their base/head/state were read from the GitHub API and are part of this S-40 evidence set.

## Owner decisions raised
**OWNER-06 — node checkout policy.** Canonical main is `66e3a4e`; both Lucy-den and Mark-2 live checkouts remain `2cd3cc5`, 136 commits behind and 4 ahead. Mark-2 remains the canonical runtime/state/scheduling authority, but this program will not touch either live checkout. Owner decision is either (a) later name a canonical-main successor as the deployment-contract SHA, or (b) explicitly keep `2cd3cc5` and fast-track the Fable-governed salvage work. This does not block M1–M5.

**OWNER-07 — main branch protection.** Live GitHub branch metadata reports `protected: false` and protection `enabled: false` for `main` at `66e3a4e`. The controller therefore continues to treat main as owner-only and will never push/merge to main. Enabling branch protection is an owner action and does not block M1–M5.

## Remote branch inventory


origin/arch/lucyos-interface-m-a	behind=138	ahead=0	contained
origin/audit/health-20260917	behind=51	ahead=0	contained
origin/backup/pre-mark2-loop-v1.2-20260908	behind=162	ahead=0	contained
origin/candidate/deployment-preflight-rendered-units-20260918	behind=0	ahead=1	unique
origin/candidate/dev-msos-20260917	behind=5	ahead=0	contained
origin/candidate/dev-msos-governed-20260918	behind=0	ahead=0	contained
origin/candidate/learnrepo-sse-study-20260918	behind=0	ahead=1	unique
origin/candidate/mark2-loop-v1.2-20260908	behind=162	ahead=1	unique
origin/candidate/scs-admin01-handoff-20260918	behind=0	ahead=1	unique
origin/claude/aion-whatsapp-control-1seild	behind=167	ahead=28	unique
origin/claude/fable-deploy-setup-mc5nr6	behind=167	ahead=32	unique
origin/claude/lucyos-architecture-audit-4o4q83	behind=125	ahead=0	contained
origin/claude/lucyos-health-audit-sonnet-repair-gfzowc	behind=0	ahead=4	unique
origin/feature/context-pack	behind=125	ahead=2	unique
origin/feature/learnrepo-queue-health	behind=135	ahead=0	contained
origin/feature/lucyos-aion-handoff	behind=173	ahead=1	unique
origin/feature/openclaw-lucyos-bridge	behind=125	ahead=0	contained
origin/feature/resource-governor	behind=136	ahead=4	unique
origin/feature/skill-system-q000-architecture-audit	behind=134	ahead=0	contained
origin/feature/skill-system-q001-capability-registry	behind=133	ahead=0	contained
origin/feature/skill-system-q002-manifest-schema	behind=132	ahead=0	contained
origin/feature/skill-system-q003-catalog-lifecycle	behind=131	ahead=0	contained
origin/feature/skill-system-q004-learnrepo-contract	behind=130	ahead=0	contained
origin/feature/skill-system-q005-policy-classes	behind=129	ahead=0	contained
origin/feature/skill-system-q006-architecture-guard	behind=128	ahead=0	contained
origin/integration/consolidation-20260916	behind=52	ahead=2	unique
origin/merge/reconcile-waves-20260917-chatgpt	behind=5	ahead=0	contained
origin/owner/dev-msos-governance-20260918	behind=30	ahead=0	contained
origin/owner/start-here-model-router-20260917	behind=98	ahead=0	contained
origin/owner/wave0-authority-reconcile-20260917	behind=96	ahead=0	contained
origin/owner/wave0-portability-refinement-20260917	behind=100	ahead=0	contained
origin/plan/lucyos-openclaw-e2e	behind=125	ahead=1	unique
origin/planning/integration-roadmap-20260917	behind=95	ahead=0	contained
origin/planning/opus-fable-20260916	behind=101	ahead=0	contained
origin/post-integration/S-30-result-contract	behind=32	ahead=0	contained
origin/repair/reconcile-20260917	behind=30	ahead=0	contained
origin/repair/resource-governor-hermetic-openclaw-20260917	behind=136	ahead=4	unique
origin/setup/ci-integration-sync-20260916	behind=114	ahead=0	contained
origin/supervised/integration-20260917	behind=33	ahead=0	contained
origin/task/S-01-skill-registry-normalize	behind=100	ahead=0	contained
origin/task/S-02-salvage-audit-branch	behind=87	ahead=0	contained
origin/task/S-05-launchd-units	behind=100	ahead=0	contained
origin/task/S-07-drive-check	behind=100	ahead=0	contained
origin/task/S-08-secret-scanner-kwarg	behind=100	ahead=0	contained
origin/task/S-09-openclaw-check	behind=100	ahead=0	contained
origin/task/S-10-host-adapter	behind=100	ahead=0	contained
origin/task/S-13-sync-outbox	behind=100	ahead=0	contained
origin/task/S-14-intake	behind=100	ahead=0	contained
origin/task/S-15-openclaw-independence	behind=100	ahead=0	contained
origin/task/S-16-tempworker-guardrails	behind=100	ahead=0	contained
origin/task/S-17-guardian-skeleton	behind=100	ahead=0	contained
origin/task/S-18-recovery-injection	behind=100	ahead=0	contained
origin/task/S-19-macos-read-safe	behind=100	ahead=0	contained
origin/task/S-20-protected-paths-render	behind=100	ahead=0	contained
origin/task/S-21-history-scan	behind=100	ahead=0	contained
origin/task/S-22-remove-desktop-commander	behind=100	ahead=0	contained
origin/task/S-23-portability-export	behind=100	ahead=0	contained
origin/task/S-24-encrypted-backup	behind=100	ahead=0	contained
origin/task/S-26-audit-chain	behind=100	ahead=0	contained
origin/task/S-27-routing-report	behind=100	ahead=0	contained
origin/task/S-28-runtime-inventory	behind=99	ahead=0	contained
origin/task/S-29-salvage-experiments	behind=100	ahead=0	contained
origin/test/authority-gate-positive-20260916	behind=117	ahead=1	unique
