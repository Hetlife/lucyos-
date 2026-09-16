# FABLE_PROGRESS — LucyOS architecture cycle 2026-09-16

Role: Fable (highest-capability architect). Branch: `planning/opus-fable-20260916`.
Input: `.lucy/planning/LUCYOS_OPUS_TO_FABLE_ARCHITECT_BRIEF.md` @ `2f5f376`.

## Current objective
Build the deterministic enforcement substrate (CI + authority freeze + protected-path
verifier), reconcile the three collisions, and hand Sonnet a bounded queue. No merge to main.

## Owner decisions received (binding for this cycle)
- LucyOS is intended to become PRIVATE unless explicitly overridden.
- Protect `main`; reviewed PR + CI required; models never merge to main directly.
- Mac readiness is an active P1 requirement.
- SEVAACONNECT integration deferred until consolidation is stable.
- Every schema/enum/policy migration ships with an upgrade-from-old-state regression test.

## Runtime corrections received (Mark-2, owner-verified; override Opus classifications)
- Q006/248-test lineage was running on Mark-2; skill-registry health DEGRADED by legacy lowercase classes.
- Scheduled loop + session logging: LIVE_VERIFIED.
- checkpoint→restart→resume, structured plan execution, approvals, local Ollama execution,
  validation gating, governor high→low handoff: LIVE_VERIFIED in isolated rehearsals.
- Drive reads LIVE_VERIFIED; Drive writes BROKEN/DEGRADED (rclone remotes read-only).
- OpenClaw 2026.9.1 works transiently on loopback; persistent integration DEGRADED.

## Independently verified by Fable (this session)
- `aion_core/learnrepo.py` add/add collision reconfirmed: blobs `524abbe2` (78 lines, RG) vs `38d16b28` (669 lines, Q006).
- No `.github/` on any of 18 branches. `main` `protected: false` (GitHub API).
- Trial merges (`git merge-tree --write-tree`): Q006+claude-audit CLEAN; RG+claude-audit CLEAN;
  Q006+RG CONFLICTS in `cli.py`, `db.py`, `health.py`, `learnrepo.py`(add/add); `worker.py` auto-merges.
  ⇒ the "three-way worker.py collision" is sequencing, not a semantic conflict.
- CI candidate steps pass locally: init → seed → health → backup → backup --verify-only → boot; init idempotent.
- Upgrade-from-`main`-schema: main tree init (23 tables) → current code boot → 30 tables, integrity ok, `validate_registry()==[]`.

## Decisions (see EXECUTION_PACKAGE for rationale)
- D1 Enforcement: base-ref protected-path verifier + anti-duplication diff scan, run from the BASE copy of the verifier; branch protection with required checks `authority-gate`, `code-and-test`.
- D2 Names: Q006 `aion_core/learnrepo.py` KEEPS its name (evidence/health contract runtime). RG's 78-line module RENAMED to `aion_core/research_registry.py` (table `research_targets` unchanged). `.claude/skills/learnrepo/` keeps its name (developer skill, not runtime).
- D3 Governors: both KEPT. Precedence = most-restrictive-wins; spend governor runs first (queue mutation), capacity gate second (per-task admission); neither upgrades; `resource_governor.enforce_admission` stays OFF this cycle.
- D4 Integration order: main → Q006 → claude-audit (clean) → RG (conflict task) on one integration branch.
- D5 `docs/architect/*` from claude-audit ARCHIVED under `.lucy/archive/`, not a second planning surface.

## Completed
- Checkpoint created.
- `scripts/verify_authority.py` (strict / anti-dup / self / deploy / freeze) + `tests/test_authority_verifier.py` (8 tests, all pass, incl. "branch cannot grant itself an override").
- `.github/workflows/lucyos-ci.yml`: code-and-test (3.9/3.11/3.13), clean-bootstrap-health, upgrade-from-main-schema, authority-gate (verifier read from BASE), authority-drift (informational), macos-readiness (advisory until FABLE-02).
- `scripts/ci_health_gate.py`: asserts the 8 checks a clean runner can honestly satisfy (raw `aion health` exits 1 on secret_store).
- `.lucy/authority/HIGH_MODEL_BASELINE.json`, `PROTECTED_PATHS.md`, `LUCYOS_FABLE_ARCHITECT_EXECUTION_PACKAGE.md`.
- `.lucy/execution/SONNET_TASK_QUEUE.md` (S-01..S-05, S-07..S-09; FABLE-01/02; OWNER-01..04).
- `.lucy/deployment/MARK2_DEPLOYMENT_CONTRACT.md` (DC-0 rehearsal = freeze sha; DC-1 unnamed until FABLE-01).
- Full suite 256 OK; scan clean; verifier self OK.

## Freeze record
- Commit A (protected files frozen): `afd84aa325e4e2abebdb616185dba63af89da24d` = FABLE_FREEZE_SHA
- Commit B (baseline records the SHA): `e4264dd3e9c99c55eb60dd3ced4f29ea4c5a53b9`
- `verify_authority.py deploy` → ok against A.
- Integration branch `integration/consolidation-20260916` created from B.

## Current task (DONE)
Freeze ritual: commit A (all files, sha PENDING) → commit B (fable_freeze_sha = A) → push → create `integration/consolidation-20260916` from B.

## Next action (after this session)
Owner: OWNER-01 (branch protection), OWNER-02 (private). Then Sonnet starts S-01 (independent) and S-02.
Fable: FABLE-01 re-freeze after S-02..S-04 merge; name DC-1 in the deployment contract.

## Exact resume point
If this session resets after commit B exists: only the push / integration-branch creation may be outstanding — check `git branch -r`. Nothing else remains for Fable this cycle.


## CI workflow-validation fix (Sonnet, 2026-09-16, post-Fable)

Owner reported both push runs on planning/opus-fable-20260916 failed at
workflow-validation time with zero jobs created:
- run 35113032369 (commit 766dc2a) -- confirmed via GitHub API: status
  completed, conclusion failure, list_workflow_jobs returns total_count 0.
- run 35113037040 -- same symptom, not independently re-queried (same root cause).

Root cause (owner's diagnosis, independently confirmed against GitHub's
context-availability rules): three jobs' `env:` blocks were at job level
(`jobs.<job_id>.env`) and referenced `${{ runner.temp }}`. The `runner`
context does not exist yet when job-level env is evaluated -- it is only
available inside a step's own env/run/with. GitHub rejects the whole
workflow file for this, producing exactly the observed zero-jobs failure
(a single validation error for the file, not a per-job one).

Fix (commit 2ff0f6b2bacfd82a4f16baf635dc8800772fb34d, pushed to
planning/opus-fable-20260916): removed job-level `env:` from
clean-bootstrap-health, upgrade-from-main-schema, macos-readiness; added an
early "Set AION_HOME" step to each doing
`echo "AION_HOME=$RUNNER_TEMP/<home>" >> "$GITHUB_ENV"`. Left the two
step-level `runner.temp` usages in code-and-test untouched (valid location
per the same rules). No architecture or functional LucyOS code changed --
workflow file only.

Verified before push: PyYAML parse OK, zero job-level env blocks remain,
grep confirms only the two legitimate step-level runner.temp usages;
every job's step sequence simulated locally end to end (clean-bootstrap-health,
upgrade-from-main-schema, macos-readiness's platform-neutral steps all
passed); full suite 256 OK; aion scan clean; verify_authority.py self:
8/8 tests OK. verify_authority.py self/deploy correctly reported hash
drift on .github/workflows/lucyos-ci.yml itself (a constitutional path) --
expected, since this fix legitimately changes it; needs a re-freeze once
the run is confirmed green (do not re-freeze on an unverified fix).

STATUS: pushed; watching for the resulting Actions run on commit 2ff0f6b
to confirm GitHub actually creates jobs this time, then driving
code-and-test / clean-bootstrap-health / upgrade-from-main-schema /
authority-gate green. macos-readiness and authority-drift stay
continue-on-error by design (advisory / informational) and do not block
this task's completion criteria.

Exact resume point if interrupted: check run status for HEAD of
planning/opus-fable-20260916 via GitHub Actions API; if jobs exist and are
red, read the specific job's log next, do not re-diagnose the workflow file.


## CI workflow-validation fix -- FINAL RESULT (2026-09-16)

Fix commit: `2ff0f6b2bacfd82a4f16baf635dc8800772fb34d`
Follow-up fix commit (Python 3.9 test compat, discovered by the now-working
matrix): `6a5f7d81cd8697e1fef5ab95095bf1fd20202ce0`

### Run 1 -- workflow fix alone (still red, but jobs now exist)
- Run: 35116873386 -- https://github.com/Hetlife/lucyos-/actions/runs/35116873386
- Overall: completed / failure
- code-and-test (py3.9): FAILURE -- `AttributeError: 'PosixPath' object has no
  attribute 'hardlink_to'` in tests/test_drive_bridge.py:120. Path.hardlink_to()
  is Python 3.10+; LucyOS commits to 3.9+ (README.md). This was LucyOS's
  first-ever real run of the 3.9 matrix entry, so the bug was never exercised
  before. code-and-test (py3.11), (py3.13): success.
- clean-bootstrap-health, upgrade-from-main-schema, authority-gate: success.
- authority-drift (informational, continue-on-error): failure -- expected;
  reports hash drift on .github/workflows/lucyos-ci.yml because that file was
  legitimately just changed and not yet re-frozen.
- macos-readiness (advisory, continue-on-error): failure -- same 3.9-class
  issue plus a macOS-specific one, superseded by run 2's finding below.

### Run 2 -- after the 3.9-compat fix
- Run: 35117351924 -- https://github.com/Hetlife/lucyos-/actions/runs/35117351924
- Overall: completed / **success**
- **code-and-test (py3.9): SUCCESS** -- https://github.com/Hetlife/lucyos-/actions/runs/35117351924/job/104866039315
- code-and-test (py3.11): SUCCESS -- job 104866039443
- code-and-test (py3.13): SUCCESS -- job 104866039354
- **clean-bootstrap-health: SUCCESS** -- job 104866039939
- **upgrade-from-main-schema: SUCCESS** -- job 104866039282
- **authority-gate: SUCCESS** -- job 104866039441
- authority-drift (informational): failure -- same expected hash-drift signal
  as run 1 (still not re-frozen -- see "Not done" below).
- macos-readiness (advisory): failure, root cause identified and DIFFERENT
  from the 3.9 issue -- `bridges/drive_bridge.py:read_safe()` rejects any path
  whose ancestor is a symlink (line 129, `part.is_symlink()`). On the macOS
  runner, `$RUNNER_TEMP`/`$TMPDIR` resolves under `/var/folders/...`, and
  `/var` itself is a symlink to `/private/var` on macOS -- so every
  drive-bridge test that stages a file under the test's tmp dir trips this
  check and raises `rejected_source`. 4 test errors, all in
  tests/test_drive_bridge.py. This is a genuine macOS-specific finding, not a
  CI or Python-version problem, and out of scope for this task (the task said
  fix the four required checks and *keep macos-readiness advisory until it
  passes* -- not fix it now). Recorded here as the exact next step for
  whoever picks up Mac readiness (S-05 territory, or a new task): either
  resolve symlinks before the ancestor walk (`path.resolve()` up front) while
  still rejecting a *final* symlink component, or scope the check to reject
  only if the leaf or an ancestor *inside the repo/AION_HOME* is a symlink,
  not OS-standard symlinked tmp roots. This needs a security-reasoning pass,
  not a quick patch -- do not weaken read_safe() without one.

### Confirmed via GitHub API (not narrated from memory)
- get_workflow_run(35113032369): status completed, conclusion failure,
  list_workflow_jobs returns total_count 0 -- matches the reported
  "zero jobs" symptom exactly, before the fix.
- get_workflow_run(35117351924): status completed, conclusion success, after
  both fixes.

### Not done (explicitly out of scope per the task)
- No Sonnet bulk coding started.
- No merge to main.
- No required-status-check configuration in branch protection -- the task
  said not to configure this until checks had actually appeared in a
  successful run; they now have (run 35117351924), so OWNER-01 (branch
  protection naming exactly `code-and-test`, `clean-bootstrap-health`,
  `upgrade-from-main-schema`, `authority-gate`) is now actionable by the
  owner, but I did not configure it myself (no tool access to repository
  admin settings, and it is an owner-only action per HIGH_MODEL_BASELINE.json
  regardless).
- authority-drift still shows hash drift on .github/workflows/lucyos-ci.yml
  (expected, since that file legitimately changed twice this session and
  hasn't been re-frozen). Re-freezing is FABLE-01-class work and wasn't part
  of this fix request; flagging so it isn't mistaken for an unresolved bug.

## Exact resume point

CI is green on the four required checks at commit 6a5f7d81. Next actions, in
order: (1) owner configures branch protection naming the four check names
now proven to exist; (2) re-freeze (FABLE_FREEZE_SHA) once this and any
further protected-path changes settle, to clear the authority-drift signal;
(3) macos-readiness's symlink/tmp-root finding is available for whoever
scopes the next Mac-readiness task -- do not fix it inline without a
security-reasoning pass on read_safe().
