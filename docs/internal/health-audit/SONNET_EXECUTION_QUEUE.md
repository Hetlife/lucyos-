# Sonnet Execution Queue — 2026-09-17

Execute **strictly in order**. TASK-003 is an owner decision and gates TASK-004 and the
final push. Do not start a task whose dependency is unresolved.

Standing rules for every task below: never weaken a test or gate, never force-push, never
push to `main`, never invent architecture, and stop rather than improvise.

| Order | Task | Sev | Owner decision? | Depends on |
|---|---|---|---|---|
| 1 | TASK-001 record the canonical branch | P1 | no | NONE |
| 2 | TASK-002 allowlist the four owner modules | P1 | no | NONE |
| 3 | TASK-003 rule on derived index + external providers | P1/P2 | **YES** | TASK-002 |
| 4 | TASK-004 execute the reconciling merge | P1 | no | 001, 002, 003 |
| 5 | FINAL-SONNET-PUSH | — | no | 004 |

---

## TASK `TASK-001` — Record the canonical branch and fix `origin/HEAD`

**Priority:** P1 · **Subsystem:** repo integrity · **Confidence:** 100% · **Depends on:** NONE

### Problem
`origin/main` @ `0720a92` is the frozen candidate carrying all 23 task PRs, but
`.lucy/planning/INTEGRATION_ROADMAP_20260917.md` and `INTEGRATION_ROADMAP_V2_20260917.md`
both still name `integration/consolidation-20260916` as the target. Every later reader
inherits the wrong mental model.

### Evidence
`git rev-list --left-right --count origin/main...origin/integration/consolidation-20260916`
returns `27 8`. All 23 task tips are ancestors of `origin/main`. `origin/HEAD` is unset.

### Root cause
The owner promoted `main` to frozen candidate mid-flight; no artifact was updated to say so.

### Objective
A reader of the repo can determine the canonical branch in one step, and the two roadmap
files no longer assert the inverted relationship.

### Allowed files
- `.lucy/planning/INTEGRATION_ROADMAP_V2_20260917.md` — append a dated "SUPERSEDED / branch
  role correction" note at the end. Do not rewrite its body.
- `docs/internal/health-audit/HEALTH_REPORT.md` — no edit needed; referenced only.
- New file `.lucy/planning/CANONICAL_BRANCH.md` — three to six lines naming
  `origin/main` as canonical as of `0720a92`, why, and the date.

### Do not change
`.lucy/authority/**` (constitutional). `INTEGRATION_ROADMAP_20260917.md` (V1 is history).
Any code. Any test.

### Implementation instructions
1. Create `.lucy/planning/CANONICAL_BRANCH.md` stating: canonical branch is `origin/main`;
   frozen at `0720a92` by "owner: freeze supervised integration candidate";
   `integration/consolidation-20260916` is retained for history and for the pending
   reconciliation merge; dated 2026-09-17.
2. Append to `INTEGRATION_ROADMAP_V2_20260917.md` a section
   `## SUPERSEDED 2026-09-17 — branch roles inverted` with two or three sentences pointing at
   `CANONICAL_BRANCH.md` and at this audit.
3. Do not attempt to set `origin/HEAD`; that is a remote setting. Note it in
   `CANONICAL_BRANCH.md` as an owner action instead.

### Required tests
None. Documentation only.

### Verification commands
```
python3 -m unittest discover -s tests -t . -q
./aion scan .
```

### Completion criteria
Both files exist, suite still OK, scan clean, no code file touched.

### Rollback
`git revert` the single commit.

### Stop and escalate if
Either roadmap file is missing, or setting the canonical branch appears to require editing
anything under `.lucy/authority/`.

---

## TASK `TASK-002` — Add the four owner modules to the baseline allowlist

**Priority:** P1 · **Subsystem:** authority · **Confidence:** 100% · **Depends on:** NONE

### Problem
`verify_authority.py anti-dup` rejects the reconciling merge with four
"not in baseline allowlist" violations.

### Evidence
Exact violations, reproduced against the real merged state:
```
aion_core/model_gateway.py: new aion_core top-level module/package 'model_gateway' not in baseline allowlist
aion_core/platform_resolver.py: ... 'platform_resolver' not in baseline allowlist
aion_core/semantic_recall.py: ... 'semantic_recall' not in baseline allowlist
aion_core/usage_telemetry.py: ... 'usage_telemetry' not in baseline allowlist
```
All four files are present on `integration` and absent on `main`, introduced by `60b2dc7`
(owner-authored). All four have dedicated passing tests.

### Root cause
The baseline was not updated alongside the code. Same omission class that blocked five PRs
earlier the same day and was fixed for `portability`, `guardian`, `experiments`,
`money_path`, `tempworker`.

### Objective
`anti-dup` reports zero "not in baseline allowlist" violations for these four modules.

### Allowed files
`.lucy/authority/HIGH_MODEL_BASELINE.json` — **only** the `aion_core_modules` array, adding
exactly four strings.

### Do not change
Anything else in the baseline: not `protected_paths`, not
`constitutional_paths_no_override_possible`, not `task_overrides`, not
`sqlite_connect_allowed`, not `fable_freeze_sha`. Not `scripts/verify_authority.py`. No code.

### Implementation instructions
1. Confirm you are on the repair branch and `git status` is clean.
2. Add exactly `"model_gateway"`, `"platform_resolver"`, `"semantic_recall"`,
   `"usage_telemetry"` to `aion_core_modules`.
3. Do **not** add `semantic_recall` to `sqlite_connect_allowed`. Those four remaining
   violations are TASK-003's owner decision, not yours.
4. Verify the JSON still parses: `python3 -c "import json;json.load(open('.lucy/authority/HIGH_MODEL_BASELINE.json'))"`.

### Required tests
No new test. The existing authority tests must still pass.

### Verification commands
```
python3 -c "import json;json.load(open('.lucy/authority/HIGH_MODEL_BASELINE.json'))"
python3 -m unittest discover -s tests -t . -q
python3 scripts/verify_authority.py anti-dup --base origin/main
```

### Completion criteria
JSON parses. Suite OK. `anti-dup` no longer lists any of the four as "not in baseline
allowlist". Exactly four `sqlite3.connect` / `CREATE TABLE` violations for
`semantic_recall.py` remain — that is expected and correct at this stage.

### Rollback
`git revert` the single commit; the baseline returns to its prior state.

### Stop and escalate if
`anti-dup` still reports allowlist violations after the edit, or the diff touches any key
other than `aion_core_modules`, or you feel tempted to silence the `semantic_recall` SQLite
violations. That last one is the exact failure mode this task exists to prevent.

---

## TASK `TASK-003` — OWNER DECISION: derived index and external providers

**Priority:** P1 / P2 · **Subsystem:** architecture, security · **Confidence:** n/a
**Depends on:** TASK-002 · **THIS IS NOT A CODING TASK**

### Problem
Two questions block the merge and neither may be answered by a bounded worker.

**Q1 (P1).** `semantic_recall.py` opens its own SQLite store, producing four `anti-dup`
violations. Reading the code it is a *rebuildable derived vector index*, which the
data-library contract permits. But nothing in the repo records it as derived, so allowing it
by widening `sqlite_connect_allowed` would weaken the rule for every future module.

**Q2 (P2).** `model_gateway.py` routes `PUBLIC`-classed prompts to `openrouter.ai`,
`api.groq.com`, `api.cerebras.ai`, reading secrets by name. It is default-deny
(`tasks.data_class` defaults to `INTERNAL`) and auxiliary to the existing executor
hierarchy, and learnrepo vetting manifests exist. It is still a new external surface.

### Evidence
Violations 5–8 in `anti-dup` output; `aion_core/semantic_recall.py:76,79,80,107`;
`aion_core/model_gateway.py:16-36,41,98-129`; `aion_core/worker.py:427` vs `:437`;
`.lucy/planning/skill-exec-20260917/*.json`.

### Objective
A recorded owner ruling on both questions, written into the repo, so TASK-004 can proceed
with an unambiguous mandate.

### What Sonnet does
**Nothing to the code.** Sonnet's entire job here is to present the decision and record the
answer. Draft `docs/internal/health-audit/OWNER_DECISIONS_20260917.md` containing both
questions, the options below, and empty ruling fields for the owner to fill.

**Q1 options:** (a) add `aion_core/semantic_recall.py` to `sqlite_connect_allowed` and record
in the data contract that it is a rebuildable derived index, never a source of truth;
(b) refine the `anti-dup` rule to recognise a declared-derived marker, which is more work but
prevents future ambiguity; (c) move the index out of `aion_core` entirely.

**Q2 options:** (a) ratify as-is, recording that free-tier providers are not "external
account creation"; (b) ratify but require a standing approval card before any non-`PUBLIC`
class is ever permitted; (c) keep the module but leave it unreachable until Mac migration.

### Do not change
Everything. No code, no baseline, no gate.

### Verification commands
None. This task's output is a document and a decision.

### Completion criteria
The decisions file exists with both rulings filled in by the owner, dated and attributed.

### Stop and escalate if
Anyone proposes answering Q1 by widening `sqlite_connect_allowed` without also recording
*why* it is a derived index. That is how a gate quietly dies.

---

## TASK `TASK-004` — Execute the reconciling merge (DETAILED MERGE PLAN)

**Priority:** P1 · **Subsystem:** repo integrity · **Confidence:** 95% · **Depends on:**
TASK-001, TASK-002, TASK-003

### Problem
`main` and `integration` have diverged and neither is a superset. `main` is missing the four
owner modules and the audit docs; `integration` is missing six task PRs.

### Evidence, already proven by execution in the audit session
- `git merge-tree --write-tree origin/main origin/integration/consolidation-20260916`
  produced a clean tree ID with **no CONFLICT lines**.
- A real `git merge --no-ff` produced **zero conflicts**.
- The merged commit ran **550 tests, OK (1 skipped)**.
- `check_portability.py`: 0 violations, 3 known exceptions, **0 stale**, 55 files, portable.
- `./aion scan .`: clean.

This merge is known-good. Sonnet is reproducing a verified result, not discovering one.

### Root cause
Parallel integration on two branches with no recorded canonical.

### Objective
A single branch containing both histories, passing the full suite and every gate, ready for
the owner to merge into `main`. **Sonnet does not merge into `main` itself.**

### Allowed files
Only what the merge itself produces. Plus conflict resolution **if and only if** a conflict
appears that did not appear in the audit.

### Do not change
Do not rewrite history. Do not rebase. Do not squash. Do not force-push. Do not push to
`main`. Do not "tidy" anything the merge produces.

### Implementation instructions
1. `git fetch origin --prune`.
2. Confirm the inputs still match the audit:
   `git rev-parse origin/main` → expect `0720a92...`;
   `git rev-parse origin/integration/consolidation-20260916` → expect `db91548...`.
   **If either differs, STOP and escalate** — the audit evidence no longer applies.
3. `git checkout -B repair/reconcile-20260917 origin/main`.
4. Apply TASK-001 and TASK-002 commits onto this branch if not already present.
5. `git merge --no-ff origin/integration/consolidation-20260916` with a message naming this
   audit and stating that the merge reconciles the branch-role inversion.
6. `git status --short | grep -E '^(UU|AA|DU|UD)'` must return nothing. **If a conflict
   appears, STOP and escalate.** Do not guess through it; the audit proved there should be
   none, so a conflict means the inputs moved.
7. Apply the TASK-003 ruling exactly as the owner recorded it, no more.

### Required tests
No new tests. The merge must not change test count downward: expect **550** (or higher if
TASK-003 added any), with 1 skip.

### Verification commands
```
git status --short
python3 -m compileall -q aion_core bridges tests scripts
python3 -m unittest discover -s tests -t . -q
./aion scan .
python3 scripts/check_portability.py
python3 scripts/verify_authority.py anti-dup --base origin/main
python3 scripts/verify_authority.py strict --base origin/main --branch "$(git branch --show-current)"
```

### Completion criteria
Zero conflicts. Suite OK with at least 550 tests. Scan clean. Portability portable with
0 stale. `anti-dup` clean, or carrying only violations the owner explicitly ratified in
TASK-003. Nothing pushed yet.

### Rollback
Delete the local branch. Nothing was pushed, so rollback is free.

### Stop and escalate if
Either input SHA moved, any conflict appears, the test count drops below 550, any gate that
passed in the audit now fails, or the TASK-003 ruling turns out not to cover something the
merge actually requires.

---

## Not queued, and deliberately so

No task is raised for persistence, recovery, evidence gates, singleton locking, secret
handling or schema migration. All were checked and all are healthy. Inventing work there
would be manufacturing activity, which the auditor spec explicitly forbids.
