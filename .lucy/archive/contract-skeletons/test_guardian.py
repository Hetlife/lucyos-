"""S-17: contract C5's deployment guardian, proven as a state machine that
cannot deploy -- not a mock of one that would."""
import unittest

from aion_core import guardian


class GuardianPipelineTest(unittest.TestCase):
    def test_enabled_flag_defaults_off(self):
        self.assertFalse(guardian.ENABLED)

    def test_stages_run_in_order(self):
        p = guardian.Pipeline("D-1")
        p.advance("SNAPSHOT", {"db_hash": "abc"})
        p.advance("ISOLATE", {"branch": "task/x"})
        self.assertEqual(p.current_stage(), "ISOLATE")
        self.assertEqual(list(p.evidence), ["SNAPSHOT", "ISOLATE"])

    def test_cannot_skip_a_stage(self):
        p = guardian.Pipeline("D-2")
        p.advance("SNAPSHOT", {"db_hash": "abc"})
        with self.assertRaises(guardian.GuardianError):
            p.advance("TEST", {"result": "pass"})  # skips ISOLATE/IMPLEMENT

    def test_cannot_advance_without_evidence(self):
        p = guardian.Pipeline("D-3")
        with self.assertRaises(guardian.GuardianError):
            p.advance("SNAPSHOT", {})
        with self.assertRaises(guardian.GuardianError):
            p.advance("SNAPSHOT", None)

    def test_exit_code_alone_is_not_evidence(self):
        p = guardian.Pipeline("D-4")
        # An int, even a "successful" 0, is not a dict of asserted state.
        with self.assertRaises(guardian.GuardianError):
            p.advance("SNAPSHOT", 0)

    def test_limited_deploy_refused_while_disabled(self):
        p = guardian.Pipeline("D-5")
        for stage, ev in [
            ("SNAPSHOT", {"db_hash": "abc"}),
            ("ISOLATE", {"branch": "task/x"}),
            ("IMPLEMENT", {"diff": "3 files"}),
            ("TEST", {"suite": "pass", "count": 274}),
            ("STATIC_SECURITY", {"scan": "clean"}),
            ("INDEPENDENT_VERIFY", {"reviewer": "second-pass", "ok": True}),
            ("STAGE", {"staged_at": "staging-host"}),
            ("HEALTH_CHECK", {"healthy": True}),
        ]:
            p.advance(stage, ev)
        self.assertFalse(guardian.ENABLED)
        with self.assertRaises(guardian.GuardianError):
            p.advance("LIMITED_DEPLOY", {"deployed": True})
        # A refused advance must not have moved the pipeline forward.
        self.assertEqual(p.current_stage(), "HEALTH_CHECK")

    def test_limited_deploy_permitted_only_if_module_flag_flipped(self):
        p = guardian.Pipeline("D-6")
        for stage in guardian.STAGES[:8]:
            p.advance(stage, {"evidence": stage})
        original = guardian.ENABLED
        try:
            guardian.ENABLED = True
            p.advance("LIMITED_DEPLOY", {"deployed": True})
            self.assertEqual(p.current_stage(), "LIMITED_DEPLOY")
        finally:
            guardian.ENABLED = original

    def test_injected_failure_at_each_stage_triggers_rollback(self):
        for i, failing_stage in enumerate(guardian.STAGES[:8]):
            p = guardian.Pipeline(f"D-fail-{i}")
            for stage in guardian.STAGES[:i]:
                p.advance(stage, {"evidence": stage})
            p.rollback(f"injected failure at {failing_stage}")
            self.assertEqual(p.status, guardian.ROLLED_BACK)
            self.assertEqual(p.evidence["AUTO_ROLLBACK"]["at_stage"], p.current_stage())
            with self.assertRaises(guardian.GuardianError):
                p.advance(guardian.STAGES[i], {"evidence": "retry after rollback"})

    def test_rollback_is_terminal_not_resumable(self):
        p = guardian.Pipeline("D-7")
        p.advance("SNAPSHOT", {"db_hash": "abc"})
        p.rollback("static/security scan found a finding")
        with self.assertRaises(guardian.GuardianError):
            p.advance("ISOLATE", {"branch": "task/x"})
        with self.assertRaises(guardian.GuardianError):
            p.rollback("cannot roll back twice")

    def test_pipeline_completes_only_after_every_stage(self):
        p = guardian.Pipeline("D-8")
        guardian_stages = guardian.STAGES
        original = guardian.ENABLED
        try:
            guardian.ENABLED = True
            for stage in guardian_stages:
                self.assertNotEqual(p.status, guardian.COMPLETE)
                p.advance(stage, {"evidence": stage})
            self.assertEqual(p.status, guardian.COMPLETE)
            self.assertEqual(p.current_stage(), "EVIDENCE")
            with self.assertRaises(guardian.GuardianError):
                p.advance("EVIDENCE", {"evidence": "again"})
        finally:
            guardian.ENABLED = original

    def test_evidence_is_stored_independently_per_stage(self):
        p = guardian.Pipeline("D-9")
        p.advance("SNAPSHOT", {"db_hash": "abc123"})
        p.advance("ISOLATE", {"branch": "task/y"})
        self.assertEqual(p.evidence["SNAPSHOT"], {"db_hash": "abc123"})
        self.assertEqual(p.evidence["ISOLATE"], {"branch": "task/y"})
        # Mutating a caller-held evidence dict after advance() must not
        # retroactively rewrite the recorded evidence.
        ev = {"db_hash": "will-be-mutated"}
        p2 = guardian.Pipeline("D-10")
        p2.advance("SNAPSHOT", ev)
        ev["db_hash"] = "mutated-after"
        self.assertEqual(p2.evidence["SNAPSHOT"]["db_hash"], "will-be-mutated")


if __name__ == "__main__":
    unittest.main()
