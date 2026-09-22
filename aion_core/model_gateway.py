"""LucyOS auxiliary external-model gateway.

Free-tier providers are supplemental compute for small PUBLIC tasks. They never
replace the Resource Governor, secret store, task queue, or main cloud worker.
No provider is called unless a legitimate owner-supplied API key exists.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from . import config, db, security

PROVIDERS = {
    "openrouter_free": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "secret": "OPENROUTER_API_KEY",
        "default_model": "openrouter/free",
        "model_meta": "provider.openrouter_free.model",
        "cost_class": "E0",
    },
    "groq_free": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "secret": "GROQ_API_KEY",
        "default_model": "",
        "model_meta": "provider.groq_free.model",
        "cost_class": "E0",
    },
    "cerebras_free": {
        "endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "secret": "CEREBRAS_API_KEY",
        "default_model": "",
        "model_meta": "provider.cerebras_free.model",
        # Cerebras currently offers trial credit before paid Developer usage.
        # Keep the integration visible, but never auto-route it through this
        # zero-cost-only gateway. A paid path needs a separate owner gate.
        "cost_class": "E1",
    },
}
DATA_POLICY = {"PUBLIC": True, "INTERNAL": False, "CONFIDENTIAL": False, "SECRET": False}
FAILURE_LIMIT = 3
COOLDOWN_SECONDS = 15 * 60


def _secret(name: str) -> str:
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


def _model(provider_id: str) -> str:
    spec = PROVIDERS[provider_id]
    return (db.get_meta(spec["model_meta"], "") or spec["default_model"]).strip()


def provider_status() -> list[dict]:
    now = int(time.time())
    out = []
    for pid, spec in PROVIDERS.items():
        failures = int(db.get_meta(f"provider.{pid}.failures", "0") or 0)
        open_until = int(db.get_meta(f"provider.{pid}.open_until", "0") or 0)
        model = _model(pid)
        out.append({
            "provider": pid,
            "configured": bool(_secret(spec["secret"])) and bool(model),
            "model": model,
            "circuit_open": open_until > now,
            "failures": failures,
            "cost_class": spec["cost_class"],
            "allowed_data": [k for k, allowed in DATA_POLICY.items() if allowed],
        })
    return out


def eligible(*, data_class: str = "PUBLIC") -> list[str]:
    dc = data_class.upper()
    if not DATA_POLICY.get(dc, False):
        return []
    return [x["provider"] for x in provider_status()
            if x["configured"] and not x["circuit_open"] and x["cost_class"] == "E0"]


def _mark_success(provider_id: str) -> None:
    db.set_meta(f"provider.{provider_id}.failures", "0")
    db.set_meta(f"provider.{provider_id}.open_until", "0")


def _mark_failure(provider_id: str, detail: str) -> None:
    failures = int(db.get_meta(f"provider.{provider_id}.failures", "0") or 0) + 1
    db.set_meta(f"provider.{provider_id}.failures", str(failures))
    if failures >= FAILURE_LIMIT:
        db.set_meta(f"provider.{provider_id}.open_until", str(int(time.time()) + COOLDOWN_SECONDS))
    db.log_event("model_gateway", "provider.failure", provider_id, security.redact(detail)[:300])


def _http_json(req: urllib.request.Request, timeout: int) -> dict:
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def complete(prompt: str, *, data_class: str = "PUBLIC", max_tokens: int = 384,
             provider: str | None = None, timeout: int = 30, transport=_http_json,
             task_id: str | None = None) -> dict:
    """Run a bounded auxiliary completion with deterministic failover."""
    if not prompt.strip():
        raise ValueError("prompt is empty")
    dc = data_class.upper()
    if not DATA_POLICY.get(dc, False):
        raise PermissionError(f"auxiliary free providers are not permitted for {dc} data")
    candidates = [provider] if provider else eligible(data_class=dc)
    if provider and provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider}")
    if provider and PROVIDERS[provider]["cost_class"] != "E0":
        raise PermissionError(f"provider {provider} is not guaranteed zero-cost; owner approval is required")
    if not candidates:
        return {"ok": False, "reason": "no eligible configured free provider", "attempted": []}
    attempted = []
    for pid in candidates:
        if pid not in PROVIDERS:
            continue
        spec = PROVIDERS[pid]
        key, model = _secret(spec["secret"]), _model(pid)
        if not key or not model:
            attempted.append({"provider": pid, "ok": False, "reason": "not configured"})
            continue
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(max_tokens),
            "temperature": 0,
        }).encode("utf-8")
        req = urllib.request.Request(spec["endpoint"], data=payload, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "User-Agent": "LucyOS-Auxiliary-Gateway/1",
        })
        try:
            result = transport(req, timeout)
            text = str(result["choices"][0]["message"]["content"])
            usage = result.get("usage") or {}
            _mark_success(pid)
            db.log_event("model_gateway", "provider.success", pid, model)
            return {"ok": True, "provider": pid, "model": model, "text": text,
                    "usage": usage, "attempted": attempted + [{"provider": pid, "ok": True}]}
        except Exception as exc:
            detail = security.redact(str(exc))
            _mark_failure(pid, detail)
            attempted.append({"provider": pid, "ok": False, "reason": detail[:300]})
    return {"ok": False, "reason": "all eligible auxiliary providers failed", "attempted": attempted}
