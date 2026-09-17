"""The one contract every platform adapter implements.

Contract C1 (`.lucy/authority/LUCYOS_PLATFORM_AND_DATA_CONTRACTS.md`): LucyOS
is one codebase that runs on macOS and Linux without forking core logic. This
is the seam -- core code asks `host.current()` a question, never `sys.platform`
or `platform.system()` directly.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class HostAdapter:
    """Base class documenting the contract. Not instantiated directly --
    `linux.py`/`macos.py` implement it, and a platform this repo does not
    recognize gets `NullHostAdapter` (defined here, used by `current()`)."""

    def name(self) -> str:
        """Short platform identity only -- never a decision input by itself."""
        raise NotImplementedError

    def scheduler_kind(self) -> str:
        """`"systemd"`, `"launchd"`, or `"native-timer"` for anything else."""
        raise NotImplementedError

    def service_unit_dir(self) -> Path:
        """Where this platform's service unit files live in this repo."""
        raise NotImplementedError

    def service_active(self, name: str) -> bool | None:
        """True/False when genuinely known, `None` when it cannot be
        determined (missing scheduler binary, permission denied, timeout).
        `None` must never be rendered as False by a caller -- that would be
        stating a fact nobody verified."""
        raise NotImplementedError

    def service_install_hint(self, name: str) -> str:
        """A human instruction string. Never executes anything."""
        raise NotImplementedError

    def probe(self) -> dict:
        """Capability facts only -- no mutation, no network, nothing sensitive
        (no hostname/username/absolute home path; see S-28's same rule)."""
        return {
            "name": self.name(),
            "scheduler_kind": self.scheduler_kind(),
            "service_unit_dir": str(self.service_unit_dir()),
        }


class NullHostAdapter(HostAdapter):
    """Conservative fallback for a platform this repo does not recognize.
    Never raises on import or on any of its own methods -- an unknown
    platform is not an error, it is just a platform with less certainty."""

    def name(self) -> str:
        return "unknown"

    def scheduler_kind(self) -> str:
        return "native-timer"

    def service_unit_dir(self) -> Path:
        return REPO / "deploy" / "native-timer"

    def service_active(self, name: str) -> bool | None:
        return None

    def service_install_hint(self, name: str) -> str:
        return (f"Unrecognized platform: no automated install path for {name!r}. "
                "Run the underlying command manually and schedule it with "
                "whatever this host provides.")
