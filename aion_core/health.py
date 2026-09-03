"""Deterministic health checks.  Every value here is measured, never assumed."""
from __future__ import annotations

import shutil
import socket
import subprocess
from pathlib import Path

from . import config, db, errors, metrics, packets, tasks, util


def _run(cmd: list[str], timeout: int = 8) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return 127, str(exc)


def check_disk() -> dict:
    root = config.home()
    root.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(root)
    free_gb = round(usage.free / 1e9, 2)
    return {"name": "disk", "ok": free_gb > 1.0, "detail": f"{free_gb} GB free at {root}"}


def check_db() -> dict:
    try:
        conn = db.connect()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        n = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        return {"name": "database", "ok": integrity == "ok",
                "detail": f"integrity={integrity}, {n} tasks, fts={'on' if db.HAS_FTS else 'off'}"}
    except Exception as exc:
        return {"name": "database", "ok": False, "detail": str(exc)}


def check_shared_brain() -> dict:
    root = config.home()
    missing = [d for d in config.DIRS if not (root / d).is_dir()]
    missing += [f for f in config.DOCS if not (root / f).is_file()]
    return {"name": "shared_brain", "ok": not missing,
            "detail": "complete" if not missing else f"missing: {', '.join(missing[:6])}"}


def check_inbox() -> dict:
    pending = len(packets.pending_files())
    stats = packets.stats()
    failed = stats.get("FAILED", 0)
    return {"name": "sync_inbox", "ok": failed == 0,
            "detail": f"{pending} pending, {failed} failed, {stats.get('PROCESSED', 0)} processed"}


def check_tasks() -> dict:
    counts = tasks.counts()
    stale = tasks.release_stale()
    blocked = counts.get("BLOCKED", 0)
    return {"name": "task_queue", "ok": True,
            "detail": f"{counts.get('READY', 0)} ready, {counts.get('RUNNING', 0)} running, "
                      f"{blocked} blocked, {len(stale)} stale claims released"}


def check_errors() -> dict:
    open_n = len(errors.open_errors(limit=100))
    return {"name": "errors", "ok": open_n == 0, "detail": f"{open_n} unresolved"}


def check_budget() -> dict:
    b = metrics.budget_status()
    ok = not (b["day_over"] or b["month_over"])
    return {"name": "budget", "ok": ok,
            "detail": f"day ₹{b['day_spend_inr']}/{b['day_cap_inr']}, "
                      f"month ₹{b['month_spend_inr']}/{b['month_cap_inr']}, "
                      f"governor {b['governor']}"}


def check_git() -> dict:
    repo = Path(__file__).resolve().parent.parent
    code, out = _run(["git", "-C", str(repo), "status", "--porcelain"])
    if code != 0:
        return {"name": "git", "ok": False, "detail": out[:200] or "git unavailable"}
    dirty = len([l for l in out.splitlines() if l.strip()])
    _, branch = _run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"])
    return {"name": "git", "ok": True, "detail": f"branch {branch}, {dirty} uncommitted paths"}


def check_ollama() -> dict:
    code, out = _run(["ollama", "list"])
    if code == 127:
        return {"name": "ollama", "ok": True, "required": False,
                "detail": "not installed here — local-model routing degrades to class B"}
    models = [l.split()[0] for l in out.splitlines()[1:] if l.strip()]
    return {"name": "ollama", "ok": bool(models), "required": False,
            "detail": f"{len(models)} local models: {', '.join(models[:5]) or 'none'}"}


def check_network() -> dict:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        return {"name": "network", "ok": True, "detail": "outbound reachable"}
    except OSError as exc:
        return {"name": "network", "ok": False, "detail": f"no outbound: {exc}"}


def check_secrets() -> dict:
    sf = config.secrets_file()
    if not sf.exists():
        return {"name": "secret_store", "ok": False,
                "detail": f"not created yet at {sf} (owner action: aion secrets init)"}
    mode = oct(sf.stat().st_mode & 0o777)
    return {"name": "secret_store", "ok": mode == "0o600",
            "detail": f"{sf} mode {mode} (must be 0o600)"}


def check_backup() -> dict:
    d = config.home() / "BACKUPS"
    if not d.is_dir():
        return {"name": "backup", "ok": False, "detail": "no BACKUPS directory"}
    files = sorted(d.glob("aion-backup-*.tar.gz"))
    if not files:
        return {"name": "backup", "ok": False, "detail": "no backup taken yet"}
    latest = files[-1]
    return {"name": "backup", "ok": True,
            "detail": f"latest {latest.name} ({round(latest.stat().st_size / 1024, 1)} KB)"}


CHECKS = [check_db, check_shared_brain, check_disk, check_inbox, check_tasks, check_errors,
          check_budget, check_git, check_ollama, check_network, check_secrets, check_backup]


def run_all(deep: bool = False) -> dict:
    results = []
    for fn in CHECKS:
        try:
            results.append(fn())
        except Exception as exc:
            results.append({"name": fn.__name__, "ok": False, "detail": f"check crashed: {exc}"})
    failing = [r for r in results if not r["ok"]]
    report = {
        "at": util.now(),
        "healthy": not failing,
        "checks": results,
        "failing": [r["name"] for r in failing],
        "deep": deep,
    }
    if deep:
        report["packet_stats"] = packets.stats()
        report["task_counts"] = tasks.counts()
        report["budget"] = metrics.budget_status()
    util.write_json(config.home() / "state" / "HEALTH.json", report)
    db.set_meta("last_health_check", util.now())
    return report
