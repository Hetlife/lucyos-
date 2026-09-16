import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aion_core.resource_governor import providers
from aion_core.resource_governor.providers import base, claude, codex, local
from tests.base import AionTest


class TestClaudeAdapter(AionTest):
    def tearDown(self):
        os.environ.pop("AION_CLAUDE_TELEMETRY_FILE", None)
        super().tearDown()

    def test_no_file_configured_is_unknown(self):
        r = claude.read(path=None)
        self.assertEqual(r["confidence"], "UNKNOWN")

    def test_missing_file_is_unknown(self):
        r = claude.read(path=self.tmp / "does_not_exist.json")
        self.assertEqual(r["confidence"], "UNKNOWN")

    def test_malformed_json_is_unknown_not_a_crash(self):
        p = self.tmp / "claude.json"
        p.write_text("{not json", encoding="utf-8")
        r = claude.read(path=p)
        self.assertEqual(r["confidence"], "UNKNOWN")

    def test_fresh_telemetry_is_official_current(self):
        p = self.tmp / "claude.json"
        p.write_text(json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "context": {"used_tokens": 1000, "limit_tokens": 200000},
            "five_hour": {"used_pct": 40.0, "reset_at": "2026-09-16T09:00:00+00:00"},
        }), encoding="utf-8")
        r = claude.read(path=p)
        self.assertEqual(r["confidence"], "OFFICIAL_CURRENT")
        self.assertEqual(r["quota"]["remaining_pct"], 60.0)
        self.assertEqual(r["context"]["used_pct"], 0.5)

    def test_stale_telemetry_is_flagged_stale(self):
        p = self.tmp / "claude.json"
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        p.write_text(json.dumps({"updated_at": old, "five_hour": {"used_pct": 10.0}}),
                    encoding="utf-8")
        r = claude.read(path=p)
        self.assertEqual(r["confidence"], "OFFICIAL_STALE")

    def test_binding_window_picks_the_more_constrained_one(self):
        p = self.tmp / "claude.json"
        p.write_text(json.dumps({
            "five_hour": {"used_pct": 20.0}, "seven_day": {"used_pct": 90.0},
        }), encoding="utf-8")
        r = claude.read(path=p)
        self.assertEqual(r["quota"]["used_pct"], 90.0)

    def test_env_var_path_is_used_when_no_explicit_path(self):
        p = self.tmp / "claude_env.json"
        p.write_text(json.dumps({"five_hour": {"used_pct": 11.0}}), encoding="utf-8")
        os.environ["AION_CLAUDE_TELEMETRY_FILE"] = str(p)
        r = claude.read()
        self.assertEqual(r["quota"]["used_pct"], 11.0)


class TestCodexAdapter(AionTest):
    def test_no_file_is_unknown(self):
        self.assertEqual(codex.read(path=None)["confidence"], "UNKNOWN")

    def test_partial_data_reports_exactly_what_is_known(self):
        p = self.tmp / "codex.json"
        p.write_text(json.dumps({"context": {"used_tokens": 500, "limit_tokens": 1000}}),
                    encoding="utf-8")
        r = codex.read(path=p)
        self.assertEqual(r["context"]["used_pct"], 50.0)
        self.assertIsNone(r["quota"]["used_pct"])
        self.assertNotEqual(r["confidence"], "UNKNOWN")

    def test_never_fabricates_a_fixed_allowance(self):
        p = self.tmp / "codex.json"
        p.write_text(json.dumps({}), encoding="utf-8")
        r = codex.read(path=p)
        self.assertEqual(r["confidence"], "UNKNOWN")
        self.assertIsNone(r["quota"]["remaining_pct"])


class TestBaseSafety(AionTest):
    def test_safe_read_survives_a_raising_adapter(self):
        def boom():
            raise RuntimeError("adapter exploded")
        r = base.safe_read("broken", boom)
        self.assertEqual(r["confidence"], "UNKNOWN")
        self.assertIn("error", r)

    def test_safe_read_survives_a_malformed_return(self):
        r = base.safe_read("broken", lambda: {"not": "a resource"})
        self.assertEqual(r["confidence"], "UNKNOWN")

    def test_read_all_never_raises_even_if_every_provider_is_unconfigured(self):
        result = providers.read_all()
        self.assertIn("claude", result)
        self.assertIn("codex", result)
        for r in result.values():
            self.assertIn(r["confidence"], ("UNKNOWN", "OFFICIAL_CURRENT", "OFFICIAL_STALE",
                                            "LOCAL_OBSERVED", "LOCAL_ESTIMATE"))


class TestLocalProvider(AionTest):
    def test_read_reports_availability_and_queue_depth(self):
        r = local.read()
        self.assertIn("available", r)
        self.assertIn("queue_depth", r)
        self.assertGreaterEqual(r["queue_depth"], 0)

    def test_ram_reader_never_raises_on_a_missing_proc(self):
        # /proc/meminfo not existing (non-Linux) must return None, not raise.
        result = local._ram_available_mb()
        self.assertTrue(result is None or isinstance(result, int))


if __name__ == "__main__":
    unittest.main()
