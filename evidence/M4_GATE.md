# FABLE-07 — M3/M4 Review and M4 Gate

**Reviewed state:** ratified integration through `bbd468d`.

## 1. Demonstrable improvements

- `aion verify --json` provides a machine acceptance verdict; deep health is
  healthy with zero tasks/errors and backup/secret checks passing.
- S-49 makes tests independent of hostile AION/OpenClaw environment variables.
- The boundary ratchet is reproducible, warning-only, stdlib-only, and runs in
  0.11 seconds; strict promotion is not enabled.
- Dependency cycles measured 11 versus the earlier 14; duplication scan found
  zero duplicate function bodies.
- Every completed wave task has checkpoint/evidence and rollback information.

## 2. Unchanged or worse

- Context proxies remain 102 and 63 files, not ≤10; actual model tokens,
  calls, retries and files opened were not recorded.
- Full-suite runtime is 56.491 seconds after S-48 versus 46.1 seconds baseline
  (+22.5% on the final run), not ≤+10%. Test count increased from 562 to 618.
- Production snapshot is additive (71 modules / 13,584 LOC); no overall LOC
  reduction is claimed. `cli._main` remains the primary decomposition hotspot.
- Two SQLite import warnings remain; separate assessment classifies both as
  harmless existing uses, not duplicate state stores.
- S-48 has not run five consecutive daily false-positive observations and was
  not promoted to required CI.

## 3. Root causes of misses

- Context: the profiler includes a fixed 1,240-LOC governance corpus and test
  import closure; worker-level telemetry is absent, so the ≤10 target cannot
  be demonstrated from this run.
- Runtime: the wave added 56 tests (including broad acceptance and hermetic
  regression coverage); no timing profile proves a single pathological test.
  The observed increase is real but not a production failure.

## 4. Priority decision

Neither miss requires emergency work. Record two prioritized backlog items:

1. **P2:** add worker context/call/retry/opened-file telemetry and split the
   fixed governance corpus from task-specific context measurement.
2. **P2:** profile the full suite, then reduce runtime only where measured;
   preserve acceptance coverage.

The two SQLite warnings remain **P3 boundary-rule refinement**, not S-46 work.

## 5. Simplification and next move

M5 low-risk cleanup has measurable value: archive superseded planning material,
collapse duplicate routers, and remove only dead-weight candidates with proof.
M6 should remain deferred until M5 and new context measurements; its first
candidate is the already-defined `cli._main` learnrepo/skills/architecture
dispatch seam, with no public behavior change.

The Secure Capability Gateway + Alternative-Path Engine is a backlog epic only.
Before implementation it needs a trust model, existing WhatsApp/OpenClaw path
map, capability boundaries, encrypted payload design, authenticated approval
protocol, and smallest MVP research.

## Gate result

**M3/M4 CLOSED WITH FOLLOW-UPS.** The completed work is operationally healthy
and verified; the two unmet targets remain explicitly unresolved. No CI
promotion, canonical merge, or security-critical implementation is authorized
by this review.

**Owner gate retained:** promotion of `check_boundaries.py` to required CI is
an L4 decision and is not included in this closeout.
