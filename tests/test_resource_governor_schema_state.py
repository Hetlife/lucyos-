import unittest

from aion_core.resource_governor import flags, schema, state
from tests.base import AionTest


class TestSchema(AionTest):
    def test_empty_resource_is_all_null_and_unknown(self):
        r = schema.empty_resource("claude")
        self.assertEqual(r["confidence"], "UNKNOWN")
        self.assertIsNone(r["context"]["used_pct"])
        self.assertIsNone(r["quota"]["remaining_pct"])
        self.assertFalse(schema.is_known(r))
        self.assertIsNone(schema.remaining_pct(r))

    def test_rejects_bad_confidence(self):
        with self.assertRaises(ValueError):
            schema.empty_resource("claude", confidence="MADE_UP")

    def test_remaining_pct_prefers_the_more_constrained_of_quota_and_context(self):
        r = schema.empty_resource("claude", confidence="OFFICIAL_CURRENT")
        r["quota"]["remaining_pct"] = 80.0
        r["context"]["used_pct"] = 90.0  # context remaining = 10%, tighter than quota
        self.assertEqual(schema.remaining_pct(r), 10.0)

    def test_quota_high_context_low_is_still_constrained(self):
        r = schema.empty_resource("claude", confidence="OFFICIAL_CURRENT")
        r["quota"]["remaining_pct"] = 95.0
        r["context"]["used_pct"] = 92.0
        self.assertEqual(state.base_state(r), "CRITICAL")

    def test_quota_low_context_high_is_still_constrained(self):
        r = schema.empty_resource("claude", confidence="OFFICIAL_CURRENT")
        r["quota"]["remaining_pct"] = 3.0
        r["context"]["used_pct"] = 5.0
        self.assertEqual(state.base_state(r), "EXHAUSTED")


class TestStateMachine(AionTest):
    def _resource(self, remaining_pct, confidence="OFFICIAL_CURRENT"):
        r = schema.empty_resource("claude", confidence=confidence)
        r["quota"]["remaining_pct"] = remaining_pct
        r["quota"]["used_pct"] = 100 - remaining_pct
        return r

    def test_normal_capacity(self):
        self.assertEqual(state.base_state(self._resource(70.0)), "NORMAL")

    def test_low_capacity_is_critical(self):
        self.assertEqual(state.base_state(self._resource(8.0)), "CRITICAL")

    def test_exhausted_below_critical_threshold(self):
        self.assertEqual(state.base_state(self._resource(2.0)), "EXHAUSTED")

    def test_unknown_capacity_stays_unknown_never_zero(self):
        r = schema.empty_resource("claude")  # no telemetry at all
        self.assertEqual(state.base_state(r), "UNKNOWN")

    def test_quota_null_falls_back_to_context_or_unknown(self):
        r = schema.empty_resource("claude", confidence="LOCAL_OBSERVED")
        r["context"]["used_pct"] = 60.0  # quota unknown, context known
        self.assertEqual(state.base_state(r), "CONSERVE")

    def test_available_at_high_remaining(self):
        self.assertEqual(state.base_state(self._resource(99.0)), "AVAILABLE")

    def test_thresholds_are_configurable(self):
        flags.set_threshold("CRITICAL", 20.0)
        self.assertEqual(state.base_state(self._resource(15.0)), "EXHAUSTED")

    def test_overall_takes_the_worst_known_state(self):
        good = self._resource(90.0)
        bad = self._resource(2.0)
        unknown = schema.empty_resource("codex")
        self.assertEqual(state.overall({"claude": good, "codex_bad": bad, "codex": unknown}),
                         "EXHAUSTED")

    def test_overall_with_no_known_providers_is_unknown(self):
        self.assertEqual(state.overall({"claude": schema.empty_resource("claude"),
                                        "codex": schema.empty_resource("codex")}), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
