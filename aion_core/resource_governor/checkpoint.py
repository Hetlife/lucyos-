"""Task-level checkpoint, defer and resume (directive sections 14-17).

This deliberately does not invent a new task state.  LucyOS already has a
`WAITING` status and an established convention for it — `tasks.py`'s
`EXECUTOR_WAIT_BLOCKERS` marks *why* a task is waiting in the `blockers`
column with an exact string, and `tasks.requeue_available_executor_waits`
matches on that marker to know it is safe to bring back automatically.  This
module follows the same convention with its own marker prefix instead of
adding a parallel status enum, so every existing piece of code that already
understands "a WAITING task with a specific blocker marker is machine-managed"
keeps working unchanged.

Checkpoint files are the schema from directive section 14, written under
`state/resource_governor/checkpoints/<task_id>.json`.  Writes are atomic
(temp file + rename, via `util.atomic_write`) and additionally keep the prior
valid checkpoint at `<task_id>.json.bak` — a checkpoint write that produces
bad JSON (should never happen, since the object is built here, but a
corrupted or hand-edited file on disk is a real possibility) never destroys
the last good one; `load()` falls back to it and reports which one it used.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .. import config, db, errors, security, tasks, util

CHECKPOINT_VERSION = 1
MARKER_PREFIX = "resource governor:"

FIELDS = ["TASK_ID", "PROJECT", "GOAL", "STATUS", "MODEL", "START_TIME", "LAST_UPDATE",
          "CURRENT_STAGE", "COMPLETED_STEPS", "PENDING_STEPS", "FILES_READ", "FILES_CHANGED",
          "IMPORTANT_FINDINGS", "DECISIONS", "TEST_RESULTS", "ERRORS", "NEXT_ACTION",
          "REQUIRED_MODEL_CLASS", "ESTIMATED_REMAINING_WORK", "PROVIDER_STATE", "RESET_TARGET",
          "CHECKPOINT_VERSION"]


def _dir() -> Path:
    d = config.home() / "state" / "resource_governor" / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(task_id: str) -> Path:
    return _dir() / f"{task_id}.json"


def _clean(value):
    if isinstance(value, str):
        return security.redact(value)
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def save(task_id: str, **fields) -> dict:
    """Merge `fields` onto the task's existing checkpoint (if any) and persist it."""
    existing = load(task_id) or {}
    doc = {k: existing.get(k) for k in FIELDS}
    doc["TASK_ID"] = task_id
    doc.setdefault("START_TIME", util.now())
    for key, value in fields.items():
        if key not in FIELDS:
            raise ValueError(f"unknown checkpoint field {key!r}")
        doc[key] = _clean(value)
    doc["LAST_UPDATE"] = util.now()
    doc["CHECKPOINT_VERSION"] = CHECKPOINT_VERSION

    path = _path(task_id)
    bak = path.with_suffix(".json.bak")
    if path.exists() and _valid_json(path):
        bak.write_bytes(path.read_bytes())
    util.write_json(path, doc)
    db.log_event("resource_governor", "checkpoint.save", task_id, doc.get("CURRENT_STAGE") or "")
    return doc


def _valid_json(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except (OSError, json.JSONDecodeError):
        return False


def load(task_id: str) -> dict | None:
    path = _path(task_id)
    if path.exists():
        if _valid_json(path):
            return json.loads(path.read_text(encoding="utf-8"))
        errors.record("resource_governor", f"checkpoint for {task_id} is corrupt",
                      "falling back to last known-good backup if one exists", task_id=task_id)
    bak = path.with_suffix(".json.bak")
    if bak.exists() and _valid_json(bak):
        return json.loads(bak.read_text(encoding="utf-8"))
    return None


def repo_signature() -> dict:
    """Best-effort git HEAD + dirty-file count.  None everywhere on failure."""
    repo = Path(__file__).resolve().parent.parent.parent
    try:
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=8)
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return {"head": None, "dirty": None}
    if head.returncode != 0:
        return {"head": None, "dirty": None}
    dirty = len([l for l in status.stdout.splitlines() if l.strip()]) if status.returncode == 0 else None
    return {"head": head.stdout.strip(), "dirty": dirty}


def mark_waiting_for_resource(task_id: str, *, resource: str, expected_reset: str | None = None,
                              min_model_class: str | None = None, reasoning: str = "",
                              estimated_remaining_work: str = "") -> dict:
    """Section 16: checkpoint, then WAITING, then back in the queue."""
    row = tasks.get(task_id)
    if row is None:
        raise ValueError(f"no such task {task_id}")
    doc = save(
        task_id, PROJECT=row["project"], GOAL=row["title"], STATUS="WAITING_FOR_RESOURCE",
        REQUIRED_MODEL_CLASS=min_model_class or row["model_class"],
        NEXT_ACTION=row["next_action"] or row["title"],
        PROVIDER_STATE=f"{resource}: {reasoning}"[:900], RESET_TARGET=expected_reset or "unknown",
        ESTIMATED_REMAINING_WORK=estimated_remaining_work or "not estimated",
    )
    doc["_repo_signature"] = repo_signature()
    util.write_json(_path(task_id), doc)
    marker = f"{MARKER_PREFIX} {resource} constrained" + (
        f", resume after ~{expected_reset}" if expected_reset else "")
    tasks.update(task_id, status="WAITING", blockers=marker[:400], owner_agent=None)
    db.log_event("resource_governor", "task.defer", task_id, marker)
    return doc


def waiting_tasks() -> list:
    return db.connect().execute(
        "SELECT * FROM tasks WHERE status='WAITING' AND blockers LIKE ? ORDER BY updated_at",
        (f"{MARKER_PREFIX}%",)).fetchall()


def resume_eligible(*, force: bool = False) -> list[dict]:
    """Section 17: validate checkpoint, repo state and admission before resuming."""
    from . import admission  # late import: avoids a checkpoint <-> admission cycle
    results = []
    for row in waiting_tasks():
        task_id = row["task_id"]
        doc = load(task_id)
        if doc is None:
            results.append({"task_id": task_id, "eligible": False,
                            "reason": "no valid checkpoint found — needs owner review"})
            continue
        repo_changed = False
        now = None
        if not force:
            before = doc.get("_repo_signature") or {}
            now = repo_signature()
            if before.get("head") and now.get("head") and before["head"] != now["head"]:
                repo_changed = True
        if repo_changed:
            results.append({"task_id": task_id, "eligible": False,
                            "reason": f"repository HEAD changed since checkpoint "
                                      f"({before['head'][:8]} -> {now['head'][:8]}) — "
                                      "needs owner review"})
            continue
        decision = admission.evaluate(row)
        eligible = decision["decision"] in ("RUN_NOW", "RUN_LOCAL", "RUN_CHEAPER_MODEL",
                                            "RUN_REDUCED_SCOPE")
        results.append({"task_id": task_id, "eligible": eligible, "reason": decision["decision"],
                        "decision": decision})
    return results


def resume_task(task_id: str, *, force: bool = False) -> dict:
    matches = [r for r in resume_eligible(force=force) if r["task_id"] == task_id]
    if not matches:
        raise ValueError(f"{task_id} is not a resource-governor WAITING task")
    result = matches[0]
    if result["eligible"]:
        tasks.update(task_id, status="READY", blockers="", last_error="")
        db.log_event("resource_governor", "task.resume", task_id, result["reason"])
    return result


def resume_all(*, force: bool = False) -> dict:
    results = resume_eligible(force=force)
    resumed = []
    for r in results:
        if r["eligible"]:
            tasks.update(r["task_id"], status="READY", blockers="", last_error="")
            db.log_event("resource_governor", "task.resume", r["task_id"], r["reason"])
            resumed.append(r["task_id"])
    return {"checked": len(results), "resumed": resumed,
            "still_waiting": [r["task_id"] for r in results if not r["eligible"]]}
