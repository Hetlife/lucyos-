"""Local durable memory with hybrid retrieval (FTS5 where available)."""
from __future__ import annotations

from . import db, security, util

KINDS = ("fact", "decision", "lesson", "preference", "research")
CONFIDENCE = ("VERIFIED_FACT", "SUPPORTED_FACT", "INFERENCE", "ESTIMATE",
              "ASSUMPTION", "HYPOTHESIS", "UNKNOWN")


def remember(kind: str, title: str, body: str, *, project: str = "default",
             confidence: str = "INFERENCE", source: str = "", source_date: str | None = None,
             tags: str = "") -> str:
    if kind not in KINDS:
        raise ValueError(f"unknown memory kind {kind!r}; use one of {KINDS}")
    if confidence not in CONFIDENCE:
        raise ValueError(f"unknown confidence {confidence!r}")
    body = security.redact(body)
    title = security.redact(title)
    # Avoid duplicate memories (sync rule): same kind+title+body is a no-op.
    key = util.sha256_text(f"{kind}|{title}|{body}")
    existing = db.connect().execute(
        "SELECT memory_id FROM memory WHERE memory_id LIKE 'MEM-%' AND title=? AND body=? AND kind=?",
        (title, body, kind)).fetchone()
    if existing:
        return existing["memory_id"]
    memory_id = f"MEM-{key[:10].upper()}"
    conn = db.connect()
    conn.execute(
        "INSERT OR IGNORE INTO memory(memory_id, at, kind, project, title, body, confidence, "
        "source, source_date, tags) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (memory_id, util.now(), kind, project, title, body, confidence, source, source_date, tags))
    conn.commit()
    return memory_id


def search(query: str, limit: int = 10, kind: str | None = None) -> list:
    conn = db.connect()
    if db.HAS_FTS and query.strip():
        safe = " ".join(f'"{tok}"' for tok in query.split() if tok.strip())
        sql = ("SELECT m.* FROM memory_fts f JOIN memory m ON m.rowid = f.rowid "
               "WHERE memory_fts MATCH ?")
        params: list = [safe]
        if kind:
            sql += " AND m.kind=?"
            params.append(kind)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        try:
            return conn.execute(sql, params).fetchall()
        except Exception:
            pass
    like = f"%{query}%"
    sql = "SELECT * FROM memory WHERE (title LIKE ? OR body LIKE ? OR tags LIKE ?)"
    params = [like, like, like]
    if kind:
        sql += " AND kind=?"
        params.append(kind)
    sql += " ORDER BY at DESC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def recent(limit: int = 10, kind: str | None = None) -> list:
    conn = db.connect()
    if kind:
        return conn.execute("SELECT * FROM memory WHERE kind=? ORDER BY at DESC LIMIT ?",
                            (kind, limit)).fetchall()
    return conn.execute("SELECT * FROM memory ORDER BY at DESC LIMIT ?", (limit,)).fetchall()


def decide(subject: str, decision: str, rationale: str = "", evidence: str = "",
           confidence: str = "INFERENCE", made_by: str = "aion") -> str:
    decision_id = util.new_id("DEC")
    conn = db.connect()
    conn.execute(
        "INSERT INTO decisions(decision_id, at, subject, decision, rationale, evidence, "
        "confidence, made_by) VALUES(?,?,?,?,?,?,?,?)",
        (decision_id, util.now(), security.redact(subject), security.redact(decision),
         security.redact(rationale), security.redact(evidence), confidence, made_by))
    conn.commit()
    remember("decision", subject, f"{decision}\n\nRationale: {rationale}",
             confidence=confidence, source=decision_id)
    return decision_id


def decisions(limit: int = 20) -> list:
    return db.connect().execute(
        "SELECT * FROM decisions ORDER BY at DESC LIMIT ?", (limit,)).fetchall()


def why(ref_id: str) -> str:
    """Explain a decision, approval or task by id — the `why <ID>` command."""
    ref = ref_id.upper()
    conn = db.connect()
    row = conn.execute("SELECT * FROM decisions WHERE decision_id=?", (ref,)).fetchone()
    if row:
        return (f"{ref} ({row['at']}) — {row['subject']}\n"
                f"Decision: {row['decision']}\nRationale: {row['rationale'] or 'not recorded'}\n"
                f"Evidence: {row['evidence'] or 'none recorded'}\nConfidence: {row['confidence']}\n"
                f"Decided by: {row['made_by']}")
    row = conn.execute("SELECT * FROM approvals WHERE approval_id=?", (ref,)).fetchone()
    if row:
        return (f"{ref} — {row['action']}\nStatus: {row['status']}\n"
                f"Why required: {row['why'] or 'not recorded'}\nCost: {row['cost']}\n"
                f"Max downside: {row['max_downside'] or 'not recorded'}\n"
                f"Reversibility: {row['reversibility']}")
    row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (ref,)).fetchone()
    if row:
        return (f"{ref} — {row['title']}\nStatus: {row['status']}\n"
                f"Why: {row['description'] or 'not recorded'}\n"
                f"Success criteria: {row['success_criteria'] or 'not recorded'}\n"
                f"Evidence: {row['evidence'] or 'none yet'}\nNext: {row['next_action'] or 'not set'}")
    row = conn.execute("SELECT * FROM errors WHERE error_id=?", (ref,)).fetchone()
    if row:
        return (f"{ref} — {row['component']} {row['kind']} failure\nMessage: {row['message']}\n"
                f"Root cause: {row['root_cause'] or 'not yet determined'}\n"
                f"Fix: {row['fix'] or 'none yet'}\nStatus: {row['status']}")
    return f"No record found for {ref}. Known id prefixes: DEC-, A-, TASK-, ERR-."
