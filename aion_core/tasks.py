"""Global task queue with explicit ownership, states and value ranking."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from contextlib import nullcontext
from pathlib import Path

from . import config, db, security, util

STATES = [
    "INBOX", "TRIAGE", "READY", "CLAIMED", "RUNNING", "WAITING",
    "NEEDS_REVIEW", "NEEDS_APPROVAL", "BLOCKED", "FAILED", "DONE", "CANCELLED",
]
OPEN_STATES = [s for s in STATES if s not in ("DONE", "CANCELLED")]
ACTIVE_STATES = ("CLAIMED", "RUNNING")
# Completion requires evidence; these states must never be reported as DONE.
INCOMPLETE = ("WAITING", "BLOCKED", "NEEDS_APPROVAL", "NEEDS_REVIEW", "FAILED")
EXECUTOR_WAIT_BLOCKERS = {
    "A": "no A-class executor on this machine",
    "B": "no B-class executor on this machine",
}

FIELDS = (
    "project parent_task title description status priority impact probability unlocks "
    "info_gain cost risk time_est human_dependence owner_agent model_class data_class dependencies "
    "blockers approval_id success_criteria validation_method output_location next_action "
    "evidence last_error kind exec_command validation_command plan_id"
).split()


DATA_CLASSES = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"}


class TaskError(Exception):
    pass


# Keep the public vocabulary. RUNNING -> NEEDS_REVIEW represents verification;
# NEEDS_REVIEW -> DONE represents closure. Direct RUNNING is retained for CLI users.
_HOLDS = {"WAITING", "BLOCKED", "FAILED", "NEEDS_REVIEW", "NEEDS_APPROVAL", "CANCELLED"}
TRANSITIONS = {
    "INBOX": _HOLDS | {"TRIAGE", "READY", "CLAIMED"},
    "TRIAGE": _HOLDS | {"READY", "CLAIMED"},
    "READY": _HOLDS | {"CLAIMED", "RUNNING"},
    "CLAIMED": _HOLDS | {"RUNNING", "READY"},
    "RUNNING": _HOLDS | {"READY", "DONE"},
    "WAITING": _HOLDS | {"READY"},
    "BLOCKED": _HOLDS | {"READY"},
    "FAILED": _HOLDS | {"READY"},
    "NEEDS_REVIEW": _HOLDS | {"READY", "RUNNING", "DONE"},
    "NEEDS_APPROVAL": {"READY", "CANCELLED"},
    "DONE": set(), "CANCELLED": set(),
}

# Ordered: authority holds outrank transient symptoms in the same message.
FAILURE_RULES = (
    ("OWNER_APPROVAL_REQUIRED", ("owner approval", "owner authority", "permission denied", "approval required")),
    ("ARCHITECTURE_GATE_FAILURE", ("architecture", "authority-gate", "protected path", "anti-dup")),
    ("MODEL_QUOTA_EXHAUSTED", ("quota", "rate limit", "429", "budget ceiling", "usage limit")),
    ("CONTEXT_OVERFLOW", ("context window", "context length", "context limit", "context exhausted", "context overflow")),
    ("PROVIDER_SCHEMA_ERROR", ("schema error", "invalid schema", "schema validation", "invalid response format")),
    ("WORKER_PROCESS_DIED", ("worker process died", "worker exited", "process killed", "sigkill", "segmentation fault")),
    ("APP_SERVER_CLOSED", ("app-server", "app server", "connection reset", "connection refused")),
    ("HEARTBEAT_LOST", ("heartbeat lost", "missing heartbeat", "stale owner")),
    ("NO_ROUTE", ("no route", "no executor", "missing executor", "no available provider")),
    ("PROVIDER_TIMEOUT", ("timed out", "timeout", "executor window ended")),
    ("TEST_FAILURE", ("validation failed", "test failed", "tests failed", "assertionerror")),
)
RECOVERY = {
    "OWNER_APPROVAL_REQUIRED": ("NEEDS_APPROVAL", "obtain owner approval", False),
    "ARCHITECTURE_GATE_FAILURE": ("NEEDS_REVIEW", "obtain architecture review", False),
    "MODEL_QUOTA_EXHAUSTED": ("WAITING", "wait for quota reset; explicitly resume", False),
    "CONTEXT_OVERFLOW": ("NEEDS_REVIEW", "save evidence and rebuild bounded task context", False),
    "PROVIDER_SCHEMA_ERROR": ("NEEDS_REVIEW", "correct provider schema before explicitly resuming", False),
    "WORKER_PROCESS_DIED": ("READY", "reconcile partial work and inspect worker exit before bounded retry", True),
    "APP_SERVER_CLOSED": ("READY", "check app-server availability before bounded retry", True),
    "HEARTBEAT_LOST": ("READY", "release stale ownership and reconcile evidence before bounded retry", True),
    "NO_ROUTE": ("WAITING", "restore an eligible executor route; explicitly resume", False),
    "PROVIDER_TIMEOUT": ("READY", "reconcile partial work before bounded retry", True),
    "TEST_FAILURE": ("READY", "inspect failing validation before bounded retry", True),
    "UNKNOWN": ("READY", "inspect failure before bounded retry", True),
}


def classify_failure(error: str) -> str:
    message = error.lower()
    return next((kind for kind, markers in FAILURE_RULES
                 if kind.lower() in message or any(marker in message for marker in markers)), "UNKNOWN")


def recovery_for(kind: str, retry_count: int) -> dict:
    if kind not in RECOVERY:
        raise TaskError(f"unknown failure classification {kind!r}")
    status, action, retry = RECOVERY[kind]
    if retry and retry_count >= config.MAX_TASK_RETRIES:
        status, action = "BLOCKED", "retry limit reached; reconcile evidence and diagnose"
    return {"kind": kind, "status": status, "next_action": action, "retry": retry}


def _approval_clear(row) -> bool:
    if not row["approval_id"]:
        return True
    approval = db.connect().execute("SELECT status FROM approvals WHERE approval_id=?",
                                    (row["approval_id"],)).fetchone()
    return bool(approval and approval["status"] == "APPROVED")


def validate_transition(row, status: str, evidence: str = "") -> None:
    before = row["status"]
    if status not in STATES:
        raise TaskError(f"invalid status {status!r}")
    if status != before and status not in TRANSITIONS[before]:
        raise TaskError(f"invalid task transition {before}->{status}")
    if status in {"READY", "CLAIMED", "RUNNING", "DONE"} and not _approval_clear(row):
        raise TaskError("task requires its recorded owner approval")
    if status == "DONE" and classify_failure(row["blockers"] or "") in ("OWNER_APPROVAL_REQUIRED", "ARCHITECTURE_GATE_FAILURE"):
        raise TaskError("resolve the owner or architecture hold before completion")
    if status == "DONE" and (not evidence.strip() or not _deps_met(row)):
        raise TaskError("cannot mark DONE without evidence and completed dependencies")


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
    if status == "DONE" and not str(row.get("evidence") or "").strip():
        raise TaskError("cannot create DONE without evidence")
    data_class = str(row.get("data_class") or "INTERNAL").upper()
    if data_class not in DATA_CLASSES:
        raise TaskError(f"invalid data_class {data_class!r}")
    row["data_class"] = data_class
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
    _update(task_id, kw)


def _update(task_id: str, kw: dict, *, reconcile: bool = False, expected=None, _conn=None) -> None:
    allowed = set(FIELDS) | {"retry_count", "claimed_at", "started_at", "completed_at", "owner_agent"}
    bad = set(kw) - allowed
    if bad:
        raise TaskError(f"unknown task fields: {sorted(bad)}")
    kw = {k: (security.redact(v) if isinstance(v, str) else v) for k, v in kw.items()}
    conn = _conn or db.connect()
    with (nullcontext() if _conn is not None else conn):
        if _conn is None:
            conn.execute("BEGIN IMMEDIATE")
        row = get(task_id)
        if row is None:
            raise TaskError(f"no such task {task_id}")
        if expected is not None and dict(row) != dict(expected):
            raise TaskError("task changed during reconciliation; retry against current state")
        # A terminal record is immutable; exact duplicate writes are harmless.
        if row["status"] in ("DONE", "CANCELLED"):
            if all(row[k] == v for k, v in kw.items()):
                return
            # Legacy DONE preparation can acquire a new, recorded approval action.
            approval = conn.execute(
                "SELECT task_id, status FROM approvals WHERE approval_id=?",
                (kw.get("approval_id"),)).fetchone()
            if not (row["status"] == "DONE" and set(kw) == {"status", "approval_id"}
                    and kw["status"] == "NEEDS_APPROVAL" and approval
                    and approval["task_id"] == task_id and approval["status"] == "PENDING"
                    and kw["approval_id"] != row["approval_id"]):
                raise TaskError("terminal task is immutable")
            row = dict(row, status="NEEDS_REVIEW")
            kw.update(completed_at=None, owner_agent=None, claimed_at=None, started_at=None)
        if (row["approval_id"] and not _approval_clear(row)
                and "approval_id" in kw and kw["approval_id"] != row["approval_id"]):
            raise TaskError("cannot detach an unresolved owner approval")
        if (kw.get("status") == "READY" and row["approval_id"] and _approval_clear(row)
                and row["blockers"] == "OWNER_APPROVAL_REQUIRED: " + RECOVERY["OWNER_APPROVAL_REQUIRED"][1]):
            kw.setdefault("blockers", "")
        transition_row = row
        if reconcile and row["status"] not in ("RUNNING", "NEEDS_REVIEW"):
            if row["status"] in ("CANCELLED", "NEEDS_APPROVAL") or not _approval_clear(row):
                raise TaskError("cannot reconcile a cancelled task or an owner hold")
            validate_transition(row, "NEEDS_REVIEW")
            transition_row = dict(row, status="NEEDS_REVIEW")
            conn.execute("INSERT INTO events(at,day,actor,kind,subject,detail) VALUES(?,?,?,?,?,?)",
                         (util.now(), util.today(), "aion", "task.reconcile", task_id,
                          row["status"] + "->NEEDS_REVIEW->DONE"))
        effective = dict(row)
        effective.update(kw)
        # Existing approvals cannot be detached in the same write as a transition.
        if "status" in kw:
            validate_transition(transition_row, kw["status"], effective["evidence"] or "")
            if kw["status"] == "DONE":
                if not str(kw.get("evidence") or "").strip():
                    raise TaskError("DONE requires explicit completion evidence")
                validate_transition(effective, "DONE", effective["evidence"] or "")
                kw.setdefault("completed_at", util.now())
        # Legacy workers park timeouts with the missing-executor marker. Keep the
        # hold, but do not let executor discovery immediately requeue that timeout.
        if (kw.get("status") == "WAITING"
                and kw.get("blockers") in EXECUTOR_WAIT_BLOCKERS.values()
                and classify_failure(kw.get("last_error", "")) == "PROVIDER_TIMEOUT"):
            kw["blockers"] = "timeout: reconcile partial work before resuming"
            kw["next_action"] = RECOVERY["PROVIDER_TIMEOUT"][1]
        kw["updated_at"] = util.now()
        sets = ", ".join(f"{k}=?" for k in kw)
        conn.execute(f"UPDATE tasks SET {sets} WHERE task_id=?", list(kw.values()) + [task_id])
        if kw.get("evidence") and kw["evidence"] != row["evidence"] and kw.get("status") == "DONE":
            _evidence_event(conn, task_id, "completion", kw["evidence"])
    _lifecycle_event(conn if _conn is not None else None, "aion", "task.update", task_id, kw.get("status", ""))


def claim(task_id: str, agent_id: str) -> bool:
    """Atomically take ownership.  False if another agent already owns it."""
    conn = db.connect()
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        row = get(task_id)
        if (row is None or row["status"] not in ("READY", "TRIAGE", "INBOX")
                or row["blockers"] or not _approval_clear(row) or not _deps_met(row)):
            return False
        validate_transition(row, "CLAIMED")
        conn.execute(
            "UPDATE tasks SET status='CLAIMED', owner_agent=?, claimed_at=?, "
            "started_at=NULL, updated_at=? WHERE task_id=?",
            (agent_id, util.now(), util.now(), task_id))
        _lifecycle_event(conn, agent_id, "task.claim", task_id)
    return True


def release_stale(max_age_s: int = config.STALE_CLAIM_SECONDS) -> list[str]:
    """Requeue silent owners within the retry bound; preserve live heartbeats."""
    cutoff = util.ago(seconds=max_age_s)
    conn = db.connect()
    rows = conn.execute(
        "SELECT task_id FROM tasks WHERE status IN ('CLAIMED','RUNNING') "
        "AND updated_at < ?", (cutoff,)
    ).fetchall()
    ids = []
    for row in rows:
        # Recheck after acquiring the write lock: a heartbeat/closure may have won.
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            current = get(row["task_id"])
            if current["status"] not in ACTIVE_STATES or current["updated_at"] >= cutoff:
                continue
            retries = current["retry_count"] + 1
            status = recovery_for("HEARTBEAT_LOST", retries)["status"]
            if not _approval_clear(current):
                status = "NEEDS_APPROVAL"
            validate_transition(current, status)
            conn.execute(
                "UPDATE tasks SET status=?, owner_agent=NULL, claimed_at=NULL, "
                "started_at=NULL, retry_count=?, updated_at=?, last_error=? WHERE task_id=?",
                (status, retries, util.now(), "stale owner; reconcile before retry", row["task_id"]))
        ids.append(row["task_id"])
        db.log_event("aion", "task.stale_release", row["task_id"], status)
    return ids


def requeue_available_executor_waits(available_classes: set[str]) -> list[str]:
    """Requeue only WAITING tasks parked by AION for a missing A/B executor.

    Exact machine-authored blocker markers keep owner, budget, safe-mode and
    other genuine holds out of this transition.  An attached approval is an
    additional hard gate even if a legacy row happens to carry our marker.
    """
    conn = db.connect()
    requeued = []
    for model_class in sorted(available_classes & set(EXECUTOR_WAIT_BLOCKERS)):
        marker = EXECUTOR_WAIT_BLOCKERS[model_class]
        rows = conn.execute(
            "SELECT task_id FROM tasks WHERE status='WAITING' AND model_class=? "
            "AND blockers=? AND approval_id IS NULL",
            (model_class, marker),
        ).fetchall()
        for row in rows:
            cur = conn.execute(
                "UPDATE tasks SET status='READY', blockers='', last_error='', "
                "owner_agent=NULL, claimed_at=NULL, updated_at=? "
                "WHERE task_id=? AND status='WAITING' AND model_class=? "
                "AND blockers=? AND approval_id IS NULL",
                (util.now(), row["task_id"], model_class, marker),
            )
            if cur.rowcount:
                requeued.append(row["task_id"])
                db.log_event("aion", "task.executor_requeue", row["task_id"], model_class)
    conn.commit()
    return requeued


def complete(task_id: str, evidence: str, next_action: str = "") -> None:
    """Evidence-bearing completion; legacy queued work is atomically reconciled."""
    _complete(task_id, evidence, next_action)


def _complete(task_id: str, evidence: str, next_action: str = "", *, expected=None) -> None:
    """DONE requires evidence.  Refuses an empty proof string.

    Completing a task is the SAVE step of the execution loop, so the resume
    point is refreshed here — otherwise a crash right after a completion would
    resume from work that is already finished.
    """
    if not evidence or not evidence.strip():
        raise TaskError("cannot mark DONE without evidence (test run, measurement or observation)")
    row = get(task_id)
    if row is None:
        raise TaskError(f"no such task {task_id}")
    if row["status"] == "DONE":
        if row["evidence"] == security.redact(evidence):
            return
        raise TaskError("task already closed with different evidence")
    # The compatibility reconciliation and DONE write share one transaction.
    _update(task_id, dict(status="DONE", evidence=evidence, next_action=next_action,
                         blockers="", last_error="", completed_at=util.now()),
            reconcile=True, expected=expected)
    from . import resume  # late import: resume depends on this module
    nxt = next_task()
    resume.checkpoint(
        last_verified_success=f"{task_id}: {evidence}"[:400],
        next_action=(f"work {nxt['task_id']}: {nxt['next_action'] or nxt['title']}"
                     if nxt else _nothing_runnable_note()),
    )


def fail(task_id: str, error: str, *, _conn=None) -> str:
    """Apply deterministic recovery through the existing worker failure seam."""
    row = get(task_id)
    if row is None:
        raise TaskError(f"no such task {task_id}")
    kind = classify_failure(error)
    retries = min(config.MAX_TASK_RETRIES, row["retry_count"] + int(RECOVERY[kind][2]))
    recovery = recovery_for(kind, retries)
    _update(task_id, dict(status=recovery["status"], retry_count=retries, last_error=error,
           blockers=(f"{kind}: {recovery['next_action']}" if recovery["status"] != "READY" else ""),
           next_action=recovery["next_action"], owner_agent=None, claimed_at=None, started_at=None), expected=row, _conn=_conn)
    _lifecycle_event(_conn, "aion", "task.failure", task_id, json.dumps(recovery, sort_keys=True))
    return recovery["status"]


def _lifecycle_event(conn, actor: str, kind: str, task_id: str, detail: str = "") -> None:
    if conn is None:
        db.log_event(actor, kind, task_id, detail)
    else:
        conn.execute("INSERT INTO events(at,day,actor,kind,subject,detail) VALUES(?,?,?,?,?,?)",
                     (util.now(), util.today(), actor, kind, task_id, security.redact(detail)))


def claim_id(task_id: str) -> str:
    """Existing claim event is an attempt fence, including same-second retries."""
    row = db.connect().execute("SELECT MAX(id) FROM events WHERE kind='task.claim' AND subject=?",
                               (task_id,)).fetchone()
    return str(row[0]) if row[0] is not None else ""


def accept_worker_result(packet: dict, *, owner_agent: str, key: str, fingerprint: str,
                         scope: str) -> dict:
    """Atomically accept a worker claim and its receipt in the canonical store.

    Output is never closure authority. A failed return can replay the receipt;
    an interrupted transaction rolls back both lifecycle changes and receipt.
    """
    conn = db.connect()
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        saved = conn.execute("SELECT scope,result FROM idempotency WHERE key=?", (key,)).fetchone()
        if saved:
            if saved["scope"] != "scs-result-v2":
                raise TaskError("idempotency key conflict")
            record = json.loads(saved["result"])
            if record["fingerprint"] != fingerprint:
                raise TaskError("idempotency key conflict")
            return dict(record["response"], replayed=True)
        task_id = packet["task_id"]
        row = get(task_id)
        if (row is None or row["owner_agent"] != owner_agent or row["status"] not in ACTIVE_STATES
                or claim_id(task_id) != packet["claim_id"]):
            raise TaskError("packet is not from the current active claim")
        status = packet["STATUS"]
        if status not in {"HEARTBEAT", "PROGRESS", "DONE", "FAILED", "BLOCKED", "NEEDS_REVIEW"}:
            raise TaskError("invalid worker result status")
        if status == "DONE" and (not packet["TESTS"].strip() or not packet["RESULTS"].strip()):
            raise TaskError("completion claim requires validation evidence")
        if status == "HEARTBEAT":
            heartbeat(task_id, owner_agent, _conn=conn)
            result_status = row["status"]
        else:
            # Actions, filenames and untyped prose are claims, not measured progress.
            if packet["TESTS"]:
                record_evidence(task_id, "TESTS: " + packet["TESTS"] + "\nRESULTS: " + packet["RESULTS"],
                                kind="validation", owner_agent=owner_agent, _conn=conn)
            _lifecycle_event(conn, owner_agent, "task.worker_result", task_id,
                             json.dumps({k: v for k, v in packet.items() if k != "idempotency_key"}, sort_keys=True))
            if status == "FAILED":
                result_status = fail(task_id, packet["BLOCKERS"] + "\n" + packet["RESULTS"], _conn=conn)
            elif status == "PROGRESS":
                result_status = row["status"]
            else:
                result_status = "NEEDS_REVIEW" if status == "DONE" else status
                _update(task_id, dict(status=result_status, blockers=packet["BLOCKERS"],
                                     next_action=packet["NEXT_ACTION"]), expected=get(task_id), _conn=conn)
        response = {"task_id": task_id, "status": result_status, "replayed": False}
        conn.execute("INSERT INTO idempotency(key,at,scope,result) VALUES(?,?,?,?)",
                     (key, util.now(), scope,
                      json.dumps({"fingerprint": fingerprint, "response": response}, sort_keys=True)))
    return response


def _evidence_event(conn, task_id: str, kind: str, evidence: str) -> None:
    conn.execute("INSERT INTO events(at, day, actor, kind, subject, detail) VALUES(?,?,?,?,?,?)",
                 (util.now(), util.today(), "aion", "task.evidence", task_id,
                  json.dumps({"kind": kind, "evidence": security.redact(evidence)}, sort_keys=True)))


def heartbeat(task_id: str, owner_agent: str, *, _conn=None) -> bool:
    """Contact only. Never manufactures progress evidence or changes ownership."""
    conn = _conn or db.connect()
    with (nullcontext() if _conn is not None else conn):
        cur = conn.execute("UPDATE tasks SET updated_at=? WHERE task_id=? AND owner_agent=? "
                           "AND status IN ('CLAIMED','RUNNING')",
                           (util.now(), task_id, owner_agent))
    return bool(cur.rowcount)


def record_evidence(task_id: str, evidence: str, *, kind: str, owner_agent: str, _conn=None) -> None:
    """Record a measured artifact/validation/git observation, never a heartbeat."""
    if kind not in {"artifact", "validation", "git"} or not evidence.strip():
        raise TaskError("meaningful evidence requires artifact, validation or git proof")
    conn = _conn or db.connect()
    with (nullcontext() if _conn is not None else conn):
        if _conn is None:
            conn.execute("BEGIN IMMEDIATE")
        row = get(task_id)
        if row is None or row["status"] not in ACTIVE_STATES or row["owner_agent"] != owner_agent:
            raise TaskError("evidence must come from the current task owner")
        if row["evidence"] == security.redact(evidence):
            return  # repeating the same observation is not new progress
        conn.execute("UPDATE tasks SET evidence=?, updated_at=? WHERE task_id=?",
                     (security.redact(evidence), util.now(), task_id))
        _evidence_event(conn, task_id, kind, evidence)


def progress(task_id: str, max_age_s: int = config.STALE_CLAIM_SECONDS) -> dict:
    """Read-only stall detection using existing task timestamps and evidence events.

    Legacy evidence has no reliable timestamp; do not infer progress from it.
    Evidence from a previous attempt cannot extend the current attempt's window.
    """
    row = get(task_id)
    if row is None:
        raise TaskError(f"no such task {task_id}")
    event = db.connect().execute("SELECT MAX(at) FROM events WHERE subject=? AND kind='task.evidence'",
                                 (task_id,)).fetchone()[0]
    start = row["started_at"] or row["claimed_at"] or row["created_at"]
    meaningful_at = max(start, event) if event else start
    return {"last_contact_at": row["updated_at"], "last_evidence_at": event,
            "stalled": row["status"] in ACTIVE_STATES and meaningful_at < util.ago(seconds=max_age_s)}


def close_implemented(task_id: str, commit: str, *, repo: Path | None = None) -> bool:
    """Reconcile a git-backed implementation without executing its work again.

    Require the exact clean HEAD, a Task-ID trailer, configured independent
    validation and repository gates. Results live in tasks.evidence as JSON.
    Return False for the same recorded closure, and refuse conflicting closures.
    This is an explicit operation, never an automatic packet completion hook.
    """
    from . import worker
    row = get(task_id)
    if row is None:
        raise TaskError(f"no such task {task_id}")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise TaskError("closure requires a full git commit SHA")
    if row["status"] == "DONE":
        try:
            saved = json.loads(row["evidence"])
        except (ValueError, TypeError):
            saved = {}
        if (isinstance(saved, dict) and saved.get("type") == "git-closure-v1"
                and saved.get("task_id") == task_id and saved.get("commit") == commit):
            return False
        raise TaskError("task already closed with different evidence")
    if (row["status"] in ("CANCELLED", "NEEDS_APPROVAL") or not _approval_clear(row)
            or row["kind"] == "architecture" or row["model_class"] == "D"
            or classify_failure(row["blockers"] or "") in ("OWNER_APPROVAL_REQUIRED", "ARCHITECTURE_GATE_FAILURE")):
        raise TaskError("closure cannot bypass an owner or architecture hold")
    if not row["validation_command"] or not row["success_criteria"] or not _deps_met(row):
        raise TaskError("closure requires success criteria, independent validation and completed dependencies")
    if row["status"] in ACTIVE_STATES:
        raise TaskError("release the active owner before reconciling implemented work")
    root = Path(repo or worker.repo_root()).resolve()

    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                text=True, timeout=30, check=False)
        if result.returncode:
            raise TaskError("cannot verify git closure: " + security.redact(result.stderr[:300]))
        return result.stdout.strip()

    if git("rev-parse", "HEAD") != commit or git("status", "--porcelain"):
        raise TaskError("closure requires the exact clean committed tree")
    if f"Task-ID: {task_id}" not in git("show", "-s", "--format=%B", commit).splitlines():
        raise TaskError("commit does not identify this task")
    parent = git("rev-parse", commit + "^")
    # Do not accept a gate rewritten by the implementation being verified.
    if git("diff", "--name-only", parent, commit, "--", "scripts/verify_authority.py",
           ".lucy/authority/HIGH_MODEL_BASELINE.json"):
        raise TaskError("closure requires unchanged authority verifier and baseline")
    commands = {
        "validation": row["validation_command"],
        "scan": "./aion scan .",
        "portability": "python3 scripts/check_portability.py",
        "authority": f"python3 scripts/verify_authority.py strict --base {parent}",
        "anti_dup": f"python3 scripts/verify_authority.py anti-dup --base {parent}",
    }
    checks = {}
    for name, command in commands.items():
        result = worker.run_command(command, cwd=root)
        if not result["ok"] or result.get("code") != 0:
            raise TaskError(f"closure {name} failed: {result.get('output', '')[:300]}")
        checks[name] = {"command": command, "exit_code": 0, "output": result["output"]}
    if git("rev-parse", "HEAD") != commit or git("status", "--porcelain"):
        raise TaskError("tree changed during closure validation")
    if dict(get(task_id)) != dict(row):
        raise TaskError("task changed during closure validation; reconcile again")
    evidence = json.dumps({"type": "git-closure-v1", "task_id": task_id, "commit": commit,
                           "success_criteria": row["success_criteria"], "checks": checks}, sort_keys=True)
    _complete(task_id, evidence, expected=row)
    return True


def _nothing_runnable_note() -> str:
    c = counts()
    if c.get("WAITING"):
        return f"{c['WAITING']} task(s) waiting on an executor or recovery condition — see `aion blockers`"
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


def ready(limit: int | None = 10) -> list:
    rows = db.connect().execute(
        "SELECT * FROM tasks WHERE status IN ('READY','TRIAGE','INBOX') "
        "AND (blockers IS NULL OR blockers='')"
    ).fetchall()
    rows = [r for r in rows if _deps_met(r) and _approval_clear(r)]
    rows.sort(key=lambda r: (-value(r), r["priority"], r["created_at"]))
    return rows if limit is None else rows[:limit]


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
