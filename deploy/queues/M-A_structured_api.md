# EXECUTION QUEUE — MILESTONE M-A: STRUCTURED DATA API

Compiled by the architect session. Executors: read only the files each task
names. Do not read the whole repository.

## Architectural decision (made, not open for re-litigation)

The interface today is a **text-dump dashboard**: `bridges/http_server.py` maps
every endpoint to `aion_core/reports.py`, which returns preformatted *strings*.
`web/app.js` renders them into `<pre>` blocks. That is why the UI cannot show
projects, cost breakdowns, real-vs-simulated money, or per-item cards — the data
never arrives as data.

Meanwhile the structured layer **already exists**: `metrics.money()`,
`metrics.budget_status()`, `tasks.ready()/blocked()/counts()`,
`approvals.pending()`, `health.run_all()`, `milestones.check()` all return
dicts/lists. The `project` column already exists on `tasks`, `finance` and
`deliveries`, with indexes.

Decision: add a thin **data assembly module** (`aion_core/api.py`) and serve it
at versioned `/api/v1/*` endpoints, **alongside** the existing text endpoints,
which stay untouched so the working UI does not regress. No canonical state
changes, no loop changes, no schema changes. Additive and reversible.

---

## TASK A1

TASK_ID: M-A.1
TITLE: Add aion_core/api.py — structured data assembly
OBJECTIVE: One module returning JSON-safe dicts for the interface, assembled
from existing structured functions. No HTTP, no text formatting, no new state.
WHY_IT_MATTERS: Every other interface feature is blocked behind data being data.
ASSIGNED_CLASS: B
PRIORITY: P0
DEPENDENCIES: none
FILES_TO_INSPECT:
- aion_core/metrics.py (money, budget_status, record_usage schema)
- aion_core/tasks.py (ready, blocked, counts, value)
- aion_core/approvals.py (pending)
- aion_core/health.py (run_all)
- aion_core/milestones.py (check)
- aion_core/resume.py (load)
FILES_ALLOWED_TO_CHANGE:
- aion_core/api.py (new)
- tests/test_api.py (new)
CURRENT_STATE: No such module. Interface reads reports.py text only.
EXACT_ACTIONS:
Implement exactly four functions, all returning plain JSON-serialisable dicts
(no sqlite3.Row objects — convert with dict()):

1. `system_snapshot() -> dict`
   keys: `as_of` (util.now()), `healthy` (bool from health.run_all()),
   `checks` (list of {name, ok, detail}), `bottleneck` (resume.load()),
   `next_action`, `task_counts` (tasks.counts()), `governor`
   (metrics.budget_status()["governor"]), `paused` (db meta if present else False).

2. `money_split() -> dict`
   keys: `real` {revenue_inr, cost_inr, net_inr} using ONLY finance rows with
   stage='ACTUAL'; `simulated` {revenue_inr, cost_inr, net_inr} for every other
   stage, summed separately; `mission_target_inr` (100000.0);
   `milestones` (milestones.check()). The two must never be added together
   anywhere in this function.

3. `projects() -> list[dict]`
   One entry per distinct `project` value across tasks/finance/deliveries.
   keys per entry: `project`, `task_counts` (by status), `open_tasks`,
   `real_net_inr` (ACTUAL only), `simulated_net_inr`, `last_activity_at`.

4. `costs() -> dict`
   keys: `today_inr`, `month_inr`, `by_model` (list of {model, model_class,
   calls, cost_inr}), `by_class`, `governor`, `strong_model_pct`.
   Source: the `model_usage` table plus metrics.budget_status().

Add `tests/test_api.py` covering, with real rows written through the normal
APIs (not raw SQL inserts where an API exists):
- money_split keeps a FORECAST row out of `real` and inside `simulated`
- projects() separates two projects' tasks and money correctly
- costs() sums only what was recorded
- system_snapshot() is JSON-serialisable: `json.dumps(system_snapshot())` works
SUCCESS_CRITERIA:
- `python3 -m unittest discover -s tests -t . -q` passes with the new tests
- `json.dumps()` succeeds on all four function results
- no changes to any file outside the two listed
VALIDATION_COMMANDS:
```
python3 -m unittest discover -s tests -t . -q
python3 -c "import json,sys;sys.path.insert(0,'.');from aion_core import api;[json.dumps(f()) for f in (api.system_snapshot,api.money_split,api.projects,api.costs)];print('JSON OK')"
git diff --check
./aion scan .
```
DO_NOT_DO: Do not modify reports.py, http_server.py, web/, db.py schema, or any
loop/worker file. Do not add third-party dependencies. Do not merge real and
simulated money in any return value.
EXPECTED_OUTPUT: aion_core/api.py + tests/test_api.py, committed.
RESULT_PACKET_FORMAT:
```
TASK: M-A.1
STATUS: DONE|PARTIAL|FAILED
TESTS: <literal "Ran N tests ... OK" line>
JSON_CHECK: <literal output of the json.dumps command>
SCAN: <literal aion scan output>
COMMIT: <sha>
NOTES: <anything surprising, else "none">
```

---

## TASK A2

TASK_ID: M-A.2
TITLE: Serve /api/v1/* structured endpoints
OBJECTIVE: Expose api.py over the existing authenticated HTTP server without
touching the endpoints the current UI depends on.
WHY_IT_MATTERS: The UI cannot consume data that is not served.
ASSIGNED_CLASS: B
PRIORITY: P0
DEPENDENCIES: M-A.1 (must be merged first)
FILES_TO_INSPECT:
- bridges/http_server.py (auth pattern, existing route table, redaction)
- tests/test_http_interface.py (existing HTTP test style — reuse it)
FILES_ALLOWED_TO_CHANGE:
- bridges/http_server.py
- tests/test_http_v1.py (new)
CURRENT_STATE: Route table maps 8 paths to reports.py text functions. Bearer
token auth via constant-time compare. Approvals POST via /api/command.
EXACT_ACTIONS:
- Add GET routes: `/api/v1/snapshot`, `/api/v1/money`, `/api/v1/projects`,
  `/api/v1/costs`, mapped to the four api.py functions.
- Same auth as existing routes: unauthenticated request returns 401.
- Same redaction path as existing responses — every payload passes through
  `security.redact` before it is written.
- Content-Type: application/json.
- Leave all existing routes and their behaviour exactly as they are.
Add `tests/test_http_v1.py` proving, against a real loopback server:
- each of the four returns 200 and valid JSON with a bearer token
- each returns 401 without one
- an existing text endpoint still returns its old text (no regression)
SUCCESS_CRITERIA: all four endpoints serve valid JSON authenticated, 401
unauthenticated, existing endpoints unchanged, full suite green.
VALIDATION_COMMANDS:
```
python3 -m unittest discover -s tests -t . -q
git diff --check
./aion scan .
```
DO_NOT_DO: Do not change the auth mechanism, do not bind to anything but
loopback, do not remove or rename existing routes, do not touch web/.
EXPECTED_OUTPUT: four working v1 endpoints + tests, committed.
RESULT_PACKET_FORMAT: same shape as M-A.1, plus:
```
ENDPOINTS: <curl status codes observed for all four, authed and unauthed>
```

---

## TASK A3

TASK_ID: M-A.3
TITLE: Correct stale test counts in documentation
OBJECTIVE: Docs claim 86, 140 and 159 tests in three places. The real number is
what the suite prints. Make every stated count match reality.
WHY_IT_MATTERS: Future agents trust these numbers and cannot tell a doc error
from a real regression.
ASSIGNED_CLASS: DET
PRIORITY: P3
DEPENDENCIES: none
FILES_TO_INSPECT: README.md, docs/MASTER_AI_HANDOFF.md, docs/DRIVE_BRIDGE_RESUME.md
FILES_ALLOWED_TO_CHANGE: the same three files
CURRENT_STATE: README says "86 tests"; handoff says 140; Drive resume says 159.
EXACT_ACTIONS: Run the suite, take the real count, update each stated figure to
it. Where a doc describes a past verification, keep it historical and dated
rather than rewriting history — only fix figures presented as current.
SUCCESS_CRITERIA: no stated current test count disagrees with the suite output.
VALIDATION_COMMANDS:
```
python3 -m unittest discover -s tests -t . -q
grep -rnE "[0-9]+ (unit )?tests" README.md docs/MASTER_AI_HANDOFF.md docs/DRIVE_BRIDGE_RESUME.md
```
DO_NOT_DO: Do not touch code. Do not rewrite historical verification records.
EXPECTED_OUTPUT: three doc files corrected, committed.
RESULT_PACKET_FORMAT: same shape as M-A.1.

---

## TASK A4

TASK_ID: M-A.4
TITLE: Assess (do not merge) the unmerged Fable-branch assets
OBJECTIVE: Decide whether `aion_core/experiments.py` and `aion_core/money_path.py`
on `claude/fable-deploy-setup-mc5nr6` can be cherry-picked onto main cleanly.
WHY_IT_MATTERS: Those two modules implement experiment verdicts from ACTUAL
revenue and an ordered "steps to real money" path — directly useful to the
interface. They are stranded on a branch nothing merges from.
ASSIGNED_CLASS: B
PRIORITY: P2
DEPENDENCIES: none
FILES_TO_INSPECT (read-only, on that branch):
- aion_core/experiments.py, aion_core/money_path.py
- their tests
- main's aion_core/metrics.py and deliveries.py (conflict surface)
FILES_ALLOWED_TO_CHANGE: deploy/queues/M-A.4_assessment.md (new, report only)
CURRENT_STATE: Branch has 2 commits past my old branch; main diverged with
deliveries.py/payer_id work that may overlap conceptually.
EXACT_ACTIONS: In a scratch worktree, attempt `git cherry-pick -n` of the two
modules' commit onto main. Record: does it apply, what conflicts, do their tests
pass on main, does anything duplicate main's deliveries/finance logic. Write the
findings and a recommended disposition. **Make no change to main. Do not merge.**
SUCCESS_CRITERIA: a written assessment naming exact conflicting hunks (if any)
and a clear MERGE / ADAPT / DROP recommendation with reasons.
VALIDATION_COMMANDS:
```
git status --short   # must show only the new assessment file
```
DO_NOT_DO: Do not merge, do not cherry-pick onto main for real, do not modify
aion_core/ or delete branches.
EXPECTED_OUTPUT: deploy/queues/M-A.4_assessment.md
RESULT_PACKET_FORMAT: same shape as M-A.1, plus `RECOMMENDATION: MERGE|ADAPT|DROP`.

---

## PARALLELIZATION

- **M-A.1** first, alone (foundation).
- **M-A.3** and **M-A.4** are PARALLEL_SAFE with everything — different files,
  no code overlap. Start them immediately alongside M-A.1.
- **M-A.2** starts only after M-A.1 is merged.

## MILESTONE ACCEPTANCE (M-A)

All of these, with literal command output as evidence:
1. Full suite green, count strictly greater than the pre-M-A count.
2. `json.dumps()` succeeds on all four api.py functions.
3. All four `/api/v1/*` endpoints: 200 + valid JSON with token, 401 without.
4. At least one existing text endpoint returns its original text unchanged.
5. `./aion scan .` clean; `git diff --check` clean.
6. A FORECAST finance row provably appears in `simulated` and never in `real`.

## HIGH-TOKEN REVIEW TRIGGER

Escalate to the architect session when **either**:
- all four result packets report DONE with the evidence above (→ milestone
  review, then compile the M-B queue), **or**
- any single task reports FAILED twice on the same root cause (→ systemic
  diagnosis, not another retry).

Do not escalate for routine choices inside a task.
