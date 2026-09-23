# Merge Protocol — Repair Mission

## Roles
Sonnet: implement, debug, test, commit, push, open PR, return evidence.
Controller: independently verify PR head, CI/gates, mergeability, and scope; merge only after all required checks pass.
Owner/high-model: resolve protected authority/re-freeze decisions.

## Merge eligibility
A non-protected repair PR is merge-eligible only when:
1. branch is based/rebased on current `origin/main`;
2. diff is limited to task scope;
3. focused tests pass;
4. full unit suite passes;
5. `./aion scan .` passes;
6. `python3 scripts/check_portability.py` passes;
7. `git diff --check` passes;
8. authority strict/anti-dup checks pass or the only failure is a documented pre-existing canonical authority-drift condition unrelated to the PR;
9. no unresolved new AION error or stale claim remains;
10. rollback is straightforward.

## Protected changes
If a fix truly requires a protected file:
- stop editing that file;
- prepare exact failing evidence, smallest proposed protected change, affected invariant, and rollback;
- label result `BLOCKED_HIGH_MODEL_AUTHORITY`;
- continue independent non-protected tasks.
## Integration order
Merge lowest-risk foundational fixes first:
R-01 execution-contract hardening
R-02 autonomous execution proof/error resolution
R-03 authority visibility
R-04 generated-state reconciliation
R-05 OpenClaw/AION integration
R-06 unattended reliability
R-07 final integration/audit package

After each merge:
- sync canonical runtime only if clean and safe;
- rerun health/status;
- rerun relevant regression;
- stop if a new failure appears.