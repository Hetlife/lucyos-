# TR-C-02 — Archive the four unreachable contract-skeleton modules

**STATUS: PR open.**
**Why:** `guardian.py`, `tempworker.py`, `intake.py`, `sync_outbox.py` have no runtime caller (ISSUE-033); they cost reading and manifest upkeep.
**Current evidence:** EV-DEAD-MODULES; module manifests; baseline `aion_core_modules`
**Executor:** CLAUDE_CODE
**Scope:** move the four modules and their tests to `.lucy/archive/contract-skeletons/`; update `.lucy/architecture/modules/*.json` owned_files and `tests/test_module_manifests.py` fixtures; remove any CLI stub that only calls them (check `aion ingest` uses `packets`, `aion intake` if present); leave baseline allowlist entries (harmless)
**Do not touch:** `.lucy/authority/**`, `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`, any protected path without a recorded override; no third-party dependency; no new `aion_core` module
**Dependencies:** none

## Steps
1. Confirm zero importers with `grep`.
2. Move, fix manifests, run suite and gates.

## Acceptance tests
- suite count drops only by the archived tests; manifests validate
- full suite OK (count never drops), `./aion scan .`, `check_portability.py`, `verify_authority.py strict --base origin/main --branch <b>`, `anti-dup`, `check_boundaries.py` all exit 0; real exit codes in the report

**Security / rollback:** revert
**Deliverables:** PR
**Stop conditions:** a runtime import appears -> keep that module
**Fable review required?** NO
