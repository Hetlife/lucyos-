"""SQLite state store: the machine-readable half of the canonical shared brain.

Markdown surfaces (SYSTEM_STATE.md, APPROVALS.md, ...) are rendered *from*
this database so the two can never drift.  The database is the source of
truth; the markdown is the human view.
"""
from __future__ import annotations

import sqlite3
import threading
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
    data_class        TEXT NOT NULL DEFAULT 'INTERNAL',
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

CREATE TABLE IF NOT EXISTS skills (
    skill_id          TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    description       TEXT NOT NULL DEFAULT '',
    version           TEXT NOT NULL DEFAULT '0.1.0',
    capabilities      TEXT NOT NULL DEFAULT '',
    executor_classes  TEXT NOT NULL DEFAULT 'DET',
    platforms         TEXT NOT NULL DEFAULT 'any',
    network_required  INTEGER NOT NULL DEFAULT 0,
    ai_required       INTEGER NOT NULL DEFAULT 0,
    offline_supported INTEGER NOT NULL DEFAULT 1,
    cost_class        TEXT NOT NULL DEFAULT 'F0',
    risk_class        TEXT NOT NULL DEFAULT 'R1',
    data_class        TEXT NOT NULL DEFAULT 'INTERNAL',
    priority          TEXT NOT NULL DEFAULT 'P1',
    enabled           INTEGER NOT NULL DEFAULT 1,
    health_command    TEXT NOT NULL DEFAULT '',
    test_command      TEXT NOT NULL DEFAULT '',
    lifecycle_state   TEXT NOT NULL DEFAULT 'ACTIVE',
    feature_flag      TEXT NOT NULL DEFAULT '',
    source_manifest   TEXT NOT NULL DEFAULT '',
    updated_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_skills_enabled ON skills(enabled);

CREATE TABLE IF NOT EXISTS learnrepo_skill_reviews (
    review_id       TEXT PRIMARY KEY,
    skill_id        TEXT NOT NULL,
    candidate_id    TEXT NOT NULL,
    candidate_url   TEXT NOT NULL DEFAULT '',
    candidate_role  TEXT NOT NULL DEFAULT 'primary',
    stage           TEXT NOT NULL,
    verdict         TEXT NOT NULL DEFAULT 'PASS',
    evidence_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE(skill_id, candidate_id, stage)
);
CREATE INDEX IF NOT EXISTS idx_learnrepo_skill_reviews_skill ON learnrepo_skill_reviews(skill_id, stage);

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

CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id TEXT PRIMARY KEY,
    project TEXT NOT NULL DEFAULT 'default',
    payer_id TEXT,
    customer_id TEXT,
    status TEXT NOT NULL DEFAULT 'PLANNED',
    reference TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_deliveries_project_status
    ON deliveries(project, status);

CREATE TABLE IF NOT EXISTS monthly_closes (
    project TEXT NOT NULL,
    month TEXT NOT NULL,
    costs_complete INTEGER NOT NULL DEFAULT 0,
    evidence TEXT NOT NULL,
    closed_at TEXT NOT NULL,
    PRIMARY KEY(project, month)
);

CREATE TABLE IF NOT EXISTS finance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          TEXT NOT NULL,
    day         TEXT NOT NULL,
    kind        TEXT NOT NULL,            -- revenue | cost | reserve
    stage       TEXT NOT NULL DEFAULT 'ACTUAL', -- ACTUAL|FORECAST|SIMULATION|PAPER|BACKTEST
    amount_inr  REAL NOT NULL,
    project     TEXT NOT NULL DEFAULT 'default',
    payer_id    TEXT,
    delivery_id TEXT REFERENCES deliveries(delivery_id),
    cost_category TEXT,
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

CREATE TABLE IF NOT EXISTS hands_off_days (
    day TEXT PRIMARY KEY,
    autonomous_completions INTEGER NOT NULL,
    owner_operations INTEGER NOT NULL,
    owner_approvals INTEGER NOT NULL,
    qualifies INTEGER NOT NULL,
    evidence TEXT NOT NULL,
    evaluated_at TEXT NOT NULL
);

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

CREATE TABLE IF NOT EXISTS sync_outbox (
    sync_id      TEXT PRIMARY KEY,
    at           TEXT NOT NULL,
    project      TEXT NOT NULL DEFAULT '',
    kind         TEXT NOT NULL,
    local_path   TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    remote_target TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL,
    attempts     INTEGER NOT NULL DEFAULT 0,
    last_error   TEXT NOT NULL DEFAULT '',
    synced_at    TEXT NOT NULL DEFAULT '',
    promoted_by  TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_sync_outbox_status ON sync_outbox(status);
CREATE INDEX IF NOT EXISTS idx_sync_outbox_hash ON sync_outbox(content_hash);
CREATE TABLE IF NOT EXISTS intake_records (
    record_id         TEXT PRIMARY KEY,
    source            TEXT NOT NULL,
    acquired_at       TEXT NOT NULL,
    project           TEXT NOT NULL DEFAULT '',
    tier              TEXT NOT NULL,
    payload_path      TEXT NOT NULL,
    entity_refs       TEXT NOT NULL DEFAULT '',
    schema_version    INTEGER NOT NULL DEFAULT 1,
    confidentiality   TEXT NOT NULL,
    transform_chain   TEXT NOT NULL DEFAULT '[]',
    content_hash      TEXT NOT NULL,
    training_eligible INTEGER NOT NULL DEFAULT 0,
    derived_from      TEXT NOT NULL DEFAULT '',
    created_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_intake_project_tier ON intake_records(project, tier);
CREATE INDEX IF NOT EXISTS idx_intake_hash ON intake_records(content_hash);

CREATE TABLE IF NOT EXISTS taskcheck_templates (
    template_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    checks_json TEXT NOT NULL,
    critical_rules_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(template_id, version)
);

CREATE TABLE IF NOT EXISTS taskcheck_runs (
    taskcheck_id TEXT PRIMARY KEY,
    aion_task_id TEXT NOT NULL UNIQUE REFERENCES tasks(task_id),
    template_id TEXT NOT NULL,
    template_version INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    requester TEXT NOT NULL,
    assignee TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    priority INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'CREATED',
    result_status TEXT NOT NULL DEFAULT '',
    access_token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT,
    revoked_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    opened_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    reviewed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_taskcheck_runs_status ON taskcheck_runs(status);

CREATE TABLE IF NOT EXISTS taskcheck_checks (
    taskcheck_id TEXT NOT NULL REFERENCES taskcheck_runs(taskcheck_id),
    check_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    response TEXT,
    note TEXT NOT NULL DEFAULT '',
    answered_at TEXT,
    PRIMARY KEY(taskcheck_id, check_id)
);

CREATE TABLE IF NOT EXISTS taskcheck_evidence (
    evidence_id TEXT PRIMARY KEY,
    taskcheck_id TEXT NOT NULL REFERENCES taskcheck_runs(taskcheck_id),
    check_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_taskcheck_evidence_task ON taskcheck_evidence(taskcheck_id, check_id);

CREATE TABLE IF NOT EXISTS idempotency (
    key       TEXT PRIMARY KEY,
    at        TEXT NOT NULL,
    scope     TEXT NOT NULL,
    result    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS learnrepo_tasks (
    task_type TEXT PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    health_level INTEGER NOT NULL DEFAULT 0,
    requires_network INTEGER NOT NULL DEFAULT 0,
    requires_ai INTEGER NOT NULL DEFAULT 0,
    safe_repair TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS learnrepo_schedules (
    schedule_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL REFERENCES learnrepo_tasks(task_type),
    schedule_class TEXT NOT NULL,
    next_run_at TEXT,
    last_run_at TEXT,
    grace_seconds INTEGER NOT NULL DEFAULT 1200,
    enabled INTEGER NOT NULL DEFAULT 1,
    change_sensitive INTEGER NOT NULL DEFAULT 1,
    change_score INTEGER NOT NULL DEFAULT 0,
    lease_owner TEXT,
    lease_until TEXT
);
CREATE INDEX IF NOT EXISTS idx_learnrepo_schedules_due ON learnrepo_schedules(enabled, next_run_at);

CREATE TABLE IF NOT EXISTS learnrepo_runs (
    run_id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL REFERENCES learnrepo_schedules(schedule_id),
    task_type TEXT NOT NULL,
    expected_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'SCHEDULED',
    grace_seconds INTEGER NOT NULL DEFAULT 1200,
    result_json TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    evidence_path TEXT NOT NULL DEFAULT '',
    lease_owner TEXT,
    lease_until TEXT
);
CREATE INDEX IF NOT EXISTS idx_learnrepo_runs_status ON learnrepo_runs(status);

CREATE TABLE IF NOT EXISTS learnrepo_contracts (
    contract_id TEXT PRIMARY KEY,
    producer TEXT NOT NULL,
    input_name TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    consumer TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    validation_command TEXT NOT NULL,
    severity_if_broken TEXT NOT NULL DEFAULT 'MEDIUM'
);

CREATE TABLE IF NOT EXISTS learnrepo_escalations (
    fingerprint TEXT PRIMARY KEY,
    escalation_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    run_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    health_level INTEGER NOT NULL,
    trigger TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    owner_approval_required INTEGER NOT NULL DEFAULT 0,
    task_id TEXT
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

_thread_state = threading.local()

HAS_FTS = True


def connect(path: Path | None = None) -> sqlite3.Connection:
    """One connection per thread, re-opened if AION_DB changes (tests)."""
    global HAS_FTS
    target = str(Path(path or config.db_path()).expanduser())
    conn = getattr(_thread_state, "conn", None)
    conn_path = getattr(_thread_state, "conn_path", None)
    if conn is not None and conn_path == target:
        return conn
    if conn is not None:
        conn.close()
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=15)
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
    _thread_state.conn, _thread_state.conn_path = conn, target
    return conn


# Columns added after the first release.  Additive only: never drop or rename,
# so an older database keeps working and an older binary keeps reading a newer one.
_ADDED_COLUMNS = {
    "tasks": [
        ("kind", "TEXT NOT NULL DEFAULT ''"),
        ("exec_command", "TEXT NOT NULL DEFAULT ''"),
        ("validation_command", "TEXT NOT NULL DEFAULT ''"),
        ("plan_id", "TEXT"),
        ("data_class", "TEXT NOT NULL DEFAULT 'INTERNAL'"),
    ],
    # Nullable by design: revenue recorded before stable payer identity was
    # introduced remains unknown rather than being inferred from description.
    "skills": [
        ("lifecycle_state", "TEXT NOT NULL DEFAULT 'ACTIVE'"),
        ("feature_flag", "TEXT NOT NULL DEFAULT ''"),
        ("source_manifest", "TEXT NOT NULL DEFAULT ''"),
        ("risk_class", "TEXT NOT NULL DEFAULT 'R1'"),
        ("data_class", "TEXT NOT NULL DEFAULT 'INTERNAL'"),
        ("priority", "TEXT NOT NULL DEFAULT 'P1'"),
    ],
    "finance": [
        ("payer_id", "TEXT"),
        # Explicitly nullable.  Old rows and genuinely unattributable money
        # must stay unlinked rather than acquiring guessed identities.
        ("delivery_id", "TEXT"),
        ("cost_category", "TEXT"),
    ],
    # Guard-rail columns for contract C6 temporary workers (S-16).  Additive
    # and both nullable: a permanent agent has neither a parent nor an
    # expiry, and nothing here ever spawns a row that sets them -- that is
    # explicitly future work, gated on this schema existing first.
    "agents": [
        ("parent_agent_id", "TEXT"),
        ("expires_at", "TEXT"),
    ],
}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, columns in _ADDED_COLUMNS.items():
        have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, spec in columns:
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {spec}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_finance_delivery ON finance(delivery_id)")
    conn.commit()


def close() -> None:
    conn = getattr(_thread_state, "conn", None)
    if conn is not None:
        conn.close()
    _thread_state.conn, _thread_state.conn_path = None, None


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
