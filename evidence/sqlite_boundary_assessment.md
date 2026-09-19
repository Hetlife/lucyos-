# SQLite Boundary Findings — S-48 follow-up

These findings are intentionally separate from S-46 and were not changed.

| File | Finding | Assessment | Action |
|---|---|---|---|
| `aion_core/tasks.py` | `import sqlite3` | Harmless existing type/API use. All connections go through the canonical `aion_core.db.connect()` store; it creates no second database. | Keep import or narrow the scanner rule to connection/schema use in a future task. |
| `scripts/runtime_inventory.py` | `import sqlite3` | Harmless read-only capability probe (`sqlite3.sqlite_version`); no connection or state. | Keep import or classify read-only stdlib probes separately in a future boundary-rule refinement. |

Neither finding is a duplicate state store, schema, or security exposure. The
current S-48 rule deliberately reports imports conservatively, so warning mode
is correct and strict mode is intentionally not promoted. No fix is included
in S-46.
