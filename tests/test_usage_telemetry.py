import json
from unittest.mock import Mock

from aion_core import db, usage_telemetry
from tests.base import AionTest


class TestUsageTelemetry(AionTest):
    def test_ccusage_snapshot_is_supplemental_and_zero_ai(self):
        payload = {"daily": [{"date": "2026-09-17"}], "totals": {
            "inputTokens": 100, "outputTokens": 20, "cacheCreationTokens": 3,
            "cacheReadTokens": 7, "totalTokens": 130, "totalCost": 0.42}}
        runner = Mock(return_value=Mock(returncode=0, stdout=json.dumps(payload), stderr=""))
        before = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        snap = usage_telemetry.refresh(command=["ccusage"], runner=runner)
        after = db.connect().execute("SELECT COUNT(*) FROM model_usage").fetchone()[0]
        self.assertTrue(snap["ok"])
        self.assertEqual(snap["totals"]["total_tokens"], 130)
        self.assertEqual(before, after)
        self.assertEqual(usage_telemetry.latest()["source"], "ccusage")

    def test_missing_ccusage_degrades_without_error(self):
        snap = usage_telemetry.read_ccusage(command=[])
        self.assertFalse(snap["ok"])
