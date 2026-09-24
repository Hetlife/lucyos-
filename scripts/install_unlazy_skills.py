#!/usr/bin/env python3
"""Install/check LucyOS's pinned Unlazy skill without network access."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "vendor" / "unlazy"
TARGETS = {
    "claude": Path.home() / ".claude" / "skills" / "unlazy",
    "codex": Path.home() / ".codex" / "skills" / "unlazy",
}


def digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix().encode()
        h.update(len(rel).to_bytes(4, "big")); h.update(rel)
        data = path.read_bytes()
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return h.hexdigest()


def source_meta() -> dict:
    return json.loads((SOURCE / "UPSTREAM.json").read_text())


def status(targets: list[str]) -> dict:
    src_digest = digest(SOURCE)
    out = {"source": source_meta(), "source_digest": src_digest, "targets": {}}
    for name in targets:
        path = TARGETS[name]
        installed = path.is_dir() and (path / "SKILL.md").is_file()
        same = installed and digest(path) == src_digest
        out["targets"][name] = {"path": str(path), "installed": installed, "matches": same}
    out["ok"] = all(x["matches"] for x in out["targets"].values())
    return out


def install_one(name: str) -> None:
    target = TARGETS[name]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and digest(target) == digest(SOURCE):
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = target.with_name(f"unlazy.backup-{stamp}")
    tmp = Path(tempfile.mkdtemp(prefix="unlazy-install-", dir=str(target.parent))) / "unlazy"
    shutil.copytree(SOURCE, tmp)
    if target.exists():
        os.replace(target, backup)
    os.replace(tmp, target)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--target", choices=["claude", "codex", "all"], default="all")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    targets = list(TARGETS) if args.target == "all" else [args.target]
    if args.install:
        for name in targets:
            install_one(name)
    result = status(targets)
    print(json.dumps(result, indent=2 if args.json else None, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
