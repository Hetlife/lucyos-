"""Platform adapter layer -- contract C1.

Core code asks `host.current()` a platform question. It never imports
`.linux`/`.macos` directly, and neither of those imports the other; this
module is the only place a platform is selected.
"""
from __future__ import annotations

import platform

from .base import HostAdapter, NullHostAdapter

__all__ = ["HostAdapter", "current"]


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
