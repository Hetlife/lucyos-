"""Backups of the canonical state, with a real restore test.

A backup that has never been restored is an assumption, not a backup, so
`verify()` actually extracts the archive to a temp dir and opens the database.

Encryption (optional): if a BACKUP_PASSPHRASE secret is configured, the
archive is encrypted before it touches disk.  LucyOS is stdlib-only, so this
is not AES -- it is an HMAC-SHA256 keystream (encrypt) plus a separate
HMAC-SHA256 tag over salt+nonce+ciphertext (authenticate), i.e. an
encrypt-then-MAC construction built entirely from `hmac`/`hashlib`.  A wrong
passphrase or a tampered archive fails the MAC check and is refused outright
-- it never produces a corrupt "success". With no passphrase configured,
backups are unencrypted exactly as before, and say so in their log line.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import tarfile
import tempfile
from pathlib import Path

from . import config, db, util

KEEP = 14
PASSPHRASE_SECRET_NAME = "BACKUP_PASSPHRASE"

_ENCRYPTED_MAGIC = b"LUCYOSENC1"
_SALT_LEN = 16
_NONCE_LEN = 16
_TAG_LEN = 32  # sha256 digest size
_PBKDF2_ITERATIONS = 200_000


class BackupError(Exception):
    pass


def _read_secret(name: str) -> str | None:
    """Read one KEY=value line from the 0600 secret store.  Never logs or
    returns the value except to the caller that asked for it by name."""
    sf = config.secrets_file()
    if not sf.exists():
        return None
    prefix = f"{name}="
    for line in sf.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            return value or None
    return None


def _derive_keys(passphrase: bytes, salt: bytes) -> tuple[bytes, bytes]:
    material = hashlib.pbkdf2_hmac("sha256", passphrase, salt, _PBKDF2_ITERATIONS, dklen=64)
    return material[:32], material[32:]  # encryption key, MAC key


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(out[:length])


def _xor(data: bytes, keystream: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, keystream))


def encrypt_bytes(data: bytes, passphrase: str) -> bytes:
    salt = secrets.token_bytes(_SALT_LEN)
    nonce = secrets.token_bytes(_NONCE_LEN)
    enc_key, mac_key = _derive_keys(passphrase.encode("utf-8"), salt)
    ciphertext = _xor(data, _keystream(enc_key, nonce, len(data)))
    tag = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    return _ENCRYPTED_MAGIC + salt + nonce + tag + ciphertext


def decrypt_bytes(blob: bytes, passphrase: str) -> bytes:
    if not blob.startswith(_ENCRYPTED_MAGIC):
        raise BackupError("not a LucyOS-encrypted backup (missing magic header)")
    rest = blob[len(_ENCRYPTED_MAGIC):]
    if len(rest) < _SALT_LEN + _NONCE_LEN + _TAG_LEN:
        raise BackupError("encrypted backup is truncated")
    salt, rest = rest[:_SALT_LEN], rest[_SALT_LEN:]
    nonce, rest = rest[:_NONCE_LEN], rest[_NONCE_LEN:]
    tag, ciphertext = rest[:_TAG_LEN], rest[_TAG_LEN:]
    enc_key, mac_key = _derive_keys(passphrase.encode("utf-8"), salt)
    expected_tag = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise BackupError("wrong passphrase or corrupted backup -- refusing to decrypt")
    return _xor(ciphertext, _keystream(enc_key, nonce, len(ciphertext)))


def is_encrypted(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(len(_ENCRYPTED_MAGIC)) == _ENCRYPTED_MAGIC


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

    passphrase = _read_secret(PASSPHRASE_SECRET_NAME)
    if passphrase:
        raw = dest.read_bytes()
        dest.write_bytes(encrypt_bytes(raw, passphrase))
        encrypted_note = "encrypted"
    else:
        encrypted_note = f"unencrypted (no {PASSPHRASE_SECRET_NAME} configured)"

    _prune(dest_dir)
    db.log_event("aion", "backup.create", dest.name,
                 f"{round(dest.stat().st_size / 1024, 1)} KB, {encrypted_note}")
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
        archive_path = path
        if is_encrypted(path):
            passphrase = _read_secret(PASSPHRASE_SECRET_NAME)
            if not passphrase:
                return {"ok": False,
                        "detail": f"{path.name} is encrypted but no {PASSPHRASE_SECRET_NAME} is configured"}
            try:
                plaintext = decrypt_bytes(path.read_bytes(), passphrase)
            except BackupError as exc:
                return {"ok": False, "detail": f"{path.name}: {exc}"}
            archive_path = Path(tmp) / "decrypted.tar.gz"
            archive_path.write_bytes(plaintext)
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(tmp, filter="data")
        except TypeError:  # Python < 3.12 has no filter kwarg
            with tarfile.open(archive_path, "r:gz") as tar:
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
