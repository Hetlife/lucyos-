"""TR-2-06: encrypted secrets escrow backup, and ISSUE-048 (no plaintext archive on disk)."""
import os
import stat
import tarfile
import unittest
from unittest import mock

from tests.base import AionTest
from aion_core import backup, bootstrap, config, db

CANARY = "CANARY-SECRET-VALUE-9f3a"
PASS = "correct horse battery"


class SecretsEscrowTest(AionTest):
    def setUp(self):
        super().setUp()
        state = config.home() / "private_state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "secrets.env").write_text(f"SOME_TOKEN={CANARY}\n")

    def test_round_trip_lists_members_without_extracting(self):
        path = backup.secrets_backup(PASS)
        result = backup.secrets_verify(PASS, path)
        self.assertTrue(result["ok"], result)
        self.assertIn("private_state/secrets.env", result["members"])
        self.assertNotIn(CANARY, str(result))
        self.assertEqual(sorted(p.name for p in path.parent.iterdir()), [path.name])

    def test_archive_is_ciphertext_and_mode_0600(self):
        path = backup.secrets_backup(PASS)
        self.assertNotIn(CANARY.encode(), path.read_bytes())
        self.assertTrue(backup.is_encrypted(path))
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_wrong_passphrase_fails_and_leaks_nothing(self):
        path = backup.secrets_backup(PASS)
        result = backup.secrets_verify("not the passphrase", path)
        self.assertFalse(result["ok"])
        self.assertNotIn(CANARY, str(result))

    def test_short_or_empty_passphrase_refused(self):
        for bad in ("", "short"):
            with self.assertRaises(backup.BackupError):
                backup.secrets_backup(bad)
        self.assertFalse((config.home() / "BACKUPS" / "secrets").exists()
                         and any((config.home() / "BACKUPS" / "secrets").iterdir()))

    def test_missing_private_state_refused(self):
        for f in (config.home() / "private_state").iterdir():
            f.unlink()
        with self.assertRaises(backup.BackupError):
            backup.secrets_backup(PASS)

    def test_prune_keeps_seven_and_event_has_no_secret(self):
        dest = config.home() / "BACKUPS" / "secrets"
        dest.mkdir(parents=True)
        for i in range(10):
            (dest / f"secrets-2000010{i}T000000Z.tar.gz.enc").write_bytes(b"x")
        backup.secrets_backup(PASS)
        self.assertEqual(len(list(dest.glob("secrets-*.tar.gz.enc"))), backup.SECRETS_KEEP)
        rows = db.connect().execute("SELECT detail FROM events WHERE kind='backup.secrets'").fetchall()
        self.assertTrue(rows)
        self.assertNotIn(CANARY, " ".join(r[0] or "" for r in rows))

    def test_passphrase_comes_from_env_only_never_the_secret_store(self):
        bootstrap.set_secret("LUCYOS_SECRETS_ESCROW_PASSPHRASE", "stored-on-same-disk")
        with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch("getpass.getpass", return_value="") as prompt:
            os.environ.pop("LUCYOS_SECRETS_ESCROW_PASSPHRASE", None)
            with self.assertRaises(backup.BackupError):
                backup.escrow_passphrase()
            prompt.assert_called_once()
        with mock.patch.dict(os.environ, {"LUCYOS_SECRETS_ESCROW_PASSPHRASE": PASS}):
            self.assertEqual(backup.escrow_passphrase(), PASS)

    def test_encrypted_create_never_writes_a_plaintext_tar(self):
        bootstrap.set_secret(backup.PASSPHRASE_SECRET_NAME, PASS)
        opened = []
        real = tarfile.open

        def spy(name=None, mode="r", fileobj=None, **kw):
            opened.append((name, mode))
            return real(name, mode, fileobj=fileobj, **kw)

        with mock.patch("aion_core.backup.tarfile.open", spy):
            path = backup.create()
        self.assertTrue(backup.is_encrypted(path))
        self.assertTrue(all(name is None for name, mode in opened if "w" in mode), opened)


    def test_existing_permissive_archive_is_preserved_and_refused(self):
        stamp = "2026-10-04T00:00:00+00:00"
        dest = config.home() / "BACKUPS" / "secrets"
        dest.mkdir(parents=True)
        old = dest / "secrets-20261004T000000+0000.tar.gz.enc"
        old.write_bytes(b"previous archive")
        old.chmod(0o644)
        with mock.patch.object(backup.util, "now", return_value=stamp):
            with self.assertRaises(backup.BackupError):
                backup.secrets_backup(PASS)
        self.assertEqual(old.read_bytes(), b"previous archive")
        self.assertEqual(sorted(p.name for p in dest.iterdir()), [old.name])

    def test_symlink_collision_does_not_overwrite_target(self):
        dest = config.home() / "BACKUPS" / "secrets"
        dest.mkdir(parents=True)
        target = config.home() / "unrelated-fixture"
        target.write_bytes(b"untouched")
        link = dest / "secrets-20261004T000000+0000.tar.gz.enc"
        link.symlink_to(target)
        with mock.patch.object(backup.util, "now", return_value="2026-10-04T00:00:00+00:00"):
            with self.assertRaises(backup.BackupError):
                backup.secrets_backup(PASS)
        self.assertEqual(target.read_bytes(), b"untouched")
        self.assertTrue(link.is_symlink())
        self.assertEqual(sorted(p.name for p in dest.iterdir()), [link.name])

    def test_failed_publication_leaves_no_partial_archive(self):
        dest = config.home() / "BACKUPS" / "secrets"
        with mock.patch.object(backup.os, "link", side_effect=OSError("publication failed")):
            with self.assertRaises(OSError):
                backup.secrets_backup(PASS)
        self.assertEqual(list(dest.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
