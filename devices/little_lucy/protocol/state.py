"""Strict, display-safe LUCY_STATE v1 wire contract."""
import json
import re
import time

STATES = frozenset("SLEEP WAKE IDLE LISTEN THINK WORK VERIFY SUCCESS NEEDS_YOU OFFLINE".split())
SCHEMA_VERSION = 1
MAX_AGE_SECONDS = 15
_SAFE = re.compile(r"^[A-Za-z0-9 .,!?':;()/-]*$")


def validate(payload, now=None):
    """Return a minimal sanitized state, rejecting unknown fields and unsafe text."""
    if not isinstance(payload, dict) or set(payload) != {"version", "sequence", "timestamp", "state", "status"}:
        raise ValueError("invalid LUCY_STATE fields")
    if type(payload["version"]) is not int or payload["version"] != SCHEMA_VERSION:
        raise ValueError("unsupported version")
    if type(payload["sequence"]) is not int or payload["sequence"] < 0:
        raise ValueError("invalid sequence")
    if type(payload["timestamp"]) not in (int, float):
        raise ValueError("invalid timestamp")
    if payload["state"] not in STATES:
        raise ValueError("invalid state")
    status = payload["status"]
    if not isinstance(status, str) or len(status) > 48 or not _SAFE.fullmatch(status):
        raise ValueError("unsafe status")
    if abs(payload["timestamp"] - (now if now is not None else time.time())) > MAX_AGE_SECONDS:
        raise ValueError("stale state")
    return dict(payload)


def encode(payload, now=None):
    return json.dumps(validate(payload, now), separators=(",", ":"), sort_keys=True).encode("utf-8")


def decode(data, now=None):
    if len(data) > 512:
        raise ValueError("oversize state")
    return validate(json.loads(data), now)
