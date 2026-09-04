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

from . import bootstrap, db

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
import urllib.parse
import urllib.request

CACHE_SECONDS = 60
_cache: dict = {"at": 0.0, "brief": None, "error": None}


class SevaaError(Exception):
    pass


def base_url() -> str:
    return bootstrap.get_secret(BASE_URL_ENV) or os.environ.get(BASE_URL_ENV, "").strip() \
        or "http://127.0.0.1:8000"


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _require_safe_transport(url: str) -> None:
    """Refuse to send a bearer token over plain HTTP to anything but loopback.

    Every call in this module that carries a token goes through this first.
    Loopback stays plain HTTP for local development; anything else must be
    HTTPS, because SEVAA_BASE_URL is exactly the kind of setting a founder
    could point at a real deployment without noticing the scheme.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname in _LOOPBACK_HOSTS:
        return
    if parsed.scheme != "https":
        raise SevaaError(
            f"refusing to send a token to {parsed.scheme}://{parsed.hostname} -- "
            f"set {BASE_URL_ENV} to an https:// URL (loopback is the only http:// exception)")


def automation_token() -> str | None:
    return bootstrap.get_secret(AUTOMATION_TOKEN_NAME) or os.environ.get(AUTOMATION_TOKEN_NAME) or None


def founder_token() -> str | None:
    return bootstrap.get_secret(FOUNDER_TOKEN_NAME) or os.environ.get(FOUNDER_TOKEN_NAME) or None


def _get(path: str, token: str, timeout: float = 5.0) -> dict:
    url = base_url().rstrip("/") + path
    _require_safe_transport(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        url,
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
    except (SevaaError, urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {"ok": False, "error": str(exc) if isinstance(exc, SevaaError) else exc.__class__.__name__}
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


# --- S09: verified SEVAA payments -> AION M0 -----------------------------
#
# Reads GET /api/v2/payment-links with the automation token. That response
# includes lead_name/lead_company (a pre-existing SEVAA characteristic, not
# introduced here); this function reads only id, provider, provider_payment_id,
# provider_payment_link_id, paid_amount and status, and never forwards the
# lead fields into AION state -- record_money's description/evidence carry
# only the payment reference, never a name or company.
#
# KNOWN GAP (recorded, not hidden): SEVAA's payment-links API does not
# currently expose whether the configured Razorpay credentials are test or
# live. This function marks a link ACTUAL revenue on status=='paid' alone,
# because that is the only verified signal SEVAA exposes today -- 'paid' is
# already provider-reconciled inside SEVAA's own webhook/refresh path
# (backend/revenue.py::_mark_paid), not a client-side claim. If the founder
# ever runs a Razorpay TEST key against a production-reachable deployment, a
# test payment would flip to 'paid' and be indistinguishable here from a real
# one. See AION_ADVERSARIAL_REVIEW.md finding F8.

def list_payment_links() -> list[dict]:
    token = automation_token()
    if not token:
        raise SevaaError(f"{AUTOMATION_TOKEN_NAME} not configured")
    return _get("/api/v2/payment-links", token)


def reconcile_payments() -> dict:
    """Record newly verified-paid links as ACTUAL revenue.  Idempotent per link."""
    from . import metrics  # local import: avoids a cycle at module load time

    try:
        links = list_payment_links()
    except (SevaaError, urllib.error.URLError, urllib.error.HTTPError, OSError,
            ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": exc.__class__.__name__, "recorded": []}

    recorded = []
    for link in links:
        if link.get("status") != "paid":
            continue
        amount = int(link.get("paid_amount") or 0)
        if amount <= 0:
            continue
        link_id = link.get("id")
        key = f"sevaa:payment_link:{link_id}"
        if db.seen(key, "sevaa_payment"):
            continue
        provider = link.get("provider", "unknown")
        provider_payment_id = link.get("provider_payment_id") or link.get("provider_payment_link_id") or "n/a"
        metrics.record_money(
            "revenue", amount, stage="ACTUAL", project="sevaa-sales-os",
            description=f"SEVAA payment link #{link_id} ({provider})",
            evidence=f"sevaa:payment_link:{link_id}:{provider}:{provider_payment_id}",
        )
        recorded.append({"link_id": link_id, "amount_inr": amount})
    return {"ok": True, "recorded": recorded}


# --- S02: founder approvals from WhatsApp --------------------------------
#
# Two distinct tokens, two distinct powers. list_pending_approvals() reads
# with the automation token (read-only). decide_approval() is the ONLY place
# in AION that reads the founder token, and it is read fresh on every call --
# never cached, never logged, never placed in a return value that could reach
# a report. The founder token grants the one truly consequential action in
# this whole integration (approve/reject real money), so it gets the
# narrowest possible surface: one function, one call, token read and used in
# the same expression.

EXTERNAL_REF_PREFIX = "sevaa:approval:"


def list_pending_approvals() -> list[dict]:
    token = automation_token()
    if not token:
        raise SevaaError(f"{AUTOMATION_TOKEN_NAME} not configured")
    return _get("/api/v2/approvals?status=pending", token)


def decide_approval(sevaa_approval_id: int, decision: str, note: str = "") -> dict:
    """decision must be 'approved' or 'rejected' -- SEVAA's own literal values."""
    if decision not in ("approved", "rejected"):
        raise SevaaError(f"invalid decision {decision!r}; must be 'approved' or 'rejected'")
    token = founder_token()
    if not token:
        raise SevaaError(f"{FOUNDER_TOKEN_NAME} not configured")
    url = base_url().rstrip("/") + f"/api/v2/approvals/{sevaa_approval_id}/decision"
    _require_safe_transport(url)
    body = json.dumps({"decision": decision, "note": note[:1000] if note else None}).encode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(
        url,
        data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "X-Actor": "founder-via-whatsapp",
                 "Content-Type": "application/json"},
    )
    with opener.open(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))
