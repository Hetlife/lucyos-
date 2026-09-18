"""Offline deterministic context proxy; supply reference-commit paths via --files.

One import hop is anchored to the touched set (never a transitive closure).
Tests importing the expanded set are then added. Documentation includes
START_HERE's explicit file routes and the routes in docs/README.md, not every
cross-reference in the resulting documents. All non-Python context is counted
as docs/instructions; tokens are only a byte-count approximation.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import re


EXCLUDED = {".git", "private_state", "secrets", ".ssh", "browser", "oauth",
            "__pycache__", ".venv", "venv", "node_modules"}
DOC_SUFFIXES = {".md", ".txt", ".json"}


def local_path(root: Path, name: str) -> Path:
    path = root / name
    if (Path(name).is_absolute() or ".." in Path(name).parts
            or any(part.lower() in EXCLUDED for part in Path(name).parts)
            or any(parent.is_symlink() for parent in (path, *path.parents) if parent != root)
            or not path.resolve().is_relative_to(root)):
        raise ValueError(f"not a safe repository file: {name}")
    return path


def python_files(root: Path) -> list[str]:
    found = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.lower() not in EXCLUDED
                         and not d.startswith(".") and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            if name.endswith(".py"):
                rel = (Path(directory) / name).relative_to(root).as_posix()
                local_path(root, rel)
                found.append(rel)
    return sorted(found)


def import_graph(root: Path) -> dict[str, set[str]]:
    paths = python_files(root)
    modules = {p.removesuffix(".py").replace("/", ".").removesuffix(".__init__"): p
               for p in paths}
    graph = {}
    for path in paths:
        module = path.removesuffix(".py").replace("/", ".")
        package = module.split(".")[:-1]
        targets = set()
        for node in ast.walk(ast.parse(local_path(root, path).read_bytes(), filename=path)):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                prefix = package[:len(package) - node.level + 1] if node.level else []
                base = ".".join(prefix + ([node.module] if node.module else []))
                names = [base] + [f"{base}.{alias.name}" if base else alias.name
                                  for alias in node.names]
            for name in names:
                if name in modules:
                    targets.add(modules[name])
        graph[path] = targets - {path}
    return graph


def routed_docs(root: Path) -> list[str]:
    selected = set()
    for router in ("START_HERE.md", "docs/README.md"):
        if router != "START_HERE.md" and router not in selected:
            continue
        path = local_path(root, router)
        if not path.is_file():
            continue
        selected.add(router)
        text = path.read_text(encoding="utf-8")
        refs = re.findall(r"`([^`\n]+)`|\]\(([^)\s]+)\)", text)
        for inline, link in refs:
            name = (inline or link).split("#", 1)[0]
            if Path(name).suffix.lower() not in DOC_SUFFIXES:
                continue
            # Root-qualified routes in START_HERE; relative routes in docs/README.
            for candidate in (str(Path(router).parent / name), name):
                try:
                    target = local_path(root, candidate)
                except ValueError:
                    continue
                if target.is_file():
                    selected.add(target.relative_to(root).as_posix())
                    break
    return sorted(selected)


def profile(root: Path, touched: list[str]) -> dict:
    root = root.resolve()
    seeds = set(touched)
    for name in seeds:
        if not local_path(root, name).is_file():
            raise ValueError(f"touched file missing from measurement tree: {name}")
    graph = import_graph(root)
    expanded = seeds | {target for path in seeds for target in graph.get(path, ())}
    expanded |= {path for path, targets in graph.items() if targets & seeds}
    tests = {path for path, targets in graph.items()
             if path.startswith("tests/") and targets & expanded}
    docs = routed_docs(root)
    files = sorted(expanded | tests | set(docs))
    contents = {path: local_path(root, path).read_bytes() for path in files}
    lines = {path: len(data.splitlines()) for path, data in contents.items()}
    return {"touched_files": sorted(seeds), "files": files, "file_count": len(files),
            "source_loc": sum(lines[p] for p in files if p.endswith(".py")),
            "docs_loc": sum(lines[p] for p in files if not p.endswith(".py")),
            "governance_files": docs, "governance_loc": sum(lines[p] for p in docs),
            "bytes": sum(map(len, contents.values())),
            "approx_tokens": sum(map(len, contents.values())) / 4}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--files", nargs="+", required=True, help="repository-relative touched files")
    args = parser.parse_args(argv)
    try:
        result = profile(args.root, args.files)
    except (OSError, ValueError, SyntaxError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
