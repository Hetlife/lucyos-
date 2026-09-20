"""Dependency-free localhost simulator; no device connection."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import time

from devices.little_lucy.protocol.state import STATES, validate

STATIC = Path(__file__).with_name("static")


class Handler(BaseHTTPRequestHandler):
    state = {"version": 1, "sequence": 0, "timestamp": 0, "state": "IDLE", "status": "Ready"}

    def do_GET(self):
        if self.path == "/state":
            body = json.dumps({**self.state, "timestamp": time.time()}).encode()
            content_type = "application/json"
        elif self.path in ("/", "/index.html"):
            body = (STATIC / "index.html").read_bytes()
            content_type = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/state":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 512:
                raise ValueError("oversize state")
            value = validate(json.loads(self.rfile.read(length)))
        except (ValueError, KeyError, json.JSONDecodeError):
            self.send_error(400, "invalid state")
            return
        type(self).state = value
        self.send_response(204)
        self.end_headers()


def serve(host="127.0.0.1", port=4872):
    if host != "127.0.0.1":
        raise ValueError("emulator is localhost only")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
