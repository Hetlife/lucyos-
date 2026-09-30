# TR-I-01 — Control Center: task detail, agents view, project-scoped command

**Why:** The PWA lacks task evidence detail, an agents/executors view and scoped work input (16_).
**Current evidence:** EV-UI; `api.py`, `web/app.js`, `router.py` grammar, `aion why`
**Executor:** CLAUDE_CODE
**Scope:** `api.py`: `task_detail(task_id)` (reuses `memory.why` + task row + events), `agents()` (from `agents.all_agents` + `worker.capability_report`); `http_server.py`: `/api/v1/task/<id>`, `/api/v1/agents`; `web/`: task card expands to detail; agents section; command box accepts `add <project>: <title>` only if the router grammar gains it under TR-5-03, else `task-add` via `/api/v1/task-add` POST calling `tasks.create` with redaction; tests in `test_http_v1`
**Do not touch:** `.lucy/authority/**`, `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`, any protected path without a recorded override; no third-party dependency; no new `aion_core` module; no new dependency; no build step; loopback binding unchanged; `router.py` untouched
**Dependencies:** none (project scoping waits for TR-5-03)

## Steps
1. Read models first with tests.
2. Minimal DOM additions; keep offline queue behaviour.

## Acceptance tests
- new endpoints tested; page renders without console errors in the existing Playwright smoke if present, else manual screenshot in the PR
- full suite OK (count never drops), `./aion scan .`, `check_portability.py`, `verify_authority.py strict --base origin/main --branch <b>`, `anti-dup`, `check_boundaries.py` all exit 0; real exit codes in the report

**Security / rollback:** revert
**Deliverables:** PR `task/TR-I-01-control-center-detail`
**Stop conditions:** —
**Fable review required?** NO
