"""Tier-3 owner approval queue.

A pending approval holds exactly one action.  Every other task keeps running:
`create()` marks only the linked task NEEDS_APPROVAL and never touches the
rest of the queue.
"""
from __future__ import annotations

from . import db, security, tasks, util

PENDING, APPROVED, DENIED, EXPIRED = "PENDING", "APPROVED", "DENIED", "EXPIRED"

FIELDS = ("project action why owner_action cost max_downside expected_benefit "
          "reversibility prepared resumes recommendation task_id").split()


class ApprovalError(Exception):
    pass


def next_id() -> str:
    row = db.connect().execute(
        "SELECT approval_id FROM approvals WHERE approval_id LIKE 'A-%' "
        "ORDER BY CAST(SUBSTR(approval_id,3) AS INTEGER) DESC LIMIT 1").fetchone()
    n = int(row["approval_id"][2:]) + 1 if row else 101
    return f"A-{n}"


def create(action: str, **kw) -> str:
    bad = set(kw) - set(FIELDS)
    if bad:
        raise ApprovalError(f"unknown approval fields: {sorted(bad)}")
    approval_id = next_id()
    row = {f: security.redact(str(kw[f])) for f in FIELDS if f in kw and kw[f] is not None}
    row["action"] = security.redact(action)
    cols = ["approval_id", "created_at"] + list(row)
    vals = [approval_id, util.now()] + [row[k] for k in row]
    conn = db.connect()
    conn.execute(f"INSERT INTO approvals({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals)
    conn.commit()
    task_id = kw.get("task_id")
    if task_id and tasks.get(task_id):
        # Hold only this action.  Independent work continues.
        tasks.update(task_id, status="NEEDS_APPROVAL", approval_id=approval_id)
    db.log_event("aion", "approval.create", approval_id, action)
    return approval_id


def get(approval_id: str):
    return db.connect().execute(
        "SELECT * FROM approvals WHERE approval_id=?", (approval_id.upper(),)).fetchone()


def pending() -> list:
    return db.connect().execute(
        "SELECT * FROM approvals WHERE status=? ORDER BY created_at", (PENDING,)).fetchall()


def decide(approval_id: str, decision: str, by: str = "owner") -> dict:
    """Apply an owner decision.  Idempotent: a repeat reply is not re-applied."""
    approval_id = approval_id.upper()
    row = get(approval_id)
    if row is None:
        raise ApprovalError(f"unknown approval {approval_id}")
    decision = decision.upper()
    if decision not in (APPROVED, DENIED):
        raise ApprovalError(f"invalid decision {decision}")
    if row["status"] != PENDING:
        return {"approval_id": approval_id, "status": row["status"], "changed": False,
                "task_id": row["task_id"]}
    conn = db.connect()
    conn.execute("UPDATE approvals SET status=?, decided_at=?, decided_by=? WHERE approval_id=?",
                 (decision, util.now(), by, approval_id))
    conn.commit()
    task_id = row["task_id"]
    if task_id and tasks.get(task_id):
        if decision == APPROVED:
            # Resume exactly where preparation stopped; nothing is rebuilt.
            tasks.update(task_id, status="READY", next_action=row["resumes"] or "execute approved action")
        else:
            tasks.update(task_id, status="CANCELLED", last_error=f"{approval_id} denied by {by}")
    db.log_event(by, f"approval.{decision.lower()}", approval_id)
    return {"approval_id": approval_id, "status": decision, "changed": True, "task_id": task_id}


def render(row) -> str:
    """The exact WhatsApp approval card format from the owner directive."""
    return "\n".join([
        f"APPROVAL {row['approval_id']}",
        "",
        f"ACTION: {row['action']}",
        f"WHY REQUIRED: {row['why'] or 'not recorded'}",
        f"COST: {row['cost']}",
        f"MAXIMUM DOWNSIDE: {row['max_downside'] or 'not recorded'}",
        f"EXPECTED BENEFIT: {row['expected_benefit'] or 'not recorded'}",
        f"REVERSIBILITY: {row['reversibility']}",
        f"ALREADY PREPARED: {row['prepared'] or 'nothing yet'}",
        f"RESUMES: {row['resumes'] or 'not recorded'}",
        f"RECOMMENDATION: {row['recommendation']}",
        "",
        f"REPLY: APPROVE {row['approval_id']}  or  DENY {row['approval_id']}",
    ])
