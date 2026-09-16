"""Turn normalized telemetry into one of the resource states (directive section 9).

Thresholds alone are not enough per the directive: a state also considers
reset time and burn rate, not just the instantaneous percentage.  This module
computes the percentage-based `base_state` first, then escalates it by one
level (never de-escalates) when the burn rate says the threshold below will
be crossed before the provider's reset time.
"""
from __future__ import annotations

from . import flags, schema

_ORDER = ("EXHAUSTED", "CRITICAL", "CONSTRAINED", "CONSERVE", "NORMAL", "AVAILABLE")


def base_state(resource: dict) -> str:
    """Percentage-only classification.  UNKNOWN stays UNKNOWN — never a guess."""
    if not schema.is_known(resource):
        return "UNKNOWN"
    pct = schema.remaining_pct(resource)
    if pct is None:
        return "UNKNOWN"
    if pct < flags.threshold("CRITICAL"):
        return "EXHAUSTED"
    if pct < flags.threshold("CONSTRAINED"):
        return "CRITICAL"
    if pct < flags.threshold("CONSERVE"):
        return "CONSTRAINED"
    if pct < flags.threshold("NORMAL"):
        return "CONSERVE"
    if pct < flags.threshold("AVAILABLE"):
        return "NORMAL"
    return "AVAILABLE"


def classify(resource: dict, *, minutes_to_reset: float | None = None,
             tokens_per_minute: float | None = None) -> str:
    """Full classification: percentage, escalated by burn-rate-vs-reset risk."""
    state = base_state(resource)
    if state in ("UNKNOWN", "EXHAUSTED"):
        return state
    if minutes_to_reset is None or not tokens_per_minute or tokens_per_minute <= 0:
        return state
    pct = schema.remaining_pct(resource)
    if pct is None:
        return state
    # Rough same-unit projection: how many more "percent" of burn happen
    # before reset, using tokens/minute against the resource's own limit
    # when known, otherwise this signal is skipped rather than guessed.
    limit = (resource.get("context") or {}).get("limit_tokens")
    if not limit:
        return state
    projected_pct_used = (tokens_per_minute * minutes_to_reset / limit) * 100.0
    if projected_pct_used >= pct:
        idx = _ORDER.index(state)
        return _ORDER[max(idx - 1, 0)]
    return state


def overall(resources: dict[str, dict]) -> str:
    """The most-constrained known state across every tracked provider."""
    known = [classify(r) for r in resources.values() if schema.is_known(r)]
    if not known:
        return "UNKNOWN"
    return min(known, key=_ORDER.index)
