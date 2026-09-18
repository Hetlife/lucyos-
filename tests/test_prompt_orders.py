from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tests.base import AionTest
from aion_core import prompt_orders, sessions

class TestPromptOrders(AionTest):
    def setUp(self):
        super().setUp()
        self.repo_prompts = Path(tempfile.mkdtemp(prefix="prompt-orders-"))
        self.patcher = patch.object(prompt_orders, "root", side_effect=self._root)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.repo_prompts, ignore_errors=True)
        super().tearDown()

    def _root(self):
        for name in prompt_orders.STATES:
            (self.repo_prompts / name).mkdir(parents=True, exist_ok=True)
        return self.repo_prompts

    def test_submit_claim_archive_links_existing_session_system(self):
        row = prompt_orders.submit("Smoke test", "Read live state and report only.")
        self.assertEqual(row["status"], "PENDING")
        claim = prompt_orders.claim(row["prompt_id"], actor="test-agent")
        self.assertTrue(claim["session_id"].startswith("SES-"))
        self.assertEqual(len(sessions.open_sessions()), 1)
        done = prompt_orders.archive(row["prompt_id"], session_id=claim["session_id"], outcome="SUCCESS", evidence="live-state-check-pass")
        self.assertEqual(done["status"], "ARCHIVED")
        self.assertEqual(len(sessions.open_sessions()), 0)
        self.assertIn("USED: yes", Path(done["path"]).read_text())

    def test_blocked_cannot_be_hidden_in_archive(self):
        row = prompt_orders.submit("Blocked", "Do a safe check.")
        claim = prompt_orders.claim(row["prompt_id"], actor="test-agent")
        with self.assertRaises(ValueError):
            prompt_orders.archive(row["prompt_id"], session_id=claim["session_id"], outcome="BLOCKED", evidence="blocked")
        self.assertTrue(Path(claim["path"]).exists())

    def test_wrong_session_cannot_archive(self):
        row = prompt_orders.submit("Ownership", "Safe check.")
        claim = prompt_orders.claim(row["prompt_id"], actor="agent-a")
        with self.assertRaises(ValueError):
            prompt_orders.archive(row["prompt_id"], session_id="SES-00000000", outcome="SUCCESS", evidence="x")
    def test_duplicate_across_states_is_fail_closed(self):
        row = prompt_orders.submit("Crash window", "Safe check.")
        src = Path(row["path"])
        duplicate = self.repo_prompts / "01_PROCESSING" / src.name
        duplicate.parent.mkdir(parents=True, exist_ok=True)
        duplicate.write_text(src.read_text())
        state = prompt_orders.status(row["prompt_id"])
        self.assertTrue(state["conflict"])
        with self.assertRaises(ValueError):
            prompt_orders.claim(row["prompt_id"], actor="agent-a")

    def test_status_reports_single_lifecycle_location(self):
        row = prompt_orders.submit("Status", "Safe check.")
        state = prompt_orders.status(row["prompt_id"])
        self.assertFalse(state["conflict"])
        self.assertEqual(state["status"], "00_PENDING")

