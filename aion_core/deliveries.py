"""Evidence-backed deliveries and their attributable unit economics."""
from __future__ import annotations

import re
from datetime import date

from . import db, util

STATUSES = ("PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED")
COST_CATEGORIES = ("delivery", "model", "payment", "refund", "acquisition", "direct")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def record(*, project: str = "default", payer_id: str | None = None,
           customer_id: str | None = None, status: str = "COMPLETED",
           reference: str = "", evidence: str = "",
           delivery_id: str | None = None) -> str:
    """Create a delivery. Completed deliveries require independent evidence."""
    status = status.upper()
    if status not in STATUSES:
        raise ValueError(f"unknown delivery status {status!r}; use one of {STATUSES}")
    if not project:
        raise ValueError("delivery project is required")
    if status == "COMPLETED" and not (evidence or reference):
        raise ValueError("COMPLETED delivery requires evidence/reference")
    delivery_id = delivery_id or util.new_id("DEL")
    now = util.now()
    conn = db.connect()
    conn.execute(
        "INSERT INTO deliveries(delivery_id, project, payer_id, customer_id, status, "
        "reference, evidence, created_at, updated_at, completed_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (delivery_id, project, payer_id, customer_id, status, reference, evidence,
         now, now, now if status == "COMPLETED" else None))
    conn.commit()
    return delivery_id


def get(delivery_id: str):
    return db.connect().execute(
        "SELECT * FROM deliveries WHERE delivery_id=?", (delivery_id,)).fetchone()


def attribute_finance(finance_id: int, delivery_id: str) -> None:
    """Link an existing row without guessing or rewriting payer identity."""
    conn = db.connect()
    delivery = get(delivery_id)
    row = conn.execute("SELECT * FROM finance WHERE id=?", (finance_id,)).fetchone()
    if not delivery:
        raise ValueError(f"unknown delivery {delivery_id}")
    if not row:
        raise ValueError(f"unknown finance row {finance_id}")
    if row["project"] != delivery["project"]:
        raise ValueError("finance row and delivery must belong to the same project")
    if row["payer_id"] and delivery["payer_id"] and row["payer_id"] != delivery["payer_id"]:
        raise ValueError("finance row and delivery have conflicting payer identities")
    conn.execute("UPDATE finance SET delivery_id=? WHERE id=?", (delivery_id, finance_id))
    conn.commit()


def economics(project: str | None = None) -> dict:
    """Contribution for evidenced completed deliveries, using linked ACTUAL money only."""
    params: list[object] = []
    project_sql = ""
    if project is not None:
        project_sql = " AND d.project=?"
        params.append(project)
    completed = db.connect().execute(
        "SELECT COUNT(*) n FROM deliveries d "
        "WHERE d.status='COMPLETED' AND (d.evidence!='' OR d.reference!='')" + project_sql,
        params).fetchone()["n"]
    rows = db.connect().execute(
        "SELECT f.kind, COALESCE(SUM(f.amount_inr), 0) amount "
        "FROM finance f JOIN deliveries d ON d.delivery_id=f.delivery_id "
        "WHERE d.status='COMPLETED' AND (d.evidence!='' OR d.reference!='') "
        "AND f.stage='ACTUAL'" + project_sql +
        " GROUP BY f.kind", params).fetchall()
    totals = {r["kind"]: float(r["amount"]) for r in rows}
    revenue = totals.get("revenue", 0.0)
    costs = totals.get("cost", 0.0)
    return {
        "completed_deliveries": completed,
        "revenue_inr": round(revenue, 2),
        "cost_inr": round(costs, 2),
        "contribution_inr": round(revenue - costs, 2),
    }


def close_month(project: str, month: str, *, costs_complete: bool, evidence: str) -> None:
    """Attest a finished project's calendar month; never infer cost completeness."""
    if not project or not MONTH_RE.fullmatch(month):
        raise ValueError("project and calendar month YYYY-MM are required")
    if month >= date.today().strftime("%Y-%m"):
        raise ValueError("only completed calendar months may be closed")
    if not costs_complete:
        raise ValueError("a close requires explicit confirmation that attributable costs are complete")
    if not evidence:
        raise ValueError("a close requires independent evidence/reference")
    conn = db.connect()
    conn.execute(
        "INSERT INTO monthly_closes(project, month, costs_complete, evidence, closed_at) "
        "VALUES(?,?,?,?,?) ON CONFLICT(project, month) DO UPDATE SET "
        "costs_complete=excluded.costs_complete, evidence=excluded.evidence, "
        "closed_at=excluded.closed_at",
        (project, month, 1, evidence, util.now()))
    conn.commit()


def closed_portfolio_months() -> list[dict]:
    """Return only fully attributable, explicitly closed portfolio months."""
    conn = db.connect()
    activity = conn.execute(
        "SELECT SUBSTR(f.day,1,7) month, f.project, f.kind, SUM(f.amount_inr) amount "
        "FROM finance f JOIN deliveries d ON d.delivery_id=f.delivery_id "
        "WHERE f.stage='ACTUAL' AND d.status='COMPLETED' "
        "AND (d.evidence!='' OR d.reference!='') GROUP BY month,f.project,f.kind"
    ).fetchall()
    unlinked = {(r["month"], r["project"]) for r in conn.execute(
        "SELECT DISTINCT SUBSTR(day,1,7) month, project FROM finance "
        "WHERE stage='ACTUAL' AND delivery_id IS NULL")}
    closes = {(r["month"], r["project"]): r for r in conn.execute(
        "SELECT * FROM monthly_closes WHERE costs_complete=1")}
    by_month: dict[str, dict[str, dict[str, float]]] = {}
    for row in activity:
        project = by_month.setdefault(row["month"], {}).setdefault(
            row["project"], {"revenue": 0.0, "cost": 0.0})
        project[row["kind"]] = float(row["amount"])
    result = []
    for month, projects in sorted(by_month.items()):
        if any((month, project) not in closes or (month, project) in unlinked
               for project in projects):
            continue
        revenue = sum(v["revenue"] for v in projects.values())
        cost = sum(v["cost"] for v in projects.values())
        largest = max((v["revenue"] for v in projects.values()), default=0.0)
        result.append({
            "month": month, "revenue_inr": round(revenue, 2),
            "cost_inr": round(cost, 2), "contribution_inr": round(revenue - cost, 2),
            "projects": len(projects),
            "largest_revenue_share_pct": round(100 * largest / revenue, 2) if revenue > 0 else None,
        })
    return result
