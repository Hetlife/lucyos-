#!/usr/bin/env python3
"""Create the parent directory for a marker file and write 'ok' into it.

Used by the deterministic plan-worker test fixture so a single argv-safe
command (no `&&`/`>` shell operators) can do what
`mkdir -p <dir> && echo ok > <file>` used to do.  See docs/architect's LQ-01
for why compound shell commands are refused by aion_core.worker.check_command.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: touch_marker.py <path>", file=sys.stderr)
        return 2
    target = Path(argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
