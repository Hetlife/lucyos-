# TR-R-01 — Land the verified integration batch and get main CI green

**Why:** main CI has been red since 2026-11-07 (ISSUE-049) and TR-* overrides could not be matched (ISSUE-050), so no protected-path order can pass the gate. Three valuable branches are waiting behind that.
**Evidence:** `21_REALITY_AUDIT_20261114.md` §1–2; `evidence/baseline_20261114.json` (`tests_candidate`: all four branches merged together, 897 tests OK, all gates pass). Baseline `main` @ `316e33e`.
**Executor:** OWNER (merges); FABLE (review of #111). No model work.
**Allowed paths:** none edited by hand. **Forbidden:** force push, squash that drops the `Task-ID`/branch name, merging #109.
**Dependencies:** none.

## Steps (in this order)
1. Merge PR `fable/recovery-audit-20261114` with admin bypass. Its `authority-gate` fails by design: it changes `.github/workflows/lucyos-ci.yml` and `scripts/verify_authority.py`, which are constitutional.
2. Re-run CI on PR #115 (`task/TR-1-06-det-context-decoupling`). The gate reads the verifier from main, so it now reports `task_id: TR-1-06`. Merge when all required checks are green.
3. Merge the PR for `task/fix-codex-worker-portable-20261102` (one script, not protected) when green.
4. PR #111 (`task/TR-AGENT-HARNESS-20261016`): Fable reviews `aion_core/cli.py`, `context.py`, `packets.py` changes; update the branch from main; merge when green.
5. Close PR #109 with the comment "superseded by a6b9fd4 (TR-6-03)". Do not delete the branch here (TR-0-06 does that).

## Acceptance
- `gh api 'repos/Hetlife/lucyos-/actions/runs?branch=main&per_page=1' --jq '.workflow_runs[0].conclusion'` → `success`
- `python3 -m unittest discover -s tests -t . -q` on main → `OK`, 897 tests or more
- `python3 scripts/branch_ledger.py | grep -c -E 'TR-1-06|TR-AGENT-HARNESS|fix-codex-worker-portable'` rows are CONTAINED or PATCH_IN_BASE
- `python3 scripts/verify_authority.py strict --base origin/main --task-id TR-4-02` no longer says "undeclared"

**Rollback:** `git revert -m 1 <merge sha>` per merge; each is independent.
**Escalate to Fable if:** any required check other than `authority-gate` on step 1 fails, or step 2 still reports "undeclared".
**Then:** TR-0-03 re-freeze (drift 6 → 0), TR-7-01.
