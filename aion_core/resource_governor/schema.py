"""The normalized resource-state schema every provider adapter returns.

Nothing outside `providers/` may depend on a provider-specific JSON shape.
Every adapter, however it reads its telemetry, returns exactly this shape so
the rest of the Resource Governor (and the rest of LucyOS) only ever deals
with one format.

CONFIDENCE is the single most important field.  It says how much to trust the
numbers next to it — and UNKNOWN must stay UNKNOWN.  Nothing here ever turns
"we don't know" into a zero or a fabricated number.
"""
from __future__ import annotations

CONFIDENCE = ("OFFICIAL_CURRENT", "OFFICIAL_STALE", "LOCAL_OBSERVED", "LOCAL_ESTIMATE", "UNKNOWN")

# Ordered weakest -> strongest so a state machine can compare confidence levels.
RESOURCE_STATES = ("UNKNOWN", "EXHAUSTED", "CRITICAL", "CONSTRAINED", "CONSERVE", "NORMAL", "AVAILABLE")


def empty_resource(provider: str, *, model: str | None = None, source: str = "none",
                    confidence: str = "UNKNOWN") -> dict:
    """The shape every adapter returns.  All-null is a legal, honest answer."""
    if confidence not in CONFIDENCE:
        raise ValueError(f"unknown confidence {confidence!r}; use one of {CONFIDENCE}")
    return {
        "provider": provider,
        "model": model,
        "context": {
            "used_tokens": None,
            "limit_tokens": None,
            "remaining_tokens": None,
            "used_pct": None,
        },
        "quota": {
            "window": None,
            "used_pct": None,
            "remaining_pct": None,
            "reset_at": None,
        },
        "observed_usage": {
            "input_tokens": None,
            "output_tokens": None,
            "cache_read_tokens": None,
            "cache_write_tokens": None,
        },
        "burn_rate": {
            "tokens_per_minute": None,
            "quota_pct_per_minute": None,
        },
        "source": source,
        "confidence": confidence,
        "updated_at": None,
    }


def is_known(resource: dict) -> bool:
    return (resource or {}).get("confidence", "UNKNOWN") != "UNKNOWN"


def remaining_pct(resource: dict) -> float | None:
    """The single most-constrained known remaining-capacity percentage.

    Context and quota are different resources (section 3 of the directive);
    when both are known this takes the smaller one, because the tighter
    constraint is the one that actually limits what can run next.
    """
    if not is_known(resource):
        return None
    candidates = []
    quota_remaining = (resource.get("quota") or {}).get("remaining_pct")
    if quota_remaining is not None:
        candidates.append(quota_remaining)
    ctx = resource.get("context") or {}
    if ctx.get("used_pct") is not None:
        candidates.append(round(100.0 - ctx["used_pct"], 2))
    elif ctx.get("limit_tokens") and ctx.get("remaining_tokens") is not None:
        candidates.append(round(100.0 * ctx["remaining_tokens"] / ctx["limit_tokens"], 2))
    if not candidates:
        return None
    return min(candidates)
