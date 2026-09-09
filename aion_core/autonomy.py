"""Evidence-derived hands-off operation days."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from . import db, util


def evaluate_day(day: str) -> dict:
    """Close one past UTC day from task and event provenance."""
    try:
        parsed = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("day must be YYYY-MM-DD") from exc
    if parsed >= date.today():
        raise ValueError("only completed UTC days may be evaluated")
    conn = db.connect()
    autonomous = conn.execute(
        "SELECT COUNT(*) n FROM tasks WHERE DATE(completed_at)=? "
        "AND owner_agent IS NOT NULL AND owner_agent!='owner' AND status='DONE'", (day,)
    ).fetchone()["n"]
    approvals = conn.execute(
        "SELECT COUNT(*) n FROM events WHERE day=? AND actor='owner' "
        "AND kind IN ('approval.approve','approval.deny')", (day,)
    ).fetchone()["n"]
    operations = conn.execute(
        "SELECT COUNT(*) n FROM events WHERE day=? AND actor='owner' "
        "AND kind NOT IN ('approval.approve','approval.deny')", (day,)
    ).fetchone()["n"]
    qualifies = int(autonomous > 0 and operations == 0)
    evidence = (f"{autonomous} autonomously owned task completion(s); "
                f"{operations} owner operation(s); {approvals} owner approval decision(s)")
    conn.execute(
        "INSERT INTO hands_off_days(day,autonomous_completions,owner_operations," 
        "owner_approvals,qualifies,evidence,evaluated_at) VALUES(?,?,?,?,?,?,?) "
        "ON CONFLICT(day) DO UPDATE SET autonomous_completions=excluded.autonomous_completions," 
        "owner_operations=excluded.owner_operations,owner_approvals=excluded.owner_approvals," 
        "qualifies=excluded.qualifies,evidence=excluded.evidence,evaluated_at=excluded.evaluated_at",
        (day, autonomous, operations, approvals, qualifies, evidence, util.now()))
    conn.commit()
    return {"day": day, "qualifies": bool(qualifies), "evidence": evidence}


def evaluate_yesterday() -> dict:
    return evaluate_day((date.today() - timedelta(days=1)).isoformat())


def consecutive_days() -> int:
    rows = db.connect().execute(
        "SELECT day FROM hands_off_days WHERE qualifies=1 ORDER BY day").fetchall()
    best = run = 0
    previous = None
    for row in rows:
        current = datetime.strptime(row["day"], "%Y-%m-%d").date()
        run = run + 1 if previous and current == previous + timedelta(days=1) else 1
        best = max(best, run)
        previous = current
    return best
