"""Deterministic coordination rules for LucyOS prompt work orders.

Prompt files are not canonical execution state. They carry pointers into the
existing AION task/session model and may be mirrored to Drive for coordination.
No database, queue, scheduler, model call, or authority layer is created here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from . import sessions, tasks, util

STATUSES = ("PENDING", "PROCESSING", "COMPLETED", "BLOCKED", "CANCELLED", "ARCHIVED")
FINAL_STATUSES = {"COMPLETED", "CANCELLED"}
REQUIRED_FIELDS = (
    "prompt_id", "title", "created_at", "created_by", "project", "objective",
    "source_context", "required_inputs", "execution_instructions", "authority_limits",
    "success_criteria", "expected_output", "status", "linked_task_id", "linked_session_id",
    "starting_git_sha", "final_git_sha", "result_summary", "evidence", "archive_status",
)

class PromptOrderError(ValueError):
    pass

@dataclass(frozen=True)
class Selection:
    action: str
    prompt_id: str | None
    reason: str


def _ids(items: Iterable[Mapping]) -> list[str]:
    return [str(x.get("prompt_id", "")).strip() for x in items if str(x.get("prompt_id", "")).strip()]


def validate_work_order(order: Mapping) -> list[str]:
    errors: list[str] = []
    missing = [k for k in REQUIRED_FIELDS if k not in order]
    if missing:
        errors.append("missing:" + ",".join(missing))
    status = str(order.get("status", "")).upper()
    if status not in STATUSES:
        errors.append("invalid-status:" + status)
    prompt_id = str(order.get("prompt_id", ""))
    if not prompt_id.startswith("PRM-"):
        errors.append("invalid-prompt-id")
    if status in {"PROCESSING", "COMPLETED", "ARCHIVED"}:
        if not str(order.get("linked_task_id", "")).startswith("TASK-"):
            errors.append("missing-task-link")
        if not str(order.get("linked_session_id", "")).startswith("SES-"):
            errors.append("missing-session-link")
    if status == "ARCHIVED" and not order.get("archive_receipt"):
        errors.append("archive-receipt-required")
    return errors


def verify_links(order: Mapping) -> list[str]:
    """Verify task/session pointers against canonical AION SQLite through existing APIs."""
    errors: list[str] = []
    task_id = str(order.get("linked_task_id", "")).strip()
    session_id = str(order.get("linked_session_id", "")).strip()
    if task_id and tasks.get(task_id) is None:
        errors.append("unknown-task:" + task_id)
    if session_id and not sessions.summary(session_id):
        errors.append("unknown-session:" + session_id)
    return errors


def select_startup(processing: Iterable[Mapping], pending: Iterable[Mapping], requested_id: str | None = None) -> Selection:
    """Apply startup anti-duplication rules without executing anything."""
    proc = _ids(processing)
    if len(proc) > 1:
        raise PromptOrderError("multiple PROCESSING prompts require reconciliation")
    if len(proc) == 1:
        return Selection("RESUME", proc[0], "exactly one prompt is already processing")
    pend = _ids(pending)
    if requested_id:
        if requested_id not in pend:
            return Selection("NONE", None, "requested prompt is not pending")
        return Selection("START", requested_id, "explicitly requested pending prompt")
    return Selection("NONE", None, "no processing prompt and no explicit pending selection")


def transition(order: Mapping, new_status: str, *, task_id: str = "", session_id: str = "", receipt: Mapping | None = None) -> dict:
    """Return a transitioned copy; caller persists/moves the coordination artifact."""
    current = str(order.get("status", "")).upper()
    new_status = new_status.upper()
    allowed = {
        "PENDING": {"PROCESSING", "BLOCKED", "CANCELLED"},
        "PROCESSING": {"COMPLETED", "BLOCKED", "CANCELLED"},
        "BLOCKED": {"PROCESSING", "CANCELLED"},
        "COMPLETED": {"ARCHIVED"},
        "CANCELLED": {"ARCHIVED"},
        "ARCHIVED": set(),
    }
    if current not in allowed or new_status not in allowed[current]:
        raise PromptOrderError(f"invalid transition {current}->{new_status}")
    out = dict(order)
    out["status"] = new_status
    if task_id:
        out["linked_task_id"] = task_id
    if session_id:
        out["linked_session_id"] = session_id
    if new_status == "PROCESSING":
        if not out.get("linked_task_id") or not out.get("linked_session_id"):
            raise PromptOrderError("PROCESSING requires existing task and session links")
        link_errors = verify_links(out)
        if link_errors:
            raise PromptOrderError("; ".join(link_errors))
    if new_status == "COMPLETED":
        if not str(out.get("result_summary", "")).strip() or not out.get("evidence"):
            raise PromptOrderError("COMPLETED requires result_summary and evidence")
    if new_status == "ARCHIVED":
        if current not in FINAL_STATUSES:
            raise PromptOrderError("only completed/cancelled prompts may archive")
        if not receipt:
            raise PromptOrderError("archive receipt required")
        out["archive_receipt"] = dict(receipt)
        out["archive_status"] = "ARCHIVED"
    return out


def build_receipt(order: Mapping, *, tests: list[str], outputs: list[str], unresolved_blockers: list[str], resume_pointer: str) -> dict:
    return {
        "final_status": str(order.get("status", "")),
        "task_id": str(order.get("linked_task_id", "")),
        "session_id": str(order.get("linked_session_id", "")),
        "starting_git_sha": str(order.get("starting_git_sha", "")),
        "final_git_sha": str(order.get("final_git_sha", "")),
        "tests": list(tests),
        "outputs": list(outputs),
        "unresolved_blockers": list(unresolved_blockers),
        "resume_pointer": resume_pointer,
        "archived_at": util.now(),
    }
