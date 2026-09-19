# S-47 Architecture Decision — dedicated `aion_core.verify`

**Status:** Fable-ratified candidate; protected owner merge pending; canonical baseline unchanged

## Decision

Keep `aion_core/verify.py` as a dedicated governance module for the machine
acceptance command `aion verify`. Do not move it into an existing module.

## Evidence reviewed

- `health.py` owns individual runtime probes and `run_all()`; it does not own
  acceptance tiers, exit semantics, or machine capability discovery.
- `host/` owns platform adaptation; `verify.py` calls its public adapter and
  does not duplicate platform branching.
- `worker.py` owns execution capability reporting; `verify.py` consumes it and
  never schedules work or changes state.
- `cli.py` owns argument parsing/output dispatch; `verify.py` owns the
  reusable verdict/report policy and is independently unit-testable.
- `scripts/verify_authority.py` is a repository gate, not an importable
  runtime acceptance API. Reusing it would couple runtime verification to the
  authority verifier and duplicate CLI/process behavior.

## Boundary and dependency review

`verify.py` depends only on existing `config`, `health`, `host`, `util`, and
`worker` seams plus Python standard-library measurement APIs. It introduces no
database, queue, scheduler, secret store, daemon, network listener, or new
state. The governance manifest is its single owner.

## Alternatives rejected

1. **Extend `health.py`:** would conflate low-level health probes with the
   machine-arrival classification (`READY`, `SETUP_REQUIRED`, `BROKEN`) and
   make fresh-machine acceptance semantics part of every health caller.
2. **Extend `worker.py`:** would put read-only machine acceptance beside
   command execution and capability routing, increasing coupling and risk.
3. **Put policy in `cli.py`:** would make the policy unavailable to other
   callers and turn the interface layer into a governance owner.
4. **Reuse `scripts/verify_authority.py`:** that script verifies repository
   change authority; it does not measure host/runtime readiness.

## Verification and rollback

- S-47 focused tests and integrated tests pass; the combined branch has
  `aion verify --json` verdict `READY`.
- Portability, secret scan, strict scope, and diff checks pass.
- Rollback is one revert of S-47; S-49 remains independently revertible.
- The remaining anti-duplication failure is intentional: the Fable baseline
  has not yet ratified this new core module in `aion_core_modules`.

## Ratification record

Fable ratification candidate `HIGH_MODEL_BASELINE.json` adds exactly one
allowlist entry, `verify`, under `aion_core_modules`. No protected paths,
authority rules, task overrides, or gate behavior are weakened. The candidate
must be merged through the protected owner process before a PR based on the
old canonical baseline can pass the base-read anti-duplication gate.
