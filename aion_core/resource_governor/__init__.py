"""LUCYOS RESOURCE GOVERNOR — native control-plane capacity awareness.

Prevents LucyOS from wasting Claude/Codex/local capacity, being surprised by
a usage limit mid-task, losing unfinished work, or reaching for an expensive
model when a cheaper one would do. This package is read-only and additive by
default (see `flags.py`): importing it, or calling its observability
functions, never changes what any other part of LucyOS does until an owner
explicitly turns on enforcement.

Public surface (what other modules should import):

    resource_governor.observability.snapshot() / .render()   — current status
    resource_governor.admission.evaluate(task) / .apply(...)  — admission control
    resource_governor.checkpoint.*                            — defer / resume
    resource_governor.ledger.*                                 — local usage ledger
    resource_governor.flags.*                                  — feature flags
    resource_governor.learnrepo_seed.ensure_targets()          — LearnRepo linkage
"""
from __future__ import annotations

from . import (admission, burn_rate, capability_gate, checkpoint, estimator, flags,
              ledger, observability, providers, schema)
from . import state as state_machine


def hook_boot() -> dict:
    """Called from `resume.boot()`.  Reports status; only mutates tasks if
    `resource_governor.auto_resume` is on, and only for tasks this subsystem
    itself parked (see `checkpoint.MARKER_PREFIX`)."""
    if not flags.flag("resource_governor.enabled"):
        return {"enabled": False}
    try:
        snap = observability.snapshot(persist=True)
    except Exception as exc:  # noqa: BLE001 - boot must never fail because of this
        return {"enabled": True, "error": str(exc)[:200]}
    result = {"enabled": True, "overall_state": snap["overall_state"],
             "waiting_for_resource": snap["waiting_for_resource"]}
    if flags.flag("resource_governor.auto_resume") and snap["waiting_for_resource"]:
        try:
            result["resume"] = checkpoint.resume_all()
        except Exception as exc:  # noqa: BLE001
            result["resume_error"] = str(exc)[:200]
    return result


def seed_learnrepo_targets() -> list[str]:
    """Directive section 29: register the telemetry research candidates.

    Idempotent — `learnrepo.register` is a no-op if the (capability,
    candidate) pair already exists.  This never runs the third-party code;
    it only records that LucyOS should keep researching it.
    """
    from .. import learnrepo
    targets = [
        ("ccusage/ccusage",
         "CLI usage/cost tracker for Claude Code; candidate telemetry-parsing adapter"),
        ("SteveHuang27GitHub/claude-usage-monitor",
         "Claude usage monitor; candidate telemetry-parsing adapter"),
    ]
    return [learnrepo.register(capability_gate.CAPABILITY, candidate, notes=notes)
            for candidate, notes in targets]
