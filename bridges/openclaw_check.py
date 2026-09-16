"""Loopback-only reachability probe for an optional OpenClaw gateway.

LucyOS has no persistent OpenClaw gateway by design (contract C4: Lucy/
OpenClaw are replaceable, never canonical). This module never starts,
installs, or configures anything -- it only reports whether something is
already listening on the loopback port the owner configured, turning
"OpenClaw has no persistent gateway" into a health line instead of tribal
knowledge. The only network target it will ever touch is 127.0.0.1.
"""
from __future__ import annotations

import urllib.error
import urllib.request

TIMEOUT_SECONDS = 2

NOT_CONFIGURED, REACHABLE, UNREACHABLE = "not-configured", "reachable", "unreachable"


def check(port_value: str | None = None) -> dict:
    """Probe 127.0.0.1:<port> where port comes from db.get_meta("openclaw_port",
    "") -- an empty value means "not configured", not an error."""
    if port_value is None:
        from aion_core import db
        port_value = db.get_meta("openclaw_port", "") or ""

    port_value = (port_value or "").strip()
    if not port_value:
        return {"state": NOT_CONFIGURED, "detail": "openclaw_port not configured"}

    try:
        port = int(port_value)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        return {"state": NOT_CONFIGURED, "detail": f"openclaw_port {port_value!r} is not a valid port"}

    url = f"http://127.0.0.1:{port}/"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS):
            pass
        return {"state": REACHABLE, "detail": f"127.0.0.1:{port} responded"}
    except urllib.error.HTTPError:
        # Any HTTP response, even an error status, proves something is listening.
        return {"state": REACHABLE, "detail": f"127.0.0.1:{port} responded"}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"state": UNREACHABLE, "detail": f"127.0.0.1:{port} unreachable: {exc}"}
