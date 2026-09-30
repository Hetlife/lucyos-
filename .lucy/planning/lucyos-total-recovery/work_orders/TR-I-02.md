# TR-I-02 — Control Center: machines, routing, sessions, search

**Why:** Owner cannot see machines, executor routing, session logs or memory search without a terminal (16_).
**Current evidence:** `health.machine()`, `routing-report`, `sessions.index`, `memory.search`, `meta.host_role`
**Executor:** CLAUDE_CODE
**Scope:** `api.py` + `http_server.py` + `web/`: `/api/v1/machines` (this host + any census JSON pushed under `<AION_HOME>/MACHINES/*.json`), `/api/v1/routing`, `/api/v1/sessions?limit=`, `/api/v1/search?q=` (redacted); sections in the page; tests
**Do not touch:** `.lucy/authority/**`, `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`, any protected path without a recorded override; no third-party dependency; no new `aion_core` module
**Dependencies:** TR-I-01

## Steps
1. Read models + tests; page sections.

## Acceptance tests
- endpoints tested
- full suite OK (count never drops), `./aion scan .`, `check_portability.py`, `verify_authority.py strict --base origin/main --branch <b>`, `anti-dup`, `check_boundaries.py` all exit 0; real exit codes in the report

**Security / rollback:** revert
**Deliverables:** PR
**Stop conditions:** —
**Fable review required?** NO
