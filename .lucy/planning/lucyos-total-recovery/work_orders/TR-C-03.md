# TR-C-03 — Consolidate skill-system design texts

**Why:** Seven Q00x design texts (40 KB) describe a rolled-out system; only the anti-duplication rules are still consulted (cleanup C-08).
**Current evidence:** `docs/skill-system/*.txt`; `START_HERE.md` item 7
**Executor:** CLAUDE_CODE (LOCAL_MODEL may draft the condensed doc)
**Scope:** `docs/ARCHITECTURE_GUARD.md` (Q006 rules, condensed), archive Q000–Q005 under `.lucy/archive/skill-system/`, fix `START_HERE.md` item 7 and `architecture.py` docstring links
**Do not touch:** `.lucy/authority/**`, `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`, any protected path without a recorded override; no third-party dependency; no new `aion_core` module
**Dependencies:** none

## Steps
1. Draft, review, move, fix links (`duplication_scan.py` dead-link check must stay clean).

## Acceptance tests
- `scripts/duplication_scan.py` reports no dead links
- full suite OK (count never drops), `./aion scan .`, `check_portability.py`, `verify_authority.py strict --base origin/main --branch <b>`, `anti-dup`, `check_boundaries.py` all exit 0; real exit codes in the report

**Security / rollback:** revert
**Deliverables:** PR
**Stop conditions:** —
**Fable review required?** NO
