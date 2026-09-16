#!/usr/bin/env python3
"""Shared path and I/O helpers for the learnrepo skill.

Investigation artifacts are machine state, not source.  They live under
AION_HOME (the LucyOS shared brain) so that quarantined third-party code,
research notes and evidence never land in a version-controlled — possibly
public — repository.  This mirrors the rule LucyOS already applies to the
shared brain itself.

Resolution order for the artifact root:
  1. $LEARNREPO_HOME                  (explicit override, used by tests)
  2. $AION_HOME/learnrepo             (normal LucyOS operation)
  3. ~/openclaw/shared_brain/learnrepo (AION's documented default)

Standard library only, Python 3.9+, to match LucyOS's dependency policy.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1

# A capability id is a stable, path-independent identifier.  Keeping it
# restrictive means it can safely become a directory name, a JSON key and a
# branch-name fragment without escaping surprises.
CAPABILITY_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SUBDIRS = ("research", "assessments", "candidate")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def home() -> Path:
    override = os.environ.get("LEARNREPO_HOME")
    if override:
        return Path(override).expanduser()
    aion_home = os.environ.get("AION_HOME")
    base = Path(aion_home).expanduser() if aion_home else Path.home() / "openclaw" / "shared_brain"
    return base / "learnrepo"


def registry_path() -> Path:
    return home() / "registry.json"


def investigations_dir() -> Path:
    return home() / "investigations"


def investigation_dir(capability_id: str) -> Path:
    return investigations_dir() / capability_id


def validate_capability_id(capability_id: str) -> None:
    if not CAPABILITY_ID.match(capability_id or ""):
        raise ValueError(
            f"invalid capability id {capability_id!r}: use lowercase words "
            "joined by single dashes, e.g. 'live-agent-activity-view'")


def read_json(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: dict) -> Path:
    """Write JSON atomically so an interrupted run never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)
    return path


def load_registry() -> dict:
    path = registry_path()
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "updated_at": now(), "capabilities": {}}
    return read_json(path)


def save_registry(registry: dict) -> Path:
    registry["updated_at"] = now()
    return write_json(registry_path(), registry)


def blank_manifest(capability_id: str, name: str = "", purpose: str = "") -> dict:
    """A manifest with every schema-v1 key present and honestly empty.

    Unknown is represented as null or an empty list rather than an optimistic
    default, so an unfilled manifest fails the gate instead of passing it.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "capability_id": capability_id,
        "name": name or capability_id.replace("-", " "),
        "purpose": purpose,
        "request": "",
        "candidates": [],
        "consumers": [],
        "status": "draft",
        "created_at": now(),
        "updated_at": now(),
        "source": {
            "kind": "unknown",
            "canonical_url": "",
            "owner": "",
            "commit": "",
            "tag": "",
            "version": "",
            "release_date": "",
            "retrieved_at": "",
            "provenance_verified": False,
            "provenance_notes": "",
        },
        "license": {
            "spdx": "",
            "source_of_truth": "",
            "obligations": [],
            "commercial_use": "unclear",
            "redistribution": "unclear",
            "network_use": "unclear",
            "modification": "unclear",
            "compatible_with_lucyos": None,
            "requires_legal_review": False,
            "notes": "",
        },
        "evidence": [],
        "learned": "",
        "disposition": {
            "reused": [], "wrapped": [], "rewritten": [], "patched": [], "rejected": [],
        },
        "dependencies": {
            "direct": [], "transitive_count": None, "pinned": False, "lockfile": "",
        },
        "runtime": {
            "permissions": [], "network": [], "secrets": [],
            "telemetry": "unknown", "data_flows": [],
        },
        "security": {
            "findings": [],
            "screened_at": "",
            "screening_method": "",
            "execution_performed": False,
            "sandbox": "none",
        },
        "changes": {"files_added": [], "files_changed": [], "files_removed": []},
        "tests": {
            "suites": [],
            "regression_suite_run": False,
            "regression_result": "not_run",
        },
        "resources": {
            "cpu": "", "memory": "", "disk": "", "network": "",
            "latency": "", "token_cost": "", "monetary_cost": "",
        },
        "confidence": {
            "evidence": None, "functional_fit": None, "lucyos_compatibility": None,
            "security": None, "license": None, "test": None,
            "maintainability": None, "overall": None,
        },
        "confidence_reasons": {},
        "assessment": {
            "expected_value": "",
            "integration_effort": "",
            "failure_impact": "",
            "reversibility": "",
            "recommendation": "",
        },
        "limitations": [],
        "residual_risks": [],
        "feature_flag": {"name": "", "default": "off"},
        "rollback": {"steps": [], "tested": False, "tested_evidence": ""},
        "integration": {
            "pattern": "", "branch": "", "baseline_commit": "", "target_branch": "main",
        },
        "external_services": {
            "required": False,
            "services": [],
            "accounts_needed": [],
            "privacy_review_required": False,
            "cost_review_required": False,
            "activation_is_separate_approval": True,
        },
        "monitoring": {"enabled": False, "watch": []},
        "approval": {"status": "not_requested", "approver": "", "timestamp": "", "note": ""},
    }
