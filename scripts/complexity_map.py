#!/usr/bin/env python3
"""Write deterministic AST metrics for Python production sources (stdlib only)."""
from __future__ import annotations

import argparse
import ast
import json
import tokenize
from pathlib import Path

SOURCE_ROOTS = ("aion_core", "bridges", "integrations", "scripts")


def cycles_for(graph):
    """Return DFS back-edge cycles, not every possible elementary cycle."""
    done, active, stack, cycles = set(), set(), [], []

    def visit(node):
        active.add(node)
        stack.append(node)
        for target in sorted(graph[node]):
            if target in active:
                cycles.append(stack[stack.index(target):] + [target])
            elif target not in done:
                visit(target)
        stack.pop()
        active.remove(node)
        done.add(node)

    for node in sorted(graph):
        if node not in done:
            visit(node)
    return cycles


def functions_for(tree):
    result = []

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            name = prefix
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + child.name + "."
                if not isinstance(child, ast.ClassDef):
                    result.append({"name": name[:-1], "line": child.lineno,
                                   "loc": child.end_lineno - child.lineno + 1})
            visit(child, name)

    visit(tree)
    return result


def collect(root):
    paths = sorted(path for folder in SOURCE_ROOTS
                   for path in (root / folder).rglob("*.py")
                   if not any(part.startswith(".") or part == "__pycache__"
                              for part in path.relative_to(root).parts)
                   and not path.is_symlink()
                   and root.resolve() in path.resolve().parents)
    modules, trees, packages = {}, {}, {}
    for path in paths:
        relative = path.relative_to(root)
        parts = list(relative.with_suffix("").parts)
        is_package = parts[-1] == "__init__"
        if is_package:
            parts.pop()
        name = ".".join(parts)
        with tokenize.open(path) as stream:
            source = stream.read()
        tree = ast.parse(source, filename=relative.as_posix())
        functions = functions_for(tree)
        modules[name] = {"path": relative.as_posix(), "loc": len(source.splitlines()),
                         "functions": functions,
                         "functions_over_120": [f for f in functions if f["loc"] > 120],
                         "classes": sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))}
        trees[name] = tree
        packages[name] = parts if is_package else parts[:-1]
    graph = {name: set() for name in modules}
    for name, tree in trees.items():
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    package = packages[name]
                    if node.level > len(package):
                        continue
                    base = ".".join(package[:len(package) - node.level + 1]
                                    + ([base] if base else []))
                # A named submodule is more precise than its containing package.
                targets = [base + "." + alias.name
                           if base + "." + alias.name in modules else base
                           for alias in node.names]
            graph[name].update(target for target in targets if target in modules)
    for name, module in modules.items():
        module["imports_out"] = sorted(graph[name])
        module["importers_in"] = sorted(src for src in graph if name in graph[src])
    return modules, graph


def render_hotspots(modules, cycles):
    lines = ["# Complexity hotspots", "",
             "Scope: Python files under aion_core, bridges, integrations and scripts; "
             "tests excluded. Package __init__.py files count as modules.", "",
             "LOC counts physical lines. Function length spans def through its final "
             "statement (including nested definitions, excluding decorators). "
             "Imports include conditional and function-local imports; fan-in/out count "
             "distinct internal modules, not external libraries or dynamic imports. "
             "Named submodules resolve before package attributes. Self-imports are retained.", "",
             f"Production modules: {len(modules)}. DFS back-edge cycles: {len(cycles)}.", "",
             "Cycles use sorted DFS roots and neighbors and list each back edge once; "
             "this is not enumeration of all elementary cycles. Counts can differ from "
             "the ad hoc 67-module / 14-cycle baseline as scripts are added or traversal "
             "and import-resolution conventions differ.", ""]
    for title, key in (("LOC", "loc"), ("Fan-in", "importers_in"), ("Fan-out", "imports_out")):
        values = [(name, row[key] if key == "loc" else len(row[key]))
                  for name, row in modules.items()]
        lines.extend([f"## Top 12 by {title}", ""])
        lines.extend(f"- `{name}`: {value}" for name, value in
                     sorted(values, key=lambda item: (-item[1], item[0]))[:12])
        lines.append("")
    functions = [(name + "." + f["name"], f["loc"]) for name, row in modules.items()
                 for f in row["functions"]]
    lines.extend(["## Top 12 by function length", ""])
    lines.extend(f"- `{name}`: {length}" for name, length in
                 sorted(functions, key=lambda item: (-item[1], item[0]))[:12])
    lines.extend(["", "## Cycles", ""])
    lines.extend("- " + " → ".join(f"`{name}`" for name in cycle) for cycle in cycles)
    if not cycles:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error("--root must be an existing directory")
    try:
        modules, graph = collect(args.root)
        cycles = cycles_for(graph)
        args.out.mkdir(parents=True, exist_ok=True)
        reports = {"complexity_map.json": {"modules": modules},
                   "dependency_graph.json": {
                       "edges": [[src, dst] for src in sorted(graph) for dst in sorted(graph[src])],
                       "cycles": cycles}}
        for filename, report in reports.items():
            (args.out / filename).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
        (args.out / "hotspots.md").write_text(render_hotspots(modules, cycles), encoding="utf-8")
    except (OSError, SyntaxError, UnicodeError) as exc:
        parser.exit(1, f"complexity map: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
