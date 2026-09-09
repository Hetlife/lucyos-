"""Evidence-backed deliveries and their attributable unit economics."""
from __future__ import annotations

from . import db, util

STATUSES = ("PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED")
COST_CATEGORIES = ("delivery", "model", "payment", "refund", "acquisition", "direct")


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
