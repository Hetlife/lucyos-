"""Contract C6 guard rails: temporary-worker scope narrowing and TTL.

This module gives C6 its enforcement primitives *before* anything can
create a bounded temporary worker -- it never spawns one itself.  There is
no insert/spawn function here at all; the additive `agents.parent_agent_id`
and `agents.expires_at` columns exist so a future spawn path has somewhere
to write, but this task deliberately stops short of writing to them.

- `derive()` computes the scope a child worker would be allowed: always the
  intersection of what the parent holds and what was requested, never a
  superset, regardless of what the child asked for.
- `is_expired()` / `assert_can_claim()` check TTL and scope fresh on every
  call -- reading a live `agents` row when given an agent_id -- never from
  a cache and never via a background sweeper (that would be a second
  scheduler, which anti-dup already forbids).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import db


class TempWorkerError(Exception):
    pass


def _parse_scope(text: str) -> set[str]:
    return {c.strip() for c in (text or "").split(",") if c.strip()}


def _coerce_scope(value) -> set[str]:
    if isinstance(value, str):
        return _parse_scope(value)
    return {str(v).strip() for v in value if str(v).strip()}


def derive(parent_scope, requested_scope, ttl_seconds: int) -> dict:
    """The scope granted to a child is the intersection of the parent's
    scope and the requested scope -- never a superset of either.  Chaining
    derive() calls (using a child's own granted `scope` as the next
    generation's parent_scope) keeps this narrowing transitive across any
    number of generations, since intersection can never grow."""
    if ttl_seconds <= 0:
        raise TempWorkerError(f"ttl_seconds must be positive, got {ttl_seconds!r}")
    parent = _coerce_scope(parent_scope)
    requested = _coerce_scope(requested_scope)
    granted = parent & requested
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=ttl_seconds)
    return {
        "scope": sorted(granted),
        "requested_scope": sorted(requested),
        "parent_scope": sorted(parent),
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "ttl_seconds": ttl_seconds,
    }


def _load(worker) -> dict:
    """Accept either a worker dict (e.g. from derive()) or an agent_id
    string naming a live row in the agents table.  A live lookup is always
    a fresh read of the current row -- never cached."""
    if isinstance(worker, dict):
        return worker
    row = db.connect().execute(
        "SELECT agent_id, capabilities, expires_at FROM agents WHERE agent_id=?",
        (worker,),
    ).fetchone()
    if row is None:
        raise TempWorkerError(f"no such agent {worker!r}")
    return {"scope": sorted(_parse_scope(row["capabilities"])), "expires_at": row["expires_at"]}


def is_expired(worker, *, now: datetime | None = None) -> bool:
    w = _load(worker)
    expires_at = w.get("expires_at")
    if not expires_at:
        return False  # no expiry recorded: not a bounded worker, never expires
    now = now or datetime.now(timezone.utc)
    return now >= datetime.fromisoformat(expires_at)


def assert_can_claim(worker, capability: str, *, now: datetime | None = None) -> None:
    """Refuse a claim from an expired worker, or one whose granted scope
    does not include the capability the claim requires."""
    w = _load(worker)
    if is_expired(w, now=now):
        raise TempWorkerError(f"worker expired at {w.get('expires_at')}; refusing claim")
    scope = set(w.get("scope") or [])
    if capability not in scope:
        raise TempWorkerError(
            f"worker scope {sorted(scope)} does not include {capability!r}; refusing claim"
        )
