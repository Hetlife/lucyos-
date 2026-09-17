"""Direct tests for aion_core.util's newer helpers.

ago() and sha256_bytes() were added while consolidating four call sites
(aion_core/sessions.py, aion_core/tasks.py, bridges/drive_bridge.py,
bridges/whatsapp_bridge.py) that had each reimplemented a piece of this —
found by the smallest-fix skill's check_reinvention.py, confirmed by reading
each site, then fixed here rather than left as duplicated logic.
"""
from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from aion_core import util


class TestNow(unittest.TestCase):
    def test_now_has_no_microseconds(self):
        self.assertNotIn(".", util.now().split("+")[0])

    def test_now_is_utc(self):
        self.assertTrue(util.now().endswith("+00:00"))


class TestAgo(unittest.TestCase):
    def test_ago_zero_is_within_a_second_of_now(self):
        before = datetime.now(timezone.utc)
        result = datetime.fromisoformat(util.ago(seconds=0))
        self.assertLess(abs((before - result).total_seconds()), 2)

    def test_ago_subtracts_the_requested_amount(self):
        now = datetime.fromisoformat(util.now())
        seven_days_ago = datetime.fromisoformat(util.ago(days=7))
        delta = now - seven_days_ago
        self.assertAlmostEqual(delta.total_seconds(), timedelta(days=7).total_seconds(), delta=2)

    def test_ago_has_no_microseconds_like_now(self):
        """The bug this fixed: a hand-rolled cutoff kept microseconds while
        rows stamped by now() never do, so an ISO-string comparison could be
        wrong right at the cutoff second."""
        self.assertNotIn(".", util.ago(days=1).split("+")[0])

    def test_ago_accepts_any_timedelta_keyword(self):
        # must not raise for any of the shapes real call sites use
        util.ago(seconds=2700)
        util.ago(days=14)
        util.ago(hours=1, minutes=30)


class TestSha256Bytes(unittest.TestCase):
    def test_matches_hashlib_directly(self):
        data = b"the quick brown fox"
        self.assertEqual(util.sha256_bytes(data), hashlib.sha256(data).hexdigest())

    def test_sha256_text_delegates_to_sha256_bytes(self):
        self.assertEqual(util.sha256_text("hello"), util.sha256_bytes(b"hello"))

    def test_empty_bytes(self):
        self.assertEqual(util.sha256_bytes(b""), hashlib.sha256(b"").hexdigest())


if __name__ == "__main__":
    unittest.main()
