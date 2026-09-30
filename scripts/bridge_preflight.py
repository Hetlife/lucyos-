#!/usr/bin/env python3
"""Preflight for the WhatsApp Cloud API bridge. Read-only; prints no secret values.

Checks, in order, and stops reporting green at the first thing that will stop
Meta's messages arriving:

  1. every variable the cloud adapter requires is present in the secret store,
     and survives being loaded the way the service loads it (a shell `source`);
     checked by name only, values are never printed
  2. something is listening on the bridge's loopback port
  3. the verification handshake rejects a wrong token (403) -- proves the
     verify-token gate is live without needing the real token
  4. optional, --probe-signature: an unsigned POST is rejected (401) -- proves
     signature checking is live. This writes ONE `whatsapp.signature_failed`
     event (subject 127.0.0.1, which is also what tunnelled requests carry, so
     it cannot be told apart from them), so it is off by default.

It cannot prove Meta can reach you or that a message reaches a phone; those
need the public callback URL and the owner's real credentials.
"""
from __future__ import annotations

import argparse
import importlib.util
import secrets
import socket
import subprocess
import sys
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aion_core import bootstrap, config  # noqa: E402


def required_variables() -> tuple:
    """Read the list from the bridge itself so it cannot drift from what the
    service actually requires."""
    path = ROOT / "bridges" / "whatsapp_bridge.py"
    spec = importlib.util.spec_from_file_location("whatsapp_bridge_preflight", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.CLOUD_ENV_REQUIRED)


def check_variables(names=None) -> tuple:
    names = required_variables() if names is None else names
    missing = [n for n in names if not bootstrap.has_secret(n)]
    if missing:
        return False, "missing from the secret store: " + ", ".join(missing)
    return True, f"all {len(names)} required variables are set"


def _stored_values(names) -> dict:
    """NAME -> raw stored value, held in memory only, for comparison."""
    path = config.secrets_file()
    found = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() in names:
                found[key.strip()] = value  # last assignment wins, as in a shell
    return found


def check_service_view(names=None) -> tuple:
    """Load the secret store the way the service does (a shell `source` with
    auto-export) and compare what comes out with what was stored.

    `has_secret` only proves a `NAME=value` line exists. The service loads the
    file through a shell, so a value containing a space, `&`, `$` or `;` is
    silently mangled or truncated and the bridge then exits or misbehaves.
    Comparing against the stored value catches truncation that an emptiness
    check would miss (`pa$word` loads as `pa`). Values stay in memory; only
    variable names are ever reported, and shell output and errors are never
    printed because they can contain fragments of a value.
    """
    names = tuple(required_variables() if names is None else names)
    marker = "\0<<AION-PREFLIGHT>>\0"
    script = ('set -a; [ -f "$1" ] && . "$1"; set +a; shift; '
              "printf '\\0<<AION-PREFLIGHT>>\\0'; "
              'for v in "$@"; do printf \'%s\\0\' "${!v}"; done')
    try:
        done = subprocess.run(["bash", "-c", script, "_", str(config.secrets_file()), *names],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"could not load the secret store ({exc.__class__.__name__})"
    loaded = done.stdout.split(marker)[-1].split("\0")[:len(names)]
    stored = _stored_values(names)
    if len(loaded) != len(names):
        return False, "could not read back what the service would load"
    unset = [n for n, got in zip(names, loaded) if not got and not stored.get(n)]
    if unset:
        return False, "not set: " + ", ".join(unset)
    bad = [n for n, got in zip(names, loaded) if got != stored.get(n, "")]
    if bad:
        return False, ("differs from what is stored, as the service would load it: "
                       + ", ".join(bad) + ". A value probably contains a space or one of "
                       "& $ ; ` \" ' \\ . Re-enter it with letters, digits, - and _ only. "
                       "(Values and shell output are never printed.)")
    if done.stderr.strip():
        return False, ("secrets.env printed errors when loaded as the service loads it; "
                       "a value probably has a shell character. (Output suppressed.)")
    return True, f"all {len(names)} load exactly as stored, the way the service loads them"


def check_listening(host: str, port: int, timeout: float = 3.0) -> tuple:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"listening on {host}:{port}"
    except OSError as exc:
        return False, f"nothing listening on {host}:{port} ({exc.__class__.__name__})"


def _request(host: str, port: int, method: str, path: str, body: bytes = b"",
             headers=None, timeout: float = 3.0) -> int:
    conn = HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        return conn.getresponse().status
    finally:
        conn.close()


def check_handshake_gate(host: str, port: int) -> tuple:
    wrong = secrets.token_urlsafe(16)  # a random wrong token; never the real one
    try:
        status = _request(host, port, "GET",
                          f"/?hub.mode=subscribe&hub.verify_token={wrong}&hub.challenge=x")
    except OSError as exc:
        return False, f"handshake probe failed to connect ({exc.__class__.__name__})"
    if status == 403:
        return True, "wrong verify token is rejected (403)"
    return False, f"wrong verify token returned {status}, expected 403"


def check_signature_gate(host: str, port: int) -> tuple:
    try:
        status = _request(host, port, "POST", "/", body=b"{}",
                          headers={"Content-Type": "application/json",
                                   "X-Hub-Signature-256": "sha256=" + "0" * 64})
    except OSError as exc:
        return False, f"signature probe failed to connect ({exc.__class__.__name__})"
    if status == 401:
        return True, "unsigned/incorrectly signed POST is rejected (401)"
    return False, f"bad signature returned {status}, expected 401"


def run(host: str, port: int, probe_signature: bool, names=None) -> int:
    results = [("variables stored", check_variables(names)),
               ("variables as service loads them", check_service_view(names))]
    listening = check_listening(host, port)
    results.append(("listening", listening))
    if listening[0]:
        results.append(("handshake gate", check_handshake_gate(host, port)))
        if probe_signature:
            results.append(("signature gate", check_signature_gate(host, port)))
    failed = False
    for label, (ok, detail) in results:
        print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
        failed = failed or not ok
    if failed:
        print("\nNOT ready. Fix the first FAIL above; later checks depend on it.")
        return 1
    print("\nReady locally. Not proven: that Meta can reach the public callback URL, "
          "or that a message reaches a phone.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--probe-signature", action="store_true",
                   help="also send one unsigned POST (logs one signature_failed event)")
    args = p.parse_args(argv)
    return run(args.host, args.port, args.probe_signature)


if __name__ == "__main__":
    raise SystemExit(main())
