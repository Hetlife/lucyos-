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


# --- S07: SEVAA figures inside AION status/today ------------------------
#
# Uses the automation token only (never the founder token — that is reserved
# for S02's approval decisions).  Every field surfaced here is a count from
# /api/v2/internal/daily-brief, which itself carries no PII (checked against
# its actual FastAPI handler in the SEVAA repo).  Nothing from /api/v2/approvals
# or /api/v2/followups — which DO include lead_name/lead_company — is ever
# read here or forwarded into a report; S02 (a separate task) is the only
# place those individual objects are touched, and even there only an
# approval's action text, never the lead identity.

import json
import time
import urllib.error
import urllib.request

from . import bootstrap

CACHE_SECONDS = 60
_cache: dict = {"at": 0.0, "brief": None, "error": None}


class SevaaError(Exception):
    pass


def base_url() -> str:
    return bootstrap.get_secret(BASE_URL_ENV) or os.environ.get(BASE_URL_ENV, "").strip() \
        or "http://127.0.0.1:8000"


def automation_token() -> str | None:
    return bootstrap.get_secret(AUTOMATION_TOKEN_NAME) or os.environ.get(AUTOMATION_TOKEN_NAME) or None


def founder_token() -> str | None:
    return bootstrap.get_secret(FOUNDER_TOKEN_NAME) or os.environ.get(FOUNDER_TOKEN_NAME) or None


def _get(path: str, token: str, timeout: float = 5.0) -> dict:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        base_url().rstrip("/") + path,
        headers={"Authorization": f"Bearer {token}", "X-Actor": "aion-automation"},
        method="GET",
    )
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def daily_brief(*, force: bool = False) -> dict:
    """Cached counts from SEVAA.  Never raises; failure is a normal, visible state."""
    now = time.monotonic()
    if not force and _cache["brief"] is not None and (now - _cache["at"]) < CACHE_SECONDS:
        return _cache["brief"]
    token = automation_token()
    if not token:
        result = {"ok": False, "error": f"{AUTOMATION_TOKEN_NAME} not configured"}
        _cache.update(at=now, brief=result, error=result["error"])
        return result
    try:
        data = _get("/api/v2/internal/daily-brief", token)
        result = {
            "ok": True,
            "new_leads": data.get("new_leads", 0),
            "proposals_awaiting_approval": data.get("proposals_awaiting_approval", 0),
            "overdue_followups": data.get("overdue_followups", 0),
            "fetched_at": now,
        }
        _cache.update(at=now, brief=result, error=None)
        return result
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"ok": False, "error": exc.__class__.__name__}
        # Keep the timestamp of the last successful fetch out of this error
        # result on purpose: `status` must say "unreachable", not stale numbers.
        _cache.update(at=now, brief=result, error=result["error"])
        return result


def status_line() -> str:
    """One line for aion status/today.  Never silently omits an outage."""
    brief = daily_brief()
    if not brief.get("ok"):
        since = time.strftime("%H:%M:%S", time.gmtime())
        return f"SEVAA: unreachable ({brief.get('error', 'unknown error')})"
    return (f"SEVAA: {brief['new_leads']} new enquiries, "
            f"{brief['proposals_awaiting_approval']} approvals pending, "
            f"{brief['overdue_followups']} follow-ups overdue")
