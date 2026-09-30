#!/usr/bin/env python3
"""Deterministic branch ledger: classify every remote branch against a base.

Replaces the hand-built branch lists (C-3, PR #88) whose three-dot diff silently
misclassified branches with no merge base as "zero diff". Read-only: it never
deletes, merges or pushes. Output is TSV on stdout (or --markdown).

Classes
  CONTAINED     every commit is an ancestor of base            -> safe to delete
  PATCH_IN_BASE ahead > 0 but `git cherry` finds no new patch  -> delete after recording tip
  UNRELATED     no merge base with base (rewritten history)    -> never "zero diff"; keep/tag
  UNIQUE        at least one patch is not in base              -> owner decision
"""
from __future__ import annotations

import argparse
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout.strip()


def classify(base: str, branch: str) -> dict:
    tip = git("rev-parse", "--short", branch)
    date = git("log", "-1", "--format=%cs", branch)
    merge_base = git("merge-base", base, branch)
    if not merge_base:
        files = git("diff", "--name-only", base, branch).count("\n") + 1
        return dict(branch=branch, tip=tip, date=date, cls="UNRELATED", ahead="-",
                    behind="-", new_patches="-", files=str(files))
    ahead = git("rev-list", "--count", f"{base}..{branch}")
    behind = git("rev-list", "--count", f"{branch}..{base}")
    new_patches = sum(1 for line in git("cherry", base, branch).splitlines() if line.startswith("+"))
    files_out = git("diff", "--name-only", f"{base}...{branch}")
    files = len(files_out.splitlines()) if files_out else 0
    if ahead == "0":
        cls = "CONTAINED"
    elif new_patches == 0:
        cls = "PATCH_IN_BASE"
    else:
        cls = "UNIQUE"
    return dict(branch=branch, tip=tip, date=date, cls=cls, ahead=ahead, behind=behind,
                new_patches=str(new_patches), files=str(files))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default="origin/main")
    p.add_argument("--remote", default="origin")
    p.add_argument("--markdown", action="store_true")
    args = p.parse_args(argv)
    refs = [r.strip() for r in git("branch", "-r", "--format=%(refname:short)").splitlines()]
    refs = [r for r in refs if r.startswith(args.remote + "/") and r != args.base and not r.endswith("/HEAD")]
    rows = [classify(args.base, r) for r in refs]
    order = {"UNIQUE": 0, "UNRELATED": 1, "PATCH_IN_BASE": 2, "CONTAINED": 3}
    rows.sort(key=lambda r: (order[r["cls"]], r["branch"]))
    cols = ["branch", "tip", "date", "cls", "ahead", "behind", "new_patches", "files"]
    if args.markdown:
        print("| " + " | ".join(cols) + " |")
        print("|" + "---|" * len(cols))
        for r in rows:
            print("| " + " | ".join(r[c] for c in cols) + " |")
    else:
        print("\t".join(cols))
        for r in rows:
            print("\t".join(r[c] for c in cols))
    counts = {}
    for r in rows:
        counts[r["cls"]] = counts.get(r["cls"], 0) + 1
    print("# base=%s branches=%d %s" % (args.base, len(rows),
          " ".join(f"{k}={v}" for k, v in sorted(counts.items()))), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
