# TR-C-04 — Retire the Fable launch pack (after D-8)

**Why:** `fable.py` (678 lines), three CLI verbs and an `install.sh` step produce a bootstrap-era launch pack that this planning package replaces (cleanup C-06).
**Current evidence:** `aion_core/fable.py`, `cli.py` (`fable-pack`, `fable-ready`, `fable-phase`), `scripts/install.sh`, `directives/*`, `docs/MASTER_AI_*`
**Executor:** CLAUDE_CODE
**Scope:** remove `fable.py` + its tests + the 3 CLI verbs + the install line; archive `directives/` and `docs/MASTER_AI_*`; keep `handoff.py` (governor uses it); update README/START_HERE
**Do not touch:** `.lucy/authority/**`, `scripts/verify_authority.py`, `.github/workflows/lucyos-ci.yml`, any protected path without a recorded override; no third-party dependency; no new `aion_core` module; keep `governor.py` untouched
**Dependencies:** owner decision D-8

## Steps
1. Confirm `fable.*` has no other importer.
2. Remove, archive, run suite.

## Acceptance tests
- suite OK; `aion --help` has no fable verbs; `install.sh` runs
- full suite OK (count never drops), `./aion scan .`, `check_portability.py`, `verify_authority.py strict --base origin/main --branch <b>`, `anti-dup`, `check_boundaries.py` all exit 0; real exit codes in the report

**Security / rollback:** revert
**Deliverables:** PR
**Stop conditions:** D-8 not decided -> stop
**Fable review required?** YES
