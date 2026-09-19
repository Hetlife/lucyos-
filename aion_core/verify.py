"""`aion verify` — the machine acceptance test.

LucyOS runs on more than one machine: the golden repository, a temporary
cloud box used for test compute, the local Linux PC that hosts OpenClaw, and
whatever workstation comes later.  The question that has to be answerable on
each of them, in one command, is:

    Is LucyOS actually sound on THIS machine, and what can this machine do?

`health.run_all()` alone cannot answer it.  Health is a running-system check:
on a freshly installed machine it reports FAILING because no secret store and
no backup exist yet, which is correct but useless as an arrival gate — every
new machine would look broken.

So this module classifies each health check into one of three tiers and turns
them into a single verdict:

    BLOCKING        the machine is genuinely broken; LucyOS cannot be trusted here
    SETUP_REQUIRED  the machine is sound but an owner step has not been done yet
    OPTIONAL        absent capability that degrades gracefully (no local model, etc.)

It measures and never assumes.  A capability this machine does not have is
reported as absent, not guessed at, and OpenClaw detection reports exactly
what was found on disk rather than inferring that a gateway is running.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from . import config, health, host, util, worker

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
EXIT_CODES = {"READY": 0, "SETUP_REQUIRED": 1, "BROKEN": 2}


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


def run(*, deep: bool = False) -> dict:
    """The full acceptance check.  Returns a verdict plus the evidence for it.

    Never raises.  This is the command an owner reaches for when a machine is
    suspect, so a machine broken badly enough to crash the health run must
    still produce a readable BROKEN verdict rather than a traceback.
    """
    try:
        report = health.run_all()
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


def render(result: dict) -> str:
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

    lines += ["", _headline(result["verdict"])]
    return "\n".join(lines)


def _headline(verdict: str) -> str:
    if verdict == "READY":
        return "This machine is verified: LucyOS is sound here and ready to use."
    if verdict == "SETUP_REQUIRED":
        return ("LucyOS is sound here; finish the owner steps above, "
                "then re-run `aion verify`.")
    return "Do not run work on this machine until the blocking failures above are fixed."
