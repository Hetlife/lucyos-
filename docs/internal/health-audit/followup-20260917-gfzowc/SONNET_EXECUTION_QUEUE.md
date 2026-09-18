# Sonnet Repair Execution Queue — 2026-09-17

Format and approval-level rules per `docs/internal/SONNET_REPAIR_APPROVAL_BOUNDARIES_TEMP.md`.
Order per the auditor spec §7 (repo/branch/commit reconciliation before
functional work). Only two repair tasks are needed — the repo is
substantively healthy; see `HEALTH_REPORT.md` for why this queue is short on
purpose ("do not manufacture work").

**Repo-only constraint applies to every task below**: Sonnet has access only
to this Git repository and GitHub-visible state. No task in this queue
requires local-machine, OpenClaw-host, or other out-of-repo evidence. None
are BLOCKED for that reason.

---

## TASK-R1 — Promote the already-fixed authority allowlist onto `main`

**Priority:** P1
**Subsystem:** `.lucy/authority`
**Confidence:** 95%
**Depends on:** NONE

**Approval level: A**
**Repo-only: YES**
**Base branch/ref:** `origin/main`
**Expected base SHA:** `0720a9209923bde9652833c4c7a9271041daa855`
**Why this level applies:** Root cause fully verified (ISSUE-1); fix already
exists, committed, and independently confirmed correct (`57f0e4c` on
`repair/reconcile-20260917` — diff is exactly 4 allowlist string additions to
`aion_core_modules` in `.lucy/authority/HIGH_MODEL_BASELINE.json`, nothing
else). Purely additive to an allowlist, reversible, no protected-path
*behavior* change (only a data entry), no interface change, no new
dependency, no schema change, tests already exist for all 4 modules on
`audit/health-20260917`/reconcile-wave.
**Evidence available in repo:** `docs/internal/health-audit/ISSUE_REGISTER.md`
ISSUE-1; `docs/internal/health-audit/COMMIT_AND_PUSH_RECONCILIATION.md` §2;
commit `57f0e4c` itself (`git show 57f0e4c`).

### Problem
`main`'s `.lucy/authority/HIGH_MODEL_BASELINE.json` does not list
`model_gateway`, `platform_resolver`, `semantic_recall`, `usage_telemetry` in
`aion_core_modules`, so any branch introducing those modules (all of which
are already fully implemented and tested elsewhere in this repo) fails
`verify_authority.py anti-dup`.

### Root cause
Baseline was never updated when commit `60b2dc7` added the four modules on
`integration/consolidation-20260916`; that branch diverged from `main`
before the modules or a baseline update could land there.

### Objective
`aion_core_modules` in `.lucy/authority/HIGH_MODEL_BASELINE.json` on the
target repair branch contains exactly the same 4 additional entries as
commit `57f0e4c` adds, and nothing else in that file changes.

### Allowed files
`.lucy/authority/HIGH_MODEL_BASELINE.json` — and *only* the `aion_core_modules`
array within it.

### Do not change
Any other key in `HIGH_MODEL_BASELINE.json` (in particular
`sqlite_connect_allowed` — that is ISSUE-2/TASK-C1, a separate, higher-level
decision; do not fold it into this task). Do not touch
`.lucy/authority/PROTECTED_PATHS.md` or `LUCYOS_PLATFORM_AND_DATA_CONTRACTS.md`.

### Implementation instructions
1. Create branch `task/R1-allowlist-owner-modules` from `origin/main` at `0720a92`.
2. Apply exactly the diff in commit `57f0e4c` (`git show 57f0e4c -- .lucy/authority/HIGH_MODEL_BASELINE.json | git apply`, or hand-edit to match it verbatim) to `.lucy/authority/HIGH_MODEL_BASELINE.json`.
3. Commit with trailer `Task-ID: R1`.
4. Do not touch any other file.

### Required tests
No new tests required — this task adds a registry entry, it does not add
behavior. Confirm the JSON parses (`python3 -c "import json; json.load(open('.lucy/authority/HIGH_MODEL_BASELINE.json'))"`).

### Verification commands
```
python3 -c "import json; json.load(open('.lucy/authority/HIGH_MODEL_BASELINE.json'))"
git diff origin/main -- .lucy/authority/HIGH_MODEL_BASELINE.json
```
Confirm the diff output matches `git show 57f0e4c -- .lucy/authority/HIGH_MODEL_BASELINE.json` exactly.

### Completion criteria
Diff is byte-for-byte the same allowlist addition as `57f0e4c`; no other
file changed; JSON is valid.

### Rollback
`git revert <commit>` on the repair branch; nothing downstream depends on
this yet since it hasn't reached `main`.

### Stop and escalate if
The diff needed is not a pure allowlist-array addition (e.g. if `main`'s
`HIGH_MODEL_BASELINE.json` has itself changed shape since this audit and a
naive apply doesn't cleanly match) — then this is no longer a mechanical
task and must go to Level B for Opus review.

**Allowed autonomous actions:** create the repair branch, make the one-file
edit, commit, run the two verification commands above.
**Actions requiring Opus review:** none for this task in isolation.
**Actions requiring owner approval:** merging/pushing to `main` — that is
covered by FINAL-SONNET-PUSH, not by this task card.
**Stop conditions:** as above.

---

## TASK-C1 — Rule on `semantic_recall.py`'s second SQLite store

**Priority:** P2
**Subsystem:** `aion_core/semantic_recall.py`, `.lucy/authority`
**Confidence:** n/a (decision task, not implementation)
**Depends on:** NONE

**Approval level: C — Sonnet must NOT modify code until Opus/high-reasoning review explicitly approves the approach**
**Repo-only: YES**
**Base branch/ref:** `origin/main` (or the reconcile-wave branch, once R1/R2 land)
**Expected base SHA:** `0720a9209923bde9652833c4c7a9271041daa855`
**Why this level applies:** Per `SONNET_REPAIR_APPROVAL_BOUNDARIES_TEMP.md`
Level C triggers directly: this touches persistence-schema/canonical-state
boundaries (`aion_core/db.py` is the named owner of "every table, every
migration"), and it requires **deciding which of several competing
resolutions is canonical** — exactly the "requires deciding which competing
implementation should become canonical" and "changes persistence schema...
or data-loss behavior" triggers. Sonnet must not pick between the three
options below.
**Evidence available in repo:** ISSUE-2; `.lucy/authority/PROTECTED_PATHS.md`
(`aion_core/db.py` protected-path entry); `.lucy/authority/LUCYOS_PLATFORM_AND_DATA_CONTRACTS.md`
(C1–C10, needs re-reading by the reviewer to check whether a "rebuildable
derived cache" carve-out already exists or must be added);
`aion_core/semantic_recall.py` itself (the 2 `sqlite3.connect()` + 2
`CREATE TABLE` call sites, findable via `verify_authority.py anti-dup`'s
output).

### Problem
`aion_core/semantic_recall.py` maintains its own SQLite connection and
schema (a `sqlite-vec` + `fastembed` derived vector index) outside the
canonical store owned by `aion_core/db.py`.

### Root cause
The module was written and merged (`60b2dc7`, owner-authored) before/without
a recorded ruling on whether a derived, rebuildable index is allowed to
bypass `db.py`.

### Objective
A recorded decision (in `.lucy/authority/LUCYOS_PLATFORM_AND_DATA_CONTRACTS.md`
or an equivalent authority doc) on exactly one of:
- **(a)** allowlist `aion_core/semantic_recall.py` in `sqlite_connect_allowed`
  *and* record in the data contract that it is a rebuildable derived index,
  never a source of truth;
- **(b)** teach `scripts/verify_authority.py` to recognize a declared-derived
  marker in code (more work, prevents recurrence for future modules);
- **(c)** move the index outside `aion_core` entirely.

### Allowed files
None for Sonnet at this stage — this task produces a written recommendation
only, for Opus/owner sign-off. Once a decision is made, a follow-up Level A
or B task implements it with `.lucy/authority/HIGH_MODEL_BASELINE.json`
(`sqlite_connect_allowed`) and/or `LUCYOS_PLATFORM_AND_DATA_CONTRACTS.md` and/or
`aion_core/semantic_recall.py` as the allowed files, scoped by the decision.

### Do not change
`aion_core/db.py`, `.lucy/authority/**`, `aion_core/semantic_recall.py` —
not until the decision above is made and recorded.

### Implementation instructions
1. Do not write code. Produce a short decision memo under
   `docs/internal/health-audit/tasks/ISSUE-2-semantic-recall-decision.md`
   summarizing the three options above with their tradeoffs (already listed
   in ISSUE_REGISTER.md / HEALTH_REPORT.md §4) for Opus/owner to pick from.
2. Stop. Wait for the decision to be recorded.

### Required tests
None until a decision authorizes an implementation task.

### Verification commands
None (decision task).

### Completion criteria
A decision is recorded by an authorized reviewer; this task then closes and
a new Level A/B task is opened to implement it.

### Rollback
N/A — no code changes made by this task.

### Stop and escalate if
Always — this entire task is a stop-and-escalate by definition.

**Allowed autonomous actions:** write the decision memo summarizing options;
nothing else.
**Actions requiring Opus review:** the entire resolution choice.
**Actions requiring owner approval:** if the chosen option (a) or (c) is
judged to touch data-loss/backup semantics materially, per
`SONNET_REPAIR_APPROVAL_BOUNDARIES_TEMP.md` Level C/D boundaries — Opus
determines this at review time.
**Stop conditions:** any attempt to implement before the decision is
recorded.

---

## TASK-R3 — Recheck the `feature/lucyos-aion-handoff` "empty diff" claim

**Priority:** P4
**Subsystem:** branch hygiene / audit-trail correctness
**Confidence:** n/a (evidence task)
**Depends on:** NONE

**Approval level: A**
**Repo-only: YES**
**Base branch/ref:** `origin/main`
**Expected base SHA:** `0720a9209923bde9652833c4c7a9271041daa855`
**Why this level applies:** Read-only investigation, no code or config
changes, fully reversible (it produces a doc, nothing else), no protected
path touched.
**Evidence available in repo:** ISSUE-5; `git diff`/`git merge-base` output
already captured in HEALTH_REPORT.md §5.

### Problem
A prior audit doc claims `feature/lucyos-aion-handoff` has an empty diff
against `main` and can be deleted as a no-op merge. This session's spot
check found its tip commit is not a literal ancestor of `main` and a full
`git diff` shows hundreds of files of difference — consistent with `main`
having grown since the claim was made, but not confirmed either way.

### Root cause
Unknown yet — this is exactly what the task is for.

### Objective
Determine definitively whether `feature/lucyos-aion-handoff`'s content is
fully subsumed by `main` (safe to delete once other branch-cleanup
prerequisites in `REPO_CLEANUP_AND_MERGE_PLAN.md` are met) or carries real
unique content that needs its own reconciliation entry.

### Allowed files
`docs/internal/health-audit/tasks/ISSUE-5-aion-handoff-recheck.md` (new file,
write findings there). No other files.

### Do not change
Nothing in `aion_core`, `bridges`, `scripts`, `.lucy/**`, or any branch ref.
Do not delete the branch — that is an owner action per
`PROTECTED_PATHS.md`/prior plan §5 regardless of this task's findings.

### Implementation instructions
1. `git log --oneline origin/main..origin/feature/lucyos-aion-handoff` and `git log --oneline origin/feature/lucyos-aion-handoff..origin/main`.
2. For each file in `git diff origin/feature/lucyos-aion-handoff origin/main --stat`, classify: present-and-identical-on-main-under-different-path, present-and-different, or absent-from-main.
3. Write the findings memo with a clear verdict: SUBSUMED / UNIQUE-CONTENT-FOUND / INCONCLUSIVE.

### Required tests
None.

### Verification commands
The two `git log` commands above; re-run and confirm output matches the memo.

### Completion criteria
Memo exists with one of the three verdicts and supporting evidence.

### Rollback
Delete the memo file; no other state changed.

### Stop and escalate if
Any unique, non-trivial content is found on the branch that is not on
`main` — escalate to Opus for a reconciliation decision rather than
recommending deletion.

**Allowed autonomous actions:** all of the above (read-only investigation +
one new doc file).
**Actions requiring Opus review:** none unless UNIQUE-CONTENT-FOUND.
**Actions requiring owner approval:** actually deleting the branch, always
(per `PROTECTED_PATHS.md` "owner_only_actions includes delete branches or
tags") — out of scope for this task regardless of verdict.
**Stop conditions:** as above.

---

## Explicitly not queued this pass

- **`feature/resource-governor` (wave 6)** — real merge conflicts in
  protected files (`aion_core/cli.py`, `db.py`, `health.py`). Per the prior
  plan this must be done "last, alone, with a human watching," which is
  Level C/D territory by definition (protected paths + non-trivial conflict
  resolution). Not given a task card because it cannot be executed
  autonomously at any level — it needs a human-supervised session, not a
  queued Sonnet task.
- **ISSUE-7 side branches** (`claude/aion-whatsapp-control-1seild`,
  `claude/fable-deploy-setup-mc5nr6`, `feature/context-pack`,
  `plan/lucyos-openclaw-e2e`, `test/authority-gate-positive-20260916`,
  `candidate/mark2-loop-v1.2-20260908`) — not on the critical path, not
  requested by the owner, and auditing each in depth would be manufacturing
  work the auditor spec explicitly says not to do ("If a subsystem is
  already healthy, say so ... do not manufacture work"). Left recorded in
  `HEALTH_REPORT.md` §5 for whenever the owner wants them triaged.

## Execution order

1. TASK-R1 (Level A, autonomous)
2. TASK-R3 (Level A, autonomous, independent of R1 — may run in parallel)
3. TASK-C1 (Level C, stop for decision) — blocks nothing else in this queue,
   but blocks a fully-clean `anti-dup` on the eventual `main` push (ERROR-2
   will still show as a known, documented exception until decided)
4. FINAL-SONNET-PUSH (see `FINAL_SONNET_PUSH_TASK.md`) — depends on R1 being
   merged onto the repair/promotion branch; does not require C1 to be
   resolved first, but the push report must explicitly carry ERROR-2 forward
   as a known, owner-acknowledged item rather than silently drop it.
