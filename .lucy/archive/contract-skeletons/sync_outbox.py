"""Local-first PENDING_SYNC ledger -- contract C2.

Outbound Drive/remote work becomes a durable row in the *existing* canonical
SQLite, never a second database or queue. Local work never blocks on Drive:
`queue()` only ever writes locally. A trusted external promoter (something
with real Drive write access) later claims a row, syncs it, and marks the
outcome; LucyOS itself never assumes the sync happened.
"""
from __future__ import annotations

from . import db, security, util

STATUSES = ("PENDING_SYNC", "CLAIMED", "SYNCED", "CONFLICT", "REJECTED", "SUPERSEDED")
# Local-wins-with-evidence (C2): a conflict is recorded, never silently
# resolved by overwriting either side, and nothing auto-retries out of it.
_TRANSITIONS = {
    "PENDING_SYNC": {"CLAIMED"},
    "CLAIMED": {"SYNCED", "CONFLICT", "PENDING_SYNC"},  # PENDING_SYNC: a promoter released its claim
    "SYNCED": set(),
    "CONFLICT": set(),
    "REJECTED": set(),
    "SUPERSEDED": set(),
}


class SyncOutboxError(ValueError):
    pass


def queue(kind: str, local_path: str, *, project: str = "", remote_target: str = "") -> str:
    """Register outbound-sync intent for a local file. Idempotent by content:
    re-queuing identical bytes returns the existing sync_id instead of adding
    a duplicate row, so a retried caller can never fan out the same content."""
    content_hash = util.sha256_file(local_path)
    conn = db.connect()
    existing = conn.execute(
        "SELECT sync_id FROM sync_outbox WHERE content_hash=? "
        "AND status NOT IN ('REJECTED','SUPERSEDED')", (content_hash,)).fetchone()
    if existing:
        return existing["sync_id"]
    sync_id = util.new_id("SYN")
    conn.execute(
        "INSERT INTO sync_outbox(sync_id,at,project,kind,local_path,content_hash,"
        "remote_target,status) VALUES (?,?,?,?,?,?,?,?)",
        (sync_id, util.now(), project, kind, str(local_path), content_hash,
         remote_target, "PENDING_SYNC"))
    conn.commit()
    return sync_id


def _row(sync_id: str):
    row = db.connect().execute(
        "SELECT * FROM sync_outbox WHERE sync_id=?", (sync_id,)).fetchone()
    if row is None:
        raise SyncOutboxError(f"no such sync_id {sync_id!r}")
    return row


def _set_status(sync_id: str, row, to_status: str, **extra) -> None:
    current = row["status"]
    if to_status not in _TRANSITIONS.get(current, set()):
        raise SyncOutboxError(f"illegal transition {current} -> {to_status} for {sync_id}")
    conn = db.connect()
    cols = ["status"] + list(extra)
    vals = [to_status] + list(extra.values()) + [sync_id]
    conn.execute(f"UPDATE sync_outbox SET {', '.join(c + '=?' for c in cols)} "
                 "WHERE sync_id=?", vals)
    conn.commit()


def claim(sync_id: str, by: str) -> None:
    """A promoter takes ownership of a PENDING_SYNC row before acting on it."""
    row = _row(sync_id)
    _set_status(sync_id, row, "CLAIMED", promoted_by=by, attempts=row["attempts"] + 1)


def mark_synced(sync_id: str) -> None:
    row = _row(sync_id)
    _set_status(sync_id, row, "SYNCED", synced_at=util.now())


def mark_conflict(sync_id: str, detail: str) -> None:
    row = _row(sync_id)
    _set_status(sync_id, row, "CONFLICT", last_error=security.redact(detail)[:500])


def pending() -> list:
    """Rows a promoter can act on next, oldest first."""
    return db.connect().execute(
        "SELECT * FROM sync_outbox WHERE status='PENDING_SYNC' ORDER BY at").fetchall()


def backlog() -> dict:
    """Counts by status -- the honest, cheap answer to 'how much is waiting'."""
    counts = {status: 0 for status in STATUSES}
    for row in db.connect().execute(
            "SELECT status, COUNT(*) AS n FROM sync_outbox GROUP BY status"):
        counts[row["status"]] = row["n"]
    return counts
