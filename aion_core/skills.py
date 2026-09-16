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
             test_command: str = "") -> str:
    skill_id = skill_id.strip().lower()
    if not _SKILL_ID.match(skill_id):
        raise SkillError(f"invalid skill_id {skill_id!r}")
    classes = _clean_csv(executor_classes.upper())
    invalid = set(classes.split(",")) - _EXECUTOR_CLASSES if classes else {""}
    if invalid:
        raise SkillError(f"invalid executor class(es): {sorted(invalid)}")
    now = util.now()
    values = (
        skill_id, security.redact(name), security.redact(description), version,
        security.redact(_clean_csv(capabilities)), classes, _clean_csv(platforms.lower()) or "any",
        int(bool(network_required)), int(bool(ai_required)), int(bool(offline_supported)),
        cost_class.strip().lower() or "none", int(bool(enabled)),
        security.redact(health_command), security.redact(test_command), now,
    )
    conn = db.connect()
    conn.execute(
        "INSERT INTO skills(skill_id,name,description,version,capabilities,executor_classes,platforms,"
        "network_required,ai_required,offline_supported,cost_class,enabled,health_command,test_command,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(skill_id) DO UPDATE SET "
        "name=excluded.name,description=excluded.description,version=excluded.version,"
        "capabilities=excluded.capabilities,executor_classes=excluded.executor_classes,"
        "platforms=excluded.platforms,network_required=excluded.network_required,"
        "ai_required=excluded.ai_required,offline_supported=excluded.offline_supported,"
        "cost_class=excluded.cost_class,enabled=excluded.enabled,health_command=excluded.health_command,"
        "test_command=excluded.test_command,updated_at=excluded.updated_at",
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
    if get(skill_id) is None:
        raise SkillError(f"unknown skill {skill_id}")
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
            "cost_class": row["cost_class"], "reason": reason,
        })
    return out
