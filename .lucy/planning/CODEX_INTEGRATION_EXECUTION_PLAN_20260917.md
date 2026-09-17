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

At the start of every Codex integration session:

```bash
git fetch --all --prune
git checkout integration/consolidation-20260916
git status --porcelain=v1
git rev-parse HEAD
git log -1 --oneline
```

Required conditions:
- working tree clean;
- current branch exactly `integration/consolidation-20260916`;
- no unresolved merge/rebase/cherry-pick state;
- integration HEAD matches the last recorded checkpoint, or the difference is explained by commits already recorded in this plan's execution log.

If any condition fails: **STOP**, do not clean/reset blindly. Record the discrepancy and exact Git evidence.

For each candidate PR, record before touching it:
- PR number and task ID;
- candidate head SHA;
- current integration HEAD;
- changed-file list;
- current GitHub CI state;
- whether `strict` is applicable because protected paths are touched.

## 2. Common validation checkpoint

After every individual merge/cherry-pick/conflict-resolution commit, run:

```bash
git diff --check
python -m compileall -q aion_core bridges tests scripts
python scripts/check_portability.py
AION_HOME="$(mktemp -d)" ./aion scan .
AION_HOME="$(mktemp -d)" python -m unittest discover -s tests -t . -q
python scripts/verify_authority.py anti-dup --base <POST-WAVE0-AUTHORIZED-BASE>
```

Then require the repository CI-equivalent checks appropriate to that wave. Do not advance after a local green if GitHub CI for the resulting integration SHA reports a required failure.

`authority-drift` remains informational by design. `macos-readiness` remains advisory until its existing promotion rule is satisfied. Neither may be used to waive any required check.

## 3. Per-candidate authority protocol

Before merging any task branch that touches protected paths:

```bash
python scripts/verify_authority.py strict \
  --base origin/integration/consolidation-20260916 \
  --branch <TASK_BRANCH>
```

Use the verifier from the authorized base when reproducing CI semantics. If `strict` fails, stop that candidate. Do not modify the branch or baseline merely to clear the gate.

After the merge into the evolving integration branch:

```bash
python scripts/verify_authority.py anti-dup --base <POST-WAVE0-AUTHORIZED-BASE>
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

Wave 0 completion criterion: re-run the previously baseline-blocked PR authority checks and confirm their only known blocker is removed without weakening anti-dup/strict semantics.

## 5. Wave 1 — zero-overlap group

Order:
`#23, #22, #13, #32, #31, #15, #25, #16, #19`

Procedure per PR:
1. verify candidate SHA/CI;
2. trial merge candidate into current integration HEAD;
3. if conflict exists despite the verified zero-overlap map: stop and report because ground truth changed;
4. run Common Validation Checkpoint;
5. record resulting integration SHA before proceeding.

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
AION_HOME="$STATE" python - <<'PY'
from aion_core import db, skills
c = db.connect()
assert c.execute("pragma integrity_check").fetchone()[0] == "ok"
errs = skills.validate_registry()
assert errs == [], errs
print("upgrade ok")
PY
AION_HOME="$STATE" python scripts/ci_health_gate.py
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
3. merge/cherry-pick only that candidate;
4. resolve conflicts mechanically and additively;
5. inspect the complete resulting `cli.py` before committing;
6. check for duplicate parser/subparser names, duplicate registration, handler shadowing, conflicting defaults, duplicate imports, and unreachable dispatch paths;
7. run `git diff --check`, compile, portability, secret scan and full unit suite;
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
python scripts/verify_authority.py freeze --sha <EXACT_FINAL_SHA>
python scripts/verify_authority.py self
python scripts/verify_authority.py deploy
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
| Merge conflict | Stop; inspect. Resolve only if mechanical/additive. Semantic conflict → abort candidate merge and escalate. |
| Dirty tree before candidate | Stop. Do not reset/clean automatically. Identify provenance. |
| `strict` fails | Candidate blocked. Do not alter authority baseline unless owner-approved Wave 0 change already covers it. |
| `anti-dup` fails | Stop integration immediately; do not add allowlist entries autonomously. |
| Portability fails | Stop. Never add suppression solely to get green. Reproduce and classify. |
| Unit/compile/scan failure | Stop at first failing candidate; preserve exact command/output and pre-merge SHA. |
| DB upgrade failure | Abort candidate merge; preserve old-state fixture/evidence. Do not edit prior schema history destructively. |
| GitHub required CI red after local green | Stop; inspect exact job/step logs before any further merge. |
| Codex timeout | Preserve work order/worktree evidence; do not claim failure or success without independent validation. |
| Attempted governance-path write | Reject task result, record exact paths, restore to pre-task state under supervision, escalate. |
| Unexpected branch/SHA drift | Stop; reconcile against GitHub and canonical shared brain before continuing. |

## 15. Execution log format

Append one compact checkpoint per attempted PR to the supervised session log / existing canonical reporting seam; do not create another state store.

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

> Read `.lucy/planning/CODEX_INTEGRATION_EXECUTION_PLAN_20260917.md` and the canonical shared-brain state. Verify the current branch, HEAD, cleanliness, CI, and last recorded checkpoint. Resume the next uncompleted safe step exactly as written. Do not redesign the plan, weaken gates, modify governance, merge to `main`, or enable unattended autonomy. Stop only on a genuine owner/high-model decision or unexpected semantic conflict, and return exact evidence.

## 17. Definition of integration success

Integration phase is successful only when:
- all approved Waves 1–6 candidates are integrated in reviewed order;
- every required checkpoint passes on the accumulated integration branch;
- old-schema upgrade remains healthy after all DB changes;
- `worker._validate`, singleton locking, secret protections, restart/resume and authority semantics remain intact;
- no unresolved required CI failure exists on the exact final integration SHA;
- owner/Fable performs final freeze/canonical merge decision;
- no claim of unattended Codex readiness is made until S-31 plus a separately approved path-immutability solution are verified.
