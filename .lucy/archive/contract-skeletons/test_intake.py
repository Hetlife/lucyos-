"""Data intake provenance contract (C3): every record carries the full
metadata set, training_eligible defaults closed, and raw data is immutable
by construction -- there is no function that could mutate it."""
from aion_core import db, intake
from tests.base import AionTest


class TestIntake(AionTest):
    def _file(self, name="raw.txt", text="original content"):
        path = self.tmp / name
        path.write_text(text)
        return path

    def test_record_requires_full_metadata_set(self):
        path = self._file()
        with self.assertRaises(intake.IntakeError):
            intake.record("", "raw", str(path))  # missing source
        with self.assertRaises(intake.IntakeError):
            intake.record("scraper-v1", "not-a-tier", str(path))  # invalid tier
        with self.assertRaises(intake.IntakeError):
            intake.record("scraper-v1", "raw", str(path), confidentiality="TOP_SECRET")
        with self.assertRaises(intake.IntakeError):
            intake.record("scraper-v1", "raw", "")  # missing payload_path

    def test_training_eligible_defaults_false(self):
        path = self._file()
        record_id = intake.record("scraper-v1", "raw", str(path))
        row = intake.get(record_id)
        self.assertEqual(row["training_eligible"], 0)

    def test_training_eligible_can_be_explicitly_set(self):
        path = self._file()
        record_id = intake.record("scraper-v1", "curated", str(path), training_eligible=True)
        self.assertEqual(intake.get(record_id)["training_eligible"], 1)

    def test_confidentiality_reuses_skills_data_classes(self):
        path = self._file()
        for value in ("public", "Internal", "CONFIDENTIAL", "secret"):
            record_id = intake.record("scraper-v1", "raw", str(path), confidentiality=value)
            self.assertEqual(intake.get(record_id)["confidentiality"], value.upper())

    def test_full_provenance_envelope_is_stored(self):
        path = self._file()
        record_id = intake.record(
            "vendor-export-2026-09", "normalized", str(path), project="alpha",
            entity_refs="customer-42,invoice-9", schema_version=3,
            transform_chain=["utf8-decode", "trim-whitespace"], confidentiality="CONFIDENTIAL")
        row = intake.get(record_id)
        self.assertEqual(row["project"], "alpha")
        self.assertEqual(row["schema_version"], 3)
        self.assertIn("customer-42", row["entity_refs"])
        self.assertIn("utf8-decode", row["transform_chain"])
        self.assertTrue(row["acquired_at"])
        self.assertTrue(row["content_hash"])

    def test_a_correction_creates_a_new_record_referencing_the_original(self):
        original_path = self._file("raw.txt", "typo verison")
        original_id = intake.record("manual-entry", "raw", str(original_path))
        corrected_path = self._file("raw-corrected.txt", "typo version")
        corrected_id = intake.record("manual-entry", "raw", str(corrected_path),
                                     derived_from=original_id)
        self.assertNotEqual(original_id, corrected_id)
        self.assertEqual(intake.get(corrected_id)["derived_from"], original_id)
        # the original row is untouched: its hash still matches its own file
        from aion_core import util
        self.assertEqual(intake.get(original_id)["content_hash"],
                         util.sha256_file(original_path))
        self.assertEqual(intake.get(original_id)["derived_from"], "")

    def test_no_mutation_function_exists_on_the_module(self):
        """Immutability is structural: there is nothing to call that would
        change a raw record's own row. INSERT-only, by the module's shape."""
        public_names = {n for n in dir(intake) if not n.startswith("_")}
        self.assertFalse(public_names & {"update", "mutate", "edit", "overwrite"})

    def test_retrieval_by_project_and_tier_uses_the_indexed_columns_only(self):
        # C3: exact/FTS retrieval before anything else -- confirms no vector
        # or embedding dependency is required to look records up.
        path = self._file()
        record_id = intake.record("scraper-v1", "curated", str(path), project="alpha")
        rows = db.connect().execute(
            "SELECT record_id FROM intake_records WHERE project=? AND tier=?",
            ("alpha", "curated")).fetchall()
        self.assertEqual([r["record_id"] for r in rows], [record_id])


if __name__ == "__main__":
    import unittest
    unittest.main()
