#!/usr/bin/env python3
"""Report what containment this host actually provides — by testing, not guessing.

The trap this exists to prevent: `docker` being on PATH while the daemon is
unreachable.  A skill that checks for the binary concludes "we have containers"
and reports a sandbox that never existed.  Every probe here therefore runs a
harmless command and checks whether it really worked.

Nothing in this script executes candidate code.  It runs fixed, local,
argument-list commands with short timeouts and no shell.

Usage:
    python3 sandbox_probe.py [--json]

Exit codes: 0 some containment is usable · 1 none usable · 2 error
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

TIMEOUT_S = 15

# Ordered strongest-first.  "strength" is a coarse, honest label — none of
# these is a security boundary against a kernel exploit, and the notes say so.
PROBES = (
    {
        "name": "docker",
        "argv": ["docker", "info"],
        "strength": "strong",
        "note": "Container isolation. Still shares the host kernel; use --network=none, "
                "a read-only rootfs, dropped capabilities and a non-root user.",
    },
    {
        "name": "podman",
        "argv": ["podman", "info"],
        "strength": "strong",
        "note": "Rootless containers. Same kernel-sharing caveat as docker.",
    },
    {
        "name": "bubblewrap",
        "argv": ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "true"],
        "strength": "medium",
        "note": "Unprivileged namespace sandbox. Good filesystem/network confinement; "
                "no seccomp policy unless you add one.",
    },
    {
        "name": "unshare",
        "argv": ["unshare", "--user", "--map-root-user", "--net", "--mount", "--pid",
                 "--fork", "true"],
        "strength": "weak",
        "note": "User+network+mount+PID namespaces. Blocks network egress and isolates "
                "mounts, but is not a hardened sandbox: no seccomp, no resource caps "
                "unless you add ulimits, and user namespaces have had kernel CVEs.",
    },
)


def probe_one(spec: dict) -> dict:
    result = {
        "name": spec["name"],
        "strength": spec["strength"],
        "note": spec["note"],
        "present": False,
        "usable": False,
        "detail": "",
    }
    if shutil.which(spec["argv"][0]) is None:
        result["detail"] = "not installed"
        return result
    result["present"] = True
    try:
        proc = subprocess.run(
            spec["argv"], shell=False, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        result["detail"] = f"installed but timed out after {TIMEOUT_S}s"
        return result
    except OSError as exc:
        result["detail"] = f"installed but could not run: {exc}"
        return result
    if proc.returncode == 0:
        result["usable"] = True
        result["detail"] = "verified working"
    else:
        stderr = (proc.stderr or proc.stdout or "").strip().splitlines()
        first = stderr[0][:160] if stderr else f"exit {proc.returncode}"
        result["detail"] = f"installed but NOT usable: {first}"
    return result


def probe() -> dict:
    probes = [probe_one(spec) for spec in PROBES]
    usable = [p for p in probes if p["usable"]]
    best = usable[0]["name"] if usable else None
    if best:
        recommendation = (
            f"Execution of candidate code is possible using '{best}'. Use synthetic "
            "data only, disable network egress, set CPU/memory/time limits, and record "
            f"sandbox='{best}' in the manifest. Static analysis first is still cheaper "
            "and answers most questions.")
    else:
        recommendation = (
            "No usable containment on this host. Do NOT execute candidate code. "
            "Complete the assessment with static analysis and say plainly in the report "
            "that dynamic behaviour was not observed.")
    return {
        "usable_containment": bool(usable),
        "best": best,
        "probes": probes,
        "recommendation": recommendation,
        "caveat": ("None of these is a guarantee. Containment reduces blast radius; it "
                   "does not make untrusted code safe to run."),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Probe available sandboxing")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    report = probe()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in report["probes"]:
            if item["usable"]:
                mark = "OK  "
            elif item["present"]:
                mark = "WARN"
            else:
                mark = "--  "
            print(f"{mark} {item['name']:<12} [{item['strength']:<6}] {item['detail']}")
        print()
        print(f"Best available: {report['best'] or 'NONE'}")
        print(f"Recommendation: {report['recommendation']}")
        print(f"Caveat: {report['caveat']}")
    return 0 if report["usable_containment"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
