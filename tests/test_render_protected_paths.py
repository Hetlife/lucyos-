"""S-20: PROTECTED_PATHS.md drift check against HIGH_MODEL_BASELINE.json.

The render script only prints to stdout; it never writes into
`.lucy/authority/**` (constitutional, can't be touched by this task). Fable
applies the rendered result to the real doc by hand. This test suite proves
the render is complete and proves the drift check itself actually works --
including against the live baseline and the live doc, which is the whole
point of the task.
"""
import unittest
from pathlib import Path

from scripts.render_protected_paths import load_baseline, missing_from_doc, render

REPO = Path(__file__).resolve().parent.parent
DOC_PATH = REPO / ".lucy" / "authority" / "PROTECTED_PATHS.md"


class RenderProtectedPathsTest(unittest.TestCase):
    def test_render_includes_every_constitutional_and_protected_path(self):
        baseline = load_baseline()
        out = render(baseline)
        for p in baseline["constitutional_paths_no_override_possible"]:
            self.assertIn(p, out, f"constitutional path {p!r} missing from rendered output")
        for p in baseline["protected_paths"]:
            self.assertIn(p, out, f"protected path {p!r} missing from rendered output")

    def test_render_separates_constitutional_from_merely_protected(self):
        baseline = load_baseline()
        out = render(baseline)
        constitutional_section, _, protected_section = out.partition(
            "## Protected (task override possible")
        for p in baseline["constitutional_paths_no_override_possible"]:
            self.assertIn(p, constitutional_section)

    def test_missing_from_doc_finds_nothing_missing_for_paths_present(self):
        doc = "the doc mentions `foo/bar.py` and `baz/**` explicitly"
        self.assertEqual(missing_from_doc(["foo/bar.py", "baz/**"], doc), [])

    def test_missing_from_doc_catches_an_absent_path(self):
        doc = "the doc mentions `foo/bar.py` only"
        self.assertEqual(missing_from_doc(["foo/bar.py", "not/mentioned.py"], doc),
                          ["not/mentioned.py"])

    def test_drift_check_would_fail_if_baseline_gained_an_untracked_path(self):
        """Proves the mechanism per the task's own acceptance criterion:
        'would fail if a path were added to the baseline alone', without
        mutating the real baseline file to demonstrate it."""
        baseline = load_baseline()
        doc_text = DOC_PATH.read_text(encoding="utf-8")
        synthetic_paths = list(baseline["protected_paths"]) + ["aion_core/this_path_does_not_exist.py"]
        missing = missing_from_doc(synthetic_paths, doc_text)
        self.assertIn("aion_core/this_path_does_not_exist.py", missing)

    def test_current_doc_matches_baseline(self):
        """The actual drift check: every protected_paths and constitutional
        entry in the live baseline must appear verbatim in the live
        PROTECTED_PATHS.md. A failure here is real drift to fix in the doc,
        not a bug in this test -- and this task cannot edit
        .lucy/authority/** to paper over it."""
        baseline = load_baseline()
        doc_text = DOC_PATH.read_text(encoding="utf-8")
        all_paths = list(baseline["protected_paths"]) + list(
            baseline["constitutional_paths_no_override_possible"])
        missing = missing_from_doc(all_paths, doc_text)
        self.assertEqual(missing, [],
                          f"PROTECTED_PATHS.md has drifted from the baseline -- "
                          f"missing verbatim mention of: {missing}")


if __name__ == "__main__":
    unittest.main()
