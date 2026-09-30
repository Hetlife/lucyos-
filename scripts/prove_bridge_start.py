#!/usr/bin/env python3
"""Prove, from a clean clone, that the WhatsApp bridge service would start.

Clones the *committed* HEAD of this repo into a temp dir, runs the real
scripts/install.sh with an isolated HOME and AION_HOME, stores FAKE credentials
through the real secret store, then runs the exact command line found in the
service unit file (not a re-typed copy) on a free port and runs
scripts/bridge_preflight.py against it. Uncommitted changes are not included.

It proves the install works, the secret store loads the way the service loads
it, and the process starts, binds loopback and enforces the verify-token and
signature gates. It does NOT contact Meta and proves nothing about a real
phone, a public callback URL, or your real credentials.
"""
from __future__ import annotations

import os
import secrets
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN",
         "WHATSAPP_APP_SECRET", "WHATSAPP_GRAPH_API_VERSION", "WHATSAPP_ALLOWED_SENDER")


def step(label: str, ok: bool, detail: str = "") -> bool:
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="lucyos-prove-"))
    repo, home, brain = work / "lucyos", work / "home", work / "brain"
    home.mkdir()
    env = dict(os.environ, HOME=str(home), AION_HOME=str(brain), PYTHONUNBUFFERED="1")
    for name in NAMES:
        env.pop(name, None)
    print(f"working in {work}\n")

    clone = subprocess.run(["git", "clone", "--quiet", str(ROOT), str(repo)],
                           capture_output=True, text=True)
    if not step("clean clone of committed HEAD", clone.returncode == 0):
        return 1
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    print(f"      at {head}")

    install = subprocess.run(["bash", str(repo / "scripts" / "install.sh")], cwd=repo,
                             env=env, capture_output=True, text=True, timeout=900)
    healthy = any(l.strip().startswith("healthy") for l in install.stdout.splitlines())
    if not step("scripts/install.sh", install.returncode == 0 and healthy,
                f"exit {install.returncode}, health {'healthy' if healthy else 'NOT healthy'}"):
        print(install.stdout[-800:])
        return 1

    fake = {n: "fake" + secrets.token_hex(6) for n in NAMES}
    store = subprocess.run(
        [sys.executable, "-c",
         "import sys; from aion_core import bootstrap\n"
         "for line in sys.stdin.read().splitlines():\n"
         "    n, v = line.split('=', 1); bootstrap.set_secret(n, v)"],
        cwd=repo, env=env, input="\n".join(f"{k}={v}" for k, v in fake.items()),
        capture_output=True, text=True)
    if not step("stored six fake credentials via the real secret store", store.returncode == 0):
        return 1

    unit = next(repo.glob("*/aion-bridge.service")).read_text()
    line = next(l for l in unit.splitlines() if l.startswith("ExecStart="))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    command = (line[len("ExecStart="):].replace("@AION_HOME@", str(brain))
               .replace("@REPO@", str(repo)).replace("--port 8765", f"--port {port}"))
    proc = subprocess.Popen(shlex.split(command), cwd=repo, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ok = False
    try:
        deadline = time.time() + 20
        while time.time() < deadline and proc.poll() is None:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                ok = True
                break
            except OSError:
                time.sleep(0.3)
        if not step("the service's own ExecStart command starts and listens on loopback",
                    ok and proc.poll() is None, f"127.0.0.1:{port}"):
            return 1
        pre = subprocess.run([sys.executable, str(repo / "scripts" / "bridge_preflight.py"),
                              "--port", str(port), "--probe-signature"],
                             cwd=repo, env=env, capture_output=True, text=True, timeout=60)
        print(pre.stdout.rstrip())
        passed = step("bridge_preflight.py --probe-signature", pre.returncode == 0)
        leaked = any(v in pre.stdout + pre.stderr for v in fake.values())
        passed = step("no credential value appears in the preflight output", not leaked) and passed
    finally:
        proc.terminate()
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("\nPROVEN: clean install, secret store loads as the service loads it, process starts,"
          "\n        binds loopback, enforces verify-token and signature gates.")
    print("NOT PROVEN: Meta reachability, a public callback URL, your real credentials,"
          "\n        or that a message has ever reached a phone.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
