#!/usr/bin/env python3
"""Deterministic high-model authority verifier for LucyOS.

Enforces the contract in .lucy/handoffs/2026-09-16/03_HIGH_TO_LOW_MODEL_AUTHORITY_CONTRACT.md
with git and hashes rather than prompt obedience.

Modes
  strict   --base REF [--task-id ID | --branch NAME]
           A lower-model branch may not change a protected path unless the task it
           declares has an override recorded in the BASE branch's baseline. The
           baseline is always read from BASE, never from the branch under test, so
           the branch cannot grant itself permission.
  anti-dup --base REF
           Diff-based duplicate-control-plane scan (no self-declaration involved):
           new sqlite connections, new aion_core top-level modules, new CREATE TABLE
           outside db.py, new service units outside deploy dirs, third-party
           orchestration imports, new governor/scheduler/approval-named files.
  self     Working tree vs the hashes recorded in the local baseline (drift report).
  deploy   `self` plus protected blobs compared against fable_freeze_sha. For Codex
           on Mark-2: proves the deployed tree carries the frozen authority files.
  freeze   --sha SHA|PENDING   Rewrite protected_file_hashes (Fable/owner ritual only).

Exit status: 0 = pass, 1 = violation, 2 = usage/infra error.
Standard library only, like the rest of LucyOS.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

BASELINE = ".lucy/authority/HIGH_MODEL_BASELINE.json"
# Paths no task override may ever cover. Changing these is an owner-merged act.
CONSTITUTIONAL = (
    ".lucy/authority/**",
    ".github/workflows/lucyos-ci.yml",
    "scripts/verify_authority.py",
)
TASK_ID = re.compile(r"\b((?:S|FABLE|OWNER|CODEX)-\d{1,4})\b")
FORBIDDEN_IMPORTS = re.compile(
    r"^\+\s*(?:from|import)\s+(apscheduler|celery|schedule|crontab|croniter|langchain|"
    r"langgraph|autogen|crewai|llama_index|haystack|prefect|airflow|dramatiq|rq)\b")
CREATE_TABLE = re.compile(r"^\+.*\bCREATE\s+TABLE\b", re.IGNORECASE)
SQLITE_CONNECT = re.compile(r"^\+.*\bsqlite3\.connect\(")
UNIT_FILE = re.compile(r"\.(service|timer|plist)$")
DUP_NAME = re.compile(r"(governor|scheduler|orchestrat|approval)", re.IGNORECASE)


def git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        return path == pattern[:-3] or path.startswith(pattern[:-2])
    return fnmatch.fnmatchcase(path, pattern)


def any_match(path: str, patterns) -> bool:
    return any(matches(path, p) for p in patterns)


def load_baseline_from(ref: str | None) -> dict:
    if ref is None:
        p = Path(BASELINE)
        if not p.exists():
            raise SystemExit(f"no baseline at {BASELINE}")
        return json.loads(p.read_text(encoding="utf-8"))
    out = subprocess.run(["git", "show", f"{ref}:{BASELINE}"], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"base ref {ref!r} carries no {BASELINE}; refusing to verify against a "
                         "base without an authority baseline")
    return json.loads(out.stdout)


def merge_base(base: str) -> str:
    return git("merge-base", base, "HEAD").strip()


def changed_paths(mb: str) -> list[str]:
    return [p for p in git("diff", "--name-only", mb, "HEAD").splitlines() if p]


def added_paths(mb: str) -> list[str]:
    return [p for p in git("diff", "--name-only", "--diff-filter=A", mb, "HEAD").splitlines() if p]


def added_lines(mb: str):
    """Yield (path, line) for every added line in the diff, unified-0."""
    path = None
    for raw in git("diff", "-U0", mb, "HEAD").splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("+") and not raw.startswith("+++") and path:
            yield path, raw


def detect_task_ids(mb: str, explicit: str | None, branch: str | None) -> set[str]:
    ids = set()
    if explicit:
        ids.add(explicit)
    if branch:
        ids.update(TASK_ID.findall(branch))
    for line in git("log", "--format=%B", f"{mb}..HEAD").splitlines():
        if line.lower().startswith("task-id:"):
            ids.update(TASK_ID.findall(line))
    return ids


# ---------------------------------------------------------------- strict

def cmd_strict(args) -> int:
    baseline = load_baseline_from(args.base)
    protected = baseline["protected_paths"]
    mb = merge_base(args.base)
    changed = changed_paths(mb)
    touched = [p for p in changed if any_match(p, protected)]
    report = {"mode": "strict", "base": args.base, "merge_base": mb[:12],
              "changed": len(changed), "protected_touched": touched, "violations": []}
    if not touched:
        return finish(report)

    ids = detect_task_ids(mb, args.task_id, args.branch)
    if len(ids) != 1:
        report["violations"].append(
            f"protected paths changed but task id is {'ambiguous: ' + ','.join(sorted(ids)) if ids else 'undeclared'}"
            " (declare exactly one via branch name task/<ID>-... or a 'Task-ID: <ID>' commit trailer)")
        return finish(report)
    task = ids.pop()
    report["task_id"] = task
    overrides = baseline.get("task_overrides", {}).get(task, [])
    for p in touched:
        if any_match(p, CONSTITUTIONAL):
            report["violations"].append(f"{p}: constitutional path; no task override can cover it (owner-merged only)")
        elif not any_match(p, overrides):
            report["violations"].append(f"{p}: protected; task {task} has no override for it in the base baseline")
    return finish(report)


# ---------------------------------------------------------------- anti-dup

def cmd_anti_dup(args) -> int:
    baseline = load_baseline_from(args.base)
    mb = merge_base(args.base)
    allow_modules = set(baseline.get("aion_core_modules", []))
    allow_connect = set(baseline.get("sqlite_connect_allowed", []))
    unit_dirs = tuple(baseline.get("service_unit_dirs", []))
    report = {"mode": "anti-dup", "base": args.base, "merge_base": mb[:12], "violations": []}
    v = report["violations"]

    for p in added_paths(mb):
        parts = p.split("/")
        if parts[0] == "aion_core" and len(parts) >= 2:
            top = parts[1][:-3] if len(parts) == 2 and parts[1].endswith(".py") else parts[1]
            if top not in allow_modules and top != "__pycache__":
                v.append(f"{p}: new aion_core top-level module/package {top!r} not in baseline allowlist "
                         "(escalate: a new core module is a Fable decision)")
        if UNIT_FILE.search(p) and not p.startswith(unit_dirs):
            v.append(f"{p}: service/timer/plist unit outside {unit_dirs}")
        base = parts[-1]
        if DUP_NAME.search(base) and not p.startswith(("tests/", "docs/", ".lucy/", "aion_core/resource_governor/")):
            v.append(f"{p}: new file named like a control-plane component ({DUP_NAME.pattern}); "
                     "LucyOS already has one — escalate")

    for path, line in added_lines(mb):
        if not path.endswith(".py"):
            continue
        if path.startswith("tests/"):
            continue
        if SQLITE_CONNECT.search(line) and path not in allow_connect:
            v.append(f"{path}: new sqlite3.connect() outside {sorted(allow_connect)} — a second state store")
        if CREATE_TABLE.search(line) and path != "aion_core/db.py":
            v.append(f"{path}: CREATE TABLE outside aion_core/db.py — schema belongs to the canonical store")
        if FORBIDDEN_IMPORTS.search(line):
            v.append(f"{path}: third-party orchestration/scheduler import: {line.strip()[:80]} "
                     "(LucyOS is standard-library only; duplicate control plane)")
    return finish(report)


# ---------------------------------------------------------------- self / deploy

def hash_drift(baseline: dict) -> list[str]:
    problems = []
    for path, expected in sorted(baseline.get("protected_file_hashes", {}).items()):
        p = Path(path)
        if not p.exists():
            problems.append(f"{path}: missing")
        elif sha256_file(p) != expected:
            problems.append(f"{path}: hash drift")
    return problems


def cmd_self(args) -> int:
    baseline = load_baseline_from(None)
    report = {"mode": "self", "fable_freeze_sha": baseline.get("fable_freeze_sha"),
              "violations": hash_drift(baseline)}
    return finish(report)


def cmd_deploy(args) -> int:
    baseline = load_baseline_from(None)
    sha = baseline.get("fable_freeze_sha")
    report = {"mode": "deploy", "fable_freeze_sha": sha, "violations": hash_drift(baseline)}
    if not sha or sha == "PENDING":
        report["violations"].append("fable_freeze_sha is PENDING; nothing is frozen yet")
        return finish(report)
    for path in sorted(baseline.get("protected_file_hashes", {})):
        want = subprocess.run(["git", "rev-parse", f"{sha}:{path}"], capture_output=True, text=True)
        have = subprocess.run(["git", "rev-parse", f"HEAD:{path}"], capture_output=True, text=True)
        if want.returncode != 0:
            report["violations"].append(f"{path}: absent at freeze sha {sha[:12]}")
        elif have.returncode != 0 or want.stdout != have.stdout:
            report["violations"].append(f"{path}: blob differs from freeze sha {sha[:12]}")
    return finish(report)


# ---------------------------------------------------------------- freeze

def cmd_freeze(args) -> int:
    baseline = load_baseline_from(None)
    tracked = git("ls-files").splitlines()
    hashes = {}
    for path in tracked:
        if path == BASELINE:
            continue  # cannot hash itself
        if any_match(path, baseline["protected_paths"]) and Path(path).is_file():
            hashes[path] = sha256_file(Path(path))
    baseline["protected_file_hashes"] = dict(sorted(hashes.items()))
    baseline["fable_freeze_sha"] = args.sha
    Path(BASELINE).write_text(json.dumps(baseline, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({"mode": "freeze", "files_hashed": len(hashes), "fable_freeze_sha": args.sha}, indent=2))
    return 0


def finish(report: dict) -> int:
    report["ok"] = not report["violations"]
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("strict"); s.add_argument("--base", required=True)
    s.add_argument("--task-id"); s.add_argument("--branch")
    a = sub.add_parser("anti-dup"); a.add_argument("--base", required=True)
    sub.add_parser("self")
    sub.add_parser("deploy")
    f = sub.add_parser("freeze"); f.add_argument("--sha", required=True)
    args = ap.parse_args(argv)
    return {"strict": cmd_strict, "anti-dup": cmd_anti_dup, "self": cmd_self,
            "deploy": cmd_deploy, "freeze": cmd_freeze}[args.mode](args)


if __name__ == "__main__":
    sys.exit(main())
