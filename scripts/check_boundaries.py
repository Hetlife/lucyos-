#!/usr/bin/env python3
"""Warning-mode import and state-boundary ratchet for LucyOS."""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARCH = REPO / ".lucy" / "architecture" / "modules"
BASELINE = REPO / ".lucy" / "authority" / "HIGH_MODEL_BASELINE.json"
ROOTS = ("aion_core", "bridges", "scripts", "integrations")
KNOWN_EXCEPTIONS: dict[str, str] = {}


def _manifests() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ARCH.glob("*.json"))]


def _owner_map() -> dict[str, str]:
    owners = {}
    for manifest in _manifests():
        for pattern in manifest["owned_files"]:
            for path in REPO.glob(pattern):
                if path.is_file():
                    owners[path.relative_to(REPO).as_posix()] = manifest["module"]
    return owners


def _module_for_import(name: str, owners: dict[str, str]) -> str | None:
    if not name.startswith("aion_core."):
        return None
    path = "aion_core/" + name.split(".", 1)[1].replace(".", "/") + ".py"
    if path in owners:
        return owners[path]
    parts = name.split(".")
    for end in range(len(parts), 1, -1):
        candidate = "/".join(parts[:end]) + ".py"
        if candidate in owners:
            return owners[candidate]
    return None


def _files() -> list[Path]:
    return sorted(p for root in ROOTS for p in (REPO / root).rglob("*.py")
                  if "__pycache__" not in p.parts)


def findings() -> list[dict]:
    owners = _owner_map()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    sqlite_allowed = set(baseline.get("sqlite_connect_allowed", []))
    sqlite_allowed.update(baseline.get("derived_sqlite_allowed", []))
    out = []
    for path in _files():
        rel = path.relative_to(REPO).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            out.append({"path": rel, "rule": "syntax", "line": exc.lineno or 0,
                        "detail": str(exc)})
            continue
        importer = owners.get(rel)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name in {"aion_core.host.linux", "aion_core.host.macos"} and rel != "aion_core/host/__init__.py":
                    out.append({"path": rel, "rule": "host_import", "line": node.lineno,
                                "detail": f"direct host implementation import: {name}"})
                target = _module_for_import(name, owners)
                if importer and target and target != importer:
                    manifest = next((m for m in _manifests() if m["module"] == importer), None)
                    if manifest and target not in manifest["allowed_dependencies"]:
                        out.append({"path": rel, "rule": "dependency", "line": node.lineno,
                                    "detail": f"{importer} imports {target} ({name})"})
                if name == "sqlite3" and rel not in sqlite_allowed:
                    out.append({"path": rel, "rule": "sqlite_import", "line": node.lineno,
                                "detail": "sqlite3 import outside the ratified allowlist"})
    return out


def _exception_key(item: dict) -> str:
    return f"{item['path']}::{item['rule']}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    raw = findings()
    exceptions = []
    violations = []
    for item in raw:
        key = _exception_key(item)
        if key in KNOWN_EXCEPTIONS:
            exceptions.append({**item, "task": KNOWN_EXCEPTIONS[key]})
        else:
            violations.append(item)
    stale = sorted(set(KNOWN_EXCEPTIONS) - {_exception_key(x) for x in raw})
    result = {"violations": violations, "exceptions": exceptions, "stale_exceptions": stale,
              "strict": args.strict, "ok": not violations and not stale}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for item in violations:
            print(f"{item['path']}:{item['line']} [{item['rule']}] {item['detail']}")
        print(f"boundary scan: {len(violations)} violation(s), {len(exceptions)} known, "
              f"{len(stale)} stale; mode={'strict' if args.strict else 'warning'}")
    report = REPO / "evidence" / "boundary_report.md"
    report.parent.mkdir(exist_ok=True)
    report.write_text("# Boundary scan\n\n" + json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 1 if args.strict and (violations or stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
