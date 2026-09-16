"""The provider-adapter contract.

Every adapter is a single function: `read(**kwargs) -> dict` returning the
normalized schema from `resource_governor.schema`.  There is no base class to
inherit because nothing here needs shared state — the contract is just the
return shape, enforced by `schema.empty_resource()` and this module's
`safe_read` wrapper.

`safe_read` is what every caller actually uses.  A provider adapter may be
wrong, may raise, may hang on a slow filesystem — none of that may ever
propagate into the rest of LucyOS.  A broken adapter degrades to UNKNOWN.
"""
from __future__ import annotations

from typing import Callable

from .. import schema


def safe_read(name: str, fn: Callable[[], dict]) -> dict:
    """Call a provider adapter and guarantee a well-formed result comes back."""
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001 - a provider must never take LucyOS down
        result = schema.empty_resource(name, source=f"adapter_error:{type(exc).__name__}")
        result["error"] = str(exc)[:300]
        return result
    if not isinstance(result, dict) or "confidence" not in result:
        return schema.empty_resource(name, source="adapter_returned_malformed_result")
    if result.get("confidence") not in schema.CONFIDENCE:
        result = dict(result)
        result["confidence"] = "UNKNOWN"
    return result
