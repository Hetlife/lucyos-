#!/usr/bin/env python3
"""Duplication and dead-weight advisory scanner for LucyOS (S-42).

Read-only, advisory. This script never edits, deletes, or moves anything --
it only reports candidates for a human to review. It is not a CI gate like
`verify_authority.py` or `check_portability.py`; it always exits 0 on a
completed scan (2 on a usage/IO error) because a finding here is a lead, not
a failure.

What it looks for, all heuristic and all explained in its own output:

  1. Duplicate function bodies -- functions whose *normalized* AST body
     (source locations ignored; leading docstring stripped) is byte-identical to another
     function's, and whose body spans more than 15 source lines. Short
     helpers are deliberately excluded: a one-line `git(cwd, *args)` wrapper
     repeated across test files is normal test hygiene, not debt.

  2. Repeated retry/backoff, health-check, and validation "shapes" -- a
     function-*name* pattern (not literal duplication) that recurs across
     two or more distinct files in aion_core/bridges/scripts. This is a
     weaker, name-based signal meant to surface candidates for consolidation
     even when the implementations have since diverged.

  3. Dead-weight module candidates -- a first-party .py file under
     aion_core/bridges/scripts that has, simultaneously: zero Python
     importers anywhere in the repo, no reference inside the CLI/entrypoint
     surface (aion_core/cli.py, the `aion` launcher, scripts/*.sh, the CI
     workflow), no reference inside any tests/test_*.py file, and no
     reference inside any *.json manifest, anything under .lucy/**, or any
     docs/**/*.md file. All four must be negative for a file to be listed;
     any single reference excludes it.

  4. Dead links and superseded planning docs -- markdown link targets
     (`[text](path)`) that resolve to nothing on disk, plus planning
     documents that are either self-declared superseded (a `# SUPERSEDED`
     heading), listed in
     the KNOWN_STALE_PLANNING_DOCS registry below for cases the generic
     heuristics cannot derive on their own (mirrors the KNOWN_EXCEPTIONS
     pattern in scripts/check_portability.py: a maintained, shrinking list of
     known facts, not a substitute for detection).

Scope for 1-3 is aion_core/, bridges/, scripts/ (production and tooling
code); dead links and superseded docs are scanned repo-wide over *.md.

Usage: python3 scripts/duplication_scan.py [--json] [--write-evidence DIR]
Exit status: 0 = scan completed (findings or not), 2 = usage/IO error.
Standard library only, like the rest of LucyOS.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PRODUCTION_ROOTS = ("aion_core", "bridges", "scripts")
MIN_DUPLICATE_BODY_LINES = 15

NAME_SHAPE_PATTERNS = {
    "retry_backoff": re.compile(r"(retry|backoff)", re.IGNORECASE),
    "health_check": re.compile(r"health.?check", re.IGNORECASE),
    "validation": re.compile(r"^validate_|_validate$|^is_valid|^check_valid", re.IGNORECASE),
}

# Cases the generic superseded-doc heuristics below cannot derive on their
# own -- either nothing textually declares them superseded (they were
# overtaken by later owner action, e.g. a freeze commit landing after the
# doc was written) or the derivation would require comparing commit SHAs
# across time, which is out of scope for a stdlib text scan. Each entry
# names why. This list should shrink as docs are retired or as detection
# improves to cover a case generically -- same discipline as
# check_portability.py's KNOWN_EXCEPTIONS.
KNOWN_STALE_PLANNING_DOCS = {
    ".lucy/planning/INTEGRATION_ROADMAP_20260917.md":
        "Roadmap V1 names integration/consolidation-20260916 as target and main as "
        "destination; inverted once main was frozen as the candidate.",
    ".lucy/planning/INTEGRATION_ROADMAP_V2_20260917.md":
        "Roadmap V2; self-declares superseded at its own tail (also caught generically).",
    ".lucy/planning/OPUS_ROADMAP_REVISION_PROMPT_20260917.md":
        "One-shot planning prompt for the V2 revision pass; the pass it requested is done "
        "and its own inputs (roadmap V1, integration branch as ground truth) are stale.",
    ".lucy/planning/CANONICAL_BRANCH.md":
        "Named origin/main frozen at 0720a920 as canonical; overtaken by later owner "
        "freezes (e.g. 'owner: freeze reconciled governance baseline', "
        "'owner: freeze governed MSOS candidate') with no update recorded here.",
}

SUPERSEDED_HEADING = re.compile(r"^#{1,6}\s*SUPERSEDED\b", re.IGNORECASE | re.MULTILINE)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def relpath(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


# ---------------------------------------------------------------- file walks

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
             "private_state", "secrets", ".ssh", "browser", "oauth"}
REPORT_NAMES = {"duplication_report.md", "dead_weight_candidates.md"}


def scan_files(base: Path):
    """Never follow symlinks or inspect private state or our own reports."""
    if base.is_symlink():
        return
    for directory, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.lower() not in SKIP_DIRS
                         and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if not path.is_symlink() and name not in REPORT_NAMES:
                yield path


def python_files(roots) -> list[Path]:
    return sorted(p for root in roots for p in scan_files(REPO / root)
                  if p.suffix == ".py")


def module_candidates(roots=PRODUCTION_ROOTS) -> list[Path]:
    return [p for p in python_files(roots) if p.name != "__init__.py"]


def markdown_files(root: Path | None = None) -> list[Path]:
    return sorted(p for p in scan_files(root or REPO) if p.suffix == ".md")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _concat_texts(paths) -> str:
    return "\n".join(_read(p) for p in paths)


# ------------------------------------------------------ AST body comparison

def iter_function_defs(tree: ast.AST):
    """Yield (qualname, node) for every def/async def, nested or not, with a
    dotted qualname reflecting its enclosing classes/functions."""
    stack: list[str] = []
    results: list[tuple[str, ast.AST]] = []

    def walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                stack.append(child.name)
                results.append((".".join(stack), child))
                walk(child)
                stack.pop()
            elif isinstance(child, ast.ClassDef):
                stack.append(child.name)
                walk(child)
                stack.pop()
            else:
                walk(child)

    walk(tree)
    return results


def _strip_docstring(body: list[ast.AST]) -> list[ast.AST]:
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def body_signature(node: ast.AST) -> str | None:
    clone = copy.deepcopy(node)
    clone.body = _strip_docstring(clone.body)
    if not clone.body:
        return None
    return "\n".join(ast.dump(stmt, annotate_fields=False) for stmt in clone.body)


def body_line_count(node: ast.AST) -> int:
    body = _strip_docstring(node.body)
    if not body:
        return 0
    start = body[0].lineno
    end = max(getattr(stmt, "end_lineno", stmt.lineno) for stmt in body)
    return end - start + 1


def find_duplicate_functions(files: list[Path],
                              min_lines: int = MIN_DUPLICATE_BODY_LINES) -> list[list[dict]]:
    groups: dict[str, list[dict]] = {}
    for path in files:
        rel = relpath(path)
        text = _read(path)
        if not text:
            continue
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            continue
        for qualname, node in iter_function_defs(tree):
            line_count = body_line_count(node)
            if line_count <= min_lines:
                continue
            sig = body_signature(node)
            if sig is None:
                continue
            # Standalone stdlib tool: avoid importing the application runtime.
            key = hashlib.sha256(sig.encode("utf-8")).hexdigest()
            groups.setdefault(key, []).append({
                "file": rel, "function": qualname,
                "lineno": node.lineno, "line_count": line_count,
            })
    duplicate_groups = [locs for locs in groups.values() if len(locs) > 1]
    duplicate_groups.sort(key=lambda g: (-len(g), -g[0]["line_count"]))
    for group in duplicate_groups:
        group.sort(key=lambda e: (e["file"], e["lineno"]))
    return duplicate_groups


def find_name_pattern_shapes(files: list[Path]) -> dict[str, list[dict]]:
    hits: dict[str, list[dict]] = {cat: [] for cat in NAME_SHAPE_PATTERNS}
    for path in files:
        rel = relpath(path)
        text = _read(path)
        if not text:
            continue
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            continue
        for qualname, node in iter_function_defs(tree):
            for cat, pattern in NAME_SHAPE_PATTERNS.items():
                if pattern.search(node.name):
                    hits[cat].append({"file": rel, "function": qualname, "lineno": node.lineno})
    repeated = {}
    for cat, entries in hits.items():
        files_involved = {e["file"] for e in entries}
        if len(files_involved) >= 2:
            entries.sort(key=lambda e: (e["file"], e["lineno"]))
            repeated[cat] = entries
    return repeated


# --------------------------------------------------------- dead-weight scan

def imported_module_stems(path: Path) -> set[str]:
    text = _read(path)
    if not text:
        return set()
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return set()
    stems = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                stems.add(alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                stems.add(node.module.split(".")[-1])
            for alias in node.names:
                stems.add(alias.name)
    return stems


def build_import_index(all_files: list[Path]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for f in all_files:
        rel = relpath(f)
        for stem in imported_module_stems(f):
            index.setdefault(stem, set()).add(rel)
    return index


def _cli_corpus() -> str:
    texts = []
    for rel in ("aion_core/cli.py", "aion", ".github/workflows/lucyos-ci.yml",
                "scripts/pre-commit"):
        p = REPO / rel
        if p.is_file() and not p.is_symlink():
            texts.append(_read(p))
    scripts_dir = REPO / "scripts"
    if scripts_dir.is_dir():
        texts.extend(_read(p) for p in sorted(scripts_dir.glob("*.sh"))
                     if not p.is_symlink())
    return "\n".join(texts)


def _tests_corpus() -> str:
    tests_dir = REPO / "tests"
    if not tests_dir.is_dir():
        return ""
    return _concat_texts((p for p in scan_files(tests_dir) if p.suffix == ".py"))


def _manifest_corpus() -> str:
    return _concat_texts(p for p in scan_files(REPO) if p.suffix == ".json")


def _lucy_corpus() -> str:
    lucy_dir = REPO / ".lucy"
    if not lucy_dir.is_dir():
        return ""
    return _concat_texts(scan_files(lucy_dir))


def _docs_corpus() -> str:
    docs_dir = REPO / "docs"
    if not docs_dir.is_dir():
        return ""
    return _concat_texts(markdown_files(docs_dir))


def dead_weight_modules(roots=PRODUCTION_ROOTS) -> list[dict]:
    all_files = [p for p in scan_files(REPO) if p.suffix == ".py"]
    import_index = build_import_index(all_files)
    cli_corpus = _cli_corpus()
    tests_corpus = _tests_corpus()
    manifest_corpus = _manifest_corpus()
    lucy_corpus = _lucy_corpus()
    docs_corpus = _docs_corpus()

    results = []
    for target in module_candidates(roots):
        stem = target.stem
        rel = relpath(target)
        word = re.compile(rf"\b{re.escape(stem)}\b")
        importers = import_index.get(stem, set()) - {rel}

        zero_importers = not importers
        no_cli_wiring = word.search(cli_corpus) is None
        no_test_import = not (
            any(i.startswith("tests/") for i in importers)
            or word.search(tests_corpus) is not None
        )
        no_manifest_doc_reference = not (
            word.search(manifest_corpus) is not None
            or word.search(lucy_corpus) is not None
            or word.search(docs_corpus) is not None
        )
        results.append({
            "file": rel,
            "zero_importers": zero_importers,
            "no_cli_wiring": no_cli_wiring,
            "no_test_import": no_test_import,
            "no_manifest_doc_reference": no_manifest_doc_reference,
            "importers": sorted(importers),
            "candidate": zero_importers and no_cli_wiring and no_test_import
            and no_manifest_doc_reference,
        })
    results.sort(key=lambda r: r["file"])
    return results


# --------------------------------------------------- dead links / superseded

def find_dead_links(root: Path | None = None) -> tuple[int, list[dict]]:
    checked = 0
    dead = []
    for path in markdown_files(root):
        text = _read(path)
        for m in MARKDOWN_LINK.finditer(text):
            target = m.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#", "data:", "tel:")):
                continue
            raw = target.split("#", 1)[0]
            if not raw:
                continue
            resolved = (path.parent / raw).resolve()
            checked += 1
            if not resolved.exists():
                dead.append({"doc": relpath(path), "link": target})
    dead.sort(key=lambda d: (d["doc"], d["link"]))
    return checked, dead


def find_superseded_docs(root: Path | None = None) -> list[dict]:
    base = root or REPO
    findings: dict[str, dict] = {}

    def add(rel: str, reason: str) -> None:
        row = findings.setdefault(rel, {"file": rel, "reasons": []})
        if reason not in row["reasons"]:
            row["reasons"].append(reason)

    for path in markdown_files(base):
        text = _read(path)
        if not text:
            continue
        rel = relpath(path)
        if SUPERSEDED_HEADING.search(text):
            add(rel, "self-declared SUPERSEDED heading")
    for rel, reason in KNOWN_STALE_PLANNING_DOCS.items():
        if (REPO / rel).is_file():
            add(rel, f"task-card ground truth: {reason}")

    return sorted(findings.values(), key=lambda r: r["file"])


# --------------------------------------------------------------- orchestrate

def run_scan(roots=PRODUCTION_ROOTS) -> dict:
    files = python_files(roots)
    checked_links, dead_links = find_dead_links()
    return {
        "scanned_python_files": len(files),
        "duplicate_functions": find_duplicate_functions(files),
        "name_pattern_shapes": find_name_pattern_shapes(files),
        "dead_weight_modules": dead_weight_modules(roots),
        "dead_links": {"checked": checked_links, "findings": dead_links},
        "superseded_docs": find_superseded_docs(),
    }


# ------------------------------------------------------------------ render

def render_text(report: dict) -> str:
    lines = ["LucyOS duplication / dead-weight scan (advisory, reports only)", ""]
    lines.append(f"Scanned {report['scanned_python_files']} Python files under "
                 f"{', '.join(PRODUCTION_ROOTS)}/")
    lines.append("")

    lines.append(f"== Duplicate function bodies (>{MIN_DUPLICATE_BODY_LINES} lines) ==")
    if not report["duplicate_functions"]:
        lines.append("none found")
    for group in report["duplicate_functions"]:
        lines.append(f"- {len(group)} identical copies, {group[0]['line_count']} lines:")
        for loc in group:
            lines.append(f"    {loc['file']}:{loc['lineno']} {loc['function']}")
    lines.append("")

    lines.append("== Repeated retry/backoff, health-check, validation shapes (by name) ==")
    if not report["name_pattern_shapes"]:
        lines.append("none found")
    for cat, entries in report["name_pattern_shapes"].items():
        files_involved = sorted({e["file"] for e in entries})
        lines.append(f"- {cat}: {len(entries)} functions across {len(files_involved)} files")
        for e in entries:
            lines.append(f"    {e['file']}:{e['lineno']} {e['function']}")
    lines.append("")

    lines.append("== Dead-weight module candidates ==")
    candidates = [m for m in report["dead_weight_modules"] if m["candidate"]]
    if not candidates:
        lines.append("none found")
    for m in candidates:
        lines.append(f"- {m['file']}")
        lines.append("    [no importers] zero other .py files import this module")
        lines.append("    [no CLI wiring] not referenced in the CLI/entrypoint surface")
        lines.append("    [no test import] no tests/test_*.py references it")
        lines.append("    [no manifest/doc reference] absent from *.json, .lucy/**, docs/**")
    lines.append("")

    lines.append("== Dead links ==")
    lines.append(f"checked {report['dead_links']['checked']} relative markdown links")
    if not report["dead_links"]["findings"]:
        lines.append("none found")
    for d in report["dead_links"]["findings"]:
        lines.append(f"- {d['doc']}: broken link -> {d['link']}")
    lines.append("")

    lines.append("== Superseded planning docs ==")
    if not report["superseded_docs"]:
        lines.append("none found")
    for d in report["superseded_docs"]:
        lines.append(f"- {d['file']}")
        for reason in d["reasons"]:
            lines.append(f"    {reason}")

    return "\n".join(lines) + "\n"


def render_duplication_markdown(report: dict) -> str:
    out = ["# Duplication scan report (S-42)", "",
           "Advisory evidence from `scripts/duplication_scan.py`. Reports only; "
           "nothing was deleted or modified by generating this file.", "",
           f"Scanned {report['scanned_python_files']} Python files under "
           f"`{'`, `'.join(PRODUCTION_ROOTS)}`.", "",
           "## Duplicate function bodies", "",
           f"Functions whose normalized AST body (source locations ignored, "
           f"docstring stripped) is identical to another function's, and whose "
           f"body spans more than {MIN_DUPLICATE_BODY_LINES} lines.", ""]
    if not report["duplicate_functions"]:
        out.append("None found.")
    else:
        for group in report["duplicate_functions"]:
            out.append(f"- **{len(group)} identical copies** ({group[0]['line_count']} lines):")
            for loc in group:
                out.append(f"  - `{loc['file']}:{loc['lineno']}` `{loc['function']}`")
    out.append("")

    out.append("## Repeated retry/backoff, health-check, validation shapes")
    out.append("")
    out.append("Name-pattern signal: the same functional category implemented by name "
               "in two or more distinct files. Not literal duplication -- a candidate "
               "list for a human to judge whether consolidation is warranted.")
    out.append("")
    if not report["name_pattern_shapes"]:
        out.append("None found.")
    else:
        for cat, entries in report["name_pattern_shapes"].items():
            files_involved = sorted({e["file"] for e in entries})
            out.append(f"- **{cat}**: {len(entries)} functions across {len(files_involved)} "
                       f"files ({', '.join(f'`{f}`' for f in files_involved)})")
            for e in entries:
                out.append(f"  - `{e['file']}:{e['lineno']}` `{e['function']}`")
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def render_dead_weight_markdown(report: dict) -> str:
    out = ["# Dead-weight candidates report (S-42)", "",
           "Advisory evidence from `scripts/duplication_scan.py`. Reports only; "
           "nothing was deleted or modified by generating this file.", "",
           "## Dead-weight module candidates", "",
           "A module is listed only when all four checks below are negative -- any "
           "single reference (an importer, CLI wiring, a test, or a manifest/doc "
           "mention) excludes it.", ""]
    candidates = [m for m in report["dead_weight_modules"] if m["candidate"]]
    if not candidates:
        out.append("None found.")
    else:
        for m in candidates:
            out.append(f"- `{m['file']}` — [no importers] [no CLI wiring] "
                       "[no test import] [no manifest/.lucy/docs reference]")
            out.append("")

    out.append("## Dead links")
    out.append("")
    out.append(f"Checked {report['dead_links']['checked']} relative markdown link targets "
               f"repo-wide for `[text](path)` links that resolve to nothing on disk.")
    out.append("")
    if not report["dead_links"]["findings"]:
        out.append("None found.")
    else:
        for d in report["dead_links"]["findings"]:
            out.append(f"- `{d['doc']}`: broken link -> `{d['link']}`")

    out.append("")

    out.append("## Superseded planning docs")
    out.append("")
    out.append("Self-declared (a `# SUPERSEDED` heading), or listed by the task card in "
               "`KNOWN_STALE_PLANNING_DOCS` for cases the "
               "generic heuristics cannot derive on their own.")
    out.append("")
    if not report["superseded_docs"]:
        out.append("None found.")
    else:
        for d in report["superseded_docs"]:
            out.append(f"- `{d['file']}`")
            for reason in d["reasons"]:
                out.append(f"  - {reason}")

    return "\n".join(out).rstrip() + "\n"


def main(argv=None) -> int:
    global REPO
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--write-evidence", metavar="DIR",
                    help="write duplication_report.md and dead_weight_candidates.md into DIR")
    ap.add_argument("--root", type=Path, default=REPO, help="tree to scan")
    args = ap.parse_args(argv)
    REPO = args.root.resolve()

    try:
        if not REPO.is_dir():
            raise OSError(f"scan root is not a directory: {REPO}")
        report = run_scan()
        if args.write_evidence:
            out_dir = Path(args.write_evidence)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "duplication_report.md").write_text(
                render_duplication_markdown(report), encoding="utf-8")
            (out_dir / "dead_weight_candidates.md").write_text(
                render_dead_weight_markdown(report), encoding="utf-8")
    except OSError as exc:
        print(f"scan error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
