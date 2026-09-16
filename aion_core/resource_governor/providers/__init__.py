"""Provider registry.

`read_all()` is the only thing most callers need: it runs every built-in
adapter through `base.safe_read` and returns normalized results keyed by
provider name.  Nothing here ever calls out to a third-party library.

External adapters (from ccusage, claude-usage-monitor or anything else
LearnRepo researches) can only be attached via `register_external`, and only
take effect once `aion_core.learnrepo.is_approved(...)` says the exact
candidate has cleared the full pipeline.  Until then this dict stays empty
and the built-in adapters are the only source of truth.
"""
from __future__ import annotations

from typing import Callable

from . import base, claude, codex, local

BUILTIN = {
    "claude": claude.read,
    "codex": codex.read,
}

EXTERNAL_ADAPTERS: dict[str, tuple[str, Callable[[], dict]]] = {}


def register_external(provider: str, *, learnrepo_candidate: str, read_fn: Callable[[], dict]) -> None:
    """Attach a LearnRepo-approved telemetry adapter.

    `learnrepo_candidate` is checked again at read time (not just at
    registration time) so a candidate that is later rejected stops being
    consulted without anyone having to remember to unregister it.
    """
    EXTERNAL_ADAPTERS[provider] = (learnrepo_candidate, read_fn)


def read_all() -> dict:
    results = {name: base.safe_read(name, fn) for name, fn in BUILTIN.items()}
    from .. import capability_gate  # local import: avoids a cycle at module load
    for provider, (candidate, fn) in EXTERNAL_ADAPTERS.items():
        if capability_gate.external_adapter_allowed(provider, candidate):
            results[provider] = base.safe_read(f"{provider}:{candidate}", fn)
    return results


def read_local() -> dict:
    try:
        return local.read()
    except Exception as exc:  # noqa: BLE001 - never let a local probe crash the caller
        return {"provider": "local", "available": False, "error": str(exc)[:300],
                "source": "adapter_error", "confidence": "UNKNOWN"}
