"""Per-session work logs.

Every working session — OpenClaw, a cloud model, a local model, the owner at the
terminal — opens a session, appends short structured entries, and closes with an
outcome and a resume point.  The point is that the *next* session can read one
compact file instead of reconstructing history from chat.

Token discipline:
  * entries are one line each, capped in length;
  * `index()` returns a table of sessions, not their contents;
  * `summary()` of a closed session is what a later agent reads, not the log;
  * logs older than KEEP_DAYS are compacted to their summary line.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, db, security, util

MAX_ENTRY_CHARS = 300
KEEP_DAYS = 30
KINDS = ("start", "action", "result", "test", "failure", "decision", "approval",
         "spend", "handoff", "note", "end")


def log_dir() -> Path:
    d = config.home() / "LOGS" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def start(actor: str, *, model: str = "", model_class: str = "B", objective: str = "") -> str:
    """Open a session.  Returns the session id used for every later call."""
    session_id = util.new_id("SES")
    path = log_dir() / f"{session_id}.md"
    conn = db.connect()
    conn.execute(
        "INSERT INTO sessions(session_id, started_at, actor, model, model_class, objective, "
        "log_path) VALUES(?,?,?,?,?,?,?)",
        (session_id, util.now(), actor, model, model_class,
         security.redact(objective), str(path)))
    conn.commit()
    util.atomic_write(path, "\n".join([
        f"# SESSION {session_id}",
        "",
        f"- **Actor**: {actor}  ·  **Model**: {model or 'n/a'} (class {model_class})",
        f"- **Started**: {util.now()}",
        f"- **Objective**: {security.redact(objective) or 'not stated'}",
        "",
        "| Time | Kind | Entry |",
        "|---|---|---|",
        "",
    ]))
    db.log_event(actor, "session.start", session_id, objective[:120])
    return session_id


def log(session_id: str, kind: str, text: str) -> None:
    """Append one short entry.  Long text is truncated, secrets are redacted."""
    if kind not in KINDS:
        kind = "note"
    row = db.connect().execute(
        "SELECT log_path, entries FROM sessions WHERE session_id=?", (session_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown session {session_id}")
    clean = security.redact(text).replace("\n", " ").replace("|", "/")
    if len(clean) > MAX_ENTRY_CHARS:
        clean = clean[:MAX_ENTRY_CHARS - 1] + "…"
    path = Path(row["log_path"])
    # Insert before the trailing blank line so the table stays valid.
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"| {util.now()[11:19]} | {kind} | {clean} |\n")
    conn = db.connect()
    conn.execute("UPDATE sessions SET entries=entries+1 WHERE session_id=?", (session_id,))
    conn.commit()


def end(session_id: str, *, outcome: str, resume_point: str = "", spend_inr: float = 0.0,
        status: str = "CLOSED", tasks_touched: str = "") -> dict:
    conn = db.connect()
    row = conn.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown session {session_id}")
    conn.execute(
        "UPDATE sessions SET ended_at=?, outcome=?, resume_point=?, spend_inr=?, status=?, "
        "tasks_touched=? WHERE session_id=?",
        (util.now(), security.redact(outcome), security.redact(resume_point), spend_inr,
         status, tasks_touched, session_id))
    conn.commit()
    path = Path(row["log_path"])
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join([
            "",
            "## Outcome",
            security.redact(outcome),
            "",
            f"- **Ended**: {util.now()}",
            f"- **Spend**: INR {spend_inr}",
            f"- **Tasks touched**: {tasks_touched or 'none'}",
            f"- **Exact resume point**: {security.redact(resume_point) or 'not recorded'}",
            "",
        ]))
    db.log_event(row["actor"], "session.end", session_id, outcome[:120])
    _write_index()
    return summary(session_id)


def summary(session_id: str) -> dict:
    row = db.connect().execute(
        "SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
    return dict(row) if row else {}


def index(limit: int = 30) -> list:
    return db.connect().execute(
        "SELECT session_id, started_at, ended_at, actor, model_class, status, spend_inr, "
        "entries, outcome, resume_point FROM sessions ORDER BY started_at DESC LIMIT ?",
        (limit,)).fetchall()


def open_sessions() -> list:
    return db.connect().execute(
        "SELECT * FROM sessions WHERE status='OPEN' ORDER BY started_at").fetchall()


def _write_index() -> Path:
    """A single compact file a future agent reads instead of every session log."""
    lines = ["# SESSION INDEX", "",
             "_Generated. Read this, not the individual logs, unless you need detail._", "",
             "| Session | Actor | Started | Status | INR | Outcome | Resume point |",
             "|---|---|---|---|---|---|---|"]
    for r in index(50):
        lines.append(
            f"| {r['session_id']} | {r['actor']} | {r['started_at'][:16]} | {r['status']} | "
            f"{r['spend_inr']} | {(r['outcome'] or '')[:80]} | {(r['resume_point'] or '')[:80]} |")
    lines.append("")
    return util.atomic_write(config.home() / "LOGS" / "SESSION_INDEX.md", "\n".join(lines))


def compact_old(keep_days: int = KEEP_DAYS) -> int:
    """Replace old session logs with their summary line to keep context cheap."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
    rows = db.connect().execute(
        "SELECT session_id, log_path, outcome, resume_point, started_at FROM sessions "
        "WHERE status!='OPEN' AND started_at < ?", (cutoff,)).fetchall()
    compacted = 0
    for r in rows:
        path = Path(r["log_path"])
        if not path.exists() or path.stat().st_size < 400:
            continue
        util.atomic_write(path, "\n".join([
            f"# SESSION {r['session_id']} (compacted)", "",
            f"Started {r['started_at']}. Full log removed to keep context cheap.", "",
            f"**Outcome**: {r['outcome'] or 'not recorded'}", "",
            f"**Resume point**: {r['resume_point'] or 'not recorded'}", "",
        ]))
        compacted += 1
    if compacted:
        _write_index()
    return compacted
