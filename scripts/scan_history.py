#!/usr/bin/env python3
"""Read-only scan of every blob ever committed to this repository's history.

`./aion scan .` only sees the working tree. A secret committed once and later
deleted still lives in git history and, on a public repository, is still
public. This walks every blob git has ever stored and runs it through the
same `aion_core.security.scan_text` patterns `./aion scan .` uses -- so a
finding here means the same thing a working-tree finding means.

Read-only: this script never writes, rewrites, or deletes anything in the
repository. It never prints a matched value -- only `scan_text`'s own
`preview` (already masked), plus the commit and path.

Usage: python3 scripts/scan_history.py [--json]
Exit status: 0 = clean, 1 = findings, 2 = usage/git error.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aion_core import security

# Matches scan_paths()'s own extension/dir exclusions so history scanning and
# working-tree scanning stay consistent -- binary/lock/generated files are not
# useful secret-scan targets and are a waste of the walk.
SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
                 ".zip", ".tar", ".gz", ".sqlite3", ".sqlite3-wal", ".sqlite3-shm"}


def iter_all_blobs(cwd=None):
    """Yield (blob_sha, path) for every file ever stored, across all history.

    Uses `git rev-list --objects --all` to get every (blob, path) pairing
    without checking anything out -- the working tree and the repository
    state are never touched. `cwd` selects which repository to scan (defaults
    to the process's own); this is what makes the function testable against a
    throwaway repo instead of only this one.
    """
    rev_list = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        capture_output=True, text=True, check=True, cwd=cwd)
    seen_blobs = set()
    for line in rev_list.stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue  # a commit/tree line with no path
        sha, path = parts
        if not path or sha in seen_blobs:
            continue
        seen_blobs.add(sha)
        yield sha, path


def owning_commit(path: str, cwd=None) -> str:
    """First commit that added this path, across all branches.

    `git log` is asked directly rather than cross-referencing every commit's
    tree, which would be O(commits x files). One commit is enough evidence to
    act on; a finding is about the blob's content, not every commit that ever
    carried it.
    """
    out = subprocess.run(
        ["git", "log", "--all", "--format=%H", "--follow", "-1",
         "--diff-filter=A", "--", path],
        capture_output=True, text=True, cwd=cwd)
    return out.stdout.strip() or "unknown"


def scan_history(cwd=None) -> list[dict]:
    findings: list[dict] = []
    for blob_sha, path in iter_all_blobs(cwd=cwd):
        if any(path.lower().endswith(suf) for suf in SKIP_SUFFIXES):
            continue
        cat = subprocess.run(["git", "cat-file", "-p", blob_sha],
                             capture_output=True, cwd=cwd)
        try:
            text = cat.stdout.decode("utf-8")
        except UnicodeDecodeError:
            continue  # binary blob; not a text-secret scan target
        for finding in security.scan_text(text):
            findings.append({
                "path": path,
                "blob": blob_sha,
                "commit": owning_commit(path, cwd=cwd),
                **finding,
            })
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        findings = scan_history(cwd=None)
    except subprocess.CalledProcessError as exc:
        print(f"git error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"findings": findings, "clean": not findings}, indent=2))
    else:
        for f in findings:
            print(f"{f['commit'][:12]} {f['path']} [{f['kind']}] line {f['line']}: {f['preview']}")
        print(f"\n{len(findings)} finding(s)")
        print("clean" if not findings else "FINDINGS -- see above; never rotate/report the value itself, only this report")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
