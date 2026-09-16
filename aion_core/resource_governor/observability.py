"""One place to ask "how are we doing on AI capacity right now" (directive section 25).

This is read-only and defensive by construction: every piece it aggregates
(`providers.read_all`, `providers.read_local`, `burn_rate`, `checkpoint`) is
already safe against its own failures, and `snapshot()` never raises — a
crash anywhere inside becomes a single UNKNOWN entry rather than an
exception that could take down `health.run_all()` or `reports.status()`.
"""
from __future__ import annotations

from .. import db, util
from . import burn_rate, checkpoint, flags, providers, schema
from . import state as state_mod


def provider_snapshot(name: str, resource: dict) -> dict:
    reset_at = (resource.get("quota") or {}).get("reset_at")
    rate = burn_rate.best_estimate(name)
    minutes = burn_rate.minutes_to_reset(reset_at)
    resource = dict(resource)
    resource["state"] = state_mod.classify(
        resource, minutes_to_reset=minutes, tokens_per_minute=rate.get("tokens_per_minute"))
    resource["burn_rate"] = {
        "tokens_per_minute": rate.get("tokens_per_minute"),
        "quota_pct_per_minute": rate.get("quota_pct_per_minute"),
        "window": rate.get("window"),
    }
    resource["minutes_to_reset"] = minutes
    resource["remaining_pct"] = schema.remaining_pct(resource)
    return resource


def snapshot(*, persist: bool = False) -> dict:
    try:
        raw = providers.read_all()
    except Exception as exc:  # noqa: BLE001 - observability must never crash a caller
        raw = {}
        db.log_event("resource_governor", "observability.error", "", str(exc)[:200])
    enriched = {}
    for name, resource in raw.items():
        try:
            enriched[name] = provider_snapshot(name, resource)
        except Exception as exc:  # noqa: BLE001
            enriched[name] = {**resource, "state": "UNKNOWN", "error": str(exc)[:200]}

    try:
        local = providers.read_local()
    except Exception as exc:  # noqa: BLE001
        local = {"provider": "local", "available": False, "confidence": "UNKNOWN",
                "error": str(exc)[:200]}

    try:
        waiting = [r["task_id"] for r in checkpoint.waiting_tasks()]
    except Exception:  # noqa: BLE001
        waiting = []

    result = {
        "at": util.now(),
        "enabled": flags.flag("resource_governor.enabled"),
        "providers": enriched,
        "local": local,
        "overall_state": state_mod.overall(enriched),
        "waiting_for_resource": waiting,
        "flags": flags.all_flags(),
    }
    if persist:
        _persist(enriched)
    return result


def _persist(enriched: dict) -> None:
    conn = db.connect()
    for name, r in enriched.items():
        ctx = r.get("context") or {}
        q = r.get("quota") or {}
        ou = r.get("observed_usage") or {}
        conn.execute(
            "INSERT INTO resource_snapshots(at, day, provider, model, context_used_tokens, "
            "context_limit_tokens, context_used_pct, quota_window, quota_used_pct, "
            "quota_remaining_pct, quota_reset_at, input_tokens, output_tokens, "
            "cache_read_tokens, cache_write_tokens, confidence, source, state) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (util.now(), util.today(), name, r.get("model"), ctx.get("used_tokens"),
             ctx.get("limit_tokens"), ctx.get("used_pct"), q.get("window"), q.get("used_pct"),
             q.get("remaining_pct"), q.get("reset_at"), ou.get("input_tokens"),
             ou.get("output_tokens"), ou.get("cache_read_tokens"), ou.get("cache_write_tokens"),
             r.get("confidence"), r.get("source", ""), r.get("state", "UNKNOWN")))
    conn.commit()


def render(snap: dict | None = None) -> str:
    snap = snap if snap is not None else snapshot()
    lines = ["RESOURCE GOVERNOR", ""]
    for name, r in snap["providers"].items():
        pct = r.get("remaining_pct")
        bit = f"{name}: {r['state']} · confidence {r['confidence']}"
        bit += f" · {pct}% remaining" if pct is not None else " · remaining unknown"
        reset_at = (r.get("quota") or {}).get("reset_at")
        if reset_at:
            bit += f" · resets {reset_at}"
        lines.append(bit)
    local = snap["local"]
    lines.append("local model: " + ("available" if local.get("available") else "unavailable")
                 + (f" ({local.get('model')})" if local.get("available") else ""))
    lines.append(f"overall: {snap['overall_state']}")
    if snap["waiting_for_resource"]:
        lines.append(f"waiting for resource: {', '.join(snap['waiting_for_resource'])}")
    if not snap["enabled"]:
        lines.append("(resource_governor.enabled is off — observability only, nothing enforced)")
    return "\n".join(lines)
