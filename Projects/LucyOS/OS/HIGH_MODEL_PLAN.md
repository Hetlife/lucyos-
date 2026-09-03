# High-Model Planning Packet

## Current objective

Restore and verify the supplied SEVAA Sales OS package under AION/LucyOS while
preserving local state, avoiding secrets, and keeping the system resumable.

## Ordered work partitions

1. **Deterministic intake** — inspect paths, hashes, archive contents, and existing
   project state.
2. **Safe staging** — extract to a dated staging directory; do not overwrite the
   existing project.
3. **Local verification** — create or reuse an isolated virtual environment, install
   only declared dependencies, run the package verification, and record results.
4. **Runtime smoke test** — start only the staged local app if verification permits;
   test health and documented public routes.
5. **AION state update** — write sanitized evidence to state files and update the
   checkpoint revision.
6. **Adversarial review** — inspect failures, secrets, persistence, and approval
   boundaries.
7. **External deployment** — separate approval-gated phase; do not begin implicitly.

## Local-model packets

The small/local lane may perform only the items in `LOW_TOKEN_QUEUE.md`. It may not
promote a staging directory, modify services, publish, push, spend, or handle secrets.

## Exit criteria

- package verification result is recorded;
- local smoke-test result is recorded;
- no secrets entered into project or checkpoint files;
- exact resume point is written;
- any external or consequential next step is listed in `APPROVALS_REQUIRED.md`.
