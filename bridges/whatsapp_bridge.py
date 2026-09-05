#!/usr/bin/env python3
"""WhatsApp bridge — transport-agnostic.

The router is pure: text in, text out.  This file is the only place that knows
about a transport, so swapping providers (OpenClaw's own bridge, a Business API
account, a self-hosted gateway) touches nothing else.

Three adapters ship here:

  stdin   — type messages in a terminal, exactly what the owner would send.
  file    — poll a directory for message files; the transport drops inbound
            files in `INBOX/whatsapp/` and reads replies from `OUTBOX/whatsapp/`.
  webhook — a dependency-free HTTP endpoint for a provider that POSTs JSON.

Security: the bridge never logs raw message bodies, refuses credential-shaped
inbound text before it reaches state, and redacts every outbound reply.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aion_core import bootstrap, config, db, intake, phone, resume, router, security, sevaa, tasks, util  # noqa: E402

MAX_MESSAGE_BYTES = 4096
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
OWNER_NUMBERS_NAME = "WHATSAPP_OWNER_NUMBERS"   # comma-separated; secret store or env
BRIDGE_TOKEN_NAME = "WHATSAPP_BRIDGE_TOKEN"


def _same(a: str, b: str) -> bool:
    """Constant-time compare that cannot raise on non-ASCII input."""
    return hmac.compare_digest(a.encode("utf-8", "replace"), b.encode("utf-8", "replace"))


def load_owner_numbers() -> frozenset:
    raw = bootstrap.get_secret(OWNER_NUMBERS_NAME) or os.environ.get(OWNER_NUMBERS_NAME, "")
    return frozenset(n.strip() for n in raw.split(",") if n.strip())


def reply_to(message: str, sender: str = "owner") -> str:
    """Route one message and return a redacted, length-bounded reply."""
    if len(message.encode("utf-8")) > MAX_MESSAGE_BYTES:
        return "That message is too long for the control channel. Send a command, not a document."
    try:
        answer = router.handle(message, sender=sender)
    except Exception as exc:  # never let a bridge crash take the channel down
        from aion_core import errors
        eid = errors.record("whatsapp_bridge", f"router failed: {exc}")
        return f"Something broke handling that ({eid}). The failure is logged; send `errors`."
    answer = security.redact(answer)
    if len(answer) > MAX_MESSAGE_BYTES:
        answer = answer[:MAX_MESSAGE_BYTES - 40] + "\n… truncated. Send `report` on the PC."
    return answer


def run_stdin() -> int:
    print("AION WhatsApp bridge (stdin adapter). Type a command, Ctrl-D to exit.")
    print(router.handle("status"))
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        print(reply_to(line))
        print()
    return 0


def run_file(poll_seconds: float = 2.0, once: bool = False) -> int:
    """Directory adapter: <home>/INBOX/whatsapp -> <home>/OUTBOX/whatsapp."""
    inbox = config.home() / "INBOX" / "whatsapp"
    outbox = config.home() / "OUTBOX" / "whatsapp"
    for d in (inbox, outbox):
        d.mkdir(parents=True, exist_ok=True)
    while True:
        for path in sorted(inbox.glob("*.txt")):
            try:
                text = path.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            # Idempotency: the same delivered message is never answered twice.
            key = util.sha256_text(f"{path.name}|{text}")
            if db.seen(f"wa:{key}", "whatsapp_inbound"):
                path.unlink(missing_ok=True)
                continue
            answer = reply_to(text)
            out = outbox / f"{path.stem}.reply.txt"
            util.atomic_write(out, answer + "\n")
            path.unlink(missing_ok=True)
        if once:
            return 0
        time.sleep(poll_seconds)


class Handler(BaseHTTPRequestHandler):
    secret_token = ""
    phone_token = ""
    # Senders allowed to drive the control channel.  Empty = every sender the
    # transport forwards (only acceptable on a private, single-user transport).
    owner_numbers: frozenset = frozenset()
    # A client that connects and stalls must not hold the single-threaded
    # server — and with it the owner's control channel — open forever.
    timeout = 15

    def log_message(self, fmt, *args):  # never log message bodies
        pass

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._send(400, {"error": "invalid content-length"})
        if length < 0:
            return self._send(400, {"error": "invalid content-length"})
        if length > MAX_MESSAGE_BYTES * 4:
            return self._send(413, {"error": "payload too large"})
        # A JSON body must say so.  A browser can fire a cross-site text/plain
        # POST at 127.0.0.1 without a preflight; application/json cannot.
        ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if ctype != "application/json":
            return self._send(415, {"error": "content-type must be application/json"})
        raw = self.rfile.read(length)

        path = self.path.split("?", 1)[0].rstrip("/")
        if path == "/api/events":
            return self._handle_event(raw)
        if path in ("/api/command", "/api/capture", "/api/feedback"):
            return self._handle_phone_post(path, raw)

        if self.secret_token:
            provided = self.headers.get("X-Bridge-Token", "")
            if not _same(provided, self.secret_token):
                db.log_event("bridge", "whatsapp.auth_failed", self.client_address[0])
                return self._send(401, {"error": "unauthorized"})

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._send(400, {"error": "invalid json"})

        message = str(payload.get("message", "")).strip()
        sender = str(payload.get("from", "owner"))[:64]
        message_id = str(payload.get("id", "")) or hashlib.sha256(raw).hexdigest()[:16]
        if not message:
            return self._send(400, {"error": "empty message"})
        if self.owner_numbers and sender not in self.owner_numbers:
            # The bridge token proves the *transport*; it says nothing about who
            # typed the message.  A business number receives messages from
            # strangers, and a stranger must never reach the router.
            db.log_event("bridge", "whatsapp.sender_refused",
                         hashlib.sha256(sender.encode()).hexdigest()[:12])
            return self._send(200, {"reply": "This number is not authorised to control AION. "
                                             "Nothing was done.", "refused": True})
        if db.seen(f"wa:{message_id}", "whatsapp_webhook"):
            return self._send(200, {"reply": "", "duplicate": True})
        self._send(200, {"reply": reply_to(message, sender=sender)})

    def _handle_event(self, raw: bytes) -> None:
        """Signed events from the revenue module (S01).  Verified before parsed."""
        key = sevaa.secret()
        if not key:
            return self._send(503, {"error": "event ingestion not configured"})
        if not sevaa.verify(raw, self.headers.get(sevaa.SIGNATURE_HEADER), key):
            db.log_event("bridge", "event.auth_failed", self.client_address[0])
            return self._send(401, {"error": "bad signature"})
        try:
            event = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._send(400, {"error": "invalid json"})
        try:
            result = intake.external_event(event)
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        self._send(200, {"ok": True, **result})

    def _phone_authorized(self) -> bool:
        if not self.phone_token:
            return False
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        return _same(header[len("Bearer "):], self.phone_token)

    def _handle_phone_post(self, path: str, raw: bytes) -> None:
        if not self._phone_authorized():
            db.log_event("phone", "auth_failed", self.client_address[0])
            return self._send(401, {"error": "unauthorized"})
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._send(400, {"error": "invalid json"})
        try:
            if path == "/api/command":
                message = str(payload.get("message", "")).strip()
                if not message:
                    return self._send(400, {"error": "message is required"})
                return self._send(200, phone.run_command(message))
            if path == "/api/capture":
                text = str(payload.get("text", "")).strip()
                kind = str(payload.get("kind", "idea"))
                if not text:
                    return self._send(400, {"error": "text is required"})
                return self._send(200, phone.capture(text, kind))
            if path == "/api/feedback":
                task_id = str(payload.get("task_id", "")).strip()
                choice = str(payload.get("choice", "")).strip()
                note = str(payload.get("note", ""))
                if not task_id or not choice:
                    return self._send(400, {"error": "task_id and choice are required"})
                return self._send(200, phone.feedback(task_id, choice, note))
        except (security.SecretLeak, ValueError, tasks.TaskError) as exc:
            return self._send(400, {"error": str(exc)})
        return self._send(404, {"error": "not found"})

    _PHONE_GET_ROUTES = {
        "/api/status": lambda: phone.dashboard(),
        "/api/dashboard": lambda: phone.dashboard(),
        "/api/tasks": lambda: {"tasks": phone.task_list()},
        "/api/blockers": lambda: phone.blockers(),
        "/api/money": lambda: phone.money(),
        "/api/errors": lambda: {"errors": phone.error_list()},
        "/api/agents": lambda: {"agents": phone.agent_list()},
        "/api/report": lambda: {"text": phone.report_text()},
    }

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"

        if path in self._PHONE_GET_ROUTES:
            if not self._phone_authorized():
                db.log_event("phone", "auth_failed", self.client_address[0])
                return self._send(401, {"error": "unauthorized"})
            return self._send(200, self._PHONE_GET_ROUTES[path]())

        if path in ("/app", "/phone"):
            return self._serve_phone_page()

        self._send(200, {"ok": True, "service": "aion-whatsapp-bridge"})

    def _serve_phone_page(self) -> None:
        page_path = Path(__file__).resolve().parent / "web" / "phone.html"
        try:
            body = page_path.read_bytes()
        except OSError:
            return self._send(404, {"error": "phone page not found"})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_webhook(host: str, port: int, *, allow_unauthenticated: bool = False) -> int:
    Handler.secret_token = (bootstrap.get_secret(BRIDGE_TOKEN_NAME)
                            or os.environ.get(BRIDGE_TOKEN_NAME, ""))
    if not Handler.secret_token:
        if host not in LOOPBACK_HOSTS and not allow_unauthenticated:
            # Fail closed: an unauthenticated control channel on a reachable
            # address lets anyone on that network approve real actions.
            print(f"REFUSING to start: {BRIDGE_TOKEN_NAME} is unset and --host {host} is not "
                  f"loopback. Set the token (`aion secrets set {BRIDGE_TOKEN_NAME}`) or pass "
                  f"--allow-unauthenticated if you really mean it.", file=sys.stderr)
            return 2
        print(f"WARNING: {BRIDGE_TOKEN_NAME} is unset — the endpoint is unauthenticated.",
              file=sys.stderr)
        print("Bind to localhost only and put a tunnel or reverse proxy in front.",
              file=sys.stderr)
    Handler.owner_numbers = load_owner_numbers()
    if not Handler.owner_numbers:
        print(f"NOTE: {OWNER_NUMBERS_NAME} is unset — every sender the transport forwards can "
              f"issue commands. Set it before connecting a shared or business number.",
              file=sys.stderr)
    Handler.phone_token = bootstrap.get_secret("PHONE_API_TOKEN") or os.environ.get("PHONE_API_TOKEN", "")
    if not Handler.phone_token:
        print("NOTE: PHONE_API_TOKEN is unset — /api/* and the phone page's data calls "
              "will refuse every request until `aion secrets set PHONE_API_TOKEN` is run.",
              file=sys.stderr)
    server = HTTPServer((host, port), Handler)
    print(f"AION WhatsApp bridge listening on http://{host}:{port} "
          f"(bridge auth {'on' if Handler.secret_token else 'OFF'}, "
          f"phone auth {'on' if Handler.phone_token else 'OFF'}, "
          f"owner allowlist {'on' if Handler.owner_numbers else 'OFF'})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="AION WhatsApp bridge")
    p.add_argument("adapter", choices=["stdin", "file", "webhook"])
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--poll", type=float, default=2.0)
    p.add_argument("--once", action="store_true", help="file adapter: one pass then exit")
    p.add_argument("--allow-unauthenticated", action="store_true",
                   help="webhook: serve without a bridge token on a non-loopback host (unsafe)")
    args = p.parse_args(argv)

    bootstrap.ensure()
    resume.boot()
    if args.adapter == "stdin":
        return run_stdin()
    if args.adapter == "file":
        return run_file(args.poll, args.once)
    return run_webhook(args.host, args.port, allow_unauthenticated=args.allow_unauthenticated)


if __name__ == "__main__":
    raise SystemExit(main())
