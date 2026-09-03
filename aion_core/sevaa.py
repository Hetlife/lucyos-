"""SEVAA Sales OS ↔ AION integration contract.

This is the single place the wire contract is written down.  The SEVAA side is
tested against exactly these names; change them here and there in one task.

Security posture:
  * Every inbound event is HMAC-signed over the raw body with a shared secret
    that lives only in the PC's 0600 secret store.  Unsigned or badly signed
    events are rejected before they are parsed.
  * The payload is PII-free by construction: an allow-list of keys is enforced
    on receipt and a forbidden-list is asserted in tests on both sides, so a
    lead's name, phone, email or company can never reach WhatsApp.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from . import bootstrap

# --- wire contract ---------------------------------------------------------
SIGNATURE_HEADER = "X-Sevaa-Signature"          # value: "sha256=<hex hmac>"
SECRET_NAME = "SEVAA_NOTIFY_WEBHOOK_SECRET"      # in the AION secret store / env
EVENT_ENQUIRY_CREATED = "enquiry.created"
EVENT_ALLOWED_KEYS = frozenset({
    "type", "lead_id", "score", "stage", "city", "source", "requirement_summary", "created_at",
})
EVENT_FORBIDDEN_KEYS = frozenset({"name", "phone", "email", "company"})
REQUIREMENT_SUMMARY_MAX = 80

# Env/secret names the PC needs for every S-task (S07, S02, S09 read these too).
BASE_URL_ENV = "SEVAA_BASE_URL"
AUTOMATION_TOKEN_NAME = "SEVAA_AUTOMATION_TOKEN"
FOUNDER_TOKEN_NAME = "SEVAA_FOUNDER_TOKEN"


def secret() -> str | None:
    """Shared webhook key: the store on the PC first, the environment second."""
    return bootstrap.get_secret(SECRET_NAME) or os.environ.get(SECRET_NAME) or None


def sign(body: bytes, key: str) -> str:
    digest = hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify(body: bytes, header_value: str | None, key: str | None) -> bool:
    """Constant-time check.  A missing key means nothing is ever accepted."""
    if not key or not header_value:
        return False
    expected = sign(body, key)
    return hmac.compare_digest(expected, header_value.strip())


def validate_event(event: dict) -> list[str]:
    """Return problems.  Empty means the event may enter state."""
    problems = []
    if not isinstance(event, dict):
        return ["event must be an object"]
    keys = set(event)
    forbidden = sorted(keys & EVENT_FORBIDDEN_KEYS)
    if forbidden:
        problems.append(f"forbidden PII keys present: {', '.join(forbidden)}")
    unknown = sorted(keys - EVENT_ALLOWED_KEYS - EVENT_FORBIDDEN_KEYS)
    if unknown:
        problems.append(f"unknown keys: {', '.join(unknown)}")
    if event.get("type") != EVENT_ENQUIRY_CREATED:
        problems.append(f"unsupported type {event.get('type')!r}")
    if not isinstance(event.get("lead_id"), int) or event["lead_id"] <= 0:
        problems.append("lead_id must be a positive integer")
    summary = event.get("requirement_summary")
    if summary is not None and (not isinstance(summary, str) or len(summary) > REQUIREMENT_SUMMARY_MAX):
        problems.append(f"requirement_summary must be a string of at most {REQUIREMENT_SUMMARY_MAX} chars")
    return problems
