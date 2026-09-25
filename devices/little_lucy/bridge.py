"""Authenticated laptop-side Lucy-Nest bridge.

This repo-owned source is intentionally inactive until a deployment task
approves replacing the currently running external copy. It reuses LucyOS's
canonical task and approval engines; it does not create another state store.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import ssl
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LUCYOS_REPO = Path(os.environ.get("LUCYOS_REPO", str(REPO_ROOT))).resolve()
if str(LUCYOS_REPO) not in sys.path:
    sys.path.insert(0, str(LUCYOS_REPO))

from aion_core import approvals, config, db, security, tasks  # noqa: E402

LOCK = threading.RLock()
APPROVAL_FIELDS = (
    "approval_id", "action", "why", "cost", "max_downside",
    "expected_benefit", "reversibility", "resumes", "task_id",
)


def _revision(row: Any) -> str:
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest()


def card(row: Any) -> dict[str, str]:
    """Return a redacted approval card and an opaque freshness revision."""
    result = {key: security.redact(str(row[key] or "Not specified")) for key in APPROVAL_FIELDS}
    result["revision"] = _revision(row)
    return result


def snapshot() -> dict[str, Any]:
    """Project only display-safe task and approval state from canonical AION."""
    with LOCK:
        connection = db.connect()
        counts = tasks.counts()
        active = []
        for row in connection.execute(
            "SELECT task_id,title,status,updated_at FROM tasks "
            "WHERE status IN ('RUNNING','VERIFYING') "
            "ORDER BY updated_at DESC LIMIT 5"
        ):
            item = dict(row)
            for key in ("task_id", "title", "status"):
                item[key] = security.redact(str(item.get(key) or ""))
            active.append(item)
        latest = connection.execute("SELECT MAX(updated_at) FROM tasks").fetchone()[0]
        return {
            "as_of": time.time(),
            "source": "LucyOS / this laptop",
            "counts": counts,
            "active": active,
            "last_task_update": latest,
            "paused": db.get_meta("paused", "0") == "1",
            "safe_mode": db.get_meta("safe_mode", "0") == "1",
            "approvals": [card(row) for row in approvals.pending()],
        }


def decide(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply one fresh, explicit owner decision to the canonical approval row."""
    if not isinstance(payload, dict) or payload.get("decision") not in {"APPROVED", "DENIED"}:
        raise ValueError("Invalid decision")
    with LOCK:
        row = approvals.get(str(payload.get("approval_id", "")))
        if row is None or row["status"] != "PENDING":
            raise ValueError("Request already resolved or unavailable. Refresh.")
        if not hmac.compare_digest(card(row)["revision"], str(payload.get("revision", ""))):
            raise ValueError("Request changed. Review it again.")
        return approvals.decide(row["approval_id"], payload["decision"], by="Het via Lucy Nest")


class Handler(BaseHTTPRequestHandler):
    """A narrow TLS bridge: status read and explicit decision write only."""

    def reply(self, code: int, body: dict[str, Any]) -> None:
        data = security.redact(json.dumps(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied, "Bearer " + self.server.auth_value)

    def do_GET(self) -> None:
        if not self.authorized():
            self.reply(401, {"error": "Unauthorized"})
            return
        if self.path != "/status":
            self.reply(404, {"error": "Not found"})
            return
        try:
            self.reply(200, snapshot())
        except Exception:
            self.reply(503, {"error": "LucyOS status unavailable"})

    def do_POST(self) -> None:
        if not self.authorized():
            self.reply(401, {"error": "Unauthorized"})
            return
        if self.path != "/decision":
            self.reply(404, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Invalid request")
            self.reply(200, decide(payload))
        except (ValueError, approvals.ApprovalError) as exc:
            self.reply(409, {"error": str(exc)})
        except Exception:
            self.reply(503, {"error": "Decision not confirmed. Refresh before trying again."})

    def log_message(self, *args: Any) -> None:
        return


def main() -> None:
    private = Path(os.environ["NEST_PRIVATE"])
    host = os.environ.get("LUCY_NEST_BIND_HOST", "192.168.31.125")
    port = int(os.environ.get("LUCY_NEST_BIND_PORT", "18792"))
    pairing_file = private / "token"
    cert_path = private / "server.crt"
    key_path = private / "server.key"
    if not config.db_path().is_file():
        raise SystemExit("Existing LucyOS database required")
    if not pairing_file.is_file() or not cert_path.is_file() or not key_path.is_file():
        raise SystemExit("Lucy-Nest pairing material is incomplete")
    db.connect()
    server = HTTPServer((host, port), Handler)
    server.auth_value = pairing_file.read_text(encoding="utf-8").strip()
    if not server.auth_value:
        raise SystemExit("Lucy-Nest pairing token is empty")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert_path), str(key_path))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f"Nest bridge ready; existing laptop state; TLS on {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
