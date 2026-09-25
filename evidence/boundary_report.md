# Boundary scan

{
  "violations": [
    {
      "path": "aion_core/tasks.py",
      "rule": "sqlite_import",
      "line": 6,
      "detail": "sqlite3 import outside the ratified allowlist"
    },
    {
      "path": "scripts/runtime_inventory.py",
      "rule": "sqlite_import",
      "line": 19,
      "detail": "sqlite3 import outside the ratified allowlist"
    }
  ],
  "exceptions": [],
  "stale_exceptions": [],
  "strict": false,
  "ok": false
}
