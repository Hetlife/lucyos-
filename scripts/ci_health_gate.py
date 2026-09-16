#!/usr/bin/env python3
"""CI health gate: assert the checks a clean runner can honestly satisfy.

`aion health` exits non-zero when *any* check fails, and on a fresh machine
`secret_store` (owner creates it) and `backup` (none taken yet) are legitimately
absent. Requiring them would make CI permanently red, and permanently red
gates get ignored. This asserts the checks that must hold everywhere and
prints the rest so a human can still see them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REQUIRED = {"database", "task_queue", "errors", "budget", "learnrepo",
            "skill_registry", "sync_inbox", "disk"}


def main() -> int:
    from aion_core import db, health
    db.connect()
    report = health.run_all()
    checks = {c["name"]: c for c in report["checks"]}
    missing = sorted(REQUIRED - set(checks))
    failing = sorted(n for n in REQUIRED if n in checks and not checks[n]["ok"])
    for c in report["checks"]:
        flag = "REQ " if c["name"] in REQUIRED else "info"
        print(f"{'OK  ' if c['ok'] else 'FAIL'} {flag} {c['name']}: {c['detail']}")
    if missing or failing:
        print(json.dumps({"missing_required": missing, "failing_required": failing}))
        return 1
    print("health gate ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
