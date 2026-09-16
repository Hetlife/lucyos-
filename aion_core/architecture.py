"""Deterministic architecture guard for LucyOS skill integrations.

Q006 prevents candidate integrations from silently creating parallel control
planes.  It performs local validation only and can record PASS/NEEDS_REVIEW
evidence into the existing LearnRepo skill-review contract.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import learnrepo, skills

FORBIDDEN_DUPLICATES = {
    "new_canonical_state": "second canonical state store",
    "new_global_queue": "second global queue",
    "new_scheduler": "second scheduler/control plane",
    "new_approval_system": "second approval system",
    "new_secret_store": "second secret store",
    "always_on_llm_health": "always-on LLM health loop",
    "mandatory_cloud_dependency": "mandatory cloud dependency",
    "direct_saas_core_coupling": "direct SaaS coupling inside core state logic",
    "broad_autonomous_installer": "broad autonomous install/upgrade path",
}
REVIEW_FLAGS = {
    "new_daemon": "new persistent daemon/service",
    "new_recurring_cost": "new recurring vendor cost",
    "new_privilege": "new OS/account privilege",
}
REQUIRED_REUSE = {
    "reuse_canonical_sqlite", "reuse_task_queue", "reuse_approval_engine",
    "reuse_health", "reuse_resource_governor", "feature_flagged",
    "rollback_defined", "evidence_defined",
}

class ArchitectureError(ValueError):
    pass

def validate_proposal(proposal: dict) -> list[str]:
    errors = []
    if not isinstance(proposal, dict):
        return ["proposal:not-object"]
    for key in ("skill_id", "candidate_id"):
        if not isinstance(proposal.get(key), str) or not proposal[key].strip():
            errors.append(f"proposal:missing-{key}")
    for key in REQUIRED_REUSE | set(FORBIDDEN_DUPLICATES) | set(REVIEW_FLAGS):
        if key not in proposal:
            errors.append(f"proposal:missing-{key}")
        elif not isinstance(proposal[key], bool):
            errors.append(f"proposal:invalid-{key}")
    unknown = set(proposal) - ({"skill_id", "candidate_id", "notes", "evidence"} | REQUIRED_REUSE | set(FORBIDDEN_DUPLICATES) | set(REVIEW_FLAGS))
    if unknown:
        errors.append("proposal:unknown:" + ",".join(sorted(unknown)))
    return errors

def audit(proposal: dict) -> dict:
    errors = validate_proposal(proposal)
    if errors:
        return {"status": "BLOCK", "errors": errors, "blockers": [], "review": []}
    sid = proposal["skill_id"].strip().lower()
    if skills.get(sid) is None:
        return {"status": "BLOCK", "errors": [f"proposal:unknown-skill:{sid}"], "blockers": [], "review": []}
    blockers = [label for key, label in FORBIDDEN_DUPLICATES.items() if proposal[key]]
    blockers += [f"must {key.replace('_',' ')}" for key in REQUIRED_REUSE if not proposal[key]]
    review = [label for key, label in REVIEW_FLAGS.items() if proposal[key]]
    status = "BLOCK" if blockers else ("NEEDS_REVIEW" if review else "PASS")
    return {"status": status, "errors": [], "blockers": sorted(blockers), "review": sorted(review)}

def audit_and_record(proposal: dict) -> dict:
    result = audit(proposal)
    if result["errors"]:
        return result
    evidence = {
        "architecture_guard": result,
        "reuse": {k: proposal[k] for k in sorted(REQUIRED_REUSE)},
        "notes": proposal.get("notes", ""),
        "evidence": proposal.get("evidence", {}),
    }
    verdict = "PASS" if result["status"] == "PASS" else "NEEDS_REVIEW"
    learnrepo.record_skill_review(
        proposal["skill_id"], proposal["candidate_id"], "ARCHITECTURE", evidence, verdict=verdict)
    return result

def load_proposal(path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_proposal(data)
    if errors:
        raise ArchitectureError("; ".join(errors))
    return data
