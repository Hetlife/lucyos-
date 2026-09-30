"""Platform adapter layer -- contract C1.

Core code asks `host.current()` a platform question. It never imports
`.linux`/`.macos` directly, and neither of those imports the other; this
module is the only place a platform is selected.
"""
from __future__ import annotations

import platform

from .base import REPO, HostAdapter, NullHostAdapter

__all__ = ["HostAdapter", "current", "for_name", "deployment_plan"]


def current() -> HostAdapter:
    """Select the adapter for the running platform. Never raises: an
    unrecognized platform gets the conservative NullHostAdapter, not an
    exception -- a platform LucyOS doesn't know yet is not a fatal error."""
    system = platform.system().lower()
    if system == "linux":
        from .linux import LinuxHost
        return LinuxHost()
    if system == "darwin":
        from .macos import MacOSHost
        return MacOSHost()
    return NullHostAdapter()


def for_name(name: str) -> HostAdapter:
    """Select an adapter for a target platform without inspecting this host."""
    system = str(name or "").strip().lower()
    if system == "linux":
        from .linux import LinuxHost
        return LinuxHost()
    if system in {"darwin", "mac", "macos"}:
        from .macos import MacOSHost
        return MacOSHost()
    return NullHostAdapter()


def deployment_plan(name: str) -> dict:
    """Return a non-mutating scheduler/template plan for a target platform."""
    adapter = for_name(name)
    unit_dir = adapter.service_unit_dir()
    try:
        rendered_dir = str(unit_dir.relative_to(REPO)) if unit_dir else None
    except ValueError:
        rendered_dir = None
    kind = adapter.scheduler_kind()
    return {
        "kind": kind,
        "service_unit_dir": rendered_dir,
        "install_mode": "manual_review" if kind == "native-timer" else "render_only",
    }
