"""Linux: systemd --user units under `systemd/`."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .base import REPO, HostAdapter


class LinuxHost(HostAdapter):
    def name(self) -> str:
        return "linux"

    def scheduler_kind(self) -> str:
        return "systemd"

    def service_unit_dir(self) -> Path:
        return REPO / "systemd"

    def service_active(self, name: str) -> bool | None:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "--quiet", name],
                capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return None
        # systemctl is-active: 0 = active, 3 = inactive/dead/failed -- both are
        # genuine, known answers. Anything else (missing unit, odd exit code)
        # is not a confident answer either way.
        if result.returncode == 0:
            return True
        if result.returncode == 3:
            return False
        return None

    def service_install_hint(self, name: str) -> str:
        return (f"cp systemd/{name} ~/.config/systemd/user/ && "
                f"systemctl --user daemon-reload && "
                f"systemctl --user enable --now {name}")
