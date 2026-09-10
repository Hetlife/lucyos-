"""Structured data assembly for the interface.

Every existing surface (WhatsApp, `aion report`, the phone UI's current
endpoints) reads through `reports.py`, which renders *text*. That is correct
for a control channel that must work when nothing else does, but it means the
interface can never show a projects list, a cost breakdown, or cards — the
data never arrives as data.

This module changes nothing about how state is computed or stored. It only
assembles the same underlying functions (`metrics`, `tasks`, `approvals`,
`health`, `milestones`, `resume`) into plain, JSON-serialisable dicts, so a
new interface layer can be built without touching canonical state or the
existing text surfaces.

No stage is ever summed with another. Real money is ACTUAL only; everything
else is simulated, always kept in its own branch of the response.
"""
from __future__ import annotations

from . import approvals, db, health, metrics, milestones, resume, tasks, util

MISSION_TARGET_INR = 100000.0


def _row(r) -> dict:
    """sqlite3.Row -> plain dict, so json.dumps never chokes on it."""
    return dict(r) if r is not None else {}


def system_snapshot() -> dict:
    """The whole first read: is it healthy, what's the bottleneck, what's next."""
    h = health.run_all(deep=False)
    r = resume.load()
    return {
        "as_of": util.now(),
        "healthy": h["healthy"],
        "checks": [{"name": c["name"], "ok": c["ok"], "detail": c.get("detail", "")}
                   for c in h["checks"]],
        "bottleneck": r.get("bottleneck", "not identified"),
        "next_action": r.get("next_action", ""),
        "task_counts": tasks.counts(),
        "governor": metrics.budget_status()["governor"],
        "paused": db.get_meta("paused", "0") == "1",
        "safe_mode": db.get_meta("safe_mode", "0") == "1",
        "pending_approvals": len(approvals.pending()),
    }


def money_split() -> dict:
    """Real (ACTUAL) and simulated (everything else) money, never combined."""
    conn = db.connect()
    rows = conn.execute(
        "SELECT kind, stage, COALESCE(SUM(amount_inr),0) s FROM finance "
        "GROUP BY kind, stage").fetchall()
    by_stage: dict = {}
    for row in rows:
        by_stage.setdefault(row["stage"], {})[row["kind"]] = round(row["s"], 2)

    actual = by_stage.get("ACTUAL", {})
    real_revenue = actual.get("revenue", 0.0)
    real_cost = actual.get("cost", 0.0) + metrics.spend("month")
    real = {
        "revenue_inr": round(real_revenue, 2),
        "cost_inr": round(real_cost, 2),
        "net_inr": round(real_revenue - real_cost, 2),
    }

    sim_revenue = sum(v.get("revenue", 0.0) for k, v in by_stage.items() if k != "ACTUAL")
    sim_cost = sum(v.get("cost", 0.0) for k, v in by_stage.items() if k != "ACTUAL")
    simulated = {
        "revenue_inr": round(sim_revenue, 2),
        "cost_inr": round(sim_cost, 2),
        "net_inr": round(sim_revenue - sim_cost, 2),
        "by_stage": {k: v for k, v in by_stage.items() if k != "ACTUAL"},
    }

    return {
        "real": real,
        "simulated": simulated,
        "mission_target_inr": MISSION_TARGET_INR,
        "mission_pct": round(100 * real["net_inr"] / MISSION_TARGET_INR, 2)
                       if MISSION_TARGET_INR else 0.0,
        "milestones": milestones.check(),
    }


def projects() -> list[dict]:
    """One entry per distinct project, real and simulated money kept apart."""
    conn = db.connect()
    names = set()
    for table in ("tasks", "finance", "deliveries"):
        for row in conn.execute(f"SELECT DISTINCT project FROM {table}").fetchall():
            if row["project"]:
                names.add(row["project"])

    out = []
    for name in sorted(names):
        task_counts = {r["status"]: r["c"] for r in conn.execute(
            "SELECT status, COUNT(*) c FROM tasks WHERE project=? GROUP BY status",
            (name,)).fetchall()}
        open_tasks = sum(c for s, c in task_counts.items() if s not in ("DONE", "CANCELLED"))

        real_rows = conn.execute(
            "SELECT kind, COALESCE(SUM(amount_inr),0) s FROM finance "
            "WHERE project=? AND stage='ACTUAL' GROUP BY kind", (name,)).fetchall()
        real_by_kind = {r["kind"]: r["s"] for r in real_rows}
        real_net = round(real_by_kind.get("revenue", 0.0) - real_by_kind.get("cost", 0.0), 2)

        sim_rows = conn.execute(
            "SELECT kind, COALESCE(SUM(amount_inr),0) s FROM finance "
            "WHERE project=? AND stage!='ACTUAL' GROUP BY kind", (name,)).fetchall()
        sim_by_kind = {r["kind"]: r["s"] for r in sim_rows}
        sim_net = round(sim_by_kind.get("revenue", 0.0) - sim_by_kind.get("cost", 0.0), 2)

        last_activity = conn.execute(
            "SELECT MAX(updated_at) t FROM tasks WHERE project=?", (name,)).fetchone()["t"]

        out.append({
            "project": name,
            "task_counts": task_counts,
            "open_tasks": open_tasks,
            "real_net_inr": real_net,
            "simulated_net_inr": sim_net,
            "last_activity_at": last_activity,
        })
    return out


def costs() -> dict:
    """Model spend, broken down, with the governor's own numbers alongside."""
    conn = db.connect()
    today, month = util.today(), util.month()
    today_inr = conn.execute(
        "SELECT COALESCE(SUM(cost_inr),0) s FROM model_usage WHERE day=?",
        (today,)).fetchone()["s"]
    month_inr = conn.execute(
        "SELECT COALESCE(SUM(cost_inr),0) s FROM model_usage WHERE month=?",
        (month,)).fetchone()["s"]

    by_model = [dict(r) for r in conn.execute(
        "SELECT model, model_class, COUNT(*) calls, COALESCE(SUM(cost_inr),0) cost_inr "
        "FROM model_usage WHERE month=? GROUP BY model, model_class "
        "ORDER BY cost_inr DESC", (month,)).fetchall()]
    by_class = [dict(r) for r in conn.execute(
        "SELECT model_class, COUNT(*) calls, COALESCE(SUM(cost_inr),0) cost_inr "
        "FROM model_usage WHERE month=? GROUP BY model_class "
        "ORDER BY cost_inr DESC", (month,)).fetchall()]

    b = metrics.budget_status()
    return {
        "today_inr": round(today_inr, 2),
        "month_inr": round(month_inr, 2),
        "by_model": by_model,
        "by_class": by_class,
        "governor": b["governor"],
        "strong_model_pct": b["strong_model_pct"],
        "strong_model_spend_inr": b["strong_model_spend_inr"],
        "strong_model_cap_inr": b["strong_model_cap_inr"],
    }
