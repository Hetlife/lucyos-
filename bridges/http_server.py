#!/usr/bin/env python3
"""Authenticated, dependency-free AION phone interface.

The app shell is public so a device can open the token-entry screen. Every API
request requires a bearer token loaded from AION's protected secret store.
Bind to loopback by default and use an SSH or private-network tunnel remotely.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import mimetypes
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aion_core import api, approvals, bootstrap, config, db, governor, metrics, router, security, tasks  # noqa: E402

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
# Structured JSON alongside the text routes above — same auth, same redaction,
# same response envelope. The text routes are untouched; this is additive.
V1_ROUTES = {
    "/api/v1/snapshot": api.system_snapshot,
    "/api/v1/money": api.money_split,
    "/api/v1/projects": api.projects,
    "/api/v1/costs": api.costs,
    "/api/v1/tasks": api.tasks_ranked,
    "/api/v1/capabilities": api.capability_plan,
    "/api/v1/aux-providers": api.auxiliary_providers,
}

SCS_TASK_PATH = "/api/v1/scs/task"
SCS_RESULT_PATH = "/api/v1/scs/result"
SCS_TASK_FIELDS = (
    "task_id", "title", "description", "success_criteria", "validation_method",
    "next_action", "model_class", "data_class", "owner_agent", "claim_id",
)
SCS_RESULT_FIELDS = {
    "task_id", "claim_id", "idempotency_key", "STATUS", "ACTIONS", "FILES_CHANGED",
    "TESTS", "RESULTS", "BLOCKERS", "NEXT_ACTION",
}
SCS_RESULT_STATES = {"DONE", "BLOCKED", "FAILED", "NEEDS_REVIEW", "HEARTBEAT", "PROGRESS"}
SCS_IDEMPOTENCY_SCOPE = "scs-result-v2"
SCS_KEY_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
SCS_TASK_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_TRUE_VALUES = {"1", "true", "yes", "on"}


def scs_handoff_enabled() -> bool:
    return os.environ.get("AION_SCS_HANDOFF_ENABLED", "").strip().lower() in _TRUE_VALUES


def scs_agent_id() -> str:
    return os.environ.get("AION_SCS_HANDOFF_AGENT", "scs-admin01").strip() or "scs-admin01"


def _claim_scs_task() -> dict | None:
    if router.is_paused():
        return None
    safe_mode = router.is_safe_mode()
    budget = metrics.budget_status()
    governor_state = governor.state()
    paid_b_held = (
        budget["day_over"] or budget["month_over"]
        or governor_state in {"RESERVE", "CRITICAL-ONLY", "HANDOFF", "STOP"}
    )
    agent = scs_agent_id()
    for row in tasks.ready(None):
        data_class = str(row["data_class"] or "INTERNAL").upper()
        model_class = str(row["model_class"] or "B").upper()
        if data_class == "SECRET" or model_class in {"C", "D"}:
            continue
        if safe_mode and model_class != "DET":
            continue
        if paid_b_held and model_class == "B":
            continue
        if tasks.claim(row["task_id"], agent):
            claimed = dict(tasks.get(row["task_id"]))
            claimed["claim_id"] = tasks.claim_id(row["task_id"])
            return {field: (claimed[field] or "") for field in SCS_TASK_FIELDS}
    return None


def _submission_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _submission_storage_key(idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"scs-result:{digest}"


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

    def _sse(self, *, after_id: int = 0, once: bool = False, max_seconds: int = 30) -> None:
        """Stream existing LucyOS events without introducing a second event bus."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close" if once else "keep-alive")
        self._security_headers()
        self.end_headers()
        last_id = max(0, int(after_id))
        deadline = time.monotonic() + max(1, min(int(max_seconds), 60))
        try:
            while True:
                rows = api.events(last_id, 100)
                for row in rows:
                    payload = security.redact(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                    body = f"id: {row['id']}\nevent: lucyos\ndata: {payload}\n\n".encode("utf-8")
                    self.wfile.write(body)
                    last_id = int(row["id"])
                self.wfile.flush()
                if once or time.monotonic() >= deadline:
                    if once:
                        self.close_connection = True
                    break
                if not rows:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                time.sleep(1.0)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

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

    def _read_json_payload(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid content length"})
            return None
        if length <= 0 or length > MAX_BODY_BYTES:
            self._json(413, {"error": "payload too large"})
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"error": "invalid json"})
            return None
        if not isinstance(payload, dict):
            self._json(400, {"error": "json object required"})
            return None
        return payload

    def _handle_scs_result(self, payload: dict) -> None:
        if not scs_handoff_enabled():
            return self._json(404, {"error": "not found"})
        if set(payload) != SCS_RESULT_FIELDS:
            return self._json(400, {"error": "result packet fields do not match contract"})
        if any(not isinstance(payload[key], str) for key in SCS_RESULT_FIELDS):
            return self._json(400, {"error": "result packet values must be strings"})

        normalized = {key: payload[key].strip() for key in SCS_RESULT_FIELDS}
        normalized["STATUS"] = normalized["STATUS"].upper()
        task_id = normalized["task_id"]
        idempotency_key = normalized["idempotency_key"]
        status = normalized["STATUS"]
        if not SCS_TASK_ID_RE.fullmatch(task_id):
            return self._json(400, {"error": "invalid task_id"})
        if not SCS_KEY_RE.fullmatch(idempotency_key):
            return self._json(400, {"error": "invalid idempotency_key"})
        if status not in SCS_RESULT_STATES:
            return self._json(400, {"error": "invalid STATUS"})
        if status == "DONE" and (not normalized["TESTS"] or not normalized["RESULTS"]):
            return self._json(400, {"error": "DONE requires non-empty TESTS and RESULTS"})

        if not normalized["claim_id"].isdigit():
            return self._json(400, {"error": "invalid claim_id"})
        if status == "HEARTBEAT" and any(normalized[k] for k in
                ("ACTIONS", "FILES_CHANGED", "TESTS", "RESULTS", "BLOCKERS", "NEXT_ACTION")):
            return self._json(400, {"error": "heartbeat is contact only"})
        try:
            response = tasks.accept_worker_result(
                normalized, owner_agent=scs_agent_id(),
                key=_submission_storage_key(idempotency_key),
                fingerprint=_submission_fingerprint(normalized),
                scope=SCS_IDEMPOTENCY_SCOPE)
        except tasks.TaskError:
            return self._json(409, {"error": "task claim or idempotency conflict"})
        except Exception:
            return self._json(500, {"error": "handoff update failed; retry same packet"})
        # Persistence finished before attempting the network return.
        return self._json(200, {"ok": True, "data": response})

    def do_GET(self):  # noqa: N802
        parsed = urlsplit(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            if not self._authorized():
                return self._json(401, {"error": "unauthorized"})
            if path == SCS_TASK_PATH:
                if not scs_handoff_enabled():
                    return self._json(404, {"error": "not found"})
                return self._json(200, {"ok": True, "data": _claim_scs_task()})
            if path == "/api/v1/events":
                qs = parse_qs(parsed.query)
                try:
                    after_id = int((qs.get("after") or ["0"])[0])
                    limit = int((qs.get("limit") or ["100"])[0])
                except ValueError:
                    return self._json(400, {"error": "invalid event cursor"})
                return self._json(200, {"ok": True, "data": api.events(after_id, limit)})
            if path == "/api/v1/events/stream":
                qs = parse_qs(parsed.query)
                try:
                    after_id = int((qs.get("after") or ["0"])[0])
                except ValueError:
                    return self._json(400, {"error": "invalid event cursor"})
                once = (qs.get("once") or ["0"])[0] == "1"
                return self._sse(after_id=after_id, once=once)
            v1_fn = V1_ROUTES.get(path)
            if v1_fn:
                return self._json(200, {"ok": True, "data": v1_fn()})
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
        if path not in {"/api/command", SCS_RESULT_PATH}:
            return self._json(404, {"error": "not found"})
        if not self._authorized():
            return self._json(401, {"error": "unauthorized"})
        payload = self._read_json_payload()
        if payload is None:
            return
        if path == SCS_RESULT_PATH:
            return self._handle_scs_result(payload)
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
