#!/usr/bin/env python3
"""Cross-platform portability guard for LucyOS core.

Owner invariant (2026-09-16): LucyOS is ONE codebase that runs on macOS and
Linux without forking core logic. OS-specific concerns live behind a small
host-adapter layer; core/domain/AION logic must not reach past it.

This guard makes that invariant machine-checkable instead of aspirational.
It is a RATCHET:

  * A file in the scanned scope that gains platform coupling FAILS the build.
  * `KNOWN_EXCEPTIONS` lists couplings that predate the invariant. Each entry
    names the task that must remove it. The list may only shrink.
  * A stale exception -- an entry whose coupling is gone -- ALSO fails, so the
    list cannot rot into a permanent excuse. Remove the entry with the fix.

Scope: `aion_core/**` and `bridges/**`, excluding the host-adapter package
(`aion_core/host/**`), which exists precisely to hold this knowledge.

What counts as coupling:
  * naming an init system (systemd/systemctl/launchd/launchctl/journalctl)
  * branching on the operating system (sys.platform, platform.system(),
    os.uname, platform.mac_ver, platform.win32_ver)
  * OS-specific absolute paths (/etc, /usr, /opt, /var, /Library,
    /Applications, /System, C:\\, %APPDATA%)
  * package managers that only exist on one platform (brew, apt-get, dpkg,
    yum, dnf, pacman)

What does NOT count (deliberately allowed anywhere):
  * `platform.node()` -- hostname/identity, not an OS branch
  * `os.name`, `pathlib`, `os.path`, `tempfile`, `Path.home()` -- these are
    the portable abstractions we WANT core to use
  * anything inside a string that is plainly a URL path or an API route
  * platform names inside statically proven rejection-only security policy
    containers; if such values are propagated/executed, they count again

Exit status: 0 = portable, 1 = violation, 2 = usage error.
Standard library only, like the rest of LucyOS.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SCAN_ROOTS = ("aion_core", "bridges")
# The host-adapter layer is the one place allowed to know about platforms.
EXEMPT_PREFIXES = ("aion_core/host/",)

# (rule_id, compiled pattern, human explanation)
RULES = [
    ("init_system", re.compile(r"\b(systemd|systemctl|launchd|launchctl|journalctl)\b", re.I),
     "names an init system; belongs in aion_core/host/"),
    ("os_branch", re.compile(r"\bsys\.platform\b|\bplatform\.system\s*\(|\bos\.uname\s*\(|"
                             r"\bplatform\.mac_ver\s*\(|\bplatform\.win32_ver\s*\("),
     "branches on the operating system; ask aion_core/host instead"),
    ("os_path", re.compile(r"""["'](?:/etc/|/usr/|/opt/|/var/|/Library/|/Applications/|/System/)"""
                           r"""|["'][A-Za-z]:\\\\|%APPDATA%"""),
     "hard-codes an OS-specific absolute path"),
    ("pkg_manager", re.compile(r"\b(?:brew|apt-get|dpkg|yum|dnf|pacman)\b"),
     "invokes a platform-specific package manager"),
]

# Couplings that predate the invariant. Each MUST name the task that removes it.
# This list may only shrink. Format: "path::rule_id": "owning task id".
#
# learnrepo.py maps platform -> scheduler name inline (scheduler_kind).
# drive_bridge.py asks systemd whether the exchange timer is running; on macOS
# that call raises, is swallowed, and the readiness report then claims "not
# active" even when the launchd equivalent IS running -- a wrong answer, not a
# graceful degrade. Both move behind aion_core/host (S-10) by S-11 and S-12,
# which hold task-scoped overrides permitting them to delete their own entry.
KNOWN_EXCEPTIONS = {
    "aion_core/learnrepo.py::init_system": "S-11",
    "aion_core/learnrepo.py::os_branch": "S-11",
    "bridges/drive_bridge.py::init_system": "S-12",
}


def scanned_files() -> list[Path]:
    out = []
    for root in SCAN_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(REPO).as_posix()
            if any(rel.startswith(p) for p in EXEMPT_PREFIXES):
                continue
            if "__pycache__" in rel:
                continue
            out.append(path)
    return out


def strip_noise(line: str) -> str:
    """Drop comment tails and obvious URLs so prose about portability, and API
    routes like '/api/money', don't register as platform coupling."""
    line = re.sub(r"https?://\S+", "", line)
    hash_at = line.find("#")
    if hash_at != -1:
        line = line[:hash_at]
    return line


# Defensive policy data may legitimately name commands that core is explicitly
# refusing to execute. Keep the scanner conservative: only mask string literals
# that are statically inside a clearly negative-policy assignment. Everything
# else remains subject to the existing raw coupling rules.
_INERT_POLICY_NAME = re.compile(
    r"(?:forbid|deny|denied|block|disallow|prohibit|reject|blacklist)", re.I)
_LITERAL_RULES = {"init_system", "pkg_manager"}


def _assigned_names(node: ast.AST) -> list[str]:
    targets = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    out = []
    for target in targets:
        if isinstance(target, ast.Name):
            out.append(target.id)
    return out


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _under(node: ast.AST, kind: type[ast.AST], parents: dict[ast.AST, ast.AST],
           stop: ast.AST) -> bool:
    cur = node
    while cur is not stop and cur in parents:
        cur = parents[cur]
        if isinstance(cur, kind):
            return True
    return False


def _defensive_for_use(loop: ast.For, parents: dict[ast.AST, ast.AST]) -> bool:
    """True only for rejection loops, never loops that execute policy entries."""
    if not isinstance(loop.target, ast.Name):
        return False
    item = loop.target.id
    has_raise = any(isinstance(n, ast.Raise) for stmt in loop.body for n in ast.walk(stmt))
    if not has_raise:
        return False
    for stmt in loop.body:
        for node in ast.walk(stmt):
            if not (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == item):
                continue
            if _under(node, ast.Raise, parents, loop):
                continue
            parent = parents.get(node)
            if isinstance(parent, ast.Compare):
                continue
            # Any other use (especially a call argument) may execute or propagate
            # the denied value, so keep the original portability finding.
            return False
    return True


def _defensive_comprehension_use(comp: ast.comprehension,
                                   parents: dict[ast.AST, ast.AST]) -> bool:
    if not isinstance(comp.target, ast.Name):
        return False
    item = comp.target.id
    root: ast.AST = comp
    while root in parents and not isinstance(root, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
        root = parents[root]
    if not isinstance(root, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
        return False
    for node in ast.walk(root):
        if not (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == item):
            continue
        if isinstance(parents.get(node), ast.Compare):
            continue
        return False
    return True


def _policy_binding_is_defensive(tree: ast.AST, name: str,
                                  parents: dict[ast.AST, ast.AST]) -> bool:
    loads = [n for n in ast.walk(tree)
             if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == name]
    for load in loads:
        parent = parents.get(load)
        if isinstance(parent, ast.For) and parent.iter is load:
            if _defensive_for_use(parent, parents):
                continue
            return False
        if isinstance(parent, ast.comprehension) and parent.iter is load:
            if _defensive_comprehension_use(parent, parents):
                continue
            return False
        if isinstance(parent, ast.Compare):
            # Direct membership checks are defensive only when the surrounding
            # branch rejects by raising.
            cur = parent
            enclosing_if = None
            while cur in parents:
                cur = parents[cur]
                if isinstance(cur, ast.If):
                    enclosing_if = cur
                    break
            if enclosing_if and any(isinstance(n, ast.Raise)
                                    for stmt in enclosing_if.body for n in ast.walk(stmt)):
                continue
        return False
    return True


def inert_policy_string_spans(text: str) -> dict[int, list[tuple[int, int]]]:
    """Return spans for literals proven to be defensive rejection policy data.

    Naming alone is insufficient: a FORBIDDEN list passed to subprocess would
    still be real coupling. A candidate binding is masked only when all of its
    uses are statically rejection-only (or it is unused).
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    parents = _parent_map(tree)
    spans: dict[int, list[tuple[int, int]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        names = [name for name in _assigned_names(node) if _INERT_POLICY_NAME.search(name)]
        if not names or not all(_policy_binding_is_defensive(tree, name, parents) for name in names):
            continue
        value = node.value
        if value is None:
            continue
        for child in ast.walk(value):
            if not (isinstance(child, ast.Constant) and isinstance(child.value, str)):
                continue
            if not all(hasattr(child, a) for a in ("lineno", "col_offset", "end_lineno", "end_col_offset")):
                continue
            if child.lineno == child.end_lineno:
                spans.setdefault(child.lineno, []).append((child.col_offset, child.end_col_offset))
            else:
                for line_no in range(child.lineno, child.end_lineno + 1):
                    start = child.col_offset if line_no == child.lineno else 0
                    end = child.end_col_offset if line_no == child.end_lineno else 10**9
                    spans.setdefault(line_no, []).append((start, end))
    return spans


def _mask_columns(line: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return line
    chars = list(line)
    for start, end in spans:
        for i in range(max(0, start), min(len(chars), end)):
            chars[i] = " "
    return "".join(chars)


def findings_for(path: Path) -> list[dict]:
    rel = path.relative_to(REPO).as_posix()
    found = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [{"file": rel, "rule": "unreadable", "line": 0,
                 "detail": f"could not read: {exc}"}]
    inert_spans = inert_policy_string_spans(text)
    in_docstring = False
    for number, raw in enumerate(text.splitlines(), start=1):
        # Skip docstrings: documenting the invariant is not violating it.
        # Complete same-line triple-quoted spans are removed first, because a
        # one-line docstring carries TWO triple quotes and would otherwise look
        # like "not a docstring" to the odd/even toggle below.
        work = re.sub(r'""".*?"""', " ", raw)
        work = re.sub(r"'''.*?'''", " ", work)
        triples = work.count('"""') + work.count("'''")
        if in_docstring:
            if triples % 2 == 1:
                in_docstring = False
            continue
        if triples % 2 == 1:
            in_docstring = True
            continue
        line = strip_noise(work)
        if not line.strip():
            continue
        masked_line = strip_noise(_mask_columns(raw, inert_spans.get(number, [])))
        for rule_id, pattern, explanation in RULES:
            scan_line = masked_line if rule_id in _LITERAL_RULES else line
            if pattern.search(scan_line):
                found.append({"file": rel, "rule": rule_id, "line": number,
                              "detail": explanation, "text": scan_line.strip()[:120]})
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    all_findings = []
    for path in scanned_files():
        all_findings.extend(findings_for(path))

    violations, excused, seen_keys = [], [], set()
    for f in all_findings:
        key = f"{f['file']}::{f['rule']}"
        seen_keys.add(key)
        if key in KNOWN_EXCEPTIONS:
            f["excused_by_task"] = KNOWN_EXCEPTIONS[key]
            excused.append(f)
        else:
            violations.append(f)

    stale = sorted(set(KNOWN_EXCEPTIONS) - seen_keys)
    report = {
        "scanned_files": len(scanned_files()),
        "violations": violations,
        "excused": excused,
        "stale_exceptions": stale,
        "ok": not violations and not stale,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for f in violations:
            print(f"FAIL {f['file']}:{f['line']} [{f['rule']}] {f['detail']}")
            if f.get("text"):
                print(f"       {f['text']}")
        for f in excused:
            print(f"note {f['file']}:{f['line']} [{f['rule']}] "
                  f"known, owned by task {f['excused_by_task']}")
        for key in stale:
            print(f"FAIL stale exception {key!r}: the coupling is gone -- delete this "
                  f"entry from KNOWN_EXCEPTIONS (it may only shrink)")
        print(f"\n{len(violations)} violation(s), {len(excused)} known exception(s), "
              f"{len(stale)} stale, across {report['scanned_files']} files")
        print("portable" if report["ok"] else "NOT portable")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
