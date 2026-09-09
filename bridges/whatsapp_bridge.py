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
from urllib import error as urlerror
from urllib import request as urlrequest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aion_core import bootstrap, config, db, resume, router, security, util  # noqa: E402

MAX_MESSAGE_BYTES = 4096


def cloud_sender_allowed(sender: str, allowed_sender: str) -> bool:
    """Authorize the single owner sender without leaking either value."""
    return bool(sender and allowed_sender) and hmac.compare_digest(sender, allowed_sender)
GRAPH_API_ROOT = "https://graph.facebook.com"


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
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_MESSAGE_BYTES * 4:
            return self._send(413, {"error": "payload too large"})
        raw = self.rfile.read(length)

        if self.secret_token:
            provided = self.headers.get("X-Bridge-Token", "")
            if not hmac.compare_digest(provided, self.secret_token):
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
        if db.seen(f"wa:{message_id}", "whatsapp_webhook"):
            return self._send(200, {"reply": "", "duplicate": True})
        self._send(200, {"reply": reply_to(message, sender=sender)})

    def do_GET(self):  # noqa: N802
        self._send(200, {"ok": True, "service": "aion-whatsapp-bridge"})


def cloud_messages(payload: dict) -> list[tuple[str, str, str]]:
    """Return (message id, sender phone, text) tuples from a Cloud API webhook."""
    found = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                text = message.get("text", {}).get("body")
                if message.get("type") == "text" and isinstance(text, str) and text.strip():
                    found.append((str(message.get("id", "")),
                                  str(message.get("from", "")), text.strip()))
    return found


class CloudAPI:
    """Minimal Meta WhatsApp Cloud API client; credentials remain in memory."""

    def __init__(self, access_token: str, phone_number_id: str, graph_version: str):
        self.auth_value = access_token
        self.phone_number_id = phone_number_id
        self.graph_version = graph_version

    def send_text(self, recipient: str, body: str) -> None:
        endpoint = (f"{GRAPH_API_ROOT}/{self.graph_version}/"
                    f"{self.phone_number_id}/messages")
        data = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }).encode("utf-8")
        req = urlrequest.Request(endpoint, data=data, method="POST", headers={
            "Authorization": f"Bearer {self.auth_value}",
            "Content-Type": "application/json",
        })
        try:
            with urlrequest.urlopen(req, timeout=15) as response:
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"Cloud API returned HTTP {response.status}")
        except urlerror.HTTPError as exc:
            # Never include the provider response: it can echo sensitive request data.
            raise RuntimeError(f"Cloud API returned HTTP {exc.code}") from None
        except urlerror.URLError as exc:
            raise RuntimeError(f"Cloud API connection failed: {exc.reason}") from None


class CloudHandler(BaseHTTPRequestHandler):
    verify_token = ""
    app_secret = ""
    client: CloudAPI | None = None
    allowed_sender = ""

    def log_message(self, fmt, *args):
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        from urllib.parse import parse_qs, urlsplit
        query = parse_qs(urlsplit(self.path).query)
        supplied = query.get("hub.verify_token", [""])[0]
        if (query.get("hub.mode", [""])[0] == "subscribe" and
                hmac.compare_digest(supplied, self.verify_token)):
            challenge = query.get("hub.challenge", [""])[0].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(challenge)))
            self.end_headers()
            self.wfile.write(challenge)
            return
        self._json(403, {"error": "verification failed"})

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_MESSAGE_BYTES * 16:
            return self._json(413, {"error": "payload too large"})
        raw = self.rfile.read(length)
        supplied = self.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            self.app_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            db.log_event("bridge", "whatsapp.signature_failed", self.client_address[0])
            return self._json(401, {"error": "invalid signature"})
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._json(400, {"error": "invalid json"})

        try:
            for message_id, sender, message in cloud_messages(payload):
                if not message_id or not sender:
                    continue
                if not cloud_sender_allowed(sender, self.allowed_sender):
                    db.log_event("bridge", "whatsapp.sender_rejected", "unauthorized sender")
                    continue
                if db.seen(f"wa-cloud:{message_id}", "whatsapp_cloud"):
                    continue
                assert self.client is not None
                self.client.send_text(sender, reply_to(message, sender=sender))
        except Exception as exc:
            from aion_core import errors
            errors.record("whatsapp_cloud", f"delivery failed: {exc}")
            return self._json(500, {"error": "delivery failed"})
        self._json(200, {"ok": True})


def run_webhook(host: str, port: int) -> int:
    Handler.secret_token = os.environ.get("WHATSAPP_BRIDGE_TOKEN", "")
    if not Handler.secret_token:
        print("WARNING: WHATSAPP_BRIDGE_TOKEN is unset — the endpoint is unauthenticated.",
              file=sys.stderr)
        print("Bind to localhost only and put a tunnel or reverse proxy in front.",
              file=sys.stderr)
    server = HTTPServer((host, port), Handler)
    print(f"AION WhatsApp bridge listening on http://{host}:{port} "
          f"(auth {'on' if Handler.secret_token else 'OFF'})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def run_cloud(host: str, port: int) -> int:
    names = ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID",
             "WHATSAPP_VERIFY_TOKEN", "WHATSAPP_APP_SECRET",
             "WHATSAPP_GRAPH_API_VERSION", "WHATSAPP_ALLOWED_SENDER")
    values = {name: os.environ.get(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing), file=sys.stderr)
        return 2
    CloudHandler.verify_token = values["WHATSAPP_VERIFY_TOKEN"]
    CloudHandler.app_secret = values["WHATSAPP_APP_SECRET"]
    CloudHandler.allowed_sender = values["WHATSAPP_ALLOWED_SENDER"]
    CloudHandler.client = CloudAPI(values["WHATSAPP_ACCESS_TOKEN"],
                                   values["WHATSAPP_PHONE_NUMBER_ID"],
                                   values["WHATSAPP_GRAPH_API_VERSION"])
    server = HTTPServer((host, port), CloudHandler)
    print(f"AION WhatsApp Cloud API bridge listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="AION WhatsApp bridge")
    p.add_argument("adapter", choices=["stdin", "file", "webhook", "cloud"])
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--poll", type=float, default=2.0)
    p.add_argument("--once", action="store_true", help="file adapter: one pass then exit")
    args = p.parse_args(argv)

    bootstrap.ensure()
    resume.boot()
    if args.adapter == "stdin":
        return run_stdin()
    if args.adapter == "file":
        return run_file(args.poll, args.once)
    if args.adapter == "cloud":
        return run_cloud(args.host, args.port)
    return run_webhook(args.host, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
