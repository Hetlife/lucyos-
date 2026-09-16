"""LucyOS-native capability/skill registry.

Q001 deliberately extends the existing SQLite + worker capability model.  It is
not a plugin loader, installer, scheduler, approval system, or second source of
truth.  Q002 will define the richer on-disk manifest contract; this module only
provides durable identity/routing metadata and measured availability.
"""
from __future__ import annotations

import re

from . import db, security, util

_SKILL_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,79}$")
_EXECUTOR_CLASSES = {"DET", "A", "B", "C", "D"}

MANIFEST_SCHEMA_VERSION = 1
LIFECYCLE_STATES = {"DISCOVERED", "RESEARCHED", "LICENSE_OK", "SECURITY_REVIEWED", "SANDBOXED", "BENCHMARKED", "ARCHITECTURE_APPROVED", "OWNER_APPROVED", "INSTALLED_DISABLED", "TESTED", "ACTIVE", "DEGRADED", "QUARANTINED", "DEPRECATED", "REJECTED", "ROLLED_BACK"}
LIFECYCLE_TRANSITIONS = {
    "DISCOVERED": {"RESEARCHED", "REJECTED", "QUARANTINED"},
    "RESEARCHED": {"LICENSE_OK", "REJECTED", "QUARANTINED"},
    "LICENSE_OK": {"SECURITY_REVIEWED", "REJECTED", "QUARANTINED"},
    "SECURITY_REVIEWED": {"SANDBOXED", "REJECTED", "QUARANTINED"},
    "SANDBOXED": {"BENCHMARKED", "REJECTED", "QUARANTINED"},
    "BENCHMARKED": {"ARCHITECTURE_APPROVED", "REJECTED", "QUARANTINED"},
    "ARCHITECTURE_APPROVED": {"OWNER_APPROVED", "INSTALLED_DISABLED", "REJECTED", "QUARANTINED"},
    "OWNER_APPROVED": {"INSTALLED_DISABLED", "REJECTED", "QUARANTINED"},
    "INSTALLED_DISABLED": {"TESTED", "ROLLED_BACK", "QUARANTINED"},
    "TESTED": {"ACTIVE", "INSTALLED_DISABLED", "ROLLED_BACK", "QUARANTINED"},
    "ACTIVE": {"DEGRADED", "DEPRECATED", "QUARANTINED", "ROLLED_BACK"},
    "DEGRADED": {"ACTIVE", "QUARANTINED", "ROLLED_BACK", "DEPRECATED"},
    "QUARANTINED": {"RESEARCHED", "REJECTED", "ROLLED_BACK"},
    "DEPRECATED": {"ROLLED_BACK"},
    "REJECTED": set(),
    "ROLLED_BACK": {"RESEARCHED"},
}
MANIFEST_REQUIRED = {
    "schema_version", "skill_id", "name", "version", "capabilities",
    "executor_classes", "platforms", "requirements", "cost_class",
}
MANIFEST_OPTIONAL = {
    "description", "enabled", "health_command", "test_command", "actions",
    "permissions", "input_schema", "output_schema", "risk_class", "data_class",
    "fallback", "evidence", "timeout_seconds", "retry", "idempotency",
    "approval_rule", "rollback", "feature_flag", "lifecycle_state", "references",
    "implementation_notes", "priority", "cost_notes",
}

DEFAULT_SKILLS = [
    dict(skill_id="core.state", name="Canonical state", capabilities="sqlite,state,events,idempotency",
         executor_classes="DET", platforms="any", network_required=0, ai_required=0,
         offline_supported=1, cost_class="none", health_command="aion health"),
    dict(skill_id="core.tasks", name="Task queue", capabilities="queue,claim,retry,evidence",
         executor_classes="DET", platforms="any", network_required=0, ai_required=0,
         offline_supported=1, cost_class="none", health_command="aion health"),
    dict(skill_id="core.approvals", name="Owner approvals", capabilities="approve,deny,resume",
         executor_classes="DET,D", platforms="any", network_required=0, ai_required=0,
         offline_supported=1, cost_class="none", health_command="aion health"),
    dict(skill_id="core.security", name="Secret protection", capabilities="redact,scan,guard",
         executor_classes="DET", platforms="any", network_required=0, ai_required=0,
         offline_supported=1, cost_class="none", health_command="aion scan ."),
    dict(skill_id="core.health", name="Deterministic health", capabilities="health,integrity,watchdog",
         executor_classes="DET", platforms="any", network_required=0, ai_required=0,
         offline_supported=1, cost_class="none", health_command="aion health"),
    dict(skill_id="core.backup", name="Backup and restore", capabilities="backup,restore,verify",
         executor_classes="DET", platforms="any", network_required=0, ai_required=0,
         offline_supported=1, cost_class="none", health_command="aion health"),
    dict(skill_id="core.learnrepo", name="LearnRepo", capabilities="dependency_research,queue,health,quarantine",
         executor_classes="DET,C", platforms="any", network_required=0, ai_required=0,
         offline_supported=1, cost_class="none", health_command="aion learnrepo-status"),
    dict(skill_id="ai.local", name="Local model worker", capabilities="classify,extract,format,summarize",
         executor_classes="A", platforms="any", network_required=0, ai_required=1,
         offline_supported=1, cost_class="none", health_command="ollama list"),
    dict(skill_id="ai.cloud", name="Cloud model worker", capabilities="code,research,debug,reason",
         executor_classes="B,C", platforms="any", network_required=1, ai_required=1,
         offline_supported=0, cost_class="external", health_command=""),
]


class SkillError(Exception):
    pass


def _clean_csv(value: str) -> str:
    items = []
    for item in (value or "").split(","):
        item = item.strip()
        if item and item not in items:
            items.append(item)
    return ",".join(items)


def register(*, skill_id: str, name: str, description: str = "", version: str = "0.1.0",
             capabilities: str = "", executor_classes: str = "DET", platforms: str = "any",
             network_required: int = 0, ai_required: int = 0, offline_supported: int = 1,
             cost_class: str = "none", enabled: int = 1, health_command: str = "",
             test_command: str = "", lifecycle_state: str = "ACTIVE", feature_flag: str = "",
             source_manifest: str = "") -> str:
    skill_id = skill_id.strip().lower()
    if not _SKILL_ID.match(skill_id):
        raise SkillError(f"invalid skill_id {skill_id!r}")
    classes = _clean_csv(executor_classes.upper())
    invalid = set(classes.split(",")) - _EXECUTOR_CLASSES if classes else {""}
    if invalid:
        raise SkillError(f"invalid executor class(es): {sorted(invalid)}")
    lifecycle_state = lifecycle_state.strip().upper()
    if lifecycle_state not in LIFECYCLE_STATES:
        raise SkillError(f"invalid lifecycle state {lifecycle_state!r}")
    now = util.now()
    values = (
        skill_id, security.redact(name), security.redact(description), version,
        security.redact(_clean_csv(capabilities)), classes, _clean_csv(platforms.lower()) or "any",
        int(bool(network_required)), int(bool(ai_required)), int(bool(offline_supported)),
        cost_class.strip().lower() or "none", int(bool(enabled)),
        security.redact(health_command), security.redact(test_command), lifecycle_state,
        security.redact(feature_flag), security.redact(source_manifest), now,
    )
    conn = db.connect()
    conn.execute(
        "INSERT INTO skills(skill_id,name,description,version,capabilities,executor_classes,platforms,"
        "network_required,ai_required,offline_supported,cost_class,enabled,health_command,test_command,"
        "lifecycle_state,feature_flag,source_manifest,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(skill_id) DO UPDATE SET "
        "name=excluded.name,description=excluded.description,version=excluded.version,"
        "capabilities=excluded.capabilities,executor_classes=excluded.executor_classes,"
        "platforms=excluded.platforms,network_required=excluded.network_required,"
        "ai_required=excluded.ai_required,offline_supported=excluded.offline_supported,"
        "cost_class=excluded.cost_class,enabled=excluded.enabled,health_command=excluded.health_command,"
        "test_command=excluded.test_command,lifecycle_state=excluded.lifecycle_state,"
        "feature_flag=excluded.feature_flag,source_manifest=excluded.source_manifest,updated_at=excluded.updated_at",
        values,
    )
    conn.commit()
    return skill_id


def ensure_defaults() -> int:
    for spec in DEFAULT_SKILLS:
        # Defaults must not silently re-enable an owner-disabled skill.
        if get(spec["skill_id"]) is None:
            register(**spec)
    return len(DEFAULT_SKILLS)


def get(skill_id: str):
    return db.connect().execute("SELECT * FROM skills WHERE skill_id=?", (skill_id.lower(),)).fetchone()


def all_skills(*, enabled_only: bool = False) -> list:
    q = "SELECT * FROM skills"
    args = ()
    if enabled_only:
        q += " WHERE enabled=1"
    q += " ORDER BY skill_id"
    return db.connect().execute(q, args).fetchall()


def set_enabled(skill_id: str, enabled: bool) -> None:
    row = get(skill_id)
    if row is None:
        raise SkillError(f"unknown skill {skill_id}")
    if enabled and row["lifecycle_state"] != "ACTIVE":
        raise SkillError(f"cannot enable {skill_id}: lifecycle is {row['lifecycle_state']}, not ACTIVE")
    conn = db.connect()
    conn.execute("UPDATE skills SET enabled=?, updated_at=? WHERE skill_id=?",
                 (int(bool(enabled)), util.now(), skill_id.lower()))
    conn.commit()
    db.log_event("aion", "skill.enabled" if enabled else "skill.disabled", skill_id)


def validate_registry() -> list[str]:
    errors = []
    for row in all_skills():
        if not _SKILL_ID.match(row["skill_id"]):
            errors.append(f"{row['skill_id']}:invalid-id")
        classes = {x for x in row["executor_classes"].split(",") if x}
        if not classes or not classes <= _EXECUTOR_CLASSES:
            errors.append(f"{row['skill_id']}:invalid-executor")
    return errors


def _available(row, runtime: dict) -> tuple[bool, str]:
    if not row["enabled"]:
        return False, "disabled"
    classes = {x for x in row["executor_classes"].split(",") if x}
    if "DET" in classes:
        return True, "deterministic executor available"
    if "A" in classes and runtime.get("ollama"):
        return True, "local model available"
    if classes & {"B", "C"} and runtime.get("cloud_worker"):
        return True, "cloud worker configured"
    if "D" in classes:
        return True, "owner authority path exists"
    return False, "no compatible executor currently available"


def report(runtime: dict) -> list[dict]:
    """Return compact measured skill availability; no model or network calls."""
    ensure_defaults()
    out = []
    for row in all_skills():
        available, reason = _available(row, runtime)
        out.append({
            "skill_id": row["skill_id"], "name": row["name"], "version": row["version"],
            "enabled": bool(row["enabled"]), "available": available,
            "executor_classes": row["executor_classes"], "network_required": bool(row["network_required"]),
            "ai_required": bool(row["ai_required"]), "offline_supported": bool(row["offline_supported"]),
            "cost_class": row["cost_class"], "lifecycle_state": row["lifecycle_state"],
            "feature_flag": row["feature_flag"], "reason": reason,
        })
    return out


def validate_manifest(data: dict) -> list[str]:
    """Validate the Q002 manifest contract without third-party schema code.

    The JSON schema file is documentation/interoperability. This deterministic
    validator is the runtime gate so manifest checks remain local and free.
    """
    errors = []
    if not isinstance(data, dict):
        return ["manifest:not-object"]
    missing = sorted(MANIFEST_REQUIRED - set(data))
    if missing:
        errors.append("manifest:missing:" + ",".join(missing))
    unknown = sorted(set(data) - MANIFEST_REQUIRED - MANIFEST_OPTIONAL)
    if unknown:
        errors.append("manifest:unknown:" + ",".join(unknown))
    if data.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("manifest:unsupported-schema")
    sid = str(data.get("skill_id", "")).strip().lower()
    if not _SKILL_ID.match(sid):
        errors.append("manifest:invalid-skill-id")
    for key in ("name", "version", "cost_class"):
        if not isinstance(data.get(key), str) or not data.get(key, "").strip():
            errors.append(f"manifest:invalid-{key}")
    for key in ("capabilities", "executor_classes", "platforms"):
        value = data.get(key)
        if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() for x in value):
            errors.append(f"manifest:invalid-{key}")
    classes = {x.strip().upper() for x in data.get("executor_classes", []) if isinstance(x, str)}
    if classes and not classes <= _EXECUTOR_CLASSES:
        errors.append("manifest:invalid-executor-class")
    req = data.get("requirements")
    if not isinstance(req, dict):
        errors.append("manifest:invalid-requirements")
    else:
        allowed_req = {"network", "ai", "offline_supported"}
        missing_req = allowed_req - set(req)
        unknown_req = set(req) - allowed_req
        if missing_req:
            errors.append("manifest:missing-requirements:" + ",".join(sorted(missing_req)))
        if unknown_req:
            errors.append("manifest:unknown-requirements:" + ",".join(sorted(unknown_req)))
        for key in allowed_req & set(req):
            if not isinstance(req[key], bool):
                errors.append(f"manifest:invalid-requirement-{key}")
    for key in ("actions", "permissions", "fallback"):
        if key in data and (not isinstance(data[key], list) or not all(isinstance(x, str) for x in data[key])):
            errors.append(f"manifest:invalid-{key}")
    if "timeout_seconds" in data and (not isinstance(data["timeout_seconds"], int) or data["timeout_seconds"] <= 0):
        errors.append("manifest:invalid-timeout")
    if "enabled" in data and not isinstance(data["enabled"], bool):
        errors.append("manifest:invalid-enabled")
    if "lifecycle_state" in data and data["lifecycle_state"] not in LIFECYCLE_STATES:
        errors.append("manifest:invalid-lifecycle-state")
    if "references" in data and (not isinstance(data["references"], list) or not all(isinstance(x, str) for x in data["references"])):
        errors.append("manifest:invalid-references")
    return errors


def register_manifest(data: dict) -> str:
    """Validate and map one manifest into the existing canonical registry.

    Q002 intentionally stores only registry/routing fields in SQLite. Richer
    policy fields remain in the manifest file until their dedicated queue items
    define runtime semantics. Nothing in a manifest is executed here.
    """
    errors = validate_manifest(data)
    if errors:
        raise SkillError("; ".join(errors))
    req = data["requirements"]
    return register(
        skill_id=data["skill_id"], name=data["name"], description=data.get("description", ""),
        version=data["version"], capabilities=",".join(data["capabilities"]),
        executor_classes=",".join(data["executor_classes"]), platforms=",".join(data["platforms"]),
        network_required=req["network"], ai_required=req["ai"],
        offline_supported=req["offline_supported"], cost_class=data["cost_class"],
        enabled=data.get("enabled", True), health_command=data.get("health_command", ""),
        test_command=data.get("test_command", ""), lifecycle_state=data.get("lifecycle_state", "DISCOVERED"),
        feature_flag=data.get("feature_flag", ""),
    )


def load_manifest(path) -> dict:
    """Read JSON data only; no imports, plugins, shell, or install hooks."""
    import json
    from pathlib import Path
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    errors = validate_manifest(data)
    if errors:
        raise SkillError("; ".join(errors))
    return data


def set_lifecycle(skill_id: str, state: str, *, force: bool = False) -> None:
    state = state.strip().upper()
    if state not in LIFECYCLE_STATES:
        raise SkillError(f"invalid lifecycle state {state!r}")
    row = get(skill_id)
    if row is None:
        raise SkillError(f"unknown skill {skill_id}")
    current = row["lifecycle_state"]
    if state == current:
        return
    if not force and state not in LIFECYCLE_TRANSITIONS.get(current, set()):
        raise SkillError(f"invalid lifecycle transition {current}->{state}")
    # Catalog candidates must carry LearnRepo evidence for every gated stage.
    # Native/core rows without a source manifest remain compatible with existing tests/workflows.
    if not force and row["source_manifest"] and state in {
            "RESEARCHED", "LICENSE_OK", "SECURITY_REVIEWED", "SANDBOXED", "BENCHMARKED",
            "ARCHITECTURE_APPROVED", "OWNER_APPROVED", "INSTALLED_DISABLED", "TESTED"}:
        from . import learnrepo
        ok, reason = learnrepo.review_gate(skill_id, state)
        if not ok:
            raise SkillError(f"cannot transition {skill_id} to {state}: {reason}")
    enabled = 0 if state != "ACTIVE" else row["enabled"]
    conn = db.connect()
    conn.execute("UPDATE skills SET lifecycle_state=?, enabled=?, updated_at=? WHERE skill_id=?",
                 (state, enabled, util.now(), skill_id.lower()))
    conn.commit()
    db.log_event("aion", "skill.lifecycle", skill_id, f"{current}->{state}")


def activate(skill_id: str) -> None:
    row = get(skill_id)
    if row is None:
        raise SkillError(f"unknown skill {skill_id}")
    if row["lifecycle_state"] != "TESTED":
        raise SkillError(f"cannot activate {skill_id}: lifecycle is {row['lifecycle_state']}, expected TESTED")
    set_lifecycle(skill_id, "ACTIVE")
    set_enabled(skill_id, True)


def catalog_root():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent / "skills" / "catalog"


def catalog_manifests() -> list:
    root = catalog_root()
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.manifest.json") if p.is_file())


def validate_catalog() -> list[str]:
    errors = []
    seen = set()
    for path in catalog_manifests():
        try:
            data = load_manifest(path)
        except Exception as exc:
            errors.append(f"{path.relative_to(catalog_root())}:{exc}")
            continue
        sid = data["skill_id"]
        if sid in seen:
            errors.append(f"{sid}:duplicate")
        seen.add(sid)
        if data.get("enabled", False):
            errors.append(f"{sid}:catalog-entry-must-start-disabled")
        if data.get("lifecycle_state", "DISCOVERED") != "DISCOVERED":
            errors.append(f"{sid}:catalog-entry-must-start-discovered")
    return errors


def sync_catalog() -> dict:
    """Learn the on-disk candidate catalog into canonical SQLite, disabled.

    Existing rows are never overwritten. This is catalog ingestion only: it
    installs no dependency, imports no plugin and activates no capability.
    """
    errors = validate_catalog()
    if errors:
        raise SkillError("catalog invalid: " + "; ".join(errors[:8]))
    added = skipped = 0
    root = catalog_root()
    for path in catalog_manifests():
        data = load_manifest(path)
        if get(data["skill_id"]) is not None:
            skipped += 1
            continue
        data = dict(data)
        data["enabled"] = False
        data["lifecycle_state"] = "DISCOVERED"
        sid = register_manifest(data)
        conn = db.connect()
        conn.execute("UPDATE skills SET source_manifest=?, feature_flag=? WHERE skill_id=?",
                     (str(path.relative_to(root.parent.parent)), data.get("feature_flag", ""), sid))
        conn.commit()
        added += 1
    if added:
        db.log_event("aion", "skill.catalog.sync", "catalog", f"{added} added, {skipped} existing")
    return {"catalog": len(catalog_manifests()), "added": added, "skipped": skipped, "errors": []}
