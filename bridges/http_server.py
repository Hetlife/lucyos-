#!/usr/bin/env python3
"""Authenticated, dependency-free AION phone interface.

The app shell is public so a device can open the token-entry screen. Every API
request requires a bearer token loaded from AION's protected secret store.
Bind to loopback by default and use an SSH or private-network tunnel remotely.
"""
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aion_core import approvals, bootstrap, config, db, router, security  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = ROOT / "web"
MAX_BODY_BYTES = 16 * 1024
API_COMMANDS = {
    "/api/status": "status",
    "/api/tasks": "tasks",
    "/api/blockers": "blockers",
    "/api/money": "money",
    "/api/errors": "errors",
    "/api/agents": "agents",
    "/api/report": "report",
    "/api/today": "today",
}


def read_secret(name: str = "AION_INTERFACE_TOKEN") -> str:
    """Read one value without placing it in logs, state, or process arguments."""
    path = config.secrets_file()
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return ""


class InterfaceHandler(BaseHTTPRequestHandler):
    token = ""

    def log_message(self, fmt, *args):
        pass

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )

    def _json(self, code: int, payload: dict) -> None:
        safe = security.redact(json.dumps(payload, ensure_ascii=False)).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.send_header("Content-Length", str(len(safe)))
        self.end_headers()
        self.wfile.write(safe)

    def _authorized(self) -> bool:
        auth = self.headers.get("Authorization", "")
        scheme, _, provided = auth.partition(" ")
        valid = scheme.lower() == "bearer" and bool(self.token)
        valid = valid and hmac.compare_digest(provided, self.token)
        if not valid:
            db.log_event("interface", "auth_failed", self.client_address[0])
        return valid

    def _serve_asset(self, path: str) -> None:
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        candidate = (WEB_ROOT / relative).resolve()
        try:
            candidate.relative_to(WEB_ROOT.resolve())
        except ValueError:
            return self._json(404, {"error": "not found"})
        if not candidate.is_file():
            return self._json(404, {"error": "not found"})
        body = candidate.read_bytes()
        self.send_response(200)
        kind = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_header("Content-Type", kind + ("; charset=utf-8" if kind.startswith("text/") else ""))
        self.send_header("Cache-Control", "no-cache" if candidate.name == "index.html" else "public, max-age=3600")
        self._security_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = urlsplit(self.path).path
        if path.startswith("/api/"):
            if not self._authorized():
                return self._json(401, {"error": "unauthorized"})
            command = API_COMMANDS.get(path)
            if path == "/api/approvals":
                rows = [{
                    "approval_id": row["approval_id"],
                    "action": row["action"],
                    "why": row["why"] or "not recorded",
                    "cost": row["cost"] or "not recorded",
                    "max_downside": row["max_downside"] or "not recorded",
                    "expected_benefit": row["expected_benefit"] or "not recorded",
                } for row in approvals.pending()]
                return self._json(200, {"ok": True, "data": rows})
            if not command:
                return self._json(404, {"error": "not found"})
            return self._json(200, {"ok": True, "data": router.handle(command, sender="interface")})
        return self._serve_asset(path)

    def do_POST(self):  # noqa: N802
        path = urlsplit(self.path).path
        if path != "/api/command":
            return self._json(404, {"error": "not found"})
        if not self._authorized():
            return self._json(401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json(400, {"error": "invalid content length"})
        if length <= 0 or length > MAX_BODY_BYTES:
            return self._json(413, {"error": "payload too large"})
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json(400, {"error": "invalid json"})
        message = str(payload.get("message", "")).strip()
        if not message:
            return self._json(400, {"error": "empty message"})
        return self._json(200, {"ok": True, "data": router.handle(message, sender="interface")})


def build_server(host: str, port: int, *, token: str | None = None) -> ThreadingHTTPServer:
    value = token if token is not None else read_secret()
    if not value:
        raise RuntimeError(
            "AION_INTERFACE_TOKEN is not set; run `aion secrets set AION_INTERFACE_TOKEN` on this PC"
        )
    handler = type("BoundInterfaceHandler", (InterfaceHandler,), {"token": value})
    return ThreadingHTTPServer((host, port), handler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AION phone interface")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8787, type=int)
    args = parser.parse_args(argv)
    bootstrap.ensure()
    try:
        server = build_server(args.host, args.port)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"AION interface listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
