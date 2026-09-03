"""Milestone detection.

A milestone is reached when it is *measured*, never when it is projected or
claimed.  Each check below reads real rows.  The continuous build loop stops on
a major milestone so the owner gets a decision point rather than a machine that
keeps building past the thing it was trying to prove.
"""
from __future__ import annotations

from . import db, memory, metrics, util

MAJOR = {"M0", "M2", "M4", "M6"}   # loop stops on these


def _actual_revenue_rows() -> list:
    return db.connect().execute(
        "SELECT * FROM finance WHERE kind='revenue' AND stage='ACTUAL' AND evidence!=''"
    ).fetchall()


def _monthly_net() -> dict:
    rows = db.connect().execute(
        "SELECT SUBSTR(day,1,7) m, kind, SUM(amount_inr) s FROM finance "
        "WHERE stage='ACTUAL' GROUP BY m, kind").fetchall()
    months: dict = {}
    for r in rows:
        months.setdefault(r["m"], {})[r["kind"]] = r["s"]
    return {m: round(v.get("revenue", 0) - v.get("cost", 0), 2) for m, v in months.items()}


def _consecutive_months_at(target: float) -> int:
    months = _monthly_net()
    best = run = 0
    for month in sorted(months):
        run = run + 1 if months[month] >= target else 0
        best = max(best, run)
    return best


def check() -> dict:
    """Return every milestone with its measured status.  Reads only real rows."""
    revenue = _actual_revenue_rows()
    payers = {}
    for r in revenue:
        payers[r["description"]] = payers.get(r["description"], 0) + 1
    deliveries = len(revenue)
    net_by_month = _monthly_net()

    results = {
        "M0": (bool(revenue),
               f"{len(revenue)} evidenced revenue row(s)"),
        "M1": (any(c >= 2 for c in payers.values()),
               f"largest payer count: {max(payers.values()) if payers else 0}"),
        "M2": (deliveries >= 10 and sum(net_by_month.values()) > 0,
               f"{deliveries} evidenced deliveries, net INR {round(sum(net_by_month.values()), 2)}"),
        "M3": (db.get_meta("hands_off_days", "0").isdigit()
               and int(db.get_meta("hands_off_days", "0")) >= 30,
               f"{db.get_meta('hands_off_days', '0')} hands-off days recorded"),
        "M4": (_consecutive_months_at(25000) >= 3,
               f"{_consecutive_months_at(25000)} consecutive month(s) at INR 25,000 net"),
        "M5": (_projects_at_m2() >= 2,
               f"{_projects_at_m2()} project(s) with positive proven economics"),
        "M6": (_consecutive_months_at(100000) >= 3,
               f"{_consecutive_months_at(100000)} consecutive month(s) at INR 1,00,000 net"),
    }
    return {code: {"reached": reached, "evidence": evidence}
            for code, (reached, evidence) in results.items()}


def _projects_at_m2() -> int:
    rows = db.connect().execute(
        "SELECT project, SUM(CASE WHEN kind='revenue' THEN amount_inr ELSE -amount_inr END) net, "
        "COUNT(*) n FROM finance WHERE stage='ACTUAL' GROUP BY project").fetchall()
    return sum(1 for r in rows if r["net"] > 0 and r["n"] >= 10)


def newly_reached() -> list[str]:
    """Milestones reached since the last check.  Records each one once."""
    state = check()
    fresh = []
    for code, info in state.items():
        if not info["reached"]:
            continue
        if db.get_meta(f"milestone_{code}"):
            continue
        db.set_meta(f"milestone_{code}", util.now())
        memory.remember("fact", f"milestone {code} reached",
                        f"Reached {util.now()}. Measured by: {info['evidence']}.",
                        confidence="VERIFIED_FACT", source="milestone check")
        db.log_event("aion", "milestone.reached", code, info["evidence"])
        fresh.append(code)
    return fresh


def reached() -> list[str]:
    return [c for c in check() if db.get_meta(f"milestone_{c}")]


def report() -> str:
    state = check()
    m = metrics.money()
    lines = [f"MILESTONES — mission INR 1,00,000/month net (now at INR {m['real_net_inr']})", ""]
    for code, info in state.items():
        mark = "reached" if info["reached"] else "not reached"
        lines.append(f"{code}: {mark} — {info['evidence']}")
    return "\n".join(lines)
