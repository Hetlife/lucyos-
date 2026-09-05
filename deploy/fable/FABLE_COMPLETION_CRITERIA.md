# FABLE COMPLETION CRITERIA — PHASE 2 (ON MACHINE)

The session is DONE only when all of the following hold and each is backed by a
command that was actually run:

1. `python3 -m pytest tests -q` (or `python3 -m unittest discover tests`) passes.
2. `aion health --deep` reports healthy, or every failing check has an open task
   with a named root cause.
3. `aion boot` completes and prints a next action that is genuinely the highest
   value item, not a stale one.
4. Every task moved to DONE carries evidence in its `evidence` field.
5. Every Tier-3 action encountered has an approval row, with everything up to the
   boundary already prepared.
6. `aion scan .` reports clean.
7. `FABLE_HANDOFF.md` and `FABLE_SESSION_LOG.md` are updated with real spend.
8. `aion checkpoint` has been run with the true next action.

Anything not meeting its criterion is PARTIAL, BLOCKED or FAILED — never DONE.
