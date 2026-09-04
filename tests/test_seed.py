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
        # Mission-level framing outranks a single experiment, and both outrank
        # the decomposition that depends on the experiment existing.
        self.assertEqual(top["model_class"], "C")
        design = [t for t in tasks.ready(50)
                  if t["title"].startswith("Design the first real revenue")][0]
        self.assertIn(design["task_id"], [t["task_id"] for t in tasks.ready(50)[:3]])
        decompose = [t for t in tasks.by_status("READY")
                     if t["title"].startswith("Decompose")][0]
        self.assertEqual(decompose["dependencies"], design["task_id"])
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
        self.assertIn("INR 4000", prompt)
        self.assertIn("aion boot", prompt)
        self.assertIn("Design the first real revenue experiment", prompt)

    def test_budget_starts_unspent_and_tracks_only_strong_model_use(self):
        from aion_core import metrics
        metrics.record_usage("cheap", "B", cost_inr=120)
        self.assertEqual(fable.budget()["used"], 0.0)
        metrics.record_usage("strong", "C", cost_inr=200)
        self.assertEqual(fable.budget()["used"], 200.0)
        self.assertEqual(fable.budget()["remaining"], 3800.0)


if __name__ == "__main__":
    unittest.main()


class TestMission(AionTest):
    def test_mission_and_milestones_are_stored(self):
        seed.apply()
        self.assertTrue(memory.search("portfolio businesses autonomously"))
        for code, _, _ in seed.MILESTONES:
            self.assertTrue(memory.search(f"milestone {code}"), f"{code} missing")

    def test_money_report_shows_progress_against_the_mission(self):
        from aion_core import metrics, milestones, reports
        seed.apply()
        before = reports.money()
        self.assertIn("Mission: INR 1,00,000/month", before)
        self.assertIn("M0 first real rupee: not reached", before)
        metrics.record_money("revenue", 1000, stage="ACTUAL", evidence="pay_TEST1")
        after = reports.money()
        self.assertIn("1.0% of it", after)
        self.assertIn("M0 first real rupee: reached", after)
        self.assertIn("M0", milestones.reached())

    def test_a_projection_does_not_move_mission_progress(self):
        from aion_core import metrics, reports
        seed.apply()
        metrics.record_money("revenue", 500000, stage="FORECAST", description="pipeline")
        self.assertIn("at 0.0% of it", reports.money())

    def test_the_portfolio_is_not_hard_coded_to_one_business(self):
        seed.apply()
        a = tasks.create("work for business A", project="alpha")
        b = tasks.create("work for business B", project="beta")
        self.assertEqual(tasks.get(a)["project"], "alpha")
        self.assertEqual(tasks.get(b)["project"], "beta")
        self.assertEqual(len(tasks.ready(50)), len(seed.TASKS) - 1 + 2)


class TestTwoPhaseBudget(AionTest):
    def test_phases_split_the_authorisation(self):
        from aion_core import fable
        b = fable.budget()
        self.assertEqual(b["phase"], "1")
        self.assertEqual(b["phase_cap_inr"], 1000.0)
        self.assertFalse(b["phase_needs_machine"])
        self.assertEqual(b["maximum_cumulative_authorization"], 4000.0)

    def test_spend_is_attributed_to_the_active_phase(self):
        from aion_core import fable, metrics
        metrics.record_usage("strong", "C", cost_inr=400)
        self.assertEqual(fable.budget()["phase_used_inr"], 400.0)
        self.assertEqual(fable.budget()["phase_remaining_inr"], 600.0)
        fable.set_phase("2")
        b = fable.budget()
        self.assertEqual(b["phase_used_inr"], 0.0, "phase 2 starts fresh")
        self.assertEqual(b["phase_cap_inr"], 3000.0)
        self.assertTrue(b["phase_needs_machine"])
        self.assertEqual(b["used"], 400.0, "cumulative spend still counts everything")

    def test_offline_prompt_forbids_claiming_execution(self):
        from aion_core import fable
        fable.build_pack()
        text = (self.tmp / "FABLE" / "FABLE_OFFLINE_PROMPT.txt").read_text()
        self.assertIn("Do not claim you ran anything", text)
        self.assertIn("INR 1000", text)
        self.assertIn("EXPERIMENT.md", text)
        self.assertIn("validation_command", text)
