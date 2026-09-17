"""S-23: aion export / aion import -- move a shared brain between hosts."""
import io
import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from tests.base import AionTest
from aion_core import config, db, memory, portability, security, tasks


class PortabilityExportTest(AionTest):
    def _seed(self):
        tasks.create("export seed task one")
        tasks.create("export seed task two")
        memory.remember("fact", "export seed memory", "body text")
        db.connect().commit()

    def test_export_import_round_trip_reproduces_counts(self):
        self._seed()
        conn = db.connect()
        pre_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        pre_mem = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]

        archive = portability.export()
        self.assertTrue(archive.exists())

        result = portability.import_(archive)
        self.assertTrue(result["ok"])
        self.assertEqual(result["tasks"], pre_tasks)
        self.assertEqual(result["memories"], pre_mem)

        conn = db.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], pre_tasks)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0], pre_mem)

    def test_round_trip_survives_source_home_deletion(self):
        self._seed()
        conn = db.connect()
        pre_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        pre_mem = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]

        archive = portability.export()
        # Copy the archive out of the source AION_HOME before destroying it --
        # the archive itself must be self-contained.
        moved = Path(tempfile.mkdtemp(prefix="aion-export-copy-")) / archive.name
        shutil.copy2(archive, moved)

        db.close()
        source_home = self.tmp
        shutil.rmtree(source_home, ignore_errors=True)

        fresh_home = Path(tempfile.mkdtemp(prefix="aion-test-fresh-"))
        try:
            import os
            os.environ["AION_HOME"] = str(fresh_home)
            db.close()
            from aion_core import bootstrap
            bootstrap.ensure()

            result = portability.import_(moved)
            self.assertTrue(result["ok"])
            self.assertEqual(result["tasks"], pre_tasks)
            self.assertEqual(result["memories"], pre_mem)

            conn = db.connect()
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], pre_tasks)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0], pre_mem)
        finally:
            db.close()
            shutil.rmtree(fresh_home, ignore_errors=True)
            shutil.rmtree(moved.parent, ignore_errors=True)
            import os
            os.environ["AION_HOME"] = str(self.tmp)

    def test_tampered_content_hash_is_refused(self):
        self._seed()
        archive = portability.export()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(tmp_path, filter="data")
            manifest_path = tmp_path / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["content_hash"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest))

            tampered = Path(tmp) / "tampered.tar.gz"
            with tarfile.open(tampered, "w:gz") as tar:
                for member in sorted(tmp_path.rglob("*")):
                    if member.is_file():
                        tar.add(member, arcname=member.relative_to(tmp_path).as_posix())

            with self.assertRaises(portability.PortabilityError):
                portability.import_(tampered)

    def test_unknown_schema_version_is_refused_not_guessed(self):
        self._seed()
        archive = portability.export()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(tmp_path, filter="data")
            manifest_path = tmp_path / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["schema_version"] = manifest["schema_version"] + 999
            manifest_path.write_text(json.dumps(manifest))

            future = Path(tmp) / "future.tar.gz"
            with tarfile.open(future, "w:gz") as tar:
                for member in sorted(tmp_path.rglob("*")):
                    if member.is_file():
                        tar.add(member, arcname=member.relative_to(tmp_path).as_posix())

            with self.assertRaises(portability.PortabilityError):
                portability.import_(future)

    def test_import_refuses_path_traversal_archive(self):
        outside = self.tmp.parent / "portability-escape-proof.txt"
        outside.unlink(missing_ok=True)
        malicious = self.tmp / "malicious.tar.gz"
        payload = b"must-not-escape"
        with tarfile.open(malicious, "w:gz") as tar:
            info = tarfile.TarInfo("../portability-escape-proof.txt")
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))

        with self.assertRaises(portability.PortabilityError):
            portability.import_(malicious)
        self.assertFalse(outside.exists())

    def test_archive_contains_no_secret_and_no_absolute_path(self):
        self._seed()
        # Plant a secret in private_state to prove it never reaches the archive.
        priv = config.home() / "private_state"
        priv.mkdir(parents=True, exist_ok=True)
        # Built via concatenation so the literal never sits in this source
        # file as a contiguous credential-shaped string (this file is not
        # in .secretscanignore, and should not need to be -- the point of
        # this test is the archive's contents, not the repo's own source).
        fake_token = "ghp_" + "AbCdEfGhIjKlMnOpQrStUvWxYz012345"
        (priv / "secrets.env").write_text(f"GITHUB_TOKEN={fake_token}\n")

        archive = portability.export()

        with tarfile.open(archive, "r:gz") as tar:
            names = tar.getnames()
            self.assertTrue(all(not n.startswith("/") for n in names),
                             f"archive contains an absolute path: {names}")
            self.assertTrue(all("private_state" not in n for n in names),
                             f"archive leaked private_state: {names}")

            with tempfile.TemporaryDirectory() as tmp:
                tar.extractall(tmp, filter="data")
                found = security.scan_paths(Path(tmp))
                self.assertEqual(found, [], f"archive contains secret-shaped content: {found}")


if __name__ == "__main__":
    unittest.main()
