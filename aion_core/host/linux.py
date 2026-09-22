"""Linux: systemd --user units under `systemd/`."""
from __future__ import annotations

import subprocess
import platform
import os
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

    def _user_systemd_env(self) -> dict[str, str]:
        """Return an environment that can reach the current user's systemd bus.

        Remote/non-login shells commonly omit XDG_RUNTIME_DIR and
        DBUS_SESSION_BUS_ADDRESS even while the user manager is alive.  For a
        numeric uid the systemd runtime directory is deterministic, so fill
        only missing values and preserve any explicit caller environment.
        """
        env = os.environ.copy()
        uid = os.getuid()
        runtime = Path(f"/run/user/{uid}")
        if runtime.is_dir():
            env.setdefault("XDG_RUNTIME_DIR", str(runtime))
            env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime}/bus")
        return env

    def scheduler_available(self) -> bool:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-system-running"],
                capture_output=True, timeout=5, text=True,
                env=self._user_systemd_env())
        except (OSError, subprocess.TimeoutExpired):
            return False
        # A state response such as "running" or "degraded" proves that the
        # user manager answered even when its overall state is not healthy.
        return bool(result.stdout.strip())

    def architecture(self) -> str:
        return platform.machine() or "unknown"

    def service_install_hint(self, name: str) -> str:
        return (f"cp systemd/{name} ~/.config/systemd/user/ && "
                f"systemctl --user daemon-reload && "
                f"systemctl --user enable --now {name}")
