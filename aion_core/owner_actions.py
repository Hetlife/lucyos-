"""Owner-facing manual actions and daily Het Task digest."""
from __future__ import annotations

import json
from pathlib import Path

from . import approvals, db, security, taskcheck, util

OWNER_NAME = "Het"
DEFAULT_EXPIRES_HOURS = 24


def request(*, title: str, instructions: str, public_base_url: str,
            expires_hours: int = DEFAULT_EXPIRES_HOURS,
            priority: int = 2, action_type: str = "manual",
            evidence_hint: str = "") -> dict:
    """Create one explicit human task for the owner using TaskCheck."""
    taskcheck.load_builtin_templates()
    meta = {
        "owner_action": True,
        "action_type": action_type,
        "evidence_hint": security.redact(evidence_hint),
    }
    out = taskcheck.create_task(
        template_id="het_manual_action",
        title=title,
        description=instructions,
        requester="LucyOS",
        assignee=OWNER_NAME,
        priority=priority,
        metadata=meta,
        expires_hours=expires_hours,
        public_base_url=public_base_url,
    )
    taskcheck._emit("owner_action.created", out["taskcheck_id"], action_type=action_type)
    return out


def active() -> list[dict]:
    """Return active owner actions, oldest deadline first."""
    taskcheck.expire_due()
    rows = db.connect().execute(
        "SELECT taskcheck_id,title,description,status,expires_at,created_at,metadata_json "
        "FROM taskcheck_runs WHERE assignee=? AND revoked_at IS NULL "
        "AND status IN ('ASSIGNED','OPENED','STARTED') ORDER BY expires_at,created_at",
        (OWNER_NAME,),
    ).fetchall()
    out=[]
    for row in rows:
        meta=json.loads(row["metadata_json"] or "{}")
        if meta.get("owner_action"):
            out.append({**dict(row),"metadata":meta})
    return out


def daily_digest() -> str:
    """Compact owner digest: manual actions first, approvals second."""
    actions=active(); pending=approvals.pending()
    lines=[f"HET TASKS · {util.today()}"]
    if not actions and not pending:
        return "HET TASKS\nNothing needs you right now. LucyOS can continue independently."
    if actions:
        lines += ["", "Manual actions:"]
        for i,item in enumerate(actions,1):
            lines.append(f"{i}. {item['title']} · due {item['expires_at']} · {item['taskcheck_id']}")
    if pending:
        lines += ["", "Approvals:"]
        for item in pending:
            lines.append(f"- {item['approval_id']} · {item['action']}")
    lines += ["", "Reply `blockers` for details or open the TaskCheck link from its alert."]
    return security.redact("\n".join(lines))


def should_alert_task(row) -> bool:
    """Hard gate: only explicit owner-action TaskChecks create manual alerts."""
    if not row or row["kind"] != "taskcheck":
        return False
    return bool(row["human_dependence"] >= 1.0 and row["status"] in ("WAITING","NEEDS_APPROVAL"))


def _runtime_public_url() -> str:
    path = taskcheck.config.home()/"TASKCHECK"/"runtime"/"public_url"
    try:
        return path.read_text(encoding="utf-8").strip().rstrip("/")
    except OSError:
        return ""


def reissue_link(taskcheck_id: str) -> str:
    row=db.connect().execute(
        "SELECT metadata_json,status FROM taskcheck_runs WHERE taskcheck_id=?",
        (taskcheck_id,),
    ).fetchone()
    if not row: raise ValueError("unknown Het Task")
    meta=json.loads(row["metadata_json"] or "{}")
    if not meta.get("owner_action"): raise ValueError("that TaskCheck is not a Het Task")
    base=_runtime_public_url()
    if not base: raise ValueError("TaskCheck public host is not currently online")
    token=taskcheck.rotate_token(taskcheck_id)
    return f"{base}/t/{token}"
