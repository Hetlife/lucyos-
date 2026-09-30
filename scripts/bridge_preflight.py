#!/usr/bin/env python3
"""Preflight for the WhatsApp Cloud API bridge. Read-only; prints no secret values.

Checks, in order, and stops reporting green at the first thing that will stop
Meta's messages arriving:

  1. every variable the cloud adapter requires is present in the secret store
     (checked by name only; values are never read into output)
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
import sys
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aion_core import bootstrap  # noqa: E402


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
    results = [("variables", check_variables(names))]
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
