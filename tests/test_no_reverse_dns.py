"""Servers must not do a reverse-DNS lookup when they bind.

http.server.HTTPServer.server_bind calls socket.getfqdn(host), a reverse-DNS
lookup. On the macOS CI runner that lookup blocked for over 30 seconds even for
127.0.0.1, so the WhatsApp bridge sat silent before ever listening (stack dump:
socket.getfqdn <- HTTPServer.server_bind <- run_cloud). The name it computes
(server_name) is not used by any of our handlers."""
import importlib.util
import socket
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from tests.base import AionTest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wa = _load("whatsapp_bridge_no_dns", "bridges/whatsapp_bridge.py")
iface = _load("http_server_no_dns", "bridges/http_server.py")
taskcheck_srv = _load("taskcheck_server_no_dns", "bridges/taskcheck_server.py")


def _forbid_dns():
    return mock.patch("socket.getfqdn",
                      side_effect=AssertionError("reverse-DNS lookup (socket.getfqdn) at bind"))


class TestServersDoNotDoReverseDns(AionTest):
    def test_the_stdlib_server_really_does_the_lookup(self):
        # Sensitivity guard: proves the checks below would notice it.
        with mock.patch("socket.getfqdn", wraps=socket.getfqdn) as spy:
            server = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
            server.server_close()
        self.assertTrue(spy.called)

    def _check(self, make):
        with _forbid_dns():
            server = make()
        try:
            self.assertEqual(server.server_name, "127.0.0.1")
            self.assertEqual(server.server_port, server.server_address[1])
            self.assertGreater(server.server_port, 0)
        finally:
            server.server_close()

    def test_whatsapp_bridge_server(self):
        self._check(lambda: wa.LocalHTTPServer(("127.0.0.1", 0), wa.CloudHandler))

    def test_phone_interface_server(self):
        token = "t" + "1" * 12
        self._check(lambda: iface.build_server("127.0.0.1", 0, token=token))

    def test_taskcheck_server(self):
        self._check(lambda: taskcheck_srv.build_server("127.0.0.1", 0))


if __name__ == "__main__":
    unittest.main()
