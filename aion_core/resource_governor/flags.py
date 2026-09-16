"""Feature flags and configurable thresholds, stored in the existing `meta` table.

Nothing here is a new persistence mechanism — `db.get_meta`/`db.set_meta` is
the same key/value store every other subsystem already uses.  Defaults are
deliberately conservative (directive section 31: "start safely"): the
subsystem observes and records from the moment it exists, but it only
*changes what LucyOS does* (gates a task, auto-defers, auto-resumes) once an
owner explicitly turns that behaviour on.
"""
from __future__ import annotations

from .. import db

DEFAULTS = {
    # Read-only: record telemetry, compute state, expose it in status/health.
    # Safe to leave on; it cannot block or alter any task by itself.
    "resource_governor.enabled": "1",
    # Actually gate `worker.work()` admission on the computed decision.
    "resource_governor.enforce_admission": "0",
    # Actually move a task to WAITING (resource) instead of just recording
    # that it would have been deferred.
    "resource_governor.auto_defer": "0",
    # Actually flip WAITING(resource) tasks back to READY when capacity and
    # the repository state both check out.
    "resource_governor.auto_resume": "0",
    # Write a task-level checkpoint before a task that looks CRITICAL-risk
    # starts, not just when it is deferred outright.
    "resource_governor.checkpoint_on_critical": "0",
}

# Percentage-remaining boundaries from directive section 9.  min-remaining%
# for a state to apply; EXHAUSTED has no floor.
THRESHOLD_DEFAULTS = {
    "AVAILABLE": 95.0,
    "NORMAL": 50.0,
    "CONSERVE": 30.0,
    "CONSTRAINED": 15.0,
    "CRITICAL": 5.0,
}


class UnknownFlag(ValueError):
    pass


def flag(name: str) -> bool:
    if name not in DEFAULTS:
        raise UnknownFlag(f"unknown resource_governor flag {name!r}")
    return db.get_meta(name, DEFAULTS[name]) == "1"


def set_flag(name: str, on: bool) -> None:
    if name not in DEFAULTS:
        raise UnknownFlag(f"unknown resource_governor flag {name!r}")
    db.set_meta(name, "1" if on else "0")
    db.log_event("owner", "resource_governor.flag", name, "on" if on else "off")


def all_flags() -> dict:
    return {name: flag(name) for name in DEFAULTS}


def threshold(state: str) -> float:
    key = f"resource_governor.threshold.{state}"
    return float(db.get_meta(key, str(THRESHOLD_DEFAULTS.get(state, 0.0))))


def set_threshold(state: str, pct: float) -> None:
    if state not in THRESHOLD_DEFAULTS:
        raise UnknownFlag(f"unknown threshold state {state!r}")
    db.set_meta(f"resource_governor.threshold.{state}", str(pct))
    db.log_event("owner", "resource_governor.threshold", state, str(pct))


def all_thresholds() -> dict:
    return {state: threshold(state) for state in THRESHOLD_DEFAULTS}
