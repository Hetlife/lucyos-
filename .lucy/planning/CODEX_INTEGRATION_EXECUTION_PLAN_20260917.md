# LucyOS / Mark-2 — Codex Integration Execution Plan

- **Status**: SUPERVISED EXECUTION PLAN. Not authority to merge `main`, change governance, deploy, spend, or enable unattended Codex.
- **Planning base**: `.lucy/planning/INTEGRATION_ROADMAP_V2_20260917.md`
- **Canonical integration branch**: `integration/consolidation-20260916`
- **Base of record**: `c11fcb6`
- **Purpose**: integrate the 23 task PRs into one healthy canonical branch with deterministic checkpoints and no gate weakening.

## 0. Non-negotiable invariants

1. Never weaken, skip, disable, quarantine, or reinterpret a required test/gate to obtain green state.
2. `strict` authority verification is **per candidate task branch before merge**. Never run `strict` on the accumulated integration branch.
3. `anti-dup` is cumulative and runs on the evolving integration branch after each merge.
4. Stop at the first unexpected conflict, regression, authority violation, portability failure, migration failure, dirty-tree anomaly, or owner-only decision.
5. Mechanical conflict resolution only. If two sides express different semantics, stop and escalate.
6. Preserve `worker._validate` semantics exactly; Codex-reported success is never proof.
7. No spending, credentials, external-account creation, deployment, real capital, ownership/control changes, or branch-protection changes.
8. Strategy Factory remains paper/sandbox only. SEVAA Sales OS remains deprioritized.
9. No second loop, scheduler, state store, top-level control-plane module, or schema outside `aion_core/db.py`.
10. Codex must not modify `AGENTS/prompts/**` or `.lucy/authority/**`. During supervised integration, any attempted governance-path modification is a hard stop.

## 1. Session bootstrap

At the start of every Codex integration session, fetch both the plan ref and the integration ref. The execution plan lives on the planning branch, not on the integration branch, so read it with `git show` rather than assuming the file exists after checkout:

```bash
PLAN_REF=origin/planning/integration-roadmap-20260917
PLAN_PATH=.lucy/planning/CODEX_INTEGRATION_EXECUTION_PLAN_20260917.md
INTEGRATION_BRANCH=integration/consolidation-20260916
git fetch origin planning/integration-roadmap-20260917 integration/consolidation-20260916 --prune
git show "$PLAN_REF:$PLAN_PATH" > /tmp/CODEX_INTEGRATION_EXECUTION_PLAN_20260917.md
git switch "$INTEGRATION_BRANCH"
git status --porcelain=v1
git rev-parse HEAD
git rev-parse "origin/$INTEGRATION_BRANCH"
git log -1 --oneline
python3 --version
```

Required conditions:
- working tree clean;
- current branch exactly `integration/consolidation-20260916`;
- no unresolved merge/rebase/cherry-pick state;
- local integration HEAD equals `origin/integration/consolidation-20260916`, unless the difference is exactly the already-recorded supervised integration checkpoint;
- integration HEAD matches the last recorded checkpoint, or the difference is explained by commits already recorded in the existing session/checkpoint state.

Do not `pull`, reset, or fast-forward merely to make the SHAs match. An unexplained local/remote difference is a hard stop. Mark-2 has `python3`; do not assume a `python` executable exists.

If any condition fails: **STOP**, do not clean/reset blindly. Record the discrepancy and exact Git evidence.

For each candidate PR, record before touching it:
- PR number and task ID;
- candidate head SHA;
- current integration HEAD;
- changed-file list;
- current GitHub CI state;
- whether `strict` is applicable because protected paths are touched.

## 2. Common validation checkpoint

After every individual candidate integration commit, run the checks against the candidate delta and the accumulated tree. `INTEGRATION_HEAD_BEFORE` must be recorded before starting that candidate; `AUTHORIZED_BASE_SHA` is the exact Wave-0-complete SHA pinned once in section 4:

```bash
git diff --check "$INTEGRATION_HEAD_BEFORE"..HEAD
python3 -m compileall -q aion_core bridges tests scripts
python3 scripts/check_portability.py
AION_HOME="$(mktemp -d)" ./aion scan .
AION_HOME="$(mktemp -d)" python3 -m unittest discover -s tests -t . -q
python3 scripts/verify_authority.py anti-dup --base "$AUTHORIZED_BASE_SHA"
```

A bare `git diff --check` after a committed merge checks only uncommitted work and is not sufficient evidence for the integrated candidate.

Then require the repository CI-equivalent checks appropriate to that wave. Do not advance after a local green if GitHub CI for the resulting integration SHA reports a required failure.

`authority-drift` remains informational by design. `macos-readiness` remains advisory until its existing promotion rule is satisfied. Neither may be used to waive any required check.

## 3. Per-candidate authority protocol

Run task-scoped `strict` for **every** candidate, not only candidates believed to touch protected paths. This prevents a stale changed-file classification from skipping authority verification. The verifier checks `HEAD`, so it must execute with `HEAD` at the candidate SHA; `--branch` supplies task identity but does not switch branches. Use the verifier file from the pinned authorized base, never the candidate copy:

```bash
CANDIDATE_ROOT="$(mktemp -d)"
CANDIDATE_DIR="$CANDIDATE_ROOT/worktree"
VERIFY_FILE="$(mktemp)"
git worktree add --detach "$CANDIDATE_DIR" "$CANDIDATE_SHA"
git show "${AUTHORIZED_BASE_SHA}:scripts/verify_authority.py" > "$VERIFY_FILE"
( cd "$CANDIDATE_DIR" && python3 "$VERIFY_FILE" strict \
    --base "$AUTHORIZED_BASE_SHA" --branch "$TASK_BRANCH" )
STRICT_RC=$?
git worktree remove "$CANDIDATE_DIR"
rm -f "$VERIFY_FILE"
rmdir "$CANDIDATE_ROOT" 2>/dev/null || true
test "$STRICT_RC" -eq 0
```

If `strict` fails, stop that candidate. Do not modify the candidate or baseline merely to clear the gate.

After the candidate is integrated into the evolving integration branch:

```bash
python3 scripts/verify_authority.py anti-dup --base "$AUTHORIZED_BASE_SHA"
```

Never run aggregate `strict` over accumulated task commits: multiple `Task-ID` trailers make the command ambiguous by construction.

## 4. Wave 0 — OWNER ONLY

Required owner/high-model decisions before autonomous integration:

1. Correct `HIGH_MODEL_BASELINE.json` with the five already-identified module entries:
   - `portability`
   - `guardian`
   - `experiments`
   - `money_path`
   - `tempworker`
2. Add the already-identified `S-22` task override.
3. Correct the `.lucy/authority/` prefix omission in `PROTECTED_PATHS.md`.
4. Decide S-02 portability handling:
   - preferred: make the rule distinguish runtime portability violations from string literals used in security deny-lists;
   - alternative: narrowly scoped explicit known exception owned by S-02.

Codex may inspect and prepare evidence for Wave 0 but **must not perform these semantic governance edits autonomously**.

Wave 0 completion criterion: re-run the previously baseline-blocked PR authority checks and confirm their only known blocker is removed without weakening anti-dup/strict semantics. Then pin the exact Wave-0-complete integration SHA once:

```bash
AUTHORIZED_BASE_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$AUTHORIZED_BASE_SHA"
```

Use that immutable SHA as the authority base for every Waves 1–6 `strict` and cumulative `anti-dup` invocation. Do not silently substitute the moving integration branch name.

## 5. Wave 1 — zero-overlap group

Order:
`#23, #22, #13, #32, #31, #15, #25, #16, #19`

Procedure per PR:
1. verify candidate SHA/CI;
2. set `INTEGRATION_HEAD_BEFORE=$(git rev-parse HEAD)`;
3. integrate the **entire candidate head**, one PR at a time. Prefer a normal merge preserving candidate ancestry; do not cherry-pick an arbitrary subset of a PR. If repository policy forbids merge commits, stop before the first candidate and obtain the approved merge method;
4. if conflict exists despite the verified zero-overlap map: stop and report because ground truth changed;
5. run Common Validation Checkpoint;
6. record resulting integration SHA before proceeding.

Do not batch several PRs into one opaque commit. Each PR must remain attributable in history/evidence.

## 6. Wave 2 — single-file-owner group

Order:
`#28, #26, #20`

Run per-candidate `strict` where protected paths are touched, then merge individually and run the Common Validation Checkpoint after each.

Stop if a candidate modifies a file not represented in the reviewed overlap assumptions in a way that creates a new semantic conflict.

## 7. Wave 3 — `db.py` convergence

Strict order:
`#17 → #18 → #35`

Never batch-resolve these.

After each merge:
1. inspect `aion_core/db.py` `_ADDED_COLUMNS` manually;
2. verify no duplicate `(table, column)` migration entry;
3. verify no drop/rename/retype migration was introduced;
4. run the Common Validation Checkpoint;
5. run clean bootstrap;
6. run an upgrade from a database created by `origin/main`;
7. verify SQLite integrity and skill registry health.

CI-equivalent old-schema proof:

```bash
TMP="$(mktemp -d)"
OLD="$TMP/old-tree"
STATE="$TMP/state"
mkdir -p "$OLD"
git fetch origin main --depth=1
git archive origin/main | tar -x -C "$OLD"
(
  cd "$OLD"
  AION_HOME="$STATE" ./aion init
  AION_HOME="$STATE" ./aion seed
)
AION_HOME="$STATE" ./aion boot
AION_HOME="$STATE" python3 - <<'PY'
from aion_core import db, skills
c = db.connect()
assert c.execute("pragma integrity_check").fetchone()[0] == "ok"
errs = skills.validate_registry()
assert errs == [], errs
print("upgrade ok")
PY
AION_HOME="$STATE" python3 scripts/ci_health_gate.py
```

Any migration discrepancy is a hard stop. Do not edit historical migration intent to make the newest branch fit.

## 8. Wave 4 — `drive_bridge.py` convergence

Strict order:
`#14 → #21`

After each:
- resolve only additive/mechanical conflicts;
- Common Validation Checkpoint;
- record `macos-readiness` outcome separately from required checks.

#14 remains first because it contains the already-verified macOS-readiness fix.

## 9. Wave 5 — `cli.py` convergence

Strict order:
`#27 → #29 → #30 → #24 → #33`

This is the highest textual-conflict wave. One PR at a time only.

For each PR:
1. save the pre-merge `cli.py` blob SHA;
2. inspect the candidate `cli.py` patch before merge;
3. integrate only that full candidate head using the same approved merge method as the earlier waves;
4. resolve conflicts mechanically and additively;
5. inspect the complete resulting `cli.py` before committing;
6. check for duplicate parser/subparser names, duplicate registration, handler shadowing, conflicting defaults, duplicate imports, and unreachable dispatch paths;
7. run the Common Validation Checkpoint, including `git diff --check "$INTEGRATION_HEAD_BEFORE"..HEAD`, compile, portability, secret scan and full unit suite;
8. run CLI smoke for each subcommand newly introduced by that candidate using non-destructive/help/dry-run forms only;
9. run cumulative `anti-dup`;
10. record resulting integration SHA.

If the intended behaviors of two CLI branches conflict rather than merely overlap textually: abort the candidate merge and escalate. Never guess which semantics wins.

## 10. Wave 6 — S-02 / `worker.py` execution boundary

Candidate: `#34` only.

Before merge:
- run task-scoped `strict`;
- read the complete `worker.py` execution-boundary diff manually;
- verify the portability fix corresponds exactly to the owner-approved Wave-0 decision.

After merge:
- Common Validation Checkpoint;
- targeted tests for command allow/deny behavior and worker validation behavior;
- prove forbidden commands remain forbidden;
- prove allowed argv execution path works;
- prove `_validate` still independently runs `validation_command`;
- prove class A/B model output without independent validation still becomes `NEEDS_REVIEW`, not DONE;
- prove singleton `_execution_lock` behavior is unchanged.

If `_validate`, evidence semantics, secret protections, lock semantics, or authority boundaries changed unintentionally: hard stop.

## 10.1 Remote CI / push boundary

GitHub CI on the **accumulated integration SHA** cannot exist until that SHA is present on GitHub. Candidate PR CI is not a substitute because it does not include earlier integrated candidates. Therefore:

- supervised Codex may push only `integration/consolidation-20260916`, never `main`, **after** local validation, and only if the owner has explicitly authorized supervised integration-branch pushes for this run;
- push must be a normal fast-forward from the last verified remote integration SHA; force-push is forbidden;
- if supervised push authority has not been granted, stop after local validation and hand the exact SHA to the owner/high model to push; do not claim GitHub CI for that SHA until it actually runs;
- after any push, fetch the workflow status for that exact SHA and stop on any required red check.

This permission is distinct from unattended-loop push authority, which remains owner-only and disabled.

## 11. Wave 7 — OWNER boundary

Codex stops before final canonicalization.

Required evidence packet to owner/high-model:
- final integration SHA;
- clean working tree proof;
- exact PRs integrated;
- required local validation results;
- GitHub CI status on the exact integration SHA;
- remaining advisory failures, clearly labelled advisory;
- unresolved findings/errors, if any;
- authority `anti-dup` result;
- confirmation that no governance files were autonomously modified outside approved Wave 0.

Owner/Fable only:

```bash
python3 scripts/verify_authority.py freeze --sha <EXACT_FINAL_SHA>
python3 scripts/verify_authority.py self
python3 scripts/verify_authority.py deploy
```

Then owner approves integration → `main`. Codex must not merge to `main` under this plan.

## 12. Wave 8 — dependency-unlocked work

Only after Wave 7 is complete and canonical task state re-triaged from the shared brain:
- S-11, S-12 after S-10 is truly landed;
- S-25 after S-05 is truly landed;
- S-03 then S-04 after S-02 is truly landed.

An open PR does not satisfy a dependency. Recompute readiness from canonical state; do not rely on old queue prose.

## 13. Post-integration bounded architecture tasks

Create/execute through normal task governance after canonical integration:

- **S-30** — normalize `context.py` and `scripts/aion_codex_worker.sh` onto exactly seven result fields:
  `STATUS / ACTIONS / FILES_CHANGED / TESTS / RESULTS / BLOCKERS / NEXT_ACTION`.
- **S-31** — add result-packet parser and changed-path governance guard inside the existing `worker.py` seam. Preserve `_validate` and `_execution_lock` semantics.
- **S-32** — append-only `.lucy/execution/CODEX_FINDINGS.md` review surface linked to canonical `errors`; no new state store.

**Mandatory autonomy gate:** S-31 must be complete and verified before any unattended Codex execution is enabled. Even then, unattended Codex remains prohibited until the owner resolves true governance-path immutability.

## 14. Recovery matrix

| Failure | Required response |
|---|---|
| Merge conflict before commit | Stop; inspect. Resolve only if mechanical/additive. Semantic conflict → `git merge --abort` (only after verifying the merge is the current candidate operation) and escalate. |
| Required validation fails after an unpushed candidate merge commit | Verify HEAD is exactly that candidate integration commit and the worktree has no unrelated changes; under supervision, return to the recorded `INTEGRATION_HEAD_BEFORE`. Never use an unscoped reset. Preserve failure evidence first. |
| Required validation fails after the integration SHA was pushed | Do not force-push or rewrite remote history. Stop and escalate for an explicit revert/repair decision. |
| Dirty tree before candidate | Stop. Do not reset/clean automatically. Identify provenance. |
| `strict` fails | Candidate blocked. Do not alter authority baseline unless owner-approved Wave 0 change already covers it. |
| `anti-dup` fails | Stop integration immediately; do not add allowlist entries autonomously. |
| Portability fails | Stop. Never add suppression solely to get green. Reproduce and classify. |
| Unit/compile/scan failure | Stop at first failing candidate; preserve exact command/output and pre-merge SHA. |
| DB upgrade failure | Abort candidate merge; preserve old-state fixture/evidence. Do not edit prior schema history destructively. |
| GitHub required CI red after local green | Stop; inspect exact job/step logs before any further merge. Never substitute candidate-PR CI for CI on the accumulated integration SHA. |
| Remote integration branch changed concurrently | Stop. Fetch, compare exact SHAs, and reconcile ownership/checkpoints. Never force-push over an unexplained remote update. |
| Codex timeout | Preserve work order/worktree evidence; do not claim failure or success without independent validation. |
| Attempted governance-path write | Reject task result, record exact paths, restore to pre-task state under supervision, escalate. |
| Unexpected branch/SHA drift | Stop; reconcile against GitHub and canonical shared brain before continuing. |

## 15. Execution log format

Append one compact checkpoint per attempted PR through the existing AION session/checkpoint seam; do not create another state store. `./aion session` and `./aion checkpoint` are the existing CLIs on Mark-2. The implementation session should record the session ID once and log each candidate checkpoint there; use `aion checkpoint` for the resume/bottleneck pointer.

Required fields:
- `PR`
- `TASK_ID`
- `CANDIDATE_SHA`
- `INTEGRATION_HEAD_BEFORE`
- `STRICT_RESULT`
- `CONFLICT_RESULT`
- `VALIDATION_COMMANDS`
- `VALIDATION_RESULT`
- `ANTI_DUP_RESULT`
- `GITHUB_CI_RESULT`
- `INTEGRATION_HEAD_AFTER`
- `BLOCKER`
- `NEXT_ACTION`

A candidate is never considered integrated from a commit exit code alone; its checkpoint must include independent validation evidence.

## 16. Tiny resume contract

A future Codex session receives only:

> Fetch `planning/integration-roadmap-20260917` and read `.lucy/planning/CODEX_INTEGRATION_EXECUTION_PLAN_20260917.md` from `origin/planning/integration-roadmap-20260917` with `git show` (the file is not assumed to exist on the integration branch). Read the canonical shared-brain state. Verify the current branch, local and remote HEADs, cleanliness, CI, and last recorded checkpoint. Resume the next uncompleted safe step exactly as written. Do not redesign the plan, weaken gates, modify governance, merge to `main`, force-push, or enable unattended autonomy. Stop only on a genuine owner/high-model decision or unexpected semantic conflict, and return exact evidence.

## 17. Definition of integration success

Integration phase is successful only when:
- all approved Waves 1–6 candidates are integrated in reviewed order;
- every required checkpoint passes on the accumulated integration branch;
- old-schema upgrade remains healthy after all DB changes;
- `worker._validate`, singleton locking, secret protections, restart/resume and authority semantics remain intact;
- no unresolved required CI failure exists on the exact final integration SHA;
- owner/Fable performs final freeze/canonical merge decision;
- no claim of unattended Codex readiness is made until S-31 plus a separately approved path-immutability solution are verified.
