"""Optional, read-only usage telemetry adapters.

The canonical accounting remains ``model_usage``. External tools such as
ccusage may enrich Resource Governor decisions, but never overwrite canonical
cost records or trigger a model call themselves.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from . import db, security, util

META_KEY = "telemetry.ccusage.latest"
OBSERVED_KEY = "telemetry.ccusage.observed_at"


def _command(command: str | list[str] | None = None) -> list[str] | None:
    if isinstance(command, list):
        return command
    if isinstance(command, str) and command.strip():
        return shlex.split(command)
    configured = os.environ.get("AION_CCUSAGE_CMD", "").strip()
    if configured:
        return shlex.split(configured)
    found = shutil.which("ccusage")
    return [found] if found else None


def read_ccusage(*, command: str | list[str] | None = None, since: str | None = None,
                 timeout: int = 20, runner=subprocess.run) -> dict:
    """Return one ccusage JSON snapshot without mutating LucyOS state."""
    argv = _command(command)
    if not argv:
        return {"available": False, "ok": False, "reason": "ccusage not installed"}
    args = [*argv, "daily", "--json", "--offline"]
    if since:
        args += ["--since", since]
    try:
        proc = runner(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "ok": False, "reason": security.redact(str(exc))}
    if proc.returncode != 0:
        detail = security.redact((proc.stderr or proc.stdout or "ccusage failed").strip())
        return {"available": True, "ok": False, "reason": detail[-1000:]}
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"available": True, "ok": False, "reason": f"invalid ccusage JSON: {exc}"}
    totals = payload.get("totals") or {}
    return {
        "available": True,
        "ok": True,
        "source": "ccusage",
        "observed_at": util.now(),
        "totals": {
            "input_tokens": int(totals.get("inputTokens", 0) or 0),
            "output_tokens": int(totals.get("outputTokens", 0) or 0),
            "cache_creation_tokens": int(totals.get("cacheCreationTokens", 0) or 0),
            "cache_read_tokens": int(totals.get("cacheReadTokens", 0) or 0),
            "total_tokens": int(totals.get("totalTokens", 0) or 0),
            "reported_cost": float(totals.get("totalCost", 0) or 0),
        },
        "rows": len(payload.get("daily") or []),
    }


def refresh(**kwargs) -> dict:
    """Persist a bounded supplemental snapshot; never inserts model_usage rows."""
    snap = read_ccusage(**kwargs)
    if snap.get("ok"):
        db.set_meta(META_KEY, json.dumps(snap, sort_keys=True, separators=(",", ":")))
        db.set_meta(OBSERVED_KEY, snap["observed_at"])
        db.log_event("telemetry", "ccusage.refresh", str(snap["totals"]["total_tokens"]),
                     "supplemental only")
    return snap


def latest() -> dict:
    raw = db.get_meta(META_KEY, "") or ""
    if not raw:
        return {"available": bool(_command()), "ok": False, "reason": "no snapshot yet"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"available": bool(_command()), "ok": False, "reason": "stored snapshot invalid"}
