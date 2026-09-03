"""Model-usage accounting, budget governor and real-vs-modelled money."""
from __future__ import annotations

from . import config, db, util

STAGES = ("ACTUAL", "FORECAST", "SIMULATION", "PAPER", "BACKTEST")


def record_usage(model: str, model_class: str, *, input_tokens: int = 0, output_tokens: int = 0,
                 cost_inr: float = 0.0, task_id: str | None = None, success: bool = True,
                 retries: int = 0, escalated: bool = False, note: str = "") -> None:
    conn = db.connect()
    conn.execute(
        "INSERT INTO model_usage(at, day, month, model, model_class, task_id, input_tokens, "
        "output_tokens, cost_inr, success, retries, escalated, note) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (util.now(), util.today(), util.month(), model, model_class, task_id, input_tokens,
         output_tokens, cost_inr, 1 if success else 0, retries, 1 if escalated else 0, note))
    conn.commit()
    if model_class == "C" and cost_inr:
        # Attribute strong-model spend to the phase that authorised it.
        phase = db.get_meta("fable_phase", "1")
        key = f"fable_phase_{phase}_spend"
        db.set_meta(key, str(round(float(db.get_meta(key, "0")) + cost_inr, 2)))


def spend(period: str = "day") -> float:
    col, val = ("day", util.today()) if period == "day" else ("month", util.month())
    row = db.connect().execute(
        f"SELECT COALESCE(SUM(cost_inr),0) s FROM model_usage WHERE {col}=?", (val,)).fetchone()
    return round(row["s"], 2)


def budget_status() -> dict:
    day, month = spend("day"), spend("month")
    day_cap = float(db.get_meta("daily_cost_cap_inr", config.DEFAULT_DAILY_COST_CAP_INR))
    month_cap = float(db.get_meta("monthly_cost_cap_inr", config.DEFAULT_MONTHLY_COST_CAP_INR))
    build_cap = float(db.get_meta("build_budget_cap_inr", "2000"))
    build_used = float(db.connect().execute(
        "SELECT COALESCE(SUM(cost_inr),0) s FROM model_usage WHERE model_class='C'").fetchone()["s"])
    pct = round(100 * build_used / build_cap, 1) if build_cap else 0.0
    return {
        "day_spend_inr": day, "day_cap_inr": day_cap, "day_over": day > day_cap,
        "month_spend_inr": month, "month_cap_inr": month_cap, "month_over": month > month_cap,
        "strong_model_spend_inr": round(build_used, 2), "strong_model_cap_inr": build_cap,
        "strong_model_pct": pct,
        "governor": _governor(pct),
    }


def _governor(pct: float) -> str:
    """Budget governor thresholds from the bootstrap directive."""
    if pct >= 100:
        return "STOP — no further strong-model use without new owner authorization"
    if pct >= 95:
        return "HANDOFF — stop discretionary strong-model use, prepare handoff"
    if pct >= 85:
        return "CRITICAL-ONLY — integration, debugging and review only"
    if pct >= 70:
        return "RESERVE — strong model only for unresolved high-value problems"
    if pct >= 50:
        return "SHIFT-DOWN — push execution to local and cheap models"
    if pct >= 25:
        return "ARCHITECTURE-DONE — persistent state should already exist"
    return "NORMAL"


def record_money(kind: str, amount_inr: float, *, stage: str = "ACTUAL", project: str = "default",
                 description: str = "", evidence: str = "") -> None:
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; use one of {STAGES}")
    if stage == "ACTUAL" and not evidence:
        raise ValueError("ACTUAL money requires evidence (transaction id, statement line, invoice)")
    conn = db.connect()
    conn.execute(
        "INSERT INTO finance(at, day, kind, stage, amount_inr, project, description, evidence) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (util.now(), util.today(), kind, stage, amount_inr, project, description, evidence))
    conn.commit()


def by_project() -> list[dict]:
    """Am I making money, how much, and from where — per business."""
    rows = db.connect().execute(
        "SELECT project, kind, stage, COALESCE(SUM(amount_inr),0) s FROM finance "
        "GROUP BY project, kind, stage").fetchall()
    agg: dict = {}
    for r in rows:
        entry = agg.setdefault(r["project"], {"project": r["project"], "revenue": 0.0,
                                              "cost": 0.0, "net": 0.0, "forecast": 0.0})
        if r["stage"] == "ACTUAL":
            if r["kind"] in ("revenue", "cost"):
                entry[r["kind"]] += r["s"]
        elif r["kind"] == "revenue":
            entry["forecast"] += r["s"]
    for entry in agg.values():
        entry["net"] = round(entry["revenue"] - entry["cost"], 2)
        entry["revenue"] = round(entry["revenue"], 2)
        entry["cost"] = round(entry["cost"], 2)
        entry["forecast"] = round(entry["forecast"], 2)
    return sorted(agg.values(), key=lambda e: -e["net"])


def trend(days: int = 7) -> dict:
    """Net over the last N days against the N before it."""
    from datetime import date, timedelta
    today_d = date.today()
    start = (today_d - timedelta(days=days)).isoformat()
    prior = (today_d - timedelta(days=days * 2)).isoformat()
    conn = db.connect()

    def net(a: str, b: str) -> float:
        r = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN kind='revenue' THEN amount_inr "
            "WHEN kind='cost' THEN -amount_inr ELSE 0 END),0) n FROM finance "
            "WHERE stage='ACTUAL' AND day >= ? AND day < ?", (a, b)).fetchone()
        return round(r["n"], 2)

    current = net(start, (today_d + timedelta(days=1)).isoformat())
    previous = net(prior, start)
    return {"days": days, "current": current, "previous": previous,
            "change": round(current - previous, 2)}


def money() -> dict:
    conn = db.connect()
    rows = conn.execute(
        "SELECT kind, stage, COALESCE(SUM(amount_inr),0) s FROM finance GROUP BY kind, stage"
    ).fetchall()
    agg: dict = {}
    for r in rows:
        agg.setdefault(r["stage"], {})[r["kind"]] = round(r["s"], 2)
    actual = agg.get("ACTUAL", {})
    revenue = actual.get("revenue", 0.0)
    cost = actual.get("cost", 0.0) + spend("month")
    return {
        "real_revenue_inr": round(revenue, 2),
        "real_cost_inr": round(cost, 2),
        "real_net_inr": round(revenue - cost, 2),
        "reserve_inr": round(actual.get("reserve", 0.0), 2),
        "model_spend_month_inr": spend("month"),
        "non_actual": {k: v for k, v in agg.items() if k != "ACTUAL"},
    }
