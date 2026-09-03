"""Global task queue with explicit ownership, states and value ranking."""
from __future__ import annotations

import sqlite3

from . import config, db, security, util

STATES = [
    "INBOX", "TRIAGE", "READY", "CLAIMED", "RUNNING", "WAITING",
    "NEEDS_REVIEW", "NEEDS_APPROVAL", "BLOCKED", "FAILED", "DONE", "CANCELLED",
]
OPEN_STATES = [s for s in STATES if s not in ("DONE", "CANCELLED")]
ACTIVE_STATES = ("CLAIMED", "RUNNING")
# Completion requires evidence; these states must never be reported as DONE.
INCOMPLETE = ("WAITING", "BLOCKED", "NEEDS_APPROVAL", "NEEDS_REVIEW", "FAILED")

FIELDS = (
    "project parent_task title description status priority impact probability unlocks "
    "info_gain cost risk time_est human_dependence owner_agent model_class dependencies "
    "blockers approval_id success_criteria validation_method output_location next_action "
    "evidence last_error kind exec_command validation_command plan_id"
).split()


class TaskError(Exception):
    pass


def create(title: str, **kw) -> str:
    """Create a task.  Only title is required; everything else has a default."""
    task_id = kw.pop("task_id", None) or util.new_id("TASK")
    bad = set(kw) - set(FIELDS)
    if bad:
        raise TaskError(f"unknown task fields: {sorted(bad)}")
    status = kw.get("status", "READY")
    if status not in STATES:
        raise TaskError(f"invalid status {status!r}")
    row = {f: kw.get(f) for f in FIELDS if f in kw}
    row["title"] = security.redact(title)
    row["status"] = status
    if "description" in row:
        row["description"] = security.redact(row["description"])
    cols = ["task_id", "created_at", "updated_at"] + list(row)
    vals = [task_id, util.now(), util.now()] + [row[k] for k in row]
    conn = db.connect()
    conn.execute(
        f"INSERT INTO tasks({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals
    )
    conn.commit()
    db.log_event("aion", "task.create", task_id, title)
    return task_id


def get(task_id: str) -> sqlite3.Row | None:
    return db.connect().execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()


def update(task_id: str, **kw) -> None:
    if not get(task_id):
        raise TaskError(f"no such task {task_id}")
    allowed = set(FIELDS) | {"retry_count", "claimed_at", "started_at", "completed_at", "owner_agent"}
    bad = set(kw) - allowed
    if bad:
        raise TaskError(f"unknown task fields: {sorted(bad)}")
    if "status" in kw and kw["status"] not in STATES:
        raise TaskError(f"invalid status {kw['status']!r}")
    kw = {k: (security.redact(v) if isinstance(v, str) else v) for k, v in kw.items()}
    kw["updated_at"] = util.now()
    sets = ", ".join(f"{k}=?" for k in kw)
    conn = db.connect()
    conn.execute(f"UPDATE tasks SET {sets} WHERE task_id=?", list(kw.values()) + [task_id])
    conn.commit()
    db.log_event("aion", "task.update", task_id, kw.get("status", ""))


def claim(task_id: str, agent_id: str) -> bool:
    """Atomically take ownership.  False if another agent already owns it."""
    conn = db.connect()
    cur = conn.execute(
        "UPDATE tasks SET status='CLAIMED', owner_agent=?, claimed_at=?, updated_at=? "
        "WHERE task_id=? AND status IN ('READY','TRIAGE','INBOX')",
        (agent_id, util.now(), util.now(), task_id),
    )
    conn.commit()
    if cur.rowcount:
        db.log_event(agent_id, "task.claim", task_id)
        return True
    return False


def release_stale(max_age_s: int = config.STALE_CLAIM_SECONDS) -> list[str]:
    """Return claimed/running tasks whose owner went silent, back to READY."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=max_age_s)).replace(microsecond=0).isoformat()
    conn = db.connect()
    rows = conn.execute(
        "SELECT task_id FROM tasks WHERE status IN ('CLAIMED','RUNNING') "
        "AND COALESCE(started_at, claimed_at, updated_at) < ?", (cutoff,)
    ).fetchall()
    ids = [r["task_id"] for r in rows]
    for tid in ids:
        conn.execute(
            "UPDATE tasks SET status='READY', owner_agent=NULL, claimed_at=NULL, updated_at=? "
            "WHERE task_id=?", (util.now(), tid))
        db.log_event("aion", "task.stale_release", tid)
    conn.commit()
    return ids


def complete(task_id: str, evidence: str, next_action: str = "") -> None:
    """DONE requires evidence.  Refuses an empty proof string.

    Completing a task is the SAVE step of the execution loop, so the resume
    point is refreshed here — otherwise a crash right after a completion would
    resume from work that is already finished.
    """
    if not evidence or not evidence.strip():
        raise TaskError("cannot mark DONE without evidence (test run, measurement or observation)")
    update(task_id, status="DONE", evidence=evidence, next_action=next_action,
           completed_at=util.now())
    from . import resume  # late import: resume depends on this module
    nxt = next_task()
    resume.checkpoint(
        last_verified_success=f"{task_id}: {evidence}"[:400],
        next_action=(f"work {nxt['task_id']}: {nxt['next_action'] or nxt['title']}"
                     if nxt else _nothing_runnable_note()),
    )


def fail(task_id: str, error: str) -> str:
    """Record a failure and decide retry vs escalate vs block."""
    row = get(task_id)
    if row is None:
        raise TaskError(f"no such task {task_id}")
    retries = row["retry_count"] + 1
    if retries >= config.MAX_TASK_RETRIES:
        status = "BLOCKED"
    else:
        status = "READY"
    update(task_id, status=status, retry_count=retries, last_error=error,
           owner_agent=None)
    return status


def _nothing_runnable_note() -> str:
    c = counts()
    if c.get("WAITING"):
        return f"{c['WAITING']} task(s) waiting on a missing executor — see `aion blockers`"
    if c.get("BLOCKED"):
        return f"{c['BLOCKED']} task(s) blocked — root-cause them before adding work"
    if c.get("NEEDS_APPROVAL"):
        return "everything left needs owner approval"
    if c.get("NEEDS_REVIEW"):
        return "remaining work is class C — open a strong-model session"
    return "queue empty — decompose the objective into executable tasks"


def value(row) -> float:
    """Expected-value ranking from the directive's action-value formula."""
    num = (row["impact"] * row["probability"] * max(row["info_gain"], 0.1)
           * max(row["unlocks"], 0.1))
    den = (max(row["time_est"], 0.1) * max(row["cost"], 0.1) * max(row["risk"], 0.1)
           * max(row["human_dependence"], 0.1))
    return round(num / den, 3)


def ready(limit: int = 10) -> list:
    rows = db.connect().execute(
        "SELECT * FROM tasks WHERE status IN ('READY','TRIAGE','INBOX') "
        "AND (blockers IS NULL OR blockers='')"
    ).fetchall()
    rows = [r for r in rows if _deps_met(r)]
    rows.sort(key=lambda r: (-value(r), r["priority"], r["created_at"]))
    return rows[:limit]


def _deps_met(row) -> bool:
    deps = [d.strip() for d in (row["dependencies"] or "").split(",") if d.strip()]
    for dep in deps:
        d = get(dep)
        if d is None or d["status"] != "DONE":
            return False
    return True


def next_task():
    rows = ready(1)
    return rows[0] if rows else None


def by_status(status: str) -> list:
    return db.connect().execute(
        "SELECT * FROM tasks WHERE status=? ORDER BY updated_at DESC", (status,)).fetchall()


def blocked() -> list:
    q = ",".join("?" * 3)
    return db.connect().execute(
        f"SELECT * FROM tasks WHERE status IN ({q}) ORDER BY updated_at DESC",
        ("BLOCKED", "NEEDS_APPROVAL", "WAITING")).fetchall()


def counts() -> dict:
    rows = db.connect().execute("SELECT status, COUNT(*) c FROM tasks GROUP BY status").fetchall()
    return {r["status"]: r["c"] for r in rows}
