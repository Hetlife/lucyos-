import hashlib
import unittest
from pathlib import Path

from devices.little_lucy import bridge

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "platforms" / "nebula" / "native"
FONT_SHA256 = "ae7b7855e115a5966d8b1b3f80f254ccc117ec86f9965e202ee2940453837280"


class NativeProvenanceTests(unittest.TestCase):
    def test_expected_source_files_exist(self):
        for name in ("__init__.py", "client.py", "ui.py", "font.ttf", "FONT-LICENSE.txt", "README.md"):
            self.assertTrue((NATIVE / name).is_file(), name)
        self.assertTrue((ROOT / "bridge.py").is_file())

    def test_private_pairing_material_was_not_imported(self):
        forbidden = {
            "connection.json", "token", "server.key", "server.crt", "client.log", "calibration.json",
        }
        present = {path.name for path in NATIVE.iterdir() if path.is_file()}
        self.assertTrue(forbidden.isdisjoint(present))

    def test_font_provenance_is_pinned_and_licensed(self):
        data = (NATIVE / "font.ttf").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), FONT_SHA256)
        license_text = (NATIVE / "FONT-LICENSE.txt").read_text(encoding="utf-8")
        self.assertIn("DejaVu", license_text)
        self.assertIn("Bitstream Vera", license_text)

    def test_bridge_defaults_to_this_repository(self):
        self.assertEqual(bridge.REPO_ROOT, ROOT.parents[1])
        self.assertIn("LUCYOS_REPO", (ROOT / "bridge.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
