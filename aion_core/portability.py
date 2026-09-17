"""Move a shared brain between hosts: `aion export` / `aion import`.

Reuses aion_core.backup's WAL-safe snapshot instead of a second copy
routine -- this is a manifest wrapper around a backup archive, not a
parallel backup system.  private_state (and therefore every secret) is
excluded exactly the same way backup.create() already excludes it: this
module never touches that directory at all.
"""
from __future__ import annotations

import json
import platform
import shutil
import tarfile
import tempfile
from pathlib import Path

from . import backup, config, util

FORMAT = "lucyos-export-v1"


class PortabilityError(Exception):
    pass


def export(dest: Path | None = None) -> Path:
    """Write a portable archive of canonical state, with a manifest that
    records schema version, a content hash of the database, and the source
    host.  Contains no absolute paths and no private_state."""
    root = config.home()
    backup_path = backup.create()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(tmp_path, filter="data")
        except TypeError:  # Python < 3.12 has no filter kwarg
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(tmp_path)

        db_file = tmp_path / "state" / "aion.sqlite3"
        if not db_file.exists():
            raise PortabilityError("backup produced no database to export")
        content_hash = util.sha256_file(db_file)

        manifest = {
            "format": FORMAT,
            "schema_version": config.SCHEMA_VERSION,
            "source_host": platform.node(),
            "exported_at": util.now(),
            "content_hash": content_hash,
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2))

        dest_dir = root / "EXPORTS"
        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = util.now().replace(":", "").replace("-", "")
        dest = dest or (dest_dir / f"lucyos-export-{stamp}.tar.gz")
        dest.parent.mkdir(parents=True, exist_ok=True)

        with tarfile.open(dest, "w:gz") as tar:
            for member in sorted(tmp_path.rglob("*")):
                if member.is_file():
                    arcname = member.relative_to(tmp_path).as_posix()
                    tar.add(member, arcname=arcname)

    return dest


def import_(archive: Path) -> dict:
    """Verify the manifest and restore into the current AION_HOME.  Refuses
    a schema version it does not understand, and refuses an archive whose
    database does not match the hash its own manifest declares -- both are
    "do not guess" refusals, not best-effort recoveries."""
    from . import db  # local import: avoid import-time cycle with cli.py

    archive = Path(archive)
    root = config.home()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(tmp_path, filter="data")
        except TypeError:
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(tmp_path)

        manifest_file = tmp_path / "manifest.json"
        if not manifest_file.exists():
            raise PortabilityError(f"{archive.name}: no manifest.json -- not a LucyOS export")
        manifest = json.loads(manifest_file.read_text())

        if manifest.get("schema_version") != config.SCHEMA_VERSION:
            raise PortabilityError(
                f"{archive.name}: schema_version {manifest.get('schema_version')!r} is not "
                f"one this build understands (expects {config.SCHEMA_VERSION}); refusing to guess"
            )

        db_file = tmp_path / "state" / "aion.sqlite3"
        if not db_file.exists():
            raise PortabilityError(f"{archive.name}: manifest present but no database in archive")

        actual_hash = util.sha256_file(db_file)
        if actual_hash != manifest.get("content_hash"):
            raise PortabilityError(
                f"{archive.name}: content hash mismatch (manifest says "
                f"{manifest.get('content_hash')!r}, archive has {actual_hash!r}) -- "
                "archive is tampered or corrupt, refusing import"
            )

        db.close()
        target_db = config.db_path()
        target_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_file, target_db)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(target_db) + suffix)
            if sidecar.exists():
                sidecar.unlink()

        for name in config.DOCS:
            f = tmp_path / name
            if f.is_file():
                dest_f = root / name
                dest_f.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest_f)
        for sub in ("MEMORY", "APPROVALS", "AGENTS", "FABLE", "METRICS", "FINANCE"):
            d = tmp_path / sub
            if d.is_dir():
                dest_d = root / sub
                if dest_d.exists():
                    shutil.rmtree(dest_d)
                shutil.copytree(d, dest_d)

    conn = db.connect()
    tasks_n = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    mem_n = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
    db.log_event("aion", "portability.import", archive.name,
                 f"schema={manifest['schema_version']}, {tasks_n} tasks, {mem_n} memories")
    return {
        "ok": True,
        "schema_version": manifest["schema_version"],
        "source_host": manifest.get("source_host", ""),
        "imported_at": util.now(),
        "tasks": tasks_n,
        "memories": mem_n,
    }
