# FINAL-SONNET-PUSH — Verify, Commit, and Push Repaired LucyOS State

**Priority:** P1 · **Depends on:** TASK-001, TASK-002, TASK-003, TASK-004, and a fully
passing `FINAL_VERIFICATION_PLAN.md`.

This is a **verification-first** task. The push is the last two lines of it. If you reach
for `git push` before every acceptance criterion below has actually been observed in this
session, you have done the task wrong even if the push succeeds.

---

## Target

- **Push to:** `repair/reconcile-20260917`
- **Do NOT push to:** `main`, `integration/consolidation-20260916`, or any `task/*` branch.
- The owner merges into `main`. You never do.

---

## Pre-push acceptance criteria

All sixteen must be observed in this session. Not remembered, not assumed, not inherited
from an earlier message.

1. **Confirm the branch.** `git branch --show-current` is `repair/reconcile-20260917`.
2. **Fetch.** `git fetch origin --prune`.
3. **Verify ancestry.** `git merge-base --is-ancestor origin/main HEAD` succeeds, so the
   branch genuinely builds on `main`.
4. **Confirm no unexpected divergence.** `git rev-parse origin/main` is still `0720a92...`
   and `git rev-parse origin/integration/consolidation-20260916` is still `db91548...`.
   **If either moved, STOP and escalate.** Do not reconcile a moved remote yourself.
5. **Inspect `git status --short`.** Clean, or only files you intend to commit.
6. **Inspect the full diff.** `git diff origin/main...HEAD` read end to end, not skimmed.
7. **Every hunk maps to an approved task.** TASK-001 docs, TASK-002 four allowlist strings,
   the TASK-003 ruling, and the TASK-004 merge. Anything else does not belong.
8. **No secrets added.** `./aion scan .` clean, and the diff contains no credential-shaped
   value. Never print a real value while checking.
9. **Targeted tests pass.** The five modules listed in the verification plan, step 3.
10. **Full suite passes.** `python3 -m unittest discover -s tests -t . -q`,
    **≥ 550 tests, OK**. Below 550 is a stop condition.
11. **CI-equivalent checks pass.** `check_portability.py` portable with **0 stale**;
    `verify_authority.py anti-dup` and `strict` both acceptable.
12. **Authority gates still enabled.** Verification plan step 8 prints its confirmation.
13. **Save/resume and core runtime healthy.** Verification plan steps 6 and 7.
14. **No unresolved conflicts.** `git status --short | grep -E '^(UU|AA|DU|UD)'` returns
    nothing.
15. **No stray files staged.** No `__pycache__`, no `*.pyc`, no `.aion_home*`, no scratch
    directory, no editor backup.
16. **No unrelated formatting churn.** `git diff origin/main...HEAD --stat` shows only files
    the approved tasks were allowed to touch.

---

## Commit

One commit per task where they are not already committed, or a single reconciliation commit
if TASK-004's merge already carries them. Message must state what was reconciled and cite
this audit. Include the standard attribution trailers. Do not amend anything already pushed.

---

## Push

```
git push -u origin repair/reconcile-20260917
```

Nothing else. No `--force`. No `--force-with-lease`. No `--no-verify`.

---

## Forbidden, without exception

- force-push, or rewriting any shared history
- pushing to `main` or to `integration/consolidation-20260916`
- bypassing branch protection
- disabling, skipping or quarantining any test or CI job
- `--no-verify` to get past a failing hook: fix the hook's complaint instead
- merging your own work into a protected branch
- proceeding after the remote HEAD changed
- guessing through a merge conflict that the audit said would not exist

If the remote HEAD moves at any point during execution: **stop immediately and escalate for
high-model reconciliation.** Do not re-plan the merge yourself.

---

## Report after pushing

State all of the following, with real values observed, not expected values copied from this
document:

- branch pushed
- previous remote SHA
- new remote SHA
- commit SHA(s) created
- files changed, by count and by name
- tests executed and the actual result line
- gate results: scan, portability, anti-dup, strict
- CI/check status if any is available yet
- remaining warnings, including anything the owner ratified in TASK-003 that still shows as
  an `anti-dup` violation

If any check was skipped, say it was skipped. A skipped check reported as a pass is worse
than a failed push.

---

## After the push

The high-reasoning agent independently verifies the pushed SHA and diff before the repair
wave is declared complete. Sonnet does not declare it complete, and does not open a pull
request into `main` unless the owner asks for one.
