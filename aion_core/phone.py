"""Structured JSON API for the phone interface.

WhatsApp gets preformatted text (aion_core/reports.py); the phone gets
structured data so the page can render money-first, a real feed, and
one-tap approval/feedback cards instead of a wall of text.

Every function here returns plain dicts/lists of JSON-safe values and passes
through security.redact on every string, exactly like the WhatsApp path.
"""
from __future__ import annotations

from . import (approvals, config, db, errors, governor, health, intake, memory,
               metrics, router, security, tasks, util)


def _clean(v):
    if isinstance(v, str):
        return security.redact(v)
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def dashboard() -> dict:
    """The whole first screen in one call: money, feed, needs-you."""
    m = metrics.money()
    by_proj = metrics.by_project()
    trend = metrics.trend(7)
    hstate = util.read_json(config.home() / "state" / "HEALTH.json", default={}) or {}

    pend = [approval_card(a) for a in approvals.pending()]
    blocked_tasks = [
        {"task_id": t["task_id"], "title": t["title"], "status": t["status"],
         "reason": t["last_error"] or t["blockers"] or "no reason recorded"}
        for t in tasks.blocked() if t["status"] != "NEEDS_APPROVAL"
    ]
    feedback_needed = [
        {"task_id": t["task_id"], "title": t["title"],
         "why": t["description"][:200] if t["description"] else ""}
        for t in tasks.by_status("NEEDS_REVIEW")
    ]

    alert = governor.pending_alert()

    return _clean({
        "as_of": util.now(),
        "healthy": hstate.get("healthy"),
        "mission_target_inr": 100000.0,
        "money": {
            "real_revenue_inr": m["real_revenue_inr"],
            "real_cost_inr": m["real_cost_inr"],
            "real_net_inr": m["real_net_inr"],
            "reserve_inr": m["reserve_inr"],
            "trend_7d": trend,
            "by_project": by_proj,
            "non_actual": m["non_actual"],
        },
        "feed": intake.feed(20),
        "needs_you": {
            "approvals": pend,
            "blocked_tasks": blocked_tasks,
            "feedback_needed": feedback_needed,
        },
        "governor_alert": alert,
    })


def approval_card(row) -> dict:
    return {
        "approval_id": row["approval_id"], "action": row["action"], "why": row["why"],
        "cost": row["cost"], "max_downside": row["max_downside"],
        "expected_benefit": row["expected_benefit"], "reversibility": row["reversibility"],
        "prepared": row["prepared"], "resumes": row["resumes"],
        "recommendation": row["recommendation"], "created_at": row["created_at"],
    }


def task_list(limit: int = 20) -> list[dict]:
    rows = tasks.ready(limit)
    return _clean([
        {"task_id": r["task_id"], "title": r["title"], "status": r["status"],
         "value": tasks.value(r), "next_action": r["next_action"], "project": r["project"]}
        for r in rows
    ])


def blockers() -> dict:
    return _clean({
        "approvals": [approval_card(a) for a in approvals.pending()],
        "blocked_tasks": [
            {"task_id": t["task_id"], "title": t["title"], "status": t["status"],
             "reason": t["last_error"] or t["blockers"] or "no reason recorded"}
            for t in tasks.blocked() if t["status"] != "NEEDS_APPROVAL"
        ],
    })


def money() -> dict:
    m = metrics.money()
    return _clean({
        "real_revenue_inr": m["real_revenue_inr"], "real_cost_inr": m["real_cost_inr"],
        "real_net_inr": m["real_net_inr"], "reserve_inr": m["reserve_inr"],
        "by_project": metrics.by_project(), "trend_7d": metrics.trend(7),
        "non_actual": m["non_actual"], "budget": metrics.budget_status(),
    })


def error_list(limit: int = 20) -> list[dict]:
    rows = errors.open_errors(limit)
    return _clean([
        {"error_id": r["error_id"], "component": r["component"], "kind": r["kind"],
         "message": r["message"], "created_at": r["created_at"]}
        for r in rows
    ])


def agent_list() -> list[dict]:
    from . import agents
    return _clean([
        {"agent_id": a["agent_id"], "model_class": a["model_class"], "status": a["status"],
         "reliability": a["reliability"], "runs": a["runs"], "failures": a["failures"],
         "current_task": a["current_task"]}
        for a in agents.all_agents()
    ])


def report_text() -> str:
    from . import reports
    return reports.full_report()


def run_command(message: str, sender: str = "phone") -> dict:
    """The phone posts a command through the SAME router as WhatsApp."""
    reply = router.handle(message, sender=sender)
    return {"reply": reply}


def capture(text: str, kind: str = "idea") -> dict:
    return intake.capture(text, kind, source="phone")


def feedback(task_id: str, choice: str, note: str = "") -> dict:
    return intake.feedback(task_id, choice, note, source="phone")
