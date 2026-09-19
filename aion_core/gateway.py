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
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from scitt_cose import CoseError, sign_sign1, verify_sign1
    from scitt_cose.cose_sign1 import strict_decode
except ImportError as exc:  # pragma: no cover - exercised by clean bootstrap
    raise RuntimeError("gateway dependencies are not installed; see requirements-gateway.txt") from exc

from . import approvals, db, security, tasks, util

SCHEMA = "lucyos.approval/1"
MAX_MESSAGE = 16 * 1024
MAX_LIFETIME = 15 * 60
ACTIVE = "ACTIVE"
CANDIDATE = "CANDIDATE"
ALLOWED_ACTIONS = {"status.read"}


class GatewayError(Exception):
    pass


def enabled() -> bool:
    return db.get_meta("scg_enabled", "0") == "1"


def set_enabled(value: bool) -> None:
    db.set_meta("scg_enabled", "1" if value else "0")
    db.log_event("owner", "gateway.enabled" if value else "gateway.disabled")


def fingerprint(public_key: bytes) -> str:
    if type(public_key) is not bytes or len(public_key) != 32:
        raise GatewayError("invalid public key")
    return hashlib.sha256(public_key).hexdigest()


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
    public_pem = Ed25519PublicKey.from_public_bytes(public_key).public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    conn.execute("INSERT INTO gateway_devices(device_id,owner_identity,public_key,key_version,enrolled_at) VALUES(?,?,?,?,?)",
                 (device_id, identity, public_pem, key_version, util.now()))
    conn.commit()


def propose_device(device_id: str, identity: str, public_key: bytes, key_version: int = 1) -> str:
    """Store public enrollment material only; owner confirmation is separate."""
    if not device_id or not identity or type(public_key) is not bytes or len(public_key) != 32:
        raise GatewayError("invalid enrollment candidate")
    conn = db.connect()
    pem = Ed25519PublicKey.from_public_bytes(public_key).public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    conn.execute("INSERT INTO gateway_devices(device_id,owner_identity,public_key,key_version,status,enrolled_at) VALUES(?,?,?,?,?,?)",
                 (device_id, identity, pem, key_version, CANDIDATE, util.now()))
    conn.commit()
    db.log_event("owner", "gateway.device.candidate", device_id, fingerprint(public_key))
    return fingerprint(public_key)


def confirm_device(device_id: str, confirmed_fingerprint: str) -> str:
    row = db.connect().execute("SELECT * FROM gateway_devices WHERE device_id=?", (device_id,)).fetchone()
    if row is None or row["status"] != CANDIDATE:
        raise GatewayError("no pending enrollment")
    actual = fingerprint(serialization.load_pem_public_key(bytes(row["public_key"])).public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    if confirmed_fingerprint != actual:
        raise GatewayError("fingerprint confirmation mismatch")
    db.connect().execute("UPDATE gateway_devices SET status=? WHERE device_id=?", (ACTIVE, device_id))
    db.connect().commit()
    db.log_event("owner", "gateway.device.enrolled", device_id, actual)
    return actual


def device_status() -> list[dict]:
    rows = db.connect().execute("SELECT device_id,owner_identity,key_version,epoch,status,enrolled_at,revoked_at FROM gateway_devices ORDER BY device_id").fetchall()
    return [dict(r) for r in rows]


def revoke_device(device_id: str, reason: str) -> None:
    conn = db.connect()
    cur = conn.execute("UPDATE gateway_devices SET status='REVOKED', epoch=epoch+1, revoked_at=?, revoke_reason=? WHERE device_id=? AND status=?",
                       (util.now(), security.redact(reason), device_id, ACTIVE))
    conn.commit()
    if not cur.rowcount:
        raise GatewayError("unknown or already revoked device")


def sign_operation(operation: dict, signing_seed: bytes) -> bytes:
    if type(signing_seed) is not bytes or len(signing_seed) != 32:
        raise GatewayError("invalid signing key")
    pem = Ed25519PrivateKey.from_private_bytes(signing_seed).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption())
    return sign_sign1(_payload(operation), alg="EdDSA", private_key_pem=pem)


def validate(message: bytes, parameters=None) -> dict:
    """Validate and atomically consume one exact-operation request."""
    if type(message) is not bytes or not message or len(message) > MAX_MESSAGE:
        raise GatewayError("malformed or oversized envelope")
    try:
        # Strictly parse only enough untrusted payload to locate the enrolled
        # key; all authority checks happen after signature verification.
        outer = strict_decode(message)
        values = outer.value
        if outer.tag != 18 or not isinstance(values, (list, tuple)) or len(values) != 4:
            raise GatewayError("malformed COSE envelope")
        operation = cbor2.loads(values[2])
    except Exception as exc:
        if isinstance(exc, GatewayError):
            raise
        raise GatewayError("malformed COSE envelope") from exc
    if not isinstance(operation, dict):
        raise GatewayError("payload must be a map")
    row = db.connect().execute("SELECT * FROM gateway_devices WHERE device_id=?", (operation["device_id"],)).fetchone()
    if row is None or row["status"] != ACTIVE or row["key_version"] != operation["key_version"] or row["epoch"] != operation["epoch"]:
        raise GatewayError("device is not enrolled at this epoch")
    try:
        msg = verify_sign1(message, public_key_pem=bytes(row["public_key"]))
        operation = cbor2.loads(msg.payload)
        if not isinstance(operation, dict):
            raise GatewayError("payload must be a map")
    except Exception as exc:
        if isinstance(exc, GatewayError):
            raise
        raise GatewayError("invalid signature or COSE envelope") from exc
    _payload(operation)
    if parameters is not None and operation["params_hash"] != parameters_hash(parameters):
        raise GatewayError("parameter digest mismatch")
    if operation["action"] not in ALLOWED_ACTIONS:
        raise GatewayError("capability is not allowlisted")
    if any(not isinstance(operation[k], (str, bytes, int)) and not (k == "target" and operation[k] is None)
           for k in operation):
        raise GatewayError("invalid payload types")
    now = _now()
    issued, expires = _parse_time(operation["issued_at"]), _parse_time(operation["expires_at"])
    if issued > now or expires <= now or (expires - issued).total_seconds() > MAX_LIFETIME:
        raise GatewayError("approval outside validity window")
    conn = db.connect()
    try:
        conn.execute("INSERT INTO gateway_nonces(nonce,request_id,device_id,expires_at,consumed_at) VALUES(?,?,?,?,?)",
                     (operation["nonce"], operation["request_id"], operation["device_id"], operation["expires_at"], util.now()))
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise GatewayError("replayed nonce or duplicate request") from exc
    return operation


def submit(message: bytes, *, title: str, parameters=None, **task_fields) -> str:
    """Validate once, create one canonical task, and attach existing approval policy."""
    if not enabled():
        raise GatewayError("SCG is disabled")
    operation = validate(message, parameters)
    digest = hashlib.sha256(_payload(operation)).digest()
    conn = db.connect()
    if conn.execute("SELECT 1 FROM gateway_requests WHERE request_id=?", (operation["request_id"],)).fetchone():
        raise GatewayError("duplicate request")
    risk = operation["risk_class"]
    status = "NEEDS_APPROVAL" if risk in {"R2", "R3"} else "READY"
    task_id = tasks.create(title, status=status, **task_fields)
    approval_id = None
    if status == "NEEDS_APPROVAL":
        approval_id = approvals.create(operation["action"], task_id=task_id,
                                       why="gateway exact-operation approval",
                                       resumes="execute approved capability")
    try:
        conn.execute("INSERT INTO gateway_requests(request_id,task_id,operation_hash,device_id,status,approval_id,created_at) VALUES(?,?,?,?,?,?,?)",
                     (operation["request_id"], task_id, digest, operation["device_id"], status, approval_id, util.now()))
        conn.commit()
    except Exception:
        # The existing task/approval remains auditable and must be reviewed; no retry is attempted.
        tasks.update(task_id, status="NEEDS_REVIEW", last_error="gateway request ledger write failed")
        raise GatewayError("gateway ledger write failed")
    return task_id
