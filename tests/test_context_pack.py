import tempfile
import unittest
from pathlib import Path

from tests.base import AionTest
from aion_core import context_pack, db


class ContextPackTest(AionTest):
    def test_build_is_bounded_and_has_delta_index(self):
        with tempfile.TemporaryDirectory() as td:
            result = context_pack.build(Path(__file__).resolve().parents[1], focus="M1", output_dir=Path(td))
            self.assertLessEqual(result["bytes"], context_pack.MAX_MARKDOWN_BYTES + 64)
            packet = result["packet"]
            self.assertEqual(packet["focus"], "M1")
            self.assertTrue(packet["head"])
            self.assertIn("recommended_files", packet)
            self.assertTrue((Path(td) / "context.md").exists())
            self.assertTrue((Path(td) / "context.json").exists())

    def test_mark_reviewed_uses_existing_meta_store(self):
        repo = Path(__file__).resolve().parents[1]
        commit = context_pack.mark_reviewed(repo)
        self.assertEqual(db.get_meta("last_high_model_reviewed_commit"), commit)
        with tempfile.TemporaryDirectory() as td:
            result = context_pack.build(repo, output_dir=Path(td))
            self.assertEqual(result["packet"]["review_watermark"], commit)


if __name__ == "__main__":
    unittest.main()
