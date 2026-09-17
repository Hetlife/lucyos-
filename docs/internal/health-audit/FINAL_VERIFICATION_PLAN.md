# Final Verification Plan — 2026-09-17

Run this after TASK-R1 (and TASK-R3 if desired) are complete and before
FINAL-SONNET-PUSH is allowed to commit/push anything. Per auditor spec §12.
Every step must be run for real; do not report a step as passed without
having executed it in this session's environment.

1. **Inspect every task diff.** `git diff origin/main...<repair-branch>` —
   confirm it is exactly: (a) TASK-R1's 4-line allowlist addition, (b) the
   full content of waves 1–5 already proven on `merge/reconcile-waves-20260917-chatgpt`
   (`git diff origin/main origin/merge/reconcile-waves-20260917-chatgpt --stat`
   as the reference shape), and (c) nothing else. Any extra file is a scope
   violation — stop.
2. **Targeted tests.** For TASK-R1: none needed (data-only change; validate
   JSON parses). For the promoted waves: `test_model_gateway.py`,
   `test_platform_resolver.py`, `test_semantic_recall.py`,
   `test_usage_telemetry.py`, `test_sse_events.py`, `test_task_data_class.py`,
   `test_context_contract.py`, `test_openclaw_lucyos_bridge.py` all pass
   individually.
3. **Full suite.** `python3 -m unittest discover -s tests -t . -q` — expect
   560 tests, 0 failures, 0 errors, ≤2 skipped (the `ssh-keygen`-absence
   skips are environment-only and expected in a sandbox without
   `ssh-keygen`; confirm the skip reason names `ssh-keygen`, not something
   else, if the skip count changes).
4. **CI-equivalent checks.**
   ```
   python3 -m compileall -q aion_core bridges tests scripts
   ./aion scan .
   python3 scripts/check_portability.py
   python3 scripts/verify_authority.py anti-dup --base origin/main
   python3 scripts/verify_authority.py strict  --base origin/main --branch <repair-branch-or-sha>
   ```
   Expected after TASK-R1 lands but before TASK-C1 is decided:
   `anti-dup` → exactly 4 violations remaining (ERROR-2/semantic_recall
   only — the allowlist 4 are gone). If `anti-dup` still shows 8, TASK-R1
   did not actually land on the branch being verified; stop.
   `strict` → must carry a real `Task-ID` (from the commit trailer this push
   task itself creates, see `FINAL_SONNET_PUSH_TASK.md`) — 0 violations.
5. **Test startup.** `python3 -m aion_core.cli --help` (or the repo's
   documented startup smoke-test command) runs without a traceback.
6. **Save/resume.** Run whatever test(s) in `tests/` cover
   `aion_core/resume.py` checkpoint/resume explicitly (already included in
   the full suite run in step 3 — confirm by name, don't just trust the
   aggregate count).
7. **Authority gates.** Confirm step 4's `anti-dup`/`strict` runs above were
   not run with any flag that suppresses or ignores violations, and that
   `.lucy/authority/**` and `.github/workflows/lucyos-ci.yml` are byte-identical
   to `origin/main` in the diff from step 1 (constitutional paths — should
   never appear as "changed" in this push's diff at all, since TASK-R1 only
   touches the allowlist *data* inside `HIGH_MODEL_BASELINE.json`, which is
   explicitly the one field designed to be updated this way).
8. **Failure/retry/recovery paths.** Confirm `tests/test_*` covering worker
   retries/timeouts/cancellation (already part of the 560) pass individually,
   not just in aggregate.
9. **`git status`.** Clean, no untracked files left behind by the test run
   (watch for stray `.lucy/planning/skill-exec-*` scratch files or SQLite
   files created by `semantic_recall.py` during the test run — these must
   not be staged).
10. **Secret scan.** `./aion scan .` (already step 4) plus a manual look at
    the diff for anything resembling a token/key/credential.
11. **Confirm no unrelated changes.** Diff touches only files named in
    TASK-R1 and the wave-1-through-5 content already reviewed by the prior
    audits; nothing outside that set.
12. **Verify remote push SHA** (post-push, see `FINAL_SONNET_PUSH_TASK.md`):
    `git ls-remote origin <branch>` matches the locally reported pushed SHA.
13. **Produce final health status.** A short PASS/FAIL note per criterion
    above, written to
    `docs/internal/health-audit/tasks/FINAL_VERIFICATION_RESULT.md`, dated
    and SHA-stamped. Do not declare the repo healthy on any criterion that
    was not actually executed.

**Owner/Level-D gate:** even with all 13 steps green, actually merging or
pushing onto `main` still requires the Level D owner approval named in
`FINAL_SONNET_PUSH_TASK.md` and `SONNET_REPAIR_APPROVAL_BOUNDARIES_TEMP.md`.
A fully green verification plan authorizes *readiness*, not the push itself.
