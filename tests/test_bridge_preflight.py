import contextlib
import importlib.util
import io
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path
from unittest import mock

from aion_core import bootstrap
from tests.base import AionTest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preflight = _load("bridge_preflight_under_test", "scripts/bridge_preflight.py")
bridge = _load("whatsapp_bridge_for_preflight_test", "bridges/whatsapp_bridge.py")


class _LiveBridge:
    """The real CloudHandler on an ephemeral loopback port, fake credentials
    assembled at runtime so no credential-shaped literal exists in the repo."""

    def __enter__(self):
        h = bridge.CloudHandler
        self._saved = (h.verify_token, h.app_secret, h.client, h.allowed_sender)
        h.verify_token = "vt-" + "x" * 12
        h.app_secret = "as-" + "y" * 12
        h.client = None
        h.allowed_sender = "15550000000"
        self.server = HTTPServer(("127.0.0.1", 0), h)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        h = bridge.CloudHandler
        h.verify_token, h.app_secret, h.client, h.allowed_sender = self._saved


class TestBridgePreflight(AionTest):
    def test_required_list_is_read_from_the_bridge(self):
        self.assertEqual(set(preflight.required_variables()),
                         set(bridge.CLOUD_ENV_REQUIRED))

    def test_variables_fail_naming_exactly_what_is_missing(self):
        have = {"WHATSAPP_ACCESS_TOKEN", "WHATSAPP_APP_SECRET"}
        with mock.patch.object(preflight.bootstrap, "has_secret",
                               side_effect=lambda n: n in have):
            ok, detail = preflight.check_variables()
        self.assertFalse(ok)
        for name in set(bridge.CLOUD_ENV_REQUIRED) - have:
            self.assertIn(name, detail)
        for name in have:
            self.assertNotIn(name, detail)

    def test_variables_pass_when_all_present(self):
        with mock.patch.object(preflight.bootstrap, "has_secret", return_value=True):
            self.assertTrue(preflight.check_variables()[0])

    def test_closed_port_fails_clearly(self):
        with _LiveBridge() as live:
            port = live.port
        ok, detail = preflight.check_listening("127.0.0.1", port)
        self.assertFalse(ok)
        self.assertIn("nothing listening", detail)

    def test_live_bridge_passes_listening_and_handshake_gate(self):
        with _LiveBridge() as live:
            self.assertTrue(preflight.check_listening("127.0.0.1", live.port)[0])
            ok, detail = preflight.check_handshake_gate("127.0.0.1", live.port)
        self.assertTrue(ok, detail)

    def test_live_bridge_rejects_a_bad_signature_with_401(self):
        with _LiveBridge() as live:
            ok, detail = preflight.check_signature_gate("127.0.0.1", live.port)
        self.assertTrue(ok, detail)

    def test_a_server_that_accepts_anything_is_reported_as_failing(self):
        # If the verify-token gate were ever removed, the preflight must say so.
        with _LiveBridge() as live:
            with mock.patch.object(preflight, "_request", return_value=200):
                ok, detail = preflight.check_handshake_gate("127.0.0.1", live.port)
        self.assertFalse(ok)
        self.assertIn("expected 403", detail)

    def test_full_run_never_prints_a_secret_and_only_probes_signature_on_request(self):
        buf = io.StringIO()
        with _LiveBridge() as live, \
                mock.patch.object(preflight.bootstrap, "has_secret", return_value=True), \
                mock.patch.object(preflight, "check_service_view", return_value=(True, "stub")), \
                contextlib.redirect_stdout(buf):
            code = preflight.run("127.0.0.1", live.port, probe_signature=False)
            out_default = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertNotIn("signature gate", out_default)
        for secret in ("vt-" + "x" * 12, "as-" + "y" * 12):
            self.assertNotIn(secret, out_default)
        self.assertIn("Not proven", out_default)

        buf = io.StringIO()
        with _LiveBridge() as live, \
                mock.patch.object(preflight.bootstrap, "has_secret", return_value=True), \
                mock.patch.object(preflight, "check_service_view", return_value=(True, "stub")), \
                contextlib.redirect_stdout(buf):
            self.assertEqual(preflight.run("127.0.0.1", live.port, probe_signature=True), 0)
        self.assertIn("signature gate", buf.getvalue())


class TestServiceViewCheck(AionTest):
    """The service loads secrets.env through a shell `source`. The preflight
    must see what the service sees, not merely that a NAME=value line exists.
    Values are written with the real set_secret, in its real (unquoted) format."""

    def _store(self, legacy=None, overrides=None):
        """Store all six via the real set_secret (quoted). `legacy` maps a name
        to a raw value written unquoted, as older versions wrote the file."""
        values = {name: "v" + name[-4:].lower() + "9Z" for name in bridge.CLOUD_ENV_REQUIRED}
        values.update(overrides or {})
        for name, value in values.items():
            bootstrap.set_secret(name, value)
        if legacy:
            sf = bootstrap.config.secrets_file()
            keep = [l for l in sf.read_text().splitlines()
                    if not any(l.startswith(n + "=") for n in legacy)]
            keep += [f"{n}={v}" for n, v in legacy.items()]
            sf.write_text("\n".join(keep) + "\n")

    def test_clean_values_load_exactly_as_stored(self):
        self._store()
        self.assertTrue(preflight.check_variables()[0])
        ok, detail = preflight.check_service_view()
        self.assertTrue(ok, detail)

    def test_a_legacy_unquoted_value_with_a_space_is_stored_but_broken_for_the_service(self):
        self._store(legacy={"WHATSAPP_VERIFY_TOKEN": "qw3 uniqfrag8"})
        # the naive check is satisfied ...
        self.assertTrue(preflight.check_variables()[0])
        # ... but the service would not get the variable, and the preflight says so
        ok, detail = preflight.check_service_view()
        self.assertFalse(ok)
        self.assertIn("aion secrets set", detail)

    def test_no_fragment_of_a_bad_value_is_ever_printed(self):
        for bad in ("qw3 uniqfrag8", "a&uniqfrag8", "pa$uniqfrag8", "x;echo uniqfrag8"):
            self._store(legacy={"WHATSAPP_VERIFY_TOKEN": bad})
            ok, detail = preflight.check_service_view()
            self.assertFalse(ok, bad)
            self.assertNotIn("uniqfrag8", detail, bad)
            self.assertNotIn("echo", detail, bad)

    def test_quoted_values_with_hostile_characters_now_load_correctly(self):
        for value in ("qw3 uniqfrag8", "a&b", "pa$word", "x;echo hi", "it's"):
            self._store(overrides={"WHATSAPP_VERIFY_TOKEN": value})
            ok, detail = preflight.check_service_view()
            self.assertTrue(ok, f"{value!r}: {detail}")

    def test_a_missing_variable_is_named(self):
        self._store()
        sf = bootstrap.config.secrets_file()
        keep = [l for l in sf.read_text().splitlines()
                if not l.startswith("WHATSAPP_APP_SECRET=")]
        sf.write_text("\n".join(keep) + "\n")
        ok, detail = preflight.check_service_view()
        self.assertFalse(ok)
        self.assertIn("WHATSAPP_APP_SECRET", detail)


if __name__ == "__main__":
    unittest.main()
