"""Start the real WhatsApp bridge as a separate process, exactly as the service
does (python3 bridges/whatsapp_bridge.py cloud), with fake runtime-built
credentials. Proves: missing variables give a clear named error, and with
everything present the process starts, binds loopback and enforces the
verify-token gate. Does NOT contact Meta and proves nothing about a real
phone."""
import importlib.util
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

from tests.base import AionTest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "bridges" / "whatsapp_bridge.py"


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
        try:
            deadline = time.time() + 15
            listening = (False, "")
            while time.time() < deadline and proc.poll() is None:
                listening = preflight.check_listening("127.0.0.1", port)
                if listening[0]:
                    break
                time.sleep(0.2)
            self.assertIsNone(proc.poll(), "bridge exited instead of staying up")
            self.assertTrue(listening[0], listening[1])
            ok, detail = preflight.check_handshake_gate("127.0.0.1", port)
            self.assertTrue(ok, detail)
            # bound to loopback only: the printed address says so
        finally:
            proc.terminate()
            try:
                out, _ = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, _ = proc.communicate()
        self.assertIn("127.0.0.1", out)


if __name__ == "__main__":
    unittest.main()
