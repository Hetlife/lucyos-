#!/usr/bin/env python3
"""Rebuild derived navigation indexes from tracked LucyOS files; no source writes."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def domain(path):
    name = path.name
    stem = path.stem
    if path.parts[0] == "bridges": return "interfaces"
    if path.parts[0] == "integrations": return "openclaw-integration"
    if path.parts[0] == "aion_core":
        if stem in {"db", "config", "bootstrap", "backup", "portability", "util"}: return "state"
        if stem in {"tasks", "plan", "worker", "agents", "tempworker", "autonomy", "sessions"}: return "execution"
        if stem in {"router", "api", "cli", "reports", "handoff", "resume", "packets", "notebook"}: return "control"
        if stem in {"governor", "model_gateway", "usage_telemetry", "platform_resolver", "fable"}: return "models"
        if stem in {"memory", "context", "semantic_recall", "recall"} or "recall" in path.parts: return "memory-context"
        if stem in {"security", "approvals", "guardian", "architecture", "skills"}: return "authority-security"
        if stem in {"health", "errors", "metrics"}: return "observability"
        if stem in {"learnrepo", "seed", "experiments", "money_path", "milestones", "deliveries", "intake", "sync_outbox", "owner_setup"}: return "operations"
        if "host" in path.parts: return "host-adapters"
    if path.parts[0] == "scripts": return "operations"
    return "other"

def imports(tree, path):
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and path.parts[0] == "aion_core":
                if node.module:
                    result.add("aion_core." + node.module.split(".")[0])
                else:
                    result.update("aion_core." + alias.name.split(".")[0] for alias in node.names)
            elif node.module and node.module.startswith(("aion_core", "bridges")):
                result.add(node.module)
                if node.module == "aion_core":
                    result.update("aion_core." + alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names if alias.name.startswith(("aion_core", "bridges")))
    return sorted(result)

def symbols(tree):
    result = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            result.append({"symbol": node.name, "line": node.lineno, "kind": "function"})
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            result.append({"symbol": node.name, "line": node.lineno, "kind": "class"})
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                    result.append({"symbol": node.name + "." + child.name, "line": child.lineno, "kind": "method"})
    return result

def main():
    tracked = [Path(p) for p in git("ls-files").splitlines()]
    source_dirs = {"aion_core", "bridges", "scripts"}
    py = [p for p in tracked if p.suffix == ".py" and p.parts[0] in source_dirs]
    tests = [p for p in tracked if p.parts[0] == "tests" and p.name.startswith("test_") and p.suffix == ".py"]
    counts = Counter((p.suffix.lower() or "[no extension]") for p in tracked)
    category = Counter(p.parts[0] if len(p.parts)>1 else "[root]" for p in tracked)
    lines = sum(len((ROOT / p).read_text(encoding="utf-8", errors="replace").splitlines()) for p in py)
    baseline = {"repository": "lucyos-", "root": str(ROOT), "branch": git("branch", "--show-current"),
                "commit": git("rev-parse", "HEAD"), "preexisting_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
                "tracked_file_count": len(tracked), "tracked_python_source_files": len(py),
                "approx_python_source_loc": lines, "generated_at_utc": datetime.now(timezone.utc).isoformat()}
    write("baseline.json", baseline)
    write("inventory.json", {"baseline_commit": baseline["commit"], "by_extension": dict(counts),
                             "by_top_level": dict(category), "tracked_paths": [str(p) for p in tracked]})
    modules = {}
    for path in py:
        text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        try: tree = ast.parse(text, filename=str(path))
        except SyntaxError: continue
        key = ".".join(path.with_suffix("").parts)
        modules[key] = {"path": str(path), "subsystem": domain(path), "language": "Python",
                        "sha256": hashlib.sha256(text.encode()).hexdigest(), "loc": len(text.splitlines()),
                        "imports": imports(tree, path), "symbols": symbols(tree)}
    for key, item in modules.items():
        item["imported_by"] = sorted(source["path"] for source in modules.values() if key in source["imports"])
        stem = Path(item["path"]).stem
        item["candidate_tests"] = sorted(str(t) for t in tests if stem in t.stem or stem in (ROOT / t).read_text(encoding="utf-8", errors="replace"))
        item["risk"] = "critical" if stem in {"db", "security", "approvals", "worker", "router", "model_gateway", "config", "backup"} else "review"
    write("FILE_INDEX.json", {"commit": baseline["commit"], "note": "candidate_tests are lexical candidates, not coverage proof", "files": list(modules.values())})
    syms = []
    for item in modules.values():
        for symbol in item["symbols"]:
            if symbol["kind"] == "method" and symbol["symbol"].split(".")[-1] in {"__init__", "main"}: continue
            syms.append({**symbol, "file": item["path"], "subsystem": item["subsystem"], "tests": item["candidate_tests"][:8]})
    write("SYMBOL_INDEX.json", {"commit": baseline["commit"], "symbols": syms})
    edges = [{"from": item["path"], "to": modules[target]["path"], "kind": "import"}
             for item in modules.values() for target in item["imports"] if target in modules]
    write("dependency_graph.json", {"commit": baseline["commit"], "edges": edges,
                                   "scope": "static Python imports; dynamic calls and shell edges are documented separately"})
    write("test_map.json", {"commit": baseline["commit"], "tests": [
        {"path": str(t), "candidate_source_files": sorted(item["path"] for item in modules.values() if str(t) in item["candidate_tests"])}
        for t in tests], "note": "lexical candidates require live source verification"})
    write("REPO_INTELLIGENCE.json", {"repository": "lucyos-", "commit": baseline["commit"],
          "generated_at_utc": baseline["generated_at_utc"], "entry_points": ["aion", "bridges/whatsapp_bridge.py", "bridges/http_server.py"],
          "index_files": ["baseline.json", "inventory.json", "FILE_INDEX.json", "SYMBOL_INDEX.json", "dependency_graph.json", "test_map.json"],
          "route_first": ["AI_START_HERE.md", "AI_TASK_ROUTER.md"],
          "source_of_truth": "tracked source at commit; verify live source and hashes before changes"})
    print(f"indexed {len(tracked)} tracked files, {len(modules)} Python source modules, {len(syms)} symbols, {len(edges)} import edges")

if __name__ == "__main__": main()
