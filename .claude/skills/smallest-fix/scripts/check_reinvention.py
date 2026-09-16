#!/usr/bin/env python3
"""Flag code that reimplements something aion_core/util.py already provides.

This is the one deterministic, checkable piece of "is it already in the
codebase before you write it" — the step in the decision ladder that a model
skips most often, because writing four new lines feels easier in the moment
than finding the existing helper.

It parses each file with ast (never regex-over-raw-text, which is what
produced the false-positive flood learnrepo hit when screening an unrelated
repo — see docs/architect for that lesson) and looks for a small, specific
set of call shapes that aion_core.util already solves: timestamps, IDs,
hashing, atomic writes, JSON read/write.

This is a lead generator, not a verdict. A flagged call may be the right
choice — a bridge script that must stay import-free of aion_core, a test
fixture that needs the raw stdlib shape, code that runs before util.py's
dependencies are available. Read the flagged line before changing anything.

Usage:
    python3 check_reinvention.py <path>... [--json] [--exempt PATTERN]...

Exit codes: 0 always (this is advisory) · 2 usage/parse error
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}

# The module every rule below points back to. Overridable with --exempt for
# use outside this repo; the rules themselves stay aion_core-specific because
# this skill is written for LucyOS, not as a generic linter.
DEFAULT_EXEMPT = ("aion_core/util.py",)

# Each rule matches the exact dotted name of the function being called
# (node.func, unparsed) — never a raw line and never the full chained-call
# text, so `hashlib.sha256(x).hexdigest()` reports once (for the sha256 call)
# rather than once for that call and again for the chain around it, and a
# mention inside a comment or string literal can never match at all.
#
# `arg_check(node)` is optional: return True to also require something about
# the arguments (used for datetime.now, which is only interesting with a
# timezone.utc argument — datetime.now() with no argument is naive-local
# time, a different bug entirely, not something util.now() replaces).
def _first_arg_is_timezone_utc(node: ast.Call) -> bool:
    return bool(node.args) and ast.unparse(node.args[0]) == "timezone.utc"


RULES = [
    ("timestamp", "datetime.now", _first_arg_is_timezone_utc,
     "util.now() returns the same UTC ISO-8601 string with second precision"),
    ("timestamp", "datetime.utcnow", None,
     "util.now() — datetime.utcnow() is also deprecated upstream"),
    ("id_generation", "uuid.uuid4", None,
     "util.new_id(prefix) gives a shorter, prefixed, still-unique id"),
    ("hashing", "hashlib.sha256", None,
     "util.sha256_text() / util.sha256_file() wrap the chunked-read and hexdigest boilerplate"),
    ("json_io", "json.dump", None,
     "util.write_json() writes atomically (temp file + rename) with sorted, trailing-newline output"),
    ("json_io", "json.load", None,
     "util.read_json() already handles a missing file and malformed JSON with a default"),
]
_RULES_BY_NAME = {name: (category, arg_check, why) for category, name, arg_check, why in RULES}


class Finding(dict):
    pass


def _is_exempt(rel_path: str, exempt: tuple) -> bool:
    norm = rel_path.replace("\\", "/")
    return any(norm.endswith(pattern) for pattern in exempt)


def _iter_python_files(paths: list) -> list:
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_file() and p.suffix == ".py":
            files.append(p)
            continue
        if p.is_dir():
            for candidate in sorted(p.rglob("*.py")):
                if any(part in SKIP_DIRS for part in candidate.parts):
                    continue
                files.append(candidate)
    return files


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def check_file(path: Path, root: Path, exempt: tuple) -> list:
    rel = _display_path(path, root)
    if _is_exempt(rel, exempt):
        return []
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        return [Finding(category="parse_error", file=rel, line=0,
                        call="", why=f"could not parse: {exc}")]

    findings = []
    has_mkstemp = False
    has_os_replace = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        try:
            func_name = ast.unparse(node.func)
        except Exception:  # pragma: no cover - defensive, ast.unparse is stdlib/stable
            continue
        if func_name == "tempfile.mkstemp":
            has_mkstemp = True
        elif func_name == "os.replace":
            has_os_replace = True

        rule = _RULES_BY_NAME.get(func_name)
        if rule is None:
            continue
        category, arg_check, why = rule
        if arg_check is not None and not arg_check(node):
            continue
        try:
            call_text = ast.unparse(node)
        except Exception:  # pragma: no cover
            call_text = func_name + "(...)"
        findings.append(Finding(
            category=category, file=rel, line=node.lineno,
            call=call_text[:100], why=why))

    if has_mkstemp and has_os_replace:
        findings.append(Finding(
            category="atomic_write", file=rel, line=0,
            call="tempfile.mkstemp(...) + os.replace(...)",
            why="util.atomic_write() is the same temp-file-then-rename pattern, already written and tested"))

    return findings


def scan(paths: list, exempt: tuple = DEFAULT_EXEMPT, root: Path | None = None) -> dict:
    root = root or Path.cwd()
    files = _iter_python_files(paths)
    all_findings = []
    for f in files:
        all_findings.extend(check_file(f, root, exempt))
    return {
        "files_scanned": len(files),
        "findings": all_findings,
        "disclaimer": ("Leads, not verdicts. A flagged call may be the right choice for that "
                       "file — read it before changing anything."),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Flag likely reinvention of aion_core.util helpers")
    p.add_argument("paths", nargs="+", help="files or directories to scan")
    p.add_argument("--json", action="store_true")
    p.add_argument("--exempt", action="append", default=[],
                   help="additional path suffix to exempt (repeatable); "
                        f"always exempts {DEFAULT_EXEMPT}")
    args = p.parse_args(argv)

    exempt = tuple(DEFAULT_EXEMPT) + tuple(args.exempt)
    result = scan(args.paths, exempt=exempt)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"scanned {result['files_scanned']} file(s)")
        if not result["findings"]:
            print("no likely reinvention found")
        for f in result["findings"]:
            if f["category"] == "parse_error":
                print(f"  [parse_error] {f['file']}: {f['why']}")
                continue
            print(f"  [{f['category']}] {f['file']}:{f['line']}  {f['call']}")
            print(f"             instead: {f['why']}")
        print(f"\n{result['disclaimer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
