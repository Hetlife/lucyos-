#!/usr/bin/env python3
"""Sync project evidence packets from a project's git repo into LucyOS.

money_path.py marks a step DONE only when a file exists inside this tree. A
project's work-order packets are written in the project's own repo (for
strategy-factory: `.autonomous/capital_engine/EVIDENCE/*.md`), so this copies
them into `PROJECTS/<id>/evidence/` where the checks look. Deterministic, no
model, no network beyond `git`.

For each PROJECTS/<id>/project.json with a "repos" list:
  1. shallow-clone (or `git pull --ff-only`) into $AION_HOME/PROJECTS/<id>/repo
  2. copy <repo>/.autonomous/capital_engine/EVIDENCE/*.md -> PROJECTS/<id>/evidence/
     only when the content changed
  3. REFUSE any packet in which aion_core.security finds credential-shaped
     content (printed as a WARNING, never copied)

One line per file: COPIED / SKIPPED (unchanged) / REFUSED.
Exit 0 on success (refusals are reported, not failures); 1 on any git failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from aion_core import security  # noqa: E402  (reuse the one scanner; never a second one)

EVIDENCE_SUBDIR = Path(".autonomous") / "capital_engine" / "EVIDENCE"
# Only https GitHub shorthand, https URLs, or an absolute local path (tests/mirrors).
_SHORTHAND = re.compile(r"^(?:https://)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def aion_home() -> Path:
    try:
        from aion_core import config
        return config.home()
    except Exception:  # config is optional here; same default as aion_core.config
        return Path(os.environ.get("AION_HOME", Path.home() / ".aion")).expanduser()


def projects_root() -> Path:
    # Same root money_path resolves against (aion_core.experiments.root()).
    env = os.environ.get("AION_PROJECTS_DIR")
    return Path(env).expanduser() if env else REPO / "PROJECTS"


def clone_url(entry: str) -> str | None:
    """github.com/<owner>/<repo> -> https URL. None if the entry is not allowed."""
    m = _SHORTHAND.match(entry.strip())
    if m:
        return f"https://github.com/{m.group(1)}/{m.group(2)}"
    if entry.startswith("/"):  # absolute local path: a bare mirror, used by tests
        return entry
    return None


def git(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="https:file")
    return subprocess.run(["git", *args], capture_output=True, text=True, env=env, check=False)


def update_clone(url: str, dest: Path, branch: str | None) -> str | None:
    """Clone or fast-forward. Returns an error string, or None on success."""
    if (dest / ".git").exists():
        r = git("-C", str(dest), "pull", "--ff-only")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["clone", "--depth", "1"] + (["--branch", branch] if branch else []) + [url, str(dest)]
        r = git(*cmd)
    return None if r.returncode == 0 else (r.stderr.strip() or r.stdout.strip() or "git failed")


def sync_packets(src_dir: Path, out_dir: Path, dry_run: bool) -> list[str]:
    lines = []
    if not src_dir.is_dir():
        return [f"  NO PACKETS  {src_dir} (directory absent)"]
    for src in sorted(src_dir.glob("*.md")):
        if src.is_symlink() or not src.is_file():  # a symlink could point outside the clone
            lines.append(f"  REFUSED     {src.name} (not a regular file)")
            continue
        data = src.read_bytes()
        findings = security.scan_text(data.decode("utf-8", errors="replace"))
        if findings:
            kinds = ", ".join(sorted({f["kind"] for f in findings}))
            lines.append(f"  REFUSED     {src.name} (WARNING: credential-shaped content: {kinds})")
            continue
        dest = out_dir / src.name
        if dest.is_file() and dest.read_bytes() == data:
            lines.append(f"  SKIPPED     {src.name} (unchanged)")
            continue
        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        lines.append(f"  {'WOULD COPY' if dry_run else 'COPIED    '}  {src.name}")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="report what would be copied; copy nothing")
    ap.add_argument("--branch", help="branch to clone (default: the repo's default branch)")
    args = ap.parse_args(argv)

    failed = False
    for pj in sorted(projects_root().glob("*/project.json")):
        try:
            doc = json.loads(pj.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{pj.parent.name}: cannot read project.json: {exc}", file=sys.stderr)
            failed = True
            continue
        repos = doc.get("repos") or []
        pid = pj.parent.name
        if not repos:
            continue
        print(f"{pid}:")
        for entry in repos:
            url = clone_url(str(entry))
            if url is None:
                print(f"  WARNING: repo entry {entry!r} not allowed (need github.com/<owner>/<repo>)",
                      file=sys.stderr)
                failed = True
                continue
            dest = aion_home() / "PROJECTS" / pid / "repo"
            err = update_clone(url, dest, args.branch)
            if err:
                print(f"  GIT FAILED  {entry}: {err}", file=sys.stderr)
                failed = True
                continue
            for line in sync_packets(dest / EVIDENCE_SUBDIR, pj.parent / "evidence", args.dry_run):
                print(line)
            break  # one repo per project holds the packets; first that works wins
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
