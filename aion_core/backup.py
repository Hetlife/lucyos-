"""Backups of the canonical state, with a real restore test.

A backup that has never been restored is an assumption, not a backup, so
`verify()` actually extracts the archive to a temp dir and opens the database.
"""
from __future__ import annotations

import sqlite3
import tarfile
import tempfile
from pathlib import Path

from . import config, db, util

KEEP = 14


def create() -> Path:
    root = config.home()
    dest_dir = root / "BACKUPS"
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = util.now().replace(":", "").replace("-", "")
    dest = dest_dir / f"aion-backup-{stamp}.tar.gz"

    # Consistent DB copy even while WAL is active.
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / "aion.sqlite3"
        src = db.connect()
        target = sqlite3.connect(str(snapshot))
        src.backup(target)
        target.close()

        with tarfile.open(dest, "w:gz") as tar:
            tar.add(snapshot, arcname="state/aion.sqlite3")
            for name in config.DOCS:
                f = root / name
                if f.is_file():
                    tar.add(f, arcname=name)
            for sub in ("MEMORY", "APPROVALS", "AGENTS", "FABLE", "METRICS", "FINANCE"):
                d = root / sub
                if d.is_dir():
                    tar.add(d, arcname=sub)
    # private_state is deliberately excluded: secrets never enter an archive
    # that might be copied to a shared drive.
    _prune(dest_dir)
    db.log_event("aion", "backup.create", dest.name,
                 f"{round(dest.stat().st_size / 1024, 1)} KB")
    return dest


def _prune(dest_dir: Path) -> None:
    files = sorted(dest_dir.glob("aion-backup-*.tar.gz"))
    for old in files[:-KEEP]:
        old.unlink()


def verify(path: Path | None = None) -> dict:
    """Restore-test the latest backup into a temp dir and query the database."""
    dest_dir = config.home() / "BACKUPS"
    files = sorted(dest_dir.glob("aion-backup-*.tar.gz"))
    if path is None:
        if not files:
            return {"ok": False, "detail": "no backup exists"}
        path = files[-1]
    with tempfile.TemporaryDirectory() as tmp:
        try:
            with tarfile.open(path, "r:gz") as tar:
                tar.extractall(tmp, filter="data")
        except TypeError:  # Python < 3.12 has no filter kwarg
            with tarfile.open(path, "r:gz") as tar:
                tar.extractall(tmp)
        restored = Path(tmp) / "state" / "aion.sqlite3"
        if not restored.exists():
            return {"ok": False, "detail": f"{path.name} has no database"}
        conn = sqlite3.connect(str(restored))
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tasks_n = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            mem_n = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        finally:
            conn.close()
    ok = integrity == "ok"
    db.log_event("aion", "backup.verify", path.name, f"integrity={integrity}")
    return {"ok": ok, "backup": path.name, "integrity": integrity,
            "tasks": tasks_n, "memories": mem_n,
            "detail": f"restored {path.name}: integrity={integrity}, {tasks_n} tasks, {mem_n} memories"}
