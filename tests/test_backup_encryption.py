"""S-24: optional symmetric encryption of the backup artifact.

Encryption is stdlib-only (HMAC-SHA256 keystream, encrypt-then-MAC) since
LucyOS carries no third-party dependency -- not a substitute for a real
audited cipher, but this test suite proves what it does claim: a wrong
passphrase or tampered archive is refused outright, never silently
"succeeds" with garbage.
"""
import unittest

from tests.base import AionTest
from aion_core import backup, bootstrap, tasks


class BackupEncryptionUnitTest(unittest.TestCase):
    def test_round_trip_recovers_original_bytes(self):
        data = b"the quick brown fox jumps over the lazy dog" * 50
        blob = backup.encrypt_bytes(data, "correct horse battery staple")
        self.assertTrue(blob.startswith(backup._ENCRYPTED_MAGIC))
        recovered = backup.decrypt_bytes(blob, "correct horse battery staple")
        self.assertEqual(recovered, data)

    def test_wrong_passphrase_raises_not_garbage(self):
        data = b"state that must never come back scrambled"
        blob = backup.encrypt_bytes(data, "right passphrase")
        with self.assertRaises(backup.BackupError):
            backup.decrypt_bytes(blob, "wrong passphrase")

    def test_tampered_ciphertext_raises(self):
        data = b"tamper-evident by construction"
        blob = backup.encrypt_bytes(data, "a passphrase")
        tampered = bytearray(blob)
        tampered[-1] ^= 0xFF
        with self.assertRaises(backup.BackupError):
            backup.decrypt_bytes(bytes(tampered), "a passphrase")

    def test_two_encryptions_of_same_data_differ(self):
        data = b"same plaintext, different salt and nonce each time"
        a = backup.encrypt_bytes(data, "pw")
        b = backup.encrypt_bytes(data, "pw")
        self.assertNotEqual(a, b)

    def test_is_encrypted_detects_magic_header(self):
        data = b"x" * 100
        with self.assertRaises(backup.BackupError):
            backup.decrypt_bytes(data, "pw")  # plain bytes: no magic header


class BackupEncryptionIntegrationTest(AionTest):
    def _seed(self):
        tasks.create("encrypted backup seed task")
        from aion_core import db
        db.connect().commit()

    def test_encrypted_backup_round_trips_through_verify(self):
        bootstrap.set_secret(backup.PASSPHRASE_SECRET_NAME, "a real drill passphrase")
        self._seed()

        path = backup.create()
        self.assertTrue(backup.is_encrypted(path))

        result = backup.verify(path)
        self.assertTrue(result["ok"], f"encrypted backup did not verify: {result}")

    def test_wrong_passphrase_fails_verify_cleanly(self):
        bootstrap.set_secret(backup.PASSPHRASE_SECRET_NAME, "the real one")
        self._seed()
        path = backup.create()

        bootstrap.set_secret(backup.PASSPHRASE_SECRET_NAME, "a different one entirely")
        result = backup.verify(path)
        self.assertFalse(result["ok"])
        self.assertIn("wrong passphrase", result["detail"].lower())

    def test_encrypted_backup_without_configured_passphrase_refuses_cleanly(self):
        bootstrap.set_secret(backup.PASSPHRASE_SECRET_NAME, "set for creation")
        self._seed()
        path = backup.create()

        bootstrap.set_secret(backup.PASSPHRASE_SECRET_NAME, "")
        result = backup.verify(path)
        self.assertFalse(result["ok"])
        self.assertIn("no BACKUP_PASSPHRASE", result["detail"])

    def test_no_passphrase_configured_behaves_exactly_as_before(self):
        self._seed()
        path = backup.create()
        self.assertFalse(backup.is_encrypted(path))

        result = backup.verify(path)
        self.assertTrue(result["ok"])
        self.assertEqual(result["integrity"], "ok")

        # Regression: the archive itself is still a plain tar.gz -- no
        # encryption wrapper, byte-identical in structure to the
        # pre-encryption implementation, extractable directly.
        import tarfile
        with tarfile.open(path, "r:gz") as tar:
            names = tar.getnames()
        self.assertIn("state/aion.sqlite3", names)

    def test_no_secret_in_artifact_filename_or_log_detail(self):
        bootstrap.set_secret(backup.PASSPHRASE_SECRET_NAME, "super-secret-drill-phrase")
        self._seed()
        path = backup.create()

        self.assertNotIn("super-secret-drill-phrase", path.name)

        from aion_core import db
        rows = db.connect().execute(
            "SELECT detail FROM events WHERE kind='backup.create' ORDER BY at DESC LIMIT 1"
        ).fetchall()
        self.assertTrue(rows)
        self.assertNotIn("super-secret-drill-phrase", rows[0]["detail"])


if __name__ == "__main__":
    unittest.main()
