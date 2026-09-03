import unittest

from tests.base import AionTest
from aion_core import backup, bootstrap, db, fable, memory, resume, seed, tasks


class TestSeed(AionTest):
    def test_seed_creates_objective_decisions_and_queue(self):
        result = seed.apply()
        self.assertEqual(result["decisions"], len(seed.DECISIONS))
        self.assertEqual(len(result["tasks"]), len(seed.TASKS))
        self.assertTrue(memory.search("revenue"))
        self.assertEqual(resume.load()["objective"], seed.OBJECTIVE)

    def test_seed_is_idempotent(self):
        seed.apply()
        before = len(tasks.ready(50))
        again = seed.apply()
        self.assertEqual(again["skipped"], 1)
        self.assertEqual(len(tasks.ready(50)), before)

    def test_design_outranks_and_gates_decomposition(self):
        seed.apply()
        top = tasks.ready(50)[0]
        self.assertIn("Design the first real revenue experiment", top["title"])
        decompose = [t for t in tasks.by_status("READY")
                     if t["title"].startswith("Decompose")][0]
        self.assertEqual(decompose["dependencies"], top["task_id"])
        self.assertNotIn(decompose["task_id"], [t["task_id"] for t in tasks.ready(50)])

    def test_a_seeded_install_reaches_fable_ready(self):
        seed.apply()
        bootstrap.init_secret_store()
        backup.create()
        resume.boot()
        fable.build_pack()
        ok, gaps = fable.is_ready()
        self.assertTrue(ok, f"not ready: {gaps}")

    def test_start_prompt_names_real_paths_and_the_budget(self):
        seed.apply()
        fable.build_pack()
        prompt = (self.tmp / "FABLE" / "FABLE_START_PROMPT.txt").read_text()
        self.assertIn(str(self.tmp), prompt)
        self.assertIn("INR 2000", prompt)
        self.assertIn("aion boot", prompt)
        self.assertIn("Design the first real revenue experiment", prompt)

    def test_budget_starts_unspent_and_tracks_only_strong_model_use(self):
        from aion_core import metrics
        metrics.record_usage("cheap", "B", cost_inr=120)
        self.assertEqual(fable.budget()["used"], 0.0)
        metrics.record_usage("strong", "C", cost_inr=200)
        self.assertEqual(fable.budget()["used"], 200.0)
        self.assertEqual(fable.budget()["remaining"], 1800.0)


if __name__ == "__main__":
    unittest.main()
