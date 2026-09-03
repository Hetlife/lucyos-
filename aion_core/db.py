"""SQLite state store: the machine-readable half of the canonical shared brain.

Markdown surfaces (SYSTEM_STATE.md, APPROVALS.md, ...) are rendered *from*
this database so the two can never drift.  The database is the source of
truth; the markdown is the human view.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id           TEXT PRIMARY KEY,
    project           TEXT NOT NULL DEFAULT 'default',
    parent_task       TEXT,
    title             TEXT NOT NULL,
    description       TEXT NOT NULL DEFAULT '',
    status            TEXT NOT NULL DEFAULT 'INBOX',
    priority          INTEGER NOT NULL DEFAULT 3,
    impact            REAL NOT NULL DEFAULT 3,
    probability       REAL NOT NULL DEFAULT 0.7,
    unlocks           REAL NOT NULL DEFAULT 1,
    info_gain         REAL NOT NULL DEFAULT 1,
    cost              REAL NOT NULL DEFAULT 1,
    risk              REAL NOT NULL DEFAULT 1,
    time_est          REAL NOT NULL DEFAULT 1,
    human_dependence  REAL NOT NULL DEFAULT 1,
    owner_agent       TEXT,
    model_class       TEXT NOT NULL DEFAULT 'B',
    dependencies      TEXT NOT NULL DEFAULT '',
    blockers          TEXT NOT NULL DEFAULT '',
    approval_id       TEXT,
    success_criteria  TEXT NOT NULL DEFAULT '',
    validation_method TEXT NOT NULL DEFAULT '',
    output_location   TEXT NOT NULL DEFAULT '',
    retry_count       INTEGER NOT NULL DEFAULT 0,
    last_error        TEXT,
    next_action       TEXT NOT NULL DEFAULT '',
    kind              TEXT NOT NULL DEFAULT '',
    exec_command      TEXT NOT NULL DEFAULT '',
    validation_command TEXT NOT NULL DEFAULT '',
    plan_id           TEXT,
    evidence          TEXT NOT NULL DEFAULT '',
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    claimed_at        TEXT,
    started_at        TEXT,
    completed_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);

CREATE TABLE IF NOT EXISTS agents (
    agent_id          TEXT PRIMARY KEY,
    role              TEXT NOT NULL,
    model             TEXT NOT NULL,
    model_class       TEXT NOT NULL,
    cost_class        TEXT NOT NULL DEFAULT 'medium',
    capabilities      TEXT NOT NULL DEFAULT '',
    max_complexity    INTEGER NOT NULL DEFAULT 3,
    allowed_tools     TEXT NOT NULL DEFAULT '',
    current_task      TEXT,
    status            TEXT NOT NULL DEFAULT 'IDLE',
    last_health_check TEXT,
    reliability       REAL NOT NULL DEFAULT 1.0,
    runs              INTEGER NOT NULL DEFAULT 0,
    failures          INTEGER NOT NULL DEFAULT 0,
    known_failures    TEXT NOT NULL DEFAULT '',
    enabled           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id     TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    decided_at      TEXT,
    project         TEXT NOT NULL DEFAULT 'default',
    action          TEXT NOT NULL,
    why             TEXT NOT NULL DEFAULT '',
    owner_action    TEXT NOT NULL DEFAULT '',
    cost            TEXT NOT NULL DEFAULT 'none',
    max_downside    TEXT NOT NULL DEFAULT '',
    expected_benefit TEXT NOT NULL DEFAULT '',
    reversibility   TEXT NOT NULL DEFAULT 'unknown',
    prepared        TEXT NOT NULL DEFAULT '',
    resumes         TEXT NOT NULL DEFAULT '',
    recommendation  TEXT NOT NULL DEFAULT 'APPROVE',
    status          TEXT NOT NULL DEFAULT 'PENDING',
    decided_by      TEXT,
    task_id         TEXT
);

CREATE TABLE IF NOT EXISTS packets (
    packet_id      TEXT PRIMARY KEY,
    source         TEXT NOT NULL,
    source_session TEXT,
    received_at    TEXT NOT NULL,
    timestamp      TEXT,
    project        TEXT NOT NULL DEFAULT 'default',
    topic          TEXT NOT NULL DEFAULT '',
    hash           TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'PENDING',
    error          TEXT,
    stored_path    TEXT,
    processed_at   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_packets_hash ON packets(hash);

CREATE TABLE IF NOT EXISTS errors (
    error_id    TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    component   TEXT NOT NULL,
    task_id     TEXT,
    kind        TEXT NOT NULL DEFAULT 'unknown',
    message     TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '',
    root_cause  TEXT,
    fix         TEXT,
    lesson      TEXT,
    status      TEXT NOT NULL DEFAULT 'OPEN',
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS model_usage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    at            TEXT NOT NULL,
    day           TEXT NOT NULL,
    month         TEXT NOT NULL,
    model         TEXT NOT NULL,
    model_class   TEXT NOT NULL,
    task_id       TEXT,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_inr      REAL NOT NULL DEFAULT 0,
    success       INTEGER NOT NULL DEFAULT 1,
    retries       INTEGER NOT NULL DEFAULT 0,
    escalated     INTEGER NOT NULL DEFAULT 0,
    note          TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_usage_day ON model_usage(day);

CREATE TABLE IF NOT EXISTS finance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          TEXT NOT NULL,
    day         TEXT NOT NULL,
    kind        TEXT NOT NULL,            -- revenue | cost | reserve
    stage       TEXT NOT NULL DEFAULT 'ACTUAL', -- ACTUAL|FORECAST|SIMULATION|PAPER|BACKTEST
    amount_inr  REAL NOT NULL,
    project     TEXT NOT NULL DEFAULT 'default',
    description TEXT NOT NULL DEFAULT '',
    evidence    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    at          TEXT NOT NULL,
    subject     TEXT NOT NULL,
    decision    TEXT NOT NULL,
    rationale   TEXT NOT NULL DEFAULT '',
    evidence    TEXT NOT NULL DEFAULT '',
    confidence  TEXT NOT NULL DEFAULT 'INFERENCE',
    made_by     TEXT NOT NULL DEFAULT 'aion'
);

CREATE TABLE IF NOT EXISTS memory (
    memory_id  TEXT PRIMARY KEY,
    at         TEXT NOT NULL,
    kind       TEXT NOT NULL,   -- fact|decision|lesson|preference|research
    project    TEXT NOT NULL DEFAULT 'default',
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'INFERENCE',
    source     TEXT NOT NULL DEFAULT '',
    source_date TEXT,
    tags       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    at      TEXT NOT NULL,
    day     TEXT NOT NULL,
    actor   TEXT NOT NULL,
    kind    TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    detail  TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_events_day ON events(day);

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    actor        TEXT NOT NULL,          -- openclaw | chatgpt | claude | ollama | owner
    model        TEXT NOT NULL DEFAULT '',
    model_class  TEXT NOT NULL DEFAULT 'B',
    objective    TEXT NOT NULL DEFAULT '',
    outcome      TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'OPEN',
    spend_inr    REAL NOT NULL DEFAULT 0,
    tasks_touched TEXT NOT NULL DEFAULT '',
    resume_point TEXT NOT NULL DEFAULT '',
    log_path     TEXT NOT NULL DEFAULT '',
    entries      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);

CREATE TABLE IF NOT EXISTS notebook (
    entry_id     TEXT PRIMARY KEY,
    at           TEXT NOT NULL,
    author       TEXT NOT NULL DEFAULT 'unknown',
    kind         TEXT NOT NULL,
    title        TEXT NOT NULL,
    body         TEXT NOT NULL DEFAULT '',
    hash         TEXT NOT NULL,
    created_ref  TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'PROCESSED'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notebook_hash ON notebook(hash);

CREATE TABLE IF NOT EXISTS idempotency (
    key       TEXT PRIMARY KEY,
    at        TEXT NOT NULL,
    scope     TEXT NOT NULL,
    result    TEXT NOT NULL DEFAULT ''
);
"""

_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    title, body, tags, content='memory', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO memory_fts(rowid, title, body, tags)
    VALUES (new.rowid, new.title, new.body, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, body, tags)
    VALUES ('delete', old.rowid, old.title, old.body, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, body, tags)
    VALUES ('delete', old.rowid, old.title, old.body, old.tags);
    INSERT INTO memory_fts(rowid, title, body, tags)
    VALUES (new.rowid, new.title, new.body, new.tags);
END;
"""

_conn: sqlite3.Connection | None = None
_conn_path: str | None = None

HAS_FTS = True


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Process-wide connection, re-opened if AION_DB changes (tests)."""
    global _conn, _conn_path, HAS_FTS
    target = str(Path(path or config.db_path()).expanduser())
    if _conn is not None and _conn_path == target:
        return _conn
    if _conn is not None:
        _conn.close()
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    # The bridge serves HTTP on a server thread while the CLI/loop uses the main
    # thread.  Access is serialised (HTTPServer is single-threaded and the loop
    # never runs concurrently with a request in the same process), so sharing
    # one connection across threads is safe; without this flag SQLite refuses.
    conn = sqlite3.connect(target, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        conn.executescript(_FTS)
        HAS_FTS = True
    except sqlite3.OperationalError:
        # SQLite build without FTS5: memory search falls back to LIKE.
        HAS_FTS = False
    _migrate(conn)
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(config.SCHEMA_VERSION),),
    )
    conn.commit()
    _conn, _conn_path = conn, target
    return conn


# Columns added after the first release.  Additive only: never drop or rename,
# so an older database keeps working and an older binary keeps reading a newer one.
_ADDED_COLUMNS = {
    "tasks": [
        ("kind", "TEXT NOT NULL DEFAULT ''"),
        ("exec_command", "TEXT NOT NULL DEFAULT ''"),
        ("validation_command", "TEXT NOT NULL DEFAULT ''"),
        ("plan_id", "TEXT"),
    ],
}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, columns in _ADDED_COLUMNS.items():
        have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, spec in columns:
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {spec}")
    conn.commit()


def close() -> None:
    global _conn, _conn_path
    if _conn is not None:
        _conn.close()
    _conn, _conn_path = None, None


def get_meta(key: str, default: str | None = None) -> str | None:
    row = connect().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(key: str, value: str) -> None:
    conn = connect()
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    conn.commit()


def log_event(actor: str, kind: str, subject: str = "", detail: str = "") -> None:
    from . import security, util
    conn = connect()
    conn.execute(
        "INSERT INTO events(at, day, actor, kind, subject, detail) VALUES(?,?,?,?,?,?)",
        (util.now(), util.today(), actor, kind, security.redact(subject), security.redact(detail)),
    )
    conn.commit()


def seen(key: str, scope: str, result: str = "") -> bool:
    """Idempotency guard.  Returns True if this key was already processed."""
    from . import util
    conn = connect()
    row = conn.execute("SELECT 1 FROM idempotency WHERE key=?", (key,)).fetchone()
    if row:
        return True
    conn.execute(
        "INSERT INTO idempotency(key, at, scope, result) VALUES(?,?,?,?)",
        (key, util.now(), scope, result),
    )
    conn.commit()
    return False
