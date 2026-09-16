"""Data intake provenance contract -- C3.

Every ingested datum carries the full provenance envelope, without
exception, so LucyOS's cross-project learning stays reversible: stricter
separation can be imposed later without a data migration crisis. A record
here is INSERT-only by design -- there is no update function, so a raw
record's immutability is a property of the API surface, not a rule someone
has to remember to follow. A correction is a new record whose `derived_from`
points at the one it supersedes.
"""
from __future__ import annotations

import json

from . import db, security, util
from .skills import DATA_CLASSES

TIERS = ("raw", "normalized", "derived", "curated", "index", "export")


class IntakeError(ValueError):
    pass


def record(source: str, tier: str, payload_path, *, project: str = "",
           confidentiality: str = "INTERNAL", entity_refs: str = "",
           schema_version: int = 1, transform_chain: list | None = None,
           training_eligible: bool = False, derived_from: str = "") -> str:
    """Register one intake record. Rejects anything missing the full C3
    metadata set rather than guessing a default for it."""
    source = (source or "").strip()
    if not source:
        raise IntakeError("source is required")
    tier = (tier or "").strip().lower()
    if tier not in TIERS:
        raise IntakeError(f"invalid tier {tier!r}; use one of {TIERS}")
    confidentiality = (confidentiality or "").strip().upper()
    if confidentiality not in DATA_CLASSES:
        raise IntakeError(f"invalid confidentiality {confidentiality!r}; use one of {sorted(DATA_CLASSES)}")
    if not payload_path:
        raise IntakeError("payload_path is required")
    content_hash = util.sha256_file(payload_path)

    record_id = util.new_id("REC")
    conn = db.connect()
    conn.execute(
        "INSERT INTO intake_records(record_id,source,acquired_at,project,tier,"
        "payload_path,entity_refs,schema_version,confidentiality,transform_chain,"
        "content_hash,training_eligible,derived_from,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (record_id, security.redact(source), util.now(), project, tier,
         str(payload_path), security.redact(entity_refs), schema_version,
         confidentiality, json.dumps(transform_chain or []), content_hash,
         int(bool(training_eligible)), derived_from, util.now()))
    conn.commit()
    return record_id


def get(record_id: str):
    return db.connect().execute(
        "SELECT * FROM intake_records WHERE record_id=?", (record_id,)).fetchone()
