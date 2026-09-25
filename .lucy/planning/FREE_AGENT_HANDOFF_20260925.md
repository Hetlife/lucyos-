# Free-Agent Handoff — LucyOS (2026-09-25)

Written by Opus 5.5 so cheaper or free agents (Gemini CLI, OpenRouter free models,
local Ollama, OpenClaw `main`) can keep going while the Claude and ChatGPT quotas reset.
**Read this whole file before doing anything.** When it conflicts with a newer
plan, `SONNET_FIX_DEBUG_MERGE_PLAN_20260925.md` wins for merge order and this
file wins for which agent does what.

## 0. Ground truth at hand-off

| Item | Value |
|---|---|
| Repo | `Hetlife/lucyos-` · local clone `~/GitHub/Hetlife/lucyos-` (DIRTY: do not touch) |
| Worktrees | `~/lucyos-worktrees/<name>` (one per task) |
| Runtime | `AION_HOME=/home/scs-admin01/openclaw/shared_brain`, `./aion status` |
| main | `46ed8c1` (PR #72), CI green on push |
| Open PR #73 | M-CONTEXT-02 worker integration, head `7a1ac8a`, owner-approved (D3) |
| New fix branch | `fix/context-shallow-origin-main-20260925` @ `e058d14` (no PR yet) |

### Why PR #73 (and every PR since #65) showed red
GitHub `pull_request` checkouts are depth-1 and **do not fetch `origin/main`**.
`aion_core/context.py` ran `git rev-parse origin/main` and raised, so
`tests/test_context_contract.py` failed with 3 errors and 1 failure. Push runs passed, which is why
main looked green. Reproduced locally with `git clone --depth 1`. The code in
#73 is fine.
Fix `e058d14`: report `origin/main` as unavailable when it is missing, plus a
regression test. Evidence: the new test fails without the fix; with the fix, 745 of 745 tests pass
in a depth-1 clone; `verify_authority strict` and `anti-dup` pass; the secret scan is clean.

## 1. Owner clicks, next in order

1. Open the PR: https://github.com/Hetlife/lucyos-/pull/new/fix/context-shallow-origin-main-20260925
   and wait for `code-and-test` to go green on the PR itself. That green run is the proof.
2. Merge it.
3. On PR #73, click **Update branch** (brings the fix in). Wait for green `code-and-test`.
   `authority-gate` stays red by design (FABLE-10 constitutional change), so the owner merges directly.
4. Merge #73.

Nothing below needs a paid model until these four are done.

## 2. Non-negotiable rules for every agent

- Never push to `main`, force-push, or merge a PR. Only the owner merges.
- Never edit protected paths. Check with
  `python3 scripts/verify_authority.py strict --base origin/main --branch <b>`
  (it must print `"ok": true`). `.github/workflows/*`, `aion_core/resume.py`,
  `router.py`, and `.lucy/authority/*` are protected.
- Never delete branches. The owner deletes them after reading a verdict.
- Never put secrets in chat, git, or logs. The owner types `A-103` in their own terminal:
  `./aion secrets set BACKUP_PASSPHRASE`.
- One task means one worktree off `origin/main`, one branch, and one PR.
- Before you push, run the CI steps yourself **in a depth-1 clone** (this is the lesson from #73):
  ```bash
  git clone -q --depth 1 --branch <b> file://$PWD /tmp/ci && cd /tmp/ci
  python3 -m compileall -q aion_core bridges tests scripts
  python3 scripts/check_portability.py
  AION_HOME=/tmp/h1 ./aion scan .
  AION_HOME=/tmp/h2 python3 -m unittest discover -s tests -t . -q   # must say OK
  ```
- Every new `aion_core/*.py` needs an owner in `.lucy/architecture/modules/*.json`,
  and the S-41 evidence must be regenerated:
  `python3 scripts/complexity_map.py --out .lucy/planning/codebase-reduction-20260918/evidence`
  (this is the lesson from #71 and #72).
- If you fail twice in materially different ways, stop and write a BLOCKER note. Don't loop.
- Report with the seven fields: STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS / BLOCKERS / NEXT_ACTION.

## 3. Which agent gets which work

| Tier | Agent | Allowed work |
|---|---|---|
| Free or local | Gemini CLI free, OpenRouter `:free`, Ollama `qwen3.5:4b`, OpenClaw `main` on a free model | Read-only audits, running tests, and branch verdict tables. Also docs/PROGRESS updates, SEVAA outreach drafts (the owner sends them), and `./aion status`/`health` reports. |
| Cheap paid | DeepSeek, Gemini Flash, or Claude Haiku API | Small bug fixes with tests in non-protected files, and rebases with no conflicts. |
| Premium | Claude Sonnet/Opus (subscription) or GPT (Codex) | Architecture, conflict resolution, anything near protected or authority files, and final review before the owner merges. |

A free agent must hand a task up a tier when a diff touches more than 3 files, any
`aion_core/` file that another module imports widely (`db.py`, `tasks.py`,
`worker.py`, `cli.py`), or anything that `verify_authority` flags.

## 4. Task queue for free agents (safe, in priority order)

| # | Task | Done when |
|---|---|---|
| F1 | Watch PR #73 and the fix PR. Post their check status to WhatsApp once an hour (anonymous API: `curl -s https://api.github.com/repos/Hetlife/lucyos-/commits/<sha>/check-runs`). | The owner has been told each result |
| F2 | Phase 4 branch verdicts: for each branch in `.lucy/planning/BRANCH_LIST_TIER_A_20260925.txt`, run `git cherry -v origin/main origin/<b>` and write MERGED / SUPERSEDED / HAS-UNIQUE-WORK into `.lucy/planning/BRANCH_VERDICTS_20260925.md`. Don't delete anything. | A table with evidence for every branch |
| F3 | SEVAA EXP-001 prep: draft 30 short WhatsApp messages for the ₹2,499 Design Clarity Call from `PROJECTS/sevaa-sales-os/experiments/EXP-001-paid-design-consult/`. The owner reviews and sends them. | Drafts are saved and the owner has been notified |
| F4 | Daily `./aion status` + `./aion health` summary sent to WhatsApp | Runs once a day |
| F5 | Update `.lucy/planning/OPUS_PROGRESS.md` with the merges #63–#72 plus this hand-off | PR opened |

Escalate these to a premium model, and don't let a free agent do them: `feature/resource-governor`
(3 unratified protected files), the LucyNest/SCG cluster, deployment-preflight,
context-pack, `router.py`, the authority re-freeze, DC-1, and A-104 (wait for the Mac).

## 5. Owner-only items still open
A-103 passphrase · SEVAA allowlist 2b · Razorpay "Design Clarity Call" link
(₹2,499) + 5 unknowns in EXP-001 · merge #73 and the fix PR · branch deletions.

## 6. Files to read first
1. This file
2. `.lucy/planning/SONNET_FIX_DEBUG_MERGE_PLAN_20260925.md`
3. `.lucy/planning/LUCYOS_OPUS_CONSOLIDATION_PLAN_20260924.md`
4. The audit: https://claude.ai/code/artifact/1e74526e-4b7f-4768-87a1-c18218824097
