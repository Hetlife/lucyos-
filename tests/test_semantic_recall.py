import importlib.util
from pathlib import Path
import tempfile
import unittest

from aion_core import memory, semantic_recall
from tests.base import AionTest

HAS_VEC = importlib.util.find_spec("sqlite_vec") is not None


@unittest.skipUnless(HAS_VEC, "optional sqlite-vec dependency not installed")
class TestSemanticRecall(AionTest):
    def test_derived_index_keeps_canonical_memory_and_returns_nearest(self):
        memory.remember("fact", "Mac local AI", "Apple Silicon runs local inference")
        memory.remember("fact", "Cloud fallback", "External API fallback for public tasks")
        def embed(texts):
            out=[]
            for t in texts:
                low=t.lower()
                out.append([1.0, 0.0] if ("mac" in low or "apple" in low or "local inference" in low) else [0.0, 1.0])
            return out
        path = Path(self.tmp) / "derived.sqlite3"
        result = semantic_recall.rebuild(path=path, embed=embed)
        self.assertTrue(result["derived"])
        hits = semantic_recall.search("apple local model", path=path, embed=embed)
        self.assertEqual(hits[0]["title"], "Mac local AI")
        self.assertEqual(len(memory.search("Mac local AI")), 1)
