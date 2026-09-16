"""Claude telemetry adapter.

There is no documented Anthropic API this codebase is willing to depend on for
critical operation, and OAuth credentials must never be handed to a
third-party monitoring tool (directive sections 6 and 27).  So this adapter
reads one thing only: an optional local JSON file the owner (or a future
LearnRepo-approved, sandboxed exporter) can drop on disk.  Its path is
configurable and nothing about it is fetched from the network.

Expected file shape (all keys optional — read whatever is present):

    {
      "updated_at": "2026-09-16T04:00:00+00:00",
      "model": "claude-sonnet-5",
      "context": {"used_tokens": 12000, "limit_tokens": 200000},
      "five_hour": {"used_pct": 41.0, "reset_at": "2026-09-16T09:00:00+00:00"},
      "seven_day": {"used_pct": 12.0, "reset_at": "2026-09-22T00:00:00+00:00"},
      "observed_usage": {"input_tokens": 5000, "output_tokens": 1200,
                          "cache_read_tokens": 0, "cache_write_tokens": 0}
    }

If the file is absent, unreadable or missing every field, the result is
UNKNOWN — never a guessed number.  A quota window preference (5h vs 7d) picks
whichever window is more constraining, since either can bind first.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import schema

STALE_AFTER = timedelta(minutes=15)


def telemetry_path() -> Path | None:
    raw = os.environ.get("AION_CLAUDE_TELEMETRY_FILE", "")
    return Path(raw).expanduser() if raw else None


def read(*, path: Path | None = None) -> dict:
    path = path if path is not None else telemetry_path()
    result = schema.empty_resource("claude", source="local_telemetry_file")
    if path is None or not path.exists():
        result["source"] = "no_telemetry_file_configured"
        return result

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["source"] = f"telemetry_file_unreadable:{type(exc).__name__}"
        return result
    if not isinstance(raw, dict):
        result["source"] = "telemetry_file_malformed"
        return result

    result["model"] = raw.get("model")
    ctx = raw.get("context") or {}
    used = ctx.get("used_tokens")
    limit = ctx.get("limit_tokens")
    if isinstance(used, (int, float)) and isinstance(limit, (int, float)) and limit > 0:
        remaining = max(limit - used, 0)
        result["context"] = {
            "used_tokens": used, "limit_tokens": limit, "remaining_tokens": remaining,
            "used_pct": round(100.0 * used / limit, 2),
        }

    window_name, window = _binding_window(raw)
    if window is not None:
        used_pct = window.get("used_pct")
        result["quota"] = {
            "window": window_name,
            "used_pct": used_pct,
            "remaining_pct": round(100.0 - used_pct, 2) if isinstance(used_pct, (int, float)) else None,
            "reset_at": window.get("reset_at"),
        }

    ou = raw.get("observed_usage") or {}
    if ou:
        result["observed_usage"] = {
            "input_tokens": ou.get("input_tokens"),
            "output_tokens": ou.get("output_tokens"),
            "cache_read_tokens": ou.get("cache_read_tokens"),
            "cache_write_tokens": ou.get("cache_write_tokens"),
        }

    updated_at = raw.get("updated_at")
    result["updated_at"] = updated_at
    have_any = (result["context"]["used_pct"] is not None
                or result["quota"]["used_pct"] is not None)
    if not have_any:
        result["source"] = "telemetry_file_had_no_usable_fields"
        return result

    result["confidence"] = _confidence_for(updated_at)
    return result


def _binding_window(raw: dict):
    """Pick whichever of the 5h/7d windows is more constraining right now."""
    candidates = [("5h", raw.get("five_hour")), ("7d", raw.get("seven_day"))]
    known = [(name, w) for name, w in candidates
             if isinstance(w, dict) and isinstance(w.get("used_pct"), (int, float))]
    if not known:
        return None, None
    return max(known, key=lambda item: item[1]["used_pct"])


def _confidence_for(updated_at) -> str:
    if not updated_at:
        return "LOCAL_OBSERVED"
    try:
        stamp = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
    except ValueError:
        return "LOCAL_OBSERVED"
    age = datetime.now(timezone.utc) - stamp
    return "OFFICIAL_CURRENT" if age <= STALE_AFTER else "OFFICIAL_STALE"
