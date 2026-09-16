#!/usr/bin/env python3
"""Sanitized runtime inventory: what a host actually provides, with nothing
sensitive in it, so a Mac or a second Linux box migration is evidence-based
rather than guessed at.

Never emits a hostname, username, absolute home path, IP address, an env
value, or a secret. Never makes a network call. Never branches on platform
outside aion_core/host -- where a platform-specific fact is needed (scheduler
kind, service activity), this calls the S-10 host adapter instead of
re-implementing platform detection here; if that adapter isn't available on
this checkout, the corresponding fields are simply omitted, not guessed.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import sqlite3
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Presence only -- never the resolved path, which can embed a username or
# home directory on some installs (e.g. a pip --user install under
# /home/<user>/.local/bin).
_PROBE_TOOLS = ("git", "python3", "sqlite3", "rclone", "ollama",
                "systemctl", "launchctl", "bash")


def _tool_presence() -> dict:
    return {tool: shutil.which(tool) is not None for tool in _PROBE_TOOLS}


def _host_adapter_facts() -> dict:
    """Best-effort: only populated when aion_core.host (S-10) is present and
    usable on this checkout. Never a local re-implementation of the same
    platform branching."""
    try:
        from aion_core import host
        adapter = host.current()
        return {
            "host_adapter_name": adapter.name(),
            "scheduler_kind": adapter.scheduler_kind(),
        }
    except Exception:
        # Best-effort only: any failure (missing module, stray empty package,
        # adapter internals changing) means this field is omitted, never guessed.
        return {}


def collect() -> dict:
    disk = shutil.disk_usage(str(REPO))
    inventory = {
        "python_version": ".".join(str(v) for v in sys.version_info[:3]),
        "python_implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "disk_total_gb": round(disk.total / 1e9, 2),
        "disk_free_gb": round(disk.free / 1e9, 2),
        "sqlite_version": sqlite3.sqlite_version,
        "has_fts5": _has_fts5(),
        "has_gzip_tar_support": _has_gzip_tar_support(),
        "tooling": _tool_presence(),
    }
    inventory.update(_host_adapter_facts())
    return inventory


def _has_fts5() -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()


def _has_gzip_tar_support() -> bool:
    return hasattr(tarfile, "open")


def render(inventory: dict) -> str:
    return json.dumps(inventory, indent=2, sort_keys=True)


def main(argv=None) -> int:
    sys.stdout.write(render(collect()) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
