"""Fail-closed COSE_Sign1 request validation for the Phase-1 gateway.

This module is deliberately a validator/authority seam, not a second queue or
executor. It accepts only bounded COSE_Sign1 messages, verifies an enrolled
Ed25519 device, binds the exact canonical operation, and atomically consumes a
nonce. Task creation remains the caller's existing ``tasks.create`` path.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

try:
    import cbor2
    from pycose.algorithms import EdDSA
    from pycose.headers import Algorithm
    from pycose.keys import OKPKey
    from pycose.messages import Sign1Message
except ImportError as exc:  # pragma: no cover - exercised by clean bootstrap
    raise RuntimeError("gateway dependencies are not installed; see requirements-gateway.txt") from exc

from . import db, security, util

SCHEMA = "lucyos.approval/1"
MAX_MESSAGE = 16 * 1024
MAX_LIFETIME = 15 * 60
ACTIVE = "ACTIVE"


class GatewayError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise GatewayError("invalid timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise GatewayError("invalid timestamp") from exc


def canonical_parameters(parameters) -> bytes:
    try:
        return cbor2.dumps(parameters, canonical=True)
    except Exception as exc:
        raise GatewayError("parameters are not canonicalizable") from exc


def parameters_hash(parameters) -> bytes:
    return hashlib.sha256(canonical_parameters(parameters)).digest()


def _payload(operation: dict) -> bytes:
    required = {
        "schema", "request_id", "action", "params_hash", "target", "risk_class",
        "capability", "device_id", "key_version", "identity", "nonce",
        "issued_at", "expires_at", "policy", "approval_id", "epoch",
    }
    if set(operation) != required:
        raise GatewayError("approval fields must be exact")
    return cbor2.dumps(operation, canonical=True)


def new_nonce() -> bytes:
    return secrets.token_bytes(32)


def register_device(device_id: str, identity: str, public_key: bytes, key_version: int = 1) -> None:
    if not device_id or not identity or type(public_key) is not bytes or len(public_key) != 32:
        raise GatewayError("invalid device enrollment")
    if not isinstance(key_version, int) or key_version < 1:
        raise GatewayError("invalid key version")
    conn = db.connect()
    conn.execute("INSERT INTO gateway_devices(device_id,owner_identity,public_key,key_version,enrolled_at) VALUES(?,?,?,?,?)",
                 (device_id, identity, public_key, key_version, util.now()))
    conn.commit()


def revoke_device(device_id: str, reason: str) -> None:
    conn = db.connect()
    cur = conn.execute("UPDATE gateway_devices SET status='REVOKED', epoch=epoch+1, revoked_at=?, revoke_reason=? WHERE device_id=? AND status=?",
                       (util.now(), security.redact(reason), device_id, ACTIVE))
    conn.commit()
    if not cur.rowcount:
        raise GatewayError("unknown or already revoked device")


def sign_operation(operation: dict, private_key: bytes) -> bytes:
    if type(private_key) is not bytes or len(private_key) != 32:
        raise GatewayError("invalid signing key")
    msg = Sign1Message(phdr={1: EdDSA}, payload=_payload(operation))
    msg.key = OKPKey(crv=6, d=private_key)
    return msg.encode()


def validate(message: bytes, parameters=None) -> dict:
    """Validate and atomically consume one exact-operation request."""
    if type(message) is not bytes or not message or len(message) > MAX_MESSAGE:
        raise GatewayError("malformed or oversized envelope")
    try:
        msg = Sign1Message.decode(message)
        algorithm = msg.phdr.get(Algorithm)
        if getattr(algorithm, "identifier", algorithm) != EdDSA.identifier or not isinstance(msg.payload, bytes):
            raise GatewayError("unsupported COSE algorithm or payload")
        operation = cbor2.loads(msg.payload)
    except GatewayError:
        raise
    except Exception as exc:
        raise GatewayError("malformed COSE envelope") from exc
    if not isinstance(operation, dict):
        raise GatewayError("payload must be a map")
    _payload(operation)
    if parameters is not None and operation["params_hash"] != parameters_hash(parameters):
        raise GatewayError("parameter digest mismatch")
    if any(not isinstance(operation[k], (str, bytes, int)) and not (k == "target" and operation[k] is None)
           for k in operation):
        raise GatewayError("invalid payload types")
    now = _now()
    issued, expires = _parse_time(operation["issued_at"]), _parse_time(operation["expires_at"])
    if issued > now or expires <= now or (expires - issued).total_seconds() > MAX_LIFETIME:
        raise GatewayError("approval outside validity window")
    row = db.connect().execute("SELECT * FROM gateway_devices WHERE device_id=?", (operation["device_id"],)).fetchone()
    if row is None or row["status"] != ACTIVE or row["key_version"] != operation["key_version"] or row["epoch"] != operation["epoch"]:
        raise GatewayError("device is not enrolled at this epoch")
    msg.key = OKPKey(crv=6, x=bytes(row["public_key"]))
    try:
        if not msg.verify_signature():
            raise GatewayError("invalid signature")
    except GatewayError:
        raise
    except Exception as exc:
        raise GatewayError("invalid signature") from exc
    conn = db.connect()
    try:
        conn.execute("INSERT INTO gateway_nonces(nonce,request_id,device_id,expires_at,consumed_at) VALUES(?,?,?,?,?)",
                     (operation["nonce"], operation["request_id"], operation["device_id"], operation["expires_at"], util.now()))
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise GatewayError("replayed nonce or duplicate request") from exc
    return operation
