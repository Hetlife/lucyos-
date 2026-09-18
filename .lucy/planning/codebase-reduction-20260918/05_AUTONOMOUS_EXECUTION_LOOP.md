# 05/13 — Autonomous Execution Loop, Failure/Rework, Checkpoint/Recovery, Rollback

## 1. Where state lives (no new store)

| State | Canonical location | Why here |
|---|---|---|
| Dev task graph (statuses, deps, levels) | `.lucy/planning/codebase-reduction-20260918/06_TASK_GRAPH.json` on `research/codebase-reduction-20260918` | Same precedent as `SONNET_TASK_QUEUE.md` ("canonical queue — there is no other"); version-controlled, diffable, survives every reset |
| Per-task execution evidence | the task PR body + commit trailers (`Task-ID: S-4N`) | Reviewable, immutable, what the verifier reads |
| Controller checkpoint | `CHECKPOINT.md` in the same folder (one compact block per event, newest first) | Restart surface for a fresh session |
| Measurements | `evidence/` in the same folder | Owner-readable, Drive-mirrored |
| Runtime task queue | Mark-2 AION SQLite | **unchanged and untouched** by this program |
| Optional local telemetry | a throwaway `AION_HOME` on Lucy-den (`aion session start/log/end`, `aion checkpoint`) | Convenience only; declared non-canonical; never synced to Mark-2 |

The controller therefore needs no scheduler: `TASK_GRAPH.json` + `git` + GitHub PRs are the queue.

## 2. The loop (one iteration = one task)

```
SYNC            git fetch --prune; confirm origin/main SHA; confirm research branch fast-forwards from main
HEALTH CHECK    CI on origin/main green? open PRs from this program? any BLOCKED_* older than 24h?
LOAD STATE      read CHECKPOINT.md (top block) → TASK_GRAPH.json → open PR list
SELECT          highest-priority task with status READY, all `depends_on` DONE, level ≤ what the current
                approvals allow (04 §5), not owned by an in-flight PR
EVIDENCE PACK   build with existing tools only: git diff/log, `aion context` (S-45 onward), module manifest,
                related tests, task card; respect the pack budget (09 §3)
CLASSIFY        confirm the card's AUTHORITY_LEVEL against the files it will touch (04 §2); if higher → escalate
SKILLS          invoke `smallest-fix` before code; `/learnrepo` only if the card says LEARNREPO_NEEDED=yes
AUDIT (pre)     04 §3 pre-code gate; record result in the card
DISPATCH        L0/L1: controller does it; L2+: assign to Codex or Claude Code per 09 §1, on branch
                task/<ID>-<slug> from origin/main (code) or research branch (docs)
EXECUTE         worker returns the 7-field packet; controller never edits the worker's diff
TARGETED TEST   card's TARGETED_TESTS + `python3 -m compileall -q aion_core bridges tests scripts`
INDEPENDENT     the other worker (or Fable for L3) reviews the diff against the card; writes VERIFIER report
REGRESSION      full suite; `./aion scan .`; `check_portability.py`; anti-dup; strict; (boundaries, from S-48)
METRICS         before/after per 14 (files read, LOC read, tokens where recorded, calls, retries, durations)
CHECKPOINT      append block to CHECKPOINT.md; set status in TASK_GRAPH.json; commit both on research branch
PROMOTE         L1: done. L2 → research: controller merges. L2/L3 → main: PR waits for owner; controller
                moves on. Milestone exit criteria met → write the gate report, request the owner decision.
CONTINUE        next SELECT. If nothing is READY: write a BLOCKED summary to CHECKPOINT.md and stop.
```

Never skip a state. A state with nothing to do is recorded as "n/a: <reason>" in the checkpoint block.

## 3. Task states — master-prompt vocabulary mapped to `tasks.STATES`

| Graph status | Meaning | `tasks.py` equivalent (if mirrored) |
|---|---|---|
| `NEW` | card exists, prerequisites unmet | `INBOX` |
| `READY_FOR_EVIDENCE` | prerequisites met, pack not built | `TRIAGE` |
| `PLANNED` | pack built, level classified | `READY` |
| `AUDIT_REQUIRED` | waiting on pre-code gate / high-model checklist | `READY` + `blockers="audit"` |
| `READY_TO_EXECUTE` | gate passed | `READY` |
| `EXECUTING` | worker owns it | `CLAIMED`/`RUNNING` |
| `VERIFYING` | independent review + regression running | `NEEDS_REVIEW` |
| `PASS` | verified; awaiting promotion | `NEEDS_REVIEW` |
| `REWORK` | failed verification; attempt counter +1 | `READY` (`retry_count`+1) |
| `BLOCKED_OWNER` | needs an owner decision (04 §5) | `NEEDS_APPROVAL` |
| `BLOCKED_TECHNICAL` | 3 failed attempts or missing dependency | `BLOCKED` |
| `CHECKPOINTED` | evidence + checkpoint committed | — |
| `MERGE_CANDIDATE` | PR open against `main`, owner to merge | `NEEDS_APPROVAL` |
| `DONE` | merged where the card says; metrics recorded | `DONE` (evidence required) |

`06_TASK_GRAPH.json` uses only these strings.

## 4. Failure / rework loop (no infinite loops)

Attempt counting follows the kernel: `config.MAX_TASK_RETRIES = 3`; `worker._fail` escalates at
`retry_count >= 2`; `agents.escalate` moves exactly one rung.

- **Attempt 1** — normal execution by the assigned worker.
- **Attempt 2** — *only after a root-cause note*: the verifier's report must name what was wrong. The pack is
  expanded (more neighbours/tests), same worker class.
- **Attempt 3** — alternate implementation **or** the other worker class **or** one rung up
  (B→C: Claude/Opus-class review before the third try). Same prompt re-sent is not an attempt.
- **After 3 materially failed attempts** → `BLOCKED_TECHNICAL`; write an evidence packet (card, three diffs
  or their PR links, three verifier reports, exact failing commands/output) into `evidence/blocked/<ID>.md`;
  escalate to Fable in `CHECKPOINT.md`; select the next READY task.
- A failure that contradicts an assumption of the plan (e.g. "context.py cannot know the repo root on
  Mark-2") → mark the assumption in `01` as CONTRADICTED, set every dependent task to `NEW`, keep completed
  unaffected work, replan only that subtree (Fable), record the replan in `CHECKPOINT.md`.
- A failing test is a defect in the change until proven otherwise; never skipped, disabled or quarantined.
- "Flake" is not a root cause. One re-run is allowed only if the job died before any test body ran or the
  same commit passed earlier.

## 5. Checkpoint format (append to top of `CHECKPOINT.md`)

```
## <UTC timestamp> · <TASK_ID> · <status>
- canonical_main: <sha>   research_branch: <sha>   task_branch: <name>@<sha or ->   pr: <url or ->
- evidence: <paths / PR comment links>
- tests: <targeted: n pass> <full: n pass, k skipped, t s>  gates: strict=<ok|fail> anti-dup=<ok|fail> portability=<ok|fail> scan=<clean|found> boundaries=<n/a|ok|warn>
- audit: pre=<PASS|NEEDS_REVIEW|BLOCK> post=<...>  verifier: <who> <PASS|REWORK> <report path>
- files_changed: <list>
- metrics: <before → after per 14, or n/a>
- risk: <unresolved risk or none>
- rollback: <git revert <sha> | delete branch | n/a>
- next_unlocked: <task ids now READY>
```

Also run, when a local `AION_HOME` exists on the node: `./aion checkpoint --current-task <ID>
--last-verified-success "<one line>" --next-action "<next task>" --files-to-read "<pack paths>"`. Optional.

## 6. Recovery procedures

| Event | Recovery |
|---|---|
| ChatGPT session reset | New session runs `17_CHATGPT_MASTER_EXECUTION_PROMPT.txt` §0: read `CHECKPOINT.md` top block → `TASK_GRAPH.json` → `git status`/open PRs on the research branch. If a task was `EXECUTING`, check its branch for uncommitted or unpushed work; if a worker packet exists in the PR, resume at VERIFYING; otherwise restart the attempt (counter unchanged if no diff was produced). |
| Codex / Claude session loss mid-task | The task branch is the state. `git status` on the node worktree; commit WIP with `Task-ID` trailer and `WIP:` prefix; re-dispatch with the card + the WIP diff as evidence. |
| Lucy-den reboot | Nothing canonical lives there. Re-clone or `git fetch`; detached worktree of `origin/main` for measurement; task branches recover from origin. Local `AION_HOME` is disposable. |
| Mark-2 restart | Out of this program's scope: `aion boot` (resume.py) handles it; timers restart per systemd. The program never writes Mark-2 state. |
| Network failure | Work continues on local branches; no PR/merge/checkpoint claims until pushed. A checkpoint block is written only after `git push` succeeds. |
| Research branch diverged from `origin/main` (owner pushed to main) | `git merge origin/main` into the research branch (never rebase shared history); re-run gates; re-verify any PASS task whose files changed. |
| Baseline / verifier changed on `main` | Re-run strict + anti-dup on every open task branch before further merges; record in checkpoint. |

## 7. Rollback rules

- **Every L2 change is one revertible unit**: one task = one branch = one PR = `git revert -m 1 <merge>` on
  the research branch, or close the PR if unmerged.
- **L3 changes** carry a rollback tag created *before* merge: `git tag pre/<TASK_ID> origin/main` (the
  controller may create tags on the research branch; tags on `main` are owner actions).
- **Metadata (manifests, boundary rules)** roll back with the same revert; `check_boundaries.py` warning
  mode guarantees a wrong rule cannot break CI before it is promoted.
- **Data**: this program creates no schema changes in M0–M5. If M6 ever does, it follows the existing rule
  (additive migration + `tests/test_migrations.py` upgrade test) and the deployment contract's backup step.
- **Nodes**: unchanged by this program until OWNER-06 names a SHA; then the deployment contract's §7 applies.

## 8. Priorities inside SELECT

`P0` repo/canonical correctness blocker (e.g. `main` CI red, verifier drift) → `P1` security/reliability/
governance → `P2` capability unlock (a blocked task's prerequisite) → `P3` codebase-reduction milestone task
→ `P4` efficiency → `P5` cleanup. After M9's entry criteria are met, P4/P5 may consume at most 20% of
controller iterations; the remainder goes to value tasks from the Mark-2 queue (`aion tasks` on the canonical
node, via the owner) or the owner's project backlog.
