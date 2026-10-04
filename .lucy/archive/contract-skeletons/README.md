# Contract skeletons (archived)

`guardian.py`, `tempworker.py`, `intake.py` and `sync_outbox.py`, with their tests, were built as contract skeletons (S-13, S-15..S-17) and never gained a runtime caller (ISSUE-033). Archived by TR-C-02; they are not on the import path and `unittest discover -s tests` does not collect them. The `sync_outbox` table in `aion_core/db.py` stays (schema, harmless). Restore with `git mv` back to `aion_core/` and `tests/`, and re-add the files to the module manifests.
