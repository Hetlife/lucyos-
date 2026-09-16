"""LearnRepo — the Talent Hunter research registry.

Anything that could eventually run inside LucyOS (a third-party library, a
telemetry parser, a monitoring tool) is registered here first and moves
through one pipeline before it touches production:

    RESEARCH -> SANDBOX -> SECURITY_REVIEW -> BENCHMARK -> OWNER_APPROVAL
    -> APPROVED (or REJECTED at any stage)

A row existing here grants it nothing.  Nothing outside this module reads
`research_targets` to decide what to execute; the only effect of reaching
APPROVED is that a human, in a separate deliberate step, wires the approved
component in.  This keeps third-party code out of the control plane.
"""
from __future__ import annotations

from . import db, security, util

STAGES = ("RESEARCH", "SANDBOX", "SECURITY_REVIEW", "BENCHMARK", "OWNER_APPROVAL",
          "APPROVED", "REJECTED")


class LearnRepoError(ValueError):
    pass


def register(capability: str, candidate: str, *, notes: str = "") -> str:
    """Register a research target.  Idempotent per (capability, candidate)."""
    conn = db.connect()
    existing = conn.execute(
        "SELECT target_id FROM research_targets WHERE capability=? AND candidate=?",
        (capability, candidate)).fetchone()
    if existing:
        return existing["target_id"]
    target_id = util.new_id("LR")
    conn.execute(
        "INSERT INTO research_targets(target_id, at, capability, candidate, notes, stage, "
        "updated_at, evidence) VALUES(?,?,?,?,?,?,?,?)",
        (target_id, util.now(), capability, candidate, security.redact(notes), "RESEARCH",
         util.now(), ""))
    conn.commit()
    db.log_event("learnrepo", "register", target_id, f"{capability}: {candidate}")
    return target_id


def advance(target_id: str, stage: str, *, evidence: str = "") -> None:
    """Move a target to a later (or REJECTED) stage.  Never skips backward silently."""
    if stage not in STAGES:
        raise LearnRepoError(f"unknown stage {stage!r}; use one of {STAGES}")
    row = get(target_id)
    if row is None:
        raise LearnRepoError(f"no such research target {target_id}")
    conn = db.connect()
    conn.execute(
        "UPDATE research_targets SET stage=?, updated_at=?, evidence=? WHERE target_id=?",
        (stage, util.now(), security.redact(evidence), target_id))
    conn.commit()
    db.log_event("learnrepo", "advance", target_id, f"{row['stage']} -> {stage}")


def get(target_id: str):
    return db.connect().execute(
        "SELECT * FROM research_targets WHERE target_id=?", (target_id,)).fetchone()


def list_targets(capability: str | None = None) -> list:
    if capability:
        return db.connect().execute(
            "SELECT * FROM research_targets WHERE capability=? ORDER BY at", (capability,)
        ).fetchall()
    return db.connect().execute("SELECT * FROM research_targets ORDER BY at").fetchall()


def is_approved(capability: str, candidate: str) -> bool:
    row = db.connect().execute(
        "SELECT stage FROM research_targets WHERE capability=? AND candidate=?",
        (capability, candidate)).fetchone()
    return bool(row) and row["stage"] == "APPROVED"
