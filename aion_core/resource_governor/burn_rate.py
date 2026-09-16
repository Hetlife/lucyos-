"""Rolling burn rate, computed locally from snapshot history (directive section 22).

Every call to `observability.snapshot(persist=True)` appends one row per
provider to `resource_snapshots`.  This module never talks to a network; it
only ever compares rows already stored, so a burn rate is either derived from
at least two real observations or reported as unavailable — never invented
from a single data point.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .. import db

INTERVALS_MINUTES = {"5m": 5, "15m": 15, "1h": 60}


def _parse(ts: str) -> datetime:
    d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def recent_snapshots(provider: str, minutes: int) -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    return db.connect().execute(
        "SELECT * FROM resource_snapshots WHERE provider=? AND at >= ? ORDER BY at",
        (provider, cutoff)).fetchall()


def rate_for_window(provider: str, window: str) -> dict:
    """tokens/minute and quota-pct/minute over one window, or None if insufficient data."""
    minutes = INTERVALS_MINUTES.get(window)
    if minutes is None:
        raise ValueError(f"unknown window {window!r}; use one of {list(INTERVALS_MINUTES)}")
    rows = recent_snapshots(provider, minutes)
    known = [r for r in rows if r["confidence"] != "UNKNOWN"]
    if len(known) < 2:
        return {"window": window, "tokens_per_minute": None, "quota_pct_per_minute": None,
                "samples": len(known)}
    first, last = known[0], known[-1]
    elapsed_min = max((_parse(last["at"]) - _parse(first["at"])).total_seconds() / 60.0, 0.01)

    tokens_per_minute = None
    a = (first["input_tokens"] or 0) + (first["output_tokens"] or 0)
    b = (last["input_tokens"] or 0) + (last["output_tokens"] or 0)
    if b >= a:
        tokens_per_minute = round((b - a) / elapsed_min, 2)

    quota_pct_per_minute = None
    if first["quota_used_pct"] is not None and last["quota_used_pct"] is not None:
        delta = last["quota_used_pct"] - first["quota_used_pct"]
        if delta >= 0:
            quota_pct_per_minute = round(delta / elapsed_min, 4)

    return {"window": window, "tokens_per_minute": tokens_per_minute,
            "quota_pct_per_minute": quota_pct_per_minute, "samples": len(known)}


def best_estimate(provider: str) -> dict:
    """Prefer the shortest window with enough samples — most responsive to a recent spike."""
    for window in ("5m", "15m", "1h"):
        rate = rate_for_window(provider, window)
        if rate["samples"] >= 2:
            return rate
    return {"window": None, "tokens_per_minute": None, "quota_pct_per_minute": None, "samples": 0}


def minutes_to_reset(reset_at: str | None) -> float | None:
    if not reset_at:
        return None
    try:
        target = _parse(reset_at)
    except ValueError:
        return None
    delta = (target - datetime.now(timezone.utc)).total_seconds() / 60.0
    return max(delta, 0.0)
