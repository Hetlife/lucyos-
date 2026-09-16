# APScheduler — extracted patterns only

Official material consulted: APScheduler master user guide and API reference, limited to
Task/Schedule/Job semantics, misfire grace, persistent state, acquisition leases, cleanup and
SQLite cautions.

## What we learned
- Keep **task**, **schedule**, and concrete **job/run** as separate concepts.
- A due schedule/job should be claimed with an expiring lease so abandoned work becomes recoverable.
- `misfire_grace_time` is a bounded tolerance for late execution, not a reason to silently lose work.
- Persistent scheduler state needs explicit IDs and careful serialization; expired results/leases need cleanup.

## Pattern LucyOS copies
- Separate task/schedule/run records.
- `lease_owner` + `lease_until` and deterministic recovery.
- Grace/misfire status and explicit next-run calculation.

## What LucyOS does not import
- APScheduler package/runtime, serializers, event broker, distributed scheduler/data-store layer.

## Known cautions
- APScheduler v4 documentation describes a pre-release line; LucyOS does not depend on its internals.
- APScheduler documentation warns against SQLite when a data store is shared by multiple schedulers.
- LucyOS pilot is therefore intentionally single-node and SQLite-native.
