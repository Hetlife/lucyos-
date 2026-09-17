"""macOS: launchd agents under `deploy/launchd/`."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .base import REPO, HostAdapter


class MacOSHost(HostAdapter):
    def name(self) -> str:
        return "macos"

    def scheduler_kind(self) -> str:
        return "launchd"

    def service_unit_dir(self) -> Path:
        return REPO / "deploy" / "launchd"

    def service_active(self, name: str) -> bool | None:
        try:
            result = subprocess.run(["launchctl", "list", name],
                                    capture_output=True, timeout=5, text=True)
        except (OSError, subprocess.TimeoutExpired):
            return None  # cannot even ask the question
        if result.returncode != 0:
            # launchctl asked and confirmed: not loaded, so definitely not
            # running. A real, verified "no" -- not a "we don't know".
            return False
        first_field = result.stdout.split()[0] if result.stdout.split() else ""
        return first_field.isdigit()  # a PID means running; "-" or blank means loaded but not running

    def service_install_hint(self, name: str) -> str:
        return (f"cp deploy/launchd/{name} ~/Library/LaunchAgents/ && "
                f"launchctl load ~/Library/LaunchAgents/{name}")
