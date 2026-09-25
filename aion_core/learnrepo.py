"""LucyOS-native LearnRepo maintenance queue and deterministic health runner.

Design goals:
- existing SQLite remains canonical;
- existing tasks/errors/events/approvals/governor stay the control plane;
- routine scheduled checks make zero model/API calls;
- only evidence-backed failures that need reasoning/code changes create
  API_WORK_REQUIRED tasks;
- single-node leases prevent duplicate execution and recover after expiry.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import config, db, errors, governor, security, tasks, util

SCHEDULE_CLASSES = {"ON_CHANGE", "HOURLY", "NIGHTLY", "DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "MANUAL"}
RUN_STATES = {"SCHEDULED", "STARTED", "SUCCESS", "FAIL", "LATE", "MISSED", "DEGRADED", "QUARANTINED"}
SAFE_REPAIRS = {"release_stale_lease", "rebuild_derived_summary", "rebuild_org_summary"}
REFERENCE_REPOS = {
    "apscheduler": "https://github.com/agronholm/apscheduler",
    "healthchecks": "https://github.com/healthchecks/healthchecks",
}
REFERENCE_DOCS = {
    "apscheduler": "https://apscheduler.readthedocs.io/en/master/userguide.html",
    "healthchecks": "https://healthchecks.io/docs/",
}
DEFAULT_GRACE_SECONDS = 20 * 60
DEFAULT_LEASE_SECONDS = 45 * 60

# Org-wide health generalization (TASK-89B0270A, stage M1).
# The LearnRepo pilot stays the default component; org checks reuse the
# existing deterministic checks in aion_core/health.py — no second control
# plane, no new daemon, zero model calls on the routine path.  Org seeding
# is gated behind a meta feature flag so nothing changes until enabled, and
# rollback is "aion orghealth off" (flag + org schedules disabled).
DEFAULT_COMPONENT = "LearnRepo"
ORG_COMPONENT = "LucyOS"
ORGHEALTH_FLAG = "ORGHEALTH_ENABLED"


def _utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _iso(value: datetime | None = None) -> str:
    return _utc(value).isoformat()


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def learnrepo_root() -> Path:
    return repo_root() / "learnrepo"


def org_enabled() -> bool:
    """Org-wide health runs only when the owner-visible flag is on."""
    return (db.get_meta(ORGHEALTH_FLAG) or "").strip().lower() in {"1", "true", "yes", "on"}


def set_org_enabled(enabled: bool, now: datetime | None = None) -> dict:
    """Turn the org-wide health schedules on or off (rollback path)."""
    now = _utc(now)
    db.set_meta(ORGHEALTH_FLAG, "1" if enabled else "0")
    conn = db.connect()
    if enabled:
        ensure_defaults(now)
        conn.execute(
            "UPDATE learnrepo_schedules SET enabled=1 WHERE component=?", (ORG_COMPONENT,))
        detail = "org-wide health schedules enabled"
    else:
        cur = conn.execute(
            "UPDATE learnrepo_schedules SET enabled=0, lease_owner=NULL, lease_until=NULL "
            "WHERE component=?", (ORG_COMPONENT,))
        detail = f"{cur.rowcount} org-wide health schedule(s) disabled"
    conn.commit()
    db.log_event("learnrepo", "orghealth.flag", ORGHEALTH_FLAG, detail)
    return {"ok": True, "enabled": bool(enabled), "detail": detail}


def ensure_defaults(now: datetime | None = None) -> None:
    """Seed one native maintenance task/schedule and core boundary contracts.

    Idempotent and intentionally small. No external scheduler dependency.
    """
    now = _utc(now)
    conn = db.connect()
    task_defs = [
        ("learnrepo.health.nightly", "Deterministic LearnRepo internal health", 3, 0, 0, "release_stale_lease"),
        ("learnrepo.health.weekly_external", "Read-only official-reference drift health", 4, 1, 0, ""),
        ("learnrepo.health.on_change", "Deterministic revalidation after committed LucyOS changes", 3, 0, 0, ""),
    ]
    for task_def in task_defs:
        conn.execute(
            "INSERT OR IGNORE INTO learnrepo_tasks(task_type, description, health_level, requires_network, requires_ai, safe_repair) "
            "VALUES(?,?,?,?,?,?)", task_def)
    schedule_defs = [
        ("LR-SCHED-NIGHTLY", "learnrepo.health.nightly", "NIGHTLY", _iso(now), DEFAULT_GRACE_SECONDS, 1, 1),
        ("LR-SCHED-WEEKLY", "learnrepo.health.weekly_external", "WEEKLY", _iso(now + timedelta(days=7)), 3600, 1, 0),
        ("LR-SCHED-ONCHANGE", "learnrepo.health.on_change", "ON_CHANGE", None, DEFAULT_GRACE_SECONDS, 1, 1),
    ]
    for sched in schedule_defs:
        conn.execute(
            "INSERT OR IGNORE INTO learnrepo_schedules(schedule_id, task_type, schedule_class, next_run_at, grace_seconds, enabled, change_sensitive) "
            "VALUES(?,?,?,?,?,?,?)", sched)
    # Additive compatibility for the first pilot schema written before the
    # task split; preserve schedule state while moving it to the named task.
    conn.execute(
        "UPDATE learnrepo_schedules SET task_type='learnrepo.health.nightly' "
        "WHERE schedule_id='LR-SCHED-NIGHTLY' AND task_type='learnrepo.health'"
    )
    contracts = [
        ("LR-CONTRACT-MODULE", "LearnRepo", "aion_core/learnrepo.py", "1", "AION CLI", "importable module",
         "python3 -m py_compile aion_core/learnrepo.py", "HIGH"),
        ("LR-CONTRACT-REFERENCES", "LearnRepo", "learnrepo/references", "1", "LearnRepo health",
         "two approved reference notes", '''python3 -c "assert len(list(__import__('pathlib').Path('learnrepo/references').glob('*.md'))) == 2"''', "MEDIUM"),
    ]
    for row in contracts:
        conn.execute(
            "INSERT OR IGNORE INTO learnrepo_contracts(contract_id, producer, input_name, schema_version, consumer, expected_output, validation_command, severity_if_broken) "
            "VALUES(?,?,?,?,?,?,?,?)", row,
        )
    if org_enabled():
        _ensure_org_defaults(now, conn)
    conn.commit()


def _ensure_org_defaults(now: datetime, conn) -> None:
    """Seed org-wide health task/schedule/contract rows (idempotent).

    Only called when the ORGHEALTH_ENABLED flag is on.  Wraps the existing
    deterministic checks from aion_core/health.py as a LucyOS component;
    everything reuses the canonical SQLite tables the pilot already owns.
    """
    task_defs = [
        ("lucyos.health.nightly", "Deterministic LucyOS org-wide health", 3, 0, 0,
         "release_stale_lease", ORG_COMPONENT),
        ("lucyos.health.on_change", "Deterministic org revalidation after committed changes",
         3, 0, 0, "", ORG_COMPONENT),
    ]
    for task_def in task_defs:
        conn.execute(
            "INSERT OR IGNORE INTO learnrepo_tasks(task_type, description, health_level, requires_network, requires_ai, safe_repair, component) "
            "VALUES(?,?,?,?,?,?,?)", task_def)
    schedule_defs = [
        ("LH-SCHED-NIGHTLY", "lucyos.health.nightly", "NIGHTLY", _iso(now), DEFAULT_GRACE_SECONDS, 1, 1, ORG_COMPONENT),
        ("LH-SCHED-ONCHANGE", "lucyos.health.on_change", "ON_CHANGE", None, DEFAULT_GRACE_SECONDS, 1, 1, ORG_COMPONENT),
    ]
    for sched in schedule_defs:
        conn.execute(
            "INSERT OR IGNORE INTO learnrepo_schedules(schedule_id, task_type, schedule_class, next_run_at, grace_seconds, enabled, change_sensitive, component) "
            "VALUES(?,?,?,?,?,?,?,?)", sched)
    # Deterministic contract checks for the org component.  Each one is a
    # single-statement validator the pilot harness already knows how to run
    # (no shell metacharacters); no scheduler, no daemon, no network beyond
    # loopback probes.
    home_expr = "__import__('os').environ.get('AION_HOME', __import__('os').path.expanduser('~/openclaw/shared_brain'))"
    contracts = [
        ("LH-CONTRACT-DB", ORG_COMPONENT, "canonical sqlite", "1", "AION CLI",
         "integrity=ok",
         f"python3 -c \"assert __import__('sqlite3').connect({home_expr} + '/state/aion.sqlite3').execute('PRAGMA integrity_check').fetchone()[0] == 'ok'\"",
         "HIGH", ORG_COMPONENT),
        ("LH-CONTRACT-BACKUP", ORG_COMPONENT, "shared brain backups", "1", "AION CLI",
         "at least one aion-backup archive present",
         f"python3 -c \"assert any(__import__('pathlib').Path({home_expr}, 'BACKUPS').glob('aion-backup-*.tar.gz'))\"",
         "MEDIUM", ORG_COMPONENT),
        ("LH-CONTRACT-SECRETS", ORG_COMPONENT, "secret store", "1", "AION CLI",
         "secrets file present with mode 0600",
         f"python3 -c \"assert __import__('stat').S_IMODE(__import__('os').stat(__import__('os').environ.get('AION_SECRETS', __import__('os').path.join({home_expr}, 'private_state', 'secrets.env'))).st_mode) == 0o600\"",
         "HIGH", ORG_COMPONENT),
        ("LH-CONTRACT-MODULE", ORG_COMPONENT, "aion_core/health.py", "1", "AION CLI",
         "importable module", "python3 -m py_compile aion_core/health.py", "HIGH", ORG_COMPONENT),
    ]
    for row in contracts:
        conn.execute(
            "INSERT OR IGNORE INTO learnrepo_contracts(contract_id, producer, input_name, schema_version, consumer, expected_output, validation_command, severity_if_broken, component) "
            "VALUES(?,?,?,?,?,?,?,?,?)", row)
    conn.commit()


def next_run(schedule_class: str, after: datetime) -> datetime | None:
    """Calculate the next eligibility boundary in UTC.

    NIGHTLY is 03:15 UTC. DAILY preserves the current UTC wall-clock. Monthly
    and quarterly use calendar boundaries without third-party dependencies.
    """
    cls = schedule_class.upper()
    if cls not in SCHEDULE_CLASSES:
        raise ValueError(f"unknown schedule class {schedule_class}")
    after = _utc(after)
    if cls in {"MANUAL", "ON_CHANGE"}:
        return None
    if cls == "HOURLY":
        return after + timedelta(hours=1)
    if cls == "NIGHTLY":
        candidate = after.replace(hour=3, minute=15, second=0)
        return candidate if candidate > after else candidate + timedelta(days=1)
    if cls == "DAILY":
        return after + timedelta(days=1)
    if cls == "WEEKLY":
        return after + timedelta(days=7)
    if cls == "MONTHLY":
        year, month = after.year, after.month + 1
        if month == 13:
            year, month = year + 1, 1
        return after.replace(year=year, month=month, day=1)
    # QUARTERLY: first day of the next quarter, preserving time-of-day.
    month = ((after.month - 1) // 3 + 1) * 3 + 1
    year = after.year
    if month > 12:
        year, month = year + 1, month - 12
    return after.replace(year=year, month=month, day=1)


def due_schedules(now: datetime | None = None) -> list:
    ensure_defaults(now)
    now_s = _iso(now)
    return db.connect().execute(
        "SELECT * FROM learnrepo_schedules WHERE enabled=1 AND next_run_at IS NOT NULL AND next_run_at <= ? "
        "ORDER BY next_run_at, schedule_id", (now_s,)
    ).fetchall()


def acquire(schedule_id: str, worker: str, now: datetime | None = None,
            lease_seconds: int = DEFAULT_LEASE_SECONDS) -> str | None:
    """Atomically acquire one due schedule and create a concrete run."""
    ensure_defaults(now)
    now = _utc(now)
    conn = db.connect()
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute("SELECT * FROM learnrepo_schedules WHERE schedule_id=?", (schedule_id,)).fetchone()
    if row is None or not row["enabled"]:
        conn.rollback(); return None
    expected = _parse(row["next_run_at"])
    lease_until = _parse(row["lease_until"])
    if expected is None or expected > now:
        conn.rollback(); return None
    if row["lease_owner"] and lease_until and lease_until > now and row["lease_owner"] != worker:
        conn.rollback(); return None
    run_id = util.new_id("LRRUN")
    until = _iso(now + timedelta(seconds=lease_seconds))
    conn.execute(
        "UPDATE learnrepo_schedules SET lease_owner=?, lease_until=? WHERE schedule_id=?",
        (worker, until, schedule_id),
    )
    conn.execute(
        "INSERT INTO learnrepo_runs(run_id, schedule_id, task_type, expected_at, status, grace_seconds, lease_owner, lease_until) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (run_id, schedule_id, row["task_type"], row["next_run_at"], "SCHEDULED", row["grace_seconds"], worker, until),
    )
    conn.commit()
    db.log_event("learnrepo", "learnrepo.run.scheduled", run_id, schedule_id)
    return run_id


def recover_stale_leases(now: datetime | None = None) -> list[str]:
    now_s = _iso(now)
    conn = db.connect()
    rows = conn.execute(
        "SELECT run_id, schedule_id FROM learnrepo_runs WHERE status IN ('SCHEDULED','STARTED') "
        "AND lease_until IS NOT NULL AND lease_until < ?", (now_s,)
    ).fetchall()
    recovered = []
    for row in rows:
        conn.execute("UPDATE learnrepo_runs SET status='FAIL', completed_at=?, error=? WHERE run_id=?",
                     (now_s, "worker lease expired; run abandoned", row["run_id"]))
        conn.execute("UPDATE learnrepo_schedules SET lease_owner=NULL, lease_until=NULL WHERE schedule_id=?",
                     (row["schedule_id"],))
        recovered.append(row["run_id"])
    conn.commit()
    if recovered:
        db.log_event("learnrepo", "learnrepo.lease.recovered", ",".join(recovered[:5]), str(len(recovered)))
    return recovered


def classify_timing(run_id: str, now: datetime | None = None) -> str:
    row = db.connect().execute("SELECT * FROM learnrepo_runs WHERE run_id=?", (run_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown run {run_id}")
    now = _utc(now)
    expected = _parse(row["expected_at"]) or now
    grace = timedelta(seconds=row["grace_seconds"])
    started = _parse(row["started_at"])
    completed = _parse(row["completed_at"])
    if completed:
        return row["status"]
    if started:
        return "FAIL" if now > started + grace else "STARTED"
    if now > expected + grace:
        return "MISSED"
    if now > expected:
        return "LATE"
    return "SCHEDULED"


def _run_command(command: str, timeout: int = 20) -> tuple[bool, str]:
    """Run a contract validator without a shell; reject shell metacharacters."""
    if any(token in command for token in (";", "&&", "||", "|", ">", "<", "`", "$(`")):
        return False, "forbidden validator syntax"
    try:
        p = subprocess.run(shlex.split(command), cwd=repo_root(), capture_output=True, text=True, timeout=timeout)
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        return p.returncode == 0, security.redact(out)[-2000:]
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return False, security.redact(str(exc))


def _git_head() -> str:
    try:
        p = subprocess.run(["git", "-C", str(repo_root()), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def trigger_on_change_if_needed(now: datetime | None = None) -> bool:
    """Wake the ON_CHANGE schedule when the committed LucyOS revision changes."""
    now = _utc(now)
    head = _git_head()
    previous = db.get_meta("learnrepo.last_git_head", "") or ""
    if not head:
        return False
    if not previous:
        db.set_meta("learnrepo.last_git_head", head)
        return False
    if head == previous:
        return False
    conn = db.connect()
    conn.execute(
        "UPDATE learnrepo_schedules SET next_run_at=? WHERE schedule_class='ON_CHANGE' AND enabled=1",
        (_iso(now),),
    )
    conn.commit()
    db.set_meta("learnrepo.last_git_head", head)
    db.log_event("learnrepo", "learnrepo.change.detected", head[:12], previous[:12])
    return True


def cleanup_history(now: datetime | None = None, keep_days: int = 90) -> int:
    cutoff = _iso(_utc(now) - timedelta(days=keep_days))
    conn = db.connect()
    cur = conn.execute(
        "DELETE FROM learnrepo_runs WHERE completed_at IS NOT NULL AND completed_at < ?", (cutoff,)
    )
    conn.commit()
    return cur.rowcount


def change_score() -> int:
    """Small deterministic score: local change + prior LearnRepo failure + age."""
    score = 0
    try:
        p = subprocess.run(["git", "-C", str(repo_root()), "status", "--porcelain", "--",
                            "learnrepo", "aion_core/learnrepo.py"], capture_output=True, text=True, timeout=5)
        score += min(5, len([x for x in p.stdout.splitlines() if x.strip()])) * 2
    except (OSError, subprocess.TimeoutExpired):
        score += 1
    row = db.connect().execute(
        "SELECT status, completed_at FROM learnrepo_runs ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    if row and row["status"] in {"FAIL", "MISSED", "QUARANTINED"}:
        score += 4
    if row and row["completed_at"]:
        age = _utc() - (_parse(row["completed_at"]) or _utc())
        if age.days >= 7:
            score += 2
    return score


def _level0() -> list[dict]:
    expected = [learnrepo_root(), learnrepo_root() / "references", learnrepo_root() / "contracts.json"]
    return [{"level": 0, "name": f"exists:{p.relative_to(repo_root())}", "ok": p.exists(),
             "detail": "present" if p.exists() else "missing"} for p in expected]


def _level1() -> list[dict]:
    checks = []
    try:
        data = json.loads((learnrepo_root() / "contracts.json").read_text(encoding="utf-8"))
        checks.append({"level": 1, "name": "contracts-json", "ok": isinstance(data, dict) and data.get("schema_version") == 1,
                       "detail": "schema_version=1" if isinstance(data, dict) else "not an object"})
    except Exception as exc:
        checks.append({"level": 1, "name": "contracts-json", "ok": False, "detail": str(exc)})
    bad = db.connect().execute(
        "SELECT schedule_id FROM learnrepo_schedules WHERE schedule_class NOT IN ('ON_CHANGE','HOURLY','NIGHTLY','DAILY','WEEKLY','MONTHLY','QUARTERLY','MANUAL')"
    ).fetchall()
    checks.append({"level": 1, "name": "schedule-classes", "ok": not bad,
                   "detail": "valid" if not bad else f"invalid: {[r['schedule_id'] for r in bad]}"})
    return checks


def _level2() -> list[dict]:
    row = db.connect().execute("PRAGMA integrity_check").fetchone()
    return [{"level": 2, "name": "sqlite-integrity", "ok": row[0] == "ok", "detail": row[0]},
            {"level": 2, "name": "reference-count", "ok": len(REFERENCE_REPOS) == 2,
             "detail": "only APScheduler and Healthchecks.io approved"}]


def _level3(component: str = DEFAULT_COMPONENT) -> list[dict]:
    rows = db.connect().execute(
        "SELECT * FROM learnrepo_contracts WHERE component=? ORDER BY contract_id", (component,)
    ).fetchall()
    out = []
    for row in rows:
        ok, detail = _run_command(row["validation_command"])
        out.append({"level": 3, "name": row["contract_id"], "ok": ok,
                    "detail": detail or row["expected_output"], "severity": row["severity_if_broken"]})
    return out


def _org_checks() -> list[dict]:
    """Org-wide checks wrap the existing deterministic checks in health.py.

    Optional components (openclaw gateway, ollama) degrade instead of failing,
    exactly as health.py classifies them — a missing optional service must not
    create API work.  Required components (database, disk, backup, secret
    store) escalate through the pilot's deduplicated evidence path.
    """
    from . import health
    out = []
    for level, fn, optional in (
        (1, health.check_disk, False),
        (2, health.check_db, False),
        (1, health.check_openclaw, True),
        (1, health.check_ollama, True),
        (2, health.check_backup, False),
        (2, health.check_secrets, False),
    ):
        try:
            result = fn()
        except Exception as exc:  # defensive: a broken probe is a failed check
            result = {"name": getattr(fn, "__name__", "unknown"), "ok": False,
                      "detail": security.redact(str(exc))[:300]}
        name = f"org:{result.get('name', fn.__name__)}"
        ok = bool(result.get("ok"))
        detail = str(result.get("detail", ""))[:300]
        if ok:
            out.append({"level": level, "name": name, "ok": True, "detail": detail})
        elif optional:
            out.append({"level": level, "name": name, "ok": False, "degraded": True,
                        "detail": detail})
        else:
            out.append({"level": level, "name": name, "ok": False, "detail": detail,
                        "severity": "HIGH" if level >= 2 else "MEDIUM"})
    return out


def _component_checks(component: str, max_level: int) -> list[dict]:
    if component == ORG_COMPONENT:
        return _org_checks() + (_level3(component) if max_level >= 3 else [])
    checks = _level0()
    if max_level >= 1:
        checks += _level1()
    if max_level >= 2:
        checks += _level2()
    if max_level >= 3:
        checks += _level3(component)
    return checks


def _default_fetch(url: str, timeout: int = 6) -> dict:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "LucyOS-LearnRepo-Health/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return {"status": resp.status, "etag": resp.headers.get("ETag", ""),
                "last_modified": resp.headers.get("Last-Modified", "")}


def level4_external(fetcher: Callable[[str], dict] | None = None) -> list[dict]:
    """Read-only upstream reachability/drift probe. Network failure is degraded,
    not reasoning failure, and therefore does not create API work by itself.
    """
    fetcher = fetcher or _default_fetch
    out = []
    for name, url in REFERENCE_DOCS.items():
        try:
            meta = fetcher(url)
            ok = 200 <= int(meta.get("status", 0)) < 400
            out.append({"level": 4, "name": f"upstream:{name}", "ok": ok, "degraded": not ok,
                        "detail": f"HTTP {meta.get('status')} etag={meta.get('etag','')[:80]}"})
        except Exception as exc:
            out.append({"level": 4, "name": f"upstream:{name}", "ok": False, "degraded": True,
                        "detail": f"offline/unreachable: {security.redact(str(exc))[:300]}"})
    return out


def _needs_reasoning(check: dict) -> bool:
    # Network-only Level 4 failures are retriable/degraded, not AI work.
    if check.get("level") == 4 and check.get("degraded"):
        return False
    return not check.get("ok", False)


def _fingerprint(check: dict, component: str = DEFAULT_COMPONENT) -> str:
    # Keep the historical "learnrepo" prefix for the pilot component so old
    # escalations deduplicate exactly as before; new components namespace
    # their own fingerprints.
    prefix = "learnrepo" if component == DEFAULT_COMPONENT else component.lower()
    raw = f"{prefix}|{check.get('level')}|{check.get('name')}|{check.get('detail','')}"
    return hashlib.sha256(raw.encode()).hexdigest()


def escalate(run_id: str, check: dict, *, component: str = DEFAULT_COMPONENT,
             owner_required: bool = False) -> str:
    """Create or update one deduplicated evidence packet + existing AION task."""
    fingerprint = _fingerprint(check, component)
    conn = db.connect()
    existing = conn.execute("SELECT * FROM learnrepo_escalations WHERE fingerprint=?", (fingerprint,)).fetchone()
    now = util.now()
    if existing:
        conn.execute("UPDATE learnrepo_escalations SET last_seen=?, occurrence_count=occurrence_count+1 WHERE fingerprint=?",
                     (now, fingerprint))
        conn.commit()
        return existing["escalation_id"]
    escalation_id = util.new_id("LRESC")
    evidence = {
        "escalation_id": escalation_id, "source": component, "run_id": run_id,
        "severity": check.get("severity", "MEDIUM"), "health_level": check.get("level"),
        "trigger": check.get("name"), "failed_check": check.get("name"),
        "expected": "deterministic check passes", "actual": check.get("detail", ""),
        "repro_command": next((r["validation_command"] for r in conn.execute(
            "SELECT * FROM learnrepo_contracts WHERE contract_id=?", (check.get("name"),)).fetchall()),
            f"aion learnrepo-run --mode nightly  # component {component}"),
        "affected_files": (["learnrepo/", "aion_core/learnrepo.py"] if component == DEFAULT_COMPONENT
                           else ["aion_core/learnrepo.py", "aion_core/health.py"]),
        "inputs": "canonical SQLite + component checks", "outputs": "health run + evidence packet",
        "first_seen": now, "last_seen": now, "occurrence_count": 1,
        "local_diagnosis": check.get("detail", ""), "safe_repairs_attempted": [],
        "evidence": check, "security_impact": "unknown; no automatic weakening permitted",
        "recommended_model_class": "C", "estimated_scope": f"bounded {component} repair",
        "owner_approval_required": owner_required, "resume_point": "reproduce check, patch narrowly, rerun deterministic validation",
    }
    task_id = tasks.create(
        f"API_WORK_REQUIRED {component}: {check.get('name')}", project="LucyOS",
        description=json.dumps(evidence, sort_keys=True), status="READY", priority=1,
        impact=4, probability=1, unlocks=2, info_gain=2, cost=1, risk=2, time_est=2,
        human_dependence=1 if owner_required else 0.2, model_class="C",
        kind="learnrepo_api_work_required",
        success_criteria="deterministic failing check passes and no security/governance regression",
        validation_method="rerun the evidence repro command and component tests",
        output_location="learnrepo/evidence", next_action="read compact evidence packet; do not reread whole LucyOS",
        evidence=fingerprint,
    )
    conn.execute(
        "INSERT INTO learnrepo_escalations(fingerprint, escalation_id, source, run_id, severity, health_level, trigger, evidence_json, first_seen, last_seen, occurrence_count, owner_approval_required, task_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (fingerprint, escalation_id, component, run_id, evidence["severity"], evidence["health_level"],
         evidence["trigger"], json.dumps(evidence, sort_keys=True), now, now, 1, int(owner_required), task_id),
    )
    conn.commit()
    errors.record(component, f"{check.get('name')} failed", check.get("detail", ""), task_id)
    governor.enforce(announce=False)
    db.log_event("learnrepo", "API_WORK_REQUIRED", escalation_id, task_id)
    return escalation_id


def safe_repair(action: str, now: datetime | None = None) -> dict:
    if action not in SAFE_REPAIRS:
        return {"ok": False, "action": action, "detail": "repair not allowlisted"}
    if action == "release_stale_lease":
        released = recover_stale_leases(now)
        return {"ok": True, "action": action, "detail": f"released {len(released)} stale run(s)"}
    if action == "rebuild_org_summary":
        conn = db.connect()
        row = conn.execute(
            "SELECT result_json FROM learnrepo_runs WHERE task_type IN "
            "(SELECT task_type FROM learnrepo_tasks WHERE component=?) "
            "ORDER BY completed_at DESC LIMIT 1", (ORG_COMPONENT,)).fetchone()
        summary = json.loads(row["result_json"]) if row and row["result_json"] else {}
        util.write_json(config.home() / "state" / "LUCYOS_HEALTH.json", summary)
        return {"ok": True, "action": action, "detail": "rebuilt org summary"}
    summary = latest_summary()
    util.write_json(config.home() / "state" / "LEARNREPO_HEALTH.json", summary)
    return {"ok": True, "action": action, "detail": "rebuilt derived summary"}


def _usage_count() -> int:
    return db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]


def execute_run(run_id: str, *, include_external: bool = False, now: datetime | None = None,
                external_fetcher: Callable[[str], dict] | None = None) -> dict:
    now = _utc(now)
    conn = db.connect()
    row = conn.execute("SELECT * FROM learnrepo_runs WHERE run_id=?", (run_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown run {run_id}")
    start = now
    conn.execute("UPDATE learnrepo_runs SET status='STARTED', started_at=? WHERE run_id=?", (_iso(start), run_id))
    conn.commit()
    before_ai = _usage_count()
    task_def = conn.execute("SELECT * FROM learnrepo_tasks WHERE task_type=?", (row["task_type"],)).fetchone()
    max_level = int(task_def["health_level"]) if task_def else 3
    component = DEFAULT_COMPONENT
    if task_def is not None and "component" in task_def.keys() and (task_def["component"] or "").strip():
        component = task_def["component"].strip()
    checks = _component_checks(component, max_level)
    if max_level >= 4 and (include_external or (task_def and task_def["requires_network"])):
        checks += level4_external(external_fetcher)
    escalations = []
    degraded = False
    for check in checks:
        if check.get("ok"):
            continue
        if check.get("degraded"):
            degraded = True
            continue
        if _needs_reasoning(check):
            escalations.append(escalate(run_id, check, component=component))
    finish = _utc()
    after_ai = _usage_count()
    ai_calls = after_ai - before_ai
    status = "FAIL" if escalations else ("DEGRADED" if degraded else "SUCCESS")
    duration_ms = max(0, int((finish - start).total_seconds() * 1000))
    summary = {
        "run_id": run_id, "status": status, "component": component, "checks": checks,
        "success": sum(1 for c in checks if c.get("ok")),
        "failed": sum(1 for c in checks if not c.get("ok") and not c.get("degraded")),
        "degraded": sum(1 for c in checks if c.get("degraded")),
        "local_repairs": 0, "api_escalations": len(escalations), "owner_escalations": 0,
        "network_requests": len(REFERENCE_DOCS) if include_external else 0,
        "ai_calls": ai_calls, "change_score": change_score(), "runtime_ms": duration_ms,
        "escalations": escalations,
    }
    conn.execute(
        "UPDATE learnrepo_runs SET status=?, completed_at=?, duration_ms=?, result_json=?, error=?, lease_until=NULL WHERE run_id=?",
        (status, _iso(finish), duration_ms, json.dumps(summary, sort_keys=True),
         "" if not escalations else f"{len(escalations)} API_WORK_REQUIRED", run_id),
    )
    sched = conn.execute("SELECT * FROM learnrepo_schedules WHERE schedule_id=?", (row["schedule_id"],)).fetchone()
    nr = next_run(sched["schedule_class"], finish)
    conn.execute(
        "UPDATE learnrepo_schedules SET last_run_at=?, next_run_at=?, lease_owner=NULL, lease_until=NULL, change_score=? WHERE schedule_id=?",
        (_iso(finish), _iso(nr) if nr else None, summary["change_score"], row["schedule_id"]),
    )
    conn.commit()
    util.write_json(config.home() / "state" / "LEARNREPO_HEALTH.json", summary)
    if component == ORG_COMPONENT:
        util.write_json(config.home() / "state" / "LUCYOS_HEALTH.json", summary)
    db.log_event("learnrepo", f"learnrepo.run.{status.lower()}", run_id,
                 f"component={component}; ai_calls={ai_calls}; escalations={len(escalations)}")
    return summary


def run_due(*, mode: str = "nightly", worker: str | None = None, now: datetime | None = None,
            external_fetcher: Callable[[str], dict] | None = None) -> dict:
    """Run all due LearnRepo schedules. Healthy routine path is deterministic."""
    now = _utc(now)
    ensure_defaults(now)
    changed = trigger_on_change_if_needed(now)
    recovered = recover_stale_leases(now)
    compacted = cleanup_history(now)
    worker = worker or f"{platform.node() or 'local'}:{os.getpid()}"
    include_external = mode.lower() in {"weekly", "monthly", "quarterly"}
    runs = []
    for schedule in due_schedules(now):
        run_id = acquire(schedule["schedule_id"], worker, now)
        if run_id:
            runs.append(execute_run(run_id, include_external=include_external, now=now,
                                    external_fetcher=external_fetcher))
    result = {
        "mode": mode.lower(), "at": _iso(now), "jobs_due": len(runs), "jobs_run": len(runs),
        "success": sum(r["status"] == "SUCCESS" for r in runs),
        "late": 0, "missed": len(recovered), "failed": sum(r["status"] == "FAIL" for r in runs),
        "degraded": sum(r["status"] == "DEGRADED" for r in runs),
        "local_repairs": len(recovered), "api_escalations": sum(r["api_escalations"] for r in runs),
        "owner_escalations": sum(r["owner_escalations"] for r in runs), "quarantined": 0,
        "network_requests": sum(r["network_requests"] for r in runs),
        "ai_calls": sum(r["ai_calls"] for r in runs), "change_triggered": changed,
        "history_compacted": compacted, "runs": runs,
    }
    return result


def latest_summary() -> dict:
    path = config.home() / "state" / "LEARNREPO_HEALTH.json"
    return util.read_json(path, default={}) or {}


def status() -> dict:
    ensure_defaults()
    conn = db.connect()
    schedules = [dict(r) for r in conn.execute("SELECT * FROM learnrepo_schedules ORDER BY schedule_id")]
    escalations = conn.execute("SELECT COUNT(*) FROM learnrepo_escalations").fetchone()[0]
    # Per-component breakdown: additive keys only, so existing consumers of
    # this JSON keep working unchanged.  Gated on the additive migration
    # having added the component columns (older databases simply omit it).
    by_component: dict[str, dict] = {}
    have_component = "component" in {r["name"] for r in conn.execute("PRAGMA table_info(learnrepo_schedules)")}
    if have_component:
        rows = conn.execute(
            "SELECT component, COUNT(*) AS n FROM learnrepo_schedules GROUP BY component")
        for r in rows:
            by_component.setdefault(r["component"] or DEFAULT_COMPONENT, {})["schedules"] = r["n"]
        rows = conn.execute(
            "SELECT component, COUNT(*) AS n FROM learnrepo_tasks GROUP BY component")
        for r in rows:
            by_component.setdefault(r["component"] or DEFAULT_COMPONENT, {})["tasks"] = r["n"]
        rows = conn.execute(
            "SELECT source, COUNT(*) AS n FROM learnrepo_escalations GROUP BY source")
        for r in rows:
            by_component.setdefault(r["source"] or DEFAULT_COMPONENT, {})["escalations"] = r["n"]
    return {"schedules": schedules, "latest": latest_summary(), "escalations": escalations,
            "org_enabled": org_enabled(), "components": by_component,
            "os_adapter": os_adapter_name()}


def os_adapter_name(system: str | None = None) -> str:
    system = (system or platform.system()).lower()
    return "systemd" if system == "linux" else ("launchd" if system == "darwin" else "native-timer")


def quarantine(candidate_id: str, reason: str) -> None:
    """Deterministic quarantine marker for future Talent Hunter candidates."""
    db.set_meta(f"learnrepo.quarantine.{candidate_id}", security.redact(reason)[:500])
    db.log_event("learnrepo", "learnrepo.quarantine", candidate_id, reason[:200])



SKILL_REVIEW_STAGES = {"RESEARCH", "LICENSE", "SECURITY", "SANDBOX", "BENCHMARK", "ARCHITECTURE", "OWNER", "INSTALL", "TEST"}
SKILL_REVIEW_ROLES = {"primary", "fallback"}
LIFECYCLE_REVIEW_STAGE = {
    "RESEARCHED": "RESEARCH",
    "LICENSE_OK": "LICENSE",
    "SECURITY_REVIEWED": "SECURITY",
    "SANDBOXED": "SANDBOX",
    "BENCHMARKED": "BENCHMARK",
    "ARCHITECTURE_APPROVED": "ARCHITECTURE",
    "OWNER_APPROVED": "OWNER",
    "INSTALLED_DISABLED": "INSTALL",
    "TESTED": "TEST",
}


def record_skill_review(skill_id: str, candidate_id: str, stage: str, evidence: dict, *,
                        verdict: str = "PASS", candidate_url: str = "", role: str = "primary") -> str:
    """Persist one LearnRepo review checkpoint for a catalog skill.

    This is evidence storage only: it installs nothing and performs no network or model call.
    At most two primary candidates plus one fallback may be tracked per skill.
    """
    from . import skills
    import json
    if skills.get(skill_id) is None:
        raise ValueError(f"unknown skill {skill_id}")
    stage = stage.strip().upper()
    verdict = verdict.strip().upper()
    role = role.strip().lower()
    if stage not in SKILL_REVIEW_STAGES:
        raise ValueError(f"invalid review stage {stage}")
    if verdict not in {"PASS", "FAIL", "NEEDS_REVIEW"}:
        raise ValueError(f"invalid review verdict {verdict}")
    if role not in SKILL_REVIEW_ROLES:
        raise ValueError(f"invalid candidate role {role}")
    if not isinstance(evidence, dict) or not evidence:
        raise ValueError("review evidence must be a non-empty object")
    conn = db.connect()
    existing_candidate = conn.execute(
        "SELECT candidate_role FROM learnrepo_skill_reviews WHERE skill_id=? AND candidate_id=? LIMIT 1",
        (skill_id, candidate_id)).fetchone()
    if existing_candidate and existing_candidate["candidate_role"] != role:
        raise ValueError("candidate role cannot change after review begins")
    candidates = conn.execute(
        "SELECT candidate_id,candidate_role FROM learnrepo_skill_reviews WHERE skill_id=? GROUP BY candidate_id,candidate_role",
        (skill_id,)).fetchall()
    if not existing_candidate:
        primaries = sum(r["candidate_role"] == "primary" for r in candidates)
        fallbacks = sum(r["candidate_role"] == "fallback" for r in candidates)
        if role == "primary" and primaries >= 2:
            raise ValueError("LearnRepo allows at most two primary candidates per skill")
        if role == "fallback" and fallbacks >= 1:
            raise ValueError("LearnRepo allows at most one fallback candidate per skill")
    review_id = util.new_id("LRREV")
    now = util.now()
    payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    conn.execute(
        "INSERT INTO learnrepo_skill_reviews(review_id,skill_id,candidate_id,candidate_url,candidate_role,stage,verdict,evidence_json,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(skill_id,candidate_id,stage) DO UPDATE SET "
        "candidate_url=excluded.candidate_url,candidate_role=excluded.candidate_role,verdict=excluded.verdict,evidence_json=excluded.evidence_json,updated_at=excluded.updated_at",
        (review_id, skill_id, candidate_id, security.redact(candidate_url), role, stage, verdict, security.redact(payload), now, now))
    conn.commit()
    db.log_event("learnrepo", "skill.review", skill_id, f"{candidate_id}:{stage}:{verdict}")
    row = conn.execute("SELECT review_id FROM learnrepo_skill_reviews WHERE skill_id=? AND candidate_id=? AND stage=?",
                       (skill_id, candidate_id, stage)).fetchone()
    return row["review_id"]


def skill_review_status(skill_id: str) -> dict:
    rows = db.connect().execute(
        "SELECT * FROM learnrepo_skill_reviews WHERE skill_id=? ORDER BY candidate_role,candidate_id,stage",
        (skill_id,)).fetchall()
    stages = {}
    for row in rows:
        stages.setdefault(row["stage"], []).append({"candidate_id": row["candidate_id"], "role": row["candidate_role"], "verdict": row["verdict"]})
    return {"skill_id": skill_id, "reviews": len(rows), "stages": stages}


def review_gate(skill_id: str, lifecycle_target: str) -> tuple[bool, str]:
    """Return whether LearnRepo evidence permits a catalog lifecycle transition."""
    required = LIFECYCLE_REVIEW_STAGE.get(lifecycle_target.strip().upper())
    if not required:
        return True, "no LearnRepo evidence required for this lifecycle target"
    rows = db.connect().execute(
        "SELECT candidate_id,candidate_role,verdict FROM learnrepo_skill_reviews WHERE skill_id=? AND stage=?",
        (skill_id, required)).fetchall()
    passed = [r for r in rows if r["verdict"] == "PASS"]
    if not passed:
        return False, f"missing PASS LearnRepo {required} evidence"
    return True, f"{required} evidence passed for {len(passed)} candidate(s)"

def log_future_whole_lucyos_task() -> str:
    title = "Generalize LearnRepo health into organization-wide LucyOS health system"
    conn = db.connect()
    row = conn.execute("SELECT task_id FROM tasks WHERE project='LucyOS' AND title=? LIMIT 1", (title,)).fetchone()
    if row:
        return row["task_id"]
    return tasks.create(
        title, project="LucyOS", status="WAITING", priority=3, model_class="C", kind="architecture",
        description=("GENERALIZE LEARNREPO HEALTH LEVELS + SCHEDULED QUEUE + CONTRACT CHECKS + "
                     "API ESCALATION INTO ORGANISATION-WIDE LUCYOS HEALTH SYSTEM. LearnRepo is the pilot."),
        blockers="deferred: LearnRepo pilot must mature before organization-wide rollout",
        success_criteria="approved architecture and staged migration after LearnRepo pilot evidence",
        next_action="review after LearnRepo pilot has stable production history",
    )
