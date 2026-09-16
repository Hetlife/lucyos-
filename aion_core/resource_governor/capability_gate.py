"""The one gate a third-party telemetry adapter must pass on every read.

This is deliberately tiny and deliberately paranoid: registering an external
adapter (`providers.register_external`) only queues it up.  Whether it is
ever actually called is decided here, fresh, every time — by asking LearnRepo
whether that exact (capability, candidate) pair reached APPROVED.  A rejection
recorded after registration takes effect immediately, with no code to update.
"""
from __future__ import annotations

CAPABILITY = "RESOURCE_GOVERNOR_TELEMETRY"


def external_adapter_allowed(provider: str, candidate: str) -> bool:
    from .. import learnrepo
    try:
        return learnrepo.is_approved(CAPABILITY, candidate)
    except Exception:  # noqa: BLE001 - a broken registry must fail closed, not crash
        return False
