"""Deterministic health checks.  Every value here is measured, never assumed."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import uuid
from pathlib import Path

from . import config, db, errors, host, metrics, packets, tasks, util, worker


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


def check_openclaw() -> dict:
    from bridges import openclaw_check
    result = openclaw_check.check()
    return {"name": "openclaw", "ok": True, "required": False,
            "detail": f"{result['state']}: {result['detail']}"}


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


def check_learnrepo() -> dict:
    try:
        from . import learnrepo
        learnrepo.ensure_defaults()
        latest = learnrepo.latest_summary()
        bad = latest.get("status") in {"FAIL", "MISSED", "QUARANTINED"}
        detail = (f"latest={latest.get('status', 'not-run')}, ai_calls={latest.get('ai_calls', 0)}, "
                  f"escalations={latest.get('api_escalations', 0)}")
        return {"name": "learnrepo", "ok": not bad, "detail": detail}
    except Exception as exc:
        return {"name": "learnrepo", "ok": False, "detail": str(exc)}


def check_skill_registry() -> dict:
    try:
        from . import skills
        skills.ensure_defaults()
        rows = skills.all_skills()
        invalid = skills.validate_registry()
        catalog_errors = skills.validate_catalog()
        problems = invalid + catalog_errors
        discovered = sum(r["lifecycle_state"] == "DISCOVERED" for r in rows)
        return {"name": "skill_registry", "ok": not problems,
                "detail": (f"{len(rows)} registered, {sum(bool(r['enabled']) for r in rows)} enabled, "
                           f"{discovered} discovered candidates, {len(skills.catalog_manifests())} catalog manifests"
                           if not problems else f"invalid: {', '.join(problems[:4])}")}
    except Exception as exc:
        return {"name": "skill_registry", "ok": False, "detail": str(exc)}



def _run_authority(args: list[str]) -> dict:
    """Invoke the existing authority verifier as a bounded subprocess.

    Reuses `scripts/verify_authority.py` rather than re-implementing hash/git
    checks here; a crash or timeout degrades to a reported failure, never a
    raised exception.
    """
    repo = Path(__file__).resolve().parent.parent
    script = repo / "scripts" / "verify_authority.py"
    code, out = _run([sys.executable, str(script), *args], timeout=20)
    try:
        return json.loads(out)
    except (ValueError, TypeError):
        return {"ok": False, "violations": [out or f"verifier exited {code} with no output"]}


def check_authority() -> dict:
    """Authority/deploy drift, reported as visible-but-non-blocking runtime signal.

    Deliberately not in BLOCKING or SETUP_REQUIRED: a healthy, working local
    runtime can coexist with stale protected-file hashes (e.g. before a
    refreeze). Drift is surfaced here for visibility; `deploy_readiness()`
    is the authoritative answer to "is this tree deployable".
    """
    report = _run_authority(["self"])
    violations = report.get("violations", [])
    return {"name": "authority", "ok": report.get("ok", False), "required": False,
            "detail": "no drift" if not violations else f"{len(violations)} drift: {', '.join(violations[:4])}"}


def deploy_readiness() -> dict:
    """Explicit, separate verdict: can this exact tree be deployed?

    Never folded into `verify()`'s READY/SETUP_REQUIRED/BROKEN verdict —
    a machine can be a perfectly sound place to develop on while its tree
    is not yet frozen/deployable, and the reverse.
    """
    report = _run_authority(["deploy"])
    violations = report.get("violations", [])
    return {"ready": bool(report.get("ok", False)),
            "fable_freeze_sha": report.get("fable_freeze_sha"),
            "violations": violations}


def check_github_remote() -> dict:
    """Repository remote usability, measured without requiring a PAT.

    A read-only `git ls-remote` proves the configured remote (SSH, HTTPS+
    credential-helper, or otherwise) is reachable for reads. It deliberately
    does not claim write authority; `check_github_write()` measures that
    separately without mutating the remote.
    """
    repo = Path(__file__).resolve().parent.parent
    code, remotes = _run(["git", "-C", str(repo), "remote"])
    if code != 0 or not remotes.strip():
        return {"name": "github_remote", "ok": False, "required": False,
                "detail": "no git remote configured"}
    remote = remotes.splitlines()[0].strip()
    code, out = _run(["git", "-C", str(repo), "ls-remote", "--exit-code", remote, "HEAD"],
                      timeout=6)
    if code == 0:
        return {"name": "github_remote", "ok": True, "required": False,
                "detail": f"remote '{remote}' reachable (read access verified, no PAT required)"}
    return {"name": "github_remote", "ok": False, "required": False,
            "detail": f"remote '{remote}' configured but read access not proven (git exit {code})"}


def check_github_write() -> dict:
    """Repo write (push) capability, proven without mutating the remote.

    `git push --dry-run` exercises the exact auth/ACL check a real push
    would — the remote validates the update and reports success or
    rejection — but `--dry-run` stops before the ref is actually updated,
    so the remote is never mutated. This is the only way to prove the
    owner requirement (repo read *and* write) rather than read-only
    `check_github_remote`, which cannot distinguish a read-only deploy key
    from a read/write credential.
    """
    repo = Path(__file__).resolve().parent.parent
    code, remotes = _run(["git", "-C", str(repo), "remote"])
    if code != 0 or not remotes.strip():
        return {"name": "github_write", "ok": False, "required": False,
                "detail": "no git remote configured"}
    remote = remotes.splitlines()[0].strip()
    probe_ref = f"refs/heads/aion-write-probe-{uuid.uuid4().hex[:8]}"
    code, out = _run(
        ["git", "-C", str(repo), "push", "--dry-run", remote, f"HEAD:{probe_ref}"],
        timeout=10)
    if code == 0:
        return {"name": "github_write", "ok": True, "required": False,
                "detail": f"remote '{remote}' write access verified (dry-run push, no mutation)"}
    return {"name": "github_write", "ok": False, "required": False,
            "detail": f"remote '{remote}' write access not proven (dry-run push exit {code})"}


def check_drive_bridge() -> dict:
    from bridges.drive_bridge import capability
    cap = capability()
    if cap["detail"] == "rclone not installed":
        return {"name": "drive_bridge", "ok": True, "required": False, "detail": cap["detail"]}
    return {"name": "drive_bridge", "ok": cap["list"], "required": False, "detail": cap["detail"]}


CHECKS = [check_db, check_shared_brain, check_disk, check_inbox, check_tasks, check_errors,
          check_budget, check_git, check_ollama, check_network, check_secrets, check_backup,
          check_learnrepo, check_skill_registry, check_openclaw, check_authority]
# Shells out with a network round-trip; too slow to run on every ordinary
# health check, so these only run when deep=True asks for them.
DEEP_ONLY_CHECKS = [check_drive_bridge, check_github_remote, check_github_write]


def run_all(deep: bool = False) -> dict:
    results = []
    for fn in CHECKS + (DEEP_ONLY_CHECKS if deep else []):
        try:
            results.append(fn())
        except Exception as exc:
            results.append({"name": fn.__name__, "ok": False, "detail": f"check crashed: {exc}"})
    failing = [r for r in results if not r["ok"]]
    required_failing = [r for r in failing if r.get("required", True)]
    report = {
        "at": util.now(),
        "healthy": not required_failing,
        "checks": results,
        "failing": [r["name"] for r in failing],
        "required_failing": [r["name"] for r in required_failing],
        "deep": deep,
    }
    if deep:
        report["packet_stats"] = packets.stats()
        report["task_counts"] = tasks.counts()
        report["budget"] = metrics.budget_status()
    util.write_json(config.home() / "state" / "HEALTH.json", report)
    db.set_meta("last_health_check", util.now())
    return report


# Machine acceptance (`aion verify`): distinguish broken health from owner setup.
# Which health checks decide the verdict.  A check not named here is treated
# as OPTIONAL: reported, never fatal.
BLOCKING = {"database", "shared_brain", "disk", "git"}
SETUP_REQUIRED = {"secret_store", "backup"}

# The exact owner command that clears each setup-required check.
SETUP_ACTIONS = {
    "secret_store": "aion secrets init",
    "backup": "aion backup",
}

VERDICTS = ("READY", "SETUP_REQUIRED", "BROKEN")
EXIT_CODES = {"READY": 0, "SETUP_REQUIRED": 0, "BROKEN": 2}


def machine() -> dict:
    """Who and what this machine is.  Pure measurement, no inference."""
    repo = Path(__file__).resolve().parent.parent
    return {
        "hostname": socket.gethostname(),
        "label": os.environ.get("AION_MACHINE", "") or "unlabelled",
        "platform": host.current().name(),
        "arch": host.current().architecture(),
        "python": ".".join(map(str, sys.version_info[:3])),
        "repo_path": str(repo),
        "repo_commit": _git(repo, ["rev-parse", "--short", "HEAD"]),
        "repo_branch": _git(repo, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "aion_home": str(config.home()),
    }


def _git(repo: Path, args: list[str]) -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(repo), *args],
                           capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def openclaw() -> dict:
    """What OpenClaw evidence exists here.  Reports findings, never infers a gateway."""
    on_path = shutil.which("openclaw")
    root = Path(os.environ.get("OPENCLAW_HOME", Path.home() / "openclaw")).expanduser()
    contents = []
    if root.is_dir():
        # `shared_brain` is AION's own state and is not evidence of OpenClaw.
        contents = sorted(p.name for p in root.iterdir() if p.name != "shared_brain")
    return {
        "executable_on_path": on_path,
        "home": str(root) if root.is_dir() else None,
        "home_contents": contents,
        "present": bool(on_path or contents),
    }


def host_capabilities() -> dict:
    """Execution capability of this machine, measured now.

    `worker.capability_report()` reads the database, which is exactly what is
    unavailable on the broken machines this command exists to diagnose, so a
    failure there degrades to "unknown" instead of taking `verify` down.
    """
    try:
        caps = dict(worker.capability_report())
    except Exception as exc:  # noqa: BLE001 - see docstring
        caps = {"ollama": False, "cloud_worker": False,
                "unavailable": f"could not read local state: {exc}"}
    adapter = host.current()
    caps["scheduler_kind"] = adapter.scheduler_kind()
    caps["scheduler_available"] = adapter.scheduler_available()
    caps["python_ok"] = sys.version_info >= (3, 9)
    return caps


def classify(report: dict) -> dict:
    """Split health results into the three tiers."""
    tiers = {"blocking": [], "setup_required": [], "optional": []}
    for check in report["checks"]:
        if check["ok"]:
            continue
        name = check["name"]
        entry = {"name": name, "detail": check["detail"]}
        if name in BLOCKING:
            tiers["blocking"].append(entry)
        elif name in SETUP_REQUIRED:
            entry["fix"] = SETUP_ACTIONS.get(name, "")
            tiers["setup_required"].append(entry)
        else:
            tiers["optional"].append(entry)
    return tiers


def run_tests(repo: Path) -> dict:
    """Run the real test suite.  Reports the measured result, never a claim."""
    try:
        p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                           capture_output=True, text=True, timeout=900, cwd=str(repo))
    except subprocess.TimeoutExpired:
        return {"ran": True, "ok": False, "detail": "test suite timed out after 900s"}
    except OSError as exc:
        return {"ran": False, "ok": False, "detail": f"could not run tests: {exc}"}
    # unittest writes its summary to stderr; test stdout is noise here.
    output = p.stderr or ""
    return {
        "ran": True,
        "ok": p.returncode == 0,
        "detail": _summary_line(output),
        "count": _test_count(output),
    }


def _summary_line(output: str) -> str:
    """unittest's own verdict ('OK', 'FAILED (errors=2)'), not stray test output."""
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        if stripped == "OK" or stripped.startswith(("OK ", "FAILED")):
            return stripped
    return "no unittest summary found"


def _test_count(output: str) -> int | None:
    for line in output.splitlines():
        if line.startswith("Ran ") and " test" in line:
            try:
                return int(line.split()[1])
            except (ValueError, IndexError):
                return None
    return None


def verify(*, deep: bool = False, deploy_readiness_check: bool = False) -> dict:
    """The full acceptance check.  Returns a verdict plus the evidence for it.

    Never raises.  This is the command an owner reaches for when a machine is
    suspect, so a machine broken badly enough to crash the health run must
    still produce a readable BROKEN verdict rather than a traceback.
    """
    try:
        report = run_all()
    except Exception as exc:  # noqa: BLE001 - a broken machine must still report
        report = {"healthy": False, "failing": ["health_run"],
                  "checks": [{"name": "database", "ok": False,
                              "detail": f"health checks could not complete: {exc}"}]}
    tiers = classify(report)
    result = {
        "at": util.now(),
        "machine": machine(),
        "openclaw": openclaw(),
        "capabilities": host_capabilities(),
        "health": {"healthy": report["healthy"], "failing": report["failing"]},
        "tiers": tiers,
    }

    if deep:
        result["tests"] = run_tests(Path(__file__).resolve().parent.parent)

    if deploy_readiness_check:
        result["deploy_readiness"] = deploy_readiness()

    result["verdict"] = _verdict(tiers, result.get("tests"))
    result["exit_code"] = EXIT_CODES[result["verdict"]]
    return result


def _verdict(tiers: dict, tests: dict | None) -> str:
    if tiers["blocking"]:
        return "BROKEN"
    if tests is not None and not tests["ok"]:
        return "BROKEN"
    if tiers["setup_required"]:
        return "SETUP_REQUIRED"
    return "READY"


def render_verify(result: dict) -> str:
    """One screen an owner (or another AI session) can read and act on."""
    m, oc, caps = result["machine"], result["openclaw"], result["capabilities"]
    lines = [
        f"AION VERIFY · {result['verdict']}",
        "",
        f"Machine: {m['label']} ({m['hostname']}) · {m['platform']} {m['arch']} · "
        f"Python {m['python']}",
        f"Repo: {m['repo_branch']}@{m['repo_commit'] or 'unknown'} at {m['repo_path']}",
        f"Shared brain: {m['aion_home']}",
        "",
        "Can execute here:",
        f"  local model (ollama): {'yes' if caps['ollama'] else 'no'}",
        f"  cloud worker: {'yes' if caps['cloud_worker'] else 'not configured'}",
        f"  scheduler ({caps['scheduler_kind']}): " +
        ("yes" if caps["scheduler_available"] else "no"),
        f"  OpenClaw: " + (
            f"present ({oc['executable_on_path'] or ', '.join(oc['home_contents'][:4])})"
            if oc["present"] else "not detected"),
    ]

    tiers = result["tiers"]
    if tiers["blocking"]:
        lines += ["", "BLOCKING — this machine is not sound:"]
        lines += [f"  ✗ {e['name']}: {e['detail']}" for e in tiers["blocking"]]
    if tiers["setup_required"]:
        lines += ["", "SETUP REQUIRED — run these here:"]
        lines += [f"  → {e['fix']}   ({e['name']}: {e['detail']})"
                  for e in tiers["setup_required"]]
    if tiers["optional"]:
        lines += ["", "Optional / degrades gracefully:"]
        lines += [f"  · {e['name']}: {e['detail']}" for e in tiers["optional"]]

    tests = result.get("tests")
    if tests:
        mark = "OK" if tests["ok"] else "FAILED"
        count = f"{tests['count']} tests" if tests.get("count") else "tests"
        lines += ["", f"Test suite: {mark} — {count} · {tests['detail']}"]
    else:
        lines += ["", "Test suite: not run (use --deep to run it here)"]

    dr = result.get("deploy_readiness")
    if dr is not None:
        mark = "READY" if dr["ready"] else "NOT READY"
        lines += ["", f"Deploy readiness (exact-SHA authority): {mark}"]
        lines += [f"  ✗ {v}" for v in dr["violations"]]

    lines += ["", _headline(result["verdict"])]
    return "\n".join(lines)


def _headline(verdict: str) -> str:
    if verdict == "READY":
        return "This machine is verified: LucyOS is sound here and ready to use."
    if verdict == "SETUP_REQUIRED":
        return ("LucyOS is sound here; finish the owner steps above, "
                "then re-run `aion verify`.")
    return "Do not run work on this machine until the blocking failures above are fixed."
