# Final Verification Plan — 2026-09-17

Run **after** TASK-001 through TASK-004 and **before** `FINAL_SONNET_PUSH_TASK.md`.
Every step states what PASS looks like. A step without a stated PASS condition is not a check.

## Baselines this plan asserts against

Measured in the audit session on the real merged commit. Any downward movement is a failure,
not a rounding difference.

| Metric | Expected |
|---|---|
| Full suite | **≥ 550 tests, OK, 1 skipped** |
| Portability guard | 0 violations, 3 known exceptions, **0 stale**, portable |
| Secret scan | clean |
| Merge conflicts | zero |
| `anti-dup` | clean, or only owner-ratified violations |

---

## 1. Diff review

```
git status --short
git log --oneline origin/main..HEAD
git diff origin/main...HEAD --stat
```
**PASS:** every commit maps to TASK-001, TASK-002, TASK-003 or the TASK-004 merge. No
unexplained file. No formatting churn. No unrequested refactor. No temporary or generated
file staged (no `.aion_home*`, no `__pycache__`, no `*.pyc`, no scratch directory).

## 2. Compile and import integrity

```
python3 -m compileall -q aion_core bridges tests scripts
python3 -c "import aion_core.worker, aion_core.db, aion_core.resume, aion_core.model_gateway, aion_core.semantic_recall, aion_core.platform_resolver, aion_core.usage_telemetry"
```
**PASS:** silent compile; all imports succeed with no circular-import error.

## 3. Targeted tests for the merged-in modules

```
python3 -m unittest tests.test_model_gateway tests.test_platform_resolver tests.test_semantic_recall tests.test_usage_telemetry tests.test_task_data_class -v
```
**PASS:** all OK. These are the modules the merge carries; they are the ones most likely to
break on contact with `main`.

## 4. Full suite

```
python3 -m unittest discover -s tests -t . -q
```
**PASS:** ≥ 550 tests, OK. A count **below** 550 means the merge dropped tests and is a
stop condition, not a curiosity.

## 5. CI-equivalent gates

```
./aion scan .
python3 scripts/check_portability.py
python3 scripts/verify_authority.py anti-dup --base origin/main
python3 scripts/verify_authority.py strict --base origin/main --branch "$(git branch --show-current)"
```
**PASS:** scan clean. Portability portable, **0 stale** (a stale exception means someone
fixed a bug without removing its excuse, and the ratchet must be allowed to tighten).
`anti-dup` clean or only owner-ratified. `strict` ok, or a single unambiguous task identity
if protected paths were touched.

## 6. Startup, persistence and recovery on a throwaway brain

```
export AION_HOME=$(mktemp -d)
./aion init && ./aion seed && ./aion boot
./aion health --deep
./aion backup
```
**PASS:** `init`/`seed`/`boot` all succeed. Required health checks pass. `backup` creates
**and restore-verifies** an archive; a backup that is not restore-tested is not a backup.

## 7. Save / resume

```
./aion boot     # second time, fresh process
```
**PASS:** reports the previously recorded next action rather than re-running it. An
interrupted external action must not be duplicated.

## 8. Authority gates still enforced

```
python3 -c "
import json;b=json.load(open('.lucy/authority/HIGH_MODEL_BASELINE.json'))
assert '.lucy/authority/**' in b['constitutional_paths_no_override_possible']
assert 'scripts/verify_authority.py' in b['constitutional_paths_no_override_possible']
assert '.github/workflows/lucyos-ci.yml' in b['constitutional_paths_no_override_possible']
print('constitutional paths intact')"
```
**PASS:** prints the confirmation. This is the check that catches a gate being quietly
loosened while everything else looks green.

## 9. Model routing and delegation unchanged

```
grep -n "run_cloud\|cloud_command\|_execution_lock\|needs_review" aion_core/worker.py | head
```
**PASS:** the DET → Ollama → `cloud_command` hierarchy is present and unmodified;
`_execution_lock` still exists; `_validate` still returns `needs_review` for class A/B work
lacking independent validation. `model_gateway` must appear only as an auxiliary call, never
as a replacement for `run_cloud`.

## 10. Secret hygiene

```
./aion scan .
git diff origin/main...HEAD | grep -iE "api[_-]?key|secret|token|password|bearer" || echo "no credential-shaped additions"
```
**PASS:** scan clean and the diff grep returns nothing beyond variable *names* already
present in the codebase. Never print an actual value while checking.

## 11. Remote state unchanged since the audit

```
git fetch origin --prune
git rev-parse origin/main origin/integration/consolidation-20260916
```
**PASS:** `0720a92...` and `db91548...` respectively. **If either moved, STOP.** The audit
evidence, including the conflict-free merge proof, no longer applies and needs a fresh
high-model pass.

---

## Final health statement

Only after every PASS above may anyone describe the repository as healthy. Record the actual
numbers observed, not the expected ones. If a step was skipped, say it was skipped; a
skipped check reported as passing is the single most damaging thing this plan can produce.
