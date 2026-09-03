"""Failure capture, classification and the lesson loop."""
from __future__ import annotations

import re

from . import config, db, security, util

CLASSES = {
    "network": re.compile(r"(?i)timeout|connection|dns|unreachable|refused|proxy|tls|ssl"),
    "auth": re.compile(r"(?i)unauthorized|forbidden|401|403|invalid[_ ]token|expired token"),
    "rate_limit": re.compile(r"(?i)rate limit|429|too many requests|quota"),
    "not_found": re.compile(r"(?i)404|no such file|not found|missing"),
    "config": re.compile(r"(?i)env|config|setting|not configured|unset"),
    "data": re.compile(r"(?i)json|parse|schema|decode|malformed|invalid input"),
    "permission": re.compile(r"(?i)permission denied|read-only|eacces"),
    "resource": re.compile(r"(?i)no space|out of memory|disk full|oom"),
}


def classify(message: str) -> str:
    for kind, pattern in CLASSES.items():
        if pattern.search(message or ""):
            return kind
    return "unknown"


def record(component: str, message: str, detail: str = "", task_id: str | None = None) -> str:
    error_id = util.new_id("ERR")
    conn = db.connect()
    conn.execute(
        "INSERT INTO errors(error_id, created_at, component, task_id, kind, message, detail) "
        "VALUES(?,?,?,?,?,?,?)",
        (error_id, util.now(), component, task_id, classify(message),
         security.redact(message)[:500], security.redact(detail)[:4000]))
    conn.commit()
    db.log_event(component, "error", error_id, message[:120])
    return error_id


def resolve(error_id: str, root_cause: str, fix: str, lesson: str = "") -> None:
    conn = db.connect()
    conn.execute(
        "UPDATE errors SET status='RESOLVED', resolved_at=?, root_cause=?, fix=?, lesson=? "
        "WHERE error_id=?",
        (util.now(), security.redact(root_cause), security.redact(fix),
         security.redact(lesson), error_id.upper()))
    conn.commit()
    if lesson:
        from . import memory
        memory.remember("lesson", f"lesson from {error_id}", lesson, confidence="SUPPORTED_FACT",
                        source=error_id)


def open_errors(limit: int = 20) -> list:
    return db.connect().execute(
        "SELECT * FROM errors WHERE status='OPEN' ORDER BY created_at DESC LIMIT ?",
        (limit,)).fetchall()


def repeated(component: str, window: int = config.MAX_CONSECUTIVE_ERRORS) -> bool:
    """Runaway detector: same component failing the same way repeatedly."""
    rows = db.connect().execute(
        "SELECT kind FROM errors WHERE component=? AND status='OPEN' "
        "ORDER BY created_at DESC LIMIT ?", (component, window)).fetchall()
    return len(rows) >= window and len({r["kind"] for r in rows}) == 1
