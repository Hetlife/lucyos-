# TR-C-01 — Archive batch: stale work artefacts and decided proposals

**Why:** Business artefacts from 2026-09-13 and inputs to already-decided architecture checks sit in the source tree (cleanup C-03, C-04, C-07).
**Current evidence:** `14_CLEANUP_REGISTER.md` rows C-03, C-04, C-07; grep shows no code references
**Executor:** DETERMINISTIC (git mv) + CLAUDE_CODE if a test references a moved file
**Scope:** `git mv work .lucy/archive/2026-09-13-work`; `git mv deploy/queues .lucy/archive/2026-09-17-deploy-queues`; `git mv taskcheck_web/preview.png docs/*_ARCHITECTURE_PROPOSAL.json skills/architecture-proposal.autonomy-growth.json .lucy/archive/2026-09-22-proposals/`; fix any test or doc that referenced them
**Do not touch:** `.lucy/authority/**`, `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`, any protected path without a recorded override; no third-party dependency; no new `aion_core` module; `deploy/**` is protected: moving `deploy/queues` needs the override `"TR-C-01": ["deploy/queues/**"]`
**Dependencies:** override for deploy/queues

## Steps
1. Grep for each path; move; run suite.

## Acceptance tests
- suite OK; `git status` clean
- full suite OK (count never drops), `./aion scan .`, `check_portability.py`, `verify_authority.py strict --base origin/main --branch <b>`, `anti-dup`, `check_boundaries.py` all exit 0; real exit codes in the report

**Security / rollback:** `git mv` back
**Deliverables:** PR
**Stop conditions:** a test depends on a moved file -> keep that file, report
**Fable review required?** NO
