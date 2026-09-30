"""Start the real WhatsApp bridge as a separate process, exactly as the service
does (python3 bridges/whatsapp_bridge.py cloud), with fake runtime-built
credentials. Proves: missing variables give a clear named error, and with
everything present the process starts, binds loopback and enforces the
verify-token gate. Does NOT contact Meta and proves nothing about a real
phone."""
import importlib.util
import os
import signal
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

from tests.base import AionTest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bridges" / "whatsapp_bridge.py"
# Generous, so a slow cold start on a CI runner is not a failure; a wedged process is.
START_DEADLINE_SECONDS = 30


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = _load("whatsapp_bridge_e2e", "bridges/whatsapp_bridge.py")
preflight = _load("bridge_preflight_e2e", "scripts/bridge_preflight.py")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _fixture_env(omit=()):
    """Inherit the (isolated) test environment, then set the six variables to
    obviously fake values assembled at runtime; drop any named in `omit`."""
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"  # the address line must survive SIGTERM
    env["PYTHONFAULTHANDLER"] = "1"  # SIGABRT then prints every thread's stack
    for name in bridge.CLOUD_ENV_REQUIRED:
        env.pop(name, None)
    for name in bridge.CLOUD_ENV_REQUIRED:
        if name not in omit:
            env[name] = "fake-" + name.lower().replace("whatsapp_", "")[:8] + "-1"
    return env


def _run(env, port):
    return subprocess.run([sys.executable, str(BRIDGE), "cloud", "--host", "127.0.0.1",
                           "--port", str(port)], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=30)


class TestBridgeStartsAsAService(AionTest):
    def test_no_variables_exits_2_naming_every_one(self):
        result = _run(_fixture_env(omit=bridge.CLOUD_ENV_REQUIRED), _free_port())
        self.assertEqual(result.returncode, 2)
        for name in bridge.CLOUD_ENV_REQUIRED:
            self.assertIn(name, result.stderr)

    def test_one_missing_variable_exits_2_naming_only_that_one(self):
        result = _run(_fixture_env(omit=("WHATSAPP_APP_SECRET",)), _free_port())
        self.assertEqual(result.returncode, 2)
        self.assertIn("WHATSAPP_APP_SECRET", result.stderr)
        for name in set(bridge.CLOUD_ENV_REQUIRED) - {"WHATSAPP_APP_SECRET"}:
            self.assertNotIn(name, result.stderr)

    def test_all_variables_present_starts_binds_loopback_and_gates_handshake(self):
        port = _free_port()
        proc = subprocess.Popen([sys.executable, str(BRIDGE), "cloud", "--host", "127.0.0.1",
                                 "--port", str(port)], cwd=ROOT, env=_fixture_env(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        listening = (False, "no attempt made")
        gate = None
        try:
            # Generous deadline and a short per-attempt timeout: a slow CI runner
            # (macOS cold start) is not a failure, a wedged process is.
            deadline = time.time() + START_DEADLINE_SECONDS
            while time.time() < deadline and proc.poll() is None:
                listening = preflight.check_listening("127.0.0.1", port, timeout=0.5)
                if listening[0]:
                    break
                time.sleep(0.2)
            exited = proc.poll() is not None
            if listening[0] and not exited:
                gate = preflight.check_handshake_gate("127.0.0.1", port)
        finally:
            if proc.poll() is None and not listening[0]:
                # Alive but never listening: ask Python for a stack dump (see
                # PYTHONFAULTHANDLER above) so the failure shows where it is stuck.
                proc.send_signal(signal.SIGABRT)
            else:
                proc.terminate()
            try:
                out, err = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
        # On any failure show what the bridge itself said. The credentials are
        # runtime-built fakes and the bridge never prints them.
        diag = (f"\n--- bridge exit code: {proc.returncode} ---"
                f"\n--- bridge stdout ---\n{out[-1500:]}"
                f"\n--- bridge stderr ---\n{err[-1500:]}")
        self.assertFalse(exited, "bridge exited instead of staying up" + diag)
        self.assertTrue(listening[0], listening[1] + diag)
        self.assertTrue(gate[0], gate[1] + diag)
        # bound to loopback only: the printed address says so
        self.assertIn("127.0.0.1", out, diag)


if __name__ == "__main__":
    unittest.main()
