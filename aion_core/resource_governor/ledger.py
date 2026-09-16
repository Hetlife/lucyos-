"""Local cost/token ledger (directive section 24).

Reuses the existing `model_usage` table rather than creating a parallel one —
it already has model, model_class, task_id, tokens and cost per completed
unit of work. The one addition is `usage_kind` (a migration column, default
`API_USAGE`) so free local compute and non-metered subscription usage never
get counted as if they had a per-token price.
"""
from __future__ import annotations

from .. import db, util

USAGE_KINDS = ("API_USAGE", "SUBSCRIPTION_USAGE", "LOCAL_COMPUTE")

_GROUP_COLUMNS = {
    "model": "model_usage.model",
    "model_class": "model_usage.model_class",
    "usage_kind": "model_usage.usage_kind",
    "project": "tasks.project",
    "day": "model_usage.day",
}


def record_local_compute(model: str, *, input_tokens: int = 0, output_tokens: int = 0,
                         task_id: str | None = None, note: str = "") -> None:
    """Free local-model usage.  Always cost_inr=0 — never given a fabricated price."""
    conn = db.connect()
    conn.execute(
        "INSERT INTO model_usage(at, day, month, model, model_class, task_id, input_tokens, "
        "output_tokens, cost_inr, success, retries, escalated, note, usage_kind) "
        "VALUES(?,?,?,?,?,?,?,?,0,1,0,0,?,?)",
        (util.now(), util.today(), util.month(), model, "A", task_id, input_tokens,
         output_tokens, note, "LOCAL_COMPUTE"))
    conn.commit()


def by_group(group_by: str, *, period: str | None = None) -> list[dict]:
    if group_by not in _GROUP_COLUMNS:
        raise ValueError(f"unknown group_by {group_by!r}; use one of {list(_GROUP_COLUMNS)}")
    col = _GROUP_COLUMNS[group_by]
    join = "JOIN tasks USING(task_id)" if group_by == "project" else ""
    where, params = "", []
    if period == "day":
        where, params = "WHERE model_usage.day=?", [util.today()]
    elif period == "week":
        where, params = "WHERE model_usage.day >= date(?, '-6 days')", [util.today()]
    elif period is not None:
        raise ValueError("period must be 'day', 'week' or None")
    sql = (f"SELECT {col} AS key, COUNT(*) n, "
           f"COALESCE(SUM(input_tokens),0) input_tokens, "
           f"COALESCE(SUM(output_tokens),0) output_tokens, "
           f"COALESCE(SUM(cost_inr),0) cost_inr "
           f"FROM model_usage {join} {where} GROUP BY {col} ORDER BY cost_inr DESC")
    return [dict(r) for r in db.connect().execute(sql, params).fetchall()]


def frontier_calls_avoided() -> int:
    """Admission decisions that kept work off a class-C (frontier) model."""
    row = db.connect().execute(
        "SELECT COUNT(*) n FROM events WHERE kind='resource_governor.admission' "
        "AND detail IN ('RUN_LOCAL','RUN_CHEAPER_MODEL')").fetchone()
    return row["n"] if row else 0


def deferred_count() -> int:
    row = db.connect().execute(
        "SELECT COUNT(*) n FROM events WHERE kind='resource_governor.admission' "
        "AND detail LIKE 'DEFER_UNTIL_RESET%'").fetchone()
    return row["n"] if row else 0
